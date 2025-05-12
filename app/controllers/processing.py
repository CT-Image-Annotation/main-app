import base64
import os
import io
import zipfile
from io import BytesIO
import json

import cv2
import numpy as np
import pydicom
from flask import (
    Blueprint, current_app, render_template, request,
    redirect, session, url_for, send_file, abort, flash, jsonify
)
from PIL import Image
from skimage import measure
from skimage.transform import resize

from app.models.Resource import Resource
from app.services.FileService import FileService
from app.services.medsam_service import MedSAMService
from app.filters import DicomFilters, Thresholding, GMM, apply_segmentation

# Blueprint for image processing routes
bp = Blueprint('processing', __name__, url_prefix='/process')

# Initialize MedSAM service (will be initialized lazily when needed)
medsam_service = MedSAMService()

# Filter names available in workspace
FILTER_NAMES = [
    'Original', 'CLAHE', 'Gamma', 'Gaussian', 'Median',
    'Non-Local Means', 'Threshold (Otsu)', 'Threshold (Binary)',
    'GMM', 'Segment'
]

# Global state to track undo/redo and history
global_original_image = None
global_current_image = None
global_history = []
global_processes = []


def get_allowed_filters():
    """Disable certain filters after threshold operations."""
    blocking = {'Threshold (Otsu)', 'Threshold (Binary)'}
    if global_processes and global_processes[-1] in blocking:
        return ['Original']
    return FILTER_NAMES


def read_and_process(path, mime_type, dataset_id=None):
    """Convert raw image or DICOM to base64 PNG for thumbnail."""
    base_folder = current_app.config['UPLOAD_FOLDER']
    if dataset_id:
        base_folder = os.path.join(base_folder, str(dataset_id))
    full_path = os.path.join(base_folder, path)

    if mime_type == 'application/dicom':
        dcm = pydicom.dcmread(full_path)
        arr = dcm.pixel_array
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        _, buf = cv2.imencode('.png', arr)
        return base64.b64encode(buf).decode('utf-8')

    img = cv2.imread(full_path)
    _, buf = cv2.imencode('.png', img)
    return base64.b64encode(buf).decode('utf-8')


@bp.route('/<int:file_id>')
def process(file_id):
    """Workspace – show the last-processed image plus history & controls."""
    global global_original_image, global_current_image, global_history, global_processes
    file = Resource.query.get_or_404(file_id)

    # Build actual filesystem path
    base_folder = current_app.config['UPLOAD_FOLDER']
    if file.dataset_id:
        base_folder = os.path.join(base_folder, str(file.dataset_id))
    img_path = os.path.join(base_folder, file.path)
    original = cv2.imread(img_path)
    if original is None:
        abort(404, description='Image file not found')

    # Reset history on new file
    if session.get('last_file') != file_id:
        global_original_image = original.copy()
        global_current_image = original.copy()
        global_history.clear()
        global_processes.clear()
        session['last_file'] = file_id

    # Encode current for display
    _, buf = cv2.imencode('.png', global_current_image)
    img_b64 = base64.b64encode(buf).decode('utf-8')

    return render_template(
        'process.html',
        file=file,
        img=img_b64,
        filter_names=FILTER_NAMES,
        allowed_filters=get_allowed_filters(),
        processes=global_processes,
        files=FileService.getUserFiles(type='AImage', dataset_id=file.dataset_id),
        read_and_process=read_and_process
    )


@bp.route('/<int:file_id>/apply', methods=['POST'])
def apply_filter(file_id):
    """Apply one filter to the current image in the workspace."""
    global global_current_image, global_history, global_processes
    name = request.form.get('filter_name')
    if name not in get_allowed_filters():
        return redirect(url_for('processing.process', file_id=file_id))

    global_history.append(global_current_image.copy())
    if name == 'Original':
        global_current_image = global_original_image.copy()
    else:
        base = global_current_image
        fmap = DicomFilters.apply_filters(base)
        thr = Thresholding(base)
        fmap['Threshold (Otsu)'] = thr.apply_otsu_threshold()
        fmap['Threshold (Binary)'] = thr.apply_binary_threshold(127)
        gmm = GMM(base); gmm.fit_gmm(n_components=2)
        fmap['GMM'] = gmm.apply_gmm_threshold()
        fmap['Segment'] = apply_segmentation(base)
        global_current_image = fmap.get(name, base)

    global_processes.append(name)
    return redirect(url_for('processing.process', file_id=file_id))


