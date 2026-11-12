"""ENTITY email_outbox — Hàng đợi gửi mail (Outbox Pattern).

Vì sao không gửi mail trực tiếp trong transaction nghiệp vụ:
nếu SMTP lỗi *sau khi* đã gửi mail nhưng *trước khi* commit → Giáo viên nhận mail
"đã duyệt" trong khi DB rollback → mất tính nhất quán dữ liệu.

Cách làm đúng: ``INSERT INTO email_outbox`` trong cùng transaction → sau ``COMMIT``,
worker đọc outbox & gửi mail.
"""
from studentapp.extensions import db


class EmailOutbox(db.Model):
    __tablename__ = "email_outbox"

    id = db.Column(
        db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    to_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    related_type = db.Column(db.String(50), nullable=True)
    related_id = db.Column(db.Integer, nullable=True)
    is_sent = db.Column(db.Boolean, nullable=False, default=False)
    sent_at = db.Column(db.TIMESTAMP, nullable=True)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )
