import enum
from studentapp import db,app
from flask_login import UserMixin

class UserRoleEnum(enum.Enum):
    ADMIN = 'admin'
    TEACHER = 'teacher'
    EMPLOYEE = 'employee'

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    role = db.Column(db.Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.EMPLOYEE)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())
    def __str__(self):
        return self.name


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.JSON, nullable=True)  # Native JSON column for before/after changes
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    # Optional relationship back to User if you want to display username easily
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

    def __str__(self):
        return self.name
if __name__== '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
