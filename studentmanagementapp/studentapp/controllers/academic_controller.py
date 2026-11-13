"""CONTROLLER academic — API cho Giáo vụ (SD16 phân công giảng dạy, SD24 duyệt bảng điểm).

Nhóm endpoints:
* ``GET    /api/v1/assignments``      — SD16: list toàn trường (ACADEMIC)
* ``GET    /api/v1/assignments/{id}`` — chi tiết (TEACHER chủ sở hữu / ACADEMIC)
* ``POST   /api/v1/assignments``      — SD16: tạo phân công (ACADEMIC)
* ``PUT    /api/v1/assignments/{id}``— SD16: cập nhật (ACADEMIC)
* ``DELETE /api/v1/assignments/{id}``— SD16: hủy (ACADEMIC, chưa phát sinh điểm)
* ``PATCH  /api/v1/assignments/{id}/lock`` — SD18: khóa/mở thủ công (ACADEMIC)
* ``GET    /api/v1/score-submissions``          — SD24: list đơn chờ duyệt (ACADEMIC)
* ``GET    /api/v1/score-submissions/{id}``     — SD24: chi tiết (ACADEMIC)
* ``PUT    /api/v1/score-submissions/{id}/approve`` — SD24: duyệt & chốt (ACADEMIC)
* ``PUT    /api/v1/score-submissions/{id}/reject``  — SD24: từ chối (ACADEMIC)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from studentapp.exceptions import AppError
from studentapp.models.user import UserRoleEnum
from studentapp.repositories import user_repository
from studentapp.services import assignment_service, change_review_service, submission_service
from studentapp.utils.decorators import admin_required, teacher_required

bp = Blueprint("academic", __name__, url_prefix="/api/v1")


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


def _actor_role():
    uid = _actor_id()
    if uid is None:
        return None
    try:
        u = user_repository.get_by_id(uid)
        return u.role if u is not None else None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# SD16 — Phân công giảng dạy
# --------------------------------------------------------------------------- #


@bp.get("/assignments")
@admin_required
def list_assignments():
    """Danh sách phân công toàn trường (ACADEMIC, phân trang + lọc)."""
    try:
        data = assignment_service.list_assignments(
            page=request.args.get("page", 1),
            limit=request.args.get("limit", 20),
            teacher_id=request.args.get("teacher_id"),
            semester_id=request.args.get("semester_id"),
            class_id=request.args.get("class_id"),
            subject_id=request.args.get("subject_id"),
        )
        return _ok(data, "Danh sách phân công giảng dạy.")
    except AppError as e:
        return _err(e)


@bp.get("/assignments/<int:assignment_id>")
@teacher_required
def get_assignment(assignment_id):
    """Chi tiết 1 phân công (TEACHER chỉ xem assignment mình phụ trách)."""
    try:
        data = assignment_service.get_assignment(assignment_id)
        role = _actor_role()
        if role == UserRoleEnum.TEACHER and int(data["teacher_id"]) != int(_actor_id()):
            from studentapp.exceptions import PermissionDeniedError

            raise PermissionDeniedError(
                "Bạn không phụ trách lớp môn học này nên không được xem chi tiết!"
            )
        return _ok(data, "Chi tiết phân công giảng dạy.")
    except AppError as e:
        return _err(e)


@bp.post("/assignments")
@admin_required
def create_assignment():
    """Phân công giáo viên dạy lớp-môn-kỳ (SD16)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = assignment_service.create_assignment(payload, _actor_id())
        return _ok(data, "Phân công giảng dạy thành công.", 201)
    except AppError as e:
        return _err(e)


