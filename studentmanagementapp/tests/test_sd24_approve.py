"""Test SD24 — Duyệt & chốt bảng điểm (Giáo vụ).

Bao phủ:
* Service: approve → scores is_draft=FALSE + assignment is_locked=TRUE cùng
  transaction, audit + outbox được ghi; reject → giữ nháp + bắt buộc lý do;
  chỉ xử lý đơn PENDING (đơn đã duyệt/từ chối/hủy → 409).
* API: 401 thiếu token, 403 sai role, ACADEMIC duyệt/từ chối đủ vòng.
"""
import pytest

from studentapp.models.score_submission import SubmissionStatusEnum
from studentapp.services import score_service, submission_service


def _fill_all_scores(seed_data, value=8.0):
    rows = []
    for st in seed_data["students"]:
        rows.append({
            "student_id": st.id,
            "score_15m_1": value, "score_15m_2": value, "score_15m_3": value,
            "score_15m_4": value, "score_15m_5": value,
            "score_45m_1": value, "score_45m_2": value, "score_45m_3": value,
            "score_final": value,
        })
    score_service.save_batch_scores(
        {"assignment_id": seed_data["assignment"].id, "scores": rows},
        seed_data["teacher"].id,
    )


def _make_pending(seed_data):
    _fill_all_scores(seed_data)
    return score_service.create_submission(
        {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
    )


class TestApproveService:
    def test_approve_locks_and_finalizes(self, app, seed_data):
        sub = _make_pending(seed_data)
        out = submission_service.approve_submission(
            sub["submission_id"], {"review_note": "OK"},
            reviewer_id=seed_data["academic"].id,
        )
        assert out["status"] == SubmissionStatusEnum.APPROVED
        assert out["is_locked"] is True
        # scores → chính thức
        from studentapp.repositories import score_repository

        rows = score_repository.list_by_assignment(
            seed_data["assignment"].id, draft_only=False
        )
        assert len(rows) == 3
        assert all(r.is_draft is False for r in rows)
        # không còn bản nháp
        assert score_repository.list_by_assignment(
            seed_data["assignment"].id, draft_only=True
        ) == []

    def test_approve_writes_audit_and_outbox(self, app, seed_data):
        from studentapp.models.audit_log import AuditLog
        from studentapp.models.email_outbox import EmailOutbox

        sub = _make_pending(seed_data)
        submission_service.approve_submission(
            sub["submission_id"], {}, reviewer_id=seed_data["academic"].id
        )
        audit = (
            AuditLog.query.filter_by(action="SCORE_TABLE_APPROVED")
            .order_by(AuditLog.id.desc()).first()
        )
        assert audit is not None
        assert audit.details["assignment_id"] == seed_data["assignment"].id
        mail = (
            EmailOutbox.query.filter_by(related_type="score_submission",
                                        related_id=sub["submission_id"])
            .order_by(EmailOutbox.id.desc()).first()
        )
        assert mail is not None
        assert mail.is_sent is False
        assert "duyệt" in mail.subject.lower()

    def test_reject_keeps_draft_requires_note(self, app, seed_data):
        from studentapp.exceptions import ValidationError
        from studentapp.repositories import score_repository

        sub = _make_pending(seed_data)
        with pytest.raises(ValidationError):
            submission_service.reject_submission(
                sub["submission_id"], {}, reviewer_id=seed_data["academic"].id
            )
        out = submission_service.reject_submission(
            sub["submission_id"], {"review_note": "Còn thiếu điểm"},
            reviewer_id=seed_data["academic"].id,
        )
        assert out["status"] == SubmissionStatusEnum.REJECTED
        assert out["is_locked"] is False
        assert len(score_repository.list_by_assignment(
            seed_data["assignment"].id, draft_only=True)) == 3

    def test_only_pending_can_be_reviewed(self, app, seed_data):
        from studentapp.exceptions import InvalidSubmissionStatusError

        sub = _make_pending(seed_data)
        submission_service.approve_submission(
            sub["submission_id"], {}, reviewer_id=seed_data["academic"].id
        )
        with pytest.raises(InvalidSubmissionStatusError):
            submission_service.approve_submission(
                sub["submission_id"], {}, reviewer_id=seed_data["academic"].id
            )
        with pytest.raises(InvalidSubmissionStatusError):
            submission_service.reject_submission(
                sub["submission_id"], {"review_note": "x"},
                reviewer_id=seed_data["academic"].id,
            )


class TestApproveEndpoints:
    def test_requires_authentication(self, app, client, seed_data):
        assert client.get("/api/v1/score-submissions").status_code == 401

    def test_teacher_forbidden(self, app, client, seed_data, auth_headers):
        resp = client.get(
            "/api/v1/score-submissions",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_academic_list_and_approve_roundtrip(
        self, app, client, seed_data, auth_headers
    ):
        sub = _make_pending(seed_data)
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        r = client.get("/api/v1/score-submissions?status=PENDING", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["total"] >= 1
        r = client.get(f"/api/v1/score-submissions/{sub['submission_id']}", headers=h)
        assert r.status_code == 200
        body = r.get_json()["data"]
        assert body["draft_count"] == 3
        r = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/approve",
            json={"review_note": "OK"}, headers=h,
        )
        assert r.status_code == 200, r.get_json()
        assert r.get_json()["data"]["status"] == "APPROVED"
        # duyệt lần 2 → 409
        r = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/approve",
            json={}, headers=h,
        )
        assert r.status_code == 409

    def test_academic_reject_roundtrip(self, app, client, seed_data, auth_headers):
        sub = _make_pending(seed_data)
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        r = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/reject",
            json={}, headers=h,
        )
        assert r.status_code == 400  # thiếu lý do
        r = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/reject",
            json={"review_note": "Thiếu điểm"}, headers=h,
        )
        assert r.status_code == 200
        assert r.get_json()["data"]["status"] == "REJECTED"