@bp.route('/<int:file_id>/undo')
def undo(file_id):
    """Undo the last single-image operation."""
    global global_current_image, global_history, global_processes
    if global_history:
        global_current_image = global_history.pop()
        global_processes.pop()
    return redirect(url_for('processing.process', file_id=file_id))


@bp.route('/<int:file_id>/reset')
def reset(file_id):
    """Reset the single-image workspace to original."""
    global global_original_image, global_current_image, global_history, global_processes
    global_current_image = global_original_image.copy()
    global_history.clear()
    global_processes.clear()
    session.pop('last_file', None)
    return redirect(url_for('processing.process', file_id=file_id))


@bp.route('/<int:file_id>/download')
def download_processed(file_id):
    """Download the currently processed single image."""
    global global_current_image
    if global_current_image is None:
        abort(404)
    success, buf = cv2.imencode('.png', global_current_image)
    if not success:
        abort(500)
    bio = io.BytesIO(buf.tobytes())
    bio.seek(0)
    return send_file(
        bio,
        mimetype='image/png',
        as_attachment=True,
        download_name=f'processed_{file_id}.png'
    )


# ── Batch processing across entire dataset ─────────────────────────────────

@bp.route('/batch/<int:ds_id>/apply', methods=['POST'])
def batch_apply(ds_id):
    """Add a filter to the per-dataset session list."""
    name = request.form['filter_name']
    if name not in FILTER_NAMES:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': f'Invalid filter name: {name}'
            })
        flash(f'Invalid filter name: {name}', 'error')
        return redirect(url_for('uploads.dataset_detail', ds_id=ds_id))

    key = f'batch_{ds_id}_processes'
    procs = session.get(key, [])
    procs.append(name)
    session[key] = procs
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'Applied "{name}" to all images.',
            'processes': procs
        })
    else:
        flash(f'Applied "{name}" to all images.', 'success')
        return redirect(url_for('uploads.dataset_detail', ds_id=ds_id))


@bp.route('/batch/<int:ds_id>/undo')
def batch_undo(ds_id):
    """Undo the last batch filter across the dataset."""
    key = f'batch_{ds_id}_processes'
    procs = session.get(key, [])
    if procs:
        procs.pop()
        session[key] = procs
        flash('Undid last batch filter.', 'info')
    else:
        flash('Nothing to undo.', 'warning')
    return redirect(url_for('uploads.dataset_detail', ds_id=ds_id))


@bp.route('/batch/<int:ds_id>/reset')
def batch_reset(ds_id):
    """Reset the entire dataset back to original images."""
    key = f'batch_{ds_id}_processes'
    session.pop(key, None)
    flash('Reset all images to original.', 'warning')
    return redirect(url_for('uploads.dataset_detail', ds_id=ds_id))


@bp.route('/batch/<int:ds_id>/download')
def batch_download(ds_id):
    """Download a ZIP of all (possibly processed) images in the dataset."""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    from app.services.DatasetService import DatasetService
    ds = DatasetService.read_for_user(ds_id, session['user_id'])
    if not ds:
        abort(403)

    files = FileService.getUserFiles(type='AImage', dataset_id=ds_id)
    memory_zip = BytesIO()
    with zipfile.ZipFile(memory_zip, 'w') as zipf:
        for f in files:
            base_folder = current_app.config['UPLOAD_FOLDER']
            if f.dataset_id:
                base_folder = os.path.join(base_folder, str(f.dataset_id))
            filepath = os.path.join(base_folder, f.path)
            zipf.write(filepath, arcname=f.path)
    memory_zip.seek(0)
    return send_file(
        memory_zip,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{ds.name}_images.zip'
    )


# ── Raw image bytes endpoint for slideshow ────────────────────────────────

