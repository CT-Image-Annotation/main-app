from app.models.BaseModel import BaseModel
from app.extensions import db

class Resource(BaseModel):
    __tablename__ = "resources"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(25), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    path = db.Column(db.String(50), nullable=False)
    mime = db.Column(db.String(10), nullable=False)

    owner_id = db.Column(db.Integer, nullable=False)
    owner_type = db.Column(db.String(4), nullable=False)

    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset.id'), nullable=True)

    annotations = db.relationship('Annotation', backref='resource', lazy=True)

    def __repr__(self):
        return f"<Resource {self.id} ({self.type})>"