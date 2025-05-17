import os
import gdown
from flask import current_app

def download_medsam_model():
    """Download the MedSAM model checkpoint if it doesn't exist."""
    checkpoint_path = current_app.config.get('MEDSAM_CHECKPOINT_PATH')
    
    # Create models directory if it doesn't exist
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    
    # Check if model already exists
    if os.path.exists(checkpoint_path):
        print(f"MedSAM model already exists at {checkpoint_path}")
        return
    
    print("Downloading MedSAM model...")
    
    # MedSAM model URL
    model_url = "https://drive.google.com/uc?id=1UAmWL88roYR7wKlnApw5Bcuzf2iQgk6_"
    
    try:
        gdown.download(model_url, checkpoint_path, quiet=False)
        print(f"MedSAM model downloaded successfully to {checkpoint_path}")
    except Exception as e:
        print(f"Error downloading MedSAM model: {str(e)}")
        raise 