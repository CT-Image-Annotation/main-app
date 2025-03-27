from app.extensions import db
from app.models.BaseModel import BaseModel

class DicomResource(BaseModel):
    __tablename__ = 'dicom_resources'
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False, primary_key=True)
    resource = db.relationship('Resource', backref='dicom_resources', uselist=False)

    body_part_examined = db.Column(db.String(255))
    slice_thickness = db.Column(db.String(255))
    modality = db.Column(db.String(255))

    patient_id = db.Column(db.String(255))
    patient_age = db.Column(db.String(255))
    patient_sex = db.Column(db.String(255))

    series_description = db.Column(db.String(255))