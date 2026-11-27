from datetime import date

import pytest

from studentapp.services import score_service

@pytest.fixture
def yearly_data(app, seed_data):

    from studentapp.extensions import db
    from studentapp.models.semester import Semester
    from studentapp.models.score import Score
    from studentapp.models.teaching_assignment import TeachingAssignment

    year = seed_data["academic_year"]
    hk2 = seed_data["semester_hk2"]

    assignment_hk2 = TeachingAssignment(
        teacher_id=seed_data["teacher"].id,
        class_id=seed_data["class"].id,
        subject_id=seed_data["subject"].id,
        semester_id=hk2.id,
        is_locked=True,
    )
    db.session.add(assignment_hk2)
    db.session.flush()

    hk1_avgs = [8.00, 6.00, 5.00]
    hk2_avgs = [9.00, 7.00, 4.00]
    for idx, student in enumerate(seed_data["students"]):
        s1 = Score(
            assignment_id=seed_data["assignment"].id,
            student_id=student.id,
            average_score=hk1_avgs[idx],
            is_passed=True,
            is_draft=False,
        )
        s2 = Score(
            assignment_id=assignment_hk2.id,
            student_id=student.id,
            average_score=hk2_avgs[idx],
            is_passed=True,
            is_draft=False,
        )
        db.session.add_all([s1, s2])

    draft = Score(
        assignment_id=seed_data["assignment"].id,
        student_id=seed_data["students"][0].id,
        average_score=1.23,
        is_passed=False,
        is_draft=True,
    )
    db.session.add(draft)
    db.session.commit()

    return {
        "hk2": hk2,
        "assignment_hk2": assignment_hk2,
        "hk1_avgs": hk1_avgs,
        "hk2_avgs": hk2_avgs,
    }

class TestYearlyClassScoresService:

    def test_returns_hk1_hk2_and_yearly_average(self, app, seed_data, yearly_data):

        data = score_service.get_yearly_class_scores(
            seed_data["class"].id,
            seed_data["subject"].id,
            seed_data["academic_year"].id,
            teacher_id=seed_data["teacher"].id,
        )
        assert data["class_name"] == "10A1"
        assert data["subject_name"] == "Toán học 10"
        assert data["academic_year"] == "2026-2027"
        assert len(data["records"]) == 3

        first = data["records"][0]
        assert first["stt"] == 1
        assert first["full_name"] == "Nguyễn Văn 1"
        assert first["class_name"] == "10A1"
        assert first["avg_hk1"] == pytest.approx(8.00)
        assert first["avg_hk2"] == pytest.approx(9.00)
        assert first["avg_yearly"] == pytest.approx(8.67)

    def test_yearly_average_uses_semester_factor(self, app, seed_data, yearly_data):

        data = score_service.get_yearly_class_scores(
            seed_data["class"].id,
            seed_data["subject"].id,
            seed_data["academic_year"].id,
            teacher_id=seed_data["teacher"].id,
        )
        for rec in data["records"]:
            expected = (rec["avg_hk1"] * 1 + rec["avg_hk2"] * 2) / 3
            assert rec["avg_yearly"] == pytest.approx(round(expected, 2))

    def test_ignores_draft_scores(self, app, seed_data, yearly_data):

        data = score_service.get_yearly_class_scores(
            seed_data["class"].id,
            seed_data["subject"].id,
            seed_data["academic_year"].id,
            teacher_id=seed_data["teacher"].id,
        )
        first = data["records"][0]
        assert first["avg_hk1"] == pytest.approx(8.00)
        assert first["avg_hk1"] != pytest.approx(1.23)

    def test_teacher_denied_for_other_class(self, app, seed_data, yearly_data):

        from studentapp.exceptions import PermissionDeniedError

        with pytest.raises(PermissionDeniedError):
            score_service.get_yearly_class_scores(
                seed_data["other_class"].id,
                seed_data["subject"].id,
                seed_data["academic_year"].id,
                teacher_id=seed_data["teacher"].id,
            )

    def test_academic_sees_all_classes(self, app, seed_data, yearly_data):

        data = score_service.get_yearly_class_scores(
            seed_data["other_class"].id,
            seed_data["subject"].id,
            seed_data["academic_year"].id,
            teacher_id=seed_data["academic"].id,
            is_academic=True,
        )
        assert data["class_name"] == "10B1"

    def test_missing_academic_year_returns_error(self, app, seed_data):

        from studentapp.exceptions import ValidationError

        with pytest.raises(ValidationError):
            score_service.get_yearly_class_scores(
                seed_data["class"].id,
                seed_data["subject"].id,
                None,
                teacher_id=seed_data["teacher"].id,
            )

