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

class ImageOptimizer:
    def __init__(self):
        pass

    def resize_image(self, image, max_width, max_height):
        """
        Resize the image while maintaining aspect ratio if the width or height exceeds the given maximums.
        """
        height, width = image.shape[:2]
        # Compute scale factors for width and height.
        scale_w = max_width / width if width > max_width else 1
        scale_h = max_height / height if height > max_height else 1
        # Use the smaller scale factor to maintain aspect ratio.
        scale = min(scale_w, scale_h)
        if scale < 1:
            new_width = int(width * scale)
            new_height = int(height * scale)
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            return resized
        return image

    def compress_image(self, image, quality):
        """
        Compress the image by encoding it as a JPEG with the given quality, and then decoding it back.
        This effectively reduces file size.
        """
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, encoded_image = cv2.imencode('.jpg', image, encode_param)
        if success:
            decompressed = cv2.imdecode(encoded_image, cv2.IMREAD_COLOR)
            return decompressed
        return image