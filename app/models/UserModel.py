from app.extensions import db
from .BaseModel import BaseModel

class UserModel(BaseModel):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30))
    password = db.Column(db.String(30))
    
    def __repr__(self):
        return f"User(id={self.id})"
    
    def __str__(self):
        return f"User(id={self.id})"