import csv
import io
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError

from studentapp.extensions import db
from studentapp.models.student import Student, StudentStatusEnum
from studentapp.repositories import student_repository, system_rule_repository
from studentapp.exceptions import AppError, DuplicateError, NotFoundError, ValidationError

class StudentBusinessError(AppError):

    status_code = 400
    error = "STUDENT_ERROR"
    message = "Dữ liệu hồ sơ học sinh không hợp lệ."

    def __init__(self, message, error_code="STUDENT_ERROR", status_code=400):
        super().__init__(error=error_code, message=message)
        self.status_code = status_code

class StudentRuleViolation(AppError):

    status_code = 422
    error = "BUSINESS_RULE_VIOLATION"
    message = "Vi phạm quy chế nghiệp vụ."

    def __init__(self, message, error_code="BUSINESS_RULE_VIOLATION", current_rules=None):
        super().__init__(error=error_code, message=message)
        self.current_rules = current_rules

class StudentDeleteBlockedError(StudentBusinessError):

    status_code = 400
    error = "STUDENT_DELETE_BLOCKED"

    def __init__(self, message, blockers=None, relations=None):
        super().__init__(message, error_code="STUDENT_DELETE_BLOCKED", status_code=400)
        self.blockers = blockers or []
        self.relations = relations or []

def get_age_rules():

    return (
        system_rule_repository.get_int("MIN_AGE", 15),
        system_rule_repository.get_int("MAX_AGE", 20),
    )

def get_max_class_size():

    return system_rule_repository.get_int("MAX_CLASS_SIZE", 40)

def calculate_age(dob, today=None):

    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def _age_rules_payload():
    lo, hi = get_age_rules()
    return {"min_age": lo, "max_age": hi}

def _write_audit(user_id, action, details=None):

    from studentapp.utils.audit import write_audit

    write_audit(user_id, action, details)

def _pick_dob(payload):

    return payload.get("date_of_birth") or payload.get("dob")

def _parse_dob(raw):
    if raw in (None, ""):
        return None
    if isinstance(raw, date):
        return raw
    if isinstance(raw, (int, float)):
        raise StudentBusinessError("Định dạng ngày sinh không hợp lệ. Vui lòng dùng YYYY-MM-DD.",
                                   error_code="INVALID_DATE_FORMAT")
    text = str(raw).strip()

    if " " in text:
        text = text.split(" ", 1)[0]
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise StudentBusinessError("Định dạng ngày sinh không hợp lệ. Vui lòng dùng YYYY-MM-DD.",
                                   error_code="INVALID_DATE_FORMAT")

def _integrity_to_duplicate(exc, student_code=None):

    raw = str(getattr(exc, "orig", exc))
    if "student_code" in raw:
        return StudentBusinessError(
            "Mã học sinh '%s' đã tồn tại trong hệ thống." % student_code,
            error_code="DUPLICATE_CODE",
        )
    for label, field in (("Email", "email"), ("Số điện thoại", "phone"),
                          ("Số CCCD", "citizen_id")):
        if field in raw:
            return DuplicateError(
                "%s đã thuộc học sinh khác." % label, error="DUPLICATE"
            )
    return DuplicateError(
        "Dữ liệu học sinh đã tồn tại (vi phạm ràng buộc duy nhất).", error="DUPLICATE"
    )

def _validate_contact(student_id, email=None, phone=None, citizen_id=None):

    duplicates = []
    checks = (
        ("email", email, "Email"),
        ("phone", phone, "Số điện thoại"),
        ("citizen_id", citizen_id, "Số CCCD"),
    )
    for field, value, label in checks:
        val = (str(value).strip() if value is not None else "")
        if not val:
            continue
        q = Student.query.filter(getattr(Student, field) == val)
        if student_id is not None:
            q = q.filter(Student.id != int(student_id))
        if q.first() is not None:
            duplicates.append((field, label, val))
    return duplicates

def _raise_if_duplicate_contact(student_id, email=None, phone=None, citizen_id=None):
    dups = _validate_contact(student_id, email, phone, citizen_id)
    if not dups:
        return
    detail = ", ".join("%s '%s'" % (label, val) for _f, label, val in dups)
    raise DuplicateError(
        "Email/SĐT/CCCD đã thuộc học sinh khác: %s." % detail,
        error="DUPLICATE",
    )

def _validate_text_length(payload, fields):

    errors = []
    max_len = {
        "full_name": 100, "gender": 10, "address": 255, "phone": 15,
        "email": 100, "citizen_id": 20, "parent_name": 100,
        "parent_phone": 15, "student_code": 30,
    }
    for f in fields:
        if f not in payload:
            continue
        v = payload.get(f)
        if v is None:
            continue
        limit = max_len.get(f)
        if limit and len(str(v)) > limit:
            errors.append("%s vượt quá độ dài tối đa %d ký tự." % (f, limit))
    return errors

