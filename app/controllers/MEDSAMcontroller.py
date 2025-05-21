from flask import Blueprint, request, jsonify
import base64, io
from PIL import Image
import numpy as np
import torch
import cv2
import json
import os

# Update paths to find the SAM2 modules
import sys
# Get the absolute path to the app directory
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
vendors_dir = os.path.join(app_dir, 'vendors', 'Medical-SAM2')
sys.path.append(vendors_dir)

from sam2_train.build_sam import build_sam2
from sam2_train.sam2_image_predictor import SAM2ImagePredictor

# Create Blueprint
bp = Blueprint('medsam', __name__, url_prefix='/medsam')

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

try:
    # --- Load model ---
    model = build_sam2(CONFIG_FILENAME, CHECKPOINT_PATH, device=DEVICE, mode="eval")
    model.to(DEVICE)
    model.eval()
    predictor = SAM2ImagePredictor(model)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    import traceback
    traceback.print_exc()
    # Create dummy predictor for development without crashing the app
    predictor = None

# Replace the _data_url_to_array function in your MEDSAMcontroller.py with this improved version

def _data_url_to_array(data_url):
    """
    Convert various image formats to numpy array.
    
    Supports:
    - Data URLs (base64 encoded)
    - File paths
    - URLs
    """
    print(f"Processing image data: {data_url[:50]}..." if isinstance(data_url, str) else "Non-string data")
    
    # Handle data URLs
    if isinstance(data_url, str) and data_url.startswith('data:'):
        try:
            header, encoded = data_url.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            print("Successfully decoded data URL")
            return np.array(img)
        except Exception as e:
            print(f"Error decoding data URL: {e}")
            raise
    
    # Handle file paths and URLs
    elif isinstance(data_url, str):
        # If it starts with http(s):// or / - treat as URL or file path
        if data_url.startswith(('http://', 'https://', '/')):
            try:
                # First try treating as a file path
                if os.path.exists(data_url):
                    img = Image.open(data_url).convert("RGB")
                    print(f"Loaded from file path: {data_url}")
                    return np.array(img)
            except Exception as e:
                print(f"Error opening as file path: {e}")
                
            try:
                # Next try treating as a URL
                from urllib.request import urlopen
                img_bytes = urlopen(data_url).read()
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                print(f"Loaded from URL: {data_url}")
                return np.array(img)
            except Exception as e:
                print(f"Error opening as URL: {e}")
                
            # If we get here, both attempts failed
            raise ValueError(f"unknown url type: '{data_url}'")
        else:
            # Not a known format
            raise ValueError(f"unknown url type: '{data_url}'")
    else:
        # Not a string
        raise ValueError("image_data must be a string")

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

# Add diagnostic endpoint to check model status
@bp.route("/model_status", methods=["GET"])
def model_status():
    """Endpoint to check model loading status"""
    global predictor, model, model_loading_error
    
    status = {
        "loaded": predictor is not None,
        "device": DEVICE,
        "config_exists": os.path.exists(CONFIG_PATH),
        "checkpoint_exists": os.path.exists(CHECKPOINT_PATH),
    }
    
    if model_loading_error:
        status["error"] = model_loading_error
    
    # If model isn't loaded but files exist, provide a reload option
    if predictor is None and os.path.exists(CONFIG_PATH) and os.path.exists(CHECKPOINT_PATH):
        status["can_reload"] = True
    
    return jsonify(status)

@bp.route("/reload_model", methods=["POST"])
def reload_model():
    """Endpoint to attempt reloading the model"""
    success = load_model()
    return jsonify({
        "success": success,
        "loaded": predictor is not None,
        "error": model_loading_error if not success else None
    })

@bp.route("/apply_clahe", methods=["POST"])
def apply_clahe():
    arr = _data_url_to_array(request.json["image"])
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    out = cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2RGB)
    return jsonify({"image": _array_to_data_url(out)})

# Add this to your MEDSAMcontroller.py to return the mask separately from the overlay

