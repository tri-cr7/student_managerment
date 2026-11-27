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

    transfer_note = db.Column(db.String(255), nullable=True)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )

    __table_args__ = (
        db.Index(
            "idx_student_year_status", "student_id", "academic_year_id", "status"
        ),
        db.Index("idx_enrollment_class", "class_id", "status"),
    )

    student = db.relationship("Student", backref=db.backref("enrollments", lazy=True))
    class_room = db.relationship("Class", backref=db.backref("enrollments", lazy=True))
