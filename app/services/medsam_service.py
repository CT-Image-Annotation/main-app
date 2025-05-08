import torch
import numpy as np
import cv2
from segment_anything import sam_model_registry, SamPredictor
from flask import current_app
from .download_medsam import download_medsam_model
import os

class MedSAMService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MedSAMService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model = None
            self.predictor = None
            self._initialized = True

    def initialize_model(self):
        """Initialize the MedSAM model."""
        if self.model is not None:
            return

        model_type = "vit_h"
        checkpoint = current_app.config.get('MEDSAM_CHECKPOINT_PATH', 'models/medsam_vit_h.pth')
        
        # Try to download the model if it doesn't exist
        if not os.path.exists(checkpoint):
            try:
                download_medsam_model()
            except Exception as e:
                raise FileNotFoundError(
                    f"Failed to download MedSAM model: {str(e)}. "
                    "Please download it manually and place it in the models directory."
                )
            
        self.model = sam_model_registry[model_type](checkpoint=checkpoint)
        self.model.to(device=self.device)
        self.predictor = SamPredictor(self.model)

    def segment_image(self, image, box):
        """
        Segment the image using MedSAM with the given bounding box.
        
        Args:
            image: numpy array of the image
            box: list of [x1, y1, x2, y2] coordinates
            
        Returns:
            numpy array of the segmentation mask
        """
        if self.predictor is None:
            self.initialize_model()

        # Set the image in the predictor
        self.predictor.set_image(image)

        # Convert box to the format expected by MedSAM
        input_box = np.array(box)

        # Generate the mask
        masks, _, _ = self.predictor.predict(
            box=input_box,
            multimask_output=False
        )

        # Return the first mask
        return masks[0]

    def overlay_mask(self, image, mask, alpha=0.5):
        """
        Overlay the segmentation mask on the original image.
        
        Args:
            image: numpy array of the original image
            mask: numpy array of the segmentation mask
            alpha: transparency of the overlay
            
        Returns:
            numpy array of the overlaid image
        """
        # Create a colored mask
        colored_mask = np.zeros_like(image)
        colored_mask[mask] = [0, 255, 0]  # Green color for the mask

        # Overlay the mask on the original image
        overlay = cv2.addWeighted(image, 1, colored_mask, alpha, 0)
        return overlay 