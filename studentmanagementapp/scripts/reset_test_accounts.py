import argparse
import os
import sys
import uuid

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import text

from studentapp import create_app
from studentapp.extensions import db
from studentapp.models.user import User, UserRoleEnum

DEFAULT_PASSWORD = "Test@123456"

ACCOUNTS = [

    ("giaovu", "giaovu@school.local", "Giáo Vụ Chính", UserRoleEnum.ACADEMIC),
    ("admin01", "admin01@school.local", "Quản Trị Hệ Thống 01", UserRoleEnum.ACADEMIC),
    ("admin02", "admin02@school.local", "Quản Trị Hệ Thống 02", UserRoleEnum.ACADEMIC),
    ("gv01", "gv01@school.local", "Nguyễn Văn An", UserRoleEnum.TEACHER),
    ("gv02", "gv02@school.local", "Trần Thị Bình", UserRoleEnum.TEACHER),
    ("gv03", "gv03@school.local", "Lê Văn Cường", UserRoleEnum.TEACHER),
    ("nv01", "nv01@school.local", "Phạm Thị Dung", UserRoleEnum.STAFF),
    ("nv02", "nv02@school.local", "Hoàng Văn Em", UserRoleEnum.STAFF),
    ("nv03", "nv03@school.local", "Vũ Thị Phương", UserRoleEnum.STAFF),
]

NULLABLE_FKS = [
    ("audit_logs", "user_id"),
    ("scores", "updated_by"),
    ("students", "created_by"),
    ("system_rules", "updated_by"),
    ("classes", "homeroom_teacher_id"),
    ("score_submissions", "reviewed_by"),
    ("score_change_requests", "approved_by"),
    ("score_change_details", "approved_by"),
]

def _wipe_dependents():

    print("[1/4] Dọn dữ liệu phụ thuộc tài khoản...")

    for table in (
        "password_otps",
        "score_change_details",
        "score_change_request_items",
        "score_change_requests",
        "score_submissions",
    ):
        try:
            db.session.execute(text(f"DELETE FROM `{table}`"))
        except Exception as exc:

            db.session.rollback()
            print(f"  ! bỏ qua {table}: {exc}")

    for table, column in NULLABLE_FKS:
        try:
            db.session.execute(text(f"UPDATE `{table}` SET `{column}` = NULL"))
        except Exception as exc:
            db.session.rollback()
            print(f"  ! bỏ qua {table}.{column}: {exc}")
    db.session.commit()

def _create_users(password):

    print("[2/4] Tạo tài khoản mới...")
    users = []
    stamp = uuid.uuid4().hex[:8]
    for idx, (_username, email, full_name, role) in enumerate(ACCOUNTS):
        u = User(
            username=f"tmp_{stamp}_{idx}",
            email=f"tmp_{stamp}_{idx}@tmp.local",
            full_name=full_name,
            role=role,
            is_active=True,
            is_locked=False,
            failed_attempts=0,
            must_change_password=False,
        )
        u.set_password(password)
        db.session.add(u)
        users.append(u)
    db.session.commit()
    return users

def _reassign_demo_data(users):

    print("[3/4] Gán lại dữ liệu demo cho tài khoản mới...")

    teachers = [u for u in users if u.role == UserRoleEnum.TEACHER]
    academics = [u for u in users if u.role == UserRoleEnum.ACADEMIC]
    if not teachers or not academics:
        return

    classes = db.session.execute(text("SELECT id FROM classes ORDER BY id")).fetchall()
    for idx, row in enumerate(classes):
        teacher = teachers[idx % len(teachers)]
        db.session.execute(
            text("UPDATE classes SET homeroom_teacher_id = :tid WHERE id = :cid"),
            {"tid": teacher.id, "cid": row[0]},
        )

    assignments = db.session.execute(
        text("SELECT id FROM teaching_assignments ORDER BY id")
    ).fetchall()
    for idx, row in enumerate(assignments):
        teacher = teachers[idx % len(teachers)]
        db.session.execute(
            text("UPDATE teaching_assignments SET teacher_id = :tid WHERE id = :aid"),
            {"tid": teacher.id, "aid": row[0]},
        )

    first_teacher = teachers[0].id
    for table, column in (
        ("students", "created_by"),
        ("scores", "updated_by"),
    ):
        try:
            db.session.execute(
                text(f"UPDATE `{table}` SET `{column}` = :uid WHERE `{column}` IS NULL"),
                {"uid": first_teacher},
            )
        except Exception as exc:

            db.session.rollback()
            print(f"  ! bỏ qua {table}.{column}: {exc}")
    db.session.commit()

    print("  Phân công giảng dạy:")
    for row in db.session.execute(
        text(
            "SELECT u.username, COUNT(*) FROM teaching_assignments ta "
            "JOIN users u ON u.id = ta.teacher_id GROUP BY u.username ORDER BY u.username"
        )
    ):
        print(f"    {row[0]:<12}{row[1]} lớp-môn")

def _delete_old_users_and_rename(users):

    print("[4/4] Xoá tài khoản cũ & đặt tên cuối cùng...")
    new_ids = [u.id for u in users]
    if new_ids:
        placeholders = ",".join(str(i) for i in new_ids)
        db.session.execute(text(f"DELETE FROM users WHERE id NOT IN ({placeholders})"))
        db.session.commit()

    for idx, u in enumerate(users):
        username, email, _full_name, _role = ACCOUNTS[idx]
        u.username = username
        u.email = email
    db.session.commit()
    return new_ids

def _print_summary(password):
    print("-" * 66)
    print(f"{'USERNAME':<12}{'ROLE':<10}{'PASSWORD':<16}EMAIL")
    print("-" * 66)
    for username, email, _name, role in ACCOUNTS:
        print(f"{username:<12}{role.value:<10}{password:<16}{email}")
    print("-" * 66)
    print("Tất cả: must_change_password = FALSE, đã mở khoá, is_active = TRUE.")

def main():
    parser = argparse.ArgumentParser(description="Reset tài khoản test (3 account/role)")
    parser.add_argument(
        "--password",
        default=os.environ.get("TEST_ACCOUNTS_PASSWORD", DEFAULT_PASSWORD),
        help="Mật khẩu chung cho các tài khoản test.",
    )
    parser.add_argument(
        "--wipe-demo-data",
        action="store_true",
        help="Xoá luôn dữ liệu demo (học sinh, lớp, môn, điểm...).",
    )
    args = parser.parse_args()

    app = create_app("development")
    with app.app_context():
        if args.wipe_demo_data:
            print("[0/4] Xoá dữ liệu demo (học sinh, lớp, môn, điểm)...")
            db.session.execute(text("DELETE FROM scores"))
            db.session.execute(text("DELETE FROM class_enrollments"))
            db.session.execute(text("DELETE FROM teaching_assignments"))
            db.session.execute(text("DELETE FROM classes"))
            db.session.execute(text("DELETE FROM students"))
            db.session.execute(text("DELETE FROM subjects"))
            db.session.commit()

        _wipe_dependents()
        users = _create_users(args.password)
        _reassign_demo_data(users)
        _delete_old_users_and_rename(users)
        _print_summary(args.password)

    print("\n✅ Hoàn tất. Đăng nhập tại http://127.0.0.1:5500/pages/login.html")

if __name__ == "__main__":
    main()
