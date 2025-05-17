from app.extensions import db
from app.models.BaseModel import BaseModel

class Annotation(BaseModel):
    id = db.Column(db.Integer, primary_key=True)



    annotator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    annotator = db.relationship('User', backref='annotations', lazy=True)
    
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    resource = db.relationship('Resource', foreign_keys=[resource_id], back_populates='annotations')

    file_id = db.Column(db.Integer, db.ForeignKey('resources.id'), unique=True)
    file = db.relationship('Resource', backref=db.backref('annotation_file', uselist=False), lazy=True, foreign_keys=[file_id])

    def serialize(self):
        base = self.file.serialize() if self.file else {}
        base.update({
            "annotatee_id": self.resource_id,
            "annotation_id": self.id
        })
        return base