from studentapp.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    ValidationError,
)
from studentapp.extensions import db
from studentapp.services.class_service import get_max_class_size

_RULE_CONSTRAINTS = (
    "MIN_AGE < MAX_AGE",
    "MAX_CLASS_SIZE > 0",
    "MIN_COL_15M <= MAX_COL_15M",
    "MIN_COL_45M <= MAX_COL_45M",
    "0 <= PASSING_SCORE <= 10",
    "MAX_LOGIN_ATTEMPTS > 0",
)

def _validate_rules_map(values: dict):

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
    from studentapp.utils.audit import write_audit

    write_audit(user_id, action, details)

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
    _validate_rules_map(merged)
    for rule, value in cleaned:
        rule.rule_value = value
        rule.updated_by = actor_id
        db.session.add(rule)
    _write_audit(actor_id, "BULK_UPDATE_RULES",
                 {"updated": [r.rule_key for r, _ in cleaned]})
    db.session.commit()
    return {"updated": [r.rule_key for r, _ in cleaned]}

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

def _parse_date(value):

    if value in (None, ""):
        return None
    if hasattr(value, "year") and hasattr(value, "month"):
        return value
    from datetime import date as _date

    try:
        return _date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError("Ngày phải có định dạng YYYY-MM-DD.")

def create_academic_year(payload, actor_id=None):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.semester import Semester

    payload = payload or {}
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
    if end < start:
        raise ValidationError("end_year không được nhỏ hơn start_year.")

    start_date = _parse_date(payload.get("start_date"))
    end_date = _parse_date(payload.get("end_date"))
    if start_date and end_date and end_date < start_date:
        raise ValidationError("end_date không được nhỏ hơn start_date.")

    is_current = bool(payload.get("is_current", False))
    y = AcademicYear(year_name=name, start_year=start, end_year=end,
                     start_date=start_date, end_date=end_date,
                     is_current=is_current)
    db.session.add(y)
    db.session.flush()

    for sem_name in Semester.SEMESTER_NAMES:
        db.session.add(Semester(
            semester_name=sem_name,
            academic_year_id=y.id,
            factor=Semester.factor_for(sem_name),
            is_current=False,
        ))
    db.session.flush()

    if is_current:
        AcademicYear.query.filter(AcademicYear.id != y.id).update(
            {AcademicYear.is_current: False}, synchronize_session=False)

        _set_current_semester_in_year(y.id, "HK1")
    _write_audit(actor_id, "CREATE_ACADEMIC_YEAR", {
        "year_id": y.id, "year_name": name,
    })
    db.session.commit()
    return y.to_dict()

def set_current_year(year_id, actor_id=None):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.semester import Semester

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

    Semester.query.filter_by(is_current=True).update(
        {Semester.is_current: False}, synchronize_session=False)
    _set_current_semester_in_year(y.id, "HK1")
    _write_audit(actor_id, "SET_CURRENT_YEAR", {"year_id": y.id})
    db.session.commit()
    return y.to_dict()

def _set_current_semester_in_year(academic_year_id, semester_name):

    from studentapp.models.semester import Semester

    Semester.query.filter_by(academic_year_id=academic_year_id).update(
        {Semester.is_current: False}, synchronize_session=False)
    row = Semester.query.filter_by(
        academic_year_id=academic_year_id, semester_name=semester_name).first()
    if row is None:
        return None
    row.is_current = True
    db.session.add(row)
    return row

def list_semesters(academic_year_id=None):

    from studentapp.models.semester import Semester

    q = Semester.query
    if academic_year_id not in (None, ""):
        try:
            q = q.filter_by(academic_year_id=int(academic_year_id))
        except (TypeError, ValueError):
            raise ValidationError("academic_year_id không hợp lệ.")
    return [s.to_dict() for s in q.order_by(
        Semester.academic_year_id.asc(), Semester.factor.asc()).all()]

