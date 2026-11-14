"""Route guards: JWT primary, session fallback."""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_login import current_user

from studentapp.models.user import UserRoleEnum
from studentapp.repositories import user_repository


def _deny(msg="Bạn không có quyền thực hiện thao tác này. Chức năng yêu cầu quyền hạn phù hợp!"):
    return jsonify({"error": "FORBIDDEN", "message": msg}), 403


def _unauthorized():
    return jsonify({
        "error": "UNAUTHORIZED",
        "message": "Phiên làm việc đã hết hạn hoặc Token không hợp lệ. Vui lòng đăng nhập lại!",
    }), 401


def _current_role():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid is not None:
            u = user_repository.get_by_id(uid)
            if u is not None and u.is_active and not u.is_locked:
                return u.role, u
    except Exception:
        pass
    try:
        if current_user.is_authenticated:
            return getattr(current_user, "role", None), current_user
    except Exception:
        pass
    return None, None


def role_required(*roles):
    allowed = set()
    for r in roles:
        if isinstance(r, UserRoleEnum):
            allowed.add(r)
        else:
            try:
                allowed.add(UserRoleEnum(str(r).strip().upper()))
            except ValueError:
                pass

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            role, _ = _current_role()
            if role is None:
                return _unauthorized()
            if role not in allowed:
                need = "/".join(sorted(x.value for x in allowed))
                return _deny(f"Bạn không có quyền thực hiện thao tác này. Chức năng yêu cầu quyền: {need}!")
            return fn(*a, **kw)

        return wrapper

    return deco


def login_required_any(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        role, _ = _current_role()
        if role is None:
            return _unauthorized()
        return fn(*a, **kw)

    return wrapper


def admin_required(fn):
    return role_required(UserRoleEnum.ACADEMIC)(fn)


def teacher_required(fn):
    return role_required(UserRoleEnum.TEACHER, UserRoleEnum.ACADEMIC)(fn)

def staff_required(fn):
    return role_required(UserRoleEnum.STAFF, UserRoleEnum.ACADEMIC)(fn)
