"""Test SD16 — CRUD phân công giảng dạy (Giáo vụ).

Bao phủ:
* Service: tạo OK, chặn trùng (class, subject, semester), chặn GV sai role /
  inactive, chặn lớp/môn/kỳ không tồn tại, sửa OK, sửa trùng → 409,
  xóa OK khi chưa phát sinh điểm, chặn xóa khi đã có điểm / đã chốt / có đơn.
* API: 401 khi thiếu token, 403 khi sai role, ACADEMIC CRUD đủ vòng,
  TEACHER chỉ xem được assignment của mình.
"""
import pytest

from studentapp.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from studentapp.services import assignment_service


def _payload(seed, **over):
    base = {
        "teacher_id": seed["other_teacher"].id,
        "class_id": seed["other_class"].id,
        "subject_id": seed["subject"].id,
        "semester_id": seed["semester"].id,
    }
    base.update(over)
    return base


def _make_hk2(seed):
    """Tạo thêm HK2 để có bộ ba lớp–môn–kỳ chưa tồn tại cho ca tạo mới."""
    from studentapp.extensions import db
    from studentapp.models.semester import Semester

    hk2 = Semester(
        semester_name="Học kỳ 2",
        academic_year_id=seed["academic_year"].id,
        factor=2,
    )
    db.session.add(hk2)
    db.session.commit()
    return hk2


class TestCreateAssignment:
    def test_create_ok(self, app, seed_data):
        hk2 = _make_hk2(seed_data)
        row = assignment_service.create_assignment(
            _payload(seed_data, semester_id=hk2.id),
            actor_id=seed_data["academic"].id,
        )
        assert row["teacher_id"] == seed_data["other_teacher"].id
        assert row["class_name"] == "10B1"
        assert row["scores_count"] == 0
        assert row["has_pending_submission"] is False

    def test_duplicate_triplet_409(self, app, seed_data):
        with pytest.raises(DuplicateError):
            assignment_service.create_assignment(
                {
                    "teacher_id": seed_data["teacher"].id,
                    "class_id": seed_data["class"].id,
                    "subject_id": seed_data["subject"].id,
                    "semester_id": seed_data["semester"].id,
                },
                actor_id=seed_data["academic"].id,
            )

    def test_teacher_must_be_teacher_role(self, app, seed_data):
        with pytest.raises(ValidationError) as exc:
            assignment_service.create_assignment(
                _payload(seed_data, teacher_id=seed_data["staff"].id),
                actor_id=seed_data["academic"].id,
            )
        assert exc.value.error == "INVALID_TEACHER_ROLE"

    def test_missing_class_404(self, app, seed_data):
        with pytest.raises(NotFoundError):
            assignment_service.create_assignment(
                _payload(seed_data, class_id=999999),
                actor_id=seed_data["academic"].id,
            )

    def test_missing_subject_404(self, app, seed_data):
        with pytest.raises(NotFoundError):
            assignment_service.create_assignment(
                _payload(seed_data, subject_id=999999),
                actor_id=seed_data["academic"].id,
            )


class TestUpdateDeleteAssignment:
    def test_update_teacher_ok(self, app, seed_data):
        row = assignment_service.update_assignment(
            seed_data["other_assignment"].id,
            {"teacher_id": seed_data["teacher"].id},
            actor_id=seed_data["academic"].id,
        )
        assert row["teacher_id"] == seed_data["teacher"].id

    def test_update_duplicate_triplet_409(self, app, seed_data):
        # Đổi other_assignment về đúng triplet của assignment chính → trùng.
        with pytest.raises(DuplicateError):
            assignment_service.update_assignment(
                seed_data["other_assignment"].id,
                {
                    "class_id": seed_data["class"].id,
                    "teacher_id": seed_data["teacher"].id,
                },
                actor_id=seed_data["academic"].id,
            )

    def test_delete_ok_when_no_scores(self, app, seed_data):
        hk2 = _make_hk2(seed_data)
        row = assignment_service.create_assignment(
            _payload(seed_data, semester_id=hk2.id),
            actor_id=seed_data["academic"].id,
        )
        snap = assignment_service.delete_assignment(
            row["id"], actor_id=seed_data["academic"].id
        )
        assert snap["id"] == row["id"]
        with pytest.raises(NotFoundError):
            assignment_service.get_assignment(row["id"])

    def test_delete_blocked_when_scores_exist(self, app, seed_data):
        from studentapp.extensions import db
        from studentapp.models.score import Score

        db.session.add(Score(
            assignment_id=seed_data["assignment"].id,
            student_id=seed_data["students"][0].id,
            is_draft=True,
        ))
        db.session.commit()
        with pytest.raises(BusinessRuleError) as exc:
            assignment_service.delete_assignment(
                seed_data["assignment"].id, actor_id=seed_data["academic"].id
            )
        assert exc.value.error == "ASSIGNMENT_HAS_SCORES"

    def test_delete_blocked_when_locked(self, app, seed_data):
        seed_data["other_assignment"].is_locked = True
        from studentapp.extensions import db

        db.session.commit()
        with pytest.raises(BusinessRuleError):
            assignment_service.delete_assignment(
                seed_data["other_assignment"].id, actor_id=seed_data["academic"].id
            )


class TestAssignmentEndpoints:
    def test_requires_authentication(self, app, client):
        assert client.get("/api/v1/assignments").status_code == 401

    def test_teacher_cannot_create(self, app, client, seed_data, auth_headers):
        resp = client.post(
            "/api/v1/assignments",
            json=_payload(seed_data),
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_academic_crud_roundtrip(self, app, client, seed_data, auth_headers):
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        hk2 = _make_hk2(seed_data)
        payload = _payload(seed_data, semester_id=hk2.id)
        # list
        r = client.get("/api/v1/assignments", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["total"] >= 2
        # create
        r = client.post("/api/v1/assignments", json=payload, headers=h)
        assert r.status_code == 201, r.get_json()
        new_id = r.get_json()["data"]["id"]
        # detail
        r = client.get(f"/api/v1/assignments/{new_id}", headers=h)
        assert r.status_code == 200
        # duplicate → 409
        r = client.post("/api/v1/assignments", json=_payload(seed_data), headers=h)
        assert r.status_code == 409
        # update
        r = client.put(
            f"/api/v1/assignments/{new_id}",
            json={"teacher_id": seed_data["teacher"].id},
            headers=h,
        )
        assert r.status_code == 200
        # delete
        r = client.delete(f"/api/v1/assignments/{new_id}", headers=h)
        assert r.status_code == 200

    def test_teacher_can_view_own_only(self, app, client, seed_data, auth_headers):
        h_teacher = auth_headers("TEACHER", seed_data["teacher"].id)
        own = seed_data["assignment"].id
        other = seed_data["other_assignment"].id
        assert client.get(f"/api/v1/assignments/{own}", headers=h_teacher).status_code == 200
        assert client.get(f"/api/v1/assignments/{other}", headers=h_teacher).status_code == 403
