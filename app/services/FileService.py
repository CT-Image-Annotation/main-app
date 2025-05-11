import os
from uuid import uuid4

from flask import current_app, session
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.Resource import Resource
from app.services.DicomService import DicomService
from app.services.UserService import UserService

class FileService:
    @staticmethod
    def create(params):
        file = params.get("file")
        if not file:
            return False
        path = str(uuid4())

        resource = Resource(
            name=secure_filename(file.filename),
            type=params.get("type"),
            mime=file.mimetype,
            path=path,
            owner_id=params.get("owner_id"),
            owner_type=params.get("owner_type"),
            dataset_id=params.get("dataset_id")
        )
        db.session.add(resource)
        db.session.commit()

        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], path))

        if resource.mime == "application/dicom":
            return DicomService.save(resource)
        return resource

    @staticmethod
    def find(resource_id):
        return Resource.query.get(resource_id)

    @staticmethod
    def load(path):
        with open(os.path.join(current_app.config['UPLOAD_FOLDER'], path), "rb") as f:
            return f.read()

    @staticmethod
    def read(resource_id):
        resource = Resource.query.get(resource_id)
        if resource and (resource.mime == "application/dicom"):
            return DicomService.read(resource_id)
        return resource

    @staticmethod
    def update():
        # Not implemented
        pass

    @staticmethod
    def delete(resource_id):
        resource = Resource.query.get(resource_id)
        if not resource:
            return False

        if resource.mime == "application/dicom":
            dicom_res = DicomService.read(resource_id)
            if dicom_res:
                db.session.delete(dicom_res)

        db.session.delete(resource)
        db.session.commit()

        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], resource.path))
        return True

    @staticmethod
    def getUserFiles(type="AImage"):
        user = UserService.currentUser()
        if not user:
            return []
        
        return user.resources.filter_by(type=type).all()
