from app.extensions import db

TeamUser = db.Table(
    "team_user",
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

# class TeamUser(BaseModel):
#     __tablename__ = "team_user"
#     team_id = db.Column('team_id', db.Integer, db.ForeignKey('teams.id'), primary_key=True)
#     user_id = db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
