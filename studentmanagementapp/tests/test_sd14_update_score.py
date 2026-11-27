import pytest

from studentapp.extensions import db
from studentapp.models.audit_log import AuditLog
from studentapp.models.score import Score
from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum
from studentapp.services import score_service

def _seed_score(seed_data, **values):

    st = seed_data["students"][0]
    row = Score(
        assignment_id=seed_data["assignment"].id,
        student_id=st.id,
        is_draft=True,
        **values,
    )
    db.session.add(row)
    db.session.commit()
    return row

class TestUpdateScoreCell:

    def test_updates_single_cell(self, app, seed_data):

        row = _seed_score(seed_data, score_15m_1=8.0, score_15m_2=9.0)
        result = score_service.update_score_cell(
            row.id,
            {"score_column": "score_15m_1", "new_value": 7.0},
            seed_data["teacher"].id,
        )
        assert result["new_value"] == 7.0
        assert result["old_value"] == 8.0
        db.session.refresh(row)
        assert float(row.score_15m_1) == 7.0
        assert float(row.score_15m_2) == 9.0

    def test_recalculates_average(self, app, seed_data):

        row = _seed_score(seed_data, score_15m_1=8.0)
        result = score_service.update_score_cell(
            row.id,
            {"score_column": "score_15m_1", "new_value": 4.0},
            seed_data["teacher"].id,
        )
        assert result["average_score"] == pytest.approx(4.0)
        assert result["is_passed"] is False

    def test_clear_sets_null(self, app, seed_data):

        row = _seed_score(seed_data, score_15m_1=8.0, score_15m_2=9.0)
        result = score_service.update_score_cell(
            row.id, {"score_column": "score_15m_1", "clear": True}, seed_data["teacher"].id
        )
        assert result["new_value"] is None
        db.session.refresh(row)
        assert row.score_15m_1 is None
        assert float(row.score_15m_2) == 9.0

    def test_clear_recalculates_average_excluding_cleared_cell(self, app, seed_data):

        row = _seed_score(seed_data, score_15m_1=8.0, score_45m_1=6.0)
        result = score_service.update_score_cell(
            row.id, {"score_column": "score_15m_1", "clear": True}, seed_data["teacher"].id
        )

        assert result["average_score"] == pytest.approx(6.0)

    def test_writes_audit_log(self, app, seed_data):

        row = _seed_score(seed_data, score_15m_1=8.0)
        score_service.update_score_cell(
            row.id,
            {"score_column": "score_15m_1", "new_value": 6.0},
            seed_data["teacher"].id,
        )
        log = AuditLog.query.filter_by(action="UPDATE_SCORE").first()
        assert log is not None
        assert log.details["old_value"] == 8.0
        assert log.details["new_value"] == 6.0
        assert log.details["score_column"] == "score_15m_1"

class TestUpdateScoreValidation:

    def test_rejects_invalid_column(self, app, seed_data):

        from studentapp.exceptions import InvalidColumnNameError

        row = _seed_score(seed_data, score_15m_1=8.0)
        with pytest.raises(InvalidColumnNameError):
            score_service.update_score_cell(
                row.id,
                {"score_column": "score_hack", "new_value": 5.0},
                seed_data["teacher"].id,
            )

    def test_rejects_out_of_range_value(self, app, seed_data):

        from studentapp.exceptions import InvalidScoreRangeError

        row = _seed_score(seed_data, score_15m_1=8.0)
        with pytest.raises(InvalidScoreRangeError):
            score_service.update_score_cell(
                row.id, {"score_column": "score_15m_1", "new_value": 15.0}, seed_data["teacher"].id
            )

    def test_requires_new_value_without_clear(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        row = _seed_score(seed_data, score_15m_1=8.0)
        with pytest.raises(ValidationError):
            score_service.update_score_cell(
                row.id, {"score_column": "score_15m_1"}, seed_data["teacher"].id
            )
        db.session.refresh(row)
        assert float(row.score_15m_1) == 8.0

    def test_404_for_missing_score(self, app, seed_data):

        from studentapp.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            score_service.update_score_cell(
                999999,
                {"score_column": "score_15m_1", "new_value": 5.0},
                seed_data["teacher"].id,
            )

class TestUpdateScoreAuthorization:

    def test_forbidden_for_other_teacher(self, app, seed_data):

        from studentapp.exceptions import PermissionDeniedError

        row = _seed_score(seed_data, score_15m_1=8.0)
        with pytest.raises(PermissionDeniedError):
            score_service.update_score_cell(
                row.id,
                {"score_column": "score_15m_1", "new_value": 5.0},
                seed_data["other_teacher"].id,
            )

    def test_forbidden_when_locked(self, app, seed_data):

        from studentapp.exceptions import ScoreTableLockedError

        row = _seed_score(seed_data, score_15m_1=8.0)
        seed_data["assignment"].is_locked = True
        db.session.commit()
        with pytest.raises(ScoreTableLockedError):
            score_service.update_score_cell(
                row.id,
                {"score_column": "score_15m_1", "new_value": 5.0},
                seed_data["teacher"].id,
            )

    def test_forbidden_when_submission_pending(self, app, seed_data):

        from studentapp.exceptions import ScoreSubmissionPendingError

        row = _seed_score(seed_data, score_15m_1=8.0)
        db.session.add(
            ScoreSubmission(
                assignment_id=seed_data["assignment"].id,
                teacher_id=seed_data["teacher"].id,
                status=SubmissionStatusEnum.PENDING,
            )
        )
        db.session.commit()
        with pytest.raises(ScoreSubmissionPendingError):
            score_service.update_score_cell(
                row.id,
                {"score_column": "score_15m_1", "new_value": 5.0},
                seed_data["teacher"].id,
            )

class TestUpdateScoreEndpoint:

    def test_requires_authentication(self, app, client):
        resp = client.put("/api/v1/scores/1", json={})
        assert resp.status_code == 401

    def test_teacher_updates_score(self, app, client, seed_data, auth_headers):
        row = _seed_score(seed_data, score_15m_1=8.0)
        resp = client.put(
            f"/api/v1/scores/{row.id}",
            json={"score_column": "score_15m_1", "new_value": 6.5},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["new_value"] == 6.5

    def test_invalid_column_returns_422(self, app, client, seed_data, auth_headers):
        row = _seed_score(seed_data, score_15m_1=8.0)
        resp = client.put(
            f"/api/v1/scores/{row.id}",
            json={"score_column": "score_hack", "new_value": 6.5},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"] == "INVALID_COLUMN_NAME"

    def test_locked_returns_423(self, app, client, seed_data, auth_headers):
        row = _seed_score(seed_data, score_15m_1=8.0)
        seed_data["assignment"].is_locked = True
        db.session.commit()
        resp = client.put(
            f"/api/v1/scores/{row.id}",
            json={"score_column": "score_15m_1", "new_value": 6.5},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 423
        assert resp.get_json()["error"] == "SCORE_TABLE_LOCKED"
