"""CONTROLLER classes — Quản lý Khối lớp, Lớp học và Phân bổ học sinh."""
from flask import Blueprint, jsonify, request
from flask_login import login_required

from studentapp.services.class_service import ClassService
from studentapp.utils.decorators import role_required

bp = Blueprint("classes", __name__, url_prefix="/api/v1") # or your project's prefix

def _err(e):
    return jsonify({"success": False, "message": str(e)}, getattr(e, "status_code", 400))

def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


@bp.post("/classes")
@role_required("STAFF", "ACADEMIC")
def create_class():
    """Item 26: Tạo mới một lớp học theo khối."""
    payload = request.get_json(silent=True) or {}
    new_class = ClassService.create_class(payload)
    return jsonify({"success": True, "message": "Tạo lớp thành công.", "data": new_class.to_dict()}), 201

@bp.put("/classes/<int:class_id>")
@role_required("STAFF", "ACADEMIC")
def update_class(class_id):
    """Item 27: Chỉnh sửa tên lớp, GV chủ nhiệm."""
    payload = request.get_json(silent=True) or {}
    updated = ClassService.update_class(class_id, payload)
    return jsonify({"success": True, "message": "Cập nhật lớp thành công.", "data": updated.to_dict()}), 200

@bp.delete("/classes/<int:class_id>")
@role_required("ACADEMIC")
def delete_class(class_id):
    """Item 28: Xóa lớp học (chỉ khi lớp chưa có học sinh)."""
    ClassService.delete_class(class_id)
    return jsonify({"success": True, "message": "Xóa lớp học thành công."}), 200

@bp.post("/classes/<int:class_id>/enroll")
@role_required("STAFF")
def enroll_student(class_id):
    """Item 30: Phân bổ học sinh vào lớp, kiểm tra sĩ số <= 40 (SD05)."""
    payload = request.get_json(silent=True) or {}
    result = ClassService.enroll_student(class_id, payload)
    return jsonify({"success": True, "message": "Phân bổ học sinh thành công.", "data": result}), 200

@bp.post("/classes/transfer")
@role_required("STAFF")
def transfer_student():
    """Item 31: Điều chuyển học sinh từ Lớp A sang Lớp B (SD06)."""
    payload = request.get_json(silent=True) or {}
    result = ClassService.transfer_student(payload)
    return jsonify({"success": True, "message": "Điều chuyển học sinh thành công.", "data": result}), 200