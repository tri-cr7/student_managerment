"""Test fixtures — app, db, client, dữ liệu mẫu cho module Giáo viên.

Nguyên tắc:
* Mỗi test chạy trên DB sạch (SQLite in-memory, ``create_all`` mỗi lần) → độc lập.
* Fixture seed tạo sẵn: Giáo viên, Giáo vụ, lớp + môn + assignment + học sinh.
"""
import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import config_by_name  # noqa: E402
from studentapp import create_app  # noqa: E402
from studentapp.extensions import db  # noqa: E402
from studentapp.models.system_rule import SystemRule, DEFAULT_RULES  # noqa: E402


@pytest.fixture
def app():
    """App Flask cấu hình testing (SQLite in-memory, CSRF tắt)."""
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        _seed_rules()
        yield application
        db.session.remove()
        db.drop_all()


def _seed_rules():
    for key, value, dtype, desc in DEFAULT_RULES:
        if not SystemRule.query.filter_by(rule_key=key).first():
            db.session.add(
                SystemRule(rule_key=key, rule_value=value, data_type=dtype, description=desc)
            )
    db.session.commit()


@pytest.fixture
def db_session(app):
    """Session DB gắn với app context hiện tại."""
    return db.session


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    """Cấp JWT token cho role theo yêu cầu.

    Dùng: ``auth_headers("TEACHER")`` hoặc ``auth_headers("TEACHER", user_id=5)``.
    """
    from flask_jwt_extended import create_access_token

    def _make(role="TEACHER", user_id=1):
        with app.app_context():
            token = create_access_token(
                identity=str(user_id), additional_claims={"role": role}
            )
        return {"Authorization": f"Bearer {token}"}

    return _make


# --------------------------------------------------------------------------- #
# Dữ liệu mẫu cho module Giáo viên
# --------------------------------------------------------------------------- #


@pytest.fixture
def seed_data(app):
    """Tạo dữ liệu mẫu đầy đủ cho module điểm.

    Cấu trúc:
    * ``teacher``      — Giáo viên chính (id = teacher.id)
    * ``other_teacher``— Giáo viên khác (dùng để test quyền sở hữu)
    * ``academic``     — Giáo vụ
    * ``assignment``   — 1 lớp môn học do ``teacher`` phụ trách
    * ``other_assignment`` — 1 lớp môn học do ``other_teacher`` phụ trách
    * ``students``     — 3 học sinh thuộc lớp của ``assignment``
    """
    from datetime import date

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
    from studentapp.models.class_room import Class
    from studentapp.models.grade import Grade
    from studentapp.models.semester import Semester
    from studentapp.models.student import Student, StudentStatusEnum
    from studentapp.models.subject import Subject
    from studentapp.models.teaching_assignment import TeachingAssignment
    from studentapp.models.user import User, UserRoleEnum

    def _make_user(username, role, full_name):
        u = User(
            username=username,
            email=f"{username}@school.local",
            full_name=full_name,
            role=role,
        )
        u.set_password("Test@123")
        db.session.add(u)
        return u

    teacher = _make_user("gv01", UserRoleEnum.TEACHER, "Giáo Viên Một")
    other_teacher = _make_user("gv02", UserRoleEnum.TEACHER, "Giáo Viên Hai")
    academic = _make_user("gv03", UserRoleEnum.ACADEMIC, "Giáo Vụ")
    staff = _make_user("nv01", UserRoleEnum.STAFF, "Nhân Viên Văn Phòng")

    year = AcademicYear(year_name="2026-2027", start_year=2026, end_year=2027, is_current=True)
    grade = Grade(grade_level=10, grade_name="Khối 10")
    db.session.add_all([year, grade])
    db.session.flush()

    sem_hk1 = Semester(
        semester_name="Học kỳ 1", academic_year_id=year.id, factor=1, is_current=True
    )
    db.session.add(sem_hk1)
    db.session.flush()

    subject = Subject(
        subject_code="TOAN10", subject_name="Toán học 10", grade_id=grade.id, periods_count=4
    )
    db.session.add(subject)
    db.session.flush()

    class_a = Class(class_name="10A1", grade_id=grade.id, academic_year_id=year.id)
    class_b = Class(class_name="10B1", grade_id=grade.id, academic_year_id=year.id)
    db.session.add_all([class_a, class_b])
    db.session.flush()

    assignment = TeachingAssignment(
        teacher_id=teacher.id,
        class_id=class_a.id,
        subject_id=subject.id,
        semester_id=sem_hk1.id,
        is_locked=False,
    )
    other_assignment = TeachingAssignment(
        teacher_id=other_teacher.id,
        class_id=class_b.id,
        subject_id=subject.id,
        semester_id=sem_hk1.id,
        is_locked=False,
    )
    db.session.add_all([assignment, other_assignment])
    db.session.flush()

    students = []
    for i in range(1, 4):
        st = Student(
            student_code=f"HS2026{i:04d}",
            full_name=f"Nguyễn Văn {i}",
            gender="Nam",
            date_of_birth=date(2010, 5, i),
            status=StudentStatusEnum.DANG_HOC,
        )
        db.session.add(st)
        db.session.flush()
        db.session.add(
            ClassEnrollment(
                student_id=st.id,
                class_id=class_a.id,
                academic_year_id=year.id,
                enrollment_date=date(2026, 9, 1),
                status=EnrollmentStatusEnum.DANG_HOC,
            )
        )
        students.append(st)

    db.session.commit()

    return {
        "teacher": teacher,
        "other_teacher": other_teacher,
        "academic": academic,
        "staff": staff,
        "academic_year": year,
        "semester": sem_hk1,
        "grade": grade,
        "subject": subject,
        "class": class_a,
        "other_class": class_b,
        "assignment": assignment,
        "other_assignment": other_assignment,
        "students": students,
    }
