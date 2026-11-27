import pytest

from studentapp.extensions import db
from studentapp.models.score import Score
from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum
from studentapp.services import score_service

def _fill_all_scores(seed_data, value=8.0):

    rows = []
    for st in seed_data["students"]:
        rows.append(
            {
                "student_id": st.id,
                "score_15m_1": value,
                "score_15m_2": value,
                "score_15m_3": value,
                "score_15m_4": value,
                "score_15m_5": value,
                "score_45m_1": value,
                "score_45m_2": value,
                "score_45m_3": value,
                "score_final": value,
            }
        )
    score_service.save_batch_scores(
        {"assignment_id": seed_data["assignment"].id, "scores": rows},
        seed_data["teacher"].id,
    )

class TestCreateSubmission:

    def test_creates_pending_submission(self, app, seed_data):

        _fill_all_scores(seed_data)
        result = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        assert result["status"] == SubmissionStatusEnum.PENDING
        assert result["assignment_id"] == seed_data["assignment"].id
        assert result["total_students"] == 3
        assert result["total_scores"] == 27

    def test_blocks_further_edits(self, app, seed_data):

        from studentapp.exceptions import ScoreSubmissionPendingError

        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        with pytest.raises(ScoreSubmissionPendingError):
            score_service.save_batch_scores(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "scores": [{"student_id": seed_data["students"][0].id, "score_15m_1": 5.0}],
                },
                seed_data["teacher"].id,
            )

    def test_rejects_duplicate_pending_submission(self, app, seed_data):

        from studentapp.exceptions import DuplicatePendingSubmissionError

        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        with pytest.raises(DuplicatePendingSubmissionError):
            score_service.create_submission(
                {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
            )

    def test_rejects_when_scores_incomplete(self, app, seed_data):

        from studentapp.exceptions import IncompleteScoresError

        st = seed_data["students"][0]
        score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": 8.0}],
            },
            seed_data["teacher"].id,
        )
        with pytest.raises(IncompleteScoresError):
            score_service.create_submission(
                {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
            )

    def test_rejects_when_no_scores_at_all(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        with pytest.raises(ValidationError):
            score_service.create_submission(
                {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
            )

    def test_rejects_other_teacher_assignment(self, app, seed_data):

        from studentapp.exceptions import PermissionDeniedError

        with pytest.raises(PermissionDeniedError):
            score_service.create_submission(
                {"assignment_id": seed_data["other_assignment"].id},
                seed_data["teacher"].id,
            )

    def test_marks_submitted_at(self, app, seed_data):

        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        rows = Score.query.filter_by(assignment_id=seed_data["assignment"].id).all()
        assert all(r.submitted_at is not None for r in rows)

class TestCancelSubmission:

    def test_cancels_pending_submission(self, app, seed_data):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {
                "assignment_id": seed_data["assignment"].id,
                "note": "Gửi lần 1",
            },
            seed_data["teacher"].id,
        )
        result = score_service.cancel_submission(
            sub["submission_id"], {"cancel_note": "Nhập nhầm"}, seed_data["teacher"].id
        )
        assert result["status"] == SubmissionStatusEnum.CANCELLED
        assert result["cancel_note"] == "Nhập nhầm"
        assert result["cancelled_at"] is not None

    def test_cancelling_unlocks_editing(self, app, seed_data):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        score_service.cancel_submission(
            sub["submission_id"], {"cancel_note": "sửa lại"}, seed_data["teacher"].id
        )

        score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": seed_data["students"][0].id, "score_15m_1": 5.0}],
            },
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=seed_data["students"][0].id).first()
        assert float(row.score_15m_1) == 5.0

    def test_cancelling_keeps_draft_state(self, app, seed_data):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        score_service.cancel_submission(
            sub["submission_id"], {"cancel_note": "sửa lại"}, seed_data["teacher"].id
        )
        rows = Score.query.filter_by(assignment_id=seed_data["assignment"].id).all()
        assert all(r.is_draft is True for r in rows)
        assert seed_data["assignment"].is_locked is False

    def test_rejects_cancelling_approved_submission(self, app, seed_data):

        from studentapp.exceptions import InvalidSubmissionStatusError

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        row = db.session.get(ScoreSubmission, sub["submission_id"])
        row.status = SubmissionStatusEnum.APPROVED
        db.session.commit()

        with pytest.raises(InvalidSubmissionStatusError):
            score_service.cancel_submission(
                sub["submission_id"], {}, seed_data["teacher"].id
            )

    def test_rejects_cancelling_other_teacher_submission(self, app, seed_data):

        from studentapp.exceptions import PermissionDeniedError

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        with pytest.raises(PermissionDeniedError):
            score_service.cancel_submission(
                sub["submission_id"], {}, seed_data["other_teacher"].id
            )

    def test_404_for_missing_submission(self, app, seed_data):

        from studentapp.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            score_service.cancel_submission(999999, {}, seed_data["teacher"].id)

class TestSubmissionEndpoints:

    def test_create_endpoint(self, app, client, seed_data, auth_headers):
        _fill_all_scores(seed_data)
        resp = client.post(
            "/api/v1/score-submissions",
            json={"assignment_id": seed_data["assignment"].id},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["status"] == "PENDING"

    def test_create_endpoint_incomplete_returns_422(self, app, client, seed_data, auth_headers):
        st = seed_data["students"][0]
        score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": 8.0}],
            },
            seed_data["teacher"].id,
        )
        resp = client.post(
            "/api/v1/score-submissions",
            json={"assignment_id": seed_data["assignment"].id},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"] == "INCOMPLETE_SCORES"

    def test_cancel_endpoint(self, app, client, seed_data, auth_headers):
        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        resp = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={"cancel_note": "nhập nhầm"},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "CANCELLED"

    def test_cancel_endpoint_wrong_status_returns_409(self, app, client, seed_data, auth_headers):
        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        row = db.session.get(ScoreSubmission, sub["submission_id"])
        row.status = SubmissionStatusEnum.REJECTED
        db.session.commit()

        resp = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 409
        assert resp.get_json()["error"] == "INVALID_SUBMISSION_STATUS"

    def test_my_submissions_endpoint(self, app, client, seed_data, auth_headers):
        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        resp = client.get(
            "/api/v1/score-submissions/my",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]) == 1

    def test_my_submissions_includes_class_subject_info(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        resp = client.get(
            "/api/v1/score-submissions/my",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        item = resp.get_json()["data"][0]
        assert item["class_name"]
        assert item["subject_name"]
        assert item["semester_name"]
        assert item["submission_id"]

    def test_my_submissions_only_returns_own(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        resp = client.get(
            "/api/v1/score-submissions/my",
            headers=auth_headers("TEACHER", seed_data["other_teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"] == []
