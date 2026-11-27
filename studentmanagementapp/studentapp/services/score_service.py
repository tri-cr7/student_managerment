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

ABSENT_ALIASES = frozenset({"v", "vang", "vắng", "absent"})

def _parse_score(value):

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

    from studentapp.models.score import MAX_SCORE, MIN_SCORE

    if value < MIN_SCORE or value > MAX_SCORE:
        raise InvalidScoreRangeError(
            f"Điểm {value} không hợp lệ — điểm phải nằm trong khoảng "
            f"[{MIN_SCORE}, {MAX_SCORE}]!"
        )

def _active_column_config():

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

    return _active_column_config()

def list_my_assignments(teacher_id):

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

def _validate_batch_shape(payload):

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
            from studentapp.exceptions import DuplicateStudentInBatchError

            raise DuplicateStudentInBatchError(
                f"Học sinh id={sid} bị trùng trong cùng một request.",
                student_id=sid,
            )
        seen.add(sid)

    return int(assignment_id), scores

def _reject_inactive_columns(row, active_columns):

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
        if col not in ALL_SCORE_COLUMNS:
            from studentapp.exceptions import InvalidColumnNameError

            raise InvalidColumnNameError(
                f"Cột điểm không hợp lệ: {col!r}. "
                f"Chỉ chấp nhận: {', '.join(ALL_SCORE_COLUMNS)}."
            )

def save_batch_scores(payload, teacher_id):

    assignment_id, rows = _validate_batch_shape(payload)

    assignment = teacher_service.ensure_teacher_owns_assignment(assignment_id, teacher_id)

    teacher_service.ensure_assignment_open(assignment)

    teacher_service.ensure_no_pending_submission(assignment_id)

    cfg = _active_column_config()
    active_columns = cfg["active_columns"]
    for row in rows:
        _reject_inactive_columns(row, active_columns)

    class_student_ids = set(
        class_enrollment_repository.list_enrolled_student_ids_by_class(
            assignment.class_id
        )
    )

    valid_rows = []
    skipped_student_ids = []
    for row in rows:
        sid = int(row["student_id"])
        if sid not in class_student_ids:

            skipped_student_ids.append(sid)
            continue
        valid_rows.append((sid, row))

    if not valid_rows:
        from studentapp.exceptions import StudentNotInAssignmentError

        raise StudentNotInAssignmentError(
            "Không có học sinh nào trong yêu cầu thuộc lớp đang được giao điểm. "
            "Vui lòng tải lại bảng điểm.",
            student_id=skipped_student_ids[0] if skipped_student_ids else None,
            assignment_id=assignment_id,
        )

    passing = _passing_score()
    updated = []

    for sid, row in valid_rows:
        score = score_repository.get_by_assignment_and_student(assignment_id, sid)
        score_map = (
            score.score_map()
            if score is not None
            else {col: None for col in ALL_SCORE_COLUMNS}
        )

        pending_values = {}
        for col in active_columns:
            if col not in row:
                continue
            value = _parse_score(row[col])
            if value is None:

                continue
            _validate_score_value(value)
            pending_values[col] = value

        if not pending_values:

            continue

        if score is None:
            score = _create_score_row(assignment_id, sid)

        for col, value in pending_values.items():
            score_map[col] = value
            setattr(score, col, value)

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
                "changed": True,
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

            "skipped_student_ids": skipped_student_ids,
            "skipped_count": len(skipped_student_ids),
        },
    }

def _create_score_row(assignment_id, student_id):

    from studentapp.models.score import Score

    score = Score(assignment_id=assignment_id, student_id=student_id, is_draft=True)
    db.session.add(score)
    db.session.flush()
    return score

def update_score_cell(score_id, payload, teacher_id):

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

    from studentapp.utils.audit import write_audit

    write_audit(user_id, action, details)

