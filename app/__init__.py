from dotenv import load_dotenv
load_dotenv()   # <-- this reads .env into os.environ

from flask import Flask
from config import Config
from app.extensions import db
from flask_migrate import Migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure all models and association tables are imported so Alembic sees them
    from app.models.User import User
    from app.models.Team import Team
    from app.models.TeamUser import TeamUser
    from app.models.Dataset import Dataset
    from app.models.Resource import Resource
    from app.models.Annotation import Annotation

    # Register blueprints/controllers
    from app.controllers import register_controllers
    register_controllers(app)

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)

    return app
