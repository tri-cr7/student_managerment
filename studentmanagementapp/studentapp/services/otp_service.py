"""SERVICE OTP 6 số qua mail — dùng chung cho quên MK (FORGOT) + đổi MK (CHANGE)."""
import secrets
from datetime import datetime, timedelta

from flask import request as freq

from studentapp.extensions import db
from studentapp.models.audit_log import AuditLog
from studentapp.models.password_otp import PasswordOtp
from studentapp.repositories import system_rule_repository as rules
from studentapp.exceptions import ValidationError


def _expire_minutes() -> int:
    return rules.get_int("OTP_EXPIRE_MINUTES", 5)


def _max_attempts() -> int:
    return rules.get_int("OTP_MAX_ATTEMPTS", 5)


def _gen_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def request_otp(user, purpose: str) -> tuple[str, str]:
    from studentapp.services import mail_service

    PasswordOtp.query.filter_by(user_id=user.id, purpose=purpose, used=False).update(
        {"used": True}, synchronize_session=False
    )
    code = _gen_code()
    otp = PasswordOtp(
        user_id=user.id,
        purpose=purpose,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=_expire_minutes()),
    )
    db.session.add(otp)
    db.session.add(
        AuditLog(
            user_id=user.id,
            action=f"OTP_REQUEST_{purpose}",
            ip_address=freq.remote_addr if freq else None,
        )
    )
    db.session.commit()
    status = mail_service.send_otp_email(
        user.email,
        user.full_name,
        user.username,
        code,
        _expire_minutes(),
        "đổi mật khẩu" if purpose == "CHANGE" else "đặt lại mật khẩu",
    )
    return code, status


def verify_and_consume(user_id: int, purpose: str, code: str) -> PasswordOtp:
    code = (code or "").strip()
    if not code:
        raise ValidationError("Vui lòng nhập mã OTP 6 số từ email.")
    otp = (
        PasswordOtp.query.filter_by(user_id=user_id, purpose=purpose, used=False)
        .order_by(PasswordOtp.id.desc())
        .first()
    )
    if otp is None:
        raise ValidationError("Mã OTP không tồn tại hoặc đã dùng. Vui lòng yêu cầu mã mới.")
    if otp.is_expired():
        otp.used = True
        db.session.commit()
        raise ValidationError("Mã OTP đã hết hạn. Vui lòng yêu cầu mã mới.")
    if otp.code != code:
        otp.attempts = (otp.attempts or 0) + 1
        if otp.attempts >= _max_attempts():
            otp.used = True
            db.session.add(
                AuditLog(
                    user_id=user_id,
                    action=f"OTP_LOCKED_{purpose}",
                    ip_address=freq.remote_addr if freq else None,
                )
            )
            db.session.commit()
            raise ValidationError(
                f"Nhập sai OTP quá {_max_attempts()} lần — mã đã bị hủy. Vui lòng yêu cầu mã mới."
            )
        db.session.commit()
        remaining = _max_attempts() - otp.attempts
        raise ValidationError(f"Mã OTP không đúng. Bạn còn {remaining} lần thử!")
    otp.used = True
    otp.attempts = otp.attempts or 0
    db.session.commit()
    return otp
