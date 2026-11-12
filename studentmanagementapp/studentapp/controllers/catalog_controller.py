"""CONTROLLER catalog — SD21 rules, SD22 subjects, SD26 years/semesters, SD27 GVCN.

Thứ tự khai báo route tĩnh trước route /{id} để Flask không nuốt.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from studentapp.exceptions import AppError
from studentapp.services import catalog_service
from studentapp.utils.decorators import admin_required, login_required_any

bp = Blueprint("catalog", __name__, url_prefix="/api/v1")


def _err(e: AppError):
    return jsonify({"error": e.error, "message": e.message}), e.status_code


def _ok(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def _actor_id():
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


# --------------------------------------------------------------------------- #
# SD21 — Quy định
# --------------------------------------------------------------------------- #

@bp.get("/rules")
@login_required_any
def list_rules():
    try:
        return _ok(catalog_service.list_rules(), "Danh sách quy định.")
    except AppError as e:
        return _err(e)


@bp.put("/rules/bulk")
@admin_required
def bulk_rules():
    try:
        payload = request.get_json(silent=True) or {}
        data = catalog_service.bulk_update_rules(
            payload.get("rules"), actor_id=_actor_id())
        return _ok(data, f"Đã cập nhật {len(data['updated'])} quy định.")
    except AppError as e:
        return _err(e)


@bp.get("/rules/<rule_key>")
@login_required_any
def get_rule(rule_key):
    try:
        return _ok(catalog_service.get_rule(rule_key.strip().upper()),
                    "Chi tiết quy định.")
    except AppError as e:
        return _err(e)


@bp.put("/rules/<rule_key>")
@admin_required
def update_rule(rule_key):
    try:
        payload = request.get_json(silent=True) or {}
        data = catalog_service.update_rule(
            rule_key.strip().upper(), payload.get("rule_value"),
            description=payload.get("description"), actor_id=_actor_id())
        return _ok(data, "Cập nhật quy định thành công.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD22 — Môn học (route tĩnh /grade/* trước /<id>)
# --------------------------------------------------------------------------- #

@bp.get("/subjects")
@login_required_any
def list_subjects():
    try:
        data = catalog_service.list_subjects(
            keyword=request.args.get("keyword"),
            grade_id=request.args.get("grade_id"),
            is_active=request.args.get("is_active"))
        return _ok(data, "Danh sách môn học.")
    except AppError as e:
        return _err(e)


@bp.get("/subjects/grade/<grade_id>")
@login_required_any
def subjects_by_grade(grade_id):
    try:
        data = catalog_service.list_subjects_by_grade(
            grade_id, is_active=request.args.get("is_active"))
        return _ok(data, "Danh sách môn học theo khối.")
    except AppError as e:
        return _err(e)


@bp.get("/subjects/<int:subject_id>")
@login_required_any
def get_subject(subject_id):
    try:
        return _ok(catalog_service.get_subject(subject_id), "Chi tiết môn học.")
    except AppError as e:
        return _err(e)


@bp.post("/subjects")
@admin_required
def create_subject():
    try:
        payload = request.get_json(silent=True) or {}
        data = catalog_service.create_subject(payload, actor_id=_actor_id())
        return _ok(data, "Thêm môn học mới thành công.", 201)
    except AppError as e:
        return _err(e)


@bp.put("/subjects/<int:subject_id>")
@admin_required
def update_subject(subject_id):
    try:
        payload = request.get_json(silent=True) or {}
        data = catalog_service.update_subject(subject_id, payload,
                                              actor_id=_actor_id())
        return _ok(data, "Cập nhật môn học thành công.")
    except AppError as e:
        return _err(e)


@bp.delete("/subjects/<int:subject_id>")
@admin_required
def delete_subject(subject_id):
    try:
        data = catalog_service.delete_subject(subject_id, actor_id=_actor_id())
        return _ok(data, "Đã xóa môn học.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD26 — Năm học & học kỳ (route tĩnh /current trước /<id>)
# --------------------------------------------------------------------------- #

@bp.get("/academic-years")
@login_required_any
def list_years():
    try:
        return _ok(catalog_service.list_academic_years(), "Danh sách năm học.")
    except AppError as e:
        return _err(e)


@bp.get("/academic-years/current")
@login_required_any
def current_year():
    try:
        return _ok(catalog_service.get_current_year(), "Năm học hiện hành.")
    except AppError as e:
        return _err(e)


@bp.post("/academic-years")
@admin_required
def create_year():
    try:
        payload = request.get_json(silent=True) or {}
        data = catalog_service.create_academic_year(payload, actor_id=_actor_id())
        return _ok(data, "Tạo năm học thành công.", 201)
    except AppError as e:
        return _err(e)


@bp.put("/academic-years/<int:year_id>/current")
@admin_required
def set_current_year(year_id):
    try:
        data = catalog_service.set_current_year(year_id, actor_id=_actor_id())
        return _ok(data, "Đã đặt năm học hiện hành.")
    except AppError as e:
        return _err(e)


@bp.get("/semesters")
@login_required_any
def list_semesters():
    try:
        data = catalog_service.list_semesters(
            academic_year_id=request.args.get("academic_year_id"))
        return _ok(data, "Danh sách học kỳ.")
    except AppError as e:
        return _err(e)


@bp.get("/semesters/current")
@login_required_any
def current_semester():
    try:
        return _ok(catalog_service.get_current_semester(), "Học kỳ hiện hành.")
    except AppError as e:
        return _err(e)


@bp.post("/semesters")
@admin_required
def create_semester():
    try:
        payload = request.get_json(silent=True) or {}
        data = catalog_service.create_semester(payload, actor_id=_actor_id())
        return _ok(data, "Tạo học kỳ thành công.", 201)
    except AppError as e:
        return _err(e)


@bp.put("/semesters/<int:semester_id>/current")
@admin_required
def set_current_semester(semester_id):
    try:
        data = catalog_service.set_current_semester(semester_id,
                                                    actor_id=_actor_id())
        return _ok(data, "Đã đặt học kỳ hiện hành.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD27 + danh mục grades/classes
# --------------------------------------------------------------------------- #

@bp.get("/grades")
@login_required_any
def list_grades():
    try:
        return _ok(catalog_service.list_grades(), "Danh sách khối lớp.")
    except AppError as e:
        return _err(e)


@bp.get("/grades/<grade_id>/classes")
@login_required_any
def classes_by_grade(grade_id):
    try:
        data = catalog_service.list_classes_by_grade(grade_id)
        return _ok(data, "Danh sách lớp thuộc khối.")
    except AppError as e:
        return _err(e)


@bp.get("/classes")
@login_required_any
def list_classes():
    try:
        data = catalog_service.list_classes(
            page=request.args.get("page", 1),
            limit=request.args.get("limit", 20),
            grade_id=request.args.get("grade_id"),
            academic_year_id=request.args.get("academic_year_id"))
        return _ok(data, "Danh sách lớp học.")
    except AppError as e:
        return _err(e)


@bp.get("/classes/<int:class_id>")
@login_required_any
def get_class(class_id):
    try:
        return _ok(catalog_service.get_class(class_id), "Chi tiết lớp học.")
    except AppError as e:
        return _err(e)


@bp.put("/classes/<int:class_id>/homeroom")
@admin_required
def set_homeroom(class_id):
    try:
        payload = request.get_json(silent=True) or {}
        if payload.get("teacher_id") in (None, ""):
            from studentapp.exceptions import ValidationError
            raise ValidationError("Thiếu teacher_id.")
        data = catalog_service.set_homeroom(class_id, payload.get("teacher_id"),
                                            actor_id=_actor_id())
        return _ok(data, "Đã gán giáo viên chủ nhiệm.")
    except AppError as e:
        return _err(e)
