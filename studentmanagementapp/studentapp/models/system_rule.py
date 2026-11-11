"""ENTITY system_rules."""
from studentapp.extensions import db


class SystemRule(db.Model):
    __tablename__ = "system_rules"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rule_key = db.Column(db.String(50), unique=True, nullable=False)
    rule_value = db.Column(db.String(100), nullable=False)
    data_type = db.Column(
        db.Enum("INT", "FLOAT", "STRING", "BOOLEAN", name="rule_data_type"),
        nullable=False,
        server_default="INT",
    )
    description = db.Column(db.String(255), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(
        db.TIMESTAMP,
        nullable=False,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp(),
    )

    def typed_value(self):
        v = self.rule_value
        if self.data_type == "INT":
            return int(float(v))
        if self.data_type == "FLOAT":
            return float(v)
        if self.data_type == "BOOLEAN":
            return str(v).strip().lower() in ("1", "true", "yes")
        return v


DEFAULT_RULES = [
    ("MIN_AGE", "15", "INT", "Do tuoi toi thieu khi tiep nhan hoc sinh (YC 1)"),
    ("MAX_AGE", "20", "INT", "Do tuoi toi da khi tiep nhan hoc sinh (YC 1)"),
    ("MAX_CLASS_SIZE", "40", "INT", "Si so toi da trong mot lop (YC 2)"),
    ("MIN_COL_15M", "1", "INT", "So cot diem 15 phut toi thieu (YC 3)"),
    ("MAX_COL_15M", "5", "INT", "So cot diem 15 phut toi da (YC 3)"),
    ("MIN_COL_45M", "1", "INT", "So cot diem 1 tiet toi thieu (YC 3)"),
    ("MAX_COL_45M", "3", "INT", "So cot diem 1 tiet toi da (YC 3)"),
    ("NUM_COL_FINAL", "1", "INT", "So cot diem thi hoc ky bat buoc (YC 3)"),
    ("PASSING_SCORE", "5.0", "FLOAT", "Diem chuan xep loai Dat mon hoc (YC 4)"),
    ("MAX_LOGIN_ATTEMPTS", "5", "INT", "So lan nhap sai MK toi da truoc khi khoa TK"),
    ("OTP_EXPIRE_MINUTES", "5", "INT", "Thoi gian song OTP 6 so (phut)"),
    ("OTP_MAX_ATTEMPTS", "5", "INT", "So lan nhap sai OTP toi da truoc khi huy ma"),
]