def _validate_email_format(email):
    from studentapp.utils.validators import is_email

    if email in (None, ""):
        return
    if not is_email(str(email)):
        raise StudentBusinessError("Định dạng email không hợp lệ.",
                                   error_code="INVALID_EMAIL")

def list_students(page=1, limit=20, keyword="", class_id=None, status=None,
                  academic_year_id=None, include_deleted=False):

    query = Student.query
    if not include_deleted:
        query = student_repository.not_deleted(query)

    kw = (keyword or "").strip()
    if kw:
        like = "%%%s%%" % kw
        query = query.filter(
            db.or_(Student.full_name.ilike(like), Student.student_code.ilike(like))
        )

    if class_id not in (None, ""):
        from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum

        try:
            cid = int(class_id)
        except (TypeError, ValueError):
            raise StudentBusinessError("Mã lớp không hợp lệ.", error_code="INVALID_CLASS_ID")

        sub = db.session.query(ClassEnrollment.student_id).filter(
            ClassEnrollment.class_id == cid,
            ClassEnrollment.status == EnrollmentStatusEnum.DANG_HOC,
        )
        if academic_year_id not in (None, ""):
            try:
                sub = sub.filter(ClassEnrollment.academic_year_id == int(academic_year_id))
            except (TypeError, ValueError):
                pass
        query = query.filter(Student.id.in_(sub))

    if status not in (None, ""):
        try:
            query = query.filter(Student.status == StudentStatusEnum(str(status).strip().upper()))
        except ValueError:
            raise StudentBusinessError(
                "Trạng thái không hợp lệ. Các giá trị cho phép: %s"
                % [e.value for e in StudentStatusEnum],
                error_code="INVALID_STATUS",
            )

    pagination = query.order_by(Student.full_name).paginate(
        page=page, per_page=limit, error_out=False
    )

    return {
        "items": _with_class_info(
            [student.to_dict() for student in pagination.items],
            academic_year_id=academic_year_id,
        ),
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": pagination.per_page,
    }

def _with_class_info(items, academic_year_id=None):

    if not items:
        return items

    from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum

    student_ids = [it.get("id") for it in items if it.get("id") is not None]
    if not student_ids:
        return items

    q = ClassEnrollment.query.filter(
        ClassEnrollment.student_id.in_(student_ids),
        ClassEnrollment.status == EnrollmentStatusEnum.DANG_HOC,
    )
    if academic_year_id not in (None, ""):
        try:
            q = q.filter(ClassEnrollment.academic_year_id == int(academic_year_id))
        except (TypeError, ValueError):
            pass

    info = {}
    for enr in q.order_by(ClassEnrollment.id.desc()).all():

        if enr.student_id in info:
            continue
        cls = enr.class_room
        if cls is None:
            continue
        grade = getattr(cls, "grade", None)
        info[enr.student_id] = {
            "class_id": cls.id,
            "class_name": cls.class_name,
            "grade_id": cls.grade_id,
            "grade_name": grade.grade_name if grade is not None else None,
        }

    for it in items:
        meta = info.get(it.get("id"))
        if meta:
            it.update(meta)
        else:
            it.setdefault("class_id", None)
            it.setdefault("class_name", None)
            it.setdefault("grade_id", None)
            it.setdefault("grade_name", None)

    return items

def get_student_detail(student_id, teacher_id=None, is_academic=False):

    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với ID: %s" % student_id,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )
    if not is_academic and teacher_id is not None:
        from studentapp.services import teacher_service

        teacher_service.ensure_teacher_can_view_student(teacher_id, student_id)
    return _with_class_info([student.to_dict()])[0]

def get_student_by_code(student_code, teacher_id=None, is_academic=False):

    student = student_repository.get_by_code(student_code)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với mã: %s" % student_code,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )
    if not is_academic and teacher_id is not None:
        from studentapp.services import teacher_service

        teacher_service.ensure_teacher_can_view_student(teacher_id, student.id)
    return _with_class_info([student.to_dict()])[0]

