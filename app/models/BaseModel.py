from datetime import datetime
from flask import abort, session as flask_session
from sqlalchemy import event
from sqlalchemy.orm import Query
from app.extensions import db

class OwnerQuery(Query):
    def get(self, ident):
        obj = super().get(ident)
        if obj and hasattr(obj, 'owner_id'):
            if obj.owner_id != flask_session.get('user_id'):
                abort(403)
        return obj
    
    def get_or_404(self, ident):
        obj = self.get(ident)
        if obj is None:
            abort(404)
        if obj.owner_id != flask_session.get('user_id'):
            abort(403) 
        return obj

    def __iter__(self):
        entity = self._entity_zero()
        model = entity.entity_zero.class_ if entity else None
        if model and hasattr(model, 'owner_id'):
            return super().filter_by(owner_id=flask_session.get('user_id')).__iter__()
        return super().__iter__()

class BaseModel(db.Model):
    __abstract__ = True
    query_class = OwnerQuery

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@event.listens_for(db.session, "before_flush")
def enforce_ownership_before_flush(db_session, flush_context, instances):
    for obj in db_session.dirty.union(db_session.deleted):
        if hasattr(obj, 'owner_id'):
            if obj.owner_id != flask_session.get('user_id'):
                abort(403)