@bp.route("/run_segmentation", methods=["POST"])
def run_segmentation():
    """Endpoint that matches what segmentation_tools.js expects, with separate mask data"""
    data = request.json
    
    # Check if model was loaded successfully
    if predictor is None:
        return jsonify({
            "success": False,
            "error": "Model not loaded. Check server logs for details."
        }), 500
    
    try:
        # Get the image
        arr = _data_url_to_array(data["image_data"])
        
        # Set up input parameters
        point_coords = None
        point_labels = None
        box = None
        
        # Extract points from the request
        if "positive_points" in data and data["positive_points"]:
            # Initialize lists if we have positive points
            if point_coords is None:
                point_coords = []
                point_labels = []
            
            # Add positive points
            for point in data["positive_points"]:
                point_coords.append(point)
                point_labels.append(1)
        
        if "negative_points" in data and data["negative_points"]:
            # Initialize lists if we have negative points but no positive points
            if point_coords is None:
                point_coords = []
                point_labels = []
            
            # Add negative points
            for point in data["negative_points"]:
                point_coords.append(point)
                point_labels.append(0)
        
        # Extract box if provided
        if "draw_path" in data and data["draw_path"]:
            # Handle draw path here (for now, we'll just use it as a hint)
            # For simplicity, we'll just extract a representative point
            draw_path = data["draw_path"]
            if len(draw_path) > 0:
                # Use the first point as a positive point
                if point_coords is None:
                    point_coords = []
                    point_labels = []
                
                # Calculate the center of the drawing as a positive point
                x_sum = sum(p[0] for p in draw_path)
                y_sum = sum(p[1] for p in draw_path)
                avg_x = x_sum / len(draw_path)
                avg_y = y_sum / len(draw_path)
                
                point_coords.append([avg_x, avg_y])
                point_labels.append(1)
        
        # Convert to numpy arrays if we have points
        if point_coords:
            point_coords = np.array(point_coords)
            point_labels = np.array(point_labels)
        
        # Set the image in the predictor
        predictor.set_image(arr)
        
        # Run prediction based on what we have
        if point_coords is not None:
            masks, scores, _ = predictor.predict(
                point_coords=point_coords,
                point_labels=point_labels,
                multimask_output=True
            )
        else:
            return jsonify({"error": "No input provided. Need point coordinates or drawing."}), 400
        
        # Create overlay for best mask (highest score)
        best_mask_idx = np.argmax(scores)
        mask = masks[best_mask_idx].astype(bool)
        
        # Create the overlay
        overlay = _create_overlay(
            arr, 
            mask, 
            point_coords=point_coords, 
            point_labels=point_labels
        )
        
        # Serialize all masks for the frontend
        all_masks, all_scores = _serialize_masks(masks, scores)
        
        # Save original image as data URL
        original_data_url = _array_to_data_url(arr)
        
        # Create a mask-only image for separate display
        # Create a separate mask-only image (white mask on black background)
        mask_only = np.zeros_like(arr)
        mask_only[mask] = [255, 255, 255]  # White mask
        mask_data_url = _array_to_data_url(mask_only)
        
        return jsonify({
            "success": True,
            "overlay": _array_to_data_url(overlay),
            "original": original_data_url,
            "mask": mask_data_url,
            "score": float(scores[best_mask_idx]),
            "all_masks": all_masks,
            "all_scores": all_scores
        })
        
    except Exception as e:
        print(f"Error in run_segmentation: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
        
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

@bp.route("/predict_point", methods=["POST"])
def predict_point():
    """Legacy endpoint for backward compatibility"""
    data = request.json
    arr = _data_url_to_array(data["image"])
    x, y = data["x"], data["y"]
    
    try:
        predictor.set_image(arr)
        masks, _, _ = predictor.predict(
            point_coords=np.array([[x,y]]),
            point_labels=np.array([1]),
            multimask_output=False
        )
        mask = masks[0].astype(bool)
        overlay = _create_overlay(arr, mask, point_coords=np.array([[x,y]]), point_labels=np.array([1]))
        return jsonify({"overlay": _array_to_data_url(overlay)})
    except Exception as e:
        print(f"Error in predict_point: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route("/predict_points", methods=["POST"])
def predict_points():
    """Legacy endpoint for backward compatibility"""
    data = request.json
    arr = _data_url_to_array(data["image"])
    point_coords = np.array(data["point_coords"])
    point_labels = np.array(data["point_labels"])
    
    try:
        predictor.set_image(arr)
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True
        )
        
        best_mask_idx = np.argmax(scores)
        mask = masks[best_mask_idx].astype(bool)
        overlay = _create_overlay(arr, mask, point_coords=point_coords, point_labels=point_labels)
        
        return jsonify({
            "overlay": _array_to_data_url(overlay),
            "score": float(scores[best_mask_idx])
        })
    except Exception as e:
        print(f"Error in predict_points: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route("/predict_box", methods=["POST"])
def predict_box():
    """Legacy endpoint for backward compatibility"""
    data = request.json
    arr = _data_url_to_array(data["image"])
    x1, y1, x2, y2 = data["box"]
    
    try:
        predictor.set_image(arr)
        masks, _, _ = predictor.predict(
            box=np.array([[x1, y1, x2, y2]]),
            multimask_output=False
        )
        mask = masks[0].astype(bool)
        overlay = _create_overlay(arr, mask, box=[x1, y1, x2, y2])
        
        return jsonify({"overlay": _array_to_data_url(overlay)})
    except Exception as e:
        print(f"Error in predict_box: {str(e)}")
        return jsonify({"error": str(e)}), 500

                                                    
@bp.route("/test", methods=["GET"])
def test():
    """Simple test endpoint to check if the blueprint is working"""
    return jsonify({"status": "ok", "message": "MEDSAMcontroller is accessible"})

# Add this improved debug route to help diagnose the segmentation issue
@bp.route("/debug_segmentation", methods=["POST"])
def debug_segmentation():
    """Endpoint to diagnose segmentation issues step by step"""
    data = request.json
    response = {
        "success": True,
        "steps": []
    }
    
    # Step 1: Check predictor status
    if predictor is None:
        response["steps"].append({"step": "Check predictor", "status": "failed", "message": "Model not loaded"})
        response["success"] = False
        return jsonify(response)
    else:
        response["steps"].append({"step": "Check predictor", "status": "success"})
    
    # Step 2: Check image data
    try:
        if "image_data" not in data:
            response["steps"].append({"step": "Check image data", "status": "failed", "message": "No image data provided"})
            response["success"] = False
            return jsonify(response)
        
        # Try to decode image
        try:
            arr = _data_url_to_array(data["image_data"])
            img_shape = arr.shape
            response["steps"].append({
                "step": "Decode image", 
                "status": "success", 
                "image_shape": f"{img_shape[0]}x{img_shape[1]}x{img_shape[2]}"
            })
        except Exception as e:
            response["steps"].append({
                "step": "Decode image", 
                "status": "failed", 
                "message": str(e)
            })
            response["success"] = False
            return jsonify(response)
        
        # Step 3: Check points data
        has_points = False
        if ("positive_points" in data and data["positive_points"]) or \
           ("negative_points" in data and data["negative_points"]) or \
           ("draw_path" in data and data["draw_path"]):
            has_points = True
            point_count = 0
            if "positive_points" in data and data["positive_points"]:
                point_count += len(data["positive_points"])
            if "negative_points" in data and data["negative_points"]:
                point_count += len(data["negative_points"])
            if "draw_path" in data and data["draw_path"]:
                point_count += 1  # We'll use one point from the drawing
                
            response["steps"].append({
                "step": "Check points data", 
                "status": "success", 
                "point_count": point_count
            })
        else:
            response["steps"].append({
                "step": "Check points data", 
                "status": "failed", 
                "message": "No selection points provided"
            })
            response["success"] = False
            return jsonify(response)
        
        # Step 4: Test setting image
        try:
            predictor.set_image(arr)
            response["steps"].append({
                "step": "Set image in predictor", 
                "status": "success"
            })
        except Exception as e:
            response["steps"].append({
                "step": "Set image in predictor", 
                "status": "failed", 
                "message": str(e)
            })
            response["success"] = False
            return jsonify(response)
        
        # Step 5: Extract a test point
        test_point = None
        test_label = None
        
        if "positive_points" in data and data["positive_points"]:
            test_point = np.array([data["positive_points"][0]])
            test_label = np.array([1])
        elif "negative_points" in data and data["negative_points"]:
            test_point = np.array([data["negative_points"][0]])
            test_label = np.array([0])
        elif "draw_path" in data and data["draw_path"]:
            # Calculate the center of the drawing as a positive point
            draw_path = data["draw_path"]
            x_sum = sum(p[0] for p in draw_path)
            y_sum = sum(p[1] for p in draw_path)
            avg_x = x_sum / len(draw_path)
            avg_y = y_sum / len(draw_path)
            test_point = np.array([[avg_x, avg_y]])
            test_label = np.array([1])
        
        # Step 6: Try a simple prediction with one point
        try:
            if test_point is not None:
                test_masks, test_scores, _ = predictor.predict(
                    point_coords=test_point,
                    point_labels=test_label,
                    multimask_output=False
                )
                
                response["steps"].append({
                    "step": "Test prediction", 
                    "status": "success",
                    "score": float(test_scores[0])
                })
                
                # Return a simple overlay for verification
                test_mask = test_masks[0].astype(bool)
                test_overlay = _create_overlay(
                    arr, 
                    test_mask, 
                    point_coords=test_point, 
                    point_labels=test_label
                )
                
                response["test_overlay"] = _array_to_data_url(test_overlay)
                
            else:
                response["steps"].append({
                    "step": "Test prediction", 
                    "status": "failed",
                    "message": "Could not create a test point"
                })
                response["success"] = False
                
        except Exception as e:
            response["steps"].append({
                "step": "Test prediction", 
                "status": "failed", 
                "message": str(e)
            })
            response["success"] = False
            import traceback
            response["traceback"] = traceback.format_exc()
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500