def admit_student(payload, actor_id=None):

    payload = payload or {}
    student_code = (payload.get("student_code") or "").strip()
    full_name = (payload.get("full_name") or "").strip()
    dob_raw = _pick_dob(payload)

    if not student_code or not full_name or dob_raw in (None, ""):
        raise StudentBusinessError(
            "Thiếu thông tin bắt buộc (student_code, full_name, date_of_birth).",
            error_code="MISSING_FIELDS",
        )

    if student_repository.get_by_code(student_code):
        raise StudentBusinessError(
            "Mã học sinh '%s' đã tồn tại trong hệ thống." % student_code,
            error_code="DUPLICATE_CODE",
        )

    length_errors = _validate_text_length(
        {"student_code": student_code, "full_name": full_name}, ("student_code", "full_name")
    )
    if length_errors:
        raise StudentBusinessError(" ".join(length_errors), error_code="INVALID_LENGTH")

    dob = _parse_dob(dob_raw)
    if dob is None:
        raise StudentBusinessError("Thiếu thông tin bắt buộc (student_code, full_name, date_of_birth).",
                                   error_code="MISSING_FIELDS")

    min_age, max_age = get_age_rules()
    age = calculate_age(dob)
    if not (min_age <= age <= max_age):
        raise StudentRuleViolation(
            "Tuổi của học sinh là %d tuổi. Không hợp lệ với quy định tiếp nhận "
            "(Từ %d đến %d tuổi)!" % (age, min_age, max_age),
            error_code="BUSINESS_RULE_VIOLATION",
            current_rules=_age_rules_payload(),
        )

    email = payload.get("email")
    _validate_email_format(email)
    _raise_if_duplicate_contact(
        None, email=email, phone=payload.get("phone"), citizen_id=payload.get("citizen_id")
    )

    new_student = Student(
        student_code=student_code,
        full_name=full_name,
        gender=payload.get("gender"),
        date_of_birth=dob,
        address=payload.get("address"),
        phone=payload.get("phone"),
        email=email,
        citizen_id=payload.get("citizen_id"),
        parent_name=payload.get("parent_name"),
        parent_phone=payload.get("parent_phone"),
        status=StudentStatusEnum.DANG_HOC,
        created_by=actor_id,
    )

    db.session.add(new_student)
    try:
        db.session.flush()
    except IntegrityError as e:

        db.session.rollback()
        raise _integrity_to_duplicate(e, student_code)

    _write_audit(actor_id, "ADMIT_STUDENT",
                 {"student_id": new_student.id, "student_code": student_code,
                  "full_name": full_name, "age": age})
    db.session.commit()
    return _student_payload(new_student, calculated_age=age)

def _student_payload(student, calculated_age=None):

    data = student.to_dict()
    if calculated_age is None and student.date_of_birth:
        calculated_age = calculate_age(student.date_of_birth)
    if calculated_age is not None:
        data["calculated_age"] = calculated_age
    data["created_at"] = student.created_at.isoformat() if student.created_at else None
    data["updated_at"] = student.updated_at.isoformat() if student.updated_at else None
    return data

def update_student(student_id, payload, actor_id=None):

    payload = payload or {}
    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với ID: %s" % student_id,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )

    length_errors = _validate_text_length(
        payload, ("full_name", "gender", "address", "phone", "email",
                  "citizen_id", "parent_name", "parent_phone")
    )
    if length_errors:
        raise StudentBusinessError(" ".join(length_errors), error_code="INVALID_LENGTH")

    if "email" in payload:
        _validate_email_format(payload.get("email"))

    new_email = payload.get("email", student.email)
    new_phone = payload.get("phone", student.phone)
    new_citizen = payload.get("citizen_id", student.citizen_id)
    _raise_if_duplicate_contact(student.id, email=new_email, phone=new_phone,
                                 citizen_id=new_citizen)

    changed = {}
    for field in ("full_name", "gender", "address", "phone", "email",
                  "citizen_id", "parent_name", "parent_phone"):
        if field in payload:
            old = getattr(student, field)
            new = payload[field]
            if old != new:
                changed[field] = {"from": old, "to": new}
            setattr(student, field, new)

    if "date_of_birth" in payload or "dob" in payload:
        dob = _parse_dob(_pick_dob(payload))
        if dob is not None:
            min_age, max_age = get_age_rules()
            age = calculate_age(dob)
            if not (min_age <= age <= max_age):
                raise StudentRuleViolation(
                    "Tuổi cập nhật là %d tuổi. Không hợp lệ với quy định "
                    "(Từ %d đến %d tuổi)!" % (age, min_age, max_age),
                    error_code="BUSINESS_RULE_VIOLATION",
                    current_rules=_age_rules_payload(),
                )
            if student.date_of_birth != dob:
                changed["date_of_birth"] = {
                    "from": student.date_of_birth.isoformat() if student.date_of_birth else None,
                    "to": dob.isoformat(),
                }
            student.date_of_birth = dob

    if changed:
        _write_audit(actor_id, "UPDATE_STUDENT",
                     {"student_id": student.id, "student_code": student.student_code,
                      "changed_fields": list(changed.keys()), "changes": changed})
    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        raise _integrity_to_duplicate(e, student.student_code)
    db.session.commit()
    return _student_payload(student)

