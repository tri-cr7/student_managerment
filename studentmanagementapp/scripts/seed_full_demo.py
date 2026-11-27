import argparse
import os
import sys
from datetime import date, datetime, timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import text

from studentapp import create_app
from studentapp.extensions import db

DEFAULT_PASSWORD = "Test@123456"

ALEMBIC_HEAD = "f6a7b8c9d0e1"

LEGACY_TABLES = ("attendances", "score_change_request_items")

def wipe_database():

    print("[1/4] Xoá toàn bộ database...")

    engine = db.engine
    with engine.connect() as conn:

        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")
        conn.commit()

        inspector = db.inspect(conn)
        existing = set(inspector.get_table_names())

        db.metadata.drop_all(bind=conn)

        for table in LEGACY_TABLES:
            if table in existing:
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS `{table}`")
                print(f"  - bảng legacy `{table}`")

        if "alembic_version" in existing:
            conn.exec_driver_sql("DELETE FROM alembic_version")
        conn.commit()

        db.metadata.create_all(bind=conn)
        conn.commit()

        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()

    print(f"  ✓ đã dựng lại {len(db.metadata.tables)} bảng")

    _verify_schema_matches_model()

    _ensure_one_class_triggers()

    db.session.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:v) "
             "ON DUPLICATE KEY UPDATE version_num = :v"),
        {"v": ALEMBIC_HEAD},
    )
    db.session.commit()
    print(f"  ✓ alembic_version = {ALEMBIC_HEAD}")

_TRIGGER_DDL = (
    "CREATE TRIGGER `{name}`\n"
    "{clause} ON `class_enrollments`\n"
    "FOR EACH ROW\n"
    "BEGIN\n"
    "    IF NEW.status = 'DANG_HOC' {extra} THEN\n"
    "        IF (SELECT COUNT(*) FROM `class_enrollments`\n"
    "            WHERE student_id = NEW.student_id\n"
    "              AND status = 'DANG_HOC'{exclude}) >= 1 THEN\n"
    "            SIGNAL SQLSTATE '45000'\n"
    "                SET MESSAGE_TEXT = 'VI PHAM QUY TAT: 1 hoc sinh chi duoc hoc "
    "1 lop tai mot thoi diem (da ton tai enrollment DANG_HOC cho hoc sinh nay).';\n"
    "        END IF;\n"
    "    END IF;\n"
    "END"
)

_TRIGGER_INS = "trg_class_enrollments_one_active_ins"
_TRIGGER_UPD = "trg_class_enrollments_one_active_upd"

def _ensure_one_class_triggers():

    from sqlalchemy import inspect

    engine = db.engine
    if engine.dialect.name == "mysql":
        existing = set()
        with engine.connect() as conn:
            rows = conn.exec_driver_sql(
                "SELECT TRIGGER_NAME FROM information_schema.TRIGGERS "
                "WHERE TRIGGER_SCHEMA = DATABASE()"
            ).fetchall()
            existing = {r[0] for r in rows}

            for name, clause, extra, exclude in (
                (_TRIGGER_INS, "BEFORE INSERT", "", ""),
                (_TRIGGER_UPD, "BEFORE UPDATE", "AND OLD.status <> 'DANG_HOC'",
                 " AND id <> NEW.id"),
            ):
                if name in existing:
                    continue
                conn.exec_driver_sql(
                    _TRIGGER_DDL.format(
                        name=name, clause=clause, extra=extra, exclude=exclude
                    )
                )
                print(f"  ✓ trigger `{name}`")
            conn.commit()
    else:

        with engine.connect() as conn:
            for name in (_TRIGGER_INS, _TRIGGER_UPD):
                conn.exec_driver_sql(f"DROP TRIGGER IF EXISTS `{name}`")
            conn.exec_driver_sql(
                "CREATE TRIGGER `trg_class_enrollments_one_active_ins` "
                "BEFORE INSERT ON `class_enrollments` "
                "WHEN NEW.status = 'DANG_HOC' AND ("
                "SELECT COUNT(*) FROM `class_enrollments` "
                "WHERE student_id = NEW.student_id AND status = 'DANG_HOC') >= 1 "
                "BEGIN SELECT RAISE(ABORT, 'VI PHAM QUY TAT: 1 hoc sinh chi duoc "
                "hoc 1 lop tai mot thoi diem.'); END"
            )
            conn.exec_driver_sql(
                "CREATE TRIGGER `trg_class_enrollments_one_active_upd` "
                "BEFORE UPDATE ON `class_enrollments` "
                "WHEN NEW.status = 'DANG_HOC' AND OLD.status <> 'DANG_HOC' AND ("
                "SELECT COUNT(*) FROM `class_enrollments` "
                "WHERE student_id = NEW.student_id AND status = 'DANG_HOC' "
                "AND id <> NEW.id) >= 1 "
                "BEGIN SELECT RAISE(ABORT, 'VI PHAM QUY TAT: 1 hoc sinh chi duoc "
                "hoc 1 lop tai mot thoi diem.'); END"
            )
            conn.commit()
        print("  ✓ trigger one-active-class (SQLite)")

