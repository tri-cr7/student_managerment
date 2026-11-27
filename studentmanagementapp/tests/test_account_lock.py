from datetime import datetime, timedelta

import pytest

from studentapp.extensions import db
from studentapp.models.audit_log import AuditLog
from studentapp.models.system_rule import SystemRule
from studentapp.models.user import User, UserRoleEnum

PASSWORD = "MatKhau@2026"

def _now():

    return datetime.utcnow()

@pytest.fixture
def account(app):
    u = User(
        username="locktest",
        email="locktest@school.local",
        full_name="Người Dùng Bị Khoá",
        role=UserRoleEnum.TEACHER,
    )
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.commit()
    return u

def _lock_now(user_id, minutes_ago=0):

    u = db.session.get(User, user_id)
    u.is_locked = True
    u.failed_attempts = 5
    u.locked_at = _now() - timedelta(minutes=minutes_ago)
    db.session.commit()

def _audit_actions(user_id):
    return [
        a.action
        for a in AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.id).all()
    ]

class TestAccountLocking:
    def test_wrong_password_5_times_locks_account(self, client, account):
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "locktest", "password": "SaiMatKhau@1"},
            )

        u = User.query.filter_by(username="locktest").first()
        assert u.is_locked is True
        assert u.failed_attempts == 5
        assert u.locked_at is not None

    def test_lock_is_logged(self, client, account):
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "locktest", "password": "SaiMatKhau@1"},
            )
        actions = _audit_actions(account.id)
        assert "ACCOUNT_LOCKED" in actions
        assert "LOGIN_FAILED" in actions

    def test_locked_account_cannot_login(self, client, account):
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "locktest", "password": "SaiMatKhau@1"},
            )
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        assert res.status_code == 403
        assert res.get_json()["error"] == "ACCOUNT_LOCKED"

    def test_locked_response_contains_duration(self, client, account):
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "locktest", "password": "SaiMatKhau@1"},
            )
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        assert res.status_code == 403
        body = res.get_json()
        assert body["lock_duration_minutes"] == 30
        assert "30 phút" in body["message"]

class TestAutoUnlock:
    def test_account_still_locked_before_expiry(self, client, account):

        _lock_now(account.id, minutes_ago=5)
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        assert res.status_code == 403

    def test_auto_unlock_after_expiry(self, client, account):

        _lock_now(account.id, minutes_ago=31)
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["token"]

    def test_auto_unlock_resets_failed_attempts(self, client, account):
        _lock_now(account.id, minutes_ago=31)
        client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        u = User.query.filter_by(username="locktest").first()
        assert u.is_locked is False
        assert u.failed_attempts == 0
        assert u.locked_at is None

    def test_auto_unlock_is_logged(self, client, account):
        _lock_now(account.id, minutes_ago=31)
        client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        actions = _audit_actions(account.id)
        assert "ACCOUNT_AUTO_UNLOCK" in actions

    def test_auto_unlock_respects_custom_duration(self, client, account):

        r = SystemRule.query.filter_by(rule_key="LOCK_DURATION_MINUTES").first()
        r.rule_value = "1"
        db.session.commit()

        _lock_now(account.id, minutes_ago=2)
        res = client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        assert res.status_code == 200

    def test_locked_without_locked_at_is_not_auto_unlocked(self, client, account):

        u = User.query.filter_by(username="locktest").first()
        u.is_locked = True
        u.failed_attempts = 5
        u.locked_at = None
        db.session.commit()

        res = client.post(
            "/api/v1/auth/login",
            json={"username": "locktest", "password": PASSWORD},
        )
        assert res.status_code == 403

class TestResetPasswordUnlocks:
    def test_forgot_password_flow_unlocks_account(self, client, account):
        from studentapp.models.password_otp import OtpPurpose, PasswordOtp

        client.post(
            "/api/v1/auth/forgot-password", json={"username": "locktest"}
        )
        otp = (
            PasswordOtp.query.filter_by(
                user_id=account.id, purpose=OtpPurpose.FORGOT, used=False
            )
            .order_by(PasswordOtp.id.desc())
            .first()
        )
        code = otp.code

        res = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"username": "locktest", "otp_code": code},
        )
        token = res.get_json()["data"]["reset_token"]

        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": token,
                "new_password": "MoiMatKhau@2026",
                "confirm_password": "MoiMatKhau@2026",
            },
        )
        assert res.status_code == 200

        u = User.query.filter_by(username="locktest").first()
        assert u.is_locked is False
        assert u.locked_at is None
        assert u.failed_attempts == 0
        assert u.check_password("MoiMatKhau@2026")
