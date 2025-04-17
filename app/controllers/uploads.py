import base64
import os
import cv2
import numpy as np
from flask import Blueprint, current_app, render_template, send_from_directory,request, redirect, flash
from app.models.Resource import Resource
from app.services.FileService import FileService
import pydicom
bp = Blueprint("uploads", __name__)

def read_and_process(path, type):
        if type == "application/dicom":
            dcm = pydicom.dcmread(os.path.join(current_app.config['UPLOAD_FOLDER'], path))
            pixel_array = dcm.pixel_array
            pixel_array = cv2.normalize(pixel_array, None, 0, 255, cv2.NORM_MINMAX)
            pixel_array = np.uint8(pixel_array)  # Convert to uint8

            # Encode as PNG
            _, buffer = cv2.imencode('.png', pixel_array)
            return base64.b64encode(buffer).decode('utf-8')
        
        img = cv2.imread(os.path.join(current_app.config['UPLOAD_FOLDER'], path))
    
        # random processing
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        img = thresh

        _, buffer = cv2.imencode('.png', img)
        res = base64.b64encode(buffer).decode('utf-8')
        return res

@bp.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        FileService.upload(file, type="AImage")
        
        return redirect(request.url)

    files = Resource.query.filter_by(type="AImage")
    
    imgs = { file.id : read_and_process(file.path, file.mime) for file in files}
    
    return render_template("uploads.html", files=files, imgs = imgs)

@bp.route('/<path:path>')
def download(path):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], path)