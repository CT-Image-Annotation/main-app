
from flask import Blueprint, request
import os
import requests

bp = Blueprint("medsam2", __name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:5001")

@bp.route("/predict_combined", methods=["POST"])
def predict_combined():
    data = request.json
    response = requests.post(f"{AI_SERVICE_URL}/medsam2/predict_combined", json=data)
    return response.json()