@bp.put("/assignments/<int:assignment_id>")
@admin_required
def update_assignment(assignment_id):
    """Cập nhật phân công giảng dạy (SD16)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = assignment_service.update_assignment(assignment_id, payload, _actor_id())
        return _ok(data, "Cập nhật phân công giảng dạy thành công.")
    except AppError as e:
        return _err(e)


@bp.delete("/assignments/<int:assignment_id>")
@admin_required
def delete_assignment(assignment_id):
    """Hủy phân công (chỉ khi chưa phát sinh điểm — SD16)."""
    try:
        data = assignment_service.delete_assignment(assignment_id, _actor_id())
        return _ok(data, "Đã hủy phân công giảng dạy.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD18 — Khóa / mở bảng điểm thủ công
# --------------------------------------------------------------------------- #


@bp.patch("/assignments/<int:assignment_id>/lock")
@admin_required
def set_lock(assignment_id):
    """Khóa / mở bảng điểm thủ công (SD18). Body: {"is_locked": true/false}."""
    try:
        payload = request.get_json(silent=True) or {}
        if "is_locked" not in payload:
            from studentapp.exceptions import ValidationError

            raise ValidationError("Thiếu trường is_locked (true/false).")
        raw = payload.get("is_locked")
        if isinstance(raw, str):
            want = raw.strip().lower() in ("1", "true", "yes", "on")
        else:
            want = bool(raw)
        data = assignment_service.set_lock(assignment_id, want, _actor_id())
        return _ok(data, data.pop("message", "OK."))
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD24 — Duyệt & chốt bảng điểm
# --------------------------------------------------------------------------- #


@bp.get("/score-submissions")
@admin_required
def list_submissions():
    """Danh sách đơn gửi duyệt (ACADEMIC, lọc ?status=PENDING&page&limit)."""
    try:
        data = submission_service.list_submissions(
            status=request.args.get("status"),
            page=request.args.get("page", 1),
            limit=request.args.get("limit", 20),
        )
        return _ok(data, "Danh sách bảng điểm chờ duyệt.")
    except AppError as e:
        return _err(e)


@bp.get("/score-submissions/<int:submission_id>")
@admin_required
def get_submission(submission_id):
    """Chi tiết 1 đơn gửi duyệt (kèm điểm tạm & điểm đã chốt)."""
    try:
        data = submission_service.get_submission(submission_id)
        return _ok(data, "Chi tiết đơn gửi duyệt.")
    except AppError as e:
        return _err(e)


@bp.put("/score-submissions/<int:submission_id>/approve")
@admin_required
def approve_submission(submission_id):
    """Duyệt & chốt bảng điểm → điểm chính thức (SD24)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = submission_service.approve_submission(
            submission_id, payload, _actor_id()
        )
        return _ok(data, "Đã duyệt & chốt bảng điểm thành điểm chính thức.")
    except AppError as e:
        return _err(e)


@bp.put("/score-submissions/<int:submission_id>/reject")
@admin_required
def reject_submission(submission_id):
    """Từ chối bảng điểm kèm lý do (SD24)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = submission_service.reject_submission(
            submission_id, payload, _actor_id()
        )
        return _ok(data, "Đã từ chối bảng điểm. Giáo viên có thể sửa và gửi lại.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD19 — Phê duyệt phúc khảo (duyệt từng ô)
# --------------------------------------------------------------------------- #


@bp.get("/score-requests")
@admin_required
def list_change_requests():
    """Danh sách đơn phúc khảo chờ duyệt (ACADEMIC, ?status=&page&limit)."""
    try:
        data = change_review_service.list_requests(
            status=request.args.get("status"),
            page=request.args.get("page", 1),
            limit=request.args.get("limit", 20),
        )
        return _ok(data, "Danh sách đơn phúc khảo.")
    except AppError as e:
        return _err(e)


@bp.get("/score-requests/<int:request_id>")
@admin_required
def get_change_request(request_id):
    """Chi tiết 1 đơn phúc khảo."""
    try:
        data = change_review_service.get_request(request_id)
        return _ok(data, "Chi tiết đơn phúc khảo.")
    except AppError as e:
        return _err(e)


@bp.get("/score-requests/<int:request_id>/diff")
@admin_required
def get_change_diff(request_id):
    """Bảng so sánh điểm cũ ↔ mới từng ô (SD19)."""
    try:
        data = change_review_service.get_diff(
            request_id, status=request.args.get("status")
        )
        return _ok(data, "Bảng so sánh điểm cũ ↔ mới.")
    except AppError as e:
        return _err(e)


@bp.put("/score-requests/<int:request_id>/approve")
@admin_required
def approve_change_request(request_id):
    """Phê duyệt phúc khảo — duyệt từng ô, 1 transaction ACID (SD19)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = change_review_service.approve_request(
            request_id, payload, _actor_id()
        )
        return _ok(data, "Phê duyệt yêu cầu sửa điểm thành công. Điểm mới đã được áp dụng và tính lại ĐTB.")
    except AppError as e:
        return _err(e)


@bp.put("/score-requests/<int:request_id>/reject")
@admin_required
def reject_change_request(request_id):
    """Từ chối toàn bộ đơn phúc khảo kèm lý do (SD19)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = change_review_service.reject_request(
            request_id, payload, _actor_id()
        )
        return _ok(data, "Đã từ chối yêu cầu chỉnh sửa điểm.")
    except AppError as e:
        return _err(e)
