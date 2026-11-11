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


class BusinessRuleError(AppError):
    status_code = 422
    error = "BUSINESS_RULE_VIOLATION"
    message = "Vi phạm quy chế nghiệp vụ."