def get_assignment_scores(assignment_id, teacher_id, is_academic=False):

    if is_academic:
        assignment = teaching_assignment_repository.get_by_id(assignment_id)
        if assignment is None:
            raise NotFoundError("Không tìm thấy lớp môn học (phân công giảng dạy).")
    else:
        assignment = teacher_service.ensure_teacher_owns_assignment(
            assignment_id, teacher_id
        )

    rows = score_repository.list_by_assignment(assignment_id, draft_only=None)
    from studentapp.repositories import student_repository, class_enrollment_repository

    roster_ids = class_enrollment_repository.list_enrolled_student_ids_by_class(
        assignment.class_id
    )
    students = {s.id: s for s in student_repository.list_by_ids(roster_ids)}
    score_by_student = {int(r.student_id): r for r in rows}

    score_list = []
    for sid in roster_ids:
        row = score_by_student.get(sid)
        student = students.get(sid)
        score_map = (
            row.score_map() if row is not None else {col: None for col in ALL_SCORE_COLUMNS}
        )
        item = {
            "student_id": sid,
            "student_code": student.student_code if student else None,
            "full_name": student.full_name if student else None,
            "average_score": (
                float(row.average_score)
                if row is not None and row.average_score is not None
                else None
            ),
            "is_passed": (
                None if row is None or row.is_passed is None else bool(row.is_passed)
            ),
            "is_draft": bool(row.is_draft) if row is not None else True,
            **{
                col: (float(val) if val is not None else None)
                for col, val in score_map.items()
            },
        }
        score_list.append(item)

    pending = teaching_assignment_repository.get_pending_submission(assignment_id)
    return {
        "assignment_id": assignment.id,
        "class_id": int(assignment.class_id),
        "class_name": assignment.class_room.class_name if assignment.class_room else None,
        "subject_id": int(assignment.subject_id),
        "subject_name": assignment.subject.subject_name if assignment.subject else None,
        "semester_id": int(assignment.semester_id) if assignment.semester_id else None,
        "semester_name": assignment.semester.semester_name if assignment.semester else None,
        "academic_year_id": (
            int(assignment.semester.academic_year_id)
            if assignment.semester and assignment.semester.academic_year_id
            else None
        ),
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

def get_student_scores(student_id, teacher_id, include_draft=False, is_academic=False):

    from studentapp.exceptions import PermissionDeniedError
    from studentapp.repositories import student_repository

    student = student_repository.get_by_id(student_id)
    if student is None:
        raise NotFoundError("Không tìm thấy học sinh.")

    my_assignments = teacher_service.list_my_assignments(teacher_id)
    my_ids = [a.id for a in my_assignments]

    if not is_academic:

        if not my_assignments:
            raise PermissionDeniedError(
                "Bạn chưa được phân công lớp môn học nào nên không được xem "
                "điểm của học sinh."
            )

        my_class_ids = {int(a.class_id) for a in my_assignments}
        student_class_ids = {
            int(cid)
            for cid in class_enrollment_repository.list_all_class_ids_by_student(student_id)
            if int(cid) in my_class_ids
        }
        if not student_class_ids:
            raise PermissionDeniedError(
                "Học sinh này không thuộc lớp bạn phụ trách nên bạn không được "
                "xem điểm của học sinh!"
            )

    rows = score_repository.list_by_student(
        student_id,

        assignment_ids=my_ids if not is_academic else None,
        draft_only=None if include_draft else False,
    )

    return {
        "student_id": student.id,
        "student_code": student.student_code,
        "full_name": student.full_name,
        "scores": [r.to_dict() for r in rows],
    }

def _resolve_yearly_scope(class_id, subject_id, academic_year_id):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.class_room import Class
    from studentapp.models.subject import Subject

    try:
        cid = int(class_id)
    except (TypeError, ValueError):
        raise ValidationError("class_id không hợp lệ.")
    try:
        sid = int(subject_id)
    except (TypeError, ValueError):
        raise ValidationError("subject_id không hợp lệ.")
    try:
        yid = int(academic_year_id)
    except (TypeError, ValueError):
        raise ValidationError("academic_year_id không hợp lệ.")

    if db.session.get(Class, cid) is None:
        raise NotFoundError("Không tìm thấy lớp học.")
    if db.session.get(Subject, sid) is None:
        raise NotFoundError("Không tìm thấy môn học.")
    if db.session.get(AcademicYear, yid) is None:
        raise NotFoundError("Không tìm thấy năm học.")

    return cid, sid, yid

def _yearly_average_rows(class_id, subject_id, academic_year_id):

    from studentapp.models.semester import Semester
    from studentapp.repositories import student_repository

    semesters = (
        Semester.query.filter_by(academic_year_id=int(academic_year_id))
        .order_by(Semester.factor.asc(), Semester.id.asc())
        .all()
    )

    student_ids = class_enrollment_repository.list_student_ids_by_class(
        class_id, academic_year_id=int(academic_year_id)
    )
    students = {int(s.id): s for s in student_repository.list_by_ids(student_ids)}

    rows = score_repository.list_by_class_subject_year(
        class_id, subject_id, academic_year_id, draft_only=False
    )

    by_student = {}
    for row in rows:
        assignment = row.assignment
        if assignment is None or assignment.semester is None:
            continue
        sem_name = assignment.semester.semester_name
        factor = int(assignment.semester.factor or 1)
        avg = row.average_score
        by_student.setdefault(int(row.student_id), {})[sem_name] = {
            "factor": factor,
            "avg": float(avg) if avg is not None else None,
        }

    sem_names = [s.semester_name for s in semesters]
    first_sem = sem_names[0] if sem_names else None
    second_sem = sem_names[1] if len(sem_names) > 1 else None

    records = []
    for stt, sid in enumerate(student_ids, start=1):
        sid = int(sid)
        student = students.get(sid)
        per_sem = by_student.get(sid, {})

        avg_hk1 = (per_sem.get(first_sem) or {}).get("avg") if first_sem else None
        avg_hk2 = (per_sem.get(second_sem) or {}).get("avg") if second_sem else None

        weighted_sum = 0.0
        weight_total = 0.0
        for item in per_sem.values():
            avg = item["avg"]
            if avg is None:
                continue
            weighted_sum += avg * item["factor"]
            weight_total += item["factor"]
        avg_yearly = round(weighted_sum / weight_total, 2) if weight_total else None

        records.append({
            "stt": stt,
            "student_id": sid,
            "student_code": student.student_code if student else None,
            "full_name": student.full_name if student else None,
            "class_name": None,
            "avg_hk1": avg_hk1,
            "avg_hk2": avg_hk2,
            "avg_yearly": avg_yearly,
        })

    return records, semesters

def get_yearly_class_scores(class_id, subject_id, academic_year_id, teacher_id=None,
                            is_academic=False):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.class_room import Class
    from studentapp.models.subject import Subject

    cid, sid, yid = _resolve_yearly_scope(class_id, subject_id, academic_year_id)

    if not is_academic:
        teacher_service.ensure_teacher_owns_class_subject(teacher_id, cid, sid)

    cls = db.session.get(Class, cid)
    subject = db.session.get(Subject, sid)
    year = db.session.get(AcademicYear, yid)

    records, semesters = _yearly_average_rows(cid, sid, yid)
    for r in records:
        r["class_name"] = cls.class_name if cls else None

    return {
        "class_id": cid,
        "class_name": cls.class_name if cls else None,
        "subject_id": sid,
        "subject_name": subject.subject_name if subject else None,
        "academic_year_id": yid,
        "academic_year": year.year_name if year else None,
        "semesters": [
            {"id": s.id, "semester_name": s.semester_name, "factor": int(s.factor)}
            for s in semesters
        ],
        "records": records,
    }

def export_yearly_class_scores(assignment_id, fmt="excel", teacher_id=None,
                               is_academic=False):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.class_room import Class
    from studentapp.models.subject import Subject
    from studentapp.models.teaching_assignment import TeachingAssignment

    try:
        aid = int(assignment_id)
    except (TypeError, ValueError):
        raise ValidationError("assignment_id không hợp lệ.")

    assignment = TeachingAssignment.query.filter_by(id=aid).first()
    if assignment is None:
        raise NotFoundError("Không tìm thấy lớp môn học (phân công giảng dạy).")

    if not is_academic:
        teacher_service.ensure_teacher_owns_assignment(aid, teacher_id)

    semester = assignment.semester
    if semester is None or semester.academic_year is None:
        raise NotFoundError("Lớp môn học chưa gắn với năm học.")

    yid = int(semester.academic_year_id)
    cid = int(assignment.class_id)
    sid = int(assignment.subject_id)

    data = get_yearly_class_scores(
        cid, sid, yid, teacher_id=teacher_id, is_academic=is_academic
    )

    fmt = (fmt or "excel").strip().lower()
    if fmt not in ("excel", "pdf"):
        raise ValidationError("format không hợp lệ. Chỉ hỗ trợ 'excel' hoặc 'pdf'.")

    cls = db.session.get(Class, cid)
    subject = db.session.get(Subject, sid)
    year = db.session.get(AcademicYear, yid)

    safe = lambda s: "".join(
        ch if ch.isalnum() else "_" for ch in str(s or "")
    ).strip("_") or "X"
    base_name = (
        f"BangDiemTrungBinhLop_{safe(cls.class_name if cls else '')}"
        f"_{safe(subject.subject_name if subject else '')}"
        f"_{safe(year.year_name if year else '')}"
    )

    if fmt == "excel":
        payload = _build_yearly_excel(data)
        return payload, f"{base_name}.xlsx", (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ), data

    payload = _build_yearly_pdf(data)
    return payload, f"{base_name}.pdf", "application/pdf", data

def _build_yearly_excel(data):

    import io

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Bang diem trung binh lop"

    ws.append(["BẢNG ĐIỂM TRUNG BÌNH LỚP"])
    ws.append([
        f"Năm học: {data['academic_year']} — Lớp: {data['class_name']} — "
        f"Môn: {data['subject_name']}",
    ])
    ws.append(["Năm học", "STT", "Họ tên", "Lớp", "Điểm TB HK1", "Điểm TB HK2"])
    for r in data["records"]:
        ws.append([
            data["academic_year"],
            r["stt"],
            r["full_name"],
            r["class_name"],
            r["avg_hk1"],
            r["avg_hk2"],
        ])

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
    ws["A1"].font = Font(bold=True, size=13)
    ws["A3"].font = Font(bold=True)
    for col, width in zip("ABCDEF", (12, 6, 28, 12, 14, 14)):
        ws.column_dimensions[col].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def _build_yearly_pdf(data):

    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    y = h - 18 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, y, "BANG DIEM TRUNG BINH LOP")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(
        15 * mm, y,
        f"Nam hoc: {data['academic_year']} - Lop: {data['class_name']} - "
        f"Mon: {data['subject_name']}",
    )
    y -= 10 * mm

    headers = ["Nam hoc", "STT", "Ho ten", "Lop", "Diem TB HK1", "Diem TB HK2"]
    xs = [15 * mm, 50 * mm, 62 * mm, 125 * mm, 145 * mm, 175 * mm]
    c.setFont("Helvetica-Bold", 9)
    for x, head in zip(xs, headers):
        c.drawString(x, y, head)
    y -= 2 * mm
    c.line(15 * mm, y, w - 15 * mm, y)
    y -= 6 * mm

    c.setFont("Helvetica", 9)
    for r in data["records"]:
        if y < 18 * mm:
            c.showPage()
            y = h - 18 * mm
            c.setFont("Helvetica", 9)
        c.drawString(xs[0], y, str(data["academic_year"]))
        c.drawString(xs[1], y, str(r["stt"]))
        c.drawString(xs[2], y, str(r["full_name"] or ""))
        c.drawString(xs[3], y, str(r["class_name"] or ""))
        c.drawString(xs[4], y, _fmt_avg(r["avg_hk1"]))
        c.drawString(xs[5], y, _fmt_avg(r["avg_hk2"]))
        y -= 6 * mm

    c.showPage()
    c.save()
    return buf.getvalue()

