"""SERVICE change_review — phê duyệt phúc khảo cho Giáo vụ (SD19).

Quy tắc bắt buộc (đã chốt):
* Điểm mới ghi thẳng vào **điểm chính thức** → **giữ nguyên
  ``scores.is_draft = FALSE``**; tuyệt đối KHÔNG ghi vào bảng tạm.
* **KHÔNG** đụng tới ``teaching_assignments.is_locked`` — bảng vẫn ĐÃ CHỐT.
* Tính lại ``average_score`` & ``is_passed`` **cùng transaction** (ACID).
* Duyệt từng ô độc lập: đơn lô có thể duyệt 15/20 ô, từ chối 5 ô.
* Đơn lẻ (1 ô) → ``decisions[]`` tùy chọn (mặc định duyệt toàn bộ).
  Đơn lô (nhiều ô) → ``decisions[]`` **bắt buộc**, thiếu → 422 DECISIONS_REQUIRED.
* Ô không có trong ``decisions[]`` → giữ nguyên PENDING (duyệt tiếp sau).
* Mail KHÔNG gửi trong transaction — enqueue ``email_outbox`` cùng transaction.
"""
from datetime import datetime

from studentapp.exceptions import (
    BusinessRuleError,
    DecisionsRequiredError,
    InvalidScoreRangeError,
    NotFoundError,
    ValidationError,
)
from studentapp.extensions import db
from studentapp.models.score import ALL_SCORE_COLUMNS, MAX_SCORE, MIN_SCORE
from studentapp.models.score_change_detail import (
    ChangeDetailStatusEnum,
    ScoreChangeDetail,
)
from studentapp.models.score_change_request import (
    ChangeRequestStatusEnum,
    ScoreChangeRequest,
)


