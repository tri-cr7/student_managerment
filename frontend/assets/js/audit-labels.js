/* ==========================================================================
   AUDIT LABELS — Dịch mã hành động & key dữ liệu audit sang tiếng Việt
   --------------------------------------------------------------------------
   DB lưu mã tiếng Anh (chuẩn để dev / truy vấn). Toàn bộ việc hiển thị
   cho người dùng nằm ở tầng frontend — file này.

   Nếu thêm mã hành động mới ở backend, chỉ cần bổ sung vào AUDIT_ACTION_LABELS
   (dropdown lọc được sinh động từ API nên không cần sửa danh sách filter).
   ========================================================================== */

/* Nhãn tiếng Việt cho mã hành động trong audit log */
export const AUDIT_ACTION_LABELS = {
  // ---- Phiên đăng nhập ----
  LOGIN_SUCCESS: "Đăng nhập thành công",
  LOGIN_FAILED: "Đăng nhập thất bại",
  LOGOUT: "Đăng xuất",
  ACCOUNT_LOCKED: "Khoá tài khoản",
  ACCOUNT_AUTO_UNLOCK: "Tự động mở khoá tài khoản",

  // ---- Mật khẩu & OTP ----
  CHANGE_PASSWORD: "Đổi mật khẩu",
  PASSWORD_RESET_SELF: "Đặt lại mật khẩu",
  RESET_PASSWORD: "Đặt lại mật khẩu (quản trị)",
  OTP_REQUEST_FORGOT: "Yêu cầu mã OTP quên mật khẩu",
  OTP_REQUEST_CHANGE: "Yêu cầu mã OTP đổi mật khẩu",
  OTP_LOCKED_FORGOT: "Huỷ mã OTP quên mật khẩu (nhập sai quá nhiều)",
  OTP_LOCKED_CHANGE: "Huỷ mã OTP đổi mật khẩu (nhập sai quá nhiều)",

  // ---- Quản lý tài khoản ----
  ADMIN_CREATE_USER: "Cấp tài khoản mới",
  CREATE_USER: "Tạo tài khoản",
  UPDATE_USER: "Cập nhật tài khoản",
  CHANGE_ROLE: "Đổi vai trò",
  LOCK_USER: "Khoá tài khoản",
  UNLOCK_USER: "Mở khoá tài khoản",

  // ---- Quy định hệ thống ----
  UPDATE_RULE: "Cập nhật quy định",
  BULK_UPDATE_RULES: "Cập nhật nhiều quy định",

  // ---- Hồ sơ học sinh ----
  ADMIT_STUDENT: "Tiếp nhận học sinh",
  UPDATE_STUDENT: "Cập nhật hồ sơ học sinh",
  UPDATE_STUDENT_STATUS: "Đổi trạng thái học sinh",
  DELETE_STUDENT_HARD: "Xoá hồ sơ học sinh",
  DELETE_STUDENT_SOFT: "Chuyển hồ sơ sang Thôi học",
  IMPORT_STUDENTS: "Import danh sách học sinh",

  // ---- Lớp học & môn học ----
  CREATE_CLASS: "Tạo lớp học",
  UPDATE_CLASS: "Cập nhật lớp học",
  DELETE_CLASS: "Xoá lớp học",
  ENROLL_STUDENT: "Phân bổ học sinh vào lớp",
  TRANSFER_STUDENT: "Chuyển lớp học sinh",
  SET_HOMEROOM: "Gán giáo viên chủ nhiệm",
  CREATE_SUBJECT: "Thêm môn học",
  UPDATE_SUBJECT: "Cập nhật môn học",
  DELETE_SUBJECT: "Xoá môn học",
  CREATE_ACADEMIC_YEAR: "Tạo năm học",
  SET_CURRENT_YEAR: "Đặt năm học hiện hành",
  CREATE_SEMESTER: "Tạo học kỳ",
  SET_CURRENT_SEMESTER: "Đặt học kỳ hiện hành",

  // ---- Phân công giảng dạy ----
  CREATE_ASSIGNMENT: "Tạo phân công giảng dạy",
  UPDATE_ASSIGNMENT: "Cập nhật phân công giảng dạy",
  DELETE_ASSIGNMENT: "Hủy phân công giảng dạy",
  LOCK_ASSIGNMENT: "Khoá bảng điểm",
  UNLOCK_ASSIGNMENT: "Mở khoá bảng điểm",

  // ---- Điểm số ----
  SAVE_SCORES: "Lưu điểm",
  UPDATE_SCORE: "Sửa điểm",
  SUBMIT_SCORES: "Gửi bảng điểm duyệt",
  CANCEL_SUBMISSION: "Huỷ đơn gửi duyệt",
  APPROVE_SUBMISSION: "Duyệt bảng điểm",
  REJECT_SUBMISSION: "Từ chối bảng điểm",
  CREATE_CHANGE_REQUEST: "Gửi đơn phúc khảo",
  APPROVE_CHANGE_REQUEST: "Phê duyệt phúc khảo",
  REJECT_CHANGE_REQUEST: "Từ chối phúc khảo",
  SCORE_TABLE_APPROVED: "Duyệt bảng điểm",
  SCORE_TABLE_REJECTED: "Từ chối bảng điểm",
  SCORE_TABLE_LOCKED: "Khoá bảng điểm",
  SCORE_TABLE_LOCK_REQUESTED: "Yêu cầu khoá bảng điểm",
  LOCK_SCORE_TABLE: "Khoá bảng điểm",
  CREATE_SCORE_CHANGE_REQUEST: "Gửi đơn phúc khảo",
  APPROVE_SCORE_CHANGE: "Phê duyệt đơn phúc khảo",
  REJECT_SCORE_CHANGE: "Từ chối đơn phúc khảo",
  CANCEL_SCORE_SUBMISSION: "Huỷ đơn gửi duyệt",
  CORRECTION_SESSION_OPENED: "Mở phiên sửa điểm",
  UNLOCK_SCORE_TABLE: "Mở khoá bảng điểm",
  DISABLE_USER: "Vô hiệu hoá tài khoản",
  ENABLE_USER: "Kích hoạt tài khoản",
  UNLOCK_SCORE_TABLE_MANUAL: "Mở khoá bảng điểm",
};