def _fmt_avg(value):

    if value is None:
        return ""
    return f"{float(value):.2f}"

def search_my_students(teacher_id, keyword=None, class_id=None, limit=20):

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

def create_submission(payload, teacher_id):

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

    existing = teaching_assignment_repository.get_pending_submission(assignment_id)
    if existing is not None:
        raise DuplicatePendingSubmissionError(
            "Bảng điểm này đã được gửi duyệt và đang chờ Giáo vụ xử lý. "
            "Vui lòng hủy đơn cũ trước khi gửi lại.",
            pending_submission_id=existing.id,
        )

    roster_ids = list(
        class_enrollment_repository.list_enrolled_student_ids_by_class(
            assignment.class_id
        )
    )
    roster_set = set(roster_ids)

    all_rows = score_repository.list_by_assignment(assignment_id, draft_only=None)
    rows = [r for r in all_rows if int(r.student_id) in roster_set]

    if not rows:
        from studentapp.exceptions import ValidationError as VE2

        raise VE2(
            "Chưa có điểm nào để gửi duyệt. Vui lòng nhập điểm trước!",
            error="NO_SCORES_TO_SUBMIT",
        )

    cfg = _active_column_config()
    active_columns = cfg["active_columns"]
    incomplete = []
    total_filled = 0
    score_by_student = {int(r.student_id): r for r in rows}

    for sid in roster_ids:
        row = score_by_student.get(sid)
        if row is None:

            from studentapp.repositories import student_repository

            student = student_repository.get_by_id(sid)
            incomplete.append({
                "student_id": sid,
                "student_name": student.full_name if student else None,
                "missing_columns": list(active_columns),
            })
            continue

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
        total_students=len(roster_ids),
        total_scores=total_filled,
        note=(payload.get("note") or "").strip() or None,
    )
    db.session.add(submission)
    db.session.flush()

    now = datetime.utcnow()
    for row in rows:
        row.submitted_at = now
        db.session.add(row)

    db.session.commit()

    return submission.to_dict()

