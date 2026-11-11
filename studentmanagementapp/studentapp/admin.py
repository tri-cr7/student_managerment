from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_admin.actions import action
from flask_admin.model import template
from studentapp.models import User,UserRoleEnum,AuditLog
from studentapp import dao,app,db
from flask_admin.contrib.sqla import ModelView
from flask import flash
import secrets
import hashlib

admin = Admin(app=app, name='Student Management Admin')


class UserAdminView(ModelView):
    # 71. List configuration matching your columns
    column_list = ['id', 'username', 'full_name', 'email', 'role', 'is_locked', 'failed_attempts', 'is_active']
    column_searchable_list = ['username', 'email', 'full_name']
    column_filters = ['role', 'is_locked', 'is_active']

    # 72. Detail view configuration
    can_view_details = True
    column_details_list = ['id', 'username', 'email', 'full_name', 'phone', 'role', 'failed_attempts', 'is_locked',
                           'is_active', 'created_at', 'updated_at']

    # 74. Edit/Update settings (exclude password hash from plain form edits)
    can_edit = True
    form_excluded_columns = ['password_hash', 'failed_attempts', 'created_at', 'updated_at']

    # --- ENDPOINT 75: Lock Action (Using your `is_locked` column) ---
    @action('lock', 'Lock Accounts', 'Are you sure you want to lock the selected user accounts?')
    def action_lock(self, ids):
        try:
            query = User.query.filter(User.id.in_(ids))
            count = query.update({User.is_locked: True}, synchronize_session=False)
            db.session.commit()
            flash(f'{count} user account(s) locked successfully.', 'success')
        except Exception as ex:
            flash(f'Failed to lock accounts. Error: {str(ex)}', 'error')

    # --- ENDPOINT 75: Unlock Action (Resets lock state and failed attempts) ---
    @action('unlock', 'Unlock Accounts', 'Are you sure you want to unlock the selected user accounts?')
    def action_unlock(self, ids):
        try:
            query = User.query.filter(User.id.in_(ids))
            # Unlocking usually resets failed attempts back to 0 as well!
            count = query.update({User.is_locked: False, User.failed_attempts: 0}, synchronize_session=False)
            db.session.commit()
            flash(f'{count} user account(s) unlocked successfully.', 'success')
        except Exception as ex:
            flash(f'Failed to unlock accounts. Error: {str(ex)}', 'error')

    # --- ENDPOINT 76: Reset Password Action ---
    @action('reset_password', 'Reset Passwords',
            'Are you sure you want to reset the password for selected users? This will generate new temporary passwords.')
    def action_reset_password(self, ids):
        try:
            users = User.query.filter(User.id.in_(ids)).all()
            count = 0

            for user in users:
                # 1. Generate a secure random temporary password (e.g., 8 characters)
                temp_password = secrets.token_urlsafe(6)

                # 2. Hash it using your project's MD5 method
                user.password_hash = hashlib.md5(temp_password.strip().encode('utf-8')).hexdigest()

                # 3. Flash the plain temporary password so the admin can see/share it
                flash(f"Temp password for [ {user.username} ]: <strong>{temp_password}</strong>", "warning")
                count += 1

            db.session.commit()
            flash(f'Successfully reset passwords for {count} user(s).', 'success')
        except Exception as ex:
            flash(f'Failed to reset passwords. Error: {str(ex)}', 'error')


class AuditLogAdminView(ModelView):
    # Lock down the view to read-only for security and compliance
    can_create = False
    can_edit = False
    can_delete = False

    # 77. Endpoint 77: List view (`GET /admin/audit-logs`)
    column_list = ['id', 'user_id', 'action', 'ip_address', 'created_at']
    column_searchable_list = ['action', 'ip_address']
    column_filters = ['action', 'created_at']

    # Sort logs by newest first by default
    column_default_sort = ('created_at', True)

    # 78. Endpoint 78: Detail view (`GET /admin/audit-logs/{id}`) showing JSON details
    can_view_details = True
    column_details_list = ['id', 'user_id', 'action', 'ip_address', 'details', 'created_at']

    # 79. Endpoint 79: Built-in CSV/Spreadsheet export (`GET /admin/audit-logs/export`)
    can_export = True
    export_types = ['csv']


# Register the view
admin.add_view(AuditLogAdminView(AuditLog, db.session, endpoint='audit-logs', url='audit-logs', name='Audit Logs'))
# Register the subclass and force the URL/endpoint to be 'users'
admin.add_view(UserAdminView(User, db.session, endpoint='users', url='users', name='Users'))

