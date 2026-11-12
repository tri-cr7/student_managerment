"""SERVICE catalog — SD21 quy định, SD22 môn học, SD26 năm học/kỳ, SD27 GVCN.

Tất cả validate tập trung ở service để controller mỏng.
"""
from studentapp.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from studentapp.extensions import db


# --------------------------------------------------------------------------- #
# SD21 — Quy định (system_rules)
# --------------------------------------------------------------------------- #

#: Quy tắc validate logic đã chốt (§4 YC5).
_RULE_CONSTRAINTS = (
    "MIN_AGE < MAX_AGE",
    "MAX_CLASS_SIZE > 0",
    "MIN_COL_15M <= MAX_COL_15M",
    "MIN_COL_45M <= MAX_COL_45M",
    "0 <= PASSING_SCORE <= 10",
    "MAX_LOGIN_ATTEMPTS > 0",
)


def _validate_rules_map(values: dict):
    """Kiểm tra tính logic của bộ quy chế sau khi áp giá trị mới.

    :raises BusinessRuleError: 422 khi phi logic.
    """
    def num(key, default=0):
        try:
            return float(values.get(key, default))
        except (TypeError, ValueError):
            raise BusinessRuleError(f"Giá trị quy định {key} phải là số.",
                                    error="INVALID_RULE_VALUE")
    min_age, max_age = num("MIN_AGE"), num("MAX_AGE")
    if min_age >= max_age:
        raise BusinessRuleError("MIN_AGE phải nhỏ hơn MAX_AGE.",
                                error="INVALID_RULE_LOGIC")
    if num("MAX_CLASS_SIZE") <= 0:
        raise BusinessRuleError("MAX_CLASS_SIZE phải lớn hơn 0.",
                                error="INVALID_RULE_LOGIC")
    if num("MIN_COL_15M") > num("MAX_COL_15M"):
        raise BusinessRuleError("MIN_COL_15M phải ≤ MAX_COL_15M.",
                                error="INVALID_RULE_LOGIC")
    if num("MIN_COL_45M") > num("MAX_COL_45M"):
        raise BusinessRuleError("MIN_COL_45M phải ≤ MAX_COL_45M.",
                                error="INVALID_RULE_LOGIC")
    passing = num("PASSING_SCORE")
    if passing < 0 or passing > 10:
        raise BusinessRuleError("PASSING_SCORE phải nằm trong [0, 10].",
                                error="INVALID_RULE_LOGIC")
    if num("MAX_LOGIN_ATTEMPTS") <= 0:
        raise BusinessRuleError("MAX_LOGIN_ATTEMPTS phải lớn hơn 0.",
                                error="INVALID_RULE_LOGIC")


def _current_rules_map():
    from studentapp.models.system_rule import SystemRule

    return {r.rule_key: r.rule_value for r in SystemRule.query.all()}


def _write_audit(user_id, action, details):
    from studentapp.models.audit_log import AuditLog

    try:
        uid = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        uid = None
    db.session.add(AuditLog(user_id=uid, action=action, details=details))


def list_rules():
    from studentapp.repositories import system_rule_repository

    return [
        {"rule_key": r.rule_key, "rule_value": r.rule_value,
         "data_type": str(r.data_type), "description": r.description}
        for r in system_rule_repository.list_all()
    ]


def get_rule(rule_key):
    from studentapp.repositories import system_rule_repository

    r = system_rule_repository.get_rule(rule_key)
    if r is None:
        raise NotFoundError(f"Không tìm thấy quy định {rule_key}.")
    return {"rule_key": r.rule_key, "rule_value": r.rule_value,
            "data_type": str(r.data_type), "description": r.description}


def _coerce_value(rule, raw):
    text = str(raw).strip()
    if not text:
        raise BusinessRuleError(f"Giá trị {rule.rule_key} không được để trống.",
                                error="INVALID_RULE_VALUE")
    if str(rule.data_type) == "INT":
        try:
            int(float(text))
        except (TypeError, ValueError):
            raise BusinessRuleError(f"Giá trị {rule.rule_key} phải là số nguyên.",
                                    error="INVALID_RULE_VALUE")
    elif str(rule.data_type) == "FLOAT":
        try:
            float(text)
        except (TypeError, ValueError):
            raise BusinessRuleError(f"Giá trị {rule.rule_key} phải là số.",
                                    error="INVALID_RULE_VALUE")
    return text


