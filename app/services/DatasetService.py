from app.models.Dataset import Dataset
from app.models.Team import Team
from app.models.TeamUser import TeamUser
from app.services.BaseService import Base

from app.extensions import db


class DatasetService(Base):
    @staticmethod
    def create(params):
        dataset = Dataset(name=params.get("name"), owner_id=params.get("owner_id"), owner_type=params.get("owner_type"))

        db.session.add(dataset)
        db.session.commit()
        return dataset

    @staticmethod
    def read(dataset_id):
        return Dataset.query.get(dataset_id)
    
    @staticmethod
    def read_all(owner_id, owner_type):
        return Dataset.query.filter_by(owner_id=owner_id, owner_type=owner_type).order_by("updated_at").all()

    @staticmethod
    def delete(dataset_id):
        db.session.delete(Dataset.query.get(dataset_id))
        db.session.commit()
        return True