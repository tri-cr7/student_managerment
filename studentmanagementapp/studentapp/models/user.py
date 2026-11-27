import datetime
import enum
import hashlib

import bcrypt
from flask_login import UserMixin
from werkzeug.security import check_password_hash as wz_check

from studentapp.extensions import db

def _lock_duration_minutes() -> int:

    try:
        from studentapp.repositories import system_rule_repository as rules

        return max(1, int(rules.get_int("LOCK_DURATION_MINUTES", 30)))
    except Exception:
        return 30

class UserRoleEnum(enum.Enum):
    STAFF = "STAFF"
    TEACHER = "TEACHER"
    ACADEMIC = "ACADEMIC"

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    role = db.Column(db.Enum(UserRoleEnum), nullable=False)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)

    locked_at = db.Column(db.TIMESTAMP, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    def set_password(self, raw: str):
        raw = (raw or "").strip()
        self.password_hash = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        if not raw or not self.password_hash:
            return False
        raw = raw.strip()
        ph = self.password_hash
        try:
            if ph.startswith(("$2b$", "$2a$", "$2y$")):
                return bcrypt.checkpw(raw.encode("utf-8"), ph.encode("utf-8"))
        except (ValueError, TypeError):
            pass
        try:
            if ":" in ph and wz_check(ph, raw):
                return True
        except (ValueError, TypeError, AttributeError):
            pass
        if len(ph) == 32:
            return ph.lower() == hashlib.md5(raw.encode("utf-8")).hexdigest()
        return False

    def get_id(self):
        return str(self.id)

    @property
    def lock_expires_at(self):

        if not self.is_locked or not self.locked_at:
            return None
        try:
            minutes = _lock_duration_minutes()
        except Exception:
            minutes = 30
        return self.locked_at + datetime.timedelta(minutes=minutes)

    @property
    def is_lock_expired(self) -> bool:

        if not self.is_locked:
            return False
        if not self.locked_at:
            return False
        return datetime.datetime.utcnow() >= self.lock_expires_at

    def unlock_if_expired(self) -> bool:

        if not self.is_lock_expired:
            return False
        self.is_locked = False
        self.failed_attempts = 0
        self.locked_at = None
        return True

    def public_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role.value if self.role else None,
            "is_locked": bool(self.is_locked),
            "is_active": bool(self.is_active),
            "must_change_password": bool(self.must_change_password),
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "lock_expires_at": (
                self.lock_expires_at.isoformat() if self.lock_expires_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def user_role(self):
        return self.role

    def to_dict(self):
        return self.public_dict()