def _verify_schema_matches_model():

    inspector = db.inspect(db.engine)
    db_tables = set(inspector.get_table_names())
    meta_tables = set(db.metadata.tables.keys())

    drift = []
    for table in sorted(db_tables & meta_tables):
        db_cols = {c["name"] for c in inspector.get_columns(table)}
        model_cols = {c.name for c in db.metadata.tables[table].columns}
        missing = model_cols - db_cols
        extra = db_cols - model_cols
        if missing or extra:
            drift.append(f"    [{table}] thiếu={sorted(missing)} thừa={sorted(extra)}")

    if drift:
        print("  ⚠ SCHEMA LỆCH với model:")
        for line in drift:
            print(line)
    else:
        print("  ✓ schema khớp hoàn toàn với model")

def _w(name, start, end, is_current=False):
    from studentapp.models.academic_year import AcademicYear

    row = AcademicYear(year_name=name, start_year=start, end_year=end,
                       is_current=is_current)
    db.session.add(row)
    db.session.flush()
    return row

def _s(name, year_id, factor, is_current=False):

    from studentapp.models.semester import Semester

    assert name in Semester.SEMESTER_NAMES, f"Học kỳ không hợp lệ: {name}"
    row = Semester(semester_name=name, academic_year_id=year_id,
                   factor=Semester.factor_for(name), is_current=is_current)
    db.session.add(row)
    db.session.flush()
    return row

def _g(level, name):
    from studentapp.models.grade import Grade

    row = Grade(grade_level=level, grade_name=name)
    db.session.add(row)
    db.session.flush()
    return row

def _sub(code, name, grade_id, periods):
    from studentapp.models.subject import Subject

    row = Subject(subject_code=code, subject_name=name, grade_id=grade_id,
                  periods_count=periods, is_active=True)
    db.session.add(row)
    db.session.flush()
    return row

def _user(username, email, full_name, role, password):
    from studentapp.models.user import User

    row = User(username=username, email=email, full_name=full_name, role=role,
               is_active=True, is_locked=False, failed_attempts=0,
               must_change_password=False)
    row.set_password(password)
    db.session.add(row)
    db.session.flush()
    return row

def _student(code, name, gender, dob, phone, email, cccd, status,
             address=None, parent_name=None, parent_phone=None,
             is_deleted=False, deleted_reason=None):
    from studentapp.models.student import Student

    row = Student(
        student_code=code, full_name=name, gender=gender, date_of_birth=dob,
        address=address, phone=phone, email=email, citizen_id=cccd,
        parent_name=parent_name, parent_phone=parent_phone,
        status=status, is_deleted=is_deleted,
        deleted_at=datetime.utcnow() if is_deleted else None,
        deleted_reason=deleted_reason,
        created_by=None,
    )
    db.session.add(row)
    db.session.flush()
    return row

def _enroll(student_id, class_id, year_id, enroll_date, status):
    from studentapp.models.class_enrollment import ClassEnrollment

    row = ClassEnrollment(student_id=student_id, class_id=class_id,
                          academic_year_id=year_id, enrollment_date=enroll_date,
                          status=status)
    db.session.add(row)
    db.session.flush()
    return row

