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
    imgs = { file.id : base64.b64encode(cv2.imread(os.path.join(current_app.config['UPLOAD_FOLDER'], file.path))).decode('utf-8') for file in files}
    
    return render_template("uploads.html", files=files, imgs = imgs)

@bp.route('/<name>')
def download(name):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)