from app.extensions import db
from app.models.TeamUser import TeamUser
from .BaseModel import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30))
    password = db.Column(db.String(30))

    datasets = db.relationship(
        'Dataset', 
        backref='owner', 
        lazy=True, 
        primaryjoin="and_(User.id == foreign(Dataset.owner_id), Dataset.owner_type == 'user')"
    )

    def __repr__(self):
        return f"User(id={self.id})"
    
    def __str__(self):
        return f"User(id={self.id})"