def _assignment(teacher_id, class_id, subject_id, semester_id, is_locked=False):
    from studentapp.models.teaching_assignment import TeachingAssignment

    row = TeachingAssignment(teacher_id=teacher_id, class_id=class_id,
                             subject_id=subject_id, semester_id=semester_id,
                             is_locked=is_locked,
                             locked_at=datetime.utcnow() if is_locked else None)
    db.session.add(row)
    db.session.flush()
    return row

def _score(assignment_id, student_id, values, is_draft, updated_by,
           submitted_at=None):

    from studentapp.models.score import Score
    from studentapp.services.score_calculator import calculate_average

    score_map = {
        "score_15m_1": values[0], "score_15m_2": values[1], "score_15m_3": values[2],
        "score_15m_4": values[3], "score_15m_5": values[4],
        "score_45m_1": values[5], "score_45m_2": values[6], "score_45m_3": values[7],
        "score_final": values[8],
    }
    avg = calculate_average(score_map)
    passed = None if avg is None else (avg >= 5.0)

    row = Score(assignment_id=assignment_id, student_id=student_id,
                average_score=avg, is_passed=passed, is_draft=is_draft,
                submitted_at=submitted_at, updated_by=updated_by,
                **score_map)
    db.session.add(row)
    db.session.flush()
    return row

