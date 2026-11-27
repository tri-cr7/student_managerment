import pytest

from studentapp.extensions import db
from studentapp.models.user import User, UserRoleEnum
from studentapp.services import user_service
from studentapp.exceptions import (
    AppError,
    BusinessRuleError,
    PermissionDeniedError,
    ValidationError,
)

ROOT_USERNAME = "giaovu"

@pytest.fixture
def accounts(app):

    def mk(username, role, locked=False, active=True):
        u = User(
            username=username,
            email=f"{username}@school.local",
            full_name=username.upper(),
            role=role,
            is_active=active,
            is_locked=locked,
        )
        u.set_password("Test@123")
        db.session.add(u)
        db.session.commit()
        return u

    root = mk(ROOT_USERNAME, UserRoleEnum.ACADEMIC)
    admin = mk("hv01", UserRoleEnum.ACADEMIC)
    teacher = mk("gv01", UserRoleEnum.TEACHER)
    staff = mk("nv01", UserRoleEnum.STAFF)
    return {
        "root": root,
        "admin": admin,
        "teacher": teacher,
        "staff": staff,
    }

@pytest.fixture
def headers(app):
    from flask_jwt_extended import create_access_token

    def _tok(u):
        with app.app_context():
            token = create_access_token(
                identity=str(u.id), additional_claims={"role": u.role.value}
            )
        return {"Authorization": f"Bearer {token}"}

    return _tok

