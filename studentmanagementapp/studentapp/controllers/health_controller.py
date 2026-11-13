"""API GET /api/v1/health — kiểm tra sống/chết + DB."""
from flask import Blueprint
from sqlalchemy import text

from studentapp.extensions import db
from studentapp.utils.helpers import ok

bp = Blueprint("health", __name__, url_prefix="/api/v1")


@bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return ok({"db": "up"}, "API sống.")
    except Exception as e:
        return ok({"db": f"down: {e}"}, "DB lỗi.", 500)


@bp.get("")
def index():
    return ok(
        {
            "message": "StudentApp API — xem danh sách endpoint bên dưới.",
            "endpoints": {
                "health": "GET /api/v1/health",
                "register": "POST /api/v1/auth/register",
                "login": "POST /api/v1/auth/login",
                "logout": "POST /api/v1/auth/logout",
                "me": "GET /api/v1/auth/me",
                "verify_token": "GET /api/v1/auth/verify-token",
                "profile": "GET /api/v1/profile",
                "profile_update": "PATCH /api/v1/profile",
                "change_password": "POST /api/v1/profile/change-password",
                "admin_users": "GET|POST /api/v1/admin/users",
                "admin_lock": "PATCH /api/v1/admin/users/<id>/lock",
            },
        },
        "StudentApp API v1.",
    )
