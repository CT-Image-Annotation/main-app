# Update paths to find the SAM2 modules
import base64
import io
import os
import sys
from PIL import Image

import cv2
from flask import Blueprint, jsonify, request
import numpy as np
import torch

# from app.vendors.MedSAM2.sam2_train.build_sam import build_sam2
# from app.vendors.MedSAM2.sam2_train.sam2_image_predictor import SAM2ImagePredictor
# Get the absolute path to the app directory
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
vendors_dir = os.path.join(app_dir, 'vendors', 'Medical-SAM2')

sys.path.append(vendors_dir)
# Create Blueprint
bp = Blueprint('MedSAM2', __name__)

# --- Config ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Use a simpler path approach for the config file
# Just use the filename instead of the full path, as the model loader
# might be expecting configs in a specific directory structure
CONFIG_FILENAME = 'sam2_hiera_s.yaml'
CHECKPOINT_PATH = os.path.join(vendors_dir, 'checkpoints', 'sam2_hiera_small.pt')


# Print paths for debugging
print(f"Using CONFIG_FILENAME: {CONFIG_FILENAME}")
print(f"Using CHECKPOINT_PATH: {CHECKPOINT_PATH}")
print(f"Checking if checkpoint exists: {os.path.exists(CHECKPOINT_PATH)}")
from sam2_train.build_sam import build_sam2
from sam2_train.sam2_image_predictor import SAM2ImagePredictor

# --- Load model once ---
model = build_sam2(CONFIG_FILENAME, CHECKPOINT_PATH, device=DEVICE, mode="eval")
model.to(DEVICE)
model.eval()
predictor = SAM2ImagePredictor(model)

def _data_url_to_array(data_url):
    header, encoded = data_url.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return np.array(img)

def _array_to_data_url(arr):
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def _create_overlay(arr, mask, point_coords=None, point_labels=None, box=None, draw_contours=False):
    """Create transparent overlay with only the mask visible"""
    # Create a transparent RGBA overlay
    overlay = np.zeros((*arr.shape[:2], 4), dtype=np.uint8)
    
    # Set the mask area to a semi-transparent red
    overlay[mask] = [255, 0, 0, 128]  # RGBA format: semi-transparent red
    
    # Draw contour of the mask for better visibility (optional)
    if draw_contours:
        contours, _ = cv2.findContours((mask).astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        # Create a temporary image for contours
        contour_img = np.zeros_like(overlay)
        cv2.drawContours(contour_img, contours, -1, (255, 255, 0, 255), 2)  # Yellow contour, fully opaque
        # Combine with the main overlay
        mask_contour = contour_img[:,:,3] > 0
        overlay[mask_contour] = contour_img[mask_contour]
    
    # Draw points if provided
    if point_coords is not None and point_labels is not None:
        for i, (x, y) in enumerate(point_coords):
            color = (0, 255, 0, 255) if point_labels[i] == 1 else (255, 0, 0, 255)  # RGBA format
            x, y = int(x), int(y)
            cv2.circle(overlay, (x, y), 6, color, -1)
            cv2.circle(overlay, (x, y), 6, (255, 255, 255, 255), 1)  # White border
    
    # Draw box if provided
    if box is not None:
        x1, y1, x2, y2 = box
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255, 255), 2)
    
    # Convert the RGBA overlay to PNG
    _, png_data = cv2.imencode('.png', overlay)
    return png_data

    
def _serialize_masks(masks, scores):
    """Serialize masks and scores for JSON transmission"""
    all_masks = []
    all_scores = []

    for i, mask in enumerate(masks):
        # Convert each mask to a flat list of booleans
        # Ensure we're working with a boolean type mask
        bool_mask = mask.astype(bool)
        mask_flat = bool_mask.flatten().tolist()
        all_masks.append(mask_flat)
        all_scores.append(float(scores[i]))
    
    return all_masks, all_scores

@bp.route("/predict_combined", methods=["POST"])
def predict_combined():
    data = request.json
    arr = _data_url_to_array(data["image"])
    
    try:
        # Set image
        predictor.set_image(arr)
        
        # Get inputs if provided
        point_coords = np.array(data.get("point_coords", [])) if "point_coords" in data else None
        point_labels = np.array(data.get("point_labels", [])) if "point_labels" in data else None
        box = np.array([data["box"]]) if "box" in data else None
        
        # Get multimask_output preference (default to True)
        multimask_output = data.get("multimask_output", False)
        
        # Predict based on available inputs
        if point_coords is not None and point_labels is not None:
            if box is not None:
                # Combined points and box
                masks, scores, _ = predictor.predict(
                    point_coords=point_coords,
                    point_labels=point_labels,
                    box=box,
                    multimask_output=multimask_output
                )
            else:
                # Only points
                masks, scores, _ = predictor.predict(
                    point_coords=point_coords,
                    point_labels=point_labels,
                    multimask_output=multimask_output
                )
        elif box is not None:
            # Only box
            masks, scores, _ = predictor.predict(
                box=box,
                multimask_output=multimask_output
            )
        else:
            return jsonify({"error": "No input provided. Need point coordinates or box."}), 400
        
        # Choose the best mask based on model scores for the overlay preview
        best_mask_idx = np.argmax(scores)
        mask = masks[best_mask_idx].astype(bool)
        
        # Create overlay for best mask
        overlay = _create_overlay(
            arr, 
            mask, 
            point_coords=point_coords, 
            point_labels=point_labels, 
            box=data.get("box"),
            draw_contours=False  # Disable contours
        )
        
        # For multi-mask output, serialize all masks and scores
        if multimask_output and len(masks) > 1:
            all_masks, all_scores = _serialize_masks(masks, scores)
            
            # Make sure mask data is properly formatted for the frontend
            print(f"Sending {len(all_masks)} masks to frontend")
            print(f"First mask shape: {masks[0].shape}, data type: {masks[0].dtype}")
            print(f"Serialized mask length: {len(all_masks[0])}")
            
            return jsonify({
                "overlay": _array_to_data_url(overlay),
                "score": float(scores[best_mask_idx]),
                "all_masks": all_masks,
                "all_scores": all_scores
            })
        else:
            # Single mask output (legacy support)
            return jsonify({
                "overlay": _array_to_data_url(overlay),
                "score": float(scores[best_mask_idx])
            })
            
    except Exception as e:
        print(f"Error in predict_combined: {str(e)}")
        return jsonify({"error": str(e)}), 500