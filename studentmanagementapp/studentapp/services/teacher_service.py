"""SERVICE teacher — nghiệp vụ dùng chung cho module Giáo viên."""
from studentapp.exceptions import NotFoundError, PermissionDeniedError
from studentapp.repositories import teaching_assignment_repository


def _get_assignment_or_404(assignment_id):
    assignment = teaching_assignment_repository.get_by_id(assignment_id)
    if assignment is None:
        raise NotFoundError("Không tìm thấy lớp môn học (phân công giảng dạy).")
    return assignment


def ensure_teacher_owns_assignment(assignment_id, teacher_id):
    """Kiểm tra Giáo viên có phụ trách lớp môn học này không (rule A7/A11).

    :raises PermissionDeniedError: nếu GV không phụ trách assignment.
    """
    assignment = _get_assignment_or_404(assignment_id)
    if int(assignment.teacher_id) != int(teacher_id):
        raise PermissionDeniedError(
            "Bạn không phụ trách lớp môn học này nên không được thao tác điểm số!"
        )
    return assignment


def ensure_assignment_open(assignment):
    """Bảng điểm phải đang MỞ (chưa chốt) để nhập/sửa điểm trực tiếp (rule A8)."""
    from studentapp.exceptions import ScoreTableLockedError

    if assignment.is_locked:
        raise ScoreTableLockedError(
            "Bảng điểm đã được chốt. Bạn không thể sửa trực tiếp — "
            "vui lòng gửi yêu cầu chỉnh điểm qua đơn phúc khảo!"
        )
    return assignment


def ensure_no_pending_submission(assignment_id):
    """Không có đơn gửi duyệt đang PENDING thì mới sửa điểm được (rule A10)."""
    from studentapp.exceptions import ScoreSubmissionPendingError

    pending = teaching_assignment_repository.get_pending_submission(assignment_id)
    if pending is not None:
        raise ScoreSubmissionPendingError(
            "Bảng điểm đang được gửi duyệt. Vui lòng hủy đơn gửi duyệt trước khi sửa điểm!",
            pending_submission_id=pending.id,
        )
    return True


def list_my_assignments(teacher_id, semester_id=None, academic_year_id=None):
    """Danh sách lớp môn học GV phụ trách (SD09)."""
    return teaching_assignment_repository.list_by_teacher(
        teacher_id, semester_id=semester_id, academic_year_id=academic_year_id
    )
