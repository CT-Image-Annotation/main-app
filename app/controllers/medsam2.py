
from re import L
from flask import Blueprint, request
import os
import requests

from app.controllers import processing

bp = Blueprint("medsam2", __name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:5001")

@bp.route("/predict_combined", methods=["POST"])
def predict_combined():
    data = request.json
    response = requests.post(f"{AI_SERVICE_URL}/medsam2/predict_combined", json=data)
    return response.json()

@bp.route("/predict_video", methods=["POST"])
def predict_video():
    req_data = request.json
    image_ids = req_data.get('image_ids', [])
    zip_stream = processing.image_multiple(image_ids)

    post_body = {
        'x': 0
    }

    files = {
        'zip': ('images.zip', zip_stream, 'application/zip')
    }
    response = requests.post(f"{AI_SERVICE_URL}/medsam3d/run", files=files, data=post_body )

    # Return AI service response
    return response.json()
