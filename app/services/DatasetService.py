from app.models.Dataset import Dataset
from app.extensions import db
from datetime import datetime

class DatasetService:
    @staticmethod
    def create(params, owner_id):
        """
        Create a new dataset owned by the given user.
        params: dict with keys 'name', 'description', 'tags', 'patient_id', 'patient_name',
               'patient_dob', 'patient_gender', 'scan_date', 'scan_type', 'scan_description',
               'scan_series_number'
        owner_id: int user ID
        """
        # Convert date strings to datetime objects if provided
        patient_dob = None
        if params.get('patient_dob'):
            try:
                patient_dob = datetime.strptime(params.get('patient_dob'), '%Y-%m-%d')
            except ValueError:
                pass

        scan_date = None
        if params.get('scan_date'):
            try:
                scan_date = datetime.strptime(params.get('scan_date'), '%Y-%m-%d')
            except ValueError:
                pass

        ds = Dataset(
            name=params.get('name'),
            description=params.get('description'),
            tags=params.get('tags', 'To Do'),
            owner_id=owner_id,
            patient_id=params.get('patient_id'),
            patient_name=params.get('patient_name'),
            patient_dob=patient_dob,
            patient_gender=params.get('patient_gender'),
            scan_date=scan_date,
            scan_type=params.get('scan_type'),
            scan_description=params.get('scan_description'),
            scan_series_number=params.get('scan_series_number')
        )
        db.session.add(ds)
        db.session.commit()
        return ds

    @staticmethod
    def list_for_user(owner_id):
        """
        Return all datasets belonging to a user, most-recently updated first.
        """
        return (
            Dataset.query
                   .filter_by(owner_id=owner_id)
                   .order_by(Dataset.updated_at.desc())
                   .all()
        )

    @staticmethod
    def read_for_user(dataset_id, owner_id):
        """
        Return a single dataset if it belongs to the user, else None.
        """
        return (
            Dataset.query
                   .filter_by(id=dataset_id, owner_id=owner_id)
                   .first()
        )

    @staticmethod
    def update_for_user(dataset_id, owner_id, params):
        """
        Update dataset fields if owned by user.
        """
        ds = DatasetService.read_for_user(dataset_id, owner_id)
        if not ds:
            return None

        # Update basic fields
        ds.name = params.get('name', ds.name)
        ds.description = params.get('description', ds.description)
        ds.tags = params.get('tags', ds.tags)

        # Update patient information
        ds.patient_id = params.get('patient_id', ds.patient_id)
        ds.patient_name = params.get('patient_name', ds.patient_name)
        if params.get('patient_dob'):
            try:
                ds.patient_dob = datetime.strptime(params.get('patient_dob'), '%Y-%m-%d')
            except ValueError:
                pass
        ds.patient_gender = params.get('patient_gender', ds.patient_gender)

        # Update scan information
        if params.get('scan_date'):
            try:
                ds.scan_date = datetime.strptime(params.get('scan_date'), '%Y-%m-%d')
            except ValueError:
                pass
        ds.scan_type = params.get('scan_type', ds.scan_type)
        ds.scan_description = params.get('scan_description', ds.scan_description)
        ds.scan_series_number = params.get('scan_series_number', ds.scan_series_number)

        db.session.commit()
        return ds

    @staticmethod
    def delete_for_user(dataset_id, owner_id):
        """
        Delete the dataset if owned by the user. Returns True if deleted, False otherwise.
        """
        ds = DatasetService.read_for_user(dataset_id, owner_id)
        if not ds:
            return False
        db.session.delete(ds)
        db.session.commit()
        return True
