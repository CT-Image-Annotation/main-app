
from app.models.User import User
from app.services.BaseService import Base
from flask import session
from app.extensions import db

class UserService(Base):
    @staticmethod
    def login(request):
        username = request.get("username")
        password = request.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
        return user
    
    @staticmethod
    def register(request):
        username = request.get("username")
        password = request.get("password")
        
        username_taken = User.query.filter_by(username=username).first()
        
        if username_taken:
            return False
        else:
            user = User(username=username,password=password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
        return {user}
    
    @staticmethod
    def read(user_id):
        return User.query.filter_by(id=user_id).first()
    
    @staticmethod
    def update(user_id):
        pass

    def delete(user_id):
        return User.query.filter_by(id=user_id).delete()