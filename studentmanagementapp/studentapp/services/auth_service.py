"""SERVICE auth — SD01/SD02/SD17. JWT chính, system_rules động, bcrypt, audit 1 transaction."""
import secrets
import string
from datetime import datetime

from flask import request as freq
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_login import login_user, logout_user
from sqlalchemy.exc import IntegrityError

from studentapp.extensions import db
from studentapp.models.user import User, UserRoleEnum
from studentapp.models.audit_log import AuditLog
from studentapp.repositories import user_repository
from studentapp.repositories import system_rule_repository as rules
from studentapp.exceptions import (
    ValidationError,
    AuthenticationError,
    DuplicateError,
    LockedError,
    BusinessRuleError,
)
from studentapp.utils.validators import is_email, is_phone, is_strong_password


def _max_attempts() -> int:
    return rules.get_int("MAX_LOGIN_ATTEMPTS", 5)


def _validate_admin_create(payload: dict):
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    if not username or len(username) < 3:
        raise ValidationError("Username phải từ 3 ký tự trở lên.")
    if not email or not is_email(email):
        raise ValidationError("Email sai định dạng cú pháp.")
    if not full_name:
        raise ValidationError("Trường họ tên không được để trống.")
    if phone and not is_phone(phone):
        raise ValidationError("Số điện thoại không hợp lệ.")
    return username, email, full_name, phone or None


def _gen_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in "!@#$%" for c in pw)
        ):
            return pw


def _notify_password_changed(user, ip):
    try:
        from studentapp.services import mail_service

        mail_service.send_password_changed_email(
            user.email,
            user.full_name,
            user.username,
            datetime.now().strftime("%H:%M %d/%m/%Y"),
            ip,
        )
    except Exception:
        pass


def create_by_admin(payload: dict, creator_id=None) -> tuple:
    from studentapp.services import mail_service

    username, email, full_name, phone = _validate_admin_create(payload)
    raw_role = (payload.get("role") or "").strip().upper()
    try:
        role = UserRoleEnum(raw_role)
    except ValueError:
        raise ValidationError("Role không hợp lệ (STAFF/TEACHER/ACADEMIC).")
    if role == UserRoleEnum.ACADEMIC:
        existing = User.query.filter_by(role=UserRoleEnum.ACADEMIC).count()
        if existing >= 1:
            raise BusinessRuleError(
                "Hệ thống chỉ giữ 1 tài khoản Giáo vụ/Admin duy nhất! "
                "Muốn thay admin thì hạ cấp/vô hiệu hóa tài khoản cũ trước "
                "(can thiệp DB với admin gốc)."
            )
    temp_password = _gen_temp_password()
    u = User(
        username=username,
        email=email,
        full_name=full_name,
        phone=phone,
        role=role,
        must_change_password=True,
    )
    u.set_password(temp_password)
    try:
        user_repository.add(u)
        db.session.add(
            AuditLog(
                user_id=int(creator_id) if creator_id else None,
                action="ADMIN_CREATE_USER",
                ip_address=freq.remote_addr if freq else None,
                details={"username": username, "role": role.value},
            )
        )
        db.session.commit()
    except DuplicateError:
        raise
    except IntegrityError:
        db.session.rollback()
        raise DuplicateError("Username/Email đã tồn tại.")
    status = mail_service.send_account_email(email, full_name, username, temp_password, role.value)
    return u, temp_password, status


def _redirect_for(role) -> str:
    return {
        "STAFF": "/staff/dashboard",
        "TEACHER": "/teacher/dashboard",
        "ACADEMIC": "/academic/dashboard",
    }.get(role.value if role else "", "/")


