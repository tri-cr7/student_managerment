import pytest

from studentapp.extensions import db
from studentapp.models.password_otp import OtpPurpose, PasswordOtp
from studentapp.models.user import User, UserRoleEnum

OLD_PW = "OldPass@2026"
NEW_PW = "BrandNew@2026"

@pytest.fixture
def account(app):

    u = User(
        username="quenhac",
        email="quenhac@school.local",
        full_name="Người Dùng Quên Mật Khẩu",
        role=UserRoleEnum.TEACHER,
    )
    u.set_password(OLD_PW)
    u.must_change_password = False
    db.session.add(u)
    db.session.commit()
    return u

def _latest_otp(user_id):
    return (
        PasswordOtp.query.filter_by(
            user_id=user_id, purpose=OtpPurpose.FORGOT, used=False
        )
        .order_by(PasswordOtp.id.desc())
        .first()
    )

def _request_otp(client):

    res = client.post(
        "/api/v1/auth/forgot-password", json={"email": "quenhac@school.local"}
    )
    assert res.status_code == 200
    return _latest_otp(account_id()).code

def account_id():
    return User.query.filter_by(username="quenhac").first().id

class TestVerifyResetOtp:
    def test_verify_correct_otp_returns_reset_token(self, client, account):
        code = _request_otp(client)
        res = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        )
        assert res.status_code == 200
        data = res.get_json()["data"]
        assert data["reset_token"]
        assert data["username"] == "quenhac"

    def test_verify_accepts_username_instead_of_email(self, client, account):
        code = _request_otp(client)
        res = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"username": "quenhac", "otp_code": code},
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["reset_token"]

    def test_verify_does_not_consume_otp(self, client, account):

        code = _request_otp(client)
        client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        )
        otp = _latest_otp(account_id())
        assert otp is not None
        assert otp.used is False

    def test_verify_wrong_otp_returns_400(self, client, account):
        _request_otp(client)
        res = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": "000000"},
        )
        assert res.status_code == 400
        assert "không đúng" in res.get_json()["message"]

    def test_verify_unknown_account_returns_400(self, client, account):
        res = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "khongco@school.local", "otp_code": "123456"},
        )
        assert res.status_code == 400

class TestResetPasswordWithToken:
    def test_reset_with_token_changes_password(self, client, account):
        code = _request_otp(client)
        res = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        )
        token = res.get_json()["data"]["reset_token"]

        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": token,
                "new_password": NEW_PW,
                "confirm_password": NEW_PW,
            },
        )
        assert res.status_code == 200
        assert res.get_json()["data"]["username"] == "quenhac"

        u = User.query.filter_by(username="quenhac").first()
        assert u.check_password(NEW_PW)
        assert not u.check_password(OLD_PW)

    def test_reset_consumes_otp(self, client, account):
        code = _request_otp(client)
        token = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        ).get_json()["data"]["reset_token"]

        client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": token,
                "new_password": NEW_PW,
                "confirm_password": NEW_PW,
            },
        )
        assert _latest_otp(account_id()) is None

    def test_reset_with_invalid_token_returns_400(self, client, account):
        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": "token-khong-hop-le",
                "new_password": NEW_PW,
                "confirm_password": NEW_PW,
            },
        )
        assert res.status_code == 400
        assert "không hợp lệ" in res.get_json()["message"]

    def test_reset_with_regular_access_token_is_rejected(self, client, account):

        from flask_jwt_extended import create_access_token

        with client.application.app_context():
            token = create_access_token(
                identity=str(account_id()), additional_claims={"role": "TEACHER"}
            )
        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": token,
                "new_password": NEW_PW,
                "confirm_password": NEW_PW,
            },
        )
        assert res.status_code == 400

    def test_reset_token_cannot_access_protected_api(self, client, account):

        code = _request_otp(client)
        token = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        ).get_json()["data"]["reset_token"]

        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401

    def test_weak_password_returns_400(self, client, account):
        code = _request_otp(client)
        token = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        ).get_json()["data"]["reset_token"]

        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": token,
                "new_password": "abc",
                "confirm_password": "abc",
            },
        )
        assert res.status_code == 400

    def test_mismatched_confirmation_returns_400(self, client, account):
        code = _request_otp(client)
        token = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        ).get_json()["data"]["reset_token"]

        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": token,
                "new_password": NEW_PW,
                "confirm_password": "KhacMatKhau@2026",
            },
        )
        assert res.status_code == 400
        assert "không khớp" in res.get_json()["message"]

    def test_reset_unlocks_locked_account(self, client, account):
        u = User.query.filter_by(username="quenhac").first()
        u.is_locked = True
        u.failed_attempts = 5
        db.session.commit()

        code = _request_otp(client)
        token = client.post(
            "/api/v1/auth/verify-reset-otp",
            json={"email": "quenhac@school.local", "otp_code": code},
        ).get_json()["data"]["reset_token"]
        client.post(
            "/api/v1/auth/reset-password",
            json={
                "reset_token": token,
                "new_password": NEW_PW,
                "confirm_password": NEW_PW,
            },
        )

        u = User.query.filter_by(username="quenhac").first()
        assert u.is_locked is False
        assert u.failed_attempts == 0

class TestLegacyOneStepReset:
    def test_legacy_reset_with_otp_code_still_works(self, client, account):
        code = _request_otp(client)
        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "quenhac@school.local",
                "otp_code": code,
                "new_password": NEW_PW,
                "confirm_password": NEW_PW,
            },
        )
        assert res.status_code == 200
        u = User.query.filter_by(username="quenhac").first()
        assert u.check_password(NEW_PW)

    def test_legacy_reset_wrong_otp_returns_400(self, client, account):
        _request_otp(client)
        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "quenhac@school.local",
                "otp_code": "000000",
                "new_password": NEW_PW,
                "confirm_password": NEW_PW,
            },
        )
        assert res.status_code == 400

class TestForgotPassword:
    def test_unknown_account_still_returns_200(self, client, account):
        res = client.post(
            "/api/v1/auth/forgot-password", json={"email": "khongco@school.local"}
        )
        assert res.status_code == 200
        assert res.get_json()["success"] is True

    def test_forgot_creates_otp_record(self, client, account):
        _request_otp(client)
        assert _latest_otp(account_id()) is not None
