"""Test SD19 — Phê duyệt phúc khảo từng ô (Giáo vụ).

Bao phủ:
* Service: đơn lẻ duyệt mặc định OK (giữ is_draft=FALSE, không đụng is_locked,
  tính lại ĐTB); đơn lô thiếu decisions → 422 DECISIONS_REQUIRED; duyệt từng ô
  (1 APPROVE + 1 REJECT → PARTIALLY_APPROVED); từ chối toàn bộ giữ nguyên điểm;
  audit + outbox được ghi; đơn đã xử lý không duyệt lại.
* API: 401/403, ACADEMIC duyệt/từ chối đủ vòng, diff lọc theo trạng thái.
"""
import pytest

from studentapp.exceptions import ValidationError
from studentapp.extensions import db
from studentapp.models.score import Score
from studentapp.models.score_change_request import ChangeRequestStatusEnum
from studentapp.services import change_review_service, score_service


def _seed_locked_scores(seed_data):
    rows = []
    for i, st in enumerate(seed_data["students"]):
        rows.append({
            "student_id": st.id,
            "score_15m_1": 7.0 + i, "score_15m_2": 8.0, "score_final": 8.5,
        })
    score_service.save_batch_scores(
        {"assignment_id": seed_data["assignment"].id, "scores": rows},
        seed_data["teacher"].id,
    )
    for row in Score.query.filter_by(assignment_id=seed_data["assignment"].id).all():
        row.is_draft = False
        db.session.add(row)
    seed_data["assignment"].is_locked = True
    db.session.commit()


def _make_single(seed_data, column="score_15m_1", new_value=9.0, student_idx=0):
    _seed_locked_scores(seed_data)
    st = seed_data["students"][student_idx]
    return score_service.create_change_request(
        {
            "assignment_id": seed_data["assignment"].id,
            "reason": "Chấm nhầm.",
            "changes": [{"student_id": st.id, "score_column": column,
                         "new_value": new_value}],
        },
        seed_data["teacher"].id,
    )


def _make_batch(seed_data):
    _seed_locked_scores(seed_data)
    s1, s2 = seed_data["students"][0], seed_data["students"][1]
    return score_service.create_change_request(
        {
            "assignment_id": seed_data["assignment"].id,
            "reason": "Chấm lại 2 ô.",
            "changes": [
                {"student_id": s1.id, "score_column": "score_15m_1", "new_value": 9.0},
                {"student_id": s2.id, "score_column": "score_final", "new_value": 9.5},
            ],
        },
        seed_data["teacher"].id,
    )


