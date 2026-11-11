import hashlib
from studentapp import app, db
from studentapp.models import User, UserRoleEnum


def authenticate(username, password):
    hashed_password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
    return User.query.filter(User.username.__eq__(username.strip()), User.password_hash.__eq__(hashed_password)).first()


def get_user_by_id(user_id):
    return User.query.get(user_id)


def create_user(username, password, email, full_name, phone=None, role=UserRoleEnum.EMPLOYEE):
    # Hash the password to match your password_hash column
    password_hash = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
    if isinstance(role, str):
        role = UserRoleEnum(role)

    # Create the user instance with all required schema fields
    u = User(
        username=username.strip(),
        email=email.strip(),
        password_hash=password_hash,
        full_name=full_name.strip(),
        phone=phone.strip() if phone else None,
        role=role
    )

    db.session.add(u)
    db.session.commit()
