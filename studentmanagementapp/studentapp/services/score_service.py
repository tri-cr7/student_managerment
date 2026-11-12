"""SERVICE score — nghiệp vụ điểm số cho Giáo viên (SD09/SD11/SD14/SD23/SD25).

Nguyên tắc xuyên suốt:
* **Bảng điểm tạm** (``scores.is_draft = TRUE``) là nơi GV nhập/sửa.
* **Bảng điểm đã CHỐT** (``teaching_assignments.is_locked = TRUE``) → GV không
  sửa trực tiếp được, phải gửi đơn phúc khảo (SD25).
* **Đang có đơn gửi duyệt PENDING** → GV không sửa được, phải hủy đơn trước.
* **Partial update**: ô gửi lên với ``null`` → giữ nguyên giá trị trong DB.
"""
from datetime import datetime

from studentapp.exceptions import (
    InvalidColumnNameError,
    InvalidScoreRangeError,
    NotFoundError,
    ValidationError,
)
from studentapp.extensions import db
from studentapp.models.score import ALL_SCORE_COLUMNS
from studentapp.models.score_submission import SubmissionStatusEnum
from studentapp.repositories import (
    class_enrollment_repository,
    score_repository,
    teaching_assignment_repository,
)
from studentapp.services import score_calculator, teacher_service


def _passing_score() -> float:
    from studentapp.repositories import system_rule_repository

    return system_rule_repository.get_float("PASSING_SCORE", 5.0)


#: Nhập "v" (vắng) được quy về 0 điểm — vẫn tính vào ĐTB.
ABSENT_ALIASES = frozenset({"v", "vang", "vắng", "absent"})


