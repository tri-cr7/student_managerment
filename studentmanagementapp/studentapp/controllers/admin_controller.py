from flask import redirect
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from studentapp.extensions import db
from studentapp.models.user import UserRoleEnum
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

    if getattr(admin, "_views_mounted", False):
        admin.init_app(app)
        return
    admin.init_app(app)
    admin.add_view(AuditLogAdminView(
        AuditLog, db, endpoint="admin_audit_logs", url="audit-logs", name="Audit Logs"
    ))

    admin._views_mounted = True