def cancel_submission(submission_id, payload, teacher_id):

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

    from studentapp.models.score_submission import ScoreSubmission
    from studentapp.services import submission_service

    rows = (
        ScoreSubmission.query.filter_by(teacher_id=int(teacher_id))
        .order_by(ScoreSubmission.id.desc())
        .all()
    )
    return [submission_service.enrich_submission(r) for r in rows]

def _validate_change_payload(payload):

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

    attachment = _read_attachment(payload)

    return int(assignment_id), reason, changes, attachment

def _read_attachment(payload):

    path = (payload.get("attachment_path") or "").strip()
    if not path:
        return None

    if path.startswith("/") or path.startswith("\\") or ".." in path.replace("\\", "/").split("/"):
        raise ValidationError(
            "Đường dẫn file đính kèm không hợp lệ.",
            error="INVALID_ATTACHMENT_PATH",
        )

    kind = (payload.get("attachment_type") or "").strip().upper() or None
    if kind not in ("IMAGE", "PDF"):
        raise ValidationError(
            "Loại file đính kèm không hợp lệ (chỉ nhận IMAGE hoặc PDF).",
            error="INVALID_ATTACHMENT_TYPE",
        )

    name = (payload.get("attachment_name") or "").strip() or path.rsplit("/", 1)[-1]
    return {"path": path, "type": kind, "name": name[:200]}

