from flask import Flask
from app.controllers.auth import bp as auth_bp
from app.controllers.api import bp as api_bp
from app.controllers.dashboard import bp as dashboard_bp
from app.controllers.datasets import bp as datasets_bp
from app.controllers.landing import bp as landing_bp
from app.controllers.editor import bp as editor_bp

def register_controllers(app: Flask):
    app.register_blueprint(auth_bp)
    app.register_blueprint(landing_bp)

    app.register_blueprint(api_bp, url_prefix="/API")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(datasets_bp, url_prefix="/datasets")
    app.register_blueprint(editor_bp, url_prefix="/editor")


    