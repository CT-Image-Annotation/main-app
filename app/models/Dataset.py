from app.models.BaseModel import BaseModel
from app.extensions import db

class Dataset(BaseModel):
    __tablename__ = "datasets"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    owner_id = db.Column(db.Integer, nullable=False) 
    owner_type = db.Column(db.String(4), nullable=False)

    resources = db.relationship('Resource', backref='dataset', lazy=True)

    def serialize(self):
        return {
            "dataset_id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type,
        }