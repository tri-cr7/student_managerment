"""ENTITY semesters — Học kỳ trong một năm học."""
from studentapp.extensions import db


class Semester(db.Model):
    __tablename__ = "semesters"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    semester_name = db.Column(db.String(20), nullable=False)
    academic_year_id = db.Column(
        db.Integer, db.ForeignKey("academic_years.id"), nullable=False
    )
    factor = db.Column(db.Integer, nullable=False, default=1)
    is_current = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )

    academic_year = db.relationship("AcademicYear", backref=db.backref("semesters", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "semester_name": self.semester_name,
            "academic_year_id": self.academic_year_id,
            "factor": self.factor,
            "is_current": bool(self.is_current),
        }
