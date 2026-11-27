from datetime import datetime

from studentapp.exceptions import (
    InvalidSubmissionStatusError,
    NotFoundError,
    ValidationError,
)
from studentapp.extensions import db
from studentapp.models.score_submission import ScoreSubmission, SubmissionStatusEnum

def _get_or_404(submission_id):
    try:
        sid = int(submission_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy đơn gửi duyệt.")
    row = db.session.get(ScoreSubmission, sid)
    if row is None:
        raise NotFoundError("Không tìm thấy đơn gửi duyệt.")
    return row

def _ensure_pending(submission):
    if not submission.is_pending():
        raise InvalidSubmissionStatusError(
            "Chỉ có thể duyệt/từ chối đơn đang ở trạng thái chờ duyệt! "
            f"Đơn hiện tại đang ở trạng thái {submission.status}.",
            current_status=submission.status,
        )
    return submission

def _enrich(submission):
    item = submission.to_dict()
    a = submission.assignment
    if a is not None:
        item["class_name"] = a.class_room.class_name if a.class_room else None
        item["subject_name"] = a.subject.subject_name if a.subject else None
        item["semester_name"] = a.semester.semester_name if a.semester else None
        item["academic_year"] = (
            a.semester.academic_year.year_name
            if a.semester and a.semester.academic_year
            else None
        )
        item["is_locked"] = bool(a.is_locked)
        item["class_id"] = a.class_id
        item["subject_id"] = a.subject_id
        item["semester_id"] = a.semester_id
    from studentapp.repositories import user_repository

    teacher = user_repository.get_by_id(submission.teacher_id)
    item["teacher"] = (
        {"id": teacher.id, "full_name": teacher.full_name} if teacher else None
    )
    return item

def enrich_submission(submission):

    return _enrich(submission)

def _write_audit(user_id, action, details):
    from studentapp.utils.audit import write_audit

    write_audit(user_id, action, details)

def _enqueue_mail(to_email, subject, body, related_id):
    from studentapp.models.email_outbox import EmailOutbox

    db.session.add(EmailOutbox(
        to_email=to_email, subject=subject, body=body,
        related_type="score_submission", related_id=int(related_id),
    ))

def list_submissions(status=None, page=1, limit=20):
    q = ScoreSubmission.query
    if status not in (None, ""):
        q = q.filter_by(status=str(status).strip().upper())
    total = q.count()
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = min(100, max(1, int(limit)))
    except (TypeError, ValueError):
        limit = 20
    rows = (
        q.order_by(ScoreSubmission.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total, "page": page, "limit": limit,
        "data": [_enrich(r) for r in rows],
    }

def get_submission(submission_id, teacher_id=None, is_academic=False):

    sub = _get_or_404(submission_id)
    if not is_academic:
        if teacher_id is None:
            from studentapp.exceptions import PermissionDeniedError

            raise PermissionDeniedError("Bạn không có quyền xem đơn gửi duyệt này.")
        if int(sub.teacher_id) != int(teacher_id):
            from studentapp.exceptions import PermissionDeniedError

            raise PermissionDeniedError(
                "Bạn không có quyền xem đơn gửi duyệt của người khác."
            )
    item = _enrich(sub)
    from studentapp.repositories import score_repository

    draft_rows = score_repository.list_by_assignment(sub.assignment_id, draft_only=True)
    official_rows = score_repository.list_by_assignment(sub.assignment_id, draft_only=False)
    item["draft_count"] = len(draft_rows)
    item["official_count"] = len(official_rows)
    item["draft_scores"] = [r.to_dict() for r in draft_rows]
    return item

def approve_submission(submission_id, payload, reviewer_id=None):

    from studentapp.models.score import Score
    from studentapp.models.teaching_assignment import TeachingAssignment
    from studentapp.repositories import user_repository

    sub = _ensure_pending(_get_or_404(submission_id))
    review_note = (payload.get("review_note") or "").strip() or None
    now = datetime.utcnow()

    db.session.query(Score).filter_by(
        assignment_id=sub.assignment_id, is_draft=True
    ).update({Score.is_draft: False}, synchronize_session=False)

    assignment = db.session.get(TeachingAssignment, sub.assignment_id)
    if assignment is not None:
        assignment.is_locked = True
        assignment.locked_at = now
        db.session.add(assignment)

    sub.status = SubmissionStatusEnum.APPROVED
    sub.reviewed_by = reviewer_id
    sub.review_note = review_note
    sub.reviewed_at = now
    db.session.add(sub)

    _write_audit(reviewer_id, "SCORE_TABLE_APPROVED", {
        "submission_id": sub.id, "assignment_id": sub.assignment_id,
    })
    teacher = user_repository.get_by_id(sub.teacher_id)
    if teacher is not None and teacher.email:
        _enqueue_mail(
            teacher.email,
            "Bảng điểm đã được Giáo vụ duyệt & chốt",
            f"Bảng điểm assignment #{sub.assignment_id} đã được duyệt"
            f"{(': ' + review_note) if review_note else ''}. "
            "Điểm đã trở thành chính thức.",
            sub.id,
        )
    db.session.commit()
    return _enrich(sub)

def reject_submission(submission_id, payload, reviewer_id=None):

    from studentapp.repositories import user_repository

    sub = _ensure_pending(_get_or_404(submission_id))
    review_note = (payload.get("review_note") or "").strip()
    if not review_note:
        raise ValidationError("Vui lòng nêu rõ lý do từ chối để giáo viên sửa lại.")
    now = datetime.utcnow()
    sub.status = SubmissionStatusEnum.REJECTED
    sub.reviewed_by = reviewer_id
    sub.review_note = review_note
    sub.reviewed_at = now
    db.session.add(sub)
    _write_audit(reviewer_id, "SCORE_TABLE_REJECTED", {
        "submission_id": sub.id, "assignment_id": sub.assignment_id,
        "review_note": review_note,
    })
    teacher = user_repository.get_by_id(sub.teacher_id)
    if teacher is not None and teacher.email:
        _enqueue_mail(
            teacher.email,
            "Bảng điểm bị từ chối — cần sửa lại",
            f"Bảng điểm assignment #{sub.assignment_id} bị từ chối: {review_note}. "
            "Vui lòng sửa bảng điểm tạm và gửi duyệt lại.",
            sub.id,
        )
    db.session.commit()
    return _enrich(sub)