def seed_all(password):

    from studentapp.models.class_enrollment import EnrollmentStatusEnum
    from studentapp.models.score_change_detail import ChangeDetailStatusEnum
    from studentapp.models.score_change_request import (
        ChangeRequestStatusEnum,
        ScoreChangeRequest,
    )
    from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum
    from studentapp.models.student import StudentStatusEnum
    from studentapp.models.user import UserRoleEnum

    from studentapp.models.system_rule import DEFAULT_RULES, SystemRule

    print("[2/4] Seed quy định hệ thống...")
    for key, value, dtype, desc in DEFAULT_RULES:
        db.session.add(SystemRule(rule_key=key, rule_value=value,
                                  data_type=dtype, description=desc))
    db.session.flush()

    print("[3/4] Seed danh mục & nghiệp vụ...")
    y2024 = _w("2024-2025", 2024, 2025, is_current=False)
    y2025 = _w("2025-2026", 2025, 2026, is_current=False)
    y2026 = _w("2026-2027", 2026, 2027, is_current=True)

    sem_hk1_2024 = _s("HK1", y2024.id, 1)
    sem_hk2_2024 = _s("HK2", y2024.id, 2)
    sem_hk1_2025 = _s("HK1", y2025.id, 1)
    sem_hk2_2025 = _s("HK2", y2025.id, 2)
    sem_hk1 = _s("HK1", y2026.id, 1, is_current=True)
    sem_hk2 = _s("HK2", y2026.id, 2)

    g10 = _g(10, "Khối 10")
    g11 = _g(11, "Khối 11")
    g12 = _g(12, "Khối 12")

    toan = _sub("TOAN10", "Toán học 10", g10.id, 4)
    vaty = _sub("VATLY10", "Vật lý 10", g10.id, 3)
    nguvan = _sub("NGUVAN10", "Ngữ văn 10", g10.id, 3)

    academics = [
        _user("giaovu", "giaovu@school.local", "Giáo Vụ Chính",
              UserRoleEnum.ACADEMIC, password),
        _user("admin01", "admin01@school.local", "Quản Trị Hệ Thống 01",
              UserRoleEnum.ACADEMIC, password),
        _user("admin02", "admin02@school.local", "Quản Trị Hệ Thống 02",
              UserRoleEnum.ACADEMIC, password),
    ]
    teachers = [
        _user("gv01", "gv01@school.local", "Nguyễn Văn An",
              UserRoleEnum.TEACHER, password),
        _user("gv02", "gv02@school.local", "Trần Thị Bình",
              UserRoleEnum.TEACHER, password),
        _user("gv03", "gv03@school.local", "Lê Văn Cường",
              UserRoleEnum.TEACHER, password),
    ]
    staffs = [
        _user("nv01", "nv01@school.local", "Phạm Thị Dung",
              UserRoleEnum.STAFF, password),
        _user("nv02", "nv02@school.local", "Hoàng Văn Em",
              UserRoleEnum.STAFF, password),
        _user("nv03", "nv03@school.local", "Vũ Thị Phương",
              UserRoleEnum.STAFF, password),
    ]
    db.session.flush()
    giaovu = academics[0]

    from studentapp.models.class_room import Class

    classes = {}
    for name, homeroom in (("10A1", teachers[0]), ("10A2", teachers[1]),
                           ("10A3", teachers[2])):
        row = Class(class_name=name, grade_id=g10.id, academic_year_id=y2026.id,
                    homeroom_teacher_id=homeroom.id, current_size=0)
        db.session.add(row)
        db.session.flush()
        classes[name] = row

    d = date

    def mk(code, name, gender, dob, phone, email, cccd, status,
           is_deleted=False, deleted_reason=None, parent="Nguyễn Văn Ba",
           parent_phone="0900000000", address="Số 1, Đường Nguyễn Huệ, Hà Nội"):
        return _student(code, name, gender, dob, phone, email, cccd, status,
                        address=address, parent_name=parent,
                        parent_phone=parent_phone, is_deleted=is_deleted,
                        deleted_reason=deleted_reason)

    a1_s1 = mk("HS2026001", "Nguyễn Văn An", "Nam", d(2009, 3, 12),
               "0901000001", "hs2026001@student.local", "001099000001",
               StudentStatusEnum.DANG_HOC)
    a1_s2 = mk("HS2026002", "Trần Thị Bình", "Nữ", d(2009, 7, 5),
               "0901000002", "hs2026002@student.local", "001099000002",
               StudentStatusEnum.DANG_HOC)
    a1_s3 = mk("HS2026003", "Lê Văn Cường", "Nam", d(2009, 11, 20),
               "0901000003", "hs2026003@student.local", "001099000003",
               StudentStatusEnum.DANG_HOC)
    a1_s4 = mk("HS2026004", "Phạm Thị Dung", "Nữ", d(2008, 1, 30),
               "0901000004", "hs2026004@student.local", "001099000004",
               StudentStatusEnum.BAO_LUU)

    a2_s1 = mk("HS2026005", "Hoàng Văn Em", "Nam", d(2009, 5, 18),
               "0901000005", "hs2026005@student.local", "001099000005",
               StudentStatusEnum.DANG_HOC)
    a2_s2 = mk("HS2026006", "Vũ Thị Phương", "Nữ", d(2009, 9, 8),
               "0901000006", "hs2026006@student.local", "001099000006",
               StudentStatusEnum.DANG_HOC)
    a2_s3 = mk("HS2026007", "Đặng Thị Quỳnh", "Nữ", d(2009, 2, 25),
               "0901000007", "hs2026007@student.local", "001099000007",
               StudentStatusEnum.DANG_HOC)
    a2_rubbish = mk("HS2026008", "Hồ Sơ Rác", "Nam", d(2010, 1, 1),
                    "0901000008", "hs2026008@student.local", "001099000008",
                    StudentStatusEnum.THOI_HOC, is_deleted=True,
                    deleted_reason="Nhập nhầm trong đợt tuyển sinh")

    a3_s1 = mk("HS2026009", "Bùi Văn Hùng", "Nam", d(2009, 6, 14),
               "0901000009", "hs2026009@student.local", "001099000009",
               StudentStatusEnum.DANG_HOC)
    a3_s2 = mk("HS2026010", "Đỗ Thị Lan", "Nữ", d(2009, 10, 2),
               "0901000010", "hs2026010@student.local", "001099000010",
               StudentStatusEnum.DANG_HOC)
    a3_s3 = mk("HS2026011", "Ngô Văn Hải", "Nam", d(2009, 12, 27),
               "0901000011", "hs2026011@student.local", "001099000011",
               StudentStatusEnum.DANG_HOC)

    a2_s4 = mk("HS2026012", "Trương Thị Mỹ", "Nữ", d(2008, 8, 9),
               "0901000012", "hs2026012@student.local", "001099000012",
               StudentStatusEnum.THOI_HOC)

    for st in (a1_s1, a1_s2, a1_s3, a1_s4, a2_s1, a2_s2, a2_s3, a2_rubbish,
               a3_s1, a3_s2, a3_s3, a2_s4):
        st.created_by = giaovu.id
    db.session.flush()

    enroll_date = date(2026, 9, 1)
    for st in (a1_s1, a1_s2, a1_s3):
        _enroll(st.id, classes["10A1"].id, y2026.id, enroll_date,
                EnrollmentStatusEnum.DANG_HOC)

    _enroll(a1_s4.id, classes["10A1"].id, y2026.id, enroll_date,
            EnrollmentStatusEnum.DA_CHUYEN)
    for st in (a2_s1, a2_s2, a2_s3):
        _enroll(st.id, classes["10A2"].id, y2026.id, enroll_date,
                EnrollmentStatusEnum.DANG_HOC)

    _enroll(a2_rubbish.id, classes["10A2"].id, y2026.id, enroll_date,
            EnrollmentStatusEnum.DA_CHUYEN)
    for st in (a3_s1, a3_s2, a3_s3):
        _enroll(st.id, classes["10A3"].id, y2026.id, enroll_date,
                EnrollmentStatusEnum.DANG_HOC)
    db.session.flush()

    classes["10A1"].current_size = 3
    classes["10A2"].current_size = 3
    classes["10A3"].current_size = 3
    db.session.flush()

    a1 = _assignment(teachers[0].id, classes["10A1"].id, toan.id, sem_hk1.id, True)
    a2 = _assignment(teachers[0].id, classes["10A1"].id, toan.id, sem_hk2.id, True)
    a3 = _assignment(teachers[1].id, classes["10A2"].id, vaty.id, sem_hk1.id, False)
    a4 = _assignment(teachers[2].id, classes["10A3"].id, nguvan.id, sem_hk1.id, False)
    a5 = _assignment(teachers[1].id, classes["10A2"].id, vaty.id, sem_hk2.id, False)

    FULL_A = (8.0, 7.5, 8.5, 9.0, 8.0, 7.0, 8.0, 7.5, 7.5)
    FULL_A2 = (8.5, 7.5, 8.5, 9.0, 8.0, 7.0, 8.0, 7.5, 7.5)
    FULL_B = (7.0, 7.5, 6.5, 8.0, 7.5, 6.5, 7.0, 6.5, 7.0)
    FULL_B2 = (7.0, 7.5, 6.5, 8.0, 7.5, 6.5, 7.0, 6.5, 7.5)
    FULL_C = (9.0, 8.5, 9.0, 9.5, 8.5, 8.0, 8.5, 8.0, 8.0)
    PARTIAL = (7.5, None, 8.0, None, 7.0, None, 7.5, None, None)

    now = datetime.utcnow()
    locked_at = now - timedelta(days=20)

    s_a1_1 = _score(a1.id, a1_s1.id, FULL_A, False, teachers[0].id, locked_at)
    s_a1_2 = _score(a1.id, a1_s2.id, FULL_B2, False, teachers[0].id, locked_at)
    s_a1_3 = _score(a1.id, a1_s3.id, FULL_C, False, teachers[0].id, locked_at)

    s_a2_1 = _score(a2.id, a1_s1.id, FULL_A2, False, teachers[0].id, locked_at)
    s_a2_2 = _score(a2.id, a1_s2.id, FULL_B, False, teachers[0].id, locked_at)
    s_a2_3 = _score(a2.id, a1_s3.id, FULL_C, False, teachers[0].id, locked_at)

    s_a3_1 = _score(a3.id, a2_s1.id, FULL_A, True, teachers[1].id, now)
    s_a3_2 = _score(a3.id, a2_s2.id, FULL_B, True, teachers[1].id, now)
    s_a3_3 = _score(a3.id, a2_s3.id, FULL_C, True, teachers[1].id, now)

    s_a4_1 = _score(a4.id, a3_s1.id, FULL_A, True, teachers[2].id, None)
    s_a4_2 = _score(a4.id, a3_s2.id, FULL_C, True, teachers[2].id, None)
    s_a4_3 = _score(a4.id, a3_s3.id, PARTIAL, True, teachers[2].id, None)

    s_a5_1 = _score(a5.id, a2_s1.id, FULL_A, True, teachers[1].id, None)
    s_a5_2 = _score(a5.id, a2_s2.id, FULL_B, True, teachers[1].id, None)
    s_a5_3 = _score(a5.id, a2_s3.id, PARTIAL, True, teachers[1].id, None)

    sub_pending = ScoreSubmission(
        assignment_id=a3.id, teacher_id=teachers[1].id,
        status=SubmissionStatusEnum.PENDING, total_students=3, total_scores=27,
        note="Bảng điểm Vật lý 10A2 học kỳ 1 — xin Giáo vụ duyệt giúp.",
        submitted_at=now - timedelta(days=2),
    )
    sub_approved = ScoreSubmission(
        assignment_id=a2.id, teacher_id=teachers[0].id,
        status=SubmissionStatusEnum.APPROVED, total_students=3, total_scores=27,
        note="Bảng điểm Toán 10A1 học kỳ 2.",
        submitted_at=now - timedelta(days=25),
        reviewed_by=academics[0].id, review_note="Đã kiểm tra, điểm hợp lệ.",
        reviewed_at=locked_at,
    )
    sub_cancelled = ScoreSubmission(
        assignment_id=a4.id, teacher_id=teachers[2].id,
        status=SubmissionStatusEnum.CANCELLED, total_students=3, total_scores=17,
        note="Bảng điểm Ngữ văn 10A3 học kỳ 1.",
        submitted_at=now - timedelta(days=5),
        cancelled_at=now - timedelta(days=4),
        cancel_note="Còn thiếu điểm 1 tiết của 1 học sinh, sửa lại rồi gửi lại.",
    )
    for sub in (sub_pending, sub_approved, sub_cancelled):
        db.session.add(sub)
    db.session.flush()

    cr_pending = ScoreChangeRequest(
        assignment_id=a1.id, teacher_id=teachers[0].id,
        reason="Học sinh Nguyễn Văn An bị chấm nhầm điểm 15 phút đầu tiên, "
               "xin Giáo vụ đối chiếu và sửa.",
        status=ChangeRequestStatusEnum.PENDING, is_batch=False, total_changes=1,
        created_at=now - timedelta(days=3),
    )
    cr_approved = ScoreChangeRequest(
        assignment_id=a2.id, teacher_id=teachers[0].id,
        reason="Đề bài kiểm tra 15 phút có lỗi trích xuất, xin sửa điểm cho "
               "học sinh Nguyễn Văn An.",
        status=ChangeRequestStatusEnum.APPROVED, is_batch=False, total_changes=1,
        approved_by=academics[0].id,
        approval_note="Đã đối chiếu bài làm — duyệt.",
        created_at=now - timedelta(days=18),
        resolved_at=locked_at,
    )
    cr_rejected = ScoreChangeRequest(
        assignment_id=a1.id, teacher_id=teachers[0].id,
        reason="Xin nâng điểm thi cuối kỳ của học sinh Trần Thị Bình.",
        status=ChangeRequestStatusEnum.REJECTED, is_batch=False, total_changes=1,
        approved_by=academics[1].id,
        approval_note="Không có minh chứng kèm theo, điểm thi giữ nguyên.",
        created_at=now - timedelta(days=15),
        resolved_at=now - timedelta(days=14),
    )
    for cr in (cr_pending, cr_approved, cr_rejected):
        db.session.add(cr)
    db.session.flush()

    from studentapp.models.score_change_detail import ScoreChangeDetail

    details = [

        (cr_pending, s_a1_1, a1_s1, "score_15m_1", 8.0, 9.0,
         ChangeDetailStatusEnum.PENDING, None),
        (cr_approved, s_a2_1, a1_s1, "score_15m_1", 8.0, 8.5,
         ChangeDetailStatusEnum.APPROVED, None),
        (cr_rejected, s_a1_2, a1_s2, "score_final", 7.5, 8.5,
         ChangeDetailStatusEnum.REJECTED, "Không có minh chứng kèm theo."),
    ]
    for cr, score, stu, col, old, new, status, note in details:
        db.session.add(ScoreChangeDetail(
            request_id=cr.id, score_id=score.id, student_id=stu.id,
            score_column=col, old_value=old, new_value=new,
            status=status, note=note,
            approved_by=None if status == ChangeDetailStatusEnum.PENDING
            else academics[0].id,
            resolved_at=None if status == ChangeDetailStatusEnum.PENDING
            else (locked_at if status == ChangeDetailStatusEnum.APPROVED
                  else now - timedelta(days=14)),
        ))
    db.session.flush()

    from studentapp.models.audit_log import AuditLog

    audits = [
        (academics[0].id, "ADMIT_STUDENT",
         {"student_id": a1_s1.id, "student_code": a1_s1.student_code,
          "full_name": a1_s1.full_name}),
        (academics[0].id, "ADMIT_STUDENT",
         {"student_id": a1_s2.id, "student_code": a1_s2.student_code,
          "full_name": a1_s2.full_name}),
        (academics[0].id, "CREATE_CLASS",
         {"class_id": classes["10A1"].id, "class_name": "10A1",
          "grade_id": g10.id, "academic_year_id": y2026.id}),
        (academics[0].id, "CREATE_ASSIGNMENT",
         {"assignment_id": a1.id, "teacher_id": teachers[0].id,
          "class_id": classes["10A1"].id, "subject_id": toan.id,
          "semester_id": sem_hk1.id}),
        (teachers[0].id, "SAVE_SCORES",
         {"assignment_id": a1.id, "total_rows": 3}),
        (teachers[0].id, "SUBMIT_SCORES",
         {"assignment_id": a2.id, "total_rows": 3}),
        (academics[0].id, "SCORE_TABLE_APPROVED",
         {"submission_id": sub_approved.id, "assignment_id": a2.id}),
        (teachers[2].id, "CANCEL_SCORE_SUBMISSION",
         {"submission_id": sub_cancelled.id, "assignment_id": a4.id}),
        (teachers[0].id, "CREATE_SCORE_CHANGE_REQUEST",
         {"request_id": cr_pending.id, "assignment_id": a1.id,
          "total_changes": 1}),
        (academics[0].id, "APPROVE_SCORE_CHANGE",
         {"request_id": cr_approved.id, "assignment_id": a2.id,
          "approved_count": 1, "rejected_count": 0,
          "status": "APPROVED"}),
        (academics[1].id, "REJECT_SCORE_CHANGE",
         {"request_id": cr_rejected.id, "assignment_id": a1.id,
          "rejected_count": 1,
          "rejection_note": "Không có minh chứng kèm theo."}),
        (academics[0].id, "DELETE_STUDENT_SOFT",
         {"student_id": a2_rubbish.id, "student_code": a2_rubbish.student_code,
          "full_name": a2_rubbish.full_name,
          "reason": "Nhập nhầm trong đợt tuyển sinh",
          "from_status": "DANG_HOC", "to_status": "THOI_HOC"}),
    ]
    for uid, action, details_json in audits:
        db.session.add(AuditLog(user_id=uid, action=action,
                                details=details_json, ip_address="127.0.0.1"))
    db.session.flush()

    from studentapp.models.email_outbox import EmailOutbox

    emails = [
        (teachers[0].email, "Bảng điểm đã được Giáo vụ duyệt & chốt",
         "Bảng điểm assignment #%d đã được duyệt. Điểm đã trở thành chính thức."
         % a2.id, "score_submission", sub_approved.id, True),
        (teachers[0].email, "Đơn phúc khảo đã được Giáo vụ xử lý",
         "Đơn #%d: duyệt 1 ô, từ chối 0 ô. Trạng thái đơn: APPROVED."
         % cr_approved.id, "score_change_request", cr_approved.id, True),
        (teachers[0].email, "Đơn phúc khảo bị từ chối",
         "Đơn #%d bị từ chối toàn bộ: Không có minh chứng kèm theo."
         % cr_rejected.id, "score_change_request", cr_rejected.id, False),
    ]
    for to, subject, body, rtype, rid, sent in emails:
        db.session.add(EmailOutbox(to_email=to, subject=subject, body=body,
                                   related_type=rtype, related_id=rid,
                                   is_sent=sent,
                                   sent_at=locked_at if sent else None))
    db.session.flush()

    from studentapp.models.password_otp import OtpPurpose, PasswordOtp

    otp_code = "123456"
    db.session.add(PasswordOtp(
        user_id=staffs[0].id, purpose=OtpPurpose.FORGOT, code=otp_code,
        expires_at=datetime.utcnow() + timedelta(minutes=5), attempts=0,
        used=False,
    ))
    db.session.flush()

    db.session.commit()

    return {
        "years": [y2024, y2025, y2026],
        "semesters": [sem_hk1_2024, sem_hk2_2024, sem_hk1_2025, sem_hk2_2025,
                      sem_hk1, sem_hk2],
        "grades": [g10, g11, g12],
        "subjects": [toan, vaty, nguvan],
        "classes": classes,
        "academics": academics,
        "teachers": teachers,
        "staffs": staffs,
        "assignments": [a1, a2, a3, a4, a5],
        "submissions": [sub_pending, sub_approved, sub_cancelled],
        "change_requests": [cr_pending, cr_approved, cr_rejected],
        "otp_code": otp_code,
    }

