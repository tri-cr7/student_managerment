import enum

from studentapp.extensions import db

class StudentStatusEnum(enum.Enum):

    DANG_HOC = "DANG_HOC"
    THOI_HOC = "THOI_HOC"
    BAO_LUU = "BAO_LUU"

class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_code = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    citizen_id = db.Column(db.String(20), unique=True, nullable=True)
    parent_name = db.Column(db.String(100), nullable=True)
    parent_phone = db.Column(db.String(15), nullable=True)
    status = db.Column(
        db.Enum(StudentStatusEnum), nullable=False, default=StudentStatusEnum.DANG_HOC
    )

    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    deleted_at = db.Column(db.TIMESTAMP, nullable=True)

    deleted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    deleted_reason = db.Column(db.String(500), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )
    updated_at = db.Column(
        db.TIMESTAMP,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "student_code": self.student_code,
            "full_name": self.full_name,
            "gender": self.gender,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "citizen_id": self.citizen_id,
            "parent_name": self.parent_name,
            "parent_phone": self.parent_phone,
            "status": self.status.value if self.status else None,
            "is_deleted": bool(self.is_deleted),
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_reason": self.deleted_reason,
        }
