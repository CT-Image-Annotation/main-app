from app.extensions import db
from app.models.TeamUser import TeamUser
from .BaseModel import BaseModel
from app.models.Dataset import Dataset
from app.models.Resource import Resource

class User(BaseModel):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    profile_photo = db.Column(db.String(256), nullable=True)    # stores the filename
    specialty     = db.Column(db.String(100), nullable=True)

    # One-to-many: a user owns multiple datasets
    datasets = db.relationship(
        'Dataset', 
        back_populates='owner',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    # One-to-many: a user owns multiple resources (files)
    resources = db.relationship(
        'Resource',
        back_populates='owner',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    # Many-to-many: user memberships in teams
    teams = db.relationship(
        'Team', secondary=TeamUser, back_populates='users'
    )

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"

    def serialize(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": getattr(self, 'email', None),
            "specialty": self.specialty,
            "datasets": [ds.serialize() for ds in self.datasets.all()],
            "resources": [res.serialize() for res in self.resources.all()],
        }