def get_current_semester(academic_year_id=None):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.semester import Semester

    if academic_year_id not in (None, ""):
        try:
            yid = int(academic_year_id)
        except (TypeError, ValueError):
            raise ValidationError("academic_year_id không hợp lệ.")
        if db.session.get(AcademicYear, yid) is None:
            raise NotFoundError("Không tìm thấy năm học.")
        q = Semester.query.filter_by(academic_year_id=yid)
    else:
        year = AcademicYear.query.filter_by(is_current=True).first()
        if year is None:
            raise NotFoundError("Chưa thiết lập năm học hiện hành.")
        q = Semester.query.filter_by(academic_year_id=year.id)

    s = q.filter_by(is_current=True).order_by(Semester.factor.asc()).first()
    if s is None:
        raise NotFoundError("Chưa thiết lập học kỳ hiện hành.")
    return s.to_dict()

def create_semester(payload, actor_id=None):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.semester import Semester

    payload = payload or {}
    name = (payload.get("semester_name") or "").strip().upper()
    if not name:
        raise ValidationError("Thiếu semester_name (chỉ nhận HK1 hoặc HK2).")
    if name not in Semester.SEMESTER_NAMES:
        raise ValidationError(
            "Chỉ có 2 học kỳ trong một niên khóa: HK1 và HK2.",
            error="INVALID_SEMESTER_NAME",
        )
    try:
        year_id = int(payload.get("academic_year_id"))
    except (TypeError, ValueError):
        raise ValidationError("academic_year_id không hợp lệ.")
    year = db.session.get(AcademicYear, year_id)
    if year is None:
        raise NotFoundError("Không tìm thấy năm học.")
    if Semester.query.filter_by(
            academic_year_id=year_id, semester_name=name).first() is not None:
        raise DuplicateError(f"Học kỳ {name} đã tồn tại trong năm học này.")

    s = Semester(semester_name=name, academic_year_id=year_id,
                 factor=Semester.factor_for(name),
                 is_current=False)
    db.session.add(s)
    db.session.flush()

    if bool(payload.get("is_current", False)):
        _set_current_semester_in_year(year_id, name)
    _write_audit(actor_id, "CREATE_SEMESTER", {
        "semester_id": s.id, "semester_name": name, "academic_year_id": year_id,
    })
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
    _set_current_semester_in_year(s.academic_year_id, s.semester_name)
    _write_audit(actor_id, "SET_CURRENT_SEMESTER", {
        "semester_id": s.id, "semester_name": s.semester_name,
        "academic_year_id": s.academic_year_id,
    })
    db.session.commit()
    return s.to_dict()

def list_grades():
    from studentapp.models.grade import Grade

    return [g.to_dict() for g in Grade.query.order_by(Grade.grade_level).all()]

def list_teachers():

    from studentapp.models.user import User, UserRoleEnum

    rows = (
        User.query.filter(
            User.role == UserRoleEnum.TEACHER,
            User.is_active.is_(True),
        )
        .order_by(User.full_name)
        .all()
    )
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "username": u.username,
            "email": u.email,
        }
        for u in rows
    ]

def _class_item(c):

    from studentapp.repositories import class_enrollment_repository, user_repository

    item = c.to_dict()
    item["current_size_live"] = len(
        class_enrollment_repository.list_student_ids_by_class(c.id))
    item["max_size"] = get_max_class_size()
    grade = getattr(c, "grade", None)
    item["grade_name"] = grade.grade_name if grade else None
    item["academic_year_name"] = (
        c.academic_year.year_name if getattr(c, "academic_year", None) else None
    )
    item["homeroom_teacher_name"] = None
    if c.homeroom_teacher_id:
        t = user_repository.get_by_id(c.homeroom_teacher_id)
        item["homeroom_teacher_name"] = t.full_name if t else None
    return item

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
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [_class_item(c) for c in rows],
    }

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

    return _class_item(c)

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
