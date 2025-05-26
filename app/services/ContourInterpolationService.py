import numpy as np
from scipy.interpolate import interp1d
import cv2
from typing import List, Tuple, Dict
import pydicom
from app.services.BaseService import Base

class ContourInterpolationService(Base):
    @staticmethod
    def interpolate_contour(source_contour: np.ndarray, target_contour: np.ndarray, 
                          num_points: int = 100) -> np.ndarray:
        """
        Interpolate between two contours using linear interpolation.
        
        Args:
            source_contour: Source contour points (N x 2 array)
            target_contour: Target contour points (N x 2 array)
            num_points: Number of points in the interpolated contour
            
        Returns:
            Interpolated contour points
        """
        # Ensure contours have the same number of points
        if len(source_contour) != len(target_contour):
            source_contour = cv2.approxPolyDP(source_contour, 0.02 * cv2.arcLength(source_contour, True), True)
            target_contour = cv2.approxPolyDP(target_contour, 0.02 * cv2.arcLength(target_contour, True), True)
            
            # Resample both contours to have the same number of points
            source_contour = cv2.approxPolyDP(source_contour, 0.02 * cv2.arcLength(source_contour, True), True)
            target_contour = cv2.approxPolyDP(target_contour, 0.02 * cv2.arcLength(target_contour, True), True)
            
            if len(source_contour) != len(target_contour):
                # If still different, use the minimum number of points
                min_points = min(len(source_contour), len(target_contour))
                source_contour = source_contour[:min_points]
                target_contour = target_contour[:min_points]

        # Create interpolation functions for x and y coordinates
        t = np.linspace(0, 1, len(source_contour))
        fx = interp1d(t, source_contour[:, 0])
        fy = interp1d(t, source_contour[:, 1])
        gx = interp1d(t, target_contour[:, 0])
        gy = interp1d(t, target_contour[:, 1])

        # Generate interpolated points
        t_new = np.linspace(0, 1, num_points)
        interpolated = np.column_stack((
            fx(t_new),
            fy(t_new)
        ))

        return interpolated

    @staticmethod
    def interpolate_between_slices(source_slice, target_slice, contours, num_intermediate=0):
        """
        Interpolate contours between two slices.
        
        Args:
            source_slice: Index of the source slice
            target_slice: Index of the target slice
            contours: Dictionary mapping slice indices to contour points
            num_intermediate: Not used, kept for backward compatibility
        """
        if source_slice not in contours or target_slice not in contours:
            raise ValueError("Both source and target slices must have contours")
        
        source_contour = contours[source_slice]
        target_contour = contours[target_slice]
        
        # Ensure both contours have the same number of points
        if len(source_contour) != len(target_contour):
            source_contour = ContourInterpolationService.resample_contour(source_contour, len(target_contour))
        
        # Return only the source and target contours
        return {
            source_slice: source_contour,
            target_slice: target_contour
        }

    @staticmethod
    def visualize_interpolated_contours(dicom_slice: pydicom.Dataset, 
                                      contours: Dict[int, np.ndarray],
                                      alpha: float = 0.5) -> np.ndarray:
        """
        Visualize interpolated contours on a DICOM slice.
        
        Args:
            dicom_slice: DICOM dataset for the slice
            contours: Dictionary mapping slice numbers to contour points
            alpha: Transparency of the overlay
            
        Returns:
            RGB image with contours overlaid
        """
        # Convert DICOM to image
        image = dicom_slice.pixel_array
        image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
        image = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_GRAY2RGB)
        
        # Create overlay
        overlay = image.copy()
        
        # Draw contours
        for slice_num, contour in contours.items():
            contour = contour.astype(np.int32)
            cv2.drawContours(overlay, [contour], -1, (0, 255, 0), 2)
        
        # Blend overlay with original image
        result = cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0)
        
        return result 