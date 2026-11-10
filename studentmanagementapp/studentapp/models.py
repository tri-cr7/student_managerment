import enum
from studentapp import db,app
from flask_login import UserMixin

class UserRoleEnum(enum.Enum):
    ADMIN = 'admin'
    TEACHER = 'teacher'
    EMPLOYEE = 'employee'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    user_role = db.Column(db.Enum(UserRoleEnum), default=UserRoleEnum.EMPLOYEE, nullable=False)

    def __str__(self):
        return self.name

if __name__== '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
