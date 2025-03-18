from flask import Blueprint, request, render_template_string
from image_processing import allowed_file, process_image
from config import UPLOAD_FOLDER

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template_string('''
    <!doctype html>
    <html>
      <head>
        <title>Upload an Image for Thresholding</title>
      </head>
      <body>
        <h1>Upload an Image to Apply OpenCV Thresholding</h1>
        <form method="POST" action="/upload" enctype="multipart/form-data">
          <input type="file" name="file">
          <input type="submit" value="Upload">
        </form>
      </body>
    </html>
    ''')

@main.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    
    if file and allowed_file(file.filename):
        file_bytes = file.read()
        encoded_image = process_image(file_bytes)
        if encoded_image is None:
            return 'Error processing image'
        
        return render_template_string('''
        <!doctype html>
        <html>
          <head>
            <title>Thresholded Image</title>
          </head>
          <body>
            <h1>Your Thresholded Image</h1>
            <img src="data:image/png;base64,{{ image_data }}" alt="Thresholded Image">
            <br><br>
            <a href="/">Upload another image</a>
          </body>
        </html>
        ''', image_data=encoded_image)
    
    return 'Invalid file type. Please upload an image file.'
