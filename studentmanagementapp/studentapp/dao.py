import hashlib
from studentapp import app, db
from studentapp.models import User

def authenticate(username, password):
    password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
    return User.query.filter(User.username.__eq__(username.strip()), User.password.__eq__(password)).first()


def get_user_by_id(user_id):
    return User.query.get(user_id)

def create_user( username, password, user_role='EMPLOYEE'):
    password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
    u = User( username=username.strip(), password=password,user_role=user_role)


    db.session.add(u)
    db.session.commit()
