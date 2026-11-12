"""App errors."""

class AppError(Exception):
    status_code = 500
    error = "INTERNAL_SERVER_ERROR"
    message = "Đã xảy ra sự cố phía máy chủ."

    def __init__(self, message=None, error=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.error = error or self.error


class ValidationError(AppError):
    status_code = 400
    error = "BAD_REQUEST"
    message = "Dữ liệu không hợp lệ."


class AuthenticationError(AppError):
    status_code = 401
    error = "UNAUTHORIZED"
    message = "Tên đăng nhập hoặc mật khẩu không đúng."


class PermissionDeniedError(AppError):
    status_code = 403
    error = "FORBIDDEN"
    message = "Bạn không có quyền thực hiện tác vụ này."


class NotFoundError(AppError):
    status_code = 404
    error = "NOT_FOUND"
    message = "Không tìm thấy dữ liệu yêu cầu."


class DuplicateError(AppError):
    status_code = 409
    error = "DUPLICATE"
    message = "Dữ liệu đã tồn tại."


class LockedError(AppError):
    status_code = 403
    error = "ACCOUNT_LOCKED"
    message = "Tài khoản đã bị tạm khóa do nhập sai quá 5 lần liên tiếp."


class ScoreTableLockedError(AppError):
    """423 — Bảng điểm đã chốt, Giáo viên không sửa trực tiếp được."""

    status_code = 423
    error = "SCORE_TABLE_LOCKED"
    message = "Bảng điểm đã được chốt. Bạn không thể sửa trực tiếp điểm số!"


class ScoreSubmissionPendingError(AppError):
    """423 — Đang có đơn gửi duyệt PENDING, Giáo viên phải hủy đơn trước khi sửa điểm."""

    status_code = 423
    error = "SCORE_SUBMISSION_PENDING"
    message = "Bảng điểm đang được gửi duyệt. Vui lòng hủy đơn gửi duyệt trước khi sửa điểm!"

    def __init__(self, message=None, error=None, pending_submission_id=None):
        super().__init__(message=message, error=error)
        self.pending_submission_id = pending_submission_id


class InvalidSubmissionStatusError(AppError):
    """409 — Đơn không ở trạng thái PENDING nên không hủy được."""

    status_code = 409
    error = "INVALID_SUBMISSION_STATUS"
    message = "Chỉ có thể hủy đơn đang ở trạng thái chờ duyệt!"

    def __init__(self, message=None, error=None, current_status=None):
        super().__init__(message=message, error=error)
        self.current_status = current_status


class IncompleteScoresError(AppError):
    """422 — Còn ô điểm chưa nhập, không thể gửi duyệt (rule B1)."""

    status_code = 422
    error = "INCOMPLETE_SCORES"
    message = "Còn ô điểm chưa được nhập. Vui lòng nhập đủ điểm trước khi gửi duyệt!"


class InvalidScoreRangeError(AppError):
    """422 — Điểm nằm ngoài khoảng [0.0, 10.0]."""

    status_code = 422
    error = "INVALID_SCORE_RANGE"
    message = "Điểm phải nằm trong khoảng từ 0.0 đến 10.0!"


class InvalidColumnNameError(AppError):
    """422 — Cột điểm không thuộc whitelist 9 cột."""

    status_code = 422
    error = "INVALID_COLUMN_NAME"
    message = "Cột điểm không hợp lệ!"


class InvalidColumnCountError(AppError):
    """422 — Cột điểm vượt quá số cột cho phép theo quy định (rule A2/A3/A4)."""

    status_code = 422
    error = "INVALID_COLUMN_COUNT"
    message = "Số cột điểm vượt quá quy định cho phép!"


class DuplicatePendingSubmissionError(AppError):
    """409 — Lớp môn học đã có đơn gửi duyệt đang chờ."""

    status_code = 409
    error = "DUPLICATE_PENDING_SUBMISSION"
    message = "Bảng điểm này đã được gửi duyệt và đang chờ Giáo vụ xử lý."

    def __init__(self, message=None, error=None, pending_submission_id=None):
        super().__init__(message=message, error=error)
        self.pending_submission_id = pending_submission_id


class ScoreValueConflictError(AppError):
    """409 — Điểm hiện tại đã thay đổi so với lúc Giáo viên gửi đơn."""

    status_code = 409
    error = "SCORE_VALUE_CONFLICT"
    message = "Điểm hiện tại đã thay đổi so với lúc bạn gửi đơn. Vui lòng tải lại điểm!"


class ScoreTableNotLockedError(AppError):
    """422 — Bảng điểm đang mở, không được gửi đơn phúc khảo (phải sửa trực tiếp)."""

    status_code = 422
    error = "SCORE_TABLE_NOT_LOCKED"
    message = "Bảng điểm đang mở. Bạn hãy sửa điểm trực tiếp thay vì gửi đơn phúc khảo!"


class BusinessRuleError(AppError):
    status_code = 422
    error = "BUSINESS_RULE_VIOLATION"
    message = "Vi phạm quy chế nghiệp vụ."