def update_student_status(student_id, payload, actor_id=None):

    payload = payload or {}
    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với ID: %s" % student_id,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )

    status_str = (payload.get("status") or "").strip().upper()
    if not status_str:
        raise StudentBusinessError(
            "Trạng thái không hợp lệ. Các giá trị cho phép: %s"
            % [e.value for e in StudentStatusEnum],
            error_code="INVALID_STATUS",
        )
    try:
        new_status = StudentStatusEnum(status_str)
    except ValueError:
        raise StudentBusinessError(
            "Trạng thái không hợp lệ. Các giá trị cho phép: %s"
            % [e.value for e in StudentStatusEnum],
            error_code="INVALID_STATUS",
        )

    old_status = student.status
    student.status = new_status

    sync = _sync_enrollment_with_status(student, old_status, new_status)

    if old_status != new_status:
        _write_audit(actor_id, "UPDATE_STUDENT_STATUS",
                     {"student_id": student.id, "student_code": student.student_code,
                      "from_status": old_status.value if old_status else None,
                      "to_status": new_status.value, "sync": sync})
    db.session.commit()
    data = _student_payload(student)
    data["sync"] = sync
    return data

def _sync_enrollment_with_status(student, old_status, new_status):

    from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum

    leaving_states = (StudentStatusEnum.THOI_HOC, StudentStatusEnum.BAO_LUU)
    leaving = new_status in leaving_states
    was_leaving = old_status in leaving_states
    if leaving == was_leaving:
        return {"changed": False}

    enrollments = ClassEnrollment.query.filter_by(student_id=student.id).all()
    changed = []
    if leaving:
        for enr in enrollments:
            if enr.status == EnrollmentStatusEnum.DANG_HOC:
                enr.status = EnrollmentStatusEnum.DA_CHUYEN
                _dec_class_size(enr.class_id)
                changed.append({"class_id": enr.class_id, "action": "ENROLLED_OUT"})
    else:

        current_year_id = _current_academic_year_id()
        candidates = [
            e for e in enrollments
            if e.status == EnrollmentStatusEnum.DA_CHUYEN
            and (current_year_id is None or int(e.academic_year_id) == int(current_year_id))
        ]
        if candidates:
            latest = max(candidates, key=lambda e: (e.enrollment_date, e.id))
            for enr in candidates:
                if enr.id == latest.id:
                    if not _inc_class_size(enr.class_id):
                        continue
                    enr.status = EnrollmentStatusEnum.DANG_HOC
                    changed.append({"class_id": enr.class_id,
                                    "action": "ENROLLED_BACK"})
    return {"changed": bool(changed), "enrollments": changed}

def _current_academic_year_id():

    try:
        from studentapp.models.academic_year import AcademicYear

        ay = AcademicYear.query.filter_by(is_current=True).first()
        if ay is None:
            ay = AcademicYear.query.order_by(AcademicYear.id.desc()).first()
        return ay.id if ay else None
    except Exception:
        return None

def _dec_class_size(class_id):

    from studentapp.models.class_room import Class

    cls = db.session.get(Class, class_id)
    if cls is not None and cls.current_size > 0:
        cls.current_size -= 1

def _inc_class_size(class_id):

    from studentapp.models.class_room import Class
    from studentapp.services.class_service import count_active_students

    cls = db.session.get(Class, class_id)
    if cls is None:
        return False
    max_size = get_max_class_size()
    if count_active_students(class_id) >= max_size:
        return False
    cls.current_size = count_active_students(class_id) + 1
    return True

_IMPORT_COLUMNS = {
    "student_code": ("student_code", "ma_hoc_sinh", "mã học sinh", "mahocsinh", "code"),
    "full_name": ("full_name", "fullname", "ho_ten", "họ tên", "hoten", "name", "ten"),
    "date_of_birth": ("date_of_birth", "dob", "ngay_sinh", "ngày sinh", "ngaysinh"),
    "gender": ("gender", "gioi_tinh", "giới tính", "gioitinh"),
    "address": ("address", "dia_chi", "địa chỉ", "diachi"),
    "phone": ("phone", "sdt", "so_dien_thoai", "số điện thoại", "sodienthoai", "phone_number"),
    "email": ("email", "mail"),
    "citizen_id": ("citizen_id", "cccd", "so_cccd", "số cccd", "cccd"),
    "parent_name": ("parent_name", "ten_phu_huynh", "tên phụ huynh", "phu_huynh"),
    "parent_phone": ("parent_phone", "sdt_phu_huynh", "sdt_phu_huynh"),
}

_REQUIRED_IMPORT = ("student_code", "full_name", "date_of_birth")

