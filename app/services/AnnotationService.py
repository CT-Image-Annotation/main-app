from flask import session

from app.models.Annotation import Annotation
from app.services.BaseService import Base

from app.extensions import db


class AnnotationService(Base):
    @staticmethod
    def create(resource_id):
        annotation = Annotation(annotator_id=session.get('user_id'), resource_id=resource_id)
        db.session.add(annotation)
        db.session.commit()
        return annotation