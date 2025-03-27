from app.extensions import db
from app.models.BaseModel import BaseModel

class Annotation(BaseModel):
    id = db.Column(db.Integer, primary_key=True)



    annotator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    annotator = db.relationship('User', backref='annotations', lazy=True)
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)