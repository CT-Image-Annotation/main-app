from datetime import datetime
from app.extensions import db
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute

class BaseModel(db.Model):
    __abstract__ = True
    __serialize_exclude__ = []


    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def serialize(self, seen=None):
        if seen is None:
            seen = set()

        identity = (self.__class__, getattr(self, 'id', id(self)))
        if identity in seen:
            return None

        seen.add(identity)
        result = {}
        mapper = inspect(self.__class__)

        for attr in mapper.attrs:
            key = attr.key
            if key in getattr(self, '__serialize_exclude__', []):
                continue

            try:
                value = getattr(self, key)
            except Exception:
                continue

            if hasattr(attr, 'mapper'):
                if attr.uselist:
                    sub = []
                    for v in value:
                        serialized = v.serialize(seen)
                        if serialized is not None:
                            sub.append(serialized)
                    result[key] = sub
                else:
                    if value is not None and hasattr(value, "serialize"):
                        serialized = value.serialize(seen)
                        if serialized is not None:
                            result[key] = serialized
            else:
                result[key] = value

        return result
    
    def __repr__(self):
        pk = getattr(self, 'id', None)
        return f"<{self.__class__.__name__}(id={pk})>"

    def __str__(self):
        return self.__repr__()