def update_rule(rule_key, rule_value, description=None, actor_id=None):
    from studentapp.repositories import system_rule_repository

    rule = system_rule_repository.get_rule(rule_key)
    if rule is None:
        raise NotFoundError(f"Không tìm thấy quy định {rule_key}.")
    new_value = _coerce_value(rule, rule_value)
    merged = _current_rules_map()
    merged[rule_key] = new_value
    _validate_rules_map(merged)
    rule.rule_value = new_value
    if description is not None:
        rule.description = str(description)[:255]
    rule.updated_by = actor_id
    db.session.add(rule)
    _write_audit(actor_id, "UPDATE_RULE",
                 {"rule_key": rule_key, "new_value": new_value})
    db.session.commit()
    return {"rule_key": rule.rule_key, "rule_value": rule.rule_value,
            "new_value": rule.rule_value}


def bulk_update_rules(items, actor_id=None):
    from studentapp.repositories import system_rule_repository

    if not isinstance(items, list) or not items:
        raise ValidationError("Danh sách rules không hợp lệ hoặc rỗng.")
    cleaned = []
    for it in items:
        key = (it.get("rule_key") or "").strip()
        if not key:
            raise ValidationError("Mỗi rule phải có rule_key.")
        rule = system_rule_repository.get_rule(key)
        if rule is None:
            raise NotFoundError(f"Không tìm thấy quy định {key}.")
        cleaned.append((rule, _coerce_value(rule, it.get("rule_value"))))
    merged = _current_rules_map()
    for rule, value in cleaned:
        merged[rule.rule_key] = value
    _validate_rules_map(merged)  # validate toàn bộ trước khi commit
    for rule, value in cleaned:
        rule.rule_value = value
        rule.updated_by = actor_id
        db.session.add(rule)
    _write_audit(actor_id, "BULK_UPDATE_RULES",
                 {"updated": [r.rule_key for r, _ in cleaned]})
    db.session.commit()
    return {"updated": [r.rule_key for r, _ in cleaned]}


# --------------------------------------------------------------------------- #
# SD22 — Môn học
# --------------------------------------------------------------------------- #

def _subject_to_dict(s):
    item = s.to_dict()
    item["grade_name"] = s.grade.grade_name if s.grade else None
    return item


def list_subjects(keyword=None, grade_id=None, is_active=None):
    from studentapp.models.subject import Subject

    q = Subject.query
    if keyword not in (None, ""):
        kw = f"%{str(keyword).strip()}%"
        q = q.filter((Subject.subject_code.ilike(kw))
                   | (Subject.subject_name.ilike(kw)))
    if grade_id not in (None, ""):
        try:
            q = q.filter_by(grade_id=int(grade_id))
        except (TypeError, ValueError):
            raise ValidationError("grade_id không hợp lệ.")
    if is_active not in (None, ""):
        raw = str(is_active).strip().lower()
        if raw in ("1", "true", "yes"):
            q = q.filter_by(is_active=True)
        elif raw in ("0", "false", "no"):
            q = q.filter_by(is_active=False)
    return [_subject_to_dict(s) for s in q.order_by(Subject.id).all()]


