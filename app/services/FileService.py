import os

from flask import current_app
# from app.models.DatasetModel import DatasetModel
from app.models.ImageModel import ImageModel
from app.services.BaseService import Base
from app import db
from werkzeug.utils import secure_filename


class FileService(Base):
    @staticmethod
    def upload(file):
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        db.session.add(ImageModel(path=filename))
        # db.session.add(DatasetModel(name="hi"))
        db.session.commit()
        return {}