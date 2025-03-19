from app.extensions import db
from app.models.BaseModel import BaseModel

class Dicom(BaseModel):
    __tablename__ = 'dicom_resources'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, primary_key=True)
    resource = db.relationship('ResourceModel', backref='dicom_resources', uselist=False)