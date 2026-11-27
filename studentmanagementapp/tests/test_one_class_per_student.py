import pytest

from studentapp.exceptions import BusinessRuleError, ValidationError
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.services.class_service import ClassService

def _active_class_ids(student_id):

    return [
        e.class_id
        for e in ClassEnrollment.query.filter_by(
            student_id=student_id, status=EnrollmentStatusEnum.DANG_HOC
        ).all()
    ]

class TestEnrollStudentOneClassRule:

    def test_enroll_new_student_has_exactly_one_active_class(self, app, seed_data):

        from studentapp.models.student import Student, StudentStatusEnum

        st = Student(
            student_code="HS9999999",
            full_name="Học Sinh Mới",
            gender="Nam",
            date_of_birth=__import__("datetime").date(2010, 1, 1),
            status=StudentStatusEnum.DANG_HOC,
        )
        app.extensions["sqlalchemy"].session.add(st)
        app.extensions["sqlalchemy"].session.commit()

        ClassService.enroll_student(
            seed_data["class"].id,
            {
                "student_ids": [st.id],
                "academic_year_id": seed_data["academic_year"].id,
            },
        )

        assert _active_class_ids(st.id) == [seed_data["class"].id]

    def test_enroll_into_same_class_is_rejected(self, app, seed_data):

        st = seed_data["students"][0]

        with pytest.raises(BusinessRuleError) as exc:
            ClassService.enroll_student(
                seed_data["class"].id,
                {
                    "student_ids": [st.id],
                    "academic_year_id": seed_data["academic_year"].id,
                },
            )
        assert "đã có trong lớp" in str(exc.value).lower()

    def test_enroll_into_other_class_moves_student(self, app, seed_data):

        st = seed_data["students"][0]

        ClassService.enroll_student(
            seed_data["other_class"].id,
            {
                "student_ids": [st.id],
                "academic_year_id": seed_data["academic_year"].id,
            },
        )

        active = _active_class_ids(st.id)
        assert active == [seed_data["other_class"].id], (
            f"Học sinh phải chỉ có 1 lớp DANG_HOC, thực tế: {active}"
        )

        old = ClassEnrollment.query.filter_by(
            student_id=st.id, class_id=seed_data["class"].id
        ).first()
        assert old.status == EnrollmentStatusEnum.DA_CHUYEN

    def test_enroll_into_other_academic_year_does_not_duplicate(self, app, seed_data):

        from datetime import date

        from studentapp.models.academic_year import AcademicYear
        from studentapp.models.class_room import Class

        st = seed_data["students"][0]

        old_year = AcademicYear(
            year_name="2024-2025", start_year=2024, end_year=2025, is_current=False
        )
        app.extensions["sqlalchemy"].session.add(old_year)
        app.extensions["sqlalchemy"].session.flush()
        old_class = Class(
            class_name="10C1",
            grade_id=seed_data["grade"].id,
            academic_year_id=old_year.id,
        )
        app.extensions["sqlalchemy"].session.add(old_class)
        app.extensions["sqlalchemy"].session.commit()

        ClassService.enroll_student(
            old_class.id,
            {"student_ids": [st.id], "academic_year_id": old_year.id},
        )

        active = _active_class_ids(st.id)
        assert len(active) == 1, (
            f"Học sinh phải chỉ có 1 lớp DANG_HOC, thực tế: {active}"
        )

    def test_enroll_with_invalid_academic_year_is_rejected(self, app, seed_data):

        st = seed_data["students"][0]

        with pytest.raises(ValidationError):
            ClassService.enroll_student(
                seed_data["other_class"].id,
                {"student_ids": [st.id], "academic_year_id": 999999},
            )

    def test_enroll_into_class_of_other_year_is_rejected(self, app, seed_data):

        from studentapp.models.academic_year import AcademicYear
        from studentapp.models.class_room import Class

        st = seed_data["students"][0]
        old_year = AcademicYear(
            year_name="2024-2025", start_year=2024, end_year=2025, is_current=False
        )
        app.extensions["sqlalchemy"].session.add(old_year)
        app.extensions["sqlalchemy"].session.flush()
        old_class = Class(
            class_name="10C1",
            grade_id=seed_data["grade"].id,
            academic_year_id=old_year.id,
        )
        app.extensions["sqlalchemy"].session.add(old_class)
        app.extensions["sqlalchemy"].session.commit()

        with pytest.raises(BusinessRuleError):
            ClassService.enroll_student(
                old_class.id,
                {
                    "student_ids": [st.id],
                    "academic_year_id": seed_data["academic_year"].id,
                },
            )

class TestTransferStudentOneClassRule:

    def test_transfer_moves_student(self, app, seed_data):
        st = seed_data["students"][0]

        ClassService.transfer_student(
            {
                "student_id": st.id,
                "from_class_id": seed_data["class"].id,
                "to_class_id": seed_data["other_class"].id,
                "academic_year_id": seed_data["academic_year"].id,
                "transfer_reason": "Chuyển lớp hợp lệ",
            }
        )

        active = _active_class_ids(st.id)
        assert active == [seed_data["other_class"].id]

    def test_transfer_to_other_academic_year_does_not_duplicate(self, app, seed_data):

        from studentapp.models.academic_year import AcademicYear
        from studentapp.models.class_room import Class

        st = seed_data["students"][0]
        old_year = AcademicYear(
            year_name="2024-2025", start_year=2024, end_year=2025, is_current=False
        )
        app.extensions["sqlalchemy"].session.add(old_year)
        app.extensions["sqlalchemy"].session.flush()
        old_class = Class(
            class_name="10C1",
            grade_id=seed_data["grade"].id,
            academic_year_id=old_year.id,
        )
        app.extensions["sqlalchemy"].session.add(old_class)
        app.extensions["sqlalchemy"].session.commit()

        ClassService.transfer_student(
            {
                "student_id": st.id,
                "from_class_id": seed_data["class"].id,
                "to_class_id": old_class.id,
                "academic_year_id": old_year.id,
                "transfer_reason": "Chuyển sang niên khóa cũ",
            }
        )

        active = _active_class_ids(st.id)
        assert len(active) == 1, (
            f"Học sinh phải chỉ có 1 lớp DANG_HOC, thực tế: {active}"
        )

class TestReactivationKeepsOneClass:

    def test_reactivate_activates_only_one_class(self, app, seed_data):

        from studentapp.services import student_service

        st = seed_data["students"][0]

        app.extensions["sqlalchemy"].session.add(
            ClassEnrollment(
                student_id=st.id,
                class_id=seed_data["other_class"].id,
                academic_year_id=seed_data["academic_year"].id,
                enrollment_date=__import__("datetime").date(2026, 9, 1),
                status=EnrollmentStatusEnum.DA_CHUYEN,
            )
        )
        app.extensions["sqlalchemy"].session.commit()

        student_service._sync_enrollment_with_status(
            st, old_status="THOI_HOC", new_status="DANG_HOC"
        )

        active = _active_class_ids(st.id)
        assert len(active) == 1, (
            f"Học sinh phải chỉ có 1 lớp DANG_HOC, thực tế: {active}"
        )
