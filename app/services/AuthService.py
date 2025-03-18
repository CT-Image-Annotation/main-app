
from app.services.BaseService import Base


class AuthService(Base):
    @staticmethod
    def isAllowed():
        return True