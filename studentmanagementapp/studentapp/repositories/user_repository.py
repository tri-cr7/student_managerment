"""Repositories."""
from sqlalchemy.exc import IntegrityError

from studentapp.extensions import db
from studentapp.models.user import User
from studentapp.exceptions import DuplicateError


def get_by_id(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, uid)


def get_by_username(username):
    username = (username or "").strip()
    if not username:
        return None
    return User.query.filter_by(username=username).first()


def get_by_email(email):
    email = (email or "").strip()
    if not email:
        return None
    return User.query.filter_by(email=email).first()


def list_all():
    return User.query.order_by(User.id.desc()).all()


def add(user):
    db.session.add(user)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        raise DuplicateError("Username/Email đã tồn tại.")
    return user
