import os
import cv2
import pydicom
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from sklearn.mixture import GaussianMixture

class Thresholding:
    def __init__(self, image):
        self.image = image

    def apply_otsu_threshold(self):
        """
        Apply Otsu's thresholding method on the image.
        """
        if len(self.image.shape) == 3:  # If the image is colored, convert to grayscale
            gray_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        else:
            gray_image = self.image

        # Otsu's thresholding
        _, thresholded_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresholded_image

    def apply_binary_threshold(self, threshold_value):
        """
        Apply simple binary thresholding.
        """
        if len(self.image.shape) == 3:
            gray_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        else:
            gray_image = self.image

        _, thresholded_image = cv2.threshold(gray_image, threshold_value, 255, cv2.THRESH_BINARY)
        return thresholded_image
