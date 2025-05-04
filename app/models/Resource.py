from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.BaseModel import BaseModel
from app.extensions import db

class Resource(BaseModel):
    __tablename__ = "resources"

    id         = Column(Integer, primary_key=True)
    type       = Column(String(25), nullable=False)
    name       = Column(String(50), nullable=False)
    path       = Column(String(256), nullable=False)
    mime       = Column(String(50), nullable=False)

    # Link back to owning user
    owner_id   = Column(Integer, ForeignKey('users.id'), nullable=False)
    owner      = relationship('User', back_populates='resources')

    # Optional link to a dataset
    dataset_id = Column(Integer, ForeignKey('datasets.id'), nullable=True)
    dataset    = relationship('Dataset', back_populates='files')

    # Annotations on this resource
    annotations = relationship(
        'Annotation',
        foreign_keys='Annotation.resource_id',
        back_populates='resource',
        lazy='dynamic'
    )

    def __repr__(self):
        return f"<Resource id={self.id} name={self.name}>"

    def serialize(self):
        return {
            "resource_id": self.id,
            "type": self.type,
            "name": self.name,
            "mime": self.mime,
            "path": self.path,
            "owner_id": self.owner_id,
            "dataset_id": self.dataset_id,
            "annotations": [a.serialize() for a in self.annotations.all()],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
