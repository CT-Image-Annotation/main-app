
import os
from flask import current_app
from app.models.DicomResource import DicomResource
from app.services.BaseService import Base
from app.extensions import db
import pydicom

class DicomService(Base):
    
    @staticmethod
    def save(resource):
        dicom = pydicom.dcmread(os.path.join(current_app.config['UPLOAD_FOLDER'], resource.path))
        dicomResource = DicomResource(
            resource_id = resource.id,
            body_part_examined = dicom.get("BodyPartExamined"),
            slice_thickness = dicom.get("SliceThickness"),
            modality = dicom.get("Modality"),
            patient_id = dicom.get("PatientID"),
            patient_age = dicom.get("PatientAge"),
            patient_sex = dicom.get("PatientSex"),
            series_description = dicom.get("SeriesDescription"),
        )

        db.session.add(dicomResource)
        db.session.commit()

        return dicomResource

    @staticmethod
    def read(resource_id):
        return DicomResource.query.get(resource_id)