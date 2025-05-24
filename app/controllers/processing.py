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
from scipy.interpolate import interp1d

from app.models.Resource import Resource
from app.services.FileService import FileService
from app.services.medsam_service import MedSAMService
from app.services.ContourInterpolationService import ContourInterpolationService
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

@bp.route('/contours/<int:file_id>')
def get_contours(file_id):
    """Get contours for a specific slice using the selected method."""
    method = request.args.get('method', 'adaptive')
    threshold = int(request.args.get('threshold', 50))
    
    # Get the file
    file = Resource.query.get_or_404(file_id)
    if not file:
        return jsonify({'error': 'File not found'}), 404
    
    # Read the DICOM file
    base_folder = current_app.config['UPLOAD_FOLDER']
    if file.dataset_id:
        base_folder = os.path.join(base_folder, str(file.dataset_id))
    dicom_path = os.path.join(base_folder, file.path)
    dicom = pydicom.dcmread(dicom_path)
    image = dicom.pixel_array
    
    # Normalize image
    image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
    image = image.astype(np.uint8)
    
    # Apply selected contour method
    if method == 'adaptive':
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
    elif method == 'canny':
        binary = cv2.Canny(image, threshold, threshold * 2)
    elif method == 'manual':
        _, binary = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
    elif method == 'otsu':
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        return jsonify({'error': 'Invalid contour method'}), 400
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Convert contours to list format
    contour_list = []
    for contour in contours:
        if len(contour) > 2:  # Only include contours with more than 2 points
            contour_list.append(contour.reshape(-1, 2).tolist())
    
    return jsonify({'contours': contour_list})

