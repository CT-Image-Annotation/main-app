from app.extensions import db
from .BaseModel import BaseModel

class ImageModel(BaseModel):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(30))
    # dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)

    # dataset = db.relationship('Dataset', back_populates='images', lazy='noload')