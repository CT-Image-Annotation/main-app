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
    def allowed_file(filename):
        """Check if the file extension is allowed."""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

    @staticmethod
    def upload(file, type, dataset_id=None):
        """
        Save an uploaded file; optionally associate it with a dataset.
        """
        if not file or not file.filename:
            raise ValueError("No file provided")

        if not FileService.allowed_file(file.filename):
            raise ValueError(f"File type not allowed. Allowed types: {', '.join(current_app.config['ALLOWED_EXTENSIONS'])}")

        # Secure original filename and extract extension
        original_name = secure_filename(file.filename)
        _, ext = os.path.splitext(original_name)
        # Generate unique filename with same extension
        unique_name = f"{uuid4()}{ext}"

        # Create resource record with owner and dataset info
        resource = Resource(
            name=file.filename,
            type=type,
            mime=file.mimetype,
            path=unique_name,
            owner_id=session.get('user_id'),
            dataset_id=dataset_id
        )
        db.session.add(resource)
        db.session.commit()

        # Determine save folder (root or dataset subfolder)
        base_folder = current_app.config['UPLOAD_FOLDER']
        if dataset_id:
            base_folder = os.path.join(base_folder, str(dataset_id))
        os.makedirs(base_folder, exist_ok=True)

        # Save file to disk under the generated name
        file_path = os.path.join(base_folder, unique_name)
        file.save(file_path)

        # DICOM processing
        if ext.lower() in ['.dcm', '.dicom'] or file.mimetype == "application/dicom":
            DicomService.save(resource)
        return resource

    @staticmethod
    def find(resource_id):
        return Resource.query.get(resource_id)

    @staticmethod
    def load(path, dataset_id=None):
        # Load binary data from disk
        base_folder = current_app.config['UPLOAD_FOLDER']
        if dataset_id:
            base_folder = os.path.join(base_folder, str(dataset_id))
        full_path = os.path.join(base_folder, path)
        with open(full_path, "rb") as f:
            return f.read()

    @staticmethod
    def read(resource_id):
        resource = Resource.query.get(resource_id)
        if resource and (resource.mime == "application/dicom" or resource.path.lower().endswith(('.dcm', '.dicom'))):
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
        # Delete DICOM if applicable
        if resource.mime == "application/dicom" or resource.path.lower().endswith(('.dcm', '.dicom')):
            dicom_res = DicomService.read(resource_id)
            if dicom_res:
                db.session.delete(dicom_res)

        # Remove DB record
        db.session.delete(resource)
        db.session.commit()

        # Remove file from disk
        base_folder = current_app.config['UPLOAD_FOLDER']
        if resource.dataset_id:
            base_folder = os.path.join(base_folder, str(resource.dataset_id))
        filepath = os.path.join(base_folder, resource.path)
        if os.path.exists(filepath):
            os.remove(filepath)

        return True

    @staticmethod
    def getUserFiles(type="AImage", dataset_id=None):
        user = UserService.currentUser()
        if not user:
            return []
        query = user.resources.filter_by(type=type)
        if dataset_id is not None:
            query = query.filter_by(dataset_id=dataset_id)
        return query.all()
