"""Mount Flask-Admin /admin — User + AuditLog (read-only, export CSV)."""
import secrets

from flask import flash, redirect
from flask_admin import Admin
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from studentapp.extensions import db
from studentapp.models.user import User, UserRoleEnum
from studentapp.models.audit_log import AuditLog

admin = Admin(name="Student Management Admin")


class _AcademicOnlyMixin:
    def is_accessible(self):
        try:
            return (
                getattr(current_user, "is_authenticated", False)
                and getattr(current_user, "role", None) == UserRoleEnum.ACADEMIC
            )
        except Exception:
            return False

    def inaccessible_callback(self, name, **kwargs):
        return redirect("/api/v1/auth/login")


class UserAdminView(_AcademicOnlyMixin, ModelView):
    column_list = ["id", "username", "full_name", "email", "role", "is_locked", "failed_attempts", "is_active"]
    column_searchable_list = ["username", "email", "full_name"]
    column_filters = ["role", "is_locked", "is_active"]
    can_view_details = True
    column_details_list = [
        "id", "username", "email", "full_name", "phone", "role",
        "failed_attempts", "is_locked", "is_active", "created_at", "updated_at",
    ]
    can_edit = True
    form_excluded_columns = ["password_hash", "failed_attempts", "created_at", "updated_at"]

    @action("lock", "Lock", "Khoá các tài khoản đã chọn?")
    def action_lock(self, ids):
        actor_id = getattr(current_user, "id", None)
        targets = User.query.filter(User.id.in_(ids)).all()
        n = User.query.filter(User.id.in_(ids)).update(
            {User.is_locked: True}, synchronize_session=False
        )
        for u in targets:
            db.session.add(
                AuditLog(
                    user_id=actor_id,
                    action="LOCK_USER",
                    details={"target_user_id": u.id, "username": u.username,
                             "role": u.role.value if u.role else None, "via": "flask_admin_bulk"},
                )
            )
        db.session.commit()
        flash(f"Đã khoá {n} tài khoản.", "success")

    @action("unlock", "Unlock", "Mở khoá + reset số lần sai?")
    def action_unlock(self, ids):
        actor_id = getattr(current_user, "id", None)
        targets = User.query.filter(User.id.in_(ids)).all()
        n = User.query.filter(User.id.in_(ids)).update(
            {User.is_locked: False, User.failed_attempts: 0}, synchronize_session=False
        )
        for u in targets:
            db.session.add(
                AuditLog(
                    user_id=actor_id,
                    action="UNLOCK_USER",
                    details={"target_user_id": u.id, "username": u.username,
                             "role": u.role.value if u.role else None, "via": "flask_admin_bulk"},
                )
            )
        db.session.commit()
        flash(f"Đã mở {n} tài khoản.", "success")

    @action("reset_password", "Reset Password", "Reset mật khẩu các user đã chọn?")
    def action_reset_password(self, ids):
        actor_id = getattr(current_user, "id", None)
        users = User.query.filter(User.id.in_(ids)).all()
        for u in users:
            temp = "Tmp@" + secrets.token_urlsafe(6)
            u.set_password(temp)
            u.failed_attempts = 0
            u.is_locked = False
            u.must_change_password = True
            db.session.add(
                AuditLog(
                    user_id=actor_id,
                    action="RESET_PASSWORD",
                    details={"target_user_id": u.id, "username": u.username,
                             "role": u.role.value if u.role else None, "via": "flask_admin_bulk"},
                )
            )
            flash(f"MK tạm [{u.username}]: {temp}", "warning")
        db.session.commit()
        flash(f"Đã reset {len(users)} user.", "success")


class AuditLogAdminView(_AcademicOnlyMixin, ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    column_list = ["id", "user_id", "action", "ip_address", "created_at"]
    column_searchable_list = ["action", "ip_address"]
    column_filters = ["action", "created_at"]
    column_default_sort = ("created_at", True)
    can_view_details = True
    column_details_list = ["id", "user_id", "action", "ip_address", "details", "created_at"]
    can_export = True
    export_types = ["csv"]


def init_admin(app):
    """Mount Flask-Admin vào app.

    Flask-Admin ``Admin`` là instance dùng chung ở module scope, nên mỗi lần
    ``create_app`` chạy lại sẽ đăng ký trùng endpoint. Guard bằng cờ trên
    chính instance ``admin`` để ``create_app`` có thể được gọi nhiều lần
    trong cùng process (ví dụ khi chạy test suite).
    """
    if getattr(admin, "_views_mounted", False):
        admin.init_app(app)
        return
    admin.init_app(app)
    admin.add_view(AuditLogAdminView(
        AuditLog, db.session, endpoint="admin_audit_logs", url="audit-logs", name="Audit Logs"
    ))
    admin.add_view(UserAdminView(
        User, db.session, endpoint="admin_users_panel", url="users", name="Users"
    ))
    admin._views_mounted = True
