"""ENTITY password_otps."""
from datetime import datetime

from studentapp.extensions import db


class OtpPurpose:
    FORGOT = "FORGOT"
    CHANGE = "CHANGE"


class PasswordOtp(db.Model):
    __tablename__ = "password_otps"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    purpose = db.Column(db.String(20), nullable=False, default=OtpPurpose.FORGOT)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("password_otps", lazy=True))

    def is_expired(self) -> bool:
        try:
            return datetime.utcnow() > self.expires_at
        except Exception:
            return True