def get_subject(subject_id):
    from studentapp.models.subject import Subject

    try:
        sid = int(subject_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy môn học.")
    s = db.session.get(Subject, sid)
    if s is None:
        raise NotFoundError("Không tìm thấy môn học.")
    return _subject_to_dict(s)


def list_subjects_by_grade(grade_id, is_active=None):
    try:
        gid = int(grade_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy khối lớp.")
    return list_subjects(grade_id=gid, is_active=is_active)


def create_subject(payload, actor_id=None):
    from studentapp.models.grade import Grade
    from studentapp.models.subject import Subject

    code = (payload.get("subject_code") or "").strip().upper()
    name = (payload.get("subject_name") or "").strip()
    if not code or not name:
        raise ValidationError("Thiếu subject_code hoặc subject_name.")
    try:
        grade_id = int(payload.get("grade_id"))
    except (TypeError, ValueError):
        raise ValidationError("grade_id không hợp lệ.")
    if db.session.get(Grade, grade_id) is None:
        raise NotFoundError("Không tìm thấy khối lớp.")
    if Subject.query.filter_by(subject_code=code).first() is not None:
        raise DuplicateError(f"Mã môn {code} đã tồn tại.")
    try:
        periods = int(payload.get("periods_count", 0) or 0)
    except (TypeError, ValueError):
        raise ValidationError("periods_count không hợp lệ.")
    s = Subject(subject_code=code, subject_name=name,
                grade_id=grade_id, periods_count=periods,
                is_active=bool(payload.get("is_active", True)))
    db.session.add(s)
    db.session.flush()
    _write_audit(actor_id, "CREATE_SUBJECT", {"subject_id": s.id, "code": code})
    db.session.commit()
    return _subject_to_dict(s)


def update_subject(subject_id, payload, actor_id=None):
    from studentapp.models.subject import Subject

    s = db.session.get(Subject, int(subject_id)) if str(subject_id).isdigit() else None
    if s is None:
        raise NotFoundError("Không tìm thấy môn học.")
    if payload.get("subject_code") not in (None, ""):
        code = str(payload["subject_code"]).strip().upper()
        dup = Subject.query.filter_by(subject_code=code).first()
        if dup is not None and dup.id != s.id:
            raise DuplicateError(f"Mã môn {code} đã tồn tại.")
        s.subject_code = code
    if payload.get("subject_name") not in (None, ""):
        s.subject_name = str(payload["subject_name"]).strip()
    if payload.get("grade_id") not in (None, ""):
        from studentapp.models.grade import Grade

        try:
            gid = int(payload["grade_id"])
        except (TypeError, ValueError):
            raise ValidationError("grade_id không hợp lệ.")
        if db.session.get(Grade, gid) is None:
            raise NotFoundError("Không tìm thấy khối lớp.")
        s.grade_id = gid
    if payload.get("periods_count") not in (None, ""):
        try:
            s.periods_count = int(payload["periods_count"])
        except (TypeError, ValueError):
            raise ValidationError("periods_count không hợp lệ.")
    if "is_active" in payload:
        raw = payload["is_active"]
        s.is_active = raw if isinstance(raw, bool) else str(raw).lower() in ("1", "true", "yes")
    db.session.add(s)
    _write_audit(actor_id, "UPDATE_SUBJECT", {"subject_id": s.id})
    db.session.commit()
    return _subject_to_dict(s)


def delete_subject(subject_id, actor_id=None):
    from studentapp.models.subject import Subject
    from studentapp.models.teaching_assignment import TeachingAssignment

    try:
        sid = int(subject_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy môn học.")
    s = db.session.get(Subject, sid)
    if s is None:
        raise NotFoundError("Không tìm thấy môn học.")
    if TeachingAssignment.query.filter_by(subject_id=sid).count() > 0:
        raise BusinessRuleError(
            "Môn học đã phát sinh phân công giảng dạy nên không thể xóa.",
            error="SUBJECT_HAS_ASSIGNMENTS",
        )
    snapshot = _subject_to_dict(s)
    db.session.delete(s)
    _write_audit(actor_id, "DELETE_SUBJECT", {"subject_id": sid})
    db.session.commit()
    return snapshot


# --------------------------------------------------------------------------- #
# SD26 — Năm học & học kỳ
# --------------------------------------------------------------------------- #

def list_academic_years():
    from studentapp.models.academic_year import AcademicYear

    return [y.to_dict() for y in AcademicYear.query.order_by(
        AcademicYear.start_year.desc()).all()]


def get_current_year():
    from studentapp.models.academic_year import AcademicYear

    y = AcademicYear.query.filter_by(is_current=True).first()
    if y is None:
        raise NotFoundError("Chưa thiết lập năm học hiện hành.")
    return y.to_dict()


def create_academic_year(payload, actor_id=None):
    from studentapp.models.academic_year import AcademicYear

    name = (payload.get("year_name") or "").strip()
    if not name:
        raise ValidationError("Thiếu year_name (VD: 2026-2027).")
    if AcademicYear.query.filter_by(year_name=name).first() is not None:
        raise DuplicateError(f"Năm học {name} đã tồn tại.")
    try:
        start = int(payload.get("start_year", name.split("-")[0]))
        end = int(payload.get("end_year", name.split("-")[-1]))
    except (TypeError, ValueError):
        raise ValidationError("start_year/end_year không hợp lệ.")
    y = AcademicYear(year_name=name, start_year=start, end_year=end,
                     is_current=bool(payload.get("is_current", False)))
    db.session.add(y)
    db.session.flush()
    if y.is_current:
        AcademicYear.query.filter(AcademicYear.id != y.id).update(
            {AcademicYear.is_current: False}, synchronize_session=False)
    _write_audit(actor_id, "CREATE_ACADEMIC_YEAR", {"year_id": y.id})
    db.session.commit()
    return y.to_dict()


def set_current_year(year_id, actor_id=None):
    from studentapp.models.academic_year import AcademicYear

    try:
        yid = int(year_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy năm học.")
    y = db.session.get(AcademicYear, yid)
    if y is None:
        raise NotFoundError("Không tìm thấy năm học.")
    AcademicYear.query.update({AcademicYear.is_current: False},
                              synchronize_session=False)
    y.is_current = True
    db.session.add(y)
    _write_audit(actor_id, "SET_CURRENT_YEAR", {"year_id": y.id})
    db.session.commit()
    return y.to_dict()


def list_semesters(academic_year_id=None):
    from studentapp.models.semester import Semester

    q = Semester.query
    if academic_year_id not in (None, ""):
        try:
            q = q.filter_by(academic_year_id=int(academic_year_id))
        except (TypeError, ValueError):
            raise ValidationError("academic_year_id không hợp lệ.")
    return [s.to_dict() for s in q.order_by(Semester.id).all()]


def get_current_semester():
    from studentapp.models.semester import Semester

    s = Semester.query.filter_by(is_current=True).first()
    if s is None:
        raise NotFoundError("Chưa thiết lập học kỳ hiện hành.")
    return s.to_dict()


def create_semester(payload, actor_id=None):
    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.semester import Semester

    name = (payload.get("semester_name") or "").strip()
    if not name:
        raise ValidationError("Thiếu semester_name (VD: HK1).")
    try:
        year_id = int(payload.get("academic_year_id"))
    except (TypeError, ValueError):
        raise ValidationError("academic_year_id không hợp lệ.")
    if db.session.get(AcademicYear, year_id) is None:
        raise NotFoundError("Không tìm thấy năm học.")
    if Semester.query.filter_by(
            academic_year_id=year_id, semester_name=name).first() is not None:
        raise DuplicateError(f"Học kỳ {name} đã tồn tại trong năm học này.")
    try:
        factor = int(payload.get("factor", 1))
    except (TypeError, ValueError):
        raise ValidationError("factor không hợp lệ.")
    s = Semester(semester_name=name, academic_year_id=year_id,
                 factor=factor, is_current=bool(payload.get("is_current", False)))
    db.session.add(s)
    db.session.flush()
    if s.is_current:
        Semester.query.filter(Semester.id != s.id).update(
            {Semester.is_current: False}, synchronize_session=False)
    _write_audit(actor_id, "CREATE_SEMESTER", {"semester_id": s.id})
    db.session.commit()
    return s.to_dict()


def set_current_semester(semester_id, actor_id=None):
    from studentapp.models.semester import Semester

    try:
        sid = int(semester_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy học kỳ.")
    s = db.session.get(Semester, sid)
    if s is None:
        raise NotFoundError("Không tìm thấy học kỳ.")
    Semester.query.update({Semester.is_current: False}, synchronize_session=False)
    s.is_current = True
    db.session.add(s)
    _write_audit(actor_id, "SET_CURRENT_SEMESTER", {"semester_id": s.id})
    db.session.commit()
    return s.to_dict()


# --------------------------------------------------------------------------- #
# SD27 — Lớp & GVCN (+ danh mục grades)
# --------------------------------------------------------------------------- #

def list_grades():
    from studentapp.models.grade import Grade

    return [g.to_dict() for g in Grade.query.order_by(Grade.grade_level).all()]


def list_classes(page=1, limit=20, grade_id=None, academic_year_id=None):
    from studentapp.models.class_room import Class

    q = Class.query
    if grade_id not in (None, ""):
        try:
            q = q.filter_by(grade_id=int(grade_id))
        except (TypeError, ValueError):
            raise ValidationError("grade_id không hợp lệ.")
    if academic_year_id not in (None, ""):
        try:
            q = q.filter_by(academic_year_id=int(academic_year_id))
        except (TypeError, ValueError):
            raise ValidationError("academic_year_id không hợp lệ.")
    total = q.count()
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = min(100, max(1, int(limit)))
    except (TypeError, ValueError):
        limit = 20
    rows = q.order_by(Class.id.desc()).offset((page - 1) * limit).limit(limit).all()
    data = []
    for c in rows:
        from studentapp.repositories import class_enrollment_repository

        size = len(class_enrollment_repository.list_student_ids_by_class(c.id))
        item = c.to_dict()
        item["current_size_live"] = size
        item["homeroom_teacher_name"] = None
        if c.homeroom_teacher_id:
            from studentapp.repositories import user_repository

            t = user_repository.get_by_id(c.homeroom_teacher_id)
            item["homeroom_teacher_name"] = t.full_name if t else None
        data.append(item)
    return {"total": total, "page": page, "limit": limit, "data": data}


def get_class(class_id):
    from studentapp.models.class_room import Class

    try:
        cid = int(class_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy lớp học.")
    c = db.session.get(Class, cid)
    if c is None:
        raise NotFoundError("Không tìm thấy lớp học.")
    return _class_detail(c)


def _class_detail(c):
    from studentapp.repositories import class_enrollment_repository, user_repository

    item = c.to_dict()
    item["current_size_live"] = len(
        class_enrollment_repository.list_student_ids_by_class(c.id))
    t = user_repository.get_by_id(c.homeroom_teacher_id) if c.homeroom_teacher_id else None
    item["homeroom_teacher_name"] = t.full_name if t else None
    return item


def set_homeroom(class_id, teacher_id, actor_id=None):
    from studentapp.models.class_room import Class
    from studentapp.models.user import UserRoleEnum
    from studentapp.repositories import user_repository

    try:
        cid = int(class_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy lớp học.")
    c = db.session.get(Class, cid)
    if c is None:
        raise NotFoundError("Không tìm thấy lớp học.")
    try:
        tid = int(teacher_id)
    except (TypeError, ValueError):
        raise ValidationError("teacher_id không hợp lệ.")
    t = user_repository.get_by_id(tid)
    if t is None:
        raise NotFoundError("Không tìm thấy giáo viên.")
    if t.role != UserRoleEnum.TEACHER:
        raise ValidationError("Người được gán phải có vai trò Giáo viên (TEACHER).",
                              error="INVALID_HOMEROOM_TEACHER")
    if not bool(t.is_active) or bool(t.is_locked):
        raise ValidationError("Giáo viên không còn hoạt động nên không thể làm GVCN.",
                              error="TEACHER_INACTIVE")
    c.homeroom_teacher_id = tid
    db.session.add(c)
    _write_audit(actor_id, "SET_HOMEROOM",
                 {"class_id": cid, "teacher_id": tid})
    db.session.commit()
    return _class_detail(c)


def list_classes_by_grade(grade_id):
    from studentapp.models.class_room import Class

    try:
        gid = int(grade_id)
    except (TypeError, ValueError):
        raise NotFoundError("Không tìm thấy khối lớp.")
    rows = Class.query.filter_by(grade_id=gid).order_by(Class.id).all()
    return [_class_detail(c) for c in rows]
