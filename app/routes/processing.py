from flask import Blueprint, request, jsonify, current_app
import cv2
import numpy as np
from app.services.ContourInterpolationService import ContourInterpolationService
from app.services.FileService import FileService
import pydicom
import os

processing = Blueprint('processing', __name__)

@processing.route('/process/contours/<int:file_id>')
def get_contours(file_id):
    """Get contours for a specific slice using the selected method."""
    method = request.args.get('method', 'adaptive')
    threshold = int(request.args.get('threshold', 50))
    
    # Get the file
    file = FileService.read(file_id)
    if not file:
        return jsonify({'error': 'File not found'}), 404
    
    # Read the DICOM file
    dicom_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.path)
    dicom = pydicom.dcmread(dicom_path)
    image = dicom.pixel_array
    
    # Normalize image
    image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
    image = image.astype(np.uint8)
    
    # Apply selected contour method
    if method == 'adaptive':
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
    elif method == 'canny':
        binary = cv2.Canny(image, threshold, threshold * 2)
    elif method == 'manual':
        _, binary = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
    elif method == 'otsu':
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        return jsonify({'error': 'Invalid contour method'}), 400
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Convert contours to list format
    contour_list = []
    for contour in contours:
        if len(contour) > 2:  # Only include contours with more than 2 points
            contour_list.append(contour.reshape(-1, 2).tolist())
    
    return jsonify({'contours': contour_list})

@processing.route('/process/interpolate-contours', methods=['POST'])
def interpolate_contours():
    """Interpolate contours between two slices."""
    data = request.get_json()
    if not data or 'contour1' not in data or 'contour2' not in data:
        return jsonify({'error': 'Missing contour data'}), 400
    
    contour1 = np.array(data['contour1'])
    contour2 = np.array(data['contour2'])
    
    try:
        # Only interpolate between the two slices, no intermediate slices
        interpolated = ContourInterpolationService.interpolate_between_slices(
            source_slice=0,
            target_slice=1,
            contours={0: contour1, 1: contour2},
            num_intermediate=0  # Set to 0 to disable intermediate slices
        )
        
        # Convert numpy arrays to lists for JSON serialization
        result = {
            'interpolated': [
                contour.tolist() for contour in interpolated.values()
            ]
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@processing.route('/process/mesh/<int:dataset_id>')
def generate_mesh(dataset_id):
    """Generate a 3D mesh from contours."""
    method = request.args.get('method', 'adaptive')
    threshold = int(request.args.get('threshold', 50))
    
    # TODO: Implement mesh generation
    # This would involve:
    # 1. Getting contours for all slices
    # 2. Interpolating between slices
    # 3. Creating a 3D mesh using marching cubes or similar algorithm
    
    return jsonify({
        'error': 'Mesh generation not implemented yet'
    }), 501

@processing.route('/process/volume/<int:dataset_id>')
def reconstruct_volume(dataset_id):
    """Reconstruct a 3D volume from contours."""
    method = request.args.get('method', 'adaptive')
    threshold = int(request.args.get('threshold', 50))
    num_interp = int(request.args.get('num_interp', 0))
    smooth = request.args.get('smooth', 'false').lower() == 'true'
    smooth_factor = float(request.args.get('smooth_factor', 1.0))
    fill_holes = request.args.get('fill_holes', 'false').lower() == 'true'
    
    # TODO: Implement volume reconstruction
    # This would involve:
    # 1. Getting contours for all slices
    # 2. Interpolating between slices
    # 3. Creating a 3D volume
    # 4. Applying smoothing and hole filling if requested
    
    return jsonify({
        'error': 'Volume reconstruction not implemented yet'
    }), 501

@processing.route('/process/export-volume/<int:dataset_id>')
def export_volume(dataset_id):
    """Export the reconstructed volume as STL."""
    # TODO: Implement STL export
    return jsonify({
        'error': 'STL export not implemented yet'
    }), 501 