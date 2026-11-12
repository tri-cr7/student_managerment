"""Script đồng bộ schema + seed dữ liệu mẫu cho module ĐIỂM (Giáo viên).

Mục đích:
1. Tạo các bảng/cột còn thiếu theo thiết kế mới trong code
   (``scores.is_draft``, ``scores.submitted_at``, ``teaching_assignments.locked_at``,
   ``score_submissions``, ``score_change_requests``, ``score_change_details``, ``email_outbox``).
2. Seed dữ liệu mẫu để test bằng Postman: GV, lớp, môn, phân công giảng dạy, học sinh.

Cách chạy (từ thư mục ``studentmanagementapp``)::

    ./venv/bin/python seed_teacher_demo.py

Tuỳ chọn::

    ./venv/bin/python seed_teacher_demo.py --reset   # xoá sạch dữ liệu điểm trước khi seed
"""
import argparse
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from studentapp import create_app  # noqa: E402
from studentapp.extensions import db  # noqa: E402


def _ensure_column(table, column, ddl, after=None):
    """Thêm cột nếu chưa có (dùng information_schema để kiểm tra trước)."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        return False
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column in existing:
        return False
    stmt = f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl}"
    if after:
        stmt += f" AFTER `{after}`"
    db.session.execute(text(stmt))
    db.session.commit()
    print(f"  + {table}.{column}")
    return True


def _migrate_score_change_requests():
    """Migrate bảng legacy score_change_requests (kiểu đơn-ô-điểm, 1 hàng = 1 ô)

    sang kiểu đơn cha + chi tiết (SD25/SD19): cha giữ assignment/teacher/reason,
    từng ô điểm nằm ở score_change_details. Chạy an toàn nhiều lần.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "score_change_requests" not in inspector.get_table_names():
        return False
    cols = {c["name"] for c in inspector.get_columns("score_change_requests")}
    if "is_batch" in cols and "score_id" not in cols:
        return False  # đã là schema mới

    print("  ~ migrate score_change_requests (legacy 1-ô → cha + chi tiết)...")
    # Xoá các đơn DRAFT dở dang của schema cũ (không có chi tiết đi kèm).
    db.session.execute(
        text("DELETE FROM score_change_requests WHERE status='DRAFT'")
    )
    # Gỡ FK trỏ tới các cột legacy trước khi DROP cột.
    for fk in inspector.get_foreign_keys("score_change_requests"):
        constrained = fk.get("constrained_columns") or []
        if any(c in ("score_id", "reviewed_by", "assignment_id", "teacher_id")
               for c in constrained):
            db.session.execute(
                text(f"ALTER TABLE `score_change_requests` DROP FOREIGN KEY `{fk['name']}`")
            )
    db.session.commit()
    inspector = inspect(db.engine)
    cols = {c["name"] for c in inspector.get_columns("score_change_requests")}
    for col in ("score_id", "score_column", "old_value", "new_value",
                "reviewed_by", "review_note", "reviewed_at"):
        if col in cols:
            db.session.execute(
                text(f"ALTER TABLE `score_change_requests` DROP COLUMN `{col}`")
            )
    db.session.commit()
    return True


def _ensure_table(table, ddl):
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if table in inspector.get_table_names():
        return False
    db.session.execute(text(ddl))
    db.session.commit()
    print(f"  + bảng {table}")
    return True


