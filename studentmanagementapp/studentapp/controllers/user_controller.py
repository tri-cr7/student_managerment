"""API quản trị user SD17: /api/v1/admin/users (chỉ ACADEMIC)."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from studentapp.services import auth_service, user_service
from studentapp.utils.decorators import role_required
from studentapp.exceptions import AppError

bp = Blueprint("admin_users", __name__, url_prefix="/api/v1/admin/users")


def _err(e: AppError):
    return jsonify({"error": e.error, "message": e.message}), e.status_code


def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _actor():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        return None


@bp.get("")
@role_required("ACADEMIC")
def list_users():
    try:
        return _ok([u.public_dict() for u in user_service.list_users()])
    except AppError as e:
        return _err(e)


@bp.get("/<int:uid>")
@role_required("ACADEMIC")
def detail(uid):
    try:
        return _ok(user_service._get(uid).public_dict())
    except AppError as e:
        return _err(e)


@bp.post("")
@role_required("ACADEMIC")
def create():
    try:
        u, _temp_pw, email_status = auth_service.create_by_admin(
            request.get_json(force=True, silent=True) or {}, _actor()
        )
    except AppError as e:
        return _err(e)
    return jsonify({
        "success": True,
        "message": "Cấp tài khoản mới thành công. Email thông báo mật khẩu khởi tạo đã được gửi qua Mail Server.",
        "data": {
            "user_id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "must_change_password": True,
            "email_sent_status": email_status,
        },
    }), 201


@bp.put("/<int:uid>")
@role_required("ACADEMIC")
def update(uid):
    try:
        u = user_service.update_info(uid, request.get_json(silent=True) or {}, _actor())
        return _ok(u.public_dict(), "Đã cập nhật tài khoản.")
    except AppError as e:
        return _err(e)


@bp.patch("/<int:uid>/lock")
@role_required("ACADEMIC")
def lock_patch(uid):
    try:
        body = request.get_json(silent=True) or {}
        want_lock = body.get("is_locked", True)
        if str(want_lock).lower() in ("false", "0", "no", "off"):
            u = user_service.unlock(uid, _actor())
            msg = "Đã mở khóa tài khoản thành công và đặt lại số lần nhập sai về 0."
        else:
            u = user_service.lock(uid, _actor())
            msg = "Đã khóa tài khoản thành công."
        return _ok(
            {"user_id": u.id, "is_locked": bool(u.is_locked), "failed_attempts": u.failed_attempts},
            msg,
        )
    except AppError as e:
        return _err(e)


@bp.post("/<int:uid>/lock")
@role_required("ACADEMIC")
def lock(uid):
    try:
        u = user_service.lock(uid, _actor())
        return _ok(u.public_dict(), "Đã khoá.")
    except AppError as e:
        return _err(e)


@bp.post("/<int:uid>/unlock")
@role_required("ACADEMIC")
def unlock(uid):
    try:
        u = user_service.unlock(uid, _actor())
        return _ok(u.public_dict(), "Đã mở khoá.")
    except AppError as e:
        return _err(e)


@bp.post("/<int:uid>/reset-password")
@role_required("ACADEMIC")
def reset(uid):
    try:
        new_pw = (request.get_json(silent=True) or {}).get("new_password", "DoiMK@123")
        u = user_service.reset_password(uid, new_pw, _actor())
        return _ok(u.public_dict(), "Đã reset mật khẩu.")
    except AppError as e:
        return _err(e)


@bp.put("/<int:uid>/role")
@role_required("ACADEMIC")
def role(uid):
    try:
        u = user_service.change_role(
            uid, (request.get_json(silent=True) or {}).get("role"), _actor()
        )
        return _ok(u.public_dict(), "Đã đổi role.")
    except AppError as e:
        return _err(e)
