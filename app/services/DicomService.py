
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
            body_part_examined = dicom.get("body_part_examined"),
            slice_thickness = dicom.get("slice_thickness"),
            modality = dicom.get("modality"),
            patient_id = dicom.get("patient_id"),
            patient_age = dicom.get("patient_age"),
            patient_sex = dicom.get("patient_sex"),
            series_description = dicom.get("series_description"),
        )

        db.session.add(dicomResource)
        db.session.commit()

        return dicomResource

