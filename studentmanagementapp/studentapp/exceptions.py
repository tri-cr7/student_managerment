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

    status_code = 423
    error = "SCORE_TABLE_LOCKED"
    message = "Bảng điểm đã được chốt. Bạn không thể sửa trực tiếp điểm số!"

class ScoreSubmissionPendingError(AppError):

    status_code = 423
    error = "SCORE_SUBMISSION_PENDING"
    message = "Bảng điểm đang được gửi duyệt. Vui lòng hủy đơn gửi duyệt trước khi sửa điểm!"

    def __init__(self, message=None, error=None, pending_submission_id=None):
        super().__init__(message=message, error=error)
        self.pending_submission_id = pending_submission_id

class InvalidSubmissionStatusError(AppError):

    status_code = 409
    error = "INVALID_SUBMISSION_STATUS"
    message = "Chỉ có thể hủy đơn đang ở trạng thái chờ duyệt!"

    def __init__(self, message=None, error=None, current_status=None):
        super().__init__(message=message, error=error)
        self.current_status = current_status

class DecisionsRequiredError(AppError):

    status_code = 422
    error = "DECISIONS_REQUIRED"
    message = "Đơn sửa điểm có nhiều ô, vui lòng gửi quyết định duyệt/từ chối cho từng ô!"

class IncompleteScoresError(AppError):

    status_code = 422
    error = "INCOMPLETE_SCORES"
    message = "Còn ô điểm chưa được nhập. Vui lòng nhập đủ điểm trước khi gửi duyệt!"

class InvalidScoreRangeError(AppError):

    status_code = 422
    error = "INVALID_SCORE_RANGE"
    message = "Điểm phải nằm trong khoảng từ 0.0 đến 10.0!"

class InvalidColumnNameError(AppError):

    status_code = 422
    error = "INVALID_COLUMN_NAME"
    message = "Cột điểm không hợp lệ!"

class InvalidColumnCountError(AppError):

    status_code = 422
    error = "INVALID_COLUMN_COUNT"
    message = "Số cột điểm vượt quá quy định cho phép!"

class DuplicateStudentInBatchError(AppError):

    status_code = 422
    error = "DUPLICATE_STUDENT_IN_BATCH"
    message = "Học sinh bị trùng trong cùng một yêu cầu lưu điểm!"

    def __init__(self, message=None, error=None, student_id=None):
        super().__init__(message, error)
        self.student_id = student_id

class StudentNotInAssignmentError(AppError):

    status_code = 422
    error = "STUDENT_NOT_IN_ASSIGNMENT"
    message = "Học sinh không thuộc lớp của lớp môn học này!"

    def __init__(self, message=None, error=None, student_id=None, assignment_id=None):
        super().__init__(message, error)
        self.student_id = student_id
        self.assignment_id = assignment_id

class DuplicatePendingSubmissionError(AppError):

    status_code = 409
    error = "DUPLICATE_PENDING_SUBMISSION"
    message = "Bảng điểm này đã được gửi duyệt và đang chờ Giáo vụ xử lý."

    def __init__(self, message=None, error=None, pending_submission_id=None):
        super().__init__(message=message, error=error)
        self.pending_submission_id = pending_submission_id

class ScoreValueConflictError(AppError):

    status_code = 409
    error = "SCORE_VALUE_CONFLICT"
    message = "Điểm hiện tại đã thay đổi so với lúc bạn gửi đơn. Vui lòng tải lại điểm!"

class ScoreTableNotLockedError(AppError):

    status_code = 422
    error = "SCORE_TABLE_NOT_LOCKED"
    message = "Bảng điểm đang mở. Bạn hãy sửa điểm trực tiếp thay vì gửi đơn phúc khảo!"

class DuplicatePendingAppealError(AppError):

    status_code = 409
    error = "DUPLICATE_PENDING_APPEAL"
    message = (
        "Một hoặc nhiều ô điểm đã có đơn phúc khảo đang chờ duyệt. "
        "Vui lòng chờ Giáo vụ xử lý trước khi gửi đơn mới."
    )

    def __init__(self, message=None, error=None, cells=None):
        super().__init__(message=message, error=error)

        self.cells = cells or []

class BusinessRuleError(AppError):
    status_code = 422
    error = "BUSINESS_RULE_VIOLATION"
    message = "Vi phạm quy chế nghiệp vụ."

class StudentBusinessError(BusinessRuleError):

    status_code = 422
    error = "STUDENT_BUSINESS_RULE_VIOLATION"
    message = "Vi phạm quy chế quản lý học sinh và lớp học."

class ClassSizeExceededError(AppError):

    status_code = 422
    error = "CLASS_SIZE_EXCEEDED"
    message = "Sĩ số lớp học vượt quá số lượng tối đa cho phép."

    def __init__(self, message=None, error=None, current_size=None, max_size=None):
        super().__init__(message=message, error=error)
        self.current_size = current_size
        self.max_size = max_size
