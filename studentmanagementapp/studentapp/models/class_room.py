from studentapp.extensions import db

class Class(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    class_name = db.Column(db.String(50), nullable=False)
    grade_id = db.Column(db.Integer, db.ForeignKey("grades.id"), nullable=False)
    academic_year_id = db.Column(
        db.Integer, db.ForeignKey("academic_years.id"), nullable=False
    )
    homeroom_teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    current_size = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )

    grade = db.relationship("Grade", backref=db.backref("classes", lazy=True))
    academic_year = db.relationship("AcademicYear", backref=db.backref("classes", lazy=True))

    homeroom_teacher = db.relationship(
        "User", backref=db.backref("homeroom_classes", lazy=True)
    )

    __table_args__ = (
        db.UniqueConstraint(
            "class_name", "academic_year_id", name="uq_class_name_year"
        ),
        db.Index("idx_classes_grade_year", "grade_id", "academic_year_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "class_name": self.class_name,
            "grade_id": self.grade_id,
            "academic_year_id": self.academic_year_id,
            "homeroom_teacher_id": self.homeroom_teacher_id,
            "current_size": self.current_size,
        }
