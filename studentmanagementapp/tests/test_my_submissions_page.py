import pytest

from studentapp.extensions import db
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

class TestMySubmissionsList:

    def test_returns_only_own_submissions(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        resp = client.get(
            "/api/v1/score-submissions/my",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data) == 1
        assert data[0]["teacher_id"] == seed_data["teacher"].id

    def test_other_teacher_sees_nothing(self, app, client, seed_data, auth_headers):

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

    def test_enriched_with_class_subject_semester(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        resp = client.get(
            "/api/v1/score-submissions/my",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        item = resp.get_json()["data"][0]

        assert item["submission_id"]
        assert item["assignment_id"] == seed_data["assignment"].id
        assert item["class_name"]
        assert item["subject_name"]
        assert item["semester_name"]
        assert item["academic_year"]
        assert item["total_students"] == 3
        assert item["total_scores"] == 27
        assert item["status"] == SubmissionStatusEnum.PENDING
        assert item["is_locked"] is False
        assert item["submitted_at"]

    def test_ordered_newest_first(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        first = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        score_service.cancel_submission(
            first["submission_id"], {"cancel_note": "sửa lại"}, seed_data["teacher"].id
        )
        _fill_all_scores(seed_data, value=9.0)
        second = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        resp = client.get(
            "/api/v1/score-submissions/my",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        ids = [r["submission_id"] for r in resp.get_json()["data"]]
        assert ids[0] == second["submission_id"]
        assert ids[-1] == first["submission_id"]

    def test_blocked_for_staff_role(self, app, client, seed_data, auth_headers):

        resp = client.get(
            "/api/v1/score-submissions/my",
            headers=auth_headers("STAFF", seed_data["staff"].id),
        )
        assert resp.status_code == 403

class TestCancelFromMySubmissions:

    def test_cancel_pending_submission(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        resp = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == SubmissionStatusEnum.CANCELLED

    def test_cancel_reopens_gradebook_for_editing(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )

        score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": seed_data["students"][0].id, "score_15m_1": 9.0}],
            },
            seed_data["teacher"].id,
        )

        row = db.session.get(ScoreSubmission, sub["submission_id"])
        assert row.status == SubmissionStatusEnum.CANCELLED
        assert row.assignment.is_locked is False

    def test_cannot_cancel_other_teacher_submission(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        resp = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={},
            headers=auth_headers("TEACHER", seed_data["other_teacher"].id),
        )
        assert resp.status_code == 403
        row = db.session.get(ScoreSubmission, sub["submission_id"])
        assert row.status == SubmissionStatusEnum.PENDING

    def test_cancel_non_pending_returns_409(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        row = db.session.get(ScoreSubmission, sub["submission_id"])
        row.status = SubmissionStatusEnum.APPROVED
        db.session.commit()

        resp = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 409
        assert resp.get_json()["error"] == "INVALID_SUBMISSION_STATUS"
