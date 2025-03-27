from flask import Flask
from .auth import bp as auth_bp
from .landing import bp as landing_bp
from .dashboard import bp as dashboard_bp
from .datasets import bp as datasets_bp
from .uploads import bp as uploads_bp


def register_controllers(app: Flask):
    app.register_blueprint(auth_bp)
    app.register_blueprint(landing_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(datasets_bp, url_prefix="/datasets")
    
    
    app.register_blueprint(uploads_bp, url_prefix="/uploads")

    