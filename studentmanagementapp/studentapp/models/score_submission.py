"""ENTITY score_submissions — Đơn gửi duyệt bảng điểm (SD23/SD24).

Vòng đời trạng thái::

    (chưa gửi) --Gửi duyệt--> PENDING --+-- Giáo vụ DUYỆT ----> APPROVED
                                         |
                                         +-- Giáo vụ TỪ CHỐI --> REJECTED
                                         |
                                         +-- GV bấm Hủy ------> CANCELLED

* ``PENDING``   → GV **không sửa được** bảng điểm tạm (423 ``SCORE_SUBMISSION_PENDING``).
* ``CANCELLED`` → GV sửa lại được rồi gửi duyệt lại (bản ghi cũ giữ làm lịch sử).
* ``APPROVED``  → bảng điểm đã chốt, GV không sửa được → phải gửi đơn phúc khảo (SD25).
"""
from studentapp.extensions import db


class SubmissionStatusEnum:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    ALL = (PENDING, APPROVED, REJECTED, CANCELLED)
    #: Trạng thái mà Giáo viên còn có thể hủy.
    CANCELLABLE = (PENDING,)


class ScoreSubmission(db.Model):
    __tablename__ = "score_submissions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("teaching_assignments.id"), nullable=False
    )
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default=SubmissionStatusEnum.PENDING
    )
    total_students = db.Column(db.Integer, nullable=False, default=0)
    total_scores = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.String(255), nullable=True)
    submitted_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    review_note = db.Column(db.String(255), nullable=True)
    reviewed_at = db.Column(db.TIMESTAMP, nullable=True)
    cancelled_at = db.Column(db.TIMESTAMP, nullable=True)
    cancel_note = db.Column(db.String(255), nullable=True)

    assignment = db.relationship(
        "TeachingAssignment", backref=db.backref("score_submissions", lazy=True)
    )

    def is_pending(self) -> bool:
        return self.status == SubmissionStatusEnum.PENDING

    def to_dict(self):
        return {
            "submission_id": self.id,
            "assignment_id": self.assignment_id,
            "teacher_id": self.teacher_id,
            "status": self.status,
            "total_students": self.total_students,
            "total_scores": self.total_scores,
            "note": self.note,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_by": self.reviewed_by,
            "review_note": self.review_note,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancel_note": self.cancel_note,
        }
