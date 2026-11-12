"""ENTITY teaching_assignments — Phân công giảng dạy (lớp + môn + GV + kỳ).

Cờ `is_locked` mang ý nghĩa **"đã chốt bảng điểm"**:
* ``False`` → bảng điểm đang MỞ, Giáo viên nhập/sửa điểm tạm được.
* ``True``  → bảng điểm đã CHỐT, Giáo viên không sửa trực tiếp được
  (phải gửi đơn phúc khảo ``POST /score-requests``).
"""
from studentapp.extensions import db


class TeachingAssignment(db.Model):
    __tablename__ = "teaching_assignments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    locked_at = db.Column(db.TIMESTAMP, nullable=True)
    created_at = db.Column(
        db.TIMESTAMP, nullable=False, server_default=db.func.current_timestamp()
    )

    teacher = db.relationship("User", backref=db.backref("teaching_assignments", lazy=True))
    class_room = db.relationship("Class", backref=db.backref("teaching_assignments", lazy=True))
    subject = db.relationship("Subject", backref=db.backref("teaching_assignments", lazy=True))
    semester = db.relationship("Semester", backref=db.backref("teaching_assignments", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "class_id": self.class_id,
            "subject_id": self.subject_id,
            "semester_id": self.semester_id,
            "is_locked": bool(self.is_locked),
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
        }
