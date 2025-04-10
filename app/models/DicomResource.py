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

    def serialize(self):
        base = self.resource.serialize() if self.resource else {}

        dicom_fields = {
            "body_part_examined": self.body_part_examined,
            "slice_thickness": self.slice_thickness,
            "modality": self.modality,
            "patient_id": self.patient_id,
            "patient_age": self.patient_age,
            "patient_sex": self.patient_sex,
            "series_description": self.series_description
        }

        base.update(dicom_fields)
        return base