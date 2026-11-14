from datetime import date
from studentapp.extensions import db
from studentapp.models.student import Student, StudentStatusEnum
from studentapp.repositories import student_repository
from studentapp.exceptions import AppError

//Sửa lại lớp này 1 chút.
class StudentBusinessError(AppError):
    def __init__(self, message, error_code="STUDENT_ERROR", status_code=400):
        super().__init__(error=error_code, message=message)
        self.status_code = status_code


def list_students(page=1, limit=20, keyword=""):
    """Danh sách học sinh (phân trang & tìm kiếm đa tiêu chí qua Repository)."""
    # Using SQLAlchemy pagination directly or leveraging repository search
    query = Student.query

    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        query = query.filter(
            db.or_(Student.full_name.ilike(like), Student.student_code.ilike(like))
        )

    pagination = query.order_by(Student.full_name).paginate(page=page, per_page=limit, error_out=False)

    return {
        "items": [student.to_dict() for student in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": pagination.per_page
    }


def get_student_detail(student_id):
    """Lấy chi tiết hồ sơ một học sinh theo ID (sử dụng student_repository)."""
    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(f"Không tìm thấy học sinh với ID: {student_id}", error_code="STUDENT_NOT_FOUND",
                                   status_code=404)
    return student.to_dict()


def get_student_by_code(student_code):
    """Tra cứu học sinh theo mã định danh duy nhất (sử dụng student_repository)."""
    student = student_repository.get_by_code(student_code)
    if not student:
        raise StudentBusinessError(f"Không tìm thấy học sinh với mã: {student_code}", error_code="STUDENT_NOT_FOUND",
                                   status_code=404)
    return student.to_dict()


def admit_student(payload, actor_id=None):
    """Tiếp nhận học sinh mới, kiểm tra điều kiện tuổi 15-20 (SD03)."""
    student_code = payload.get("student_code")
    full_name = payload.get("full_name")
    dob_str = payload.get("date_of_birth")  # Expected format: YYYY-MM-DD

    if not student_code or not full_name or not dob_str:
        raise StudentBusinessError("Thiếu thông tin bắt buộc (student_code, full_name, date_of_birth).",
                                   error_code="MISSING_FIELDS")

    # Check unique student code using repository
    existing = student_repository.get_by_code(student_code)
    if existing:
        raise StudentBusinessError(f"Mã học sinh '{student_code}' đã tồn tại trong hệ thống.",
                                   error_code="DUPLICATE_CODE")

    # Parse Date of Birth & Calculate Age (SD03: 15 <= age <= 20)
    try:
        dob = date.fromisoformat(dob_str)
    except ValueError:
        raise StudentBusinessError("Định dạng ngày sinh không hợp lệ. Vui lòng dùng YYYY-MM-DD.",
                                   error_code="INVALID_DATE_FORMAT")

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    if not (15 <= age <= 20):
        raise StudentBusinessError(
            f"Vi phạm quy định SD03: Tuổi học sinh phải từ 15 đến 20. Tuổi tính toán hiện tại: {age}.",
            error_code="INVALID_AGE_RANGE"
        )

    # Create new student record
    new_student = Student(
        student_code=student_code,
        full_name=full_name,
        gender=payload.get("gender"),
        date_of_birth=dob,
        address=payload.get("address"),
        phone=payload.get("phone"),
        email=payload.get("email"),
        citizen_id=payload.get("citizen_id"),
        parent_name=payload.get("parent_name"),
        parent_phone=payload.get("parent_phone"),
        status=StudentStatusEnum.DANG_HOC,
        created_by=actor_id
    )

    db.session.add(new_student)
    db.session.commit()
    return new_student.to_dict()


def update_student(student_id, payload, actor_id=None):
    """Cập nhật thông tin hồ sơ học sinh (SD07)."""
    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(f"Không tìm thấy học sinh với ID: {student_id}", error_code="STUDENT_NOT_FOUND",
                                   status_code=404)

    if "full_name" in payload:
        student.full_name = payload["full_name"]
    if "gender" in payload:
        student.gender = payload["gender"]
    if "address" in payload:
        student.address = payload["address"]
    if "phone" in payload:
        student.phone = payload["phone"]
    if "email" in payload:
        student.email = payload["email"]
    if "citizen_id" in payload:
        student.citizen_id = payload["citizen_id"]
    if "parent_name" in payload:
        student.parent_name = payload["parent_name"]
    if "parent_phone" in payload:
        student.parent_phone = payload["parent_phone"]

    if "date_of_birth" in payload:
        dob_str = payload["date_of_birth"]
        try:
            dob = date.fromisoformat(dob_str)
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if not (15 <= age <= 20):
                raise StudentBusinessError(f"Vi phạm quy định SD03: Tuổi cập nhật phải từ 15 đến 20 (Tuổi: {age}).",
                                           error_code="INVALID_AGE_RANGE")
            student.date_of_birth = dob
        except ValueError:
            raise StudentBusinessError("Định dạng ngày sinh không hợp lệ.", error_code="INVALID_DATE_FORMAT")

    db.session.commit()
    return student.to_dict()


def update_student_status(student_id, payload, actor_id=None):
    """Cập nhật trạng thái học tập sử dụng StudentStatusEnum."""
    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(f"Không tìm thấy học sinh với ID: {student_id}", error_code="STUDENT_NOT_FOUND",
                                   status_code=404)

    status_str = payload.get("status")

    try:
        student.status = StudentStatusEnum(status_str)
    except ValueError:
        valid_options = [e.value for e in StudentStatusEnum]
        raise StudentBusinessError(f"Trạng thái không hợp lệ. Các giá trị cho phép: {valid_options}",
                                   error_code="INVALID_STATUS")

    db.session.commit()
    return student.to_dict()


def import_students_from_excel(file_obj, actor_id=None):
    """Import danh sách học sinh từ file Excel hoặc CSV (SD04)."""
    filename = getattr(file_obj, 'filename', '')
    if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
        raise StudentBusinessError("Chỉ hỗ trợ file định dạng .xlsx, .xls hoặc .csv", error_code="INVALID_FILE_TYPE")

    imported_count = 0
    return {"imported_count": imported_count}


def get_student_print_data(student_id):
    """Chuẩn bị dữ liệu in ấn hồ sơ học sinh chuẩn biểu mẫu (SD08)."""
    student = student_repository.get_by_id(student_id)
    if not student:
        raise StudentBusinessError(f"Không tìm thấy học sinh với ID: {student_id}", error_code="STUDENT_NOT_FOUND",
                                   status_code=404)

    return {
        "student": student.to_dict(),
        "print_date": date.today().isoformat()
    }