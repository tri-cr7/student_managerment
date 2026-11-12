"""ENTITY score_change_requests — Đơn phúc khảo (đơn cha), SD25/SD19.

Chỉ tạo được khi bảng điểm đã **CHỐT** (``teaching_assignments.is_locked = true``)
⇒ mọi ô điểm đã ``NOT NULL`` ⇒ ``old_value`` **luôn có giá trị**.
"""
from studentapp.extensions import db


class ChangeRequestStatusEnum:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"

    ALL = (PENDING, APPROVED, REJECTED, PARTIALLY_APPROVED)


class ScoreChangeRequest(db.Model):
    __tablename__ = "score_change_requests"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("teaching_assignments.id"), nullable=False
    )
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(30), nullable=False, default=ChangeRequestStatusEnum.PENDING
    )
    is_batch = db.Column(db.Boolean, nullable=False, default=False)
    total_changes = db.Column(db.Integer, nullable=False, default=1)
    attachment_path = db.Column(db.String(255), nullable=True)
    attachment_type = db.Column(db.String(20), nullable=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approval_note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )
    resolved_at = db.Column(db.TIMESTAMP, nullable=True)

    #: Khai báo quan hệ ở phía "cha" để cascade delete-orphan hoạt động đúng.
    details = db.relationship(
        "ScoreChangeDetail",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ScoreChangeDetail.id",
    )

    def to_dict(self):
        return {
            "request_id": self.id,
            "assignment_id": self.assignment_id,
            "teacher_id": self.teacher_id,
            "reason": self.reason,
            "status": self.status,
            "is_batch": bool(self.is_batch),
            "total_changes": self.total_changes,
            "attachment_path": self.attachment_path,
            "attachment_type": self.attachment_type,
            "attachment_name": self.attachment_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "details": [d.to_dict() for d in self.details],
        }
