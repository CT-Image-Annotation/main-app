from app.models.BaseModel import BaseModel
from app.extensions import db
from app.models.Ownable import Ownable

class Resource(BaseModel, Ownable):
    __tablename__ = "resources"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(25), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    path = db.Column(db.String(50), nullable=False)
    mime = db.Column(db.String(25), nullable=False)

    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=True)
    dataset    = db.relationship('Dataset', back_populates='resources')

    annotations = db.relationship('Annotation', foreign_keys='Annotation.resource_id', back_populates='resource', lazy="dynamic")