def login(payload: dict) -> dict:
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        raise AuthenticationError("Thiếu username/password.")

    q = User.query.filter_by(username=username)
    try:
        if db.engine.dialect.name != "sqlite":
            q = q.with_for_update()
        u = q.first()
    except Exception:
        u = user_repository.get_by_username(username)

    max_attempts = _max_attempts()
    ip = freq.remote_addr if freq else None

    if u is None or not u.is_active:
        raise AuthenticationError("Tên đăng nhập hoặc mật khẩu không đúng.")
    if u.is_locked:
        raise LockedError(
            f"Tài khoản đã bị tạm khóa do nhập sai quá {max_attempts} lần liên tiếp. "
            "Vui lòng liên hệ Giáo vụ/Admin để mở khóa!"
        )
    if not u.check_password(password):
        u.failed_attempts = (u.failed_attempts or 0) + 1
        locked_now = u.failed_attempts >= max_attempts
        if locked_now:
            u.is_locked = True
        db.session.add(
            AuditLog(user_id=u.id, action="LOGIN_FAILED", ip_address=ip, details={"username": username})
        )
        db.session.commit()
        if locked_now:
            raise LockedError(
                f"Tài khoản đã bị tạm khóa do nhập sai quá {max_attempts} lần liên tiếp. "
                "Vui lòng liên hệ Giáo vụ/Admin để mở khóa!"
            )
        remaining = max_attempts - u.failed_attempts
        raise AuthenticationError(f"Mật khẩu không chính xác. Bạn còn {remaining} lần thử!")

    u.failed_attempts = 0
    try:
        if not (u.password_hash or "").startswith(("$2b$", "$2a$", "$2y$")):
            u.set_password(password)
    except Exception:
        pass
    db.session.add(AuditLog(user_id=u.id, action="LOGIN_SUCCESS", ip_address=ip))
    db.session.commit()

    try:
        login_user(u)
    except Exception:
        pass
    token = create_access_token(
        identity=str(u.id),
        additional_claims={
            "role": u.role.value,
            "must_change_password": bool(u.must_change_password),
        },
    )
    refresh_token = create_refresh_token(identity=str(u.id))
    return {
        "token": token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 1800,
        "user": u.public_dict(),
        "redirect_url": _redirect_for(u.role),
        "must_change_password": bool(u.must_change_password),
    }


def logout(user_id=None):
    try:
        logout_user()
    except Exception:
        pass
    if user_id:
        try:
            db.session.add(
                AuditLog(
                    user_id=int(user_id),
                    action="LOGOUT",
                    ip_address=freq.remote_addr if freq else None,
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()


def request_password_reset(identifier: str):
    from studentapp.services import otp_service
    from studentapp.models.password_otp import OtpPurpose

    ident = (identifier or "").strip()
    if not ident:
        raise ValidationError("Vui lòng nhập email hoặc tên đăng nhập.")
    u = user_repository.get_by_email(ident) or user_repository.get_by_username(ident)
    if u is None or not u.is_active:
        return False, None
    _code, status = otp_service.request_otp(u, OtpPurpose.FORGOT)
    return True, status


def reset_password_with_otp(identifier: str, code: str, new_password: str, confirm: str):
    from studentapp.services import otp_service
    from studentapp.models.password_otp import OtpPurpose

    ident = (identifier or "").strip()
    if not ident:
        raise ValidationError("Vui lòng nhập email hoặc tên đăng nhập.")
    u = user_repository.get_by_email(ident) or user_repository.get_by_username(ident)
    if u is None or not u.is_active:
        raise ValidationError("Mã OTP không đúng. Vui lòng kiểm tra lại.")
    otp_service.verify_and_consume(u.id, OtpPurpose.FORGOT, code)
    ok, msg = is_strong_password(new_password)
    if not ok:
        raise ValidationError(msg + " (Mật khẩu mạnh: \u22658 ký tự, có Hoa + thường + số + ký tự đặc biệt).")
    if new_password != (confirm or ""):
        raise ValidationError("Mật khẩu xác nhận không khớp.")
    u.set_password(new_password)
    u.failed_attempts = 0
    u.is_locked = False
    u.must_change_password = False
    ip = freq.remote_addr if freq else None
    db.session.add(AuditLog(user_id=u.id, action="PASSWORD_RESET_SELF", ip_address=ip))
    db.session.commit()
    _notify_password_changed(u, ip)
    return u
