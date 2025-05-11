import cv2
from flask import current_app
import numpy as np
import torch
from skimage import transform
import os
import gdown
from segment_anything import sam_model_registry
import torch.nn.functional as F
from app.services.BaseService import Base

class BoundingBoxSegmentationService(Base):
    @staticmethod
    def segmentBox(image_buffer, box_coords):
        image_bgr = cv2.imdecode(np.frombuffer(image_buffer, np.uint8), cv2.IMREAD_COLOR)

        segmenter = BoundingBoxSegmenter(os.path.join(current_app.config['MEDSAM_PATH'], "work_dir/MedSAM/medsam_vit_b.pth"))
        return segmenter.apply_medsam_segmentation(image_bgr, box_coords)

class BoundingBoxSegmenter:
    """
    Uses MedSAM for bounding-box-based segmentation.
    """
    def __init__(self, medsam_checkpoint_path, device="cuda" if torch.cuda.is_available() else "cpu"):
        if not os.path.exists(medsam_checkpoint_path):
            os.makedirs(os.path.dirname(medsam_checkpoint_path), exist_ok=True)
            url = "https://drive.google.com/uc?id=1UAmWL88roYR7wKlnApw5Bcuzf2iQgk6_"
            print(f"[MedSAM] Model not found, downloading.")
            gdown.download(url, medsam_checkpoint_path, quiet=False)
            print(f"[MedSAM] Model downloaded.")

        self.scribble_enabled = False
        self.scribble_points_fg = []
        self.scribble_points_bg = []
        self.device = device

        # Load MedSAM
        self.model = sam_model_registry['vit_b'](checkpoint=medsam_checkpoint_path)
        self.model.to(self.device)
        self.model.eval()
        print(f"[MedSAM] Model loaded from {medsam_checkpoint_path} on {self.device}")

        # We will store the raw bounding box, but typically we pass it directly
        self.bounding_box = None

    def set_bounding_box(self, box_coords):
        """Stores the bounding box coords: (x_min, y_min, x_max, y_max)."""
        self.bounding_box = box_coords
        print(f"[INFO] Bounding box saved: {self.bounding_box}")

    def apply_medsam_segmentation(self, image_bgr, box_np):
        """
        Run MedSAM bounding box segmentation on the full image with the given box.
        
        :param image_bgr: The entire image (BGR) as a NumPy array.
        :param box_np: shape (1,4) -> [[x_min, y_min, x_max, y_max]]
        :return: Image with yellow overlay for segmentation and blue bounding box.
        """
        if box_np is None:
            print("[ERROR] No bounding box provided for MedSAM!")
            return image_bgr

        try:
            # Convert BGR to RGB for MedSAM
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            H, W = image_rgb.shape[:2]

            # Get box region for analysis
            x_min, y_min, x_max, y_max = map(int, box_np[0])
            
            # Ensure box coordinates are within image bounds
            x_min = max(0, x_min)
            y_min = max(0, y_min)
            x_max = min(W, x_max)
            y_max = min(H, y_max)
            
            # Check if box is too small
            if x_max - x_min < 10 or y_max - y_min < 10:
                print("[ERROR] Bounding box is too small!")
                return image_bgr
            
            # Expand region for analysis (with bounds checking)
            analysis_x_min = max(0, x_min - 10)
            analysis_y_min = max(0, y_min - 10)
            analysis_x_max = min(W, x_max + 10)
            analysis_y_max = min(H, y_max + 10)
            
            # Get both the exact box region and the expanded region
            box_region = image_rgb[y_min:y_max, x_min:x_max]
            analysis_region = image_rgb[analysis_y_min:analysis_y_max, analysis_x_min:analysis_x_max]
            
            # Convert both to grayscale
            box_gray = cv2.cvtColor(box_region, cv2.COLOR_RGB2GRAY)
            analysis_gray = cv2.cvtColor(analysis_region, cv2.COLOR_RGB2GRAY)
            
            # Enhanced local contrast analysis on the expanded region
            mean_intensity = np.mean(analysis_gray)
            std_intensity = np.std(analysis_gray)
            
            # Calculate adaptive thresholds with more lenient bounds near edges
            edge_factor = 0.8  # More lenient threshold for edges
            center_factor = 1.5  # Stricter threshold for center
            
            # Create distance map from edges of the box
            h, w = box_gray.shape
            y_coords, x_coords = np.ogrid[:h, :w]
            
            # Calculate distance from each edge separately
            dist_left = x_coords
            dist_right = w - 1 - x_coords
            dist_top = y_coords
            dist_bottom = h - 1 - y_coords
            
            # Combine distances
            distance_from_edge = np.minimum(np.minimum(dist_left, dist_right),
                                         np.minimum(dist_top, dist_bottom))
            
            # Normalize distance map to [0, 1]
            max_distance = np.max(distance_from_edge)
            if max_distance > 0:
                distance_factor = distance_from_edge / max_distance
            else:
                distance_factor = np.ones_like(distance_from_edge)
            
            # Create intensity mask with adaptive thresholding
            intensity_mask = np.zeros_like(box_gray)
            
            # Calculate thresholds for each pixel based on distance
            threshold_factor = edge_factor + (center_factor - edge_factor) * distance_factor
            lower_thresholds = mean_intensity - threshold_factor * std_intensity
            upper_thresholds = mean_intensity + threshold_factor * std_intensity
            
            # Apply thresholding manually
            intensity_mask = np.logical_and(
                box_gray >= lower_thresholds,
                box_gray <= upper_thresholds
            ).astype(np.uint8) * 255
            
            # Calculate gradient magnitude with extra context
            sobelx = cv2.Sobel(analysis_gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(analysis_gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
            
            # Crop gradient magnitude back to box size
            pad_x = 10
            pad_y = 10
            gradient_magnitude = gradient_magnitude[pad_y:pad_y+box_gray.shape[0], 
                                                 pad_x:pad_x+box_gray.shape[1]]
            
            # Normalize gradient magnitude
            gradient_magnitude = cv2.normalize(gradient_magnitude, None, 0, 255, cv2.NORM_MINMAX)
            
            # Enhanced preprocessing pipeline
            enhanced = cv2.edgePreservingFilter(image_rgb, flags=cv2.NORMCONV_FILTER, 
                                              sigma_s=30, sigma_r=0.3)

            # Multi-scale CLAHE for better local contrast
            lab = cv2.cvtColor(enhanced, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE at different scales
            clahe_strong = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            clahe_weak = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16,16))
            
            l_strong = clahe_strong.apply(l)
            l_weak = clahe_weak.apply(l)
            
            # Blend the two CLAHE results
            l_enhanced = cv2.addWeighted(l_strong, 0.6, l_weak, 0.4, 0)
            
            enhanced = cv2.merge([l_enhanced, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)

            # Rest of the preprocessing remains the same
            img_1024 = transform.resize(
                enhanced, (1024, 1024),
                order=3, preserve_range=True,
                anti_aliasing=True
            ).astype(np.uint8)

            scaled_box = np.array([[
                x_min * 1024 / W,
                y_min * 1024 / H,
                x_max * 1024 / W,
                y_max * 1024 / H
            ]], dtype=float)

            img_1024_tensor = torch.tensor(img_1024).float()
            img_1024_tensor = img_1024_tensor / 255.0
            img_1024_tensor = img_1024_tensor.permute(2, 0, 1).unsqueeze(0)
            img_1024_tensor = img_1024_tensor.to(self.device)

            with torch.no_grad():
                img_embed = self.model.image_encoder(img_1024_tensor)
                # Lower threshold near edges
                base_threshold = 0.7
                edge_threshold = 0.5
                masks = self._medsam_inference(img_embed, scaled_box, H, W, 
                                             threshold=edge_threshold)  # Start with lower threshold
                
                if len(masks.shape) == 3:
                    scores = []
                    for i, m in enumerate(masks):
                        try:
                            mask_region = m[y_min:y_max, x_min:x_max]
                            
                            # Calculate edge alignment score with distance-based weighting
                            edge_score = self._calculate_edge_score(box_gray, mask_region)
                            
                            # Calculate intensity separation score
                            mask_mean = np.mean(box_gray[mask_region > 0])
                            non_mask_mean = np.mean(box_gray[mask_region == 0])
                            intensity_diff = abs(mask_mean - non_mask_mean) / 255.0
                            
                            # Calculate gradient alignment score
                            mask_edges = cv2.Canny(mask_region.astype(np.uint8) * 255, 100, 200)
                            gradient_alignment = np.mean(gradient_magnitude[mask_edges > 0]) / 255.0
                            
                            # Weight scores based on distance from edge
                            edge_weight = np.mean(1 - distance_factor[mask_region > 0])
                            center_weight = 1 - edge_weight
                            
                            # Combined score with edge-aware weighting
                            score = (edge_score * (0.4 + 0.1 * edge_weight) + 
                                   intensity_diff * (0.3 + 0.1 * center_weight) + 
                                   gradient_alignment * 0.3)
                            
                            # Penalize if mask doesn't align with intensity mask
                            overlap = np.sum(mask_region & intensity_mask) / (np.sum(mask_region) + 1e-6)
                            if overlap < 0.5:
                                score *= 0.5
                                
                            scores.append(score)
                            
                        except Exception as e:
                            print(f"[WARNING] Error calculating score for mask {i}: {e}")
                            scores.append(-1)
                    
                    if all(s == -1 for s in scores):
                        print("[WARNING] No valid masks found, using first mask")
                        mask = masks[0]
                    else:
                        best_mask_idx = np.argmax(scores)
                        mask = masks[best_mask_idx]
                else:
                    mask = masks

                # Refined post-processing with edge awareness
                mask = mask.astype(np.uint8)
                refined_mask = np.zeros_like(mask)
                
                # Get contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                
                if contours:
                    # Draw all contours
                    for contour in contours:
                        cv2.drawContours(refined_mask, [contour], -1, 1, -1)
                    
                    # Extract the region of interest for refinement
                    mask_region = refined_mask[y_min:y_max, x_min:x_max]
                    
                    # Create edge-aware kernel sizes
                    kernel_size = np.clip(3 - distance_factor.astype(np.int32), 1, 3)
                    
                    # Refine edges with variable kernel sizes
                    dilated = np.zeros_like(mask_region)
                    eroded = np.zeros_like(mask_region)
                    
                    # Apply morphological operations with distance-based kernels
                    for ks in range(1, 4):
                        kernel = np.ones((ks, ks), np.uint8)
                        mask_region_ks = mask_region.copy()
                        dilated_ks = cv2.dilate(mask_region_ks, kernel, iterations=1)
                        eroded_ks = cv2.erode(mask_region_ks, kernel, iterations=1)
                        
                        # Apply operations where kernel_size matches
                        apply_mask = (kernel_size == ks)
                        dilated[apply_mask] = dilated_ks[apply_mask]
                        eroded[apply_mask] = eroded_ks[apply_mask]
                    
                    boundary = dilated - eroded
                    
                    # Adaptive edge strength threshold
                    edge_percentile = np.clip(70 + 20 * distance_factor, 70, 90)
                    strong_edges = gradient_magnitude > np.percentile(gradient_magnitude, edge_percentile)
                    
                    # Combine results
                    refined_region = cv2.bitwise_and(mask_region, mask_region, 
                                                   mask=cv2.bitwise_not(boundary)) | \
                                   (boundary & strong_edges)
                    
                    # Put the refined region back into the full mask
                    refined_mask[y_min:y_max, x_min:x_max] = refined_region
                    mask = refined_mask

        except Exception as e:
            print(f"[ERROR] MedSAM failed: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return image_bgr

        try:
            # Create result image with precise overlay
            result_image = image_bgr.copy()
            yellow_overlay = np.zeros_like(result_image)
            yellow_overlay[:] = (0, 255, 255)  # BGR for yellow
            mask_bgr = cv2.cvtColor((mask * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
            yellow_overlay = cv2.bitwise_and(yellow_overlay, mask_bgr)
            
            # Add edge highlight
            edges = cv2.Canny(mask_bgr, 100, 200)
            
            # Create edge mask for the box region
            edge_mask = np.zeros_like(mask)
            edge_mask[y_min:y_max, x_min:x_max] = edges[y_min:y_max, x_min:x_max]
            
            # Calculate edge intensity based on distance factor
            edge_intensity = np.zeros_like(edge_mask, dtype=np.uint8)
            edge_intensity[y_min:y_max, x_min:x_max] = np.clip(200 + 55 * distance_factor, 200, 255).astype(np.uint8)
            
            # Apply edge highlighting
            edge_overlay = np.zeros_like(result_image)
            edge_overlay[edge_mask > 0] = [0, 255, 255]  # Yellow edges
            
            # Combine overlays
            result_image = cv2.addWeighted(result_image, 1.0, yellow_overlay, 0.4, 0)
            result_image = cv2.addWeighted(result_image, 1.0, edge_overlay, 0.6, 0)
            
            # Draw bounding box
            cv2.rectangle(result_image, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
            
            return result_image
        except Exception as e:
            print(f"[ERROR] Failed to create overlay: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return image_bgr

    def _calculate_edge_score(self, gray_image, mask):
        """Calculate how well the mask aligns with strong edges in the image."""
        try:
            # Ensure mask has same size as gray_image
            mask = cv2.resize(mask.astype(np.uint8), (gray_image.shape[1], gray_image.shape[0]))
            
            # Calculate edges at multiple scales
            edges1 = cv2.Canny(gray_image, 50, 150)
            edges2 = cv2.Canny(gray_image, 100, 200)
            edges = cv2.bitwise_or(edges1, edges2)
            
            # Calculate mask edges
            mask_edges = cv2.Canny(mask * 255, 100, 200)
            
            # Dilate both edge maps slightly for better matching
            kernel = np.ones((3,3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            mask_edges = cv2.dilate(mask_edges, kernel, iterations=1)
            
            # Calculate intersection
            intersection = cv2.bitwise_and(edges, mask_edges)
            
            return np.sum(intersection) / (np.sum(mask_edges) + 1e-6)
        except Exception as e:
            print(f"[WARNING] Edge score calculation failed: {e}")
            return 0.5  # Return neutral score on failure

    @torch.no_grad()
    def _medsam_inference(self, img_embed, scaled_box, H, W, threshold=0.6):
        """
        Feed the bounding box into prompt_encoder as boxes=...
        Then upsample to H×W.
        """
        box_torch = torch.tensor(scaled_box, dtype=torch.float, device=self.device)

        sparse_embeddings, dense_embeddings = self.model.prompt_encoder(
            points=None,
            boxes=box_torch,
            masks=None,
        )

        # Get multiple mask predictions
        low_res_logits, iou_predictions = self.model.mask_decoder(
            image_embeddings=img_embed,
            image_pe=self.model.prompt_encoder.get_dense_pe(),
            sparse_prompt_embeddings=sparse_embeddings,
            dense_prompt_embeddings=dense_embeddings,
            multimask_output=True,
        )
        
        low_res_pred = torch.sigmoid(low_res_logits)
        upscaled = F.interpolate(low_res_pred, size=(H, W), mode="bilinear", align_corners=False)
        masks = upscaled.squeeze().cpu().numpy()
        
        # Use higher threshold for more precise segmentation
        masks = masks > threshold
        
        return masks

    def _overlay_mask(self, base_image, mask):
        """Overlays a red transparency where mask=255."""
        mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        red_overlay = np.zeros_like(base_image)
        red_overlay[:] = (0, 0, 255)  # BGR for red
        # Keep red only where mask is nonzero
        red_overlay = cv2.bitwise_and(red_overlay, mask_bgr)
        return cv2.addWeighted(base_image, 1.0, red_overlay, 0.4, 0)