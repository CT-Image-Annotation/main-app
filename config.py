import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    MEDSAM_CHECKPOINT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'medsam_vit_h.pth')
    
    MEDSAM_PATH = os.path.join(basedir, "app/vendors/MedSAM")

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'dcm', 'dicom'}