def sync_schema():
    """Đồng bộ schema DB với model mới."""
    print("[1/4] Đồng bộ schema...")

    _ensure_column(
        "scores", "is_draft", "TINYINT(1) NOT NULL DEFAULT 1", after="is_passed"
    )
    _ensure_column(
        "scores", "submitted_at", "TIMESTAMP NULL DEFAULT NULL", after="is_draft"
    )
    _ensure_column(
        "teaching_assignments", "locked_at", "TIMESTAMP NULL DEFAULT NULL", after="is_locked"
    )

    # Migrate bảng legacy (1 hàng = 1 ô điểm) sang kiểu cha + chi tiết.
    # Phải chạy TRƯỚC _ensure_table vì bảng cũ đã tồn tại.
    _migrate_score_change_requests()

    _ensure_table(
        "score_submissions",
        """
        CREATE TABLE IF NOT EXISTS score_submissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            assignment_id INT NOT NULL,
            teacher_id INT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            total_students INT NOT NULL DEFAULT 0,
            total_scores INT NOT NULL DEFAULT 0,
            note VARCHAR(255) NULL,
            submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_by INT NULL,
            review_note VARCHAR(255) NULL,
            reviewed_at TIMESTAMP NULL DEFAULT NULL,
            cancelled_at TIMESTAMP NULL DEFAULT NULL,
            cancel_note VARCHAR(255) NULL,
            INDEX ix_sub_assignment (assignment_id),
            INDEX ix_sub_teacher (teacher_id),
            INDEX ix_sub_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _ensure_table(
        "score_change_requests",
        """
        CREATE TABLE IF NOT EXISTS score_change_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            assignment_id INT NOT NULL,
            teacher_id INT NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            is_batch TINYINT(1) NOT NULL DEFAULT 0,
            total_changes INT NOT NULL DEFAULT 1,
            attachment_path VARCHAR(255) NULL,
            attachment_type VARCHAR(20) NULL,
            attachment_name VARCHAR(255) NULL,
            approved_by INT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP NULL DEFAULT NULL,
            INDEX ix_scr_assignment (assignment_id),
            INDEX ix_scr_teacher (teacher_id),
            INDEX ix_scr_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _ensure_table(
        "score_change_details",
        """
        CREATE TABLE IF NOT EXISTS score_change_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            request_id INT NOT NULL,
            score_id BIGINT NOT NULL,
            student_id INT NOT NULL,
            score_column VARCHAR(30) NOT NULL,
            old_value DECIMAL(4,2) NOT NULL,
            new_value DECIMAL(4,2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            note VARCHAR(255) NULL,
            approved_by INT NULL,
            resolved_at TIMESTAMP NULL DEFAULT NULL,
            INDEX ix_scd_request (request_id),
            INDEX ix_scd_score (score_id),
            INDEX ix_scd_student (student_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )

    _ensure_table(
        "email_outbox",
        """
        CREATE TABLE IF NOT EXISTS email_outbox (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            to_email VARCHAR(255) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            related_type VARCHAR(50) NULL,
            related_id INT NULL,
            is_sent TINYINT(1) NOT NULL DEFAULT 0,
            sent_at TIMESTAMP NULL DEFAULT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX ix_outbox_sent (is_sent)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    )


def seed_demo(reset_scores=False):
    """Seed dữ liệu mẫu: GV, lớp, môn, assignment, học sinh."""
    print("[2/4] Seed dữ liệu nền...")

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
    from studentapp.models.class_room import Class
    from studentapp.models.grade import Grade
    from studentapp.models.semester import Semester
    from studentapp.models.student import Student, StudentStatusEnum
    from studentapp.models.subject import Subject
    from studentapp.models.teaching_assignment import TeachingAssignment
    from studentapp.models.user import User, UserRoleEnum

    # --- Bảng nền: năm học / khối / học kỳ ---
    year = AcademicYear.query.filter_by(year_name="2026-2027").first()
    if year is None:
        year = AcademicYear(year_name="2026-2027", start_year=2026, end_year=2027, is_current=True)
        db.session.add(year)
    grade = Grade.query.filter_by(grade_level=10).first()
    if grade is None:
        grade = Grade(grade_level=10, grade_name="Khối 10")
        db.session.add(grade)
    db.session.flush()

    semester = Semester.query.filter_by(
        semester_name="Học kỳ 1", academic_year_id=year.id
    ).first()
    if semester is None:
        semester = Semester(
            semester_name="Học kỳ 1",
            academic_year_id=year.id,
            factor=1,
            is_current=True,
        )
        db.session.add(semester)
    db.session.flush()

    # --- Môn học ---
    subject = Subject.query.filter_by(subject_code="TOAN10").first()
    if subject is None:
        subject = Subject(
            subject_code="TOAN10",
            subject_name="Toán học 10",
            grade_id=grade.id,
            periods_count=4,
        )
        db.session.add(subject)
    db.session.flush()

    # --- Tài khoản ---
    def ensure_user(username, email, full_name, role, password):
        u = User.query.filter_by(username=username).first()
        if u is None:
            u = User(username=username, email=email, full_name=full_name, role=role)
            db.session.add(u)
            db.session.flush()
        # Luôn ép mật khẩu demo về giá trị cố định để test Postman ổn định.
        u.set_password(password)
        u.is_active = True
        u.is_locked = False
        u.failed_attempts = 0
        return u

    teacher = ensure_user(
        "gv01", "gv01@school.local", "Nguyễn Văn An", UserRoleEnum.TEACHER, "Gv@123456"
    )
    other_teacher = ensure_user(
        "gv02", "gv02@school.local", "Trần Thị Bình", UserRoleEnum.TEACHER, "Gv@123456"
    )
    ensure_user(
        "giaovu", "giaovu@school.local", "Giáo Vụ", UserRoleEnum.ACADEMIC, "Admin@123"
    )

    # --- Lớp ---
    class_room = Class.query.filter_by(class_name="10A1").first()
    if class_room is None:
        class_room = Class(
            class_name="10A1",
            grade_id=grade.id,
            academic_year_id=year.id,
            homeroom_teacher_id=teacher.id,
        )
        db.session.add(class_room)
        db.session.flush()
    else:
        class_room.homeroom_teacher_id = teacher.id
        class_room.academic_year_id = year.id

    # --- Phân công giảng dạy ---
    assignment = TeachingAssignment.query.filter_by(
        teacher_id=teacher.id, class_id=class_room.id, subject_id=subject.id
    ).first()
    if assignment is None:
        assignment = TeachingAssignment(
            teacher_id=teacher.id,
            class_id=class_room.id,
            subject_id=subject.id,
            semester_id=semester.id,
            is_locked=False,
        )
        db.session.add(assignment)
        db.session.flush()

    other_assignment = TeachingAssignment.query.filter_by(
        teacher_id=other_teacher.id, class_id=class_room.id, subject_id=subject.id
    ).first()
    if other_assignment is None:
        db.session.add(
            TeachingAssignment(
                teacher_id=other_teacher.id,
                class_id=class_room.id,
                subject_id=subject.id,
                semester_id=semester.id,
                is_locked=False,
            )
        )

    # --- Học sinh + ghi danh lớp ---
    student_names = [
        ("HS2026001", "Nguyễn Văn An"),
        ("HS2026002", "Trần Thị Bình"),
        ("HS2026003", "Lê Văn Cường"),
        ("HS2026004", "Phạm Thị Dung"),
        ("HS2026005", "Hoàng Văn Em"),
    ]
    for code, name in student_names:
        st = Student.query.filter_by(student_code=code).first()
        if st is None:
            st = Student(
                student_code=code,
                full_name=name,
                gender="Nam",
                date_of_birth=date(2010, 1, 1),
                status=StudentStatusEnum.DANG_HOC,
            )
            db.session.add(st)
            db.session.flush()
        enrolled = ClassEnrollment.query.filter_by(
            student_id=st.id, class_id=class_room.id
        ).first()
        if enrolled is None:
            db.session.add(
                ClassEnrollment(
                    student_id=st.id,
                    class_id=class_room.id,
                    academic_year_id=year.id,
                    enrollment_date=date(2026, 9, 1),
                    status=EnrollmentStatusEnum.DANG_HOC,
                )
            )

    db.session.commit()
    print(f"  GV giao viên      : {teacher.username} / Gv@123456  (id={teacher.id})")
    print(f"  GV khác           : {other_teacher.username} / Gv@123456  (id={other_teacher.id})")
    print(f"  Lớp               : {class_room.class_name} (id={class_room.id})")
    print(f"  Môn               : {subject.subject_name} (id={subject.id})")
    print(f"  Assignment (GV1)  : id={assignment.id}  (dùng cho {{assignmentId}})")
    print(f"  Assignment (GV2)  : id={other_assignment.id if other_assignment else '-'}")
    return teacher, assignment


def reset_score_data():
    """Xoá sạch dữ liệu điểm + đơn từ chối + đơn phúc khảo (để test lại từ đầu)."""
    print("[3/4] Xoá dữ liệu điểm cũ (--reset)...")
    from sqlalchemy import text

    db.session.execute(text("DELETE FROM score_change_details"))
    db.session.execute(text("DELETE FROM score_change_requests"))
    db.session.execute(text("DELETE FROM score_submissions"))
    db.session.execute(text("DELETE FROM scores"))
    db.session.execute(text("UPDATE teaching_assignments SET is_locked = 0, locked_at = NULL"))
    db.session.commit()


def print_ids():
    """In ra các ID quan trọng để điền vào biến Postman."""
    print("[4/4] ID tham chiếu cho Postman")
    from studentapp.models.class_room import Class
    from studentapp.models.student import Student
    from studentapp.models.subject import Subject
    from studentapp.models.teaching_assignment import TeachingAssignment
    from studentapp.models.user import User, UserRoleEnum

    # Lấy GV đang có assignment để biến Postman trỏ đúng lớp GV phụ trách.
    assignment = (
        TeachingAssignment.query.join(
            User, TeachingAssignment.teacher_id == User.id
        )
        .filter(User.role == UserRoleEnum.TEACHER)
        .order_by(TeachingAssignment.id)
        .first()
    )
    teacher = (
        User.query.get(assignment.teacher_id)
        if assignment
        else User.query.filter_by(role=UserRoleEnum.TEACHER).order_by(User.id).first()
    )
    class_room = Class.query.order_by(Class.id).first()
    subject = Subject.query.order_by(Subject.id).first()
    student = Student.query.order_by(Student.id).first()

    print("-" * 58)
    print(f"  {{{{teacherId}}}}      = {teacher.id if teacher else '-'}")
    print(f"  {{{{classId}}}}        = {class_room.id if class_room else '-'}")
    print(f"  {{{{subjectId}}}}      = {subject.id if subject else '-'}")
    print(f"  {{{{studentId}}}}      = {student.id if student else '-'}")
    print(f"  {{{{assignmentId}}}}   = {assignment.id if assignment else '-'}")
    print("-" * 58)


def main():
    parser = argparse.ArgumentParser(description="Seed dữ liệu demo cho module Giáo viên")
    parser.add_argument(
        "--reset", action="store_true", help="Xoá sạch dữ liệu điểm trước khi seed"
    )
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        db.create_all()
        sync_schema()
        if args.reset:
            reset_score_data()
        seed_demo()
        print_ids()
    print("\n✅ Hoàn tất. Mở Postman và import file postman_teacher_collection.json")


if __name__ == "__main__":
    main()
