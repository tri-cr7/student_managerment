import datetime

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity,
    get_jwt,
    create_access_token,
    decode_token,
)
from flask_login import current_user

from studentapp.services import auth_service
from studentapp.repositories import user_repository
from studentapp.exceptions import AppError, ValidationError
from studentapp.utils.decorators import login_required_any

bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

def _err(e: AppError):
    return jsonify({"error": e.error, "message": e.message}), e.status_code

@bp.post("/register")
def register():
    return jsonify({
        "error": "FORBIDDEN",
        "message": "Hệ thống không cho tự đăng ký. Vui lòng liên hệ Giáo vụ/Admin để được cấp tài khoản!",
    }), 403

@bp.post("/login")
def login():
    try:
        data = auth_service.login(request.get_json(force=True, silent=True) or {})
    except AppError as e:
        if e.error == "ACCOUNT_LOCKED":

            return jsonify({
                "error": e.error,
                "message": e.message,
                "lock_duration_minutes": auth_service.lock_duration_minutes(),
            }), e.status_code
        return _err(e)
    return jsonify({"success": True, "message": "Đăng nhập thành công.", "data": data}), 200

@bp.post("/refresh")
def refresh():
    try:
        verify_jwt_in_request(refresh=True)
        uid = get_jwt_identity()
        u = user_repository.get_by_id(uid)
        if u is None or not u.is_active or u.is_locked:
            raise Exception("invalid user")
        new_token = create_access_token(
            identity=str(u.id),
            additional_claims={
                "role": u.role.value,
                "must_change_password": bool(u.must_change_password),
            },
        )
        return jsonify({
            "success": True,
            "message": "Đã cấp access token mới.",
            "data": {"token": new_token, "token_type": "Bearer", "expires_in": 1800},
        }), 200
    except Exception:
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": "Refresh token không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại!",
        }), 401

@bp.post("/forgot-password")
def forgot_password():
    try:
        body = request.get_json(force=True, silent=True) or {}
        ident = body.get("email") or body.get("username") or ""
        ok, result = auth_service.request_password_reset(ident)
    except AppError as e:
        if isinstance(e, AppError) and e.error == "BAD_REQUEST":
            return _err(e)

    data = None
    if ok and result and result[0] == "DEV":
        data = {"dev_otp": result[1], "note": "Chế độ dev — mã OTP trả trực tiếp, không gửi email."}
    return jsonify({
        "success": True,
        "message": "Nếu thông tin đúng, email chứa mã OTP 6 số đã được gửi. Mã hết hạn sau 5 phút, 1 lần dùng.",
        "data": data,
    }), 200

@bp.post("/verify-reset-otp")
def verify_reset_otp():

    try:
        body = request.get_json(force=True, silent=True) or {}
        ident = body.get("email") or body.get("username") or ""
        code = body.get("otp_code") or body.get("otp") or ""
        u, _otp = auth_service.verify_reset_otp(ident, code)
    except AppError as e:
        return _err(e)
    reset_token = create_access_token(
        identity=str(u.id),
        additional_claims={"role": u.role.value, "purpose": "PASSWORD_RESET"},
    )
    return jsonify({
        "success": True,
        "message": "Mã OTP hợp lệ. Vui lòng đặt mật khẩu mới.",
        "data": {
            "reset_token": reset_token,
            "username": u.username,
            "expires_in": 900,
        },
    }), 200

@bp.post("/reset-password")
def reset_password():

    try:
        body = request.get_json(force=True, silent=True) or {}
        reset_token = body.get("reset_token") or ""
        if reset_token:
            u = _reset_password_with_token(reset_token, body)
        else:
            u = auth_service.reset_password_with_otp(
                body.get("email") or body.get("username") or "",
                body.get("otp_code") or body.get("otp") or "",
                body.get("new_password") or "",
                body.get("confirm_password") or body.get("confirm") or "",
            )
    except AppError as e:
        return _err(e)
    return jsonify({
        "success": True,
        "message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.",
        "data": {"username": u.username},
    }), 200

def _reset_password_with_token(reset_token: str, body: dict):

    try:
        claims = decode_token(reset_token)
    except Exception:
        raise ValidationError(
            "Phiên đặt lại mật khẩu không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu mã OTP mới."
        )
    if claims.get("purpose") != "PASSWORD_RESET":
        raise ValidationError(
            "Phiên đặt lại mật khẩu không hợp lệ. Vui lòng yêu cầu mã OTP mới."
        )
    uid = claims.get("sub")
    if not uid:
        raise ValidationError(
            "Phiên đặt lại mật khẩu không hợp lệ. Vui lòng yêu cầu mã OTP mới."
        )
    try:
        user_id = int(uid)
    except (TypeError, ValueError):
        raise ValidationError(
            "Phiên đặt lại mật khẩu không hợp lệ. Vui lòng yêu cầu mã OTP mới."
        )
    return auth_service.reset_password_by_user(
        user_id,
        body.get("new_password") or "",
        body.get("confirm_password") or body.get("confirm") or "",
    )

@bp.post("/logout")
@login_required_any
def logout():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
    except Exception:
        uid = None
    auth_service.logout(uid)
    return jsonify({"success": True, "message": "Đăng xuất thành công"}), 200

@bp.get("/me")
@login_required_any
def me():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
    except Exception:
        uid = None
    u = user_repository.get_by_id(uid) if uid else None
    if u is None and getattr(current_user, "is_authenticated", False):
        u = current_user
    if u is None:
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại!",
        }), 401
    return jsonify({"success": True, "message": "OK", "data": u.public_dict()}), 200

@bp.get("/verify-token")
def verify_token():
    try:
        verify_jwt_in_request()
        uid = get_jwt_identity()
        claims = get_jwt()
        u = user_repository.get_by_id(uid)
        if u is None or not u.is_active or u.is_locked:
            raise Exception("invalid user")
        exp = claims.get("exp")
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        remaining = int(exp - now) if exp else 1800
        return jsonify({
            "success": True,
            "data": {
                "valid": True,
                "user_id": int(uid),
                "role": u.role.value,
                "expires_in": max(remaining, 0),
            },
        }), 200
    except Exception:
        return jsonify({
            "error": "UNAUTHORIZED",
            "message": "Token không hợp lệ hoặc đã hết hạn.",
        }), 401
