# from app.models.DatasetModel import DatasetModel
import os
from uuid import uuid4

from flask import current_app, session
from app.models.Resource import Resource
from app.services.AnnotationService import AnnotationService
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
            path=path,
            owner_id = session.get('user_id'),
            owner_type = "user"
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
    def load(path):
        with open(os.path.join(current_app.config['UPLOAD_FOLDER'], path), "rb") as f:
            file = f.read()
        return file
    
    @staticmethod
    def create(params):
        file = params.get("file")

        path = str(uuid4())
        resource = Resource(
            name=secure_filename(file.filename),
            type=params.get("type"),
            mime=file.mimetype,
            path=path,
            owner_id = params.get("owner_id"),
            owner_type = params.get("owner_type"),
            dataset_id = params.get("dataset_id"),
            )
        db.session.add(resource)
        db.session.commit()

        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], path))

        if(resource.mime == "application/dicom"):
            return DicomService.save(resource)
        
        return resource

    @staticmethod
    def read(resource_id):
        image = Resource.query.get(resource_id)

        if(image.mime=="application/dicom"):
            return DicomService.read(resource_id)
        return image

    @staticmethod
    def update():
        pass

    @staticmethod
    def delete(resource_id):
        resource = Resource.query.get(resource_id)

        if(resource.mime=="application/dicom"):
            dicomResource = DicomService.read(resource_id)
            db.session.delete(dicomResource)

        db.session.delete(resource)
        
        db.session.commit()

        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], resource.path)
        os.remove(filepath)

        return True