"""ENTITY score_change_details — Ô điểm được đề nghị sửa (đơn con), SD25/SD19.

Trạng thái thật của từng ô nằm ở đây — Giáo vụ duyệt/từ chối **độc lập từng ô**
(đơn lô có thể duyệt 15/20 ô, từ chối 5 ô).
"""
from studentapp.extensions import db


class ChangeDetailStatusEnum:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    ALL = (PENDING, APPROVED, REJECTED)


class ScoreChangeDetail(db.Model):
    __tablename__ = "score_change_details"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_id = db.Column(
        db.Integer, db.ForeignKey("score_change_requests.id"), nullable=False
    )
    score_id = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"),
        db.ForeignKey("scores.id"),
        nullable=False,
    )
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    score_column = db.Column(db.String(30), nullable=False)
    old_value = db.Column(db.Numeric(4, 2), nullable=False)
    new_value = db.Column(db.Numeric(4, 2), nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default=ChangeDetailStatusEnum.PENDING
    )
    note = db.Column(db.String(255), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolved_at = db.Column(db.TIMESTAMP, nullable=True)

    request = db.relationship("ScoreChangeRequest", back_populates="details")
    score = db.relationship("Score", backref=db.backref("change_details", lazy=True))
    student = db.relationship("Student", backref=db.backref("change_details", lazy=True))

    def to_dict(self):
        return {
            "detail_id": self.id,
            "request_id": self.request_id,
            "score_id": self.score_id,
            "student_id": self.student_id,
            "score_column": self.score_column,
            "old_value": float(self.old_value),
            "new_value": float(self.new_value),
            "status": self.status,
            "note": self.note,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
