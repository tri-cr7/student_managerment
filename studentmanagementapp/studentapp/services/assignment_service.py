"""SERVICE assignment — phân công giảng dạy cho Giáo vụ (SD16).

Quy tắc:
* Giáo viên được phân công phải tồn tại, đang active, không bị khóa,
  role = TEACHER (ACADEMIC cũng được chấp nhận để kiêm nhiệm).
* Lớp / môn / học kỳ phải tồn tại.
* Unique (class_id, subject_id, semester_id) → trùng thì 409.
* Xóa chỉ khi chưa phát sinh điểm (scores) và chưa có đơn gửi duyệt (SD24/SD19).
"""
from studentapp.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from studentapp.extensions import db
from studentapp.models.user import UserRoleEnum
from studentapp.repositories import teaching_assignment_repository


def _as_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} không hợp lệ.")


def _get_or_404(assignment_id):
    row = teaching_assignment_repository.get_by_id(assignment_id)
    if row is None:
        raise NotFoundError("Không tìm thấy phân công giảng dạy.")
    return row


def _ensure_teacher(teacher_id):
    from studentapp.repositories import user_repository

    tid = _as_int(teacher_id, "teacher_id")
    user = user_repository.get_by_id(tid)
    if user is None:
        raise NotFoundError("Không tìm thấy giáo viên được phân công.")
    if user.role not in (UserRoleEnum.TEACHER, UserRoleEnum.ACADEMIC):
        raise ValidationError(
            "Người được phân công phải có vai trò Giáo viên (TEACHER).",
            error="INVALID_TEACHER_ROLE",
        )
    if not bool(user.is_active) or bool(user.is_locked):
        raise ValidationError(
            "Giáo viên không còn hoạt động nên không thể phân công.",
            error="TEACHER_INACTIVE",
        )
    return user


def _ensure_class(class_id):
    from studentapp.models.class_room import Class

    cid = _as_int(class_id, "class_id")
    row = db.session.get(Class, cid)
    if row is None:
        raise NotFoundError("Không tìm thấy lớp học.")
    return row


def _ensure_subject(subject_id):
    from studentapp.models.subject import Subject

    sid = _as_int(subject_id, "subject_id")
    row = db.session.get(Subject, sid)
    if row is None:
        raise NotFoundError("Không tìm thấy môn học.")
    if not bool(row.is_active):
        raise ValidationError(
            "Môn học đã ngừng hoạt động nên không thể phân công.",
            error="SUBJECT_INACTIVE",
        )
    return row


def _ensure_semester(semester_id):
    from studentapp.models.semester import Semester

    sid = _as_int(semester_id, "semester_id")
    row = db.session.get(Semester, sid)
    if row is None:
        raise NotFoundError("Không tìm thấy học kỳ.")
    return row


def _enrich(row):
    item = row.to_dict()
    item["teacher_name"] = row.teacher.full_name if row.teacher else None
    item["class_name"] = row.class_room.class_name if row.class_room else None
    item["subject_name"] = row.subject.subject_name if row.subject else None
    item["semester_name"] = row.semester.semester_name if row.semester else None
    item["academic_year_name"] = (
        row.semester.academic_year.year_name
        if row.semester and row.semester.academic_year
        else None
    )
    item["scores_count"] = teaching_assignment_repository.count_scores(row.id)
    item["has_pending_submission"] = (
        teaching_assignment_repository.get_pending_submission(row.id) is not None
    )
    return item


def _write_audit(actor_id, action, details):
    from studentapp.models.audit_log import AuditLog

    try:
        uid = int(actor_id) if actor_id is not None else None
    except (TypeError, ValueError):
        uid = None
    db.session.add(AuditLog(user_id=uid, action=action, details=details))


# --------------------------------------------------------------------------- #
# SD16 — CRUD
# --------------------------------------------------------------------------- #


def list_assignments(page=1, limit=20, teacher_id=None,
                     semester_id=None, class_id=None, subject_id=None):
    result = teaching_assignment_repository.list_all(
        page=page, limit=limit, teacher_id=teacher_id,
        semester_id=semester_id, class_id=class_id, subject_id=subject_id,
    )
    result["data"] = [_enrich(r) for r in result["data"]]
    return result


def get_assignment(assignment_id):
    return _enrich(_get_or_404(assignment_id))


def create_assignment(payload, actor_id=None):
    teacher = _ensure_teacher(payload.get("teacher_id"))
    cls = _ensure_class(payload.get("class_id"))
    subject = _ensure_subject(payload.get("subject_id"))
    semester = _ensure_semester(payload.get("semester_id"))

    dup = teaching_assignment_repository.get_by_triplet(cls.id, subject.id, semester.id)
    if dup is not None:
        raise DuplicateError(
            f"Lớp {cls.class_name} — môn {subject.subject_name} — "
            f"{semester.semester_name} đã được phân công cho giáo viên khác "
            f"(assignment id={dup.id})."
        )

    row = teaching_assignment_repository.create(teacher.id, cls.id, subject.id, semester.id)
    _write_audit(actor_id, "CREATE_ASSIGNMENT", {
        "assignment_id": row.id, "teacher_id": teacher.id,
        "class_id": cls.id, "subject_id": subject.id, "semester_id": semester.id,
    })
    db.session.commit()
    return _enrich(row)