def _normalize_header(raw):

    text = str(raw or "").strip().lower()

    table = {
        "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a", "â": "a", "ấ": "a", "ầ": "a",
        "ẩ": "a", "ẫ": "a", "ậ": "a", "ă": "a", "ắ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a",
        "ặ": "a", "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e", "ê": "e", "ế": "e",
        "ề": "e", "ể": "e", "ễ": "e", "ệ": "e", "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i",
        "ị": "i", "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o", "ô": "o", "ố": "o",
        "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o", "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o",
        "ỡ": "o", "ợ": "o", "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u", "ư": "u",
        "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u", "ỳ": "y", "ý": "y", "ỷ": "y",
        "ỹ": "y", "ỵ": "y", "đ": "d",
    }
    text = "".join(table.get(ch, ch) for ch in text)
    return "".join(ch for ch in text if ch.isalnum())

def _map_header(raw):

    norm = _normalize_header(raw)
    for key, aliases in _IMPORT_COLUMNS.items():
        if norm in {(_normalize_header(a)) for a in aliases}:
            return key
    return None

def _read_rows(file_obj, filename):

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext in ("xlsx", "xlsm"):
        from openpyxl import load_workbook

        wb = load_workbook(file_obj, data_only=True, read_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            return []
        mapping = [(i, _map_header(h)) for i, h in enumerate(header)]
        out = []
        for offset, row in enumerate(rows_iter, start=2):
            if row is None or all(c is None or str(c).strip() == "" for c in row):
                continue
            rec = {}
            for idx, key in mapping:
                if key is None or idx >= len(row):
                    continue
                val = row[idx]
                if val is None:
                    continue
                rec[key] = val
            out.append((offset, rec))
        wb.close()
        return out

    content = file_obj.read()
    if isinstance(content, bytes):
        for enc in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise StudentBusinessError("Không đọc được nội dung file (mã hoá không hỗ trợ).",
                                       error_code="INVALID_FILE_ENCODING")
    else:
        text = content

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = list(reader)
    if not rows:
        return []
    header = rows[0]
    mapping = [(i, _map_header(h)) for i, h in enumerate(header)]
    out = []
    for offset, row in enumerate(rows[1:], start=2):
        if not row or all(not str(c).strip() for c in row):
            continue
        rec = {}
        for idx, key in mapping:
            if key is None or idx >= len(row):
                continue
            val = str(row[idx]).strip()
            if val:
                rec[key] = val
        out.append((offset, rec))
    return out

def import_students_from_excel(file_obj, actor_id=None):

    filename = getattr(file_obj, "filename", "") or ""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in ("xlsx", "xls", "xlsm", "csv"):
        raise StudentBusinessError(
            "Chỉ hỗ trợ file định dạng .xlsx, .xls hoặc .csv", error_code="INVALID_FILE_TYPE"
        )

    try:
        file_obj.stream.seek(0)
    except Exception:
        pass

    try:
        rows = _read_rows(file_obj, filename)
    except StudentBusinessError:
        raise
    except Exception as e:
        raise StudentBusinessError(
            "Không đọc được nội dung file: %s" % e, error_code="INVALID_FILE_CONTENT"
        )

    min_age, max_age = get_age_rules()
    errors = []
    to_insert = []
    seen_codes = set()
    total_rows = len(rows)

    for row_no, rec in rows:
        code = str(rec.get("student_code") or "").strip()
        name = str(rec.get("full_name") or "").strip()

        missing = [f for f in _REQUIRED_IMPORT if not str(rec.get(f) or "").strip()]
        if missing:
            errors.append({
                "row": row_no,
                "student_name": name or None,
                "reason": "Thiếu cột bắt buộc: %s" % ", ".join(missing),
            })
            continue

        try:
            dob = _parse_dob(rec.get("date_of_birth"))
        except StudentBusinessError as e:
            errors.append({"row": row_no, "student_name": name,
                           "reason": "Ngày sinh không hợp lệ (cần định dạng YYYY-MM-DD)."})
            continue
        if dob is None:
            errors.append({"row": row_no, "student_name": name,
                           "reason": "Thiếu ngày sinh."})
            continue

        age = calculate_age(dob)
        if not (min_age <= age <= max_age):
            errors.append({
                "row": row_no,
                "student_name": name,
                "reason": "Tuổi %d vi phạm quy định nhỏ hơn %d tuổi hoặc lớn hơn %d tuổi."
                          % (age, min_age, max_age),
            })
            continue

        if code in seen_codes:
            errors.append({"row": row_no, "student_name": name,
                           "reason": "Mã học sinh %s bị trùng trong file." % code})
            continue

        if student_repository.get_by_code(code) is not None:
            errors.append({"row": row_no, "student_name": name,
                           "reason": "Mã học sinh %s đã tồn tại." % code})
            continue

        email = rec.get("email")
        dups = _validate_contact(None, email=email, phone=rec.get("phone"),
                                 citizen_id=rec.get("citizen_id"))
        if dups:
            errors.append({
                "row": row_no, "student_name": name,
                "reason": "%s đã thuộc học sinh khác." % ", ".join(l for _f, l, _v in dups),
            })
            continue

        seen_codes.add(code)
        to_insert.append((row_no, code, name, dob, rec))

    success_count = 0
    for row_no, code, name, dob, rec in to_insert:
        st = Student(
            student_code=code,
            full_name=name,
            gender=(str(rec.get("gender")).strip() if rec.get("gender") else None),
            date_of_birth=dob,
            address=(str(rec.get("address")).strip() if rec.get("address") else None),
            phone=(str(rec.get("phone")).strip() if rec.get("phone") else None),
            email=(str(rec.get("email")).strip() if rec.get("email") else None),
            citizen_id=(str(rec.get("citizen_id")).strip() if rec.get("citizen_id") else None),
            parent_name=(str(rec.get("parent_name")).strip() if rec.get("parent_name") else None),
            parent_phone=(str(rec.get("parent_phone")).strip() if rec.get("parent_phone") else None),
            status=StudentStatusEnum.DANG_HOC,
            created_by=actor_id,
        )
        db.session.add(st)
        try:
            db.session.flush()
            success_count += 1
        except IntegrityError:
            db.session.rollback()
            errors.append({"row": row_no, "student_name": name,
                           "reason": "Mã học sinh %s đã tồn tại." % code})

    if success_count:
        _write_audit(actor_id, "IMPORT_STUDENTS",
                     {"total_rows": total_rows, "success_count": success_count,
                      "failed_count": len(errors)})
    db.session.commit()

    return {
        "total_rows": total_rows,
        "success_count": success_count,
        "failed_count": len(errors),
        "errors": errors,
    }

DELETE_MODE_AUTO = "AUTO"
DELETE_MODE_SOFT = "SOFT"
DELETE_MODES = (DELETE_MODE_AUTO, DELETE_MODE_SOFT)

def _collect_student_relations(student):

    from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum
    from studentapp.models.score import Score
    from studentapp.models.score_change_detail import (
        ScoreChangeDetail,
        ChangeDetailStatusEnum,
    )
    from studentapp.models.score_change_request import (
        ScoreChangeRequest,
        ChangeRequestStatusEnum,
    )

    enrollments = ClassEnrollment.query.filter_by(student_id=student.id).all()
    active_enrollments = [
        e for e in enrollments if e.status == EnrollmentStatusEnum.DANG_HOC
    ]

    scores = Score.query.filter_by(student_id=student.id).all()
    official_scores, draft_scores = [], []
    for sc in scores:
        assignment = getattr(sc, "assignment", None)
        locked = bool(getattr(assignment, "is_locked", False))

        if (not sc.is_draft) or locked:
            official_scores.append(sc)
        else:
            draft_scores.append(sc)

    details = ScoreChangeDetail.query.filter_by(student_id=student.id).all()
    pending_details = [
        d for d in details if d.status == ChangeDetailStatusEnum.PENDING
    ]
    request_ids = {d.request_id for d in details}
    requests = []
    if request_ids:
        requests = ScoreChangeRequest.query.filter(
            ScoreChangeRequest.id.in_(request_ids)
        ).all()
    pending_requests = [
        r for r in requests if r.status == ChangeRequestStatusEnum.PENDING
    ]

    blockers = []

    if scores:
        official_n = len(official_scores)
        draft_n = len(draft_scores)
        detail = "%d bản điểm" % len(scores)
        if official_n and draft_n:
            detail += " (%d chính thức đã chốt, %d chưa duyệt)" % (official_n, draft_n)
        elif official_n:
            detail += " (đã chốt)"
        blockers.append({
            "code": "HAS_SCORES",
            "message": "Học sinh đã phát sinh %s — không thể xoá mềm. "
                       "Hãy chuyển sang trạng thái 'Thôi học' hoặc 'Bảo lưu' "
                       "để giữ lại học bạ." % detail,
        })

    current_classes = _active_classes_in_current_academic_year(student.id)
    if current_classes:
        names = ", ".join(current_classes)
        blockers.append({
            "code": "ACTIVE_ENROLLMENT",
            "message": "Học sinh đang học tại lớp %s trong năm học hiện hành — "
                       "phải chuyển sang 'Thôi học' hoặc rút khỏi lớp trước khi xoá."
                       % names,
        })

    if pending_requests:
        blockers.append({
            "code": "PENDING_CHANGE_REQUEST",
            "message": "Còn %d đơn phúc khảo đang chờ duyệt — phải xử lý "
                       "trước khi xoá hồ sơ." % len(pending_requests),
        })
    elif pending_details:
        blockers.append({
            "code": "PENDING_SCORE_CHANGE",
            "message": "Còn %d ô điểm đang chờ xử lý — phải duyệt hoặc từ chối "
                       "trước khi xoá hồ sơ." % len(pending_details),
        })

    return {
        "enrollments": {
            "total": len(enrollments),
            "active": len(active_enrollments),
        },
        "scores": {
            "total": len(scores),
            "official": len(official_scores),
            "draft": len(draft_scores),
        },
        "requests": {
            "total": len(requests),
            "pending": len(pending_requests),
        },
        "blockers": blockers,
    }

def _active_classes_in_current_academic_year(student_id):

    from studentapp.models.academic_year import AcademicYear
    from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum

    year = AcademicYear.query.filter_by(is_current=True).first()
    if year is None:
        return []

    enrollments = ClassEnrollment.query.filter(
        ClassEnrollment.student_id == student_id,
        ClassEnrollment.academic_year_id == year.id,
        ClassEnrollment.status == EnrollmentStatusEnum.DANG_HOC,
    ).all()

    names = []
    for enr in enrollments:
        cls = enr.class_room
        if cls is not None:
            names.append(cls.class_name)
    return names

def check_student_delete(student_id):

    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với ID: %s" % student_id,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )

    info = _collect_student_relations(student)
    blockers = info["blockers"]
    can_soft = not blockers

    return {
        "student_id": int(student_id),
        "student_code": student.student_code,
        "full_name": student.full_name,
        "status": student.status.value if student.status else None,
        "can_soft_delete": can_soft,
        "has_data": bool(
            info["enrollments"]["total"]
            or info["scores"]["total"]
            or info["requests"]["total"]
        ),
        "recommended_mode": DELETE_MODE_SOFT if can_soft else DELETE_MODE_AUTO,
        "blockers": blockers,
        "relations": {
            "enrollments": info["enrollments"],
            "scores": info["scores"],
            "requests": info["requests"],
        },
    }

def delete_student(student_id, payload=None, actor_id=None):

    payload = payload or {}
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise ValidationError("Vui lòng nhập lý do xoá hồ sơ học sinh.")

    mode = str(payload.get("mode") or DELETE_MODE_AUTO).strip().upper()
    if mode not in DELETE_MODES:
        raise ValidationError(
            "Chế độ xoá không hợp lệ. Các giá trị cho phép: %s"
            % ", ".join(DELETE_MODES)
        )

    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với ID: %s" % student_id,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )

    if student.is_deleted:
        raise StudentBusinessError(
            "Hồ sơ học sinh này đã bị xoá mềm trước đó.",
            error_code="STUDENT_ALREADY_DELETED", status_code=409,
        )

    info = _collect_student_relations(student)
    blockers = info["blockers"]
    if blockers:
        raise StudentDeleteBlockedError(
            "Không thể xoá mềm hồ sơ này.",
            blockers=blockers,
            relations=info,
        )

    code = student.student_code
    name = student.full_name

    old_status = student.status
    student.is_deleted = True
    student.deleted_at = datetime.utcnow()
    student.deleted_by = actor_id
    student.deleted_reason = reason

    if old_status == StudentStatusEnum.DANG_HOC:
        student.status = StudentStatusEnum.THOI_HOC
        _sync_enrollment_with_status(student, old_status, StudentStatusEnum.THOI_HOC)

    _write_audit(actor_id, "DELETE_STUDENT_SOFT",
                 {"student_id": int(student_id), "student_code": code,
                  "full_name": name, "reason": reason,
                  "deleted_at": student.deleted_at.isoformat(),
                  "from_status": old_status.value if old_status else None,
                  "to_status": student.status.value})
    db.session.commit()
    return {"student_id": int(student_id), "student_code": code,
            "deleted": True, "mode": DELETE_MODE_SOFT,
            "status": student.status.value, "reason": reason}

def restore_student(student_id, payload=None, actor_id=None):

    payload = payload or {}
    reason = (payload.get("reason") or "").strip()

    student = student_repository.get_by_id_including_deleted(student_id)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với ID: %s" % student_id,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )
    if not student.is_deleted:
        raise StudentBusinessError(
            "Hồ sơ học sinh này chưa bị xoá mềm.",
            error_code="STUDENT_NOT_DELETED", status_code=409,
        )

    student.is_deleted = False
    student.deleted_at = None
    student.deleted_by = None
    student.deleted_reason = None

    _write_audit(actor_id, "RESTORE_STUDENT",
                 {"student_id": int(student_id), "student_code": student.student_code,
                  "full_name": student.full_name, "reason": reason or None})
    db.session.commit()
    return _student_payload(student)

def get_student_print_data(student_id):

    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(
            "Không tìm thấy học sinh với ID: %s" % student_id,
            error_code="STUDENT_NOT_FOUND", status_code=404,
        )

    class_name = None
    grade_name = None
    try:
        from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum

        enr = ClassEnrollment.query.filter_by(
            student_id=student.id, status=EnrollmentStatusEnum.DANG_HOC
        ).order_by(ClassEnrollment.id.desc()).first()
        if enr is not None and enr.class_room is not None:
            class_name = enr.class_room.class_name
            if enr.class_room.grade is not None:
                grade_name = enr.class_room.grade.grade_name
    except Exception:
        pass

    data = _student_payload(student)
    data["class_name"] = class_name
    data["grade_name"] = grade_name
    data["print_date"] = date.today().isoformat()
    return {"student": data, "print_date": date.today().isoformat()}

def build_print_pdf(student_id):

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    payload = get_student_print_data(student_id)
    st = payload["student"]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 20 * mm

    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(w / 2, y, "HO SO HOC SINH")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, "Ngay in: %s" % payload["print_date"])
    y -= 6 * mm

    def line(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(55 * mm, y, str(value if value not in (None, "") else "-"))
        y -= 6 * mm

    line("Ma hoc sinh:", st.get("student_code"))
    line("Ho va ten:", st.get("full_name"))
    line("Gioi tinh:", st.get("gender"))
    line("Ngay sinh:", st.get("date_of_birth"))
    line("Tuoi:", st.get("calculated_age"))
    line("Lop:", st.get("class_name") or st.get("grade_name"))
    line("Dia chi:", st.get("address"))
    line("So dien thoai:", st.get("phone"))
    line("Email:", st.get("email"))
    line("So CCCD:", st.get("citizen_id"))
    line("Phu huynh:", st.get("parent_name"))
    line("SDT phu huynh:", st.get("parent_phone"))
    line("Trang thai:", st.get("status"))

    y -= 4 * mm
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(20 * mm, y, "Trang thai: DANG_HOC / THOI_HOC")

    c.showPage()
    c.save()
    return buf.getvalue()

def build_class_export_excel(class_id):

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    from studentapp.models.class_room import Class

    cls = db.session.get(Class, class_id)
    if cls is None:
        raise NotFoundError("Không tìm thấy lớp học.")

    rows = ClassService_students_in_class(class_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Danh sach lop"
    ws.append(["DANH SACH HOC SINH LOP %s" % cls.class_name])
    ws.append(["Khoi:", cls.grade.grade_name if cls.grade else "",
               "Nam hoc:", cls.academic_year.year_name if cls.academic_year else "",
               "Si so:", cls.current_size])
    ws.append(["STT", "Ma hoc sinh", "Ho ten", "Ngay sinh", "Gioi tinh",
               "Email", "So dien thoai", "Trang thai"])
    for i, st in enumerate(rows, start=1):
        ws.append([i, st.get("student_code"), st.get("full_name"),
                   st.get("date_of_birth"), st.get("gender"), st.get("email"),
                   st.get("phone"), st.get("status")])
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
    ws["A1"].font = Font(bold=True, size=13)
    for col, width in zip("ABCDEFGH", (8, 16, 26, 14, 12, 26, 16, 14)):
        ws.column_dimensions[col].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def build_class_export_pdf(class_id):

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    from studentapp.models.class_room import Class

    cls = db.session.get(Class, class_id)
    if cls is None:
        raise NotFoundError("Không tìm thấy lớp học.")

    rows = ClassService_students_in_class(class_id)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 18 * mm

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, y, "DANH SACH HOC SINH LOP %s" % cls.class_name)
    y -= 7 * mm
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, y, "Si so: %d" % cls.current_size)
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 9)
    headers = [("STT", 15), ("Ma HS", 32), ("Ho ten", 62), ("Ngay sinh", 118), ("Trang thai", 155)]
    for text, x in headers:
        c.drawString(x * mm, y, text)
    y -= 2 * mm
    c.line(15 * mm, y, 190 * mm, y)
    y -= 6 * mm

    c.setFont("Helvetica", 9)
    for i, st in enumerate(rows, start=1):
        if y < 20 * mm:
            c.showPage()
            y = h - 20 * mm
        c.drawString(15 * mm, y, str(i))
        c.drawString(32 * mm, y, str(st.get("student_code") or "")[:14])
        c.drawString(62 * mm, y, str(st.get("full_name") or "")[:26])
        c.drawString(118 * mm, y, str(st.get("date_of_birth") or ""))
        c.drawString(155 * mm, y, str(st.get("status") or ""))
        y -= 6 * mm

    c.showPage()
    c.save()
    return buf.getvalue()

def ClassService_students_in_class(class_id):

    from studentapp.models.class_enrollment import ClassEnrollment, EnrollmentStatusEnum

    enrollments = ClassEnrollment.query.filter_by(
        class_id=class_id, status=EnrollmentStatusEnum.DANG_HOC
    ).all()

    return [
        e.student.to_dict()
        for e in enrollments
        if e.student is not None and not e.student.is_deleted
    ]
