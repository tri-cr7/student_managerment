from datetime import date

import pytest

from studentapp.extensions import db
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.score import Score
from studentapp.models.score_change_detail import ScoreChangeDetail
from studentapp.models.score_change_request import ScoreChangeRequest
from studentapp.models.score_submission import ScoreSubmission
from studentapp.models.student import Student, StudentStatusEnum

@pytest.fixture
def outsider_student(app, seed_data):

    outsider = Student(
        student_code="HS20267777",
        full_name="Học Sinh Lớp Khác",
        gender="Nam",
        date_of_birth=date(2010, 6, 1),
        status=StudentStatusEnum.DANG_HOC,
    )
    db.session.add(outsider)
    db.session.flush()
    db.session.add(
        ClassEnrollment(
            student_id=outsider.id,
            class_id=seed_data["other_class"].id,
            academic_year_id=seed_data["academic_year"].id,
            enrollment_date=date(2026, 9, 1),
            status=EnrollmentStatusEnum.DANG_HOC,
        )
    )
    db.session.commit()
    return outsider

@pytest.fixture
def own_submission(app, seed_data):

    sub = ScoreSubmission(
        assignment_id=seed_data["assignment"].id,
        teacher_id=seed_data["teacher"].id,
        status="PENDING",
        total_students=3,
        total_scores=27,
    )
    db.session.add(sub)
    db.session.commit()
    return sub

@pytest.fixture
def other_submission(app, seed_data):

    sub = ScoreSubmission(
        assignment_id=seed_data["other_assignment"].id,
        teacher_id=seed_data["other_teacher"].id,
        status="PENDING",
        total_students=0,
        total_scores=0,
    )
    db.session.add(sub)
    db.session.commit()
    return sub

@pytest.fixture
def own_request(app, seed_data):

    score = Score(
        assignment_id=seed_data["assignment"].id,
        student_id=seed_data["students"][0].id,
        score_final=7.0,
        average_score=7.0,
        is_draft=False,
    )
    db.session.add(score)
    db.session.flush()

    req = ScoreChangeRequest(
        assignment_id=seed_data["assignment"].id,
        teacher_id=seed_data["teacher"].id,
        reason="Gõ nhầm điểm",
        status="PENDING",
        is_batch=False,
        total_changes=1,
    )
    db.session.add(req)
    db.session.flush()
    db.session.add(
        ScoreChangeDetail(
            request_id=req.id,
            student_id=seed_data["students"][0].id,
            score_id=score.id,
            score_column="score_final",
            old_value=7.0,
            new_value=8.0,
            status="PENDING",
        )
    )
    db.session.commit()
    return req

@pytest.fixture
def other_request(app, seed_data):

    req = ScoreChangeRequest(
        assignment_id=seed_data["other_assignment"].id,
        teacher_id=seed_data["other_teacher"].id,
        reason="Đơn của GV khác",
        status="PENDING",
        is_batch=False,
        total_changes=1,
    )
    db.session.add(req)
    db.session.commit()
    return req

class TestTeacherStudentScope:

    def test_teacher_can_view_own_class_student(self, app, client, seed_data,
                                                auth_headers):
        resp = client.get(
            f"/api/v1/students/{seed_data['students'][0].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["student_code"].startswith("HS")

    def test_teacher_denied_for_outsider_student(self, app, client, seed_data,
                                                 outsider_student, auth_headers):
        resp = client.get(
            f"/api/v1/students/{outsider_student.id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "FORBIDDEN"

    def test_teacher_denied_by_code_for_outsider(self, app, client, seed_data,
                                                 outsider_student, auth_headers):
        resp = client.get(
            f"/api/v1/students/code/{outsider_student.student_code}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_staff_can_view_any_student(self, app, client, seed_data,
                                        outsider_student, auth_headers):
        resp = client.get(
            f"/api/v1/students/{outsider_student.id}",
            headers=auth_headers("STAFF", seed_data["staff"].id),
        )
        assert resp.status_code == 200

    def test_academic_can_view_any_student(self, app, client, seed_data,
                                           outsider_student, auth_headers):
        resp = client.get(
            f"/api/v1/students/{outsider_student.id}",
            headers=auth_headers("ACADEMIC", seed_data["academic"].id),
        )
        assert resp.status_code == 200

class TestAcademicAssignmentScores:

    def test_academic_can_view_any_assignment(self, app, client, seed_data,
                                               auth_headers):
        resp = client.get(
            f"/api/v1/scores/assignment/{seed_data['other_assignment'].id}",
            headers=auth_headers("ACADEMIC", seed_data["academic"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["class_name"] == "10B1"

    def test_teacher_still_denied_for_other_assignment(self, app, client,
                                                        seed_data, auth_headers):
        resp = client.get(
            f"/api/v1/scores/assignment/{seed_data['other_assignment'].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

class TestTeacherOwnRequestAccess:

    def test_teacher_can_view_own_submission(self, app, client, seed_data,
                                             own_submission, auth_headers):
        resp = client.get(
            f"/api/v1/score-submissions/{own_submission.id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["submission_id"] == own_submission.id

    def test_teacher_denied_other_submission(self, app, client, seed_data,
                                             other_submission, auth_headers):
        resp = client.get(
            f"/api/v1/score-submissions/{other_submission.id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_academic_can_view_any_submission(self, app, client, seed_data,
                                               other_submission, auth_headers):
        resp = client.get(
            f"/api/v1/score-submissions/{other_submission.id}",
            headers=auth_headers("ACADEMIC", seed_data["academic"].id),
        )
        assert resp.status_code == 200

    def test_teacher_can_view_own_change_request(self, app, client, seed_data,
                                                  own_request, auth_headers):
        resp = client.get(
            f"/api/v1/score-requests/{own_request.id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["request_id"] == own_request.id

    def test_teacher_denied_other_change_request(self, app, client, seed_data,
                                                  other_request, auth_headers):
        resp = client.get(
            f"/api/v1/score-requests/{other_request.id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_teacher_denied_other_change_request_diff(self, app, client,
                                                       seed_data,
                                                       other_request, auth_headers):
        resp = client.get(
            f"/api/v1/score-requests/{other_request.id}/diff",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

    def test_teacher_can_view_own_change_request_diff(self, app, client,
                                                       seed_data, own_request,
                                                       auth_headers):
        resp = client.get(
            f"/api/v1/score-requests/{own_request.id}/diff",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert "changes" in resp.get_json()["data"]

    def test_academic_can_view_any_change_request(self, app, client, seed_data,
                                                  other_request, auth_headers):
        resp = client.get(
            f"/api/v1/score-requests/{other_request.id}",
            headers=auth_headers("ACADEMIC", seed_data["academic"].id),
        )
        assert resp.status_code == 200

    def test_staff_forbidden(self, app, client, seed_data, own_request,
                             auth_headers):

        resp = client.get(
            f"/api/v1/score-requests/{own_request.id}",
            headers=auth_headers("STAFF", seed_data["staff"].id),
        )
        assert resp.status_code == 403