class TestApproveService:
    def test_approve_single_keeps_official(self, app, seed_data):
        req = _make_single(seed_data)
        out = change_review_service.approve_request(
            req["request_id"], {}, reviewer_id=seed_data["academic"].id
        )
        assert out["status"] == ChangeRequestStatusEnum.APPROVED
        assert out["approved_count"] == 1
        row = Score.query.filter_by(
            assignment_id=seed_data["assignment"].id,
            student_id=seed_data["students"][0].id,
        ).first()
        assert float(row.score_15m_1) == 9.0
        assert row.is_draft is False  # giữ nguyên điểm chính thức
        assert bool(seed_data["assignment"].is_locked) is True  # vẫn chốt
        assert row.average_score is not None

    def test_batch_requires_decisions(self, app, seed_data):
        from studentapp.exceptions import DecisionsRequiredError

        req = _make_batch(seed_data)
        with pytest.raises(DecisionsRequiredError) as exc:
            change_review_service.approve_request(
                req["request_id"], {}, reviewer_id=seed_data["academic"].id
            )
        assert exc.value.error == "DECISIONS_REQUIRED"

    def test_partial_approve_batch(self, app, seed_data):
        req = _make_batch(seed_data)
        details = {d["score_column"]: d["detail_id"] for d in req["details"]}
        out = change_review_service.approve_request(
            req["request_id"],
            {"decisions": [
                {"detail_id": details["score_15m_1"], "action": "APPROVE"},
                {"detail_id": details["score_final"], "action": "REJECT",
                 "note": "Không có bằng chứng"},
            ], "approval_note": "Đã đối chiếu"},
            reviewer_id=seed_data["academic"].id,
        )
        assert out["status"] == ChangeRequestStatusEnum.PARTIALLY_APPROVED
        assert out["approved_count"] == 1
        assert out["rejected_count"] == 1
        # Ô duyệt được áp, ô từ chối giữ nguyên
        r1 = Score.query.filter_by(
            assignment_id=seed_data["assignment"].id,
            student_id=seed_data["students"][0].id).first()
        r2 = Score.query.filter_by(
            assignment_id=seed_data["assignment"].id,
            student_id=seed_data["students"][1].id).first()
        assert float(r1.score_15m_1) == 9.0
        assert float(r2.score_final) == 8.5

    def test_reject_all_keeps_scores(self, app, seed_data):
        req = _make_single(seed_data)
        with pytest.raises(ValidationError):
            change_review_service.reject_request(
                req["request_id"], {}, reviewer_id=seed_data["academic"].id
            )
        out = change_review_service.reject_request(
            req["request_id"], {"rejection_note": "Không đủ căn cứ"},
            reviewer_id=seed_data["academic"].id,
        )
        assert out["status"] == ChangeRequestStatusEnum.REJECTED
        row = Score.query.filter_by(
            assignment_id=seed_data["assignment"].id,
            student_id=seed_data["students"][0].id).first()
        assert float(row.score_15m_1) == 7.0

    def test_audit_and_outbox_written(self, app, seed_data):
        from studentapp.models.audit_log import AuditLog
        from studentapp.models.email_outbox import EmailOutbox

        req = _make_single(seed_data)
        change_review_service.approve_request(
            req["request_id"], {}, reviewer_id=seed_data["academic"].id
        )
        audit = (AuditLog.query.filter_by(action="APPROVE_SCORE_CHANGE")
                 .order_by(AuditLog.id.desc()).first())
        assert audit is not None
        mail = (EmailOutbox.query
                .filter_by(related_type="score_change_request",
                           related_id=req["request_id"])
                .order_by(EmailOutbox.id.desc()).first())
        assert mail is not None and mail.is_sent is False

    def test_cannot_review_twice(self, app, seed_data):
        from studentapp.exceptions import BusinessRuleError

        req = _make_single(seed_data)
        change_review_service.approve_request(
            req["request_id"], {}, reviewer_id=seed_data["academic"].id
        )
        with pytest.raises(BusinessRuleError):
            change_review_service.approve_request(
                req["request_id"], {}, reviewer_id=seed_data["academic"].id
            )


class TestReviewEndpoints:
    def test_requires_authentication(self, app, client, seed_data):
        assert client.get("/api/v1/score-requests").status_code == 401

    def test_teacher_forbidden(self, app, client, seed_data, auth_headers):
        resp = client.get(
            "/api/v1/score-requests",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_academic_approve_roundtrip(self, app, client, seed_data, auth_headers):
        req = _make_batch(seed_data)
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        r = client.get("/api/v1/score-requests?status=PENDING", headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["total"] >= 1
        r = client.get(f"/api/v1/score-requests/{req['request_id']}/diff", headers=h)
        assert r.status_code == 200
        assert len(r.get_json()["data"]["changes"]) == 2
        # thiếu decisions → 422
        r = client.put(f"/api/v1/score-requests/{req['request_id']}/approve",
                       json={}, headers=h)
        assert r.status_code == 422
        details = {d["score_column"]: d["detail_id"] for d in req["details"]}
        r = client.put(
            f"/api/v1/score-requests/{req['request_id']}/approve",
            json={"decisions": [
                {"detail_id": details["score_15m_1"], "action": "APPROVE"},
                {"detail_id": details["score_final"], "action": "REJECT",
                 "note": "Giữ nguyên"},
            ]}, headers=h)
        assert r.status_code == 200, r.get_json()
        assert r.get_json()["data"]["status"] == "PARTIALLY_APPROVED"

    def test_academic_reject_roundtrip(self, app, client, seed_data, auth_headers):
        req = _make_single(seed_data)
        h = auth_headers("ACADEMIC", seed_data["academic"].id)
        r = client.put(f"/api/v1/score-requests/{req['request_id']}/reject",
                       json={}, headers=h)
        assert r.status_code == 400
        r = client.put(f"/api/v1/score-requests/{req['request_id']}/reject",
                       json={"rejection_note": "Không đủ căn cứ"}, headers=h)
        assert r.status_code == 200
        assert r.get_json()["data"]["status"] == "REJECTED"
