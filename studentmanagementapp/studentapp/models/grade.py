from studentapp.extensions import db

VALID_GRADE_LEVELS = (10, 11, 12)

class Grade(db.Model):
    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grade_level = db.Column(db.Integer, unique=True, nullable=False)
    grade_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )

    __table_args__ = (
        db.CheckConstraint(
            "grade_level IN (10, 11, 12)",
            name="ck_grades_grade_level",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "grade_level": self.grade_level,
            "grade_name": self.grade_name,
        }
