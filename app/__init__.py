from flask import Flask
from config import Config
from app.extensions import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)


    from app.controllers import register_controllers
    register_controllers(app)

    db.init_app(app)
    with app.app_context():
        # db.drop_all()
        db.create_all()
        
    return app