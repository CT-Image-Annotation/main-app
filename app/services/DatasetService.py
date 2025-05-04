from app.models.Dataset import Dataset
from app.extensions import db

class DatasetService:
    @staticmethod
    def create(params, owner_id):
        """
        Create a new dataset owned by the given user.
        params: dict with keys 'name', 'description', 'tags'
        owner_id: int user ID
        """
        ds = Dataset(
            name=params.get('name'),
            description=params.get('description'),
            tags=params.get('tags', 'To Do'),
            owner_id=owner_id
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
        Update name, description, and tags for a dataset if owned by user.
        """
        ds = DatasetService.read_for_user(dataset_id, owner_id)
        if not ds:
            return None
        ds.name = params.get('name', ds.name)
        ds.description = params.get('description', ds.description)
        ds.tags = params.get('tags', ds.tags)
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
