from app.models.BaseModel import BaseModel
from app.extensions import db
from app.models.Ownable import Ownable

class Dataset(BaseModel, Ownable):
    __tablename__ = "datasets"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(4), nullable=False, default='todo')

    resources = db.relationship('Resource', back_populates='dataset', lazy=True, cascade='all, delete-orphan')