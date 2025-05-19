# app/models/Dataset.py
from app.models.BaseModel import BaseModel
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.extensions import db
from datetime import datetime

class Dataset(BaseModel):
    __tablename__ = 'datasets'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(String(50), nullable=False, default='To Do')  # 'To Do' or 'Done'
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Patient information
    patient_id = Column(String(100), nullable=True)  # Medical record number or patient identifier
    patient_name = Column(String(100), nullable=True)
    patient_dob = Column(DateTime, nullable=True)
    patient_gender = Column(String(10), nullable=True)

    # Scan information
    scan_date = Column(DateTime, nullable=True)
    scan_type = Column(String(50), nullable=True)  # e.g., CT, MRI, etc.
    scan_description = Column(Text, nullable=True)
    scan_series_number = Column(String(50), nullable=True)

    files = relationship('Resource', back_populates='dataset', cascade='all, delete-orphan')
    owner = relationship('User', back_populates='datasets')