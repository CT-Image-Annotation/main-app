from flask import Flask
from app.controllers.auth import bp as auth_bp
from app.controllers.uploads import bp as uploads_bp
from app.controllers.processing import bp as processing_bp
from app.controllers.api import bp as api_bp
from app.controllers.dashboard import bp as dashboard_bp
from app.controllers.datasets import bp as datasets_bp
from app.controllers.landing import bp as landing_bp
from app.controllers.medsam2 import bp as medsam2_bp

def register_controllers(app: Flask):
    app.register_blueprint(auth_bp)
    app.register_blueprint(uploads_bp, url_prefix='/uploads')
    app.register_blueprint(processing_bp, url_prefix='/process')
    app.register_blueprint(api_bp, url_prefix = "/api")
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(datasets_bp, url_prefix = "/datasets")
    app.register_blueprint(landing_bp)
    app.register_blueprint(medsam2_bp, url_prefix = "/medsam2")


    