
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
            BodyPartExamined = dicom.get("BodyPartExamined"),
            SliceThickness = dicom.get("SliceThickness"),
            Modality = dicom.get("Modality"),
            PatientID = dicom.get("PatientID"),
            PatientAge = dicom.get("PatientAge"),
            PatientSex = dicom.get("PatientSex"),
            SeriesDescription = dicom.get("SeriesDescription"),
        )

        db.session.add(dicomResource)
        db.session.commit()

        return dicomResource

