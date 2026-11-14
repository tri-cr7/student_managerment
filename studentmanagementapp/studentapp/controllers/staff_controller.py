"""CONTROLLER staff — API cho Nhân viên (module quản lý học sinh & tiếp nhận hồ sơ).

Nhóm endpoints:
- GET  /api/v1/students                    — SD03/SD07: Danh sách học sinh (phân trang, tìm kiếm)
- GET  /api/v1/students/<id>               — Chi tiết hồ sơ một học sinh
- GET  /api/v1/students/code/<code >       — Tra cứu theo mã học sinh
- POST /api/v1/students/admit              — SD03: Tiếp nhận học sinh mới (tuổi 15-20)
- PUT  /api/v1/students/<id>               — SD07: Cập nhật thông tin học sinh
- PATCH /api/v1/students/<id>/status       — Cập nhật trạng thái học tập (Đang học, Thôi học, v.v.)
- POST /api/v1/students/import-excel       — SD04: Import danh sách học sinh từ Excel/CSV
- GET  /api/v1/students/<id>/print         — SD08: Xuất dữ liệu in hồ sơ học sinh chuẩn biểu mẫu
"""
from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from studentapp.exceptions import AppError
from studentapp.services import student_service
from studentapp.utils.decorators import staff_required

# url_prefix changed to "/api/v1" so it registers cleanly under /api/v1/students/...
bp = Blueprint("staff", __name__, url_prefix="/api/v1")


def _err(e: AppError):
    payload = {"success": False, "error": e.error, "message": e.message}
    return jsonify(payload), e.status_code


def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _actor_id():
    """Lấy ID người dùng hiện tại từ JWT (fallback session)."""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity is not None:
            return int(identity)
    except Exception:
        pass
    from flask_login import current_user

    try:
        if current_user.is_authenticated:
            return int(current_user.id)
    except Exception:
        pass
    return None



@bp.get("/students/form")
@staff_required
def render_admission_form():
    """Giao diện HTML form tiếp nhận học sinh."""
    return render_template('admit.html')

@bp.get("/students/ui")
@staff_required
def render_student_ui():
    """Giao diện HTML quản lý học sinh (UI)."""
    return render_template('student.html')


# --------------------------------------------------------------------------- #
# Quản lý & Tra cứu học sinh (Route 13, 14, 15)
# --------------------------------------------------------------------------- #

@bp.get("/students")
@staff_required
def list_students():
    """Danh sách học sinh phân trang và tìm kiếm đa tiêu chí."""
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        keyword = request.args.get("q", "")

        data = student_service.list_students(page=page, limit=limit, keyword=keyword)
        return _ok(data, "Danh sách học sinh.")
    except AppError as e:
        return _err(e)



@bp.get("/students/<int:student_id>")
@staff_required
def get_student_detail(student_id):
    """Lấy chi tiết hồ sơ một học sinh theo ID."""
    try:
        data = student_service.get_student_detail(student_id)
        return _ok(data, "Lấy chi tiết hồ sơ học sinh thành công.")
    except AppError as e:
        return _err(e)


@bp.get("/students/code/<string:student_code>")
@staff_required
def get_student_by_code(student_code):
    """Tra cứu học sinh theo mã định danh duy nhất (SD08)."""
    try:
        data = student_service.get_student_by_code(student_code)
        return _ok(data, "Tra cứu học sinh thành công.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD03 — Tiếp nhận học sinh mới
# --------------------------------------------------------------------------- #

@bp.post("/students/admit")
@staff_required
def admit_student():
    """Tiếp nhận học sinh mới, kiểm tra điều kiện tuổi 15-20 (SD03)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.admit_student(payload, actor_id=_actor_id())
        return _ok(data, "Tiếp nhận học sinh mới thành công.", 201)
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD07 — Cập nhật thông tin học sinh
# --------------------------------------------------------------------------- #

@bp.put("/students/<int:student_id>")
@staff_required
def update_student(student_id):
    """Cập nhật thông tin hồ sơ học sinh (SD07)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.update_student(student_id, payload, actor_id=_actor_id())
        return _ok(data, "Cập nhật thông tin học sinh thành công.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# Cập nhật trạng thái học tập
# --------------------------------------------------------------------------- #

@bp.patch("/students/<int:student_id>/status")
@staff_required
def update_student_status(student_id):
    """Cập nhật trạng thái học tập (Đang học, Thôi học, Chuyển trường)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.update_student_status(student_id, payload, actor_id=_actor_id())
        return _ok(data, "Cập nhật trạng thái học tập thành công.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD04 — Import danh sách học sinh từ Excel/CSV
# --------------------------------------------------------------------------- #

@bp.post("/students/import-excel")
@staff_required
def import_excel():
    """Import danh sách học sinh từ file Excel hoặc CSV (SD04)."""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "MISSING_FILE", "message": "Không tìm thấy file tải lên."}), 400

        file_obj = request.files['file']
        data = student_service.import_students_from_excel(file_obj, actor_id=_actor_id())
        return _ok(data, "Import danh sách học sinh thành công.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD08 — Xuất dữ liệu in hồ sơ
# --------------------------------------------------------------------------- #

@bp.get("/students/<int:student_id>/print")
@staff_required
def print_student_profile(student_id):
    """Xuất dữ liệu in hồ sơ học sinh chuẩn biểu mẫu (SD08)."""
    try:
        data = student_service.get_student_print_data(student_id)
        return render_template('students/print_profile.html', student=data)
    except AppError as e:
        return _err(e)

