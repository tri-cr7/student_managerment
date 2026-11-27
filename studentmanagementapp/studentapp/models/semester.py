from studentapp.extensions import db

class Semester(db.Model):
    __tablename__ = "semesters"

    SEMESTER_NAMES = ("HK1", "HK2")

    FACTOR_BY_NAME = {"HK1": 1, "HK2": 2}

    DISPLAY_NAMES = {"HK1": "Học kỳ 1", "HK2": "Học kỳ 2"}

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

    __table_args__ = (
        db.UniqueConstraint(
            "academic_year_id", "semester_name", name="uq_semester_year"
        ),
    )

    academic_year = db.relationship("AcademicYear", backref=db.backref("semesters", lazy=True))

    @classmethod
    def factor_for(cls, semester_name):

        return cls.FACTOR_BY_NAME.get(semester_name, 1)

    @classmethod
    def display_name(cls, semester_name):

        return cls.DISPLAY_NAMES.get(semester_name, semester_name)

    def to_dict(self):
        return {
            "id": self.id,
            "semester_name": self.semester_name,
            "semester_display": self.display_name(self.semester_name),
            "academic_year_id": self.academic_year_id,
            "academic_year_name": (
                self.academic_year.year_name if self.academic_year else None
            ),
            "factor": int(self.factor or 1),
            "is_current": bool(self.is_current),
        }
