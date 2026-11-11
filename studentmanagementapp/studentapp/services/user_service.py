"""SERVICE user — quản trị (chỉ ACADEMIC)."""
import os

from sqlalchemy.exc import IntegrityError

from studentapp.extensions import db
from studentapp.models.audit_log import AuditLog
from studentapp.models.user import User, UserRoleEnum
from studentapp.repositories import user_repository
from studentapp.exceptions import (
    NotFoundError,
    ValidationError,
    DuplicateError,
    BusinessRuleError,
    PermissionDeniedError,
)
from studentapp.utils.validators import is_email, is_strong_password


def _get(uid):
    u = user_repository.get_by_id(uid)
    if not u:
        raise NotFoundError("Không tìm thấy người dùng.")
    return u


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def count_active_academics() -> int:
    return User.query.filter_by(
        role=UserRoleEnum.ACADEMIC, is_active=True, is_locked=False
    ).count()


def _ensure_not_self(uid, actor_id, action="khóa"):
    if actor_id is not None and _as_int(uid) == _as_int(actor_id):
        raise ValidationError(f"Không thể tự {action} chính tài khoản đang đăng nhập.")


def _ensure_keep_last_academic(target) -> None:
    if (
        target.role == UserRoleEnum.ACADEMIC
        and bool(target.is_active)
        and not bool(target.is_locked)
        and count_active_academics() <= 1
    ):
        raise BusinessRuleError(
            "Hệ thống phải giữ ít nhất 1 tài khoản Giáo vụ/Admin đang hoạt động!"
        )


def _root_username() -> str:
    return os.environ.get("SEED_ADMIN_USERNAME", "giaovu").strip() or "giaovu"


def _is_root(user) -> bool:
    try:
        return (user.username or "").strip() == _root_username()
    except Exception:
        return False


def _ensure_can_touch_academic(target, actor_id, action: str) -> None:
    if target.role != UserRoleEnum.ACADEMIC:
        return
    if _is_root(target):
        raise PermissionDeniedError(
            f"Tài khoản admin gốc '{target.username}' được bảo vệ — "
            "không thể khóa/vô hiệu/hạ cấp qua API, chỉ can thiệp trực tiếp từ DB!"
        )
    if actor_id is None:
        return
    actor = user_repository.get_by_id(actor_id)
    if (
        actor is not None
        and not _is_root(actor)
        and _as_int(actor_id) != _as_int(target.id)
    ):
        raise PermissionDeniedError(
            f"Chỉ admin gốc mới được {action} một tài khoản Giáo vụ/Admin khác!"
        )


def list_users():
    return user_repository.list_all()


def lock(uid, actor_id=None):
    u = _get(uid)
    _ensure_not_self(uid, actor_id, "khóa")
    _ensure_can_touch_academic(u, actor_id, "khóa")
    _ensure_keep_last_academic(u)
    u.is_locked = True
    db.session.commit()
    return u


def unlock(uid):
    u = _get(uid)
    u.is_locked = False
    u.failed_attempts = 0
    db.session.commit()
    return u


def reset_password(uid, new_password="DoiMK@123"):
    ok, msg = is_strong_password(new_password or "")
    if not ok:
        raise ValidationError(
            msg + " (Mật khẩu mạnh: \u22658 ký tự, có Hoa + thường + số + ký tự đặc biệt)."
        )
    u = _get(uid)
    u.set_password(new_password)
    u.failed_attempts = 0
    u.is_locked = False
    u.must_change_password = True
    db.session.add(AuditLog(user_id=u.id, action="RESET_PASSWORD"))
    db.session.commit()
    try:
        from studentapp.services import mail_service

        mail_service.send_account_email(
            u.email, u.full_name, u.username, new_password, u.role.value
        )
    except Exception:
        pass
    return u


def change_role(uid, role_raw, actor_id=None):
    try:
        role = UserRoleEnum(str(role_raw or "").strip().upper())
    except ValueError:
        raise ValidationError("Role không hợp lệ (STAFF/TEACHER/ACADEMIC).")
    u = _get(uid)
    if u.role != UserRoleEnum.ACADEMIC and role == UserRoleEnum.ACADEMIC:
        existing = User.query.filter_by(role=UserRoleEnum.ACADEMIC).count()
        if existing >= 1:
            raise BusinessRuleError(
                "Hệ thống chỉ giữ 1 tài khoản Giáo vụ/Admin duy nhất! "
                "Không thể thăng cấp thêm ACADEMIC."
            )
    if u.role == UserRoleEnum.ACADEMIC and role != UserRoleEnum.ACADEMIC:
        _ensure_can_touch_academic(u, actor_id, "hạ cấp")
        if (
            bool(u.is_active)
            and not bool(u.is_locked)
            and count_active_academics() <= 1
        ):
            raise BusinessRuleError(
                "Hệ thống phải giữ ít nhất 1 tài khoản Giáo vụ/Admin đang hoạt động!"
            )
    u.role = role
    db.session.commit()
    return u


def update_info(uid, payload: dict, actor_id=None):
    u = _get(uid)
    if payload.get("full_name"):
        u.full_name = payload["full_name"].strip()
    if payload.get("email"):
        email = payload["email"].strip()
        if not is_email(email):
            raise ValidationError("Email sai định dạng cú pháp.")
        other = user_repository.get_by_email(email)
        if other and other.id != u.id:
            raise DuplicateError("Email đã tồn tại.")
        u.email = email
    if payload.get("phone") is not None:
        u.phone = (payload.get("phone") or "").strip() or None
    if "is_active" in payload:
        want = bool(payload["is_active"])
        if u.is_active and not want:
            _ensure_not_self(uid, actor_id, "vô hiệu hóa")
            _ensure_can_touch_academic(u, actor_id, "vô hiệu hóa")
            _ensure_keep_last_academic(u)
        u.is_active = want
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise DuplicateError("Email đã tồn tại.")
    return u
