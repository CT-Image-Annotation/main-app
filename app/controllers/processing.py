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
    key = f'batch_{ds_id}_processes'
    procs = session.get(key, [])
    procs.append(name)
    session[key] = procs
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
    file = Resource.query.get_or_404(file_id)

    # figure out dataset folder
    base = current_app.config['UPLOAD_FOLDER']
    if file.dataset_id:
        base = os.path.join(base, str(file.dataset_id))
    path = os.path.join(base, file.path)

    # load raw
    raw = cv2.imread(path) if file.mime != 'application/dicom' else None
    if file.mime == 'application/dicom':
        dcm = pydicom.dcmread(path)
        arr = dcm.pixel_array
        raw = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    if raw is None:
        abort(404, "File not found")

    # replay batch filters
    key   = f'batch_{file.dataset_id}_processes'
    procs = session.get(key, [])
    img   = raw.copy()
    for name in procs:
        if name == 'Original':
            img = raw.copy()
        else:
            fmap = DicomFilters.apply_filters(img)
            thr  = Thresholding(img)
            fmap['Threshold (Otsu)']   = thr.apply_otsu_threshold()
            fmap['Threshold (Binary)'] = thr.apply_binary_threshold(127)
            gmm  = GMM(img); gmm.fit_gmm(n_components=2)
            fmap['GMM']     = gmm.apply_gmm_threshold()
            fmap['Segment'] = apply_segmentation(img)
            img = fmap.get(name, img)

    # send out as PNG
    _, buf = cv2.imencode('.png', img)
    bio = BytesIO(buf.tobytes())
    bio.seek(0)
    return send_file(bio, mimetype='image/png')


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