@bp.route('/interpolate-contours', methods=['POST'])
def interpolate_contours_api():
    """Interpolate contours between two slices."""
    data = request.get_json()
    if not data or 'contour1' not in data or 'contour2' not in data:
        return jsonify({'error': 'Missing contour data'}), 400
    
    contour1 = np.array(data['contour1'])
    contour2 = np.array(data['contour2'])
    num_slices = int(data.get('num_slices', 1))
    
    try:
        interpolated = ContourInterpolationService.interpolate_between_slices(
            source_slice=0,
            target_slice=1,
            contours={0: contour1, 1: contour2},
            num_intermediate=num_slices
        )
        
        # Convert numpy arrays to lists for JSON serialization
        result = {
            'interpolated': [
                contour.tolist() for contour in interpolated.values()
            ]
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/mesh/<int:ds_id>')
def get_mesh(ds_id):
    """Generate a 3D mesh from contours."""
    method = request.args.get('method', 'adaptive')
    threshold = int(request.args.get('threshold', 50))
    
    # Get all files in the dataset
    files = FileService.getUserFiles(type='AImage', dataset_id=ds_id)
    if not files:
        return jsonify({'error': 'No files found in dataset'}), 404
    
    # Get contours for all slices
    all_contours = []
    for file in files:
        base_folder = current_app.config['UPLOAD_FOLDER']
        if file.dataset_id:
            base_folder = os.path.join(base_folder, str(file.dataset_id))
        dicom_path = os.path.join(base_folder, file.path)
        
        # Get contours for this slice
        contours = extract_contours_from_dicom(dicom_path, method, threshold)
        if contours:
            all_contours.append(contours[0])  # Take the largest contour
    
    if not all_contours:
        return jsonify({'error': 'No contours found'}), 404
    
    # Create volume from contours
    volume = create_volume_from_contours(all_contours, len(all_contours), (512, 512))
    
    # Generate mesh using marching cubes
    vertices, faces, normals, _ = measure.marching_cubes(volume, level=0.5)
    
    return jsonify({
        'vertices': vertices.tolist(),
        'faces': faces.tolist(),
        'normals': normals.tolist()
    })

@bp.route('/volume/<int:ds_id>')
def get_volume(ds_id):
    """Reconstruct a 3D volume from contours."""
    method = request.args.get('method', 'adaptive')
    threshold = int(request.args.get('threshold', 50))
    num_interp = int(request.args.get('num_interp', 0))
    smooth = request.args.get('smooth', 'false').lower() == 'true'
    smooth_factor = float(request.args.get('smooth_factor', 1.0))
    fill_holes = request.args.get('fill_holes', 'false').lower() == 'true'
    
    # Get all files in the dataset
    files = FileService.getUserFiles(type='AImage', dataset_id=ds_id)
    if not files:
        return jsonify({'error': 'No files found in dataset'}), 404
    
    # Get contours for all slices
    all_contours = []
    for file in files:
        base_folder = current_app.config['UPLOAD_FOLDER']
        if file.dataset_id:
            base_folder = os.path.join(base_folder, str(file.dataset_id))
        dicom_path = os.path.join(base_folder, file.path)
        
        # Get contours for this slice
        contours = extract_contours_from_dicom(dicom_path, method, threshold)
        if contours:
            all_contours.append(contours[0])  # Take the largest contour
    
    if not all_contours:
        return jsonify({'error': 'No contours found'}), 404
    
    # Create volume from contours
    volume = create_volume_from_contours(all_contours, len(all_contours), (512, 512))
    
    # Process volume based on options
    volume = process_volume(volume, {
        'smooth': smooth,
        'smooth_factor': smooth_factor,
        'fill_holes': fill_holes
    })
    
    # Generate mesh using marching cubes
    vertices, faces, normals, _ = measure.marching_cubes(volume, level=0.5)
    
    return jsonify({
        'vertices': vertices.tolist(),
        'faces': faces.tolist(),
        'normals': normals.tolist(),
        'volume_shape': volume.shape
    })

@bp.route('/export-volume/<int:ds_id>')
def export_volume(ds_id):
    """Export the reconstructed volume as STL."""
    method = request.args.get('method', 'adaptive')
    threshold = int(request.args.get('threshold', 50))
    num_interp = int(request.args.get('num_interp', 0))
    smooth = request.args.get('smooth', 'false').lower() == 'true'
    smooth_factor = float(request.args.get('smooth_factor', 1.0))
    fill_holes = request.args.get('fill_holes', 'false').lower() == 'true'
    
    # Get volume data
    response = get_volume(ds_id)
    if response.status_code != 200:
        return response
    
    data = response.get_json()
    vertices = np.array(data['vertices'])
    faces = np.array(data['faces'])
    
    # Create STL file
    from stl import mesh
    volume_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, face in enumerate(faces):
        for j in range(3):
            volume_mesh.vectors[i][j] = vertices[face[j]]
    
    # Save to BytesIO
    stl_file = BytesIO()
    volume_mesh.save(stl_file)
    stl_file.seek(0)
    
    return send_file(
        stl_file,
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=f'volume_{ds_id}.stl'
    )

# Helper functions
def extract_contours_from_dicom(dicom_path, method='adaptive', user_threshold=50):
    """Extract contours from a DICOM file using the specified method."""
    dicom = pydicom.dcmread(dicom_path)
    image = dicom.pixel_array
    
    # Normalize image
    image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
    image = image.astype(np.uint8)
    
    # Apply selected contour method
    if method == 'adaptive':
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
    elif method == 'canny':
        binary = cv2.Canny(image, user_threshold, user_threshold * 2)
    elif method == 'manual':
        _, binary = cv2.threshold(image, user_threshold, 255, cv2.THRESH_BINARY)
    elif method == 'otsu':
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        return []
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Sort contours by area (largest first)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    return contours

def create_volume_from_contours(contours_list, num_slices, image_shape):
    """Create a 3D volume from a list of contours."""
    volume = np.zeros((num_slices, *image_shape), dtype=np.uint8)
    
    for i, contour in enumerate(contours_list):
        if contour is not None and len(contour) > 2:
            mask = np.zeros(image_shape, dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            volume[i] = mask
    
    return volume

def process_volume(volume, options):
    """Process the volume based on the given options."""
    if options.get('smooth', False):
        from scipy.ndimage import gaussian_filter
        volume = gaussian_filter(volume, sigma=options.get('smooth_factor', 1.0))
    
    if options.get('fill_holes', False):
        from scipy.ndimage import binary_fill_holes
        volume = binary_fill_holes(volume)
    
    return volume