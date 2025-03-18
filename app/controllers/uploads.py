import base64
from logging import Logger
import os
import cv2
from flask import Blueprint, current_app, render_template, send_from_directory, make_response,request, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from app import db
from app.models.ImageModel import ImageModel
from app.services.FileService import FileService
bp = Blueprint("uploads", __name__)

def read_and_process(name):
        img = cv2.imread(os.path.join(current_app.config['UPLOAD_FOLDER'], name))
       
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
        
        FileService.upload(file)
        
        return redirect(request.url)

    files = ImageModel.query.all()
    
    imgs = { file.id : read_and_process(file.path) for file in files}
    
    return render_template("uploads.html", files=files, imgs = imgs)

@bp.route('/<name>')
def download(name):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)