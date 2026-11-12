"""CONTROLLER teacher — API cho Giáo viên (module điểm số).

Nhóm endpoints:
* ``GET  /api/v1/assignments/my``              — SD09: lớp môn học phụ trách
* ``POST /api/v1/scores/batch``                 — SD11: nhập điểm (bảng điểm tạm)
* ``PUT  /api/v1/scores/{id}``                  — SD14: sửa 1 ô điểm
* ``GET  /api/v1/scores/assignment/{id}``       — xem bảng điểm
* ``GET  /api/v1/scores/student/{studentId}``   — xem điểm 1 học sinh
* ``POST /api/v1/score-submissions``            — SD23: gửi bảng điểm lên duyệt
* ``PUT  /api/v1/score-submissions/{id}/cancel`` — SD23: hủy đơn để sửa
* ``POST /api/v1/score-requests``               — SD25: gửi đơn phúc khảo
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from studentapp.exceptions import AppError
from studentapp.services import score_service
from studentapp.utils.decorators import teacher_required

bp = Blueprint("teacher", __name__, url_prefix="/api/v1")


def _err(e: AppError):
    payload = {"error": e.error, "message": e.message}
    for attr in ("pending_submission_id", "current_status"):
        value = getattr(e, attr, None)
        if value is not None:
            payload[attr] = value
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


# --------------------------------------------------------------------------- #
# SD09 — Tra cứu danh sách lớp phụ trách
# --------------------------------------------------------------------------- #


@bp.get("/assignments/my")
@teacher_required
def my_assignments():
    """Danh sách lớp môn học Giáo viên được phụ trách (SD09)."""
    try:
        data = score_service.list_my_assignments(_actor_id())
        return _ok(data, "Danh sách lớp phụ trách.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD11 — Nhập điểm môn học
# --------------------------------------------------------------------------- #


@bp.post("/scores/batch")
@teacher_required
def save_scores_batch():
    """Nhập & lưu điểm cho cả lớp vào BẢNG ĐIỂM TẠM (SD11)."""
    try:
        payload = request.get_json(silent=True) or {}
        result = score_service.save_batch_scores(payload, _actor_id())
        return _ok(result["data"], result["message"])
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD14 — Sửa 1 ô điểm
# --------------------------------------------------------------------------- #


@bp.put("/scores/<int:score_id>")
@teacher_required
def update_score(score_id):
    """Sửa một ô điểm khi bảng điểm đang MỞ (SD14)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.update_score_cell(score_id, payload, _actor_id())
        return _ok(data, "Cập nhật điểm thành công.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# Đọc điểm
# --------------------------------------------------------------------------- #


@bp.get("/scores/assignment/<int:assignment_id>")
@teacher_required
def get_assignment_scores(assignment_id):
    """Xem bảng điểm của một lớp môn học (cả nháp & chính thức, kèm cờ is_draft)."""
    try:
        data = score_service.get_assignment_scores(assignment_id, _actor_id())
        return _ok(data, "Lấy bảng điểm thành công.")
    except AppError as e:
        return _err(e)


@bp.get("/scores/student/<int:student_id>")
@teacher_required
def get_student_scores(student_id):
    """Xem toàn bộ điểm của một học sinh.

    Mặc định chỉ trả điểm **chính thức** đã duyệt — tránh lộ điểm tạm.
    """
    try:
        include_draft = request.args.get("include_draft", "").lower() in ("1", "true", "yes")
        data = score_service.get_student_scores(student_id, _actor_id(), include_draft)
        return _ok(data, "Lấy điểm học sinh thành công.")
    except AppError as e:
        return _err(e)


@bp.get("/students/search")
@teacher_required
def search_students():
    """Tìm học sinh trong các lớp GV phụ trách (theo tên / mã số HS)."""
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


# --------------------------------------------------------------------------- #
# SD23 — Gửi bảng điểm lên duyệt & hủy đơn
# --------------------------------------------------------------------------- #


@bp.post("/score-submissions")
@teacher_required
def create_submission():
    """Gửi bảng điểm tạm lên Giáo vụ để duyệt & chốt (SD23)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.create_submission(payload, _actor_id())
        return _ok(data, "Đã gửi bảng điểm lên Giáo vụ chờ duyệt & chốt.", 201)
    except AppError as e:
        return _err(e)


@bp.put("/score-submissions/<int:submission_id>/cancel")
@teacher_required
def cancel_submission(submission_id):
    """Hủy đơn gửi duyệt để sửa lại bảng điểm tạm (SD23)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.cancel_submission(submission_id, payload, _actor_id())
        return _ok(data, "Đã hủy đơn gửi duyệt. Bạn có thể sửa lại bảng điểm tạm.")
    except AppError as e:
        return _err(e)


@bp.get("/score-submissions/my")
@teacher_required
def my_submissions():
    """Danh sách bảng điểm Giáo viên đã gửi duyệt."""
    try:
        data = score_service.list_my_submissions(_actor_id())
        return _ok(data, "Danh sách bảng điểm đã gửi duyệt.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# Cấu hình cột điểm (nhóm gọn 15' / 1 tiết / thi theo system_rules)
# --------------------------------------------------------------------------- #


@bp.get("/scores/columns/config")
@teacher_required
def score_column_config():
    """Cấu hình cột điểm đang dùng (UI render nhóm gọn theo 3 nhóm)."""
    try:
        data = score_service.get_score_column_config()
        return _ok(data, "Cấu hình cột điểm.")
    except AppError as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# SD25 — Gửi yêu cầu chỉnh điểm (phúc khảo)
# --------------------------------------------------------------------------- #


@bp.post("/score-requests")
@teacher_required
def create_change_request():
    """Gửi đơn phúc khảo khi bảng điểm đã CHỐT (SD25)."""
    try:
        payload = request.get_json(silent=True) or {}
        data = score_service.create_change_request(payload, _actor_id())
        return _ok(data, "Đã gửi yêu cầu tới Giáo vụ chờ phê duyệt.", 201)
    except AppError as e:
        return _err(e)


@bp.get("/score-requests/my")
@teacher_required
def my_change_requests():
    """Danh sách đơn phúc khảo Giáo viên đã gửi."""
    try:
        data = score_service.list_my_change_requests(_actor_id())
        return _ok(data, "Danh sách yêu cầu chỉnh điểm.")
    except AppError as e:
        return _err(e)
