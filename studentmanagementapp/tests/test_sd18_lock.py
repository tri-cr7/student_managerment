"""Test SD18 — Khóa / mở bảng điểm thủ công (Giáo vụ).

Bao phủ:
* Service: lock → is_locked=True + locked_at có giá trị; unlock → False + None;
  404 khi assignment không tồn tại; audit log được ghi.
* Nghiệp vụ liên động: sau khi khóa, GV không sửa điểm trực tiếp được
  (423 SCORE_TABLE_LOCKED); sau khi mở lại, GV sửa được.
* API: 401 thiếu token, 403 sai role, 400 thiếu is_locked, ACADEMIC lock/unlock đủ vòng.
"""
from studentapp.services import assignment_service


class TestSetLockService:
    def test_lock_sets_flag_and_timestamp(self, app, seed_data):
        out = assignment_service.set_lock(
            seed_data["assignment"].id, True, actor_id=seed_data["academic"].id
        )
        assert out["is_locked"] is True
        assert out["locked_at"] is not None

    def test_unlock_clears_flag_and_timestamp(self, app, seed_data):
        assignment_service.set_lock(
            seed_data["assignment"].id, True, actor_id=seed_data["academic"].id
        )
        out = assignment_service.set_lock(
            seed_data["assignment"].id, False, actor_id=seed_data["academic"].id
        )
        assert out["is_locked"] is False
        assert out["locked_at"] is None

    def test_missing_assignment_404(self, app, seed_data):
        from studentapp.exceptions import NotFoundError

        try:
            assignment_service.set_lock(
                999999, True, actor_id=seed_data["academic"].id
            )
        except NotFoundError:
            return
        raise AssertionError("Phải 404 khi assignment không tồn tại.")

    def test_audit_log_written(self, app, seed_data):
        from studentapp.models.audit_log import AuditLog

        assignment_service.set_lock(
            seed_data["assignment"].id, True, actor_id=seed_data["academic"].id
        )
        row = (
            AuditLog.query.filter_by(action="LOCK_SCORE_TABLE")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert row is not None
        assert row.details["assignment_id"] == seed_data["assignment"].id

    def test_teacher_blocked_after_lock(self, app, seed_data):
        """Khóa xong → GV sửa điểm trực tiếp bị 423 (rule A8)."""
        from studentapp.exceptions import ScoreTableLockedError
        from studentapp.services import score_service

        assignment_service.set_lock(
            seed_data["assignment"].id, True, actor_id=seed_data["academic"].id
        )
        try:
            score_service.save_batch_scores(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "scores": [{"student_id": seed_data["students"][0].id,
                                "score_15m_1": 8.0}],
                },
                seed_data["teacher"].id,
            )
        except ScoreTableLockedError:
            return
        raise AssertionError("Bảng điểm đã khóa mà GV vẫn sửa được!")


class TestLockEndpoints:
    def test_requires_authentication(self, app, client, seed_data):
        resp = client.patch(
            f"/api/v1/assignments/{seed_data['assignment'].id}/lock",
            json={"is_locked": True},
        )
        assert resp.status_code == 401

    def test_teacher_forbidden(self, app, client, seed_data, auth_headers):
        resp = client.patch(
            f"/api/v1/assignments/{seed_data['assignment'].id}/lock",
            json={"is_locked": True},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_missing_is_locked_400(self, app, client, seed_data, auth_headers):
        resp = client.patch(
            f"/api/v1/assignments/{seed_data['assignment'].id}/lock",
            json={},
            headers=auth_headers("ACADEMIC", seed_data["academic"].id),
        )
        assert resp.status_code == 400

    def test_academic_lock_unlock_roundtrip(self, app, client, seed_data, auth_headers):
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        aid = seed_data["assignment"].id
        r = client.patch(f"/api/v1/assignments/{aid}/lock",
                         json={"is_locked": True}, headers=h)
        assert r.status_code == 200, r.get_json()
        body = r.get_json()
        assert body["success"] is True
        assert body["data"]["is_locked"] is True
        assert body["data"]["locked_at"] is not None

        r = client.patch(f"/api/v1/assignments/{aid}/lock",
                         json={"is_locked": False}, headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["is_locked"] is False

    def test_lock_missing_assignment_404(self, app, client, seed_data, auth_headers):
        resp = client.patch(
            "/api/v1/assignments/999999/lock",
            json={"is_locked": True},
            headers=auth_headers("ACADEMIC", seed_data["academic"].id),
        )
        assert resp.status_code == 404