def _get_or_404(request_id):
    try:
        rid = int(request_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy đơn phúc khảo.")
    row = db.session.get(ScoreChangeRequest, rid)
    if row is None:
        raise NotFoundError("Không tìm thấy đơn phúc khảo.")
    return row


def _passing_score() -> float:
    from studentapp.repositories import system_rule_repository

    return system_rule_repository.get_float("PASSING_SCORE", 5.0)


def _write_audit(user_id, action, details):
    from studentapp.models.audit_log import AuditLog

    try:
        uid = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        uid = None
    db.session.add(AuditLog(user_id=uid, action=action, details=details))


def _enqueue_mail(to_email, subject, body, related_id):
    from studentapp.models.email_outbox import EmailOutbox

    db.session.add(EmailOutbox(
        to_email=to_email, subject=subject, body=body,
        related_type="score_change_request", related_id=int(related_id),
    ))


def _enrich(request):
    from studentapp.repositories import user_repository

    item = {
        "request_id": request.id,
        "assignment_id": request.assignment_id,
        "teacher_id": request.teacher_id,
        "reason": request.reason,
        "status": request.status,
        "is_batch": bool(request.is_batch),
        "total_changes": request.total_changes,
        "attachment_path": request.attachment_path,
        "attachment_type": request.attachment_type,
        "attachment_name": request.attachment_name,
        "approved_by": request.approved_by,
        "approval_note": getattr(request, "approval_note", None),
        "created_at": request.created_at.isoformat() if request.created_at else None,
        "resolved_at": request.resolved_at.isoformat() if request.resolved_at else None,
    }
    a = getattr(request, "assignment", None)
    # lazy load assignment qua query để tránh lỗi khi relationship chưa khai báo
    if a is None:
        from studentapp.repositories import teaching_assignment_repository

        a = teaching_assignment_repository.get_by_id(request.assignment_id)
    if a is not None:
        item["class_name"] = a.class_room.class_name if a.class_room else None
        item["subject_name"] = a.subject.subject_name if a.subject else None
        item["semester_name"] = a.semester.semester_name if a.semester else None
    teacher = user_repository.get_by_id(request.teacher_id)
    item["teacher"] = (
        {"id": teacher.id, "full_name": teacher.full_name,
         "email": teacher.email} if teacher else None
    )
    item["details"] = [d.to_dict() for d in request.details]
    counts = {"total": len(request.details), "pending": 0,
              "approved": 0, "rejected": 0}
    for d in request.details:
        if d.status == ChangeDetailStatusEnum.PENDING:
            counts["pending"] += 1
        elif d.status == ChangeDetailStatusEnum.APPROVED:
            counts["approved"] += 1
        elif d.status == ChangeDetailStatusEnum.REJECTED:
            counts["rejected"] += 1
    item["summary"] = counts
    return item


def list_requests(status=None, page=1, limit=20):
    q = ScoreChangeRequest.query
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
        q.order_by(ScoreChangeRequest.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total, "page": page, "limit": limit,
        "data": [_enrich(r) for r in rows],
    }


def get_request(request_id):
    return _enrich(_get_or_404(request_id))


def get_diff(request_id, status=None):
    """Bảng so sánh điểm cũ ↔ điểm mới từng ô (SD19 duyệt đơn lô)."""
    from studentapp.repositories import student_repository

    request = _get_or_404(request_id)
    details = list(request.details)
    if status not in (None, ""):
        want = str(status).strip().upper()
        details = [d for d in details if d.status == want]
    changes = []
    for d in details:
        student = student_repository.get_by_id(d.student_id)
        changes.append({
            "detail_id": d.id,
            "student_id": d.student_id,
            "student_name": student.full_name if student else None,
            "student_code": student.student_code if student else None,
            "score_column": d.score_column,
            "old_value": float(d.old_value),
            "new_value": float(d.new_value),
            "status": d.status,
            "note": d.note,
        })
    return {
        "request_id": request.id,
        "assignment_id": request.assignment_id,
        "is_batch": bool(request.is_batch),
        "status": request.status,
        "summary": _enrich(request)["summary"],
        "changes": changes,
    }


def _apply_approved_cell(detail, reviewer_id, now):
    """Áp 1 ô được duyệt vào điểm chính thức + tính lại ĐTB (cùng transaction)."""
    from studentapp.models.score import Score
    from studentapp.services import score_calculator

    if detail.score_column not in ALL_SCORE_COLUMNS:
        raise BusinessRuleError(
            f"Cột điểm {detail.score_column!r} không còn hợp lệ.",
            error="INVALID_COLUMN_NAME",
        )
    score = db.session.get(Score, int(detail.score_id))
    if score is None:
        raise NotFoundError(
            f"Không tìm thấy dòng điểm (score_id={detail.score_id})."
        )
    new_value = float(detail.new_value)
    if new_value < MIN_SCORE or new_value > MAX_SCORE:
        raise InvalidScoreRangeError(
            f"Điểm {new_value} không hợp lệ — phải nằm trong [{MIN_SCORE}, {MAX_SCORE}]!"
        )
    setattr(score, detail.score_column, new_value)
    average, passed = score_calculator.calculate(score.score_map(), _passing_score())
    score.average_score = average
    score.is_passed = passed
    # GIỮ NGUYÊN is_draft = FALSE — tuyệt đối không hạ về bản nháp.
    score.is_draft = False
    db.session.add(score)

    detail.status = ChangeDetailStatusEnum.APPROVED
    detail.approved_by = reviewer_id
    detail.resolved_at = now
    db.session.add(detail)


def _resolve_parent_status(request, now):
    statuses = {d.status for d in request.details}
    if statuses == {ChangeDetailStatusEnum.APPROVED}:
        request.status = ChangeRequestStatusEnum.APPROVED
        request.resolved_at = now
    elif statuses == {ChangeDetailStatusEnum.REJECTED}:
        request.status = ChangeRequestStatusEnum.REJECTED
        request.resolved_at = now
    elif ChangeDetailStatusEnum.PENDING in statuses:
        # Còn ô chưa xử lý → đơn vẫn PENDING, Giáo vụ duyệt tiếp sau.
        request.status = ChangeRequestStatusEnum.PENDING
        request.resolved_at = None
    else:
        request.status = ChangeRequestStatusEnum.PARTIALLY_APPROVED
        request.resolved_at = now


def _parse_decisions(request, payload):
    decisions = payload.get("decisions")
    if decisions is None:
        if bool(request.is_batch) and len(request.details) > 1:
            raise DecisionsRequiredError()
        # Đơn lẻ → mặc định duyệt toàn bộ ô PENDING.
        return [
            {"detail_id": d.id, "action": "APPROVE"}
            for d in request.details
            if d.status == ChangeDetailStatusEnum.PENDING
        ]
    if not isinstance(decisions, list) or not decisions:
        raise DecisionsRequiredError(
            "Danh sách decisions không hợp lệ hoặc rỗng."
        )
    by_id = {}
    for dec in decisions:
        try:
            did = int(dec.get("detail_id"))
        except (TypeError, ValueError):
            raise ValidationError("Mỗi decision phải có detail_id hợp lệ.")
        action = str(dec.get("action") or "").strip().upper()
        if action not in ("APPROVE", "REJECT"):
            raise ValidationError(
                f"action của ô {did} phải là APPROVE hoặc REJECT."
            )
        if did in by_id:
            raise ValidationError(
                f"Ô detail_id={did} bị trùng trong decisions.",
                error="DUPLICATE_DECISION",
            )
        by_id[did] = {"action": action,
                      "note": (dec.get("note") or "").strip() or None}
    known = {d.id for d in request.details}
    for did in by_id:
        if did not in known:
            raise ValidationError(
                f"Ô detail_id={did} không thuộc đơn phúc khảo này."
            )
    return [{"detail_id": did, **v} for did, v in by_id.items()]


def approve_request(request_id, payload, reviewer_id=None):
    """Phê duyệt đơn phúc khảo — duyệt từng ô, 1 transaction ACID (SD19)."""
    from studentapp.repositories import user_repository

    request = _get_or_404(request_id)
    if request.status in (ChangeRequestStatusEnum.APPROVED,
                          ChangeRequestStatusEnum.REJECTED,
                          ChangeRequestStatusEnum.PARTIALLY_APPROVED):
        raise BusinessRuleError(
            f"Đơn đã được xử lý (trạng thái {request.status}), "
            "không thể duyệt lại.",
            error="INVALID_REQUEST_STATUS",
        )
    decisions = _parse_decisions(request, payload)
    approval_note = (payload.get("approval_note") or "").strip() or None
    now = datetime.utcnow()

    detail_map = {d.id: d for d in request.details}
    approved_count = 0
    rejected_count = 0
    for dec in decisions:
        detail = detail_map[dec["detail_id"]]
        if detail.status != ChangeDetailStatusEnum.PENDING:
            raise BusinessRuleError(
                f"Ô detail_id={detail.id} đã được xử lý "
                f"(trạng thái {detail.status}), không thể xử lý lại.",
                error="INVALID_DETAIL_STATUS",
            )
        if dec["action"] == "APPROVE":
            _apply_approved_cell(detail, reviewer_id, now)
            approved_count += 1
        else:
            detail.status = ChangeDetailStatusEnum.REJECTED
            detail.approved_by = reviewer_id
            detail.resolved_at = now
            if dec.get("note"):
                detail.note = dec["note"]
            db.session.add(detail)
            rejected_count += 1

    request.approved_by = reviewer_id
    request.approval_note = approval_note
    db.session.add(request)
    db.session.flush()
    _resolve_parent_status(request, now)
    db.session.add(request)
    _write_audit(reviewer_id, "APPROVE_SCORE_CHANGE", {
        "request_id": request.id, "assignment_id": request.assignment_id,
        "approved_count": approved_count, "rejected_count": rejected_count,
        "status": request.status,
    })
    teacher = user_repository.get_by_id(request.teacher_id)
    if teacher is not None and teacher.email:
        _enqueue_mail(
            teacher.email,
            "Đơn phúc khảo đã được Giáo vụ xử lý",
            f"Đơn #{request.id}: duyệt {approved_count} ô, "
            f"từ chối {rejected_count} ô. Trạng thái đơn: {request.status}."
            f"{(' Ghi chú: ' + approval_note) if approval_note else ''}",
            request.id,
        )
    db.session.commit()
    out = _enrich(request)
    out["approved_count"] = approved_count
    out["rejected_count"] = rejected_count
    return out


def reject_request(request_id, payload, reviewer_id=None):
    """Từ chối toàn bộ đơn (mọi ô PENDING → REJECTED) — không đụng điểm (SD19)."""
    from studentapp.repositories import user_repository

    request = _get_or_404(request_id)
    if request.status in (ChangeRequestStatusEnum.APPROVED,
                          ChangeRequestStatusEnum.REJECTED,
                          ChangeRequestStatusEnum.PARTIALLY_APPROVED):
        raise BusinessRuleError(
            f"Đơn đã được xử lý (trạng thái {request.status}), "
            "không thể từ chối lại.",
            error="INVALID_REQUEST_STATUS",
        )
    rejection_note = (payload.get("rejection_note") or "").strip()
    if not rejection_note:
        raise ValidationError("Vui lòng nêu rõ lý do từ chối đơn phúc khảo.")
    now = datetime.utcnow()
    rejected_count = 0
    for detail in request.details:
        if detail.status != ChangeDetailStatusEnum.PENDING:
            continue
        detail.status = ChangeDetailStatusEnum.REJECTED
        detail.approved_by = reviewer_id
        detail.resolved_at = now
        detail.note = rejection_note
        db.session.add(detail)
        rejected_count += 1
    request.status = ChangeRequestStatusEnum.REJECTED
    request.approved_by = reviewer_id
    request.approval_note = rejection_note
    request.resolved_at = now
    db.session.add(request)
    _write_audit(reviewer_id, "REJECT_SCORE_CHANGE", {
        "request_id": request.id, "assignment_id": request.assignment_id,
        "rejected_count": rejected_count, "rejection_note": rejection_note,
    })
    teacher = user_repository.get_by_id(request.teacher_id)
    if teacher is not None and teacher.email:
        _enqueue_mail(
            teacher.email,
            "Đơn phúc khảo bị từ chối",
            f"Đơn #{request.id} bị từ chối toàn bộ: {rejection_note}. "
            "Điểm chính thức được giữ nguyên.",
            request.id,
        )
    db.session.commit()
    out = _enrich(request)
    out["approved_count"] = 0
    out["rejected_count"] = rejected_count
    return out
