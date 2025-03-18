# from app.models.BaseModel import BaseModel
# from app.extensions import db


# class DatasetModel(BaseModel):
#     __tablename__ = "datasets"
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(30))
    
#     images = db.relationship('Image', back_populates='dataset', cascade="all, delete-orphan")