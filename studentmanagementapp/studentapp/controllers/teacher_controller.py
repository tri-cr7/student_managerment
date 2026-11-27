import io

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from studentapp.exceptions import AppError, ValidationError
from studentapp.models.user import UserRoleEnum
from studentapp.services import score_service
from studentapp.utils.decorators import teacher_required

bp = Blueprint("teacher", __name__, url_prefix="/api/v1")

def _err(e: AppError):
    payload = {"error": e.error, "message": e.message}

    for attr in (
        "pending_submission_id",
        "current_status",
        "student_id",
        "assignment_id",
        "cells",
    ):
        value = getattr(e, attr, None)
        if value is not None:
            payload[attr] = value
    return jsonify(payload), e.status_code

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

def _is_academic():

    from studentapp.utils.decorators import _current_role

    role, _user = _current_role()
    return role == UserRoleEnum.ACADEMIC

@bp.get("/assignments/my")
@teacher_required
def my_assignments():

    try:
        data = score_service.list_my_assignments(_actor_id())
        return _ok(data, "Danh sách lớp phụ trách.")
    except AppError as e:
        return _err(e)

@bp.post("/scores/batch")
@teacher_required
def save_scores_batch():

    try:
        payload = request.get_json(silent=True) or {}
        result = score_service.save_batch_scores(payload, _actor_id())
        return _ok(result["data"], result["message"])
    except AppError as e:
        return _err(e)

@bp.put("/scores/<int:score_id>")
@teacher_required
def update_score(score_id):

    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.update_score_cell(score_id, payload, _actor_id())
        return _ok(data, "Cập nhật điểm thành công.")
    except AppError as e:
        return _err(e)

@bp.get("/scores/assignment/<int:assignment_id>")
@teacher_required
def get_assignment_scores(assignment_id):

    try:
        data = score_service.get_assignment_scores(
            assignment_id, _actor_id(), is_academic=_is_academic()
        )
        return _ok(data, "Lấy bảng điểm thành công.")
    except AppError as e:
        return _err(e)

@bp.get("/scores/student/<int:student_id>")
@teacher_required
def get_student_scores(student_id):

    try:
        include_draft = request.args.get("include_draft", "").lower() in ("1", "true", "yes")
        data = score_service.get_student_scores(
            student_id,
            _actor_id(),
            include_draft,
            is_academic=_is_academic(),
        )
        return _ok(data, "Lấy điểm học sinh thành công.")
    except AppError as e:
        return _err(e)

@bp.get("/students/search")
@teacher_required
def search_students():

    try:
        data = score_service.search_my_students(
            _actor_id(),
            keyword=request.args.get("q", ""),
            class_id=request.args.get("class_id"),
            limit=request.args.get("limit", 20),
        )
        return _ok(data, "Tìm kiếm học sinh thành công.")
    except AppError as e:
        return _err(e)

@bp.post("/score-submissions")
@teacher_required
def create_submission():

    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.create_submission(payload, _actor_id())
        return _ok(data, "Đã gửi bảng điểm lên Giáo vụ chờ duyệt & chốt.", 201)
    except AppError as e:
        return _err(e)

@bp.put("/score-submissions/<int:submission_id>/cancel")
@teacher_required
def cancel_submission(submission_id):

    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.cancel_submission(submission_id, payload, _actor_id())
        return _ok(data, "Đã hủy đơn gửi duyệt. Bạn có thể sửa lại bảng điểm tạm.")
    except AppError as e:
        return _err(e)

@bp.get("/score-submissions/my")
@teacher_required
def my_submissions():

    try:
        data = score_service.list_my_submissions(_actor_id())
        return _ok(data, "Danh sách bảng điểm đã gửi duyệt.")
    except AppError as e:
        return _err(e)

@bp.get("/scores/columns/config")
@teacher_required
def score_column_config():

    try:
        data = score_service.get_score_column_config()
        return _ok(data, "Cấu hình cột điểm.")
    except AppError as e:
        return _err(e)

@bp.get("/scores/class/<int:class_id>/subject/<int:subject_id>/yearly")
@teacher_required
def get_yearly_class_scores(class_id, subject_id):

    try:
        academic_year_id = request.args.get("academic_year_id")
        data = score_service.get_yearly_class_scores(
            class_id,
            subject_id,
            academic_year_id,
            teacher_id=_actor_id(),
            is_academic=_is_academic(),
        )
        return _ok(data, "Lấy bảng điểm trung bình lớp thành công.")
    except AppError as e:
        return _err(e)

@bp.get("/scores/export")
@teacher_required
def export_yearly_class_scores():

    try:
        assignment_id = request.args.get("assignment_id")
        fmt = request.args.get("format", "excel")
        payload, filename, mime, _data = score_service.export_yearly_class_scores(
            assignment_id,
            fmt=fmt,
            teacher_id=_actor_id(),
            is_academic=_is_academic(),
        )
        return send_file(
            io.BytesIO(payload),
            mimetype=mime,
            as_attachment=True,
            download_name=filename,
        )
    except AppError as e:
        return _err(e)

@bp.post("/score-requests")
@teacher_required
def create_change_request():

    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.create_change_request(payload, _actor_id())
        return _ok(data, "Đã gửi yêu cầu tới Giáo vụ chờ phê duyệt.", 201)
    except AppError as e:
        return _err(e)

@bp.get("/score-requests/my")
@teacher_required
def my_change_requests():

    try:
        data = score_service.list_my_change_requests(_actor_id())
        return _ok(data, "Danh sách yêu cầu chỉnh điểm.")
    except AppError as e:
        return _err(e)

@bp.post("/score-requests/attachment")
@teacher_required
def upload_change_request_attachment():

    try:
        from studentapp.services import attachment_service

        file_obj = request.files.get("file")
        if file_obj is None or not file_obj.filename:
            return _err(
                ValidationError(
                    "Không tìm thấy file tải lên.",
                    error="MISSING_FILE",
                )
            )
        data = attachment_service.save_attachment(file_obj, teacher_id=_actor_id())
        return _ok(data, "Đã tải lên file đính kèm thành công.", 201)
    except AppError as e:
        return _err(e)
