from studentapp.exceptions import AppError
from studentapp.extensions import db
from studentapp.models.academic_year import AcademicYear
from studentapp.models.semester import Semester


def list_academic_years():
    years = AcademicYear.query.order_by(AcademicYear.start_year.desc(), AcademicYear.id.desc()).all()
    return [y.to_dict() for y in years]


def get_current_academic_year():
    year = AcademicYear.query.filter_by(is_current=True).first()
    if not year:
        raise AppError(
            "Chưa thiết lập niên khóa hiện hành.",
            error="NO_CURRENT_ACADEMIC_YEAR",
            status_code=404,
        )
    return year.to_dict()


def create_academic_year(payload):
    payload = payload or {}
    year_name = (payload.get("year_name") or "").strip()
    start_year = payload.get("start_year")
    end_year = payload.get("end_year")
    is_current = bool(payload.get("is_current", False))

    if not year_name or start_year is None or end_year is None:
        raise AppError(
            "Thiếu thông tin bắt buộc (year_name, start_year, end_year).",
            error="MISSING_FIELDS",
            status_code=400,
        )

    try:
        start_year = int(start_year)
        end_year = int(end_year)
    except (TypeError, ValueError):
        raise AppError(
            "start_year và end_year phải là số nguyên.",
            error="INVALID_YEAR_FORMAT",
            status_code=400,
        )

    if end_year < start_year:
        raise AppError(
            "end_year không được nhỏ hơn start_year.",
            error="INVALID_YEAR_RANGE",
            status_code=400,
        )

    existing = AcademicYear.query.filter_by(year_name=year_name).first()
    if existing:
        raise AppError(
            f"Niên khóa '{year_name}' đã tồn tại.",
            error="DUPLICATE_ACADEMIC_YEAR",
            status_code=409,
        )

    if is_current:
        AcademicYear.query.filter_by(is_current=True).update({"is_current": False})

    new_year = AcademicYear(
        year_name=year_name,
        start_year=start_year,
        end_year=end_year,
        is_current=is_current,
    )
    db.session.add(new_year)
    db.session.commit()
    return new_year.to_dict()


def list_semesters(academic_year_id=None):
    query = Semester.query
    if academic_year_id is not None:
        query = query.filter_by(academic_year_id=academic_year_id)
    semesters = query.order_by(Semester.id.asc()).all()
    return [s.to_dict() for s in semesters]


def get_current_semester(academic_year_id=None):
    query = Semester.query.filter_by(is_current=True)
    if academic_year_id is not None:
        query = query.filter_by(academic_year_id=academic_year_id)
    semester = query.first()
    if not semester:
        raise AppError(
            "Chưa thiết lập học kỳ hiện hành.",
            error="NO_CURRENT_SEMESTER",
            status_code=404,
        )
    return semester.to_dict()