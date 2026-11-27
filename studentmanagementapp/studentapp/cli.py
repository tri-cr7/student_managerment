import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from studentapp import create_app
from studentapp.extensions import db
from studentapp.models.user import User, UserRoleEnum
from studentapp.utils.validators import is_email, is_strong_password

ADMIN_ROLES = (UserRoleEnum.ACADEMIC, UserRoleEnum.STAFF)

def _app():
    cfg = os.environ.get("FLASK_CONFIG", "development")
    return create_app(cfg)

def _find(username=None, email=None):
    q = User.query
    if username:
        q = q.filter_by(username=username)
    elif email:
        q = q.filter_by(email=email)
    else:
        raise SystemExit("Thiếu --username hoặc --email.")
    return q.first()

def cmd_list_admins(args):
    app = _app()
    with app.app_context():
        users = User.query.filter(User.role.in_(ADMIN_ROLES)).order_by(User.id).all()
        if not users:
            print("Khong co tai khoan quan tri nao.")
            return
        print(f"{'ID':<5}{'USERNAME':<18}{'ROLE':<10}{'LOCKED':<8}EMAIL")
        print("-" * 78)
        for u in users:
            lock = "CO" if u.is_locked else "KHONG"
            print(f"{u.id:<5}{u.username:<18}{u.role.value:<10}{lock:<8}{u.email}")
        print(f"\nTong: {len(users)} tai khoan quan tri.")

def cmd_unlock(args):
    app = _app()
    with app.app_context():
        u = _find(args.username, args.email)
        if u is None:
            raise SystemExit("Khong tim thay tai khoan.")
        if not u.is_locked:
            print(f"Tai khoan '{u.username}' van dang mo khoa.")
            return
        u.is_locked = False
        u.failed_attempts = 0
        u.locked_at = None
        db.session.commit()
        print(f"Da mo khoa tai khoan '{u.username}'.")

def cmd_reset_admin(args):
    app = _app()
    with app.app_context():
        u = _find(args.username, args.email)
        if u is None:
            raise SystemExit("Khong tim thay tai khoan.")

        pwd = args.password
        if not pwd:
            pwd = getpass.getpass("Mat khau moi: ")
            pwd2 = getpass.getpass("Nhap lai mat khau moi: ")
            if pwd != pwd2:
                raise SystemExit("Hai lan nhap mat khau khong khop.")
        ok, msg = is_strong_password(pwd)
        if not ok:
            raise SystemExit(
                msg + " (>=8 ky tu, co Hoa + thuong + so + ky tu dac biet)."
            )

        u.set_password(pwd)
        u.failed_attempts = 0
        u.is_locked = False
        u.locked_at = None
        u.must_change_password = args.force_change
        u.is_active = True
        db.session.commit()
        print(f"Da dat lai mat khau va mo khoa tai khoan '{u.username}'.")

def cmd_create_admin(args):
    app = _app()
    with app.app_context():
        if User.query.filter_by(username=args.username).first():
            raise SystemExit(f"Username '{args.username}' da ton tai.")
        if User.query.filter_by(email=args.email).first():
            raise SystemExit(f"Email '{args.email}' da ton tai.")
        if not is_email(args.email):
            raise SystemExit("Email sai dinh dang.")

        ok, msg = is_strong_password(args.password)
        if not ok:
            raise SystemExit(
                msg + " (>=8 ky tu, co Hoa + thuong + so + ky tu dac biet)."
            )

        u = User(
            username=args.username,
            email=args.email,
            full_name=args.full_name or args.username,
            phone=args.phone,
            role=UserRoleEnum.ACADEMIC,
        )
        u.set_password(args.password)
        u.must_change_password = True
        db.session.add(u)
        db.session.commit()
        print(f"Da tao tai khoan quan tri '{u.username}' (id={u.id}).")
        print("He thong se yeu cau doi mat khau lan dang nhap dau tien.")

def build_parser():
    p = argparse.ArgumentParser(
        prog="python -m studentapp.cli",
        description="CLI cuu ho tai khoan quan tri.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("list-admins", help="Liet ke tai khoan quan tri.")
    s.set_defaults(func=cmd_list_admins)

    s = sub.add_parser("unlock", help="Mo khoa tai khoan (giu nguyen mat khau).")
    s.add_argument("--username")
    s.add_argument("--email")
    s.set_defaults(func=cmd_unlock)

    s = sub.add_parser("reset-admin", help="Dat lai mat khau + mo khoa tai khoan.")
    s.add_argument("--username")
    s.add_argument("--email")
    s.add_argument("--password", help="Bo trong de nhap an toan.")
    s.add_argument(
        "--force-change",
        action="store_true",
        help="Yeu cau doi mat khau lan dang nhap dau tien.",
    )
    s.set_defaults(func=cmd_reset_admin)

    s = sub.add_parser("create-admin", help="Tao tai khoan quan tri du phong.")
    s.add_argument("--username", required=True)
    s.add_argument("--password", required=True)
    s.add_argument("--email", required=True)
    s.add_argument("--full-name", dest="full_name")
    s.add_argument("--phone")
    s.set_defaults(func=cmd_create_admin)

    return p

def main():
    args = build_parser().parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
