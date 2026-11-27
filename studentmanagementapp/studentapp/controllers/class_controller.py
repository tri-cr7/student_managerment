import io

from flask import Blueprint, jsonify, request, send_file

from studentapp.exceptions import AppError
from studentapp.services.class_service import ClassService
from studentapp.services import student_service
from studentapp.utils.decorators import role_required, current_actor_id

bp = Blueprint("classes", __name__, url_prefix="/api/v1")

def _actor_id():

    return current_actor_id()

def _err(e):

    payload = {
        "success": False,
        "error": getattr(e, "error", "BAD_REQUEST"),
        "message": str(getattr(e, "message", None) or e),
    }
    if payload["error"] == "CLASS_SIZE_EXCEEDED":
        payload["current_size"] = getattr(e, "current_size", None)
        payload["max_size"] = getattr(e, "max_size", None)
    return jsonify(payload), getattr(e, "status_code", 400)

def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status

@bp.post("/classes")
@role_required("STAFF", "ACADEMIC")
def create_class():

    payload = request.get_json(silent=True) or {}
    new_class = ClassService.create_class(payload)
    return jsonify({"success": True, "message": "Tạo lớp thành công.", "data": new_class.to_dict()}), 201

@bp.put("/classes/<int:class_id>")
@role_required("STAFF", "ACADEMIC")
def update_class(class_id):

    payload = request.get_json(silent=True) or {}
    payload["actor_id"] = _actor_id()
    try:
        updated = ClassService.update_class(class_id, payload)
    except AppError as e:
        return _err(e)
    return jsonify({"success": True, "message": "Cập nhật lớp thành công.", "data": updated.to_dict()}), 200

@bp.delete("/classes/<int:class_id>")
@role_required("ACADEMIC")
def delete_class(class_id):

    ClassService.delete_class(class_id)
    return jsonify({"success": True, "message": "Xóa lớp học thành công."}), 200

@bp.post("/classes/<int:class_id>/enroll")
@role_required("STAFF")
def enroll_student(class_id):

    payload = request.get_json(silent=True) or {}
    try:
        result = ClassService.enroll_student(class_id, payload)
    except AppError as e:
        return _err(e)
    msg = "Phân bổ %d học sinh vào lớp %s thành công" % (
        result.get("enrolled_count", 0), result.get("class_name") or class_id)
    return jsonify({
        "success": True,
        "message": msg,
        "class_id": result.get("class_id"),
        "enrolled_count": result.get("enrolled_count"),
        "new_current_size": result.get("new_current_size"),
        "data": result,
    }), 200

@bp.post("/classes/transfer")
@role_required("STAFF", "ACADEMIC")
def transfer_student():

    payload = request.get_json(silent=True) or {}
    payload["actor_id"] = _actor_id()
    try:
        result = ClassService.transfer_student(payload)
    except AppError as e:
        return _err(e)
    return jsonify({
        "success": True,
        "message": "Điều chuyển học sinh thành công",
        "student_id": result.get("student_id"),
        "from_class": result.get("from_class"),
        "to_class": result.get("to_class"),
        "from_class_new_size": result.get("from_class_new_size"),
        "to_class_new_size": result.get("to_class_new_size"),
        "data": result,
    }), 200

@bp.get("/classes/<int:class_id>/export")
@role_required("STAFF", "ACADEMIC")
def export_class(class_id):

    fmt = (request.args.get("format") or "excel").strip().lower()
    if fmt == "pdf":
        payload = student_service.build_class_export_pdf(class_id)
        mimetype = "application/pdf"
        filename = "danh-sach-lop-%d.pdf" % class_id
    else:
        payload = student_service.build_class_export_excel(class_id)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "danh-sach-lop-%d.xlsx" % class_id
    return send_file(io.BytesIO(payload), mimetype=mimetype,
                     as_attachment=True, download_name=filename)