def update_assignment(assignment_id, payload, actor_id=None):
    row = _get_or_404(assignment_id)

    new_teacher_id = row.teacher_id
    new_class_id = row.class_id
    new_subject_id = row.subject_id
    new_semester_id = row.semester_id

    if payload.get("teacher_id") not in (None, ""):
        new_teacher_id = _ensure_teacher(payload.get("teacher_id")).id
    if payload.get("class_id") not in (None, ""):
        new_class_id = _ensure_class(payload.get("class_id")).id
    if payload.get("subject_id") not in (None, ""):
        new_subject_id = _ensure_subject(payload.get("subject_id")).id
    if payload.get("semester_id") not in (None, ""):
        new_semester_id = _ensure_semester(payload.get("semester_id")).id

    if (
        (new_class_id, new_subject_id, new_semester_id)
        != (row.class_id, row.subject_id, row.semester_id)
    ):
        dup = teaching_assignment_repository.get_by_triplet(
            new_class_id, new_subject_id, new_semester_id, exclude_id=row.id
        )
        if dup is not None:
            raise DuplicateError(
                "Bộ ba lớp–môn–kỳ sau khi sửa bị trùng với một phân công khác "
                f"(assignment id={dup.id})."
            )

    row.teacher_id = int(new_teacher_id)
    row.class_id = int(new_class_id)
    row.subject_id = int(new_subject_id)
    row.semester_id = int(new_semester_id)
    db.session.add(row)
    _write_audit(actor_id, "UPDATE_ASSIGNMENT", {
        "assignment_id": row.id, "teacher_id": row.teacher_id,
        "class_id": row.class_id, "subject_id": row.subject_id,
        "semester_id": row.semester_id,
    })
    db.session.commit()
    return _enrich(row)


def delete_assignment(assignment_id, actor_id=None):
    row = _get_or_404(assignment_id)
    if bool(row.is_locked):
        raise BusinessRuleError(
            "Bảng điểm đã chốt nên không thể hủy phân công. "
            "Hãy mở khóa trước nếu thật sự cần hủy."
        )
    if teaching_assignment_repository.count_scores(row.id) > 0:
        raise BusinessRuleError(
            "Lớp môn học đã phát sinh điểm nên không thể hủy phân công.",
            error="ASSIGNMENT_HAS_SCORES",
        )
    if teaching_assignment_repository.has_submissions(row.id):
        raise BusinessRuleError(
            "Lớp môn học đã có đơn gửi duyệt nên không thể hủy phân công.",
            error="ASSIGNMENT_HAS_SUBMISSIONS",
        )
    snapshot = _enrich(row)
    teaching_assignment_repository.delete_row(row)
    _write_audit(actor_id, "DELETE_ASSIGNMENT", {"assignment_id": assignment_id})
    db.session.commit()
    return snapshot


# --------------------------------------------------------------------------- #
# SD18 — Khóa / mở bảng điểm thủ công
# --------------------------------------------------------------------------- #


def set_lock(assignment_id, is_locked, actor_id=None):
    """Khóa / mở bảng điểm thủ công (SD18).

    * Khóa (``is_locked=True``): ``locked_at = now()`` — GV không sửa trực tiếp
      được, muốn sửa phải gửi đơn phúc khảo (SD25).
    * Mở (``is_locked=False``): ``locked_at = None`` — điểm chính thức giữ
      nguyên ``is_draft = FALSE``; GV sửa sẽ chuyển dòng thành bản nháp rồi
      gửi duyệt lại (SD23 → SD24).
    """
    from datetime import datetime

    row = _get_or_404(assignment_id)
    want = bool(is_locked)
    if want:
        row.is_locked = True
        row.locked_at = datetime.utcnow()
        action = "LOCK_SCORE_TABLE"
        message = "Đã khóa bảng điểm thành công. Giáo viên không thể chỉnh sửa điểm trực tiếp."
    else:
        row.is_locked = False
        row.locked_at = None
        action = "UNLOCK_SCORE_TABLE"
        message = (
            "Đã mở khóa bảng điểm thành công. Giáo viên có thể sửa "
            "bảng điểm tạm và gửi duyệt lại."
        )
    db.session.add(row)
    _write_audit(actor_id, action, {
        "assignment_id": row.id, "is_locked": bool(row.is_locked),
    })
    db.session.commit()
    return {"message": message, **_enrich(row)}