def _assert_no_pending_duplicate(assignment_id, changes):

    from studentapp.exceptions import DuplicatePendingAppealError
    from studentapp.models.score_change_detail import (
        ChangeDetailStatusEnum,
        ScoreChangeDetail,
    )
    from studentapp.models.score_change_request import (
        ChangeRequestStatusEnum,
        ScoreChangeRequest,
    )

    if not changes:
        return

    pending_request_ids = [
        r.id
        for r in ScoreChangeRequest.query.filter_by(
            assignment_id=int(assignment_id),
            status=ChangeRequestStatusEnum.PENDING,
        ).all()
    ]
    if not pending_request_ids:
        return

    pending_cells = set()
    for detail in ScoreChangeDetail.query.filter(
        ScoreChangeDetail.request_id.in_(pending_request_ids),
        ScoreChangeDetail.status == ChangeDetailStatusEnum.PENDING,
    ).all():
        pending_cells.add((int(detail.student_id), detail.score_column))

    if not pending_cells:
        return

    duplicates = []
    for change in changes:
        key = (int(change["student_id"]), change["score_column"].strip())
        if key in pending_cells:
            duplicates.append(
                {"student_id": key[0], "score_column": key[1]}
            )

    if duplicates:
        raise DuplicatePendingAppealError(cells=duplicates)

def create_change_request(payload, teacher_id):

    from studentapp.exceptions import (
        DuplicatePendingAppealError,
        ScoreTableNotLockedError,
        ScoreValueConflictError,
    )
    from studentapp.models.score_change_detail import (
        ChangeDetailStatusEnum,
        ScoreChangeDetail,
    )
    from studentapp.models.score_change_request import (
        ChangeRequestStatusEnum,
        ScoreChangeRequest,
    )

    assignment_id, reason, changes, attachment = _validate_change_payload(payload)

    assignment = teacher_service.ensure_teacher_owns_assignment(assignment_id, teacher_id)

    if not assignment.is_locked:
        raise ScoreTableNotLockedError(
            "Bảng điểm đang mở. Bạn hãy sửa điểm trực tiếp thay vì gửi đơn phúc khảo!"
        )

    _assert_no_pending_duplicate(assignment_id, changes)

    request = ScoreChangeRequest(
        assignment_id=assignment_id,
        teacher_id=teacher_id,
        reason=reason,
        status=ChangeRequestStatusEnum.PENDING,
        is_batch=len(changes) > 1,
        total_changes=len(changes),
    )
    if attachment:
        request.attachment_path = attachment["path"]
        request.attachment_type = attachment["type"]
        request.attachment_name = attachment["name"]
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

    from studentapp.models.score_change_request import ScoreChangeRequest
    from studentapp.services import change_review_service

    rows = (
        ScoreChangeRequest.query.filter_by(teacher_id=int(teacher_id))
        .order_by(ScoreChangeRequest.id.desc())
        .all()
    )
    return [change_review_service.enrich_request(r) for r in rows]
