from app.extensions import db
from app.models.BaseModel import BaseModel

class DicomResource(BaseModel):
    __tablename__ = 'dicom_resources'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, primary_key=True)
    resource = db.relationship('Resource', backref='dicom_resources', uselist=False)

    BodyPartExamined = db.Column(db.String(255))
    SliceThickness = db.Column(db.String(255))
    Modality = db.Column(db.String(255))

    PatientID = db.Column(db.String(255))
    PatientAge = db.Column(db.String(255))
    PatientSex = db.Column(db.String(255))

    SeriesDescription = db.Column(db.String(255))