class TestChangeRoleService:
    def test_change_role_ok(self, app, accounts):
        out = user_service.change_role(
            accounts["teacher"].id, "STAFF", actor_id=accounts["root"].id
        )
        assert out.role == UserRoleEnum.STAFF

    def test_invalid_role_raises_400(self, app, accounts):
        with pytest.raises(ValidationError) as exc:
            user_service.change_role(
                accounts["teacher"].id, "SUPERADMIN", actor_id=accounts["root"].id
            )
        assert exc.value.status_code == 400

    def test_missing_role_raises_400(self, app, accounts):
        with pytest.raises(ValidationError):
            user_service.change_role(
                accounts["teacher"].id, None, actor_id=accounts["root"].id
            )

    def test_promote_to_academic_blocked_when_exists(self, app, accounts):

        with pytest.raises(BusinessRuleError) as exc:
            user_service.change_role(
                accounts["staff"].id, "ACADEMIC", actor_id=accounts["root"].id
            )
        assert exc.value.status_code == 422

    def test_demote_last_academic_blocked(self, app, accounts):

        accounts["root"].is_active = False
        db.session.commit()
        with pytest.raises(BusinessRuleError) as exc:
            user_service.change_role(
                accounts["admin"].id, "STAFF", actor_id=accounts["root"].id
            )
        assert exc.value.status_code == 422

    def test_demote_allowed_when_another_academic_remains(self, app, accounts):

        out = user_service.change_role(
            accounts["admin"].id, "STAFF", actor_id=accounts["root"].id
        )
        assert out.role == UserRoleEnum.STAFF

    def test_audit_log_written(self, app, accounts):
        from studentapp.models.audit_log import AuditLog

        user_service.change_role(
            accounts["teacher"].id, "STAFF", actor_id=accounts["root"].id
        )
        row = (
            AuditLog.query.filter_by(action="CHANGE_ROLE")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert row is not None
        assert row.details["old_role"] == "TEACHER"
        assert row.details["new_role"] == "STAFF"
        assert row.details["target_user_id"] == accounts["teacher"].id

    def test_noop_change_does_not_write_audit(self, app, accounts):
        from studentapp.models.audit_log import AuditLog

        before = AuditLog.query.filter_by(action="CHANGE_ROLE").count()
        user_service.change_role(
            accounts["teacher"].id, "TEACHER", actor_id=accounts["root"].id
        )
        after = AuditLog.query.filter_by(action="CHANGE_ROLE").count()
        assert before == after

class TestRootAdminProtection:
    def test_demote_root_blocked(self, app, accounts):
        with pytest.raises(PermissionDeniedError) as exc:
            user_service.change_role(
                accounts["root"].id, "STAFF", actor_id=accounts["root"].id
            )
        assert exc.value.status_code == 403

    def test_lock_root_blocked(self, app, accounts):
        with pytest.raises(PermissionDeniedError):
            user_service.lock(
                accounts["root"].id, actor_id=accounts["admin"].id
            )

    def test_reset_password_root_blocked(self, app, accounts):

        with pytest.raises(PermissionDeniedError) as exc:
            user_service.reset_password(
                accounts["root"].id, "Hacker@123", actor_id=accounts["admin"].id
            )
        assert exc.value.status_code == 403

    def test_reset_password_root_blocked_even_for_root_actor(self, app, accounts):

        with pytest.raises(PermissionDeniedError):
            user_service.reset_password(
                accounts["root"].id, "Hacker@123", actor_id=accounts["root"].id
            )

    def test_unlock_root_blocked(self, app, accounts):
        with pytest.raises(PermissionDeniedError):
            user_service.unlock(
                accounts["root"].id, actor_id=accounts["admin"].id
            )

    def test_root_password_unchanged_after_blocked_reset(self, app, accounts):

        with pytest.raises(PermissionDeniedError):
            user_service.reset_password(
                accounts["root"].id, "Hacker@123", actor_id=accounts["admin"].id
            )
        db.session.refresh(accounts["root"])
        assert accounts["root"].check_password("Test@123") is True

    def test_change_root_email_blocked_for_other_admin(self, app, accounts):

        with pytest.raises(PermissionDeniedError):
            user_service.update_info(
                accounts["root"].id,
                {"email": "attacker@evil.local"},
                actor_id=accounts["admin"].id,
            )

    def test_admin_cannot_demote_other_admin(self, app, accounts):

        other = User(
            username="hv02",
            email="hv02@school.local",
            full_name="HV02",
            role=UserRoleEnum.ACADEMIC,
        )
        other.set_password("Test@123")
        db.session.add(other)
        db.session.commit()
        with pytest.raises(PermissionDeniedError):
            user_service.change_role(
                other.id, "STAFF", actor_id=accounts["admin"].id
            )

    def test_non_academic_target_is_not_root_protected(self, app, accounts):

        out = user_service.reset_password(
            accounts["staff"].id, "MoiMK@123", actor_id=accounts["root"].id
        )
        assert out.must_change_password is True

class TestChangeRoleApi:
    def test_requires_token(self, client, accounts):
        res = client.put(f"/api/v1/admin/users/{accounts['teacher'].id}/role",
                         json={"role": "STAFF"})
        assert res.status_code == 401

    def test_forbidden_for_non_academic(self, client, accounts, headers):
        res = client.put(f"/api/v1/admin/users/{accounts['staff'].id}/role",
                         json={"role": "TEACHER"},
                         headers=headers(accounts["teacher"]))
        assert res.status_code == 403

    def test_academic_can_change_role(self, client, accounts, headers):
        res = client.put(f"/api/v1/admin/users/{accounts['teacher'].id}/role",
                         json={"role": "STAFF"},
                         headers=headers(accounts["root"]))
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert body["data"]["role"] == "STAFF"

    def test_api_blocks_demote_root(self, client, accounts, headers):
        res = client.put(f"/api/v1/admin/users/{accounts['root'].id}/role",
                         json={"role": "STAFF"},
                         headers=headers(accounts["root"]))
        assert res.status_code == 403

    def test_api_blocks_reset_password_root(self, client, accounts, headers):
        res = client.post(
            f"/api/v1/admin/users/{accounts['root'].id}/reset-password",
            json={"new_password": "Hacker@123"},
            headers=headers(accounts["admin"]),
        )
        assert res.status_code == 403

    def test_api_blocks_promote_second_academic(self, client, accounts, headers):
        res = client.put(f"/api/v1/admin/users/{accounts['staff'].id}/role",
                         json={"role": "ACADEMIC"},
                         headers=headers(accounts["root"]))
        assert res.status_code == 422

    def test_api_invalid_role_returns_400(self, client, accounts, headers):
        res = client.put(f"/api/v1/admin/users/{accounts['teacher'].id}/role",
                         json={"role": "ROOT"},
                         headers=headers(accounts["root"]))
        assert res.status_code == 400

class TestFlaskAdminNoUserPanel:
    def test_admin_user_panel_route_absent(self, app):

        routes = {str(r) for r in app.url_map.iter_rules()}
        assert "/admin/users/" not in routes
        assert not any(r.startswith("/admin/users") for r in routes)

    def test_audit_log_panel_still_present(self, app):
        routes = {str(r) for r in app.url_map.iter_rules()}
        assert "/admin/audit-logs/" in routes
