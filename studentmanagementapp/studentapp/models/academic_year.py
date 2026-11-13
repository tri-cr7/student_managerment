"""ENTITY academic_years — Năm học."""
from studentapp.extensions import db


class AcademicYear(db.Model):
    __tablename__ = "academic_years"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year_name = db.Column(db.String(20), unique=True, nullable=False)
    start_year = db.Column(db.Integer, nullable=False)
    end_year = db.Column(db.Integer, nullable=False)
    is_current = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "year_name": self.year_name,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "is_current": bool(self.is_current),
        }
