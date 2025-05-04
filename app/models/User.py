from app.extensions import db
from app.models.TeamUser import TeamUser
from .BaseModel import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30))
    password = db.Column(db.String(30))
    profile_photo = db.Column(db.String(256), nullable=True)    # stores the filename or URL
    specialty     = db.Column(db.String(100), nullable=True)
    
    datasets = db.relationship(
        'Dataset', 
        backref='owner', 
        lazy="dynamic", 
        primaryjoin="and_(User.id == foreign(Dataset.owner_id), Dataset.owner_type == 'user')"
    )

    resources = db.relationship(
        'Resource', 
        backref='owner', 
        lazy="dynamic", 
        primaryjoin="and_(User.id == foreign(Resource.owner_id), Resource.owner_type == 'user')"
    )

    teams = db.relationship('Team', secondary=TeamUser, backref='users')

    def __repr__(self):
        return f"User(id={self.id})"
    
    def __str__(self):
        return f"User(id={self.id})"
    
    def serialize(self):
        return {
            "user_id": self.id,
            "username": self.username,
            "datasets": [r.serialize() for r in self.datasets.all()],
            "resources": [r.serialize() for r in self.resources.all()],
            "teams": self.teams,
        }