/* Nhãn tiếng Việt cho key trong `details` của audit log */
export const AUDIT_DETAIL_LABELS = {
  // -- Định danh --
  id: "Mã",
  student_id: "ID học sinh",
  student_code: "Mã học sinh",
  assignment_id: "ID phân công",
  submission_id: "ID đơn gửi duyệt",
  request_id: "ID đơn phúc khảo",
  score_id: "ID dòng điểm",
  teacher_id: "ID giáo viên",
  class_id: "ID lớp",
  subject_id: "ID môn học",
  semester_id: "ID học kỳ",
  year_id: "ID năm học",
  target_user_id: "Tài khoản bị tác động",

  // -- Người / tài khoản --
  username: "Tên đăng nhập",
  full_name: "Họ và tên",
  role: "Vai trò",
  email: "Email",
  phone: "Số điện thoại",

  // -- Hồ sơ học sinh --
  age: "Tuổi",
  gender: "Giới tính",
  address: "Địa chỉ",
  date_of_birth: "Ngày sinh",
  citizen_id: "Số CCCD",
  parent_name: "Tên phụ huynh",
  parent_phone: "Số điện thoại phụ huynh",
  dob: "Ngày sinh",
  from_status: "Trạng thái trước",
  to_status: "Trạng thái sau",
  new_status: "Trạng thái mới",
  changed: "Đã thay đổi",
  enrollments: "Danh sách lớp đăng ký",
  action: "Thao tác",
  class_name: "Tên lớp",

  // -- Thay đổi --
  changed_fields: "Các trường đã thay đổi",
  changes: "Chi tiết thay đổi",
  from: "Giá trị cũ",
  to: "Giá trị mới",
  old_value: "Điểm cũ",
  new_value: "Điểm mới",
  cleared: "Đã xoá điểm",
  score_column: "Cột điểm",
  updated: "Đã cập nhật",
  sync: "Đồng bộ lớp",

  // -- Kết quả xử lý --
  total_rows: "Tổng số dòng",
  success_count: "Số thành công",
  failed_count: "Số thất bại",
  approved_count: "Số được duyệt",
  rejected_count: "Số bị từ chối",
  total_changes: "Tổng số thay đổi",
  status: "Trạng thái",

  // -- Ghi chú --
  note: "Ghi chú",
  review_note: "Ghi chú duyệt",
  rejection_note: "Lý do từ chối",
  reason: "Lý do",
  until: "Đến thời điểm",
  locked_at: "Thời điểm khoá",
  lock_duration_minutes: "Thời hạn khoá (phút)",
  failed_attempts: "Số lần nhập sai",
  was_locked: "Tài khoản đang bị khoá",
  lock_duration_expired: "Đã quá thời hạn khoá",
  brute_force: "Nhập sai quá nhiều lần",
  via: "Thực hiện qua",
  flask_admin_bulk: "Flask-Admin (thao tác hàng loạt)",

  // -- Khoá bảng điểm --
  is_locked: "Đang khoá",
  is_active: "Đang hoạt động",
  old: "Giá trị cũ",
  new: "Giá trị mới",
  old_role: "Vai trò cũ",
  new_role: "Vai trò mới",
  rule_key: "Mã quy định",
  rule_value: "Giá trị quy định",
  data_type: "Kiểu dữ liệu",
  description: "Mô tả",
  detail_id: "ID chi tiết",
  row: "Dòng dữ liệu",
  student_name: "Tên học sinh",
};

/* Giá trị enum trong `details` → tiếng Việt */
export const AUDIT_VALUE_LABELS = {
  DANG_HOC: "Đang học",
  THOI_HOC: "Thôi học",
  CHUYEN_TRUONG: "Chuyển trường",
  TOT_NGHIEP: "Tốt nghiệp",
  STAFF: "Nhân viên",
  TEACHER: "Giáo viên",
  ACADEMIC: "Giáo vụ",
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  PARTIALLY_APPROVED: "Duyệt một phần",
  CANCELLED: "Đã huỷ",
  TRUE: "Có",
  FALSE: "Không",
  ENROLLED_BACK: "Thêm lại vào lớp",
  ENROLLED_OUT: "Rời khỏi lớp",
  ENROLLED: "Đăng ký lớp",
  UNENROLLED: "Rời lớp",
  TRANSFERRED: "Chuyển lớp",
  APPROVE: "Duyệt",
  REJECT: "Từ chối",
  PENDING: "Chờ duyệt",
};

