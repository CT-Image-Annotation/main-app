from flask import Blueprint, jsonify, render_template, session, request, redirect, url_for

from app.services.DatasetService import DatasetService

bp = Blueprint("datasets", __name__)

@bp.route('/')
def index():
    return render_template('datasets/index.html')
