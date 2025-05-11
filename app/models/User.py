from app.extensions import db
from app.models.TeamUser import TeamUser
from .BaseModel import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    __serialize_exclude__ = ['password']
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30))
    password = db.Column(db.String(30))
    specialty = db.Column(db.String(100), nullable=True)

    datasets = db.relationship(
        'Dataset', 
        backref='owner', 
        lazy="dynamic", 
        primaryjoin="and_(User.id == foreign(Dataset.owner_id), Dataset.owner_type == 'user')",
        cascade="all, delete-orphan"
    )

    resources = db.relationship(
        'Resource', 
        backref='owner', 
        lazy="dynamic", 
        primaryjoin="and_(User.id == foreign(Resource.owner_id), Resource.owner_type == 'user')",
        cascade="all, delete-orphan"
    )

    teams = db.relationship('Team', secondary=TeamUser, back_populates='users')