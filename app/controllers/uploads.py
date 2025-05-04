import base64
import os
import io

import cv2
import numpy as np
import pydicom
from flask import (
    Blueprint, current_app, render_template, send_from_directory,
    request, redirect, session, url_for, send_file, abort, flash
)
from werkzeug.utils import secure_filename

from app.models.Resource import Resource
from app.services.FileService import FileService
from app.services.DatasetService import DatasetService
from app.filters import DicomFilters, Thresholding, GMM, apply_segmentation

# ── global state & constants ───────────────────────────────────────────
FILTER_NAMES = [
    "Original", "CLAHE", "Gamma", "Gaussian", "Median",
    "Non-Local Means", "Threshold (Otsu)", "Threshold (Binary)",
    "GMM", "Segment"
]

global_original_image = None
global_current_image  = None
global_history        = []
global_processes      = []

bp = Blueprint("uploads", __name__)


def get_allowed_filters():
    blocking = {"Threshold (Otsu)", "Threshold (Binary)"}
    if global_processes and global_processes[-1] in blocking:
        return ["Original"]
    return FILTER_NAMES


def read_and_process(path, mime_type, dataset_id=None):
    # Determine correct folder (dataset subfolder if present)
    base_folder = current_app.config['UPLOAD_FOLDER']
    if dataset_id:
        base_folder = os.path.join(base_folder, str(dataset_id))
    full_path = os.path.join(base_folder, path)

    if mime_type == "application/dicom":
        dcm = pydicom.dcmread(full_path)
        arr = dcm.pixel_array
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        _, buf = cv2.imencode('.png', arr)
        return base64.b64encode(buf).decode('utf-8')

    img = cv2.imread(full_path)
    _, buf = cv2.imencode('.png', img)
    return base64.b64encode(buf).decode('utf-8')


# ── Image processing endpoints ─────────────────────────────────────────
@bp.route('/process/<int:file_id>')
def process(file_id):
    global global_original_image, global_current_image, global_history, global_processes
    file = Resource.query.get_or_404(file_id)

    # Build path including dataset folder if attached
    base_folder = current_app.config['UPLOAD_FOLDER']
    if file.dataset_id:
        base_folder = os.path.join(base_folder, str(file.dataset_id))
    img_path = os.path.join(base_folder, file.path)
    original = cv2.imread(img_path)

    if original is None:
        abort(404, description="Image file not found on disk")

    # Reset history if switching files
    if session.get('last_file') != file_id:
        global_original_image = original.copy()
        global_current_image  = original.copy()
        global_history.clear()
        global_processes.clear()
        session['last_file'] = file_id

    # Encode for display
    _, buf = cv2.imencode('.png', global_current_image)
    img_b64 = base64.b64encode(buf).decode('utf-8')
    allowed = get_allowed_filters()

    return render_template(
        'process.html',
        file=file,
        img=img_b64,
        filter_names=FILTER_NAMES,
        allowed_filters=allowed,
        processes=global_processes,
        files = FileService.getUserFiles(type="AImage", dataset_id=file.dataset_id),
        read_and_process=read_and_process
    )


@bp.route('/process/<int:file_id>/apply', methods=['POST'])
def apply_filter(file_id):
    global global_current_image, global_history, global_processes
    name = request.form.get('filter_name')
    if name not in get_allowed_filters():
        return redirect(url_for('uploads.process', file_id=file_id))

    global_history.append(global_current_image.copy())
    if name == "Original":
        global_current_image = global_original_image.copy()
    else:
        base = global_current_image
        fmap = DicomFilters.apply_filters(base)
        thr  = Thresholding(base)
        fmap["Threshold (Otsu)"]   = thr.apply_otsu_threshold()
        fmap["Threshold (Binary)"] = thr.apply_binary_threshold(127)
        gmm  = GMM(base); gmm.fit_gmm(n_components=2)
        fmap["GMM"]     = gmm.apply_gmm_threshold()
        fmap["Segment"] = apply_segmentation(base)
        global_current_image = fmap.get(name, base)

    global_processes.append(name)
    return redirect(url_for('uploads.process', file_id=file_id))


@bp.route('/process/<int:file_id>/undo')
def undo(file_id):
    global global_current_image, global_history, global_processes
    if global_history:
        global_current_image = global_history.pop()
        global_processes.pop()
    return redirect(url_for('uploads.process', file_id=file_id))


@bp.route('/process/<int:file_id>/reset')
def reset(file_id):
    global global_original_image, global_current_image, global_history, global_processes
    global_current_image = global_original_image.copy()
    global_history.clear()
    global_processes.clear()
    session.pop('last_file', None)
    return redirect(url_for('uploads.process', file_id=file_id))


@bp.route('/process/<int:file_id>/download')
def download_processed(file_id):
    global global_current_image
    if global_current_image is None:
        abort(404)
    success, buf = cv2.imencode('.png', global_current_image)
    if not success:
        abort(500)
    buf_io = io.BytesIO(buf.tobytes())
    buf_io.seek(0)
    return send_file(buf_io, mimetype='image/png', as_attachment=True, download_name=f'processed_{file_id}.png')


# ── Dataset & File Management ──────────────────────────────────────────
@bp.route('/')
def root():
    return redirect(url_for('uploads.datasets_index'))


@bp.route('/datasets', methods=['GET','POST'])
def datasets_index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    if request.method == 'POST':
        DatasetService.create(request.form, user_id)
        flash('Dataset created!', 'success')
        return redirect(url_for('uploads.datasets_index'))
    datasets = DatasetService.list_for_user(user_id)
    return render_template('uploads.html', datasets=datasets)


@bp.route('/datasets/<int:ds_id>/upload', methods=['POST'])
def upload_to_dataset(ds_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    ds = DatasetService.read_for_user(ds_id, user_id)
    if not ds:
        abort(403)
    files = request.files.getlist('files')
    for f in files:
        if f and f.filename:
            FileService.upload(f, type="AImage", dataset_id=ds_id)
    flash(f"Uploaded {len(files)} files.", 'success')
    return redirect(url_for('uploads.datasets_index'))


@bp.route('/datasets/<int:ds_id>/delete', methods=['POST'])
def delete_dataset(ds_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    if not DatasetService.delete_for_user(ds_id, user_id):
        abort(403)
    flash('Dataset deleted.', 'info')
    return redirect(url_for('uploads.datasets_index'))


@bp.route('/files/<int:file_id>/delete', methods=['POST'])
def delete_file(file_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    file = FileService.read(file_id)
    if not file or file.dataset_id is None or file.dataset.owner_id != user_id:
        abort(403)
    FileService.delete(file_id)
    flash('File deleted.', 'info')
    return redirect(url_for('uploads.datasets_index'))


@bp.route('/<int:ds_id>/<filename>')
def serve_dataset_file(ds_id, filename):
    """
    Serve the raw file from uploads/<dataset_id>/<filename>
    so URL is exactly /uploads/1/yourfile.png when blueprint is mounted at /uploads.
    """
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    ds = DatasetService.read_for_user(ds_id, session['user_id'])
    if not ds:
        abort(403)

    directory = os.path.join(current_app.config['UPLOAD_FOLDER'], str(ds_id))
    return send_from_directory(directory, filename)
