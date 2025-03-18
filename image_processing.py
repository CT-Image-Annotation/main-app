import cv2
import numpy as np
import base64
from config import ALLOWED_EXTENSIONS

def allowed_file(filename):
    """Return True if the filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file_bytes):
    """Processes the image: convert to grayscale, apply threshold, and return a base64 string."""
    npimg = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if img is None:
        return None
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    success, buffer = cv2.imencode('.png', thresh)
    if not success:
        return None

    return base64.b64encode(buffer).decode('utf-8')
