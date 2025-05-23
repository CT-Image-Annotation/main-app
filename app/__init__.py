from dotenv import load_dotenv
load_dotenv()   # <-- this reads .env into os.environ

from flask import Flask
from config import Config
from app.extensions import db
from flask_migrate import Migrate
import os

migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions first
    db.init_app(app)
    migrate.init_app(app, db)

    # Ensure all models and association tables are imported so Alembic sees them
    from app.models.User import User
    from app.models.Team import Team
    from app.models.TeamUser import TeamUser
    from app.models.Dataset import Dataset
    from app.models.Resource import Resource
    from app.models.Annotation import Annotation

    # Register blueprints/controllers after db initialization
    from app.controllers import register_controllers, landing
    register_controllers(app)

    @app.cli.command("download-medsam")
    def download_medsam():
        """Download the MedSAM model."""
        with app.app_context():
            from app.services.download_medsam import download_medsam_model
            download_medsam_model()

    return app
