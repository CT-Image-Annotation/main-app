from app.extensions import db
from app.models.Team import Team
from app.models.User import User

class Ownable:
    owner_id = db.Column(db.Integer, nullable=False)
    owner_type = db.Column(db.String(4), nullable=False)

    @property
    def owner(self):
        if self.owner_type == "user":
            return db.session.get(User, self.owner_id)
        elif self.owner_type == "team":
            return db.session.get(Team, self.owner_id)
        return None

    @owner.setter
    def owner(self, obj):
        if isinstance(obj, User):
            self.owner_type = "user"
        elif isinstance(obj, Team):
            self.owner_type = "team"
        else:
            raise ValueError("Invalid owner type")
        self.owner_id = obj.id
