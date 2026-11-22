from flask import Blueprint, jsonify, request

from studentapp.exceptions import AppError
from studentapp.services import semesters_service
from studentapp.utils.decorators import role_required

bp = Blueprint("semesters", __name__, url_prefix="/api/v1")


def _err(e: AppError):
    return jsonify({"success": False, "error": e.error, "message": e.message}), e.status_code


def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


# #33 — GET /api/v1/academic-years
@bp.get("/academic-years")
def list_academic_years():
    try:
        data = semesters_service.list_academic_years()
        return _ok(data, "Danh sách niên khóa.")
    except AppError as e:
        return _err(e)


# #34 — POST /api/v1/academic-years
@bp.post("/academic-years")
@role_required("ACADEMIC")
def create_academic_year():
    try:
        payload = request.get_json(silent=True) or {}
        data = semesters_service.create_academic_year(payload)
        return _ok(data, "Tạo niên khóa mới thành công.", 201)
    except AppError as e:
        return _err(e)


# #35 — GET /api/v1/academic-years/current
@bp.get("/academic-years/current")
def get_current_academic_year():
    try:
        data = semesters_service.get_current_academic_year()
        return _ok(data, "Niên khóa hiện hành.")
    except AppError as e:
        return _err(e)


# #36 — GET /api/v1/semesters
@bp.get("/semesters")
def list_semesters():
    try:
        academic_year_id = request.args.get("academic_year_id", type=int)
        data = semesters_service.list_semesters(academic_year_id=academic_year_id)
        return _ok(data, "Danh sách học kỳ.")
    except AppError as e:
        return _err(e)


# #37 — GET /api/v1/semesters/current
@bp.get("/semesters/current")
def get_current_semester():
    try:
        academic_year_id = request.args.get("academic_year_id", type=int)
        data = semesters_service.get_current_semester(academic_year_id=academic_year_id)
        return _ok(data, "Học kỳ hiện hành.")
    except AppError as e:
        return _err(e)