import os
import cv2
import pydicom
import numpy as np
import pandas as pd

class DicomFilters:
    @staticmethod
    def apply_filters(img):
        base_img = ((img - np.min(img)) / (np.max(img) - np.min(img)) * 255).astype(np.uint8)
        if len(base_img.shape) == 3 and base_img.shape[2] == 3:
            gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = base_img

        return {
            "Original": base_img,
            "CLAHE": cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray),
            "Gamma": cv2.LUT(base_img, np.array([(i / 255.0) ** (1.2) * 255 for i in range(256)]).astype("uint8")),
            "Gaussian": cv2.GaussianBlur(base_img, (5, 5), 0),
            "Median": cv2.medianBlur(base_img, 5),
            "Non-Local Means": cv2.fastNlMeansDenoising(base_img, None, 10, 7, 21)
        }