@bp.route('/image/<int:file_id>')
def image(file_id):
    """
    Returns the slide image with all batch filters applied in order
    before sending it back as a PNG (or original mime-type).
    """
    try:
        print(f"Starting image endpoint for file_id: {file_id}")  # Early debug log
        
        file = Resource.query.get_or_404(file_id)
        print(f"Found file: {file.path}, mime: {file.mime}")  # Debug log

        # figure out dataset folder
        base = current_app.config['UPLOAD_FOLDER']
        if file.dataset_id:
            base = os.path.join(base, str(file.dataset_id))
        path = os.path.join(base, file.path)
        print(f"Full file path: {path}")  # Debug log

        # Check if file exists
        if not os.path.exists(path):
            print(f"File does not exist: {path}")  # Debug log
            return jsonify({'error': 'File not found'}), 404

        # load raw
        raw = None
        if file.mime == 'application/dicom' or file.path.lower().endswith('.dcm'):
            try:
                print(f"Reading DICOM file: {path}")  # Debug log
                dcm = pydicom.dcmread(path, force=True)
                print(f"Successfully read DICOM file")  # Debug log
                
                if not hasattr(dcm, 'pixel_array'):
                    print("DICOM file has no pixel array")  # Debug log
                    return jsonify({'error': 'DICOM file has no pixel data'}), 500
                    
                arr = dcm.pixel_array
                print(f"DICOM array shape: {arr.shape}, dtype: {arr.dtype}")  # Debug log
                
                # Handle different array shapes
                if len(arr.shape) == 3:  # Multi-slice DICOM
                    print("Multi-slice DICOM detected, using first slice")  # Debug log
                    arr = arr[0]  # Take first slice
                elif len(arr.shape) != 2:
                    print(f"Unexpected array shape: {arr.shape}")  # Debug log
                    return jsonify({'error': 'Unexpected DICOM array shape'}), 500
                    
                # Normalize to 8-bit
                raw = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
                print(f"Normalized array shape: {raw.shape}, dtype: {raw.dtype}")  # Debug log
                
                # Convert to 3-channel if grayscale
                if len(raw.shape) == 2:
                    raw = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
                    print("Converted grayscale to BGR")  # Debug log
                    
            except Exception as e:
                print(f"Error reading DICOM file {path}: {str(e)}")  # Debug log
                return jsonify({'error': f'Error reading DICOM file: {str(e)}'}), 500
        else:
            raw = cv2.imread(path)
            if raw is None:
                print(f"Failed to load image: {path}")  # Debug log
                return jsonify({'error': 'File not found'}), 404

        if raw is None:
            print(f"Failed to process image: {path}")  # Debug log
            return jsonify({'error': 'Failed to process image'}), 500

        # replay batch filters
        key = f'batch_{file.dataset_id}_processes'
        procs = session.get(key, [])
        img = raw.copy()
        
        for name in procs:
            if name == 'Original':
                img = raw.copy()
            elif name == 'GMM':
                # Special handling for GMM
                gmm = GMM(img)
                gmm.fit_gmm(n_components=2)
                img = gmm.apply_gmm_threshold()
                print("GMM output shape:", img.shape, "dtype:", img.dtype, "min:", img.min(), "max:", img.max())
                # Convert binary image to 3-channel if needed
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else:
                fmap = DicomFilters.apply_filters(img)
                thr = Thresholding(img)
                fmap['Threshold (Otsu)'] = thr.apply_otsu_threshold()
                fmap['Threshold (Binary)'] = thr.apply_binary_threshold(127)
                fmap['Segment'] = apply_segmentation(img)
                if name in fmap:
                    img = fmap[name]
                else:
                    print(f"Warning: Unknown filter name: {name}")

        # send out as PNG
        try:
            _, buf = cv2.imencode('.png', img)
            bio = BytesIO(buf.tobytes())
            bio.seek(0)
            print(f"Successfully encoded image to PNG, size: {len(buf.tobytes())} bytes")  # Debug log
            return send_file(bio, mimetype='image/png')
        except Exception as e:
            print(f"Error encoding image to PNG: {str(e)}")  # Debug log
            return jsonify({'error': f'Error encoding image: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Unexpected error in image endpoint: {str(e)}")  # Debug log
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@bp.route('/<int:file_id>/segment', methods=['POST'])
def segment_with_medsam(file_id):
    """Apply MedSAM segmentation using the provided rectangle coordinates."""
    global global_current_image
    
    try:
        # Get rectangle coordinates from request
        data = request.get_json()
        box = data.get('box')  # [x1, y1, x2, y2]
        
        if not box or len(box) != 4:
            return jsonify({'error': 'Invalid box coordinates'}), 400
            
        # Get the current image
        if global_current_image is None:
            return jsonify({'error': 'No image loaded'}), 400
            
        # Apply MedSAM segmentation
        mask = medsam_service.segment_image(global_current_image, box)
        
        # Overlay the mask on the image
        result = medsam_service.overlay_mask(global_current_image, mask)
        
        # Update the current image
        global_current_image = result
        
        # Encode the result for display
        _, buf = cv2.imencode('.png', result)
        img_b64 = base64.b64encode(buf).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': img_b64
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/test-medsam')
def test_medsam():
    """Test page for MedSAM segmentation."""
    return render_template(
        'test_medsam.html'
    )

@bp.route('/test-medsam/segment', methods=['POST'])
def test_medsam_segment():
    """Test endpoint for MedSAM segmentation."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        # Get box coordinates from request
        box = request.form.get('box')
        if not box:
            return jsonify({'error': 'No box coordinates provided'}), 400
        
        # Parse box coordinates
        box = json.loads(box)
        if not isinstance(box, list) or len(box) != 4:
            return jsonify({'error': 'Invalid box coordinates'}), 400
        
        # Read image
        img = Image.open(file.stream)
        
        # Apply segmentation
        result = medsam_service.segment_image(img, box)
        
        # Convert result to base64 for display
        buffered = BytesIO()
        result.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{img_str}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/dicom-info/<int:file_id>')
def dicom_info(file_id):
    """Get metadata about a DICOM file, including number of slices."""
    file = Resource.query.get_or_404(file_id)
    
    if file.mime != 'application/dicom' and not file.path.lower().endswith('.dcm'):
        return jsonify({'error': 'Not a DICOM file'}), 400
        
    # figure out dataset folder
    base = current_app.config['UPLOAD_FOLDER']
    if file.dataset_id:
        base = os.path.join(base, str(file.dataset_id))
    path = os.path.join(base, file.path)
    
    try:
        print(f"Reading DICOM file: {path}")  # Debug log
        dcm = pydicom.dcmread(path, force=True)
        print(f"Successfully read DICOM file")  # Debug log
        
        if hasattr(dcm, 'pixel_array'):
            if len(dcm.pixel_array.shape) == 3:  # Multi-slice DICOM
                num_slices = dcm.pixel_array.shape[0]
            else:  # Single-slice DICOM
                num_slices = 1
        else:
            num_slices = 1
            
        return jsonify({
            'total_slices': num_slices,  # Changed from num_slices to total_slices to match frontend
            'rows': dcm.Rows if hasattr(dcm, 'Rows') else None,
            'columns': dcm.Columns if hasattr(dcm, 'Columns') else None,
            'modality': dcm.Modality if hasattr(dcm, 'Modality') else None,
            'study_date': str(dcm.StudyDate) if hasattr(dcm, 'StudyDate') else None,
            'patient_name': str(dcm.PatientName) if hasattr(dcm, 'PatientName') else None
        })
    except Exception as e:
        print(f"Error reading DICOM file {path}: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 500

@bp.route('/dataset-info/<int:ds_id>')
def dataset_info(ds_id):
    """Get information about the dataset's DICOM files, including whether they are multi-slice."""
    if not session.get('user_id'):
        return jsonify({'error': 'Not authenticated'}), 401

    from app.services.DatasetService import DatasetService
    ds = DatasetService.read_for_user(ds_id, session['user_id'])
    if not ds:
        return jsonify({'error': 'Dataset not found'}), 404

    files = FileService.getUserFiles(type='AImage', dataset_id=ds_id)
    if not files:
        return jsonify({'error': 'No files found in dataset'}), 400

    # Check for both .dcm files and files with DICOM mime type
    dicom_files = [f for f in files if f.mime == 'application/dicom' or f.path.lower().endswith('.dcm')]
    if not dicom_files:
        return jsonify({'error': 'No DICOM files in dataset'}), 400

    # Check the first DICOM file to determine if it's multi-slice
    base = current_app.config['UPLOAD_FOLDER']
    if ds.id:
        base = os.path.join(base, str(ds.id))
    
    try:
        first_dicom = dicom_files[0]
        path = os.path.join(base, first_dicom.path)
        
        # Log the path and check if file exists
        print(f"Attempting to read DICOM file at: {path}")
        if not os.path.exists(path):
            return jsonify({'error': f'DICOM file not found at path: {path}'}), 404
            
        try:
            # Try reading with force=True to handle missing DICOM header
            dcm = pydicom.dcmread(path, force=True)
            print(f"Successfully read DICOM file: {path}")
        except Exception as e:
            print(f"Error reading DICOM file {path}: {str(e)}")
            return jsonify({'error': f'Error reading DICOM file: {str(e)}'}), 500
        
        # For CT series, each file is a slice, so the total number of files is the number of slices
        is_multi_slice = len(dicom_files) > 1
        print(f"Number of DICOM files: {len(dicom_files)}")
        
        # Get additional DICOM metadata
        metadata = {
            'is_multi_slice': is_multi_slice,
            'total_files': len(files),
            'dicom_files': len(dicom_files),
            'first_file_slices': 1,  # Each file is one slice
            'total_slices': len(dicom_files),  # Total number of slices in the series
            'file_path': first_dicom.path,
            'modality': str(dcm.get('Modality', 'Unknown')),
            'rows': dcm.get('Rows', 'Unknown'),
            'columns': dcm.get('Columns', 'Unknown'),
            'bits_allocated': dcm.get('BitsAllocated', 'Unknown'),
            'samples_per_pixel': dcm.get('SamplesPerPixel', 'Unknown'),
            'warning': 'DICOM header was missing, file was read in forced mode'
        }
        
        print(f"DICOM metadata: {metadata}")
        return jsonify(metadata)
        
    except Exception as e:
        print(f"Error processing DICOM file: {str(e)}")
        return jsonify({'error': f'Error processing DICOM file: {str(e)}'}), 500

def extract_contours_from_dicom(dicom_path, method='adaptive', user_threshold=50):
    try:
        dcm = pydicom.dcmread(dicom_path, force=True)
        if not hasattr(dcm, 'pixel_array'):
            return []
        img = dcm.pixel_array
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        if method == 'adaptive':
            mask = cv2.adaptiveThreshold(
                img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 51, 2
            )
        elif method == 'canny':
            mask = cv2.Canny(img, 50, 150)
        elif method == 'manual':
            _, mask = cv2.threshold(img, user_threshold, 255, cv2.THRESH_BINARY)
        else:  # fallback to Otsu
            _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour_points = [c.squeeze().tolist() for c in contours if c.shape[0] >= 3]
        return contour_points
    except Exception as e:
        print(f"Error extracting contours: {e}")
        return []

@bp.route('/contours/<int:file_id>')
def get_contours(file_id):
    method = request.args.get('method', 'adaptive')
    try:
        user_threshold = int(request.args.get('threshold', 50))
    except Exception:
        user_threshold = 50
    file = Resource.query.get_or_404(file_id)
    base = current_app.config['UPLOAD_FOLDER']
    if file.dataset_id:
        base = os.path.join(base, str(file.dataset_id))
    path = os.path.join(base, file.path)
    contours = extract_contours_from_dicom(path, method=method, user_threshold=user_threshold)
    return jsonify({'contours': contours})

def extract_mask_from_dicom(dicom_path, method='adaptive', user_threshold=50):
    dcm = pydicom.dcmread(dicom_path, force=True)
    if not hasattr(dcm, 'pixel_array'):
        return None
    img = dcm.pixel_array
    img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    if method == 'adaptive':
        mask = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 2)
    elif method == 'canny':
        mask = cv2.Canny(img, 50, 150)
    elif method == 'manual':
        _, mask = cv2.threshold(img, user_threshold, 255, cv2.THRESH_BINARY)
    else:
        _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return (mask > 0).astype(np.uint8)

@bp.route('/mesh/<int:ds_id>')
def get_mesh(ds_id):
    method = request.args.get('method', 'adaptive')
    try:
        user_threshold = int(request.args.get('threshold', 50))
    except Exception:
        user_threshold = 50

    files = FileService.getUserFiles(type='AImage', dataset_id=ds_id)
    masks = []
    for f in files:
        base = current_app.config['UPLOAD_FOLDER']
        if f.dataset_id:
            base = os.path.join(base, str(f.dataset_id))
        path = os.path.join(base, f.path)
        mask = extract_mask_from_dicom(path, method, user_threshold)
        if mask is not None:
            masks.append(mask)
    if not masks:
        return jsonify({'error': 'No valid masks found'}), 400

    volume = np.stack(masks, axis=0)
    # Downsample to 64x64 for speed
    volume_small = resize(volume, (volume.shape[0], 64, 64), order=0, preserve_range=True, anti_aliasing=False).astype(volume.dtype)
    verts, faces, normals, values = measure.marching_cubes(volume_small, level=0.5)
    return jsonify({
        'vertices': verts.tolist(),
        'faces': faces.tolist()
    })