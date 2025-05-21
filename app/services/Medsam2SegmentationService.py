from flask import Flask, render_template, request, jsonify
import base64, io
from PIL import Image
import numpy as np
import torch
import cv2
import json

from sam2_train.build_sam import build_sam2
from sam2_train.sam2_image_predictor import SAM2ImagePredictor

# --- Config ---
DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
CONFIG     = "sam2_hiera_s.yaml"
CHECKPOINT = "./checkpoints/sam2_hiera_small.pt"

# --- Load model once ---
model = build_sam2(CONFIG, CHECKPOINT, device=DEVICE, mode="eval")
model.to(DEVICE)
model.eval()
predictor = SAM2ImagePredictor(model)

app = Flask(__name__, template_folder='templates', static_folder='static')

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
    """Create overlay with mask and optionally points and box"""
    overlay = arr.copy()
    
    # More vibrant red for better visibility
    mask_color = np.array([255, 0, 0], dtype=np.uint8)
    
    # Apply the mask directly with higher opacity
    overlay[mask] = cv2.addWeighted(
        overlay[mask], 0.4, 
        np.ones_like(overlay[mask]) * mask_color, 0.6, 
        0
    )
    
    # Draw contour of the mask for better visibility (optional)
    if draw_contours:
        contours, _ = cv2.findContours((mask).astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (255, 255, 0), 2)  # Yellow contour
    
    # Draw points if provided
    if point_coords is not None and point_labels is not None:
        for i, (x, y) in enumerate(point_coords):
            color = (0, 255, 0) if point_labels[i] == 1 else (255, 0, 0)  # Green for positive, Red for negative
            cv2.circle(overlay, (int(x), int(y)), 6, color, -1)
            cv2.circle(overlay, (int(x), int(y)), 6, (255, 255, 255), 1)  # White border
    
    # Draw box if provided
    if box is not None:
        x1, y1, x2, y2 = box
        cv2.rectangle(overlay, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
    
    return overlay

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

@app.route("/predict_combined", methods=["POST"])
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
        multimask_output = data.get("multimask_output", True)
        
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
            
            return jsonify({ # Regular response
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
