from app.extensions import db
from app.models.BaseModel import BaseModel
from app.models.TeamUser import TeamUser

class Team(BaseModel):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    # Many-to-many: users belonging to this team
    users = db.relationship(
        'User', secondary=TeamUser, back_populates='teams', lazy='dynamic'
    )
