import pytest

from studentapp.extensions import db
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.score import Score
from studentapp.models.score_change_request import ScoreChangeRequest
from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum
from studentapp.services import score_service

def _enroll(seed_data, student_id, class_id=None, status=EnrollmentStatusEnum.DANG_HOC):

    from datetime import date

    enrollment = ClassEnrollment.query.filter_by(
        student_id=student_id, class_id=class_id or seed_data["class"].id
    ).first()
    if enrollment is None:
        enrollment = ClassEnrollment(
            student_id=student_id,
            class_id=class_id or seed_data["class"].id,
            academic_year_id=seed_data["academic_year"].id,
            enrollment_date=date(2026, 9, 1),
            status=status,
        )
        db.session.add(enrollment)
    else:
        enrollment.status = status
    db.session.flush()
    return enrollment

def _new_student(seed_data, code, full_name):

    from datetime import date

    from studentapp.models.student import Student, StudentStatusEnum

    st = Student(
        student_code=code,
        full_name=full_name,
        gender="Nam",
        date_of_birth=date(2010, 4, 1),
        status=StudentStatusEnum.DANG_HOC,
    )
    db.session.add(st)
    db.session.flush()
    return st

def _all_columns(value=8.0):

    return {
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

def _fill_all_scores(seed_data, value=8.0):

    roster = [
        int(sid)
        for sid in ClassEnrollment.query.filter_by(
            class_id=seed_data["class"].id, status=EnrollmentStatusEnum.DANG_HOC
        ).all()
        for sid in [sid.student_id]
    ]
    rows = [{"student_id": sid, **_all_columns(value)} for sid in roster]
    if not rows:
        return
    score_service.save_batch_scores(
        {"assignment_id": seed_data["assignment"].id, "scores": rows},
        seed_data["teacher"].id,
    )

class TestStudentLeftClass:

    def test_transferred_student_excluded_from_gradebook(self, app, seed_data):

        st = seed_data["students"][0]
        _enroll(seed_data, st.id, status=EnrollmentStatusEnum.DA_CHUYEN)

        result = score_service.get_assignment_scores(
            seed_data["assignment"].id, seed_data["teacher"].id
        )
        shown = [r["student_id"] for r in result["score_list"]]
        assert st.id not in shown

        assert len(shown) == 2

    def test_transferred_student_not_returned_by_endpoint(self, app, client, seed_data,
                                                        auth_headers):

        st = seed_data["students"][0]
        _enroll(seed_data, st.id, status=EnrollmentStatusEnum.DA_CHUYEN)
        db.session.commit()

        resp = client.get(
            f"/api/v1/scores/assignment/{seed_data['assignment'].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        shown = [r["student_id"] for r in resp.get_json()["data"]["score_list"]]
        assert st.id not in shown

    def test_save_scores_succeeds_for_remaining_students(self, app, seed_data):

        departed = seed_data["students"][0]
        remaining = seed_data["students"][1]
        _enroll(seed_data, departed.id, status=EnrollmentStatusEnum.DA_CHUYEN)

        result = score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": remaining.id, "score_15m_1": 8.0}],
            },
            seed_data["teacher"].id,
        )
        assert result["data"]["updated_count"] == 1

        row = Score.query.filter_by(
            assignment_id=seed_data["assignment"].id, student_id=remaining.id
        ).first()
        assert row is not None
        assert float(row.score_15m_1) == 8.0

    def test_batch_with_transferred_student_is_skipped_not_blocked(
        self, app, client, seed_data, auth_headers
    ):

        departed = seed_data["students"][0]
        remaining = seed_data["students"][1]
        _enroll(seed_data, departed.id, status=EnrollmentStatusEnum.DA_CHUYEN)

        resp = client.post(
            "/api/v1/scores/batch",
            json={
                "assignment_id": seed_data["assignment"].id,
                "scores": [
                    {"student_id": departed.id, "score_15m_1": 7.0},
                    {"student_id": remaining.id, "score_15m_1": 8.0},
                ],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["updated_count"] == 1
        assert body["data"]["skipped_student_ids"] == [departed.id]

    def test_all_rows_invalid_still_raises_422(self, app, seed_data):

        for st in seed_data["students"]:
            _enroll(seed_data, st.id, status=EnrollmentStatusEnum.DA_CHUYEN)

        from studentapp.exceptions import StudentNotInAssignmentError

        with pytest.raises(StudentNotInAssignmentError):
            score_service.save_batch_scores(
                {
                    "assignment_id": seed_data["assignment"].id,
                    "scores": [{"student_id": seed_data["students"][0].id, "score_15m_1": 8.0}],
                },
                seed_data["teacher"].id,
            )

class TestNewlyEnrolledStudent:

    def test_new_student_appears_with_null_scores(self, app, seed_data):

        newcomer = _new_student(seed_data, "HS20269001", "Học Sinh Mới")
        _enroll(seed_data, newcomer.id)
        db.session.commit()

        result = score_service.get_assignment_scores(
            seed_data["assignment"].id, seed_data["teacher"].id
        )
        row = next(r for r in result["score_list"] if r["student_id"] == newcomer.id)

        assert row["student_code"] == "HS20269001"
        assert row["full_name"] == "Học Sinh Mới"
        assert row["average_score"] is None
        assert row["is_passed"] is None
        for col in (
            "score_15m_1", "score_15m_2", "score_15m_3", "score_15m_4", "score_15m_5",
            "score_45m_1", "score_45m_2", "score_45m_3", "score_final",
        ):
            assert row[col] is None

    def test_new_student_visible_via_endpoint(self, app, client, seed_data, auth_headers):

        newcomer = _new_student(seed_data, "HS20269002", "Học Sinh Mới 2")
        _enroll(seed_data, newcomer.id)
        db.session.commit()

        resp = client.get(
            f"/api/v1/scores/assignment/{seed_data['assignment'].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        rows = resp.get_json()["data"]["score_list"]
        row = next(r for r in rows if r["student_id"] == newcomer.id)
        assert row["score_15m_1"] is None
        assert row["average_score"] is None

    def test_teacher_can_grade_new_student_on_first_save(self, app, seed_data):

        newcomer = _new_student(seed_data, "HS20269003", "Học Sinh Mới 3")
        _enroll(seed_data, newcomer.id)

        result = score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": newcomer.id, "score_15m_1": 8.5}],
            },
            seed_data["teacher"].id,
        )
        assert result["data"]["updated_count"] == 1

        row = Score.query.filter_by(
            assignment_id=seed_data["assignment"].id, student_id=newcomer.id
        ).first()
        assert row is not None
        assert float(row.score_15m_1) == 8.5
        assert row.is_draft is True

    def test_new_student_gradeable_via_endpoint(self, app, client, seed_data,
                                                auth_headers):

        newcomer = _new_student(seed_data, "HS20269004", "Học Sinh Mới 4")
        _enroll(seed_data, newcomer.id)
        db.session.commit()

        resp = client.post(
            "/api/v1/scores/batch",
            json={
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": newcomer.id, "score_15m_1": 7.5}],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["updated_count"] == 1

    def test_roster_drives_grid_not_score_table(self, app, seed_data):

        newcomer = _new_student(seed_data, "HS20269005", "Học Sinh Mới 5")
        _enroll(seed_data, newcomer.id)

        result = score_service.get_assignment_scores(
            seed_data["assignment"].id, seed_data["teacher"].id
        )
        shown = [r["student_id"] for r in result["score_list"]]
        roster = [st.id for st in seed_data["students"]] + [newcomer.id]
        assert sorted(shown) == sorted(roster)

class TestAppealContract:

    def test_create_appeal_with_score_column(self, app, client, seed_data, auth_headers):

        st = seed_data["students"][0]
        _fill_all_scores(seed_data)

        seed_data["assignment"].is_locked = True
        db.session.commit()

        resp = client.post(
            "/api/v1/score-requests",
            json={
                "assignment_id": seed_data["assignment"].id,
                "reason": "Nhập nhầm điểm kiểm tra 15 phút",
                "changes": [
                    {
                        "student_id": st.id,
                        "score_column": "score_15m_1",
                        "new_value": 9.0,
                    }
                ],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["total_changes"] == 1

    def test_create_appeal_rejects_column_name_key(self, app, client, seed_data,
                                                    auth_headers):

        st = seed_data["students"][0]
        _fill_all_scores(seed_data)
        seed_data["assignment"].is_locked = True
        db.session.commit()

        resp = client.post(
            "/api/v1/score-requests",
            json={
                "assignment_id": seed_data["assignment"].id,
                "reason": "Nhập nhầm",
                "changes": [
                    {
                        "student_id": st.id,
                        "column_name": "score_15m_1",
                        "new_value": 9.0,
                    }
                ],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 422
        assert resp.get_json()["error"] == "INVALID_COLUMN_NAME"

    def test_appeal_detail_persisted_in_db(self, app, seed_data):

        st = seed_data["students"][0]
        _fill_all_scores(seed_data)
        seed_data["assignment"].is_locked = True
        db.session.commit()

        score_service.create_change_request(
            {
                "assignment_id": seed_data["assignment"].id,
                "reason": "Nhập nhầm điểm",
                "changes": [
                    {
                        "student_id": st.id,
                        "score_column": "score_15m_1",
                        "new_value": 9.0,
                    }
                ],
            },
            seed_data["teacher"].id,
        )

        request = ScoreChangeRequest.query.filter_by(
            assignment_id=seed_data["assignment"].id
        ).first()
        assert request is not None
        detail = request.details[0]
        assert detail.score_column == "score_15m_1"
        assert float(detail.new_value) == 9.0

class TestCancelSubmissionContract:

    def test_cancel_with_cancel_note_persisted(self, app, client, seed_data,
                                                auth_headers):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        resp = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={"cancel_note": "Nhập nhầm cột điểm 15 phút"},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "CANCELLED"

        row = db.session.get(ScoreSubmission, sub["submission_id"])
        assert row.status == SubmissionStatusEnum.CANCELLED
        assert row.cancel_note == "Nhập nhầm cột điểm 15 phút"
        assert row.cancelled_at is not None

    def test_cancel_with_reason_key_is_ignored(self, app, client, seed_data,
                                               auth_headers):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )

        resp = client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={"reason": "Nhập nhầm cột điểm 15 phút"},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200

        row = db.session.get(ScoreSubmission, sub["submission_id"])
        assert row.status == SubmissionStatusEnum.CANCELLED
        assert row.cancel_note is None

    def test_cancel_restores_editability(self, app, client, seed_data, auth_headers):

        _fill_all_scores(seed_data)
        sub = score_service.create_submission(
            {"assignment_id": seed_data["assignment"].id}, seed_data["teacher"].id
        )
        client.put(
            f"/api/v1/score-submissions/{sub['submission_id']}/cancel",
            json={"cancel_note": "sửa lại"},
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )

        resp = client.post(
            "/api/v1/scores/batch",
            json={
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": seed_data["students"][0].id, "score_15m_1": 5.0}],
            },
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200

class TestDirtyCheck:

    def test_no_change_row_does_not_create_score(self, app, seed_data):

        st = seed_data["students"][0]
        result = score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": None}],
            },
            seed_data["teacher"].id,
        )
        assert result["data"]["updated_count"] == 0
        assert (
            Score.query.filter_by(
                assignment_id=seed_data["assignment"].id, student_id=st.id
            ).count()
            == 0
        )

    def test_partial_update_still_preserves_other_cells(self, app, seed_data):

        st = seed_data["students"][0]
        score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": 8.0, "score_15m_2": 9.0}],
            },
            seed_data["teacher"].id,
        )
        score_service.save_batch_scores(
            {
                "assignment_id": seed_data["assignment"].id,
                "scores": [{"student_id": st.id, "score_15m_1": 7.0, "score_15m_2": None}],
            },
            seed_data["teacher"].id,
        )
        row = Score.query.filter_by(student_id=st.id).first()
        assert float(row.score_15m_1) == 7.0
        assert float(row.score_15m_2) == 9.0
