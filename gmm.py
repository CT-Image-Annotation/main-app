import os
import cv2
import pydicom
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from sklearn.mixture import GaussianMixture
class GMM:
    def __init__(self, image):
        self.image = image
        self.gmm = None

    def fit_gmm(self, n_components=2):
        """
        Fit a Gaussian Mixture Model to the image (grayscale).
        """
        if len(self.image.shape) == 3:
            gray_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        else:
            gray_image = self.image

        pixels = gray_image.flatten().reshape(-1, 1)
        
        self.gmm = GaussianMixture(n_components=n_components)
        self.gmm.fit(pixels)

    def apply_gmm_threshold(self):
        """
        Apply GMM-based thresholding using the fitted model.
        """
        if self.gmm is None:
            print("GMM not fitted yet. Fit the model first.")
            return self.image

        # Predict the component for each pixel
        pixels = self.image.flatten().reshape(-1, 1)
        labels = self.gmm.predict(pixels)

        # Use the mean of the components to threshold
        thresholds = self.gmm.means_.flatten()
        binary_image = labels.reshape(self.image.shape) == np.argmin(thresholds)  # Choose the lowest mean as background
        return (binary_image * 255).astype(np.uint8)