class TestExportYearlyClassScores:

    def test_export_excel_returns_bytes(self, app, seed_data, yearly_data):
        payload, filename, mime, data = (
            score_service.export_yearly_class_scores(
                seed_data["assignment"].id,
                fmt="excel",
                teacher_id=seed_data["teacher"].id,
            )
        )
        assert payload[:2] == b"PK"
        assert filename.endswith(".xlsx")
        assert "10A1" in filename
        assert "openxmlformats" in mime
        assert len(data["records"]) == 3

    def test_export_pdf_returns_bytes(self, app, seed_data, yearly_data):
        payload, filename, mime, _data = (
            score_service.export_yearly_class_scores(
                seed_data["assignment"].id,
                fmt="pdf",
                teacher_id=seed_data["teacher"].id,
            )
        )
        assert payload[:4] == b"%PDF"
        assert filename.endswith(".pdf")
        assert mime == "application/pdf"

    def test_excel_has_no_yearly_average_column(self, app, seed_data, yearly_data):

        import io

        from openpyxl import load_workbook

        payload, _fn, _mime, _data = (
            score_service.export_yearly_class_scores(
                seed_data["assignment"].id,
                fmt="excel",
                teacher_id=seed_data["teacher"].id,
            )
        )
        wb = load_workbook(io.BytesIO(payload))
        ws = wb.active
        headers = [c.value for c in ws[3]]
        assert headers == [
            "Năm học", "STT", "Họ tên", "Lớp", "Điểm TB HK1", "Điểm TB HK2",
        ]

        assert not any("cả năm" in str(h) for h in headers)

    def test_export_denied_for_other_teacher(self, app, seed_data, yearly_data):

        from studentapp.exceptions import PermissionDeniedError

        with pytest.raises(PermissionDeniedError):
            score_service.export_yearly_class_scores(
                seed_data["other_assignment"].id,
                fmt="excel",
                teacher_id=seed_data["teacher"].id,
            )

    def test_invalid_format_rejected(self, app, seed_data, yearly_data):
        from studentapp.exceptions import ValidationError

        with pytest.raises(ValidationError):
            score_service.export_yearly_class_scores(
                seed_data["assignment"].id,
                fmt="docx",
                teacher_id=seed_data["teacher"].id,
            )

class TestYearlyScoresEndpoint:

    def test_requires_authentication(self, app, client, seed_data):
        resp = client.get(
            f"/api/v1/scores/class/{seed_data['class'].id}"
            f"/subject/{seed_data['subject'].id}/yearly"
            f"?academic_year_id={seed_data['academic_year'].id}"
        )
        assert resp.status_code == 401

    def test_forbidden_for_staff(self, app, client, seed_data, auth_headers):
        resp = client.get(
            f"/api/v1/scores/class/{seed_data['class'].id}"
            f"/subject/{seed_data['subject'].id}/yearly"
            f"?academic_year_id={seed_data['academic_year'].id}",
            headers=auth_headers("STAFF", seed_data["staff"].id),
        )
        assert resp.status_code == 403

    def test_teacher_gets_yearly_table(self, app, client, seed_data, yearly_data,
                                       auth_headers):
        resp = client.get(
            f"/api/v1/scores/class/{seed_data['class'].id}"
            f"/subject/{seed_data['subject'].id}/yearly"
            f"?academic_year_id={seed_data['academic_year'].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["academic_year"] == "2026-2027"
        assert len(body["data"]["records"]) == 3

    def test_other_teacher_gets_403(self, app, client, seed_data, yearly_data,
                                    auth_headers):
        resp = client.get(
            f"/api/v1/scores/class/{seed_data['other_class'].id}"
            f"/subject/{seed_data['subject'].id}/yearly"
            f"?academic_year_id={seed_data['academic_year'].id}",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 403

class TestExportScoresEndpoint:

    def test_requires_authentication(self, app, client, seed_data):
        resp = client.get("/api/v1/scores/export")
        assert resp.status_code == 401

    def test_returns_excel_file(self, app, client, seed_data, yearly_data,
                                auth_headers):
        resp = client.get(
            f"/api/v1/scores/export?assignment_id={seed_data['assignment'].id}"
            "&format=excel",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.data[:2] == b"PK"
        assert "spreadsheetml" in resp.headers["Content-Type"]
        assert "attachment" in resp.headers["Content-Disposition"]

    def test_returns_pdf_file(self, app, client, seed_data, yearly_data,
                              auth_headers):
        resp = client.get(
            f"/api/v1/scores/export?assignment_id={seed_data['assignment'].id}"
            "&format=pdf",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 200
        assert resp.data[:4] == b"%PDF"
        assert resp.headers["Content-Type"] == "application/pdf"

    def test_missing_assignment_returns_404(self, app, client, seed_data,
                                             auth_headers):
        resp = client.get(
            "/api/v1/scores/export?assignment_id=999999&format=excel",
            headers=auth_headers("TEACHER", seed_data["teacher"].id),
        )
        assert resp.status_code == 404
