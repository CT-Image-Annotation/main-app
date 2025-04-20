import os
from uuid import uuid4

from flask import current_app, session
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.Resource import Resource
from app.services.BaseService import Base
from app.services.DicomService import DicomService


class FileService(Base):
    @staticmethod
    def upload(file, type):
        # Secure original filename and extract extension
        original_name = secure_filename(file.filename)
        _, ext = os.path.splitext(original_name)
        # Generate unique filename with same extension
        unique_name = f"{uuid4()}{ext}"

        # Create resource record with owner info
        resource = Resource(
            name=original_name,
            type=type,
            mime=file.mimetype,
            path=unique_name,
            owner_id=session.get('user_id'),
            owner_type="user"
        )
        db.session.add(resource)
        db.session.commit()

        # Ensure upload folder exists
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        # Save file to disk under the generated name
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name))

        # If DICOM, delegate to DicomService; otherwise preload file bytes
        if resource.mime == "application/dicom":
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
            return f.read()

    @staticmethod
    def create(params):
        file = params.get("file")
        original_name = secure_filename(file.filename)
        _, ext = os.path.splitext(original_name)
        unique_name = f"{uuid4()}{ext}"

        resource = Resource(
            name=original_name,
            type=params.get("type"),
            mime=file.mimetype,
            path=unique_name,
            owner_id=params.get("owner_id"),
            owner_type=params.get("owner_type"),
            dataset_id=params.get("dataset_id")
        )
        db.session.add(resource)
        db.session.commit()

        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name))

        if resource.mime == "application/dicom":
            return DicomService.save(resource)
        return resource

    @staticmethod
    def read(resource_id):
        image = Resource.query.get(resource_id)
        if image.mime == "application/dicom":
            return DicomService.read(resource_id)
        return image

    @staticmethod
    def update():
        pass

    @staticmethod
    def delete(resource_id):
        resource = Resource.query.get(resource_id)
        if resource.mime == "application/dicom":
            dicom_res = DicomService.read(resource_id)
            db.session.delete(dicom_res)

        db.session.delete(resource)
        db.session.commit()

        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], resource.path)
        if os.path.exists(filepath):
            os.remove(filepath)

        return True