def _parse_score(value):
    """Chuyển giá trị ô điểm về float; trả về None nếu chưa nhập (null).

    Quy ước vắng: nhập ``"v"`` (hoặc ``vang``/``vắng``) → hiểu là vắng,
    lưu thành ``0.0`` và **vẫn tính vào ĐTB**.
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.lower() in ABSENT_ALIASES:
            return 0.0
        value = text
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Giá trị điểm không hợp lệ: {value!r} "
            "(nhập số 0–10, hoặc 'v' nếu học sinh vắng)."
        )


def _validate_score_value(value: float):
    """Kiểm tra điểm nằm trong khoảng [0.0, 10.0] (rule A1)."""
    from studentapp.models.score import MAX_SCORE, MIN_SCORE

    if value < MIN_SCORE or value > MAX_SCORE:
        raise InvalidScoreRangeError(
            f"Điểm {value} không hợp lệ — điểm phải nằm trong khoảng "
            f"[{MIN_SCORE}, {MAX_SCORE}]!"
        )


def _active_column_config():
    """Số cột điểm ĐANG DÙNG theo system_rules (rule A2/A3/A4).

    DB giữ nguyên 9 cột tối đa; UI + kiểm tra "đủ điểm" chỉ tính các cột
    đang dùng: N_15m = MAX_COL_15M, N_45m = MAX_COL_45M, N_final = NUM_COL_FINAL.
    """
    from studentapp.models.score import (
        SCORE_COLUMNS_15M,
        SCORE_COLUMNS_45M,
        SCORE_COLUMN_FINAL,
        SCORE_GROUPS,
    )
    from studentapp.repositories import system_rule_repository

    n15 = system_rule_repository.get_int("MAX_COL_15M", 5)
    n45 = system_rule_repository.get_int("MAX_COL_45M", 3)
    nfin = system_rule_repository.get_int("NUM_COL_FINAL", 1)

    n15 = max(1, min(int(n15), len(SCORE_COLUMNS_15M)))
    n45 = max(1, min(int(n45), len(SCORE_COLUMNS_45M)))
    nfin = 1 if int(nfin) >= 1 else 0
    active_15m = list(SCORE_COLUMNS_15M[:n15])
    active_45m = list(SCORE_COLUMNS_45M[:n45])
    active_final = [SCORE_COLUMN_FINAL] if nfin else []
    return {
        "groups": [
            {"key": g["key"], "label": g["label"],
             "columns": (active_15m if g["key"] == "15m"
                         else active_45m if g["key"] == "45m"
                         else active_final)}
            for g in SCORE_GROUPS
        ],
        "active_columns": active_15m + active_45m + active_final,
        "counts": {"15m": n15, "45m": n45, "final": nfin},
    }


def get_score_column_config():
    """Cấu hình cột điểm cho UI (nhóm gọn + cột đang dùng)."""
    return _active_column_config()


# --------------------------------------------------------------------------- #
# SD09 — Danh sách lớp phụ trách
# --------------------------------------------------------------------------- #


def list_my_assignments(teacher_id):
    """Danh sách lớp môn học GV phụ trách, kèm thông tin lớp/môn/kỳ."""
    assignments = teacher_service.list_my_assignments(teacher_id)
    result = []
    for a in assignments:
        item = a.to_dict()
        item["class_name"] = a.class_room.class_name if a.class_room else None
        item["subject_name"] = a.subject.subject_name if a.subject else None
        item["semester_name"] = a.semester.semester_name if a.semester else None
        item["academic_year_name"] = (
            a.semester.academic_year.year_name
            if a.semester and a.semester.academic_year
            else None
        )
        item["has_pending_submission"] = (
            teaching_assignment_repository.get_pending_submission(a.id) is not None
        )
        result.append(item)
    return result


# --------------------------------------------------------------------------- #
# SD11 — Nhập điểm (lưu bảng điểm tạm)
# --------------------------------------------------------------------------- #


def _validate_batch_shape(payload):
    """Kiểm tra cấu trúc request: assignment_id + scores[] (rule A5 - không trùng HS)."""
    assignment_id = payload.get("assignment_id")
    if not assignment_id:
        raise ValidationError("Thiếu assignment_id trong request.")

    scores = payload.get("scores")
    if not isinstance(scores, list) or not scores:
        raise ValidationError("Danh sách điểm (scores) không hợp lệ hoặc rỗng.")

    seen = set()
    for row in scores:
        sid = row.get("student_id")
        if sid is None:
            raise ValidationError("Mỗi dòng điểm phải có student_id.")
        sid = int(sid)
        if sid in seen:
            from studentapp.exceptions import ValidationError as VE

            raise VE(
                f"Học sinh id={sid} bị trùng trong cùng một request.",
                error="DUPLICATE_STUDENT_IN_BATCH",
            )
        seen.add(sid)

    return int(assignment_id), scores


def _reject_inactive_columns(row, active_columns):
    """Rule A2/A3/A4 — chặn ghi vào cột vượt quá số cột quy định."""
    from studentapp.exceptions import InvalidColumnCountError

    active = set(active_columns)
    for col in row:
        if col == "student_id":
            continue
        if col in ALL_SCORE_COLUMNS and col not in active:
            raise InvalidColumnCountError(
                f"Cột {col} vượt quá số cột điểm cho phép "
                f"(15': {len([c for c in active_columns if '15m' in c])}, "
                f"1 tiết: {len([c for c in active_columns if '45m' in c])}). "
                "Vui lòng liên hệ Giáo vụ nếu muốn mở thêm cột!"
            )


def save_batch_scores(payload, teacher_id):
    """SD11 — Lưu điểm lớp vào bảng điểm tạm (partial update).

    * Ô ``null`` → **giữ nguyên** giá trị đang có trong DB (không xoá điểm đã chấm).
    * Ô có giá trị → kiểm tra [0, 10] rồi ghi.
    * Tính lại ĐTB & trạng thái Đạt cho từng học sinh.
    """
    assignment_id, rows = _validate_batch_shape(payload)

    # Rule A7/A11 — GV phải phụ trách lớp môn học
    assignment = teacher_service.ensure_teacher_owns_assignment(assignment_id, teacher_id)
    # Rule A8 — bảng điểm phải đang MỞ
    teacher_service.ensure_assignment_open(assignment)
    # Rule A10 — không có đơn gửi duyệt đang PENDING
    teacher_service.ensure_no_pending_submission(assignment_id)

    # Rule A6 — học sinh phải thuộc lớp
    class_student_ids = set(
        class_enrollment_repository.list_student_ids_by_class(assignment.class_id)
    )
    for row in rows:
        sid = int(row["student_id"])
        if sid not in class_student_ids:
            raise ValidationError(
                f"Học sinh id={sid} không thuộc lớp đang được giao điểm.",
                error="STUDENT_NOT_IN_ASSIGNMENT",
            )

    passing = _passing_score()
    cfg = _active_column_config()
    active_columns = cfg["active_columns"]
    updated = []

    for row in rows:
        # Rule A2/A3/A4 — chặn ghi vào cột vượt quá số cột quy định
        _reject_inactive_columns(row, active_columns)
        sid = int(row["student_id"])
        score = score_repository.get_by_assignment_and_student(assignment_id, sid)
        if score is None:
            score = _create_score_row(assignment_id, sid)

        score_map = score.score_map()
        changed = False

        for col in active_columns:
            if col not in row:
                continue
            value = _parse_score(row[col])
            if value is None:
                # Partial update — giữ nguyên giá trị cũ (chống mất dữ liệu)
                continue
            _validate_score_value(value)
            score_map[col] = value
            setattr(score, col, value)
            changed = True

        average, passed = score_calculator.calculate(score_map, passing)
        score.average_score = average
        score.is_passed = passed
        score.is_draft = True
        score.updated_by = teacher_id

        db.session.add(score)
        updated.append(
            {
                "student_id": sid,
                "average_score": float(average) if average is not None else None,
                "is_passed": passed,
                "changed": changed,
            }
        )

    db.session.commit()

    return {
        "message": "Lưu bảng điểm tạm và tính toán điểm trung bình môn thành công",
        "data": {
            "assignment_id": assignment_id,
            "updated_count": len(updated),
            "is_draft": True,
            "message_hint": (
                "Điểm đã lưu vào bảng điểm TẠM. "
                "Bấm 'Gửi duyệt' để Giáo vụ duyệt & chốt thành điểm chính thức."
            ),
            "scores": updated,
        },
    }


def _create_score_row(assignment_id, student_id):
    """Tạo dòng điểm mới (chưa có ô nào có giá trị)."""
    from studentapp.models.score import Score

    score = Score(assignment_id=assignment_id, student_id=student_id, is_draft=True)
    db.session.add(score)
    db.session.flush()
    return score


# --------------------------------------------------------------------------- #
# SD14 — Sửa 1 ô điểm
# --------------------------------------------------------------------------- #


def update_score_cell(score_id, payload, teacher_id):
    """SD14 — Sửa một ô điểm của một học sinh (bảng điểm đang MỞ).

    Hỗ trợ ``clear: true`` để **xoá có chủ đích** một ô đã chấm (set NULL)
    — thao tác này ghi audit log, khác với việc gửi ``null`` trong batch
    (partial update — giữ nguyên).
    """
    score = score_repository.get_by_id(score_id)
    if score is None:
        raise NotFoundError("Không tìm thấy dòng điểm cần sửa.")

    assignment = teacher_service.ensure_teacher_owns_assignment(
        score.assignment_id, teacher_id
    )
    teacher_service.ensure_assignment_open(assignment)
    teacher_service.ensure_no_pending_submission(score.assignment_id)

    column = (payload.get("score_column") or "").strip()
    if column not in ALL_SCORE_COLUMNS:
        raise InvalidColumnNameError(
            f"Cột điểm không hợp lệ: {column!r}. "
            f"Chỉ chấp nhận: {', '.join(ALL_SCORE_COLUMNS)}."
        )
    # Rule A2/A3/A4 — chặn sửa cột vượt quá số cột quy định
    if column not in _active_column_config()["active_columns"]:
        from studentapp.exceptions import InvalidColumnCountError

        raise InvalidColumnCountError(
            f"Cột {column} hiện không được sử dụng theo quy định số cột điểm. "
            "Vui lòng liên hệ Giáo vụ nếu muốn mở thêm cột!"
        )

    clear = bool(payload.get("clear"))
    old_value = getattr(score, column)

    if clear:
        new_value = None
        setattr(score, column, None)
    else:
        new_value = _parse_score(payload.get("new_value"))
        if new_value is None:
            raise ValidationError(
                "Thiếu new_value. Muốn xoá ô điểm hãy dùng cờ clear = true."
            )
        _validate_score_value(new_value)
        setattr(score, column, new_value)

    score_map = score.score_map()
    average, passed = score_calculator.calculate(score_map, _passing_score())
    score.average_score = average
    score.is_passed = passed
    score.is_draft = True
    score.updated_by = teacher_id

    db.session.add(score)
    db.session.commit()

    _write_audit(teacher_id, "UPDATE_SCORE", {
        "score_id": score.id,
        "assignment_id": score.assignment_id,
        "student_id": score.student_id,
        "score_column": column,
        "old_value": float(old_value) if old_value is not None else None,
        "new_value": new_value,
        "cleared": clear,
    })

    return {
        "score_id": score.id,
        "score_column": column,
        "old_value": float(old_value) if old_value is not None else None,
        "new_value": new_value,
        "average_score": float(average) if average is not None else None,
        "is_passed": passed,
        "is_draft": True,
    }


def _write_audit(user_id, action, details):
    """Ghi vết hoạt động vào audit_logs."""
    from studentapp.models.audit_log import AuditLog

    db.session.add(AuditLog(user_id=user_id, action=action, details=details))


# --------------------------------------------------------------------------- #
# Đọc điểm
# --------------------------------------------------------------------------- #


def get_assignment_scores(assignment_id, teacher_id):
    """Xem bảng điểm của lớp môn học (cả nháp & chính thức, kèm cờ is_draft)."""
    assignment = teacher_service.ensure_teacher_owns_assignment(assignment_id, teacher_id)

    rows = score_repository.list_by_assignment(assignment_id, draft_only=None)
    student_ids = [r.student_id for r in rows]
    from studentapp.repositories import student_repository

    students = {s.id: s for s in student_repository.list_by_ids(student_ids)}

    score_list = []
    for row in rows:
        student = students.get(row.student_id)
        item = {
            "student_id": row.student_id,
            "student_code": student.student_code if student else None,
            "full_name": student.full_name if student else None,
            "average_score": float(row.average_score) if row.average_score is not None else None,
            "is_passed": None if row.is_passed is None else bool(row.is_passed),
            "is_draft": bool(row.is_draft),
            **row.score_map(),
        }
        score_list.append(item)

    pending = teaching_assignment_repository.get_pending_submission(assignment_id)
    return {
        "assignment_id": assignment.id,
        "class_name": assignment.class_room.class_name if assignment.class_room else None,
        "subject_name": assignment.subject.subject_name if assignment.subject else None,
        "academic_year": (
            assignment.semester.academic_year.year_name
            if assignment.semester and assignment.semester.academic_year
            else None
        ),
        "is_locked": bool(assignment.is_locked),
        "is_draft": True,
        "pending_submission_id": pending.id if pending else None,
        "column_config": _active_column_config(),
        "score_list": score_list,
    }


def get_student_scores(student_id, teacher_id, include_draft=False):
    """Xem toàn bộ điểm của một học sinh.

    Mặc định chỉ trả điểm **chính thức** đã duyệt (chống lộ điểm tạm).
    """
    from studentapp.repositories import student_repository

    student = student_repository.get_by_id(student_id)
    if student is None:
        raise NotFoundError("Không tìm thấy học sinh.")

    my_assignments = teacher_service.list_my_assignments(teacher_id)
    my_ids = [a.id for a in my_assignments]

    rows = score_repository.list_by_student(
        student_id,
        assignment_ids=my_ids or None,
        draft_only=None if include_draft else False,
    )

    return {
        "student_id": student.id,
        "student_code": student.student_code,
        "full_name": student.full_name,
        "scores": [r.to_dict() for r in rows],
    }


def search_my_students(teacher_id, keyword=None, class_id=None, limit=20):
    """Tìm kiếm học sinh trong các lớp GV phụ trách (theo tên / mã số HS).

    :param keyword: chuỗi tìm theo ``full_name`` hoặc ``student_code`` (LIKE).
    :param class_id: lọc thêm theo 1 lớp (phải là lớp GV đang dạy).
    """
    from studentapp.exceptions import PermissionDeniedError
    from studentapp.repositories import class_enrollment_repository, student_repository

    assignments = teacher_service.list_my_assignments(teacher_id)
    my_class_ids = sorted({int(a.class_id) for a in assignments})

    wanted_class = None
    if class_id not in (None, ""):
        try:
            wanted_class = int(class_id)
        except (TypeError, ValueError):
            raise ValidationError("class_id không hợp lệ.")
        if wanted_class not in my_class_ids:
            raise PermissionDeniedError(
                "Bạn không phụ trách lớp này nên không được tìm kiếm học sinh trong lớp!"
            )
        my_class_ids = [wanted_class]

    if not my_class_ids:
        return []

    allowed_ids = set()
    student_class_map = {}
    for cid in my_class_ids:
        for sid in class_enrollment_repository.list_student_ids_by_class(cid):
            allowed_ids.add(int(sid))
            student_class_map.setdefault(int(sid), []).append(cid)

    students = student_repository.search_students(
        keyword, student_ids=sorted(allowed_ids), limit=limit
    )

    class_names = {}
    for a in assignments:
        if a.class_room is not None:
            class_names[int(a.class_id)] = a.class_room.class_name

    result = []
    for s in students:
        item = s.to_dict()
        item["classes"] = [
            {"class_id": cid, "class_name": class_names.get(cid)}
            for cid in student_class_map.get(int(s.id), [])
        ]
        result.append(item)
    return result


# --------------------------------------------------------------------------- #
# SD23 — Gửi bảng điểm lên duyệt & hủy đơn
# --------------------------------------------------------------------------- #


def create_submission(payload, teacher_id):
    """SD23 — Gửi bảng điểm tạm lên Giáo vụ để duyệt & chốt."""
    from studentapp.exceptions import (
        DuplicatePendingSubmissionError,
        IncompleteScoresError,
        ValidationError as VE,
    )
    from studentapp.models.score_submission import ScoreSubmission

    assignment_id = payload.get("assignment_id")
    if not assignment_id:
        raise VE("Thiếu assignment_id trong request.")

    assignment = teacher_service.ensure_teacher_owns_assignment(assignment_id, teacher_id)
    teacher_service.ensure_assignment_open(assignment)

    # Rule B3 — không gửi trùng khi đã có đơn PENDING
    existing = teaching_assignment_repository.get_pending_submission(assignment_id)
    if existing is not None:
        raise DuplicatePendingSubmissionError(
            "Bảng điểm này đã được gửi duyệt và đang chờ Giáo vụ xử lý. "
            "Vui lòng hủy đơn cũ trước khi gửi lại.",
            pending_submission_id=existing.id,
        )

    rows = score_repository.list_by_assignment(assignment_id, draft_only=True)

    # Rule B2 — phải có ít nhất 1 dòng điểm
    if not rows:
        from studentapp.exceptions import ValidationError as VE2

        raise VE2(
            "Chưa có điểm nào để gửi duyệt. Vui lòng nhập điểm trước!",
            error="NO_SCORES_TO_SUBMIT",
        )

    # Rule B1 — không ô nào được để trống (chỉ tính cột ĐANG DÙNG theo quy định)
    cfg = _active_column_config()
    active_columns = cfg["active_columns"]
    incomplete = []
    total_filled = 0
    for row in rows:
        missing = score_repository.count_missing_cells(row, active_columns)
        total_filled += score_repository.count_filled_cells(row, active_columns)
        if missing:
            from studentapp.repositories import student_repository

            student = student_repository.get_by_id(row.student_id)
            incomplete.append({
                "student_id": row.student_id,
                "student_name": student.full_name if student else None,
                "missing_columns": missing,
            })

    if incomplete:
        raise IncompleteScoresError(
            f"Còn {len(incomplete)} học sinh có ô điểm chưa được nhập. "
            "Vui lòng nhập đủ điểm (hoặc nhập 0 nếu học sinh vắng) trước khi gửi duyệt!"
        )

    submission = ScoreSubmission(
        assignment_id=assignment_id,
        teacher_id=teacher_id,
        status=SubmissionStatusEnum.PENDING,
        total_students=len(rows),
        total_scores=total_filled,
        note=(payload.get("note") or "").strip() or None,
    )
    db.session.add(submission)
    db.session.flush()

    # Đóng dấu submitted_at trên các dòng điểm
    now = datetime.utcnow()
    for row in rows:
        row.submitted_at = now
        db.session.add(row)

    db.session.commit()

    return submission.to_dict()


def cancel_submission(submission_id, payload, teacher_id):
    """SD23 — Hủy đơn gửi duyệt để sửa lại bảng điểm tạm.

    Hiệu lực: ``status = CANCELLED``, ghi ``cancelled_at`` + ``cancel_note``;
    **giữ nguyên** ``scores.is_draft = TRUE`` và ``teaching_assignments.is_locked = FALSE``.
    """
    from studentapp.exceptions import InvalidSubmissionStatusError
    from studentapp.models.score_submission import ScoreSubmission

    submission = db.session.get(ScoreSubmission, submission_id)
    if submission is None:
        raise NotFoundError("Không tìm thấy đơn gửi duyệt.")

    if int(submission.teacher_id) != int(teacher_id):
        from studentapp.exceptions import PermissionDeniedError

        raise PermissionDeniedError("Bạn không có quyền hủy đơn gửi duyệt của người khác.")

    if not submission.is_pending():
        raise InvalidSubmissionStatusError(
            f"Chỉ có thể hủy đơn đang ở trạng thái chờ duyệt! "
            f"Đơn hiện tại đang ở trạng thái {submission.status}.",
            current_status=submission.status,
        )

    submission.status = SubmissionStatusEnum.CANCELLED
    submission.cancelled_at = datetime.utcnow()
    submission.cancel_note = (payload.get("cancel_note") or "").strip() or None
    db.session.add(submission)
    db.session.commit()

    _write_audit(teacher_id, "CANCEL_SCORE_SUBMISSION", {
        "submission_id": submission.id,
        "assignment_id": submission.assignment_id,
    })

    return submission.to_dict()


def list_my_submissions(teacher_id):
    """Danh sách bảng điểm GV đã gửi duyệt."""
    from studentapp.models.score_submission import ScoreSubmission

    rows = (
        ScoreSubmission.query.filter_by(teacher_id=int(teacher_id))
        .order_by(ScoreSubmission.id.desc())
        .all()
    )
    return [r.to_dict() for r in rows]


# --------------------------------------------------------------------------- #
# SD25 — Gửi yêu cầu chỉnh điểm (đơn phúc khảo) khi bảng điểm đã CHỐT
# --------------------------------------------------------------------------- #


def _validate_change_payload(payload):
    """Kiểm tra cấu trúc đơn phúc khảo: assignment_id + reason + changes[]."""
    assignment_id = payload.get("assignment_id")
    if not assignment_id:
        raise ValidationError("Thiếu assignment_id trong request.")

    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise ValidationError("Vui lòng nêu rõ lý do yêu cầu chỉnh điểm.")
    if len(reason) > 1000:
        raise ValidationError("Lý do yêu cầu chỉnh điểm không được vượt quá 1000 ký tự.")

    changes = payload.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ValidationError(
            "Danh sách ô điểm cần chỉnh (changes) không hợp lệ hoặc rỗng."
        )

    seen = set()
    for change in changes:
        sid = change.get("student_id")
        col = (change.get("score_column") or "").strip()
        if sid is None:
            raise ValidationError("Mỗi thay đổi phải có student_id.")
        if col not in ALL_SCORE_COLUMNS:
            raise InvalidColumnNameError(
                f"Cột điểm không hợp lệ: {col!r}. "
                f"Chỉ chấp nhận: {', '.join(ALL_SCORE_COLUMNS)}."
            )
        key = (int(sid), col)
        if key in seen:
            raise ValidationError(
                f"Ô điểm bị trùng trong đơn: học sinh id={sid}, cột {col}.",
                error="DUPLICATE_CHANGE_IN_REQUEST",
            )
        seen.add(key)

    return int(assignment_id), reason, changes


def create_change_request(payload, teacher_id):
    """SD25 — Gửi đơn yêu cầu chỉnh điểm khi bảng điểm đã CHỐT.

    * Chỉ tạo được khi ``teaching_assignments.is_locked = TRUE``
      (bảng đang mở thì GV sửa trực tiếp, không cần đơn).
    * Mỗi ô đề nghị sửa ghi rõ **giá trị cũ** (``old_value``, lấy từ DB)
      và **giá trị mới** (``new_value``) — Giáo vụ duyệt/từ chối từng ô.
    * ``old_value`` luôn có giá trị vì bảng đã chốt ⇒ không còn ô NULL.
    """
    from studentapp.exceptions import ScoreValueConflictError, ScoreTableNotLockedError
    from studentapp.models.score_change_detail import ScoreChangeDetail
    from studentapp.models.score_change_request import (
        ChangeRequestStatusEnum,
        ScoreChangeRequest,
    )

    assignment_id, reason, changes = _validate_change_payload(payload)

    assignment = teacher_service.ensure_teacher_owns_assignment(assignment_id, teacher_id)

    # Bảng điểm đang MỞ → GV sửa trực tiếp, không cần gửi đơn.
    if not assignment.is_locked:
        raise ScoreTableNotLockedError(
            "Bảng điểm đang mở. Bạn hãy sửa điểm trực tiếp thay vì gửi đơn phúc khảo!"
        )

    request = ScoreChangeRequest(
        assignment_id=assignment_id,
        teacher_id=teacher_id,
        reason=reason,
        status=ChangeRequestStatusEnum.PENDING,
        is_batch=len(changes) > 1,
        total_changes=len(changes),
    )
    db.session.add(request)
    db.session.flush()

    for change in changes:
        sid = int(change["student_id"])
        col = change["score_column"].strip()

        score = score_repository.get_by_assignment_and_student(assignment_id, sid)
        if score is None:
            raise ValidationError(
                f"Không tìm thấy dòng điểm của học sinh id={sid} trong lớp này.",
                error="SCORE_ROW_NOT_FOUND",
            )

        old_value = getattr(score, col)
        if old_value is None:
            # Bảng đã chốt mà ô vẫn NULL ⇒ dữ liệu bất nhất, chặn lại.
            raise ScoreValueConflictError(
                f"Ô điểm {col} của học sinh id={sid} đang trống. "
                "Vui lòng liên hệ Giáo vụ để kiểm tra lại bảng điểm.",
                error="SCORE_CELL_EMPTY",
            )

        new_value = _parse_score(change.get("new_value"))
        if new_value is None:
            raise ValidationError(
                "Thiếu new_value cho ô điểm cần chỉnh. "
                "Nếu cần xoá ô điểm, vui lòng ghi rõ new_value = 0."
            )
        _validate_score_value(new_value)

        if float(old_value) == new_value:
            raise ValidationError(
                f"Giá trị mới của ô {col} (học sinh id={sid}) trùng với giá trị cũ.",
                error="SAME_SCORE_VALUE",
            )

        detail = ScoreChangeDetail(
            request_id=request.id,
            score_id=score.id,
            student_id=sid,
            score_column=col,
            old_value=old_value,
            new_value=new_value,
            status="PENDING",
            note=(change.get("note") or "").strip() or None,
        )
        db.session.add(detail)

    db.session.commit()

    _write_audit(teacher_id, "CREATE_SCORE_CHANGE_REQUEST", {
        "request_id": request.id,
        "assignment_id": assignment_id,
        "total_changes": len(changes),
    })

    return request.to_dict()


def list_my_change_requests(teacher_id):
    """Danh sách đơn phúc khảo GV đã gửi."""
    from studentapp.models.score_change_request import ScoreChangeRequest

    rows = (
        ScoreChangeRequest.query.filter_by(teacher_id=int(teacher_id))
        .order_by(ScoreChangeRequest.id.desc())
        .all()
    )
    return [r.to_dict() for r in rows]
