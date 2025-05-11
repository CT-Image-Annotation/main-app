from app.models.Dataset import Dataset
from app.extensions import db

class DatasetService:
    @staticmethod
    def create(params):
        ds = Dataset(
            name=params.get('name'),
            description=params.get('description'),
            status=params.get('status', 'todo'), #todo or done
            owner_id=params.get('owner_id'),
            owner_type=params.get('owner_type')
        )
        db.session.add(ds)
        db.session.commit()
        return ds

    @staticmethod
    def read(dataset_id):
        return Dataset.query.get(dataset_id)
    
    @staticmethod
    def read_all(owner_id, owner_type, filters = None):
        conditions = [Dataset.owner_id == owner_id, Dataset.owner_type == owner_type]
    
        if filters:
            conditions.extend(filters)
        return Dataset.query.filter(*conditions).order_by(Dataset.updated_at.desc()).all()

    @staticmethod
    def update(params):
        if not params.get('dataset_id'):
            return False
        ds = DatasetService.read(params.get('dataset_id'))

        if name := params.get('name'):
            ds.name = name
        if description := params.get('description'):
            ds.description = description
        if status := params.get('status'):
            ds.status = status
        
        db.session.commit()
        return ds

    @staticmethod
    def delete(dataset_id):
        db.session.delete(Dataset.query.get(dataset_id))
        db.session.commit()
        return True


