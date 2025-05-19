import random
from flask import session

from app.models.Annotation import Annotation
from app.services.BaseService import Base

from app.extensions import db
from app.services.FileService import FileService


class AnnotationService(Base):
    @staticmethod
    def create(params):

        resource = FileService.read(params.get("resource_id"))
        if not resource:
            return None
        if not params.get("file"):
            return None
        
        fileParams = {
            "type": "annotation",
            "owner_id": session.get('user_id'),
            "file": params.get("file"),
            "dataset_id": resource.dataset_id,
            "name": resource.name + str(random.randint(0,2048)) + "annotation"
        }
        annotation_file = FileService.create(fileParams)

        annotation = Annotation(
            annotator_id=session.get('user_id'),
            resource_id=params.get("resource_id"),
            file_id=annotation_file.id,
        )
        
        db.session.add(annotation)
        db.session.commit()
        return annotation
    
    @staticmethod
    def read(annotation_id):
        return Annotation.query.get(annotation_id)
    
    @staticmethod
    def read_last(resource_id):
        resource = FileService.read(resource_id)

        last_annotation = resource.annotations.order_by(Annotation.updated_at.desc()).first()
        return last_annotation
        