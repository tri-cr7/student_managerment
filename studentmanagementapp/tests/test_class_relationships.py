import pytest

from studentapp.exceptions import (
    BusinessRuleError,
    ClassSizeExceededError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
from studentapp.models.class_room import Class
from studentapp.models.grade import Grade
from studentapp.services.class_service import ClassService, count_active_students

def _make_student(app, code, name="Học Sinh"):
    from datetime import date

    from studentapp.models.student import Student, StudentStatusEnum

    st = Student(
        student_code=code,
        full_name=name,
        date_of_birth=date(2010, 1, 1),
        status=StudentStatusEnum.DANG_HOC,
    )
    app.extensions["sqlalchemy"].session.add(st)
    app.extensions["sqlalchemy"].session.commit()
    return st

class TestCreateClassValidation:

    def test_create_class_with_invalid_grade_id_is_rejected(self, app, seed_data):

        with pytest.raises(NotFoundError):
            ClassService.create_class(
                {
                    "class_name": "10X9",
                    "grade_id": 999999,
                    "academic_year_id": seed_data["academic_year"].id,
                }
            )

    def test_create_class_with_invalid_academic_year_is_rejected(
        self, app, seed_data
    ):

        with pytest.raises(NotFoundError):
            ClassService.create_class(
                {
                    "class_name": "10X9",
                    "grade_id": seed_data["grade"].id,
                    "academic_year_id": 999999,
                }
            )

    def test_create_class_with_non_teacher_homeroom_is_rejected(
        self, app, seed_data
    ):

        with pytest.raises(ValidationError):
            ClassService.create_class(
                {
                    "class_name": "10X9",
                    "grade_id": seed_data["grade"].id,
                    "academic_year_id": seed_data["academic_year"].id,
                    "homeroom_teacher_id": seed_data["academic"].id,
                }
            )

    def test_create_class_with_valid_teacher_is_ok(self, app, seed_data):

        new_class = ClassService.create_class(
            {
                "class_name": "10X9",
                "grade_id": seed_data["grade"].id,
                "academic_year_id": seed_data["academic_year"].id,
                "homeroom_teacher_id": seed_data["teacher"].id,
            }
        )
        assert new_class.id is not None
        assert new_class.homeroom_teacher_id == seed_data["teacher"].id

    def test_duplicate_class_name_in_same_year_is_rejected(self, app, seed_data):

        with pytest.raises(DuplicateError) as exc:
            ClassService.create_class(
                {
                    "class_name": "10A1",
                    "grade_id": seed_data["grade"].id,
                    "academic_year_id": seed_data["academic_year"].id,
                }
            )
        assert exc.value.error == "DUPLICATE_CLASS_NAME"

    def test_same_class_name_in_different_year_is_allowed(self, app, seed_data):

        from studentapp.models.academic_year import AcademicYear

        other_year = AcademicYear(
            year_name="2025-2026", start_year=2025, end_year=2026, is_current=False
        )
        app.extensions["sqlalchemy"].session.add(other_year)
        app.extensions["sqlalchemy"].session.commit()

        new_class = ClassService.create_class(
            {
                "class_name": "10A1",
                "grade_id": seed_data["grade"].id,
                "academic_year_id": other_year.id,
            }
        )
        assert new_class.id is not None

class TestClassSizeLimit:

    def test_capacity_uses_real_count_not_stale_cache(self, app, seed_data):

        db = app.extensions["sqlalchemy"].session
        cls = seed_data["class"]

        extra = []
        for i in range(37):
            extra.append(_make_student(app, f"HSX{i:04d}"))
        db.commit()

        ClassService.enroll_student(
            cls.id,
            {
                "student_ids": [s.id for s in extra],
                "academic_year_id": seed_data["academic_year"].id,
            },
        )
        assert count_active_students(cls.id) == 40

        extra[0].is_deleted = True
        db.commit()

        new_student = _make_student(app, "HSX9999")
        db.commit()

        ClassService.enroll_student(
            cls.id,
            {
                "student_ids": [new_student.id],
                "academic_year_id": seed_data["academic_year"].id,
            },
        )
        assert count_active_students(cls.id) == 40

    def test_exceeding_max_class_size_is_rejected(self, app, seed_data):

        db = app.extensions["sqlalchemy"].session
        cls = seed_data["class"]

        students = [_make_student(app, f"HSY{i:04d}") for i in range(40)]
        db.commit()

        with pytest.raises(ClassSizeExceededError):
            ClassService.enroll_student(
                cls.id,
                {
                    "student_ids": [s.id for s in students],
                    "academic_year_id": seed_data["academic_year"].id,
                },
            )

    def test_current_size_is_resynced_after_enroll(self, app, seed_data):

        db = app.extensions["sqlalchemy"].session
        cls = seed_data["class"]
        new_student = _make_student(app, "HSZ0001")
        db.commit()

        ClassService.enroll_student(
            cls.id,
            {
                "student_ids": [new_student.id],
                "academic_year_id": seed_data["academic_year"].id,
            },
        )
        assert cls.current_size == count_active_students(cls.id)

class TestCrossGradeTransfer:

    def test_transfer_to_other_grade_is_rejected(self, app, seed_data):

        db = app.extensions["sqlalchemy"].session
        grade12 = Grade(grade_level=12, grade_name="Khối 12")
        db.add(grade12)
        db.commit()

        class12 = Class(
            class_name="12A1",
            grade_id=grade12.id,
            academic_year_id=seed_data["academic_year"].id,
        )
        db.add(class12)
        db.commit()

        st = seed_data["students"][0]
        with pytest.raises(BusinessRuleError) as exc:
            ClassService.transfer_student(
                {
                    "student_id": st.id,
                    "to_class_id": class12.id,
                    "academic_year_id": seed_data["academic_year"].id,
                    "transfer_reason": "Chuyển khối",
                }
            )
        assert exc.value.error == "CROSS_GRADE_TRANSFER_NOT_ALLOWED"

        active = ClassEnrollment.query.filter_by(
            student_id=st.id, status=EnrollmentStatusEnum.DANG_HOC
        ).all()
        assert [e.class_id for e in active] == [seed_data["class"].id]

    def test_transfer_within_same_grade_is_allowed(self, app, seed_data):

        st = seed_data["students"][0]
        ClassService.transfer_student(
            {
                "student_id": st.id,
                "to_class_id": seed_data["other_class"].id,
                "academic_year_id": seed_data["academic_year"].id,
                "transfer_reason": "Chuyển lớp hợp lệ",
            }
        )
        active = ClassEnrollment.query.filter_by(
            student_id=st.id, status=EnrollmentStatusEnum.DANG_HOC
        ).all()
        assert [e.class_id for e in active] == [seed_data["other_class"].id]

    def test_transfer_stores_reason_in_transfer_note(self, app, seed_data):

        st = seed_data["students"][0]
        ClassService.transfer_student(
            {
                "student_id": st.id,
                "to_class_id": seed_data["other_class"].id,
                "academic_year_id": seed_data["academic_year"].id,
                "transfer_reason": "Chuyển vì nhập học",
            }
        )
        old = ClassEnrollment.query.filter_by(
            student_id=st.id,
            class_id=seed_data["class"].id,
            status=EnrollmentStatusEnum.DA_CHUYEN,
        ).first()
        assert old is not None
        assert old.transfer_note == "Chuyển vì nhập học"

class TestDeleteClass:

    def test_delete_class_with_teaching_assignments_is_rejected(
        self, app, seed_data
    ):

        with pytest.raises(BusinessRuleError) as exc:
            ClassService.delete_class(seed_data["class"].id)
        assert exc.value.error == "CLASS_HAS_ASSIGNMENTS"

    def test_delete_empty_class_is_allowed(self, app, seed_data):

        db = app.extensions["sqlalchemy"].session
        empty = Class(
            class_name="10Z9",
            grade_id=seed_data["grade"].id,
            academic_year_id=seed_data["academic_year"].id,
        )
        db.add(empty)
        db.commit()
        empty_id = empty.id

        ClassService.delete_class(empty_id)
        assert Class.query.get(empty_id) is None

class TestReactivationAcademicYear:

    def test_reactivation_does_not_restore_old_academic_year_class(
        self, app, seed_data
    ):
        from datetime import date

        from studentapp.models.academic_year import AcademicYear
        from studentapp.services import student_service

        db = app.extensions["sqlalchemy"].session
        st = seed_data["students"][0]

        old_year = AcademicYear(
            year_name="2024-2025", start_year=2024, end_year=2025, is_current=False
        )
        db.add(old_year)
        db.flush()
        old_class = Class(
            class_name="11B9",
            grade_id=seed_data["grade"].id,
            academic_year_id=old_year.id,
        )
        db.add(old_class)
        db.flush()
        db.add(
            ClassEnrollment(
                student_id=st.id,
                class_id=old_class.id,
                academic_year_id=old_year.id,
                enrollment_date=date(2024, 9, 1),
                status=EnrollmentStatusEnum.DA_CHUYEN,
            )
        )
        db.commit()

        student_service._sync_enrollment_with_status(
            st, old_status="THOI_HOC", new_status="DANG_HOC"
        )

        active = ClassEnrollment.query.filter_by(
            student_id=st.id, status=EnrollmentStatusEnum.DANG_HOC
        ).all()

        assert all(
            int(e.academic_year_id) != int(old_year.id) for e in active
        ), "Không được khôi phục lớp của niên khóa đã qua."

class TestDatabaseConstraints:

    def test_classes_table_has_required_constraints(self, app):

        from sqlalchemy import inspect

        inspector = inspect(app.extensions["sqlalchemy"].engine)
        index_names = {i["name"] for i in inspector.get_indexes("classes")}
        unique_names = {u["name"] for u in inspector.get_unique_constraints("classes")}

        assert "idx_classes_grade_year" in index_names
        assert "uq_class_name_year" in unique_names

    def test_grades_table_rejects_invalid_grade_level(self, app):

        from sqlalchemy.exc import IntegrityError

        db = app.extensions["sqlalchemy"].session
        db.add(Grade(grade_level=13, grade_name="Khối 13"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_duplicate_class_name_same_year_rejected_by_db(self, app, seed_data):

        from sqlalchemy.exc import IntegrityError

        db = app.extensions["sqlalchemy"].session
        db.add(
            Class(
                class_name="10A1",
                grade_id=seed_data["grade"].id,
                academic_year_id=seed_data["academic_year"].id,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
