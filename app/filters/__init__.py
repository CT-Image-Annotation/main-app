import cv2
import numpy as np

from .dicom_filters import DicomFilters
from .threshold     import Thresholding
from .gmm           import GMM

# k‑means–based segmentation
def apply_segmentation(image):
    gray    = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape)==3 else image
    blurred = cv2.GaussianBlur(gray, (5,5), 0)
    pixels  = blurred.reshape(-1,1).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 100, 0.2)
    k = 4
    _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = np.sort(centers, axis=0).astype(np.uint8)
    seg = centers[labels.flatten()].reshape(gray.shape)
    thresh = cv2.adaptiveThreshold(
        seg, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
