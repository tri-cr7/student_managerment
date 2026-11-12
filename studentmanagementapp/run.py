"""Dev entry: venv/bin/python run.py (port 5001)."""
import os

from studentapp import create_app
from studentapp.extensions import db

app = create_app("development")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        from studentapp.models.system_rule import SystemRule, DEFAULT_RULES

        for k, v, t, d in DEFAULT_RULES:
            if not SystemRule.query.filter_by(rule_key=k).first():
                db.session.add(SystemRule(rule_key=k, rule_value=v, data_type=t, description=d))

        from studentapp.models.user import User, UserRoleEnum

        seed_user = os.environ.get("SEED_ADMIN_USERNAME", "giaovu")
        seed_email = os.environ.get("SEED_ADMIN_EMAIL", "giaovu@school.local")
        seed_pass = os.environ.get("SEED_ADMIN_PASSWORD", "Admin@123")
        if not User.query.filter_by(username=seed_user).first():
            admin = User(
                username=seed_user,
                email=seed_email,
                full_name="Giao Vu Admin",
                role=UserRoleEnum.ACADEMIC,
            )
            admin.set_password(seed_pass)
            db.session.add(admin)
            print(f"[seed] Da tao admin goc '{seed_user}'. Doi MK ngay sau deploy!")
        db.session.commit()
    app.run(debug=True, port=5001)
