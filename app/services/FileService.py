# from app.models.DatasetModel import DatasetModel
import os
from uuid import uuid4

from flask import current_app, make_response
from app.models.Resource import Resource
from app.services.BaseService import Base
from app.extensions import db
from werkzeug.utils import secure_filename

from app.services.DicomService import DicomService


class FileService(Base):
    @staticmethod
    def upload(file, type):
        path = str(uuid4())
        resource = Resource(
            name=secure_filename(file.filename),
            type=type,
            mime=file.mimetype,
            path=path
            )
        db.session.add(resource)
        db.session.commit()

        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], path))

        if(resource.mime == "application/dicom"):
            DicomService.save(resource)
        else:
            resource.file = FileService.load(resource.path)

        return resource
    
    @staticmethod
    def find(resource_id):
        return Resource.query.filter_by(id=resource_id)
    
    @staticmethod
    def read(resource_id):
        resource = FileService.find(resource_id)
        resource.file = FileService.load(resource.path)
        return resource
    
    @staticmethod
    def load(path):
        with open(os.path.join(current_app.config['UPLOAD_FOLDER'], path), "rb") as f:
            file = f.read()
        return file