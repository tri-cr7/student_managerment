import io

from flask import Blueprint, jsonify, request, send_file

from studentapp.exceptions import AppError
from studentapp.models.user import UserRoleEnum
from studentapp.services import student_service
from studentapp.utils.decorators import staff_required, role_required, current_actor_id

bp = Blueprint("staff", __name__, url_prefix="/api/v1")

def _err(e: AppError):
    payload = {"success": False, "error": e.error, "message": e.message}

    current_rules = getattr(e, "current_rules", None)
    if current_rules:
        payload["current_rules"] = current_rules

    blockers = getattr(e, "blockers", None)
    if blockers:
        payload["blockers"] = blockers
    relations = getattr(e, "relations", None)
    if relations:
        payload["relations"] = relations
    return jsonify(payload), e.status_code

def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status

def _actor_id():

    return current_actor_id()

def _actor_role():

    from studentapp.utils.decorators import _current_role

    role, _user = _current_role()
    return role if role in (UserRoleEnum.STAFF, UserRoleEnum.TEACHER,
                             UserRoleEnum.ACADEMIC) else None

@bp.get("/students")
@role_required("STAFF", "ACADEMIC")
def list_students():

    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        keyword = request.args.get("q", "")
        class_id = request.args.get("class_id")
        status = request.args.get("status")
        academic_year_id = request.args.get("academic_year_id")

        include_deleted = request.args.get("include_deleted", "false").lower() in (
            "1", "true", "yes",
        )

        data = student_service.list_students(
            page=page, limit=limit, keyword=keyword,
            class_id=class_id, status=status,
            academic_year_id=academic_year_id,
            include_deleted=include_deleted,
        )
        return _ok(data, "Danh sách học sinh.")
    except AppError as e:
        return _err(e)

@bp.get("/students/<int:student_id>")
@role_required("STAFF", "TEACHER", "ACADEMIC")
def get_student_detail(student_id):

    try:
        role = _actor_role()

        is_teacher = (role == UserRoleEnum.TEACHER)
        data = student_service.get_student_detail(
            student_id,
            teacher_id=_actor_id() if is_teacher else None,
            is_academic=not is_teacher,
        )
        return _ok(data, "Lấy chi tiết hồ sơ học sinh thành công.")
    except AppError as e:
        return _err(e)

@bp.get("/students/code/<string:student_code>")
@role_required("STAFF", "TEACHER", "ACADEMIC")
def get_student_by_code(student_code):

    try:
        role = _actor_role()
        is_teacher = (role == UserRoleEnum.TEACHER)
        data = student_service.get_student_by_code(
            student_code,
            teacher_id=_actor_id() if is_teacher else None,
            is_academic=not is_teacher,
        )
        return _ok(data, "Tra cứu học sinh thành công.")
    except AppError as e:
        return _err(e)

@bp.post("/students/admit")
@staff_required
def admit_student():

    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.admit_student(payload, actor_id=_actor_id())
        return _ok(data, "Tiếp nhận học sinh mới thành công.", 201)
    except AppError as e:
        return _err(e)

@bp.put("/students/<int:student_id>")
@staff_required
def update_student(student_id):

    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.update_student(student_id, payload, actor_id=_actor_id())
        return _ok(data, "Cập nhật thông tin học sinh thành công.")
    except AppError as e:
        return _err(e)

@bp.get("/students/<int:student_id>/delete-check")
@role_required("STAFF", "ACADEMIC")
def check_delete_student(student_id):

    try:
        data = student_service.check_student_delete(student_id)
        return _ok(data, "Kiểm tra điều kiện xoá hồ sơ thành công.")
    except AppError as e:
        return _err(e)

@bp.delete("/students/<int:student_id>")
@role_required("STAFF", "ACADEMIC")
def delete_student(student_id):

    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.delete_student(student_id, payload, actor_id=_actor_id())
        return _ok(data, "Đã xoá mềm hồ sơ học sinh.")
    except AppError as e:
        return _err(e)

@bp.post("/students/<int:student_id>/restore")
@role_required("ACADEMIC")
def restore_student(student_id):

    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.restore_student(student_id, payload, actor_id=_actor_id())
        return _ok(data, "Đã khôi phục hồ sơ học sinh.")
    except AppError as e:
        return _err(e)

@bp.patch("/students/<int:student_id>/status")
@role_required("STAFF", "ACADEMIC")
def update_student_status(student_id):

    try:
        payload = request.get_json(silent=True) or {}
        data = student_service.update_student_status(student_id, payload, actor_id=_actor_id())
        return _ok(data, "Cập nhật trạng thái học tập thành công.")
    except AppError as e:
        return _err(e)

@bp.post("/students/import-excel")
@staff_required
def import_excel():

    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "MISSING_FILE",
                "message": "Không tìm thấy file tải lên.",
            }), 400

        file_obj = request.files['file']
        data = student_service.import_students_from_excel(file_obj, actor_id=_actor_id())
        return _ok(
            data,
            "Import danh sách học sinh hoàn tất: %d/%d dòng hợp lệ."
            % (data.get("success_count", 0), data.get("total_rows", 0)),
        )
    except AppError as e:
        return _err(e)

@bp.get("/students/<int:student_id>/print")
@role_required("STAFF", "ACADEMIC")
def print_student_profile(student_id):

    try:
        fmt = (request.args.get("format") or "json").strip().lower()

        if fmt == "pdf":
            pdf_bytes = student_service.build_print_pdf(student_id)
            return send_file(
                io.BytesIO(pdf_bytes),
                mimetype="application/pdf",
                as_attachment=True,
                download_name="ho-so-hoc-sinh-%d.pdf" % student_id,
            )

        data = student_service.get_student_print_data(student_id)
        return _ok(data, "Dữ liệu in hồ sơ học sinh.")
    except AppError as e:
        return _err(e)
