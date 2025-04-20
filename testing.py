from flask import Flask, request, render_template_string, redirect, url_for, send_file
import os
import cv2
import numpy as np
import base64
import io
import pydicom

# Import functions/classes from your attached modules.
from threshold import Thresholding
from gmm import GMM
from dicom_filters import DicomFilters

# Import the ImageOptimizer class from your image_processing module.
from image_processing import ImageOptimizer

app = Flask(__name__)

# Configure an upload folder.
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions (including DICOM).
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'dcm'}

# Define the available filters.
FILTER_NAMES = [
    "Original", "CLAHE", "Gamma", "Gaussian", "Median",
    "Non-Local Means", "Threshold (Otsu)", "Threshold (Binary)", "GMM", "Segment"
]

# ------------------
# Global State
# ------------------
global_original_image = None   # The uploaded (and optimized) image.
global_current_image = None    # The current image with filters/drawings applied.
global_history = []            # History of previous versions (for undo)
global_processes = []          # List of applied process names (in order)

# ------------------
# Utility Functions
# ------------------
def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_image_to_base64(img):
    """Encode a cv2 image to a PNG base64 string."""
    success, buffer = cv2.imencode('.png', img)
    if success:
        return base64.b64encode(buffer).decode('utf-8')
    return None

def apply_segmentation(image):
    """
    Apply k-means–based segmentation and return a segmented BGR image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    pixels = blurred.reshape(-1, 1).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 100, 0.2)
    k = 4  # number of clusters
    ret, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = np.sort(centers, axis=0)
    centers = np.uint8(centers)
    segmented = centers[labels.flatten()]
    segmented = segmented.reshape(gray.shape)
    segmented = cv2.adaptiveThreshold(segmented, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 11, 2)
    segmented = cv2.cvtColor(segmented, cv2.COLOR_GRAY2BGR)
    return segmented

def get_filters_for_image(img):
    """Compute available filters for the given image."""
    filters = DicomFilters.apply_filters(img)
    thresh_obj = Thresholding(img)
    filters["Threshold (Otsu)"] = thresh_obj.apply_otsu_threshold()
    filters["Threshold (Binary)"] = thresh_obj.apply_binary_threshold(127)
    gmm_obj = GMM(img)
    gmm_obj.fit_gmm(n_components=2)
    filters["GMM"] = gmm_obj.apply_gmm_threshold()
    filters["Segment"] = apply_segmentation(img)
    return filters

def apply_filter_to_image(img, filter_name):
    """
    Apply the requested filter on the given image.
    For "Original", reset to the original uploaded image.
    """
    global global_original_image
    if filter_name == "Original":
        return global_original_image.copy()
    filters = get_filters_for_image(img)
    return filters.get(filter_name, img)

def get_allowed_filters():
    """
    Returns the list of filter names allowed to be applied at this moment.
    If the last applied process is a threshold operation (Threshold (Otsu)
    or Threshold (Binary)), only "Original" is allowed; otherwise, all filters
    in FILTER_NAMES are allowed.
    """
    blocking_filters = {"Threshold (Otsu)", "Threshold (Binary)"}
    if global_processes and global_processes[-1] in blocking_filters:
        return ["Original"]
    else:
        return FILTER_NAMES


# ------------------
# Routes
# ------------------

# Upload Page – remains unchanged.
@app.route('/')
def index():
    return render_template_string(f'''
    <!doctype html>
    <html>
      <head>
        <title>Upload an Image for Processing</title>
        <style>
          body {{
              font-family: Helvetica, sans-serif;
              text-align: center;
              background: #f4f4f4;
              margin: 0;
              padding: 20px;
          }}
          .container {{
              max-width: 800px;
              margin: 0 auto;
              background: #fff;
              padding: 20px;
              border-radius: 8px;
              box-shadow: 0 0 10px rgba(0,0,0,0.1);
          }}
          button, input[type=submit] {{
              font-family: Helvetica, sans-serif;
              padding: 10px 20px;
              margin: 10px;
              border: none;
              background: #007bff;
              color: #fff;
              border-radius: 4px;
              cursor: pointer;
          }}
          button:hover, input[type=submit]:hover {{
              background: #0056b3;
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Upload an Image</h1>
          <form method="POST" action="/upload" enctype="multipart/form-data">
            <input type="file" name="file">
            <input type="submit" value="Upload">
          </form>
          <p>Allowed formats: png, jpg, jpeg, gif, dcm (DICOM)</p>
          <a href="/download" class="button">Download Image</a>
        </div>
      </body>
    </html>
    ''')

# Upload Endpoint: process file, optimize image, and reset globals.
@app.route('/upload', methods=["POST"])
def upload():
    global global_original_image, global_current_image, global_history, global_processes
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        file_bytes = file.read()
        file_size = len(file_bytes)
        optimizer = ImageOptimizer()
        if ext == "dcm":
            try:
                dcm = pydicom.dcmread(io.BytesIO(file_bytes))
                img = dcm.pixel_array
            except Exception as e:
                return f'Error processing DICOM image: {str(e)}'
            img = img.astype(np.float32)
            if img.max() - img.min() > 0:
                img = (img - img.min()) / (img.max() - img.min()) * 255
            img = img.astype(np.uint8)
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            npimg = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
            if img is None:
                return 'Error processing image'
        height, width = img.shape[:2]
        if width > 3840 or height > 2160:
            img = optimizer.resize_image(img, max_width=3840, max_height=2160)
        if file_size > (10 * 1024 * 1024):
            img = optimizer.compress_image(img, quality=85)
        global_original_image = img.copy()
        global_current_image = img.copy()
        global_history = []
        global_processes = []
        return redirect(url_for("workspace"))
    return 'Invalid file type.'

# Workspace: the main interactive screen.
@app.route('/workspace')
def workspace():
    global global_current_image, global_processes
    if global_current_image is None:
        return redirect(url_for("index"))
    allowed_filters = get_allowed_filters()
    encoded_img = encode_image_to_base64(global_current_image)
    current_process = global_processes[-1] if global_processes else "None"
    return render_template_string(f'''
    <!doctype html>
    <html>
      <head>
        <title>Image Workspace</title>
        <style>
          body {{
              font-family: Helvetica, sans-serif;
              background: #f4f4f4;
              margin: 0;
              padding: 20px;
          }}
          .container {{
              max-width: 800px;
              margin: 0 auto;
              background: #fff;
              padding: 20px;
              border-radius: 8px;
              box-shadow: 0 0 10px rgba(0,0,0,0.1);
          }}
          .header {{
              text-align: center;
              margin-bottom: 10px;
          }}
          .workspace {{
              display: flex;
          }}
          .filters {{
              width: 30%;
              display: grid;
              grid-template-columns: 1fr 1fr;
              grid-gap: 10px;
          }}
          .filters form {{
              margin: 0;
          }}
          .filters button {{
              width: 100%;
              padding: 10px;
              font-size: 14px;
          }}
          .image-container {{
              width: 70%;
              text-align: center;
          }}
          .process-log {{
              margin-top: 20px;
              text-align: left;
              max-width: 800px;
              margin-left: auto;
              margin-right: auto;
          }}
          .button {{
              padding: 10px 20px;
              background: #007bff;
              color: #fff;
              text-decoration: none;
              border-radius: 4px;
              margin: 5px;
          }}
        </style>
      </head>
      <body>
        <div class="header">
          <a href="/" class="button">Main Menu</a>
          <a href="/download" class="button">Download Image</a>
          <a href="/undo" class="button">Undo</a>
          <a href="/edit" class="button">Drawing</a>
        </div>
        <div class="workspace">
          <div class="filters">
            {{% for name in filter_names %}}
              <form action="/apply_filter" method="get">
                <input type="hidden" name="name" value="{{{{ name }}}}">
                <button type="submit" {{% if name not in allowed_filters %}}disabled{{% endif %}}>{{{{ name }}}}</button>
              </form>
            {{% endfor %}}
          </div>
          <div class="image-container">
            <img src="data:image/png;base64,{{{{ encoded_img }}}}" style="max-width: 100%;">
            <div>
              <p><strong>Current Process:</strong> {{{{ current_process }}}}</p>
            </div>
          </div>
        </div>
        <div class="process-log">
          <h3>Process History:</h3>
          <ul>
            {{% for process in processes %}}
              <li>{{{{ process }}}}</li>
            {{% endfor %}}
          </ul>
        </div>
      </body>
    </html>
    ''', encoded_img=encoded_img, filter_names=FILTER_NAMES, allowed_filters=allowed_filters,
         current_process=current_process, processes=global_processes)

# Apply a filter and stack it on the current image.
@app.route('/apply_filter')
def apply_filter_route():
    global global_current_image, global_original_image, global_history, global_processes
    if global_current_image is None:
        return redirect(url_for("index"))
    filter_name = request.args.get("name")
    allowed_filters = get_allowed_filters()
    if filter_name not in allowed_filters:
        # Block disallowed filter application.
        return redirect(url_for("workspace"))
    global_history.append(global_current_image.copy())
    if filter_name == "Original":
        global_current_image = global_original_image.copy()
        global_processes.append("Reset to Original")
    else:
        new_img = apply_filter_to_image(global_current_image, filter_name)
        global_current_image = new_img
        global_processes.append(filter_name)
    return redirect(url_for("workspace"))

# Undo the last change.
@app.route('/undo')
def undo():
    global global_current_image, global_history, global_processes
    if global_history:
        global_current_image = global_history.pop()
        if global_processes:
            global_processes.pop()
    return redirect(url_for("workspace"))

# Drawing/Editing Interface.
@app.route('/edit')
def edit():
    global global_current_image
    if global_current_image is None:
        return redirect(url_for("index"))
    encoded_img = encode_image_to_base64(global_current_image)
    return render_template_string(f'''
    <!doctype html>
    <html>
      <head>
        <title>Edit Image (Draw/Eraser)</title>
        <style>
          body {{
              font-family: Helvetica, sans-serif;
              text-align: center;
              background: #f4f4f4;
              margin: 0;
              padding: 20px;
          }}
          .container {{
              max-width: 800px;
              margin: 0 auto;
              background: #fff;
              padding: 20px;
              border-radius: 8px;
              box-shadow: 0 0 10px rgba(0,0,0,0.1);
          }}
          #canvasContainer {{
              position: relative;
              margin: 0 auto;
              border: 1px solid #ccc;
          }}
          #backgroundCanvas {{
              display: block;
          }}
          #drawingCanvas {{
              position: absolute;
              top: 0;
              left: 0;
          }}
          .header {{
              text-align: center;
              margin-bottom: 10px;
          }}
          .button {{
              padding: 10px 20px;
              background: #007bff;
              color: #fff;
              text-decoration: none;
              border-radius: 4px;
              margin: 5px;
          }}
        </style>
      </head>
      <body>
        <div class="header">
          <a href="/workspace" class="button">Back to Workspace</a>
          <a href="/download" class="button">Download Image</a>
        </div>
        <div class="container">
          <h1>Edit Image (Draw/Eraser)</h1>
          <div id="canvasContainer"></div>
          <br>
          <button onclick="toggleEraser()">Toggle Draw/Eraser</button>
          <button onclick="clearCanvas()">Reset Drawing</button>
          <button onclick="saveDrawing()">Save Drawing</button>
        </div>
        <form id="drawingForm" action="/save_drawing" method="post">
          <input type="hidden" name="imgData" id="imgData">
        </form>
        <script>
          var eraser = false;
          var drawing = false;
          var container = document.getElementById('canvasContainer');
          var bgCanvas = document.createElement('canvas');
          bgCanvas.id = 'backgroundCanvas';
          var drawCanvas = document.createElement('canvas');
          drawCanvas.id = 'drawingCanvas';
          container.appendChild(bgCanvas);
          container.appendChild(drawCanvas);
          
          var bgCtx = bgCanvas.getContext('2d');
          var drawCtx = drawCanvas.getContext('2d');
          var lastX, lastY;
          var img = new Image();
          img.onload = function() {{
              var scale = 1;
              if (img.width > 600) {{
                  scale = 600 / img.width;
              }}
              bgCanvas.width = drawCanvas.width = img.width * scale;
              bgCanvas.height = drawCanvas.height = img.height * scale;
              container.style.width = (img.width * scale) + 'px';
              bgCtx.drawImage(img, 0, 0, bgCanvas.width, bgCanvas.height);
          }};
          img.src = "data:image/png;base64,{{{{ encoded_img }}}}";
          
          drawCanvas.addEventListener('mousedown', function(e) {{
              drawing = true;
              var rect = drawCanvas.getBoundingClientRect();
              lastX = e.clientX - rect.left;
              lastY = e.clientY - rect.top;
          }});
          drawCanvas.addEventListener('mousemove', function(e) {{
              if (!drawing) return;
              var rect = drawCanvas.getBoundingClientRect();
              var x = e.clientX - rect.left;
              var y = e.clientY - rect.top;
              drawCtx.lineWidth = 3;
              drawCtx.lineCap = "round";
              if (eraser) {{
                  drawCtx.clearRect(x - 10, y - 10, 20, 20);
              }} else {{
                  drawCtx.strokeStyle = "red";
                  drawCtx.beginPath();
                  drawCtx.moveTo(lastX, lastY);
                  drawCtx.lineTo(x, y);
                  drawCtx.stroke();
              }}
              lastX = x;
              lastY = y;
          }});
          drawCanvas.addEventListener('mouseup', function(e) {{
              drawing = false;
          }});
          drawCanvas.addEventListener('mouseout', function(e) {{
              drawing = false;
          }});
          
          function toggleEraser() {{
              eraser = !eraser;
              alert(eraser ? "Eraser mode enabled" : "Draw mode enabled");
          }}
          
          function clearCanvas() {{
              drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
          }}
          
          function saveDrawing() {{
              var composite = document.createElement('canvas');
              composite.width = bgCanvas.width;
              composite.height = bgCanvas.height;
              var compCtx = composite.getContext('2d');
              compCtx.drawImage(bgCanvas, 0, 0);
              compCtx.drawImage(drawCanvas, 0, 0);
              var dataURL = composite.toDataURL();
              document.getElementById('imgData').value = dataURL;
              document.getElementById('drawingForm').submit();
          }}
        </script>
      </body>
    </html>
    ''', encoded_img=encoded_img)

# Save the drawing and update the current image.
@app.route('/save_drawing', methods=['POST'])
def save_drawing():
    global global_current_image, global_history, global_processes
    imgData = request.form.get('imgData')
    if not imgData:
        return redirect(url_for("edit"))
    header, encoded = imgData.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    npimg = np.frombuffer(img_bytes, np.uint8)
    new_img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    global_history.append(global_current_image.copy())
    global_processes.append("Drawing")
    global_current_image = new_img
    return redirect(url_for("workspace"))

# Download the current manipulated image.
@app.route('/download')
def download():
    global global_current_image
    if global_current_image is None:
        return redirect(url_for("index"))
    success, buffer = cv2.imencode('.png', global_current_image)
    if not success:
        return 'Error encoding image for download.'
    io_buf = io.BytesIO(buffer.tobytes())
    io_buf.seek(0)
    return send_file(io_buf, mimetype='image/png', as_attachment=True, download_name='manipulated_image.png')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True, use_reloader=False)
