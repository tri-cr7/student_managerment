from studentapp.extensions import db

SCORE_COLUMNS_15M = ("score_15m_1", "score_15m_2", "score_15m_3", "score_15m_4", "score_15m_5")
SCORE_COLUMNS_45M = ("score_45m_1", "score_45m_2", "score_45m_3")
SCORE_COLUMN_FINAL = "score_final"

ALL_SCORE_COLUMNS = SCORE_COLUMNS_15M + SCORE_COLUMNS_45M + (SCORE_COLUMN_FINAL,)

SCORE_GROUPS = (
    {"key": "15m", "label": "Điểm 15'", "columns": SCORE_COLUMNS_15M,
     "min_rule": "MIN_COL_15M", "max_rule": "MAX_COL_15M"},
    {"key": "45m", "label": "Điểm 1 tiết", "columns": SCORE_COLUMNS_45M,
     "min_rule": "MIN_COL_45M", "max_rule": "MAX_COL_45M"},
    {"key": "final", "label": "Điểm thi", "columns": (SCORE_COLUMN_FINAL,),
     "min_rule": "NUM_COL_FINAL", "max_rule": "NUM_COL_FINAL"},
)

WEIGHT_15M = 1
WEIGHT_45M = 2
WEIGHT_FINAL = 3

MIN_SCORE = 0.0
MAX_SCORE = 10.0

class Score(db.Model):
    __tablename__ = "scores"

    id = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("teaching_assignments.id"), nullable=False
    )
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    score_15m_1 = db.Column(db.Numeric(4, 2), nullable=True)
    score_15m_2 = db.Column(db.Numeric(4, 2), nullable=True)
    score_15m_3 = db.Column(db.Numeric(4, 2), nullable=True)
    score_15m_4 = db.Column(db.Numeric(4, 2), nullable=True)
    score_15m_5 = db.Column(db.Numeric(4, 2), nullable=True)
    score_45m_1 = db.Column(db.Numeric(4, 2), nullable=True)
    score_45m_2 = db.Column(db.Numeric(4, 2), nullable=True)
    score_45m_3 = db.Column(db.Numeric(4, 2), nullable=True)
    score_final = db.Column(db.Numeric(4, 2), nullable=True)

    average_score = db.Column(db.Numeric(4, 2), nullable=True)
    is_passed = db.Column(db.Boolean, nullable=True)
    is_draft = db.Column(db.Boolean, nullable=False, default=True)
    submitted_at = db.Column(db.TIMESTAMP, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(
        db.TIMESTAMP,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    assignment = db.relationship(
        "TeachingAssignment", backref=db.backref("scores", lazy=True)
    )
    student = db.relationship("Student", backref=db.backref("scores", lazy=True))

    def score_map(self) -> dict:

        return {col: getattr(self, col) for col in ALL_SCORE_COLUMNS}

    def to_dict(self):
        return {
            "id": self.id,
            "assignment_id": self.assignment_id,
            "student_id": self.student_id,
            "average_score": float(self.average_score) if self.average_score is not None else None,
            "is_passed": None if self.is_passed is None else bool(self.is_passed),
            "is_draft": bool(self.is_draft),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            **self.score_map(),
        }
