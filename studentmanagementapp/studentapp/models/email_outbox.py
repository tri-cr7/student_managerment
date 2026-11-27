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
