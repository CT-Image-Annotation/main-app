# app/models/Dataset.py
from app.models.BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.extensions import db

class Dataset(BaseModel):
    __tablename__ = 'datasets'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(String(50), nullable=False, default='To Do')  # 'To Do' or 'Done'
    owner_id    = Column(Integer, ForeignKey('users.id'), nullable=False)

    files       = relationship('Resource', back_populates='dataset', cascade='all, delete-orphan')
    owner       = relationship('User', back_populates='datasets')