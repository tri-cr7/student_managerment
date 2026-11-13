"""API profile cá nhân SD02."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_login import current_user

from studentapp.services import profile_service, user_service
from studentapp.repositories import user_repository
from studentapp.utils.decorators import login_required_any
from studentapp.exceptions import AppError

bp = Blueprint("profile", __name__, url_prefix="/api/v1/profile")


def _err(e: AppError):
    return jsonify({"error": e.error, "message": e.message}), e.status_code


def _uid():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid is not None:
            return int(uid)
    except Exception:
        pass
    try:
        if getattr(current_user, "is_authenticated", False):
            return int(current_user.get_id())
    except Exception:
        pass
    return None


@bp.get("")
@login_required_any
def get_profile():
    u = user_repository.get_by_id(_uid())
    if u is None:
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại!",
        }), 401
    return jsonify({"success": True, "message": "OK", "data": u.public_dict()}), 200


@bp.patch("")
@login_required_any
def update_profile():
    try:
        uid = _uid()
        body = request.get_json(silent=True) or {}
        body.pop("is_active", None)
        u = user_service.update_info(uid, body, uid)
        return jsonify({"success": True, "message": "Đã cập nhật hồ sơ.", "data": u.public_dict()}), 200
    except AppError as e:
        return _err(e)


@bp.post("/change-password")
@login_required_any
def change_password():
    try:
        profile_service.change_password(_uid(), request.get_json(force=True, silent=True) or {})
    except AppError as e:
        return _err(e)
    return jsonify({
        "success": True,
        "message": "Đổi mật khẩu thành công. Vui lòng sử dụng mật khẩu mới cho lần đăng nhập kế tiếp.",
        "data": None,
    }), 200


@bp.post("/change-password/request")
@login_required_any
def change_password_request():
    try:
        status = profile_service.request_change_otp(
            _uid(), request.get_json(force=True, silent=True) or {}
        )
    except AppError as e:
        return _err(e)
    return jsonify({
        "success": True,
        "message": "Mã OTP 6 số đã được gửi về email. Mã hết hạn sau 5 phút, 1 lần dùng.",
        "data": {"email_sent_status": status},
    }), 200


@bp.post("/change-password/confirm")
@login_required_any
def change_password_confirm():
    try:
        profile_service.confirm_change_password(
            _uid(), request.get_json(force=True, silent=True) or {}
        )
    except AppError as e:
        return _err(e)
    return jsonify({
        "success": True,
        "message": "Đổi mật khẩu thành công. Vui lòng sử dụng mật khẩu mới cho lần đăng nhập kế tiếp.",
        "data": None,
    }), 200
