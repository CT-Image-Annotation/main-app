# app/controllers/uploads.py

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

from app.models.Resource import Resource
from app.services.FileService import FileService
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

def get_allowed_filters():
    """Disable all but 'Original' after a threshold operation."""
    blocking = {"Threshold (Otsu)", "Threshold (Binary)"}
    if global_processes and global_processes[-1] in blocking:
        return ["Original"]
    return FILTER_NAMES

bp = Blueprint("uploads", __name__)

def read_and_process(path, mime_type):
    """Load image or DICOM, return a base64 PNG for the upload list."""
    full = os.path.join(current_app.config['UPLOAD_FOLDER'], path)

    if mime_type == "application/dicom":
        dcm = pydicom.dcmread(full)
        arr = dcm.pixel_array
        arr = cv2.normalize(arr, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        _, buf = cv2.imencode('.png', arr)
        return base64.b64encode(buf).decode('utf-8')

    img = cv2.imread(full)
    _, buf = cv2.imencode('.png', img)
    return base64.b64encode(buf).decode('utf-8')

@bp.route('/process/<int:file_id>')
def process(file_id):
    global global_original_image, global_current_image, global_history, global_processes

    # load the raw original on first visit
    file = Resource.query.get_or_404(file_id)
    img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.path)
    original = cv2.imread(img_path)

    if session.get('last_file') != file_id:
        global_original_image = original.copy()
        global_current_image  = original.copy()
        global_history.clear()
        global_processes.clear()
        session['last_file'] = file_id

    # encode current for display
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
        files = FileService.getUserFiles()
    )

@bp.route('/process/<int:file_id>/apply', methods=['POST'])
def apply_filter(file_id):
    global global_current_image, global_history, global_processes

    name = request.form.get('filter_name')
    if name not in get_allowed_filters():
        return redirect(url_for('uploads.process', file_id=file_id))

    # save for undo
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
    return send_file(
        buf_io,
        mimetype='image/png',
        as_attachment=True,
        download_name=f'processed_{file_id}.png'
    )

@bp.route('/', methods=['GET', 'POST'])
def upload():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        f = request.files['file']
        if f.filename == '':
            flash('No selected file')
            return redirect(request.url)

        FileService.upload(f, type="AImage")
        return redirect(request.url)

    files = FileService.getUserFiles(type="AImage")#Resource.query.filter_by(type="AImage")
    imgs = { f.id: read_and_process(f.path, f.mime) for f in files }
    return render_template("uploads.html", files=files, imgs=imgs)

@bp.route('/<path:path>')
def download(path):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], path)