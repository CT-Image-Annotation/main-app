import base64
import os
import cv2
from flask import Blueprint, current_app, render_template, send_from_directory,request, redirect, flash
from app.models.Resource import Resource
from app.services.FileService import FileService
bp = Blueprint("uploads", __name__)

def read_and_process(name):
        try:
            img = cv2.imread(os.path.join(current_app.config['UPLOAD_FOLDER'], name))
        
            # random processing
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            img = thresh

            _, buffer = cv2.imencode('.png', img)
            res = base64.b64encode(buffer).decode('utf-8')
            return res
        except:
             return base64.b64encode(b'0').decode('utf-8')

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

    files = Resource.query.all()
    
    imgs = { file.id : read_and_process(file.path) for file in files}
    
    return render_template("uploads.html", files=files, imgs = imgs)

@bp.route('/<name>')
def download(name):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], name)