COUNT_TABLES = (
    ("users", "Tài khoản"),
    ("academic_years", "Năm học"),
    ("semesters", "Học kỳ"),
    ("grades", "Khối lớp"),
    ("subjects", "Môn học"),
    ("classes", "Lớp học"),
    ("students", "Học sinh"),
    ("class_enrollments", "Ghi danh lớp"),
    ("teaching_assignments", "Phân công giảng dạy"),
    ("scores", "Dòng điểm"),
    ("score_submissions", "Đơn gửi duyệt"),
    ("score_change_requests", "Đơn phúc khảo"),
    ("score_change_details", "Ô điểm đề nghị sửa"),
    ("system_rules", "Quy định hệ thống"),
    ("audit_logs", "Nhật ký hệ thống"),
    ("email_outbox", "Hàng đợi email"),
    ("password_otps", "Mã OTP"),
)

def print_summary():
    print("[4/4] Tổng kết dữ liệu đã seed:")
    print("-" * 52)
    for table, label in COUNT_TABLES:
        try:
            n = db.session.execute(
                text(f"SELECT COUNT(*) FROM `{table}`")
            ).scalar()
        except Exception:
            n = "-"
        print(f"  {label:<26}{n}")
    print("-" * 52)

def print_accounts(password):
    print("\n" + "=" * 66)
    print(f"{'USERNAME':<12}{'ROLE':<10}{'PASSWORD':<16}EMAIL")
    print("=" * 66)
    from studentapp.models.user import User

    for u in User.query.order_by(User.id).all():
        print(f"{u.username:<12}{u.role.value:<10}{password:<16}{u.email}")
    print("=" * 66)
    print("Mã OTP quên mật khẩu (cho nv01): 123456 — hết hạn sau 5 phút.")

def main():
    parser = argparse.ArgumentParser(
        description="Xoá toàn bộ DB & seed lại ~3 bản ghi cho mỗi thứ"
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("TEST_ACCOUNTS_PASSWORD", DEFAULT_PASSWORD),
        help="Mật khẩu chung cho các tài khoản test.",
    )
    parser.add_argument(
        "--no-wipe",
        action="store_true",
        help="Không xoá schema cũ — chỉ seed thêm dữ liệu mẫu.",
    )
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        if not args.no_wipe:
            wipe_database()
        seed_all(args.password)
        print_summary()
        print_accounts(args.password)

    print("\n✅ Hoàn tất. Đăng nhập tại http://127.0.0.1:5500/pages/login.html")

if __name__ == "__main__":
    main()
