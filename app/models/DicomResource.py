from app.extensions import db
from app.models.BaseModel import BaseModel
from app.models.Resource import Resource

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
    
    @property
    def name(self):
        return self.resource.name

    @property
    def path(self):
        return self.resource.path

    @property
    def mime(self):
        return self.resource.mime

    @property
    def owner_id(self):
        return self.resource.owner_id

    @property
    def owner_type(self):
        return self.resource.owner_type

    @property
    def dataset_id(self):
        return self.resource.dataset_id

    @property
    def annotations(self):
        return self.resource.annotations