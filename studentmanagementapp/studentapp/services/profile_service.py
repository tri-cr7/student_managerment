"""SERVICE profile SD02."""
from datetime import datetime

from flask import request as freq

from studentapp.extensions import db
from studentapp.models.audit_log import AuditLog
from studentapp.models.password_otp import OtpPurpose
from studentapp.repositories import user_repository
from studentapp.exceptions import NotFoundError, ValidationError, AuthenticationError
from studentapp.utils.validators import is_strong_password


def _get_user(user_id):
    u = user_repository.get_by_id(user_id)
    if u is None:
        raise NotFoundError("Không tìm thấy người dùng.")
    return u


def _check_new_password(u, new: str, confirm: str):
    ok, msg = is_strong_password(new)
    if not ok:
        raise ValidationError(msg)
    if new != (confirm or ""):
        raise ValidationError("Mật khẩu xác nhận không khớp.")
    if u.check_password(new):
        raise ValidationError("Mật khẩu mới phải khác mật khẩu cũ.")


def _notify_password_changed(u, ip):
    try:
        from studentapp.services import mail_service

        when_str = datetime.now().strftime("%H:%M %d/%m/%Y")
        mail_service.send_password_changed_email(u.email, u.full_name, u.username, when_str, ip)
    except Exception:
        pass


def _apply_new_password(u, new: str, action: str):
    u.set_password(new)
    u.failed_attempts = 0
    u.must_change_password = False
    ip = freq.remote_addr if freq else None
    db.session.add(AuditLog(user_id=u.id, action=action, ip_address=ip))
    db.session.commit()
    _notify_password_changed(u, ip)
    return True


def request_change_otp(user_id, payload: dict):
    from studentapp.services import otp_service

    u = _get_user(user_id)
    old = payload.get("old_password") or ""
    new = payload.get("new_password") or ""
    confirm = payload.get("confirm_password") or payload.get("confirm") or ""
    if not old or not new:
        raise ValidationError("Thiếu mật khẩu cũ/mới.")
    if not u.check_password(old):
        raise AuthenticationError("Mật khẩu cũ không chính xác.")
    _check_new_password(u, new, confirm)
    _code, status = otp_service.request_otp(u, OtpPurpose.CHANGE)
    return status


def confirm_change_password(user_id, payload: dict):
    from studentapp.services import otp_service

    u = _get_user(user_id)
    new = payload.get("new_password") or ""
    confirm = payload.get("confirm_password") or payload.get("confirm") or ""
    code = payload.get("otp_code") or payload.get("otp") or ""
    _check_new_password(u, new, confirm)
    otp_service.verify_and_consume(u.id, OtpPurpose.CHANGE, code)
    return _apply_new_password(u, new, "CHANGE_PASSWORD")


def change_password(user_id, payload: dict):
    u = _get_user(user_id)
    old = payload.get("old_password") or ""
    new = payload.get("new_password") or ""
    confirm = payload.get("confirm_password") or payload.get("confirm") or ""
    if not old or not new:
        raise ValidationError("Thiếu mật khẩu cũ/mới.")
    if not u.check_password(old):
        raise AuthenticationError("Mật khẩu cũ không chính xác.")
    _check_new_password(u, new, confirm)
    return _apply_new_password(u, new, "CHANGE_PASSWORD")
