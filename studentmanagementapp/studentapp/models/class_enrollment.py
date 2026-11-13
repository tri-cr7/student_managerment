"""ENTITY class_enrollments — Danh sách học sinh thuộc lớp (Yêu cầu 2)."""
import enum

from studentapp.extensions import db


class EnrollmentStatusEnum(enum.Enum):
    DANG_HOC = "DANG_HOC"
    DA_CHUYEN = "DA_CHUYEN"


class ClassEnrollment(db.Model):
    __tablename__ = "class_enrollments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    academic_year_id = db.Column(
        db.Integer, db.ForeignKey("academic_years.id"), nullable=False
    )
    enrollment_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(EnrollmentStatusEnum), nullable=False, default=EnrollmentStatusEnum.DANG_HOC
    )
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )

    student = db.relationship("Student", backref=db.backref("enrollments", lazy=True))
    class_room = db.relationship("Class", backref=db.backref("enrollments", lazy=True))
