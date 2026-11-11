# API Documentation — Hệ Thống Quản Lý Học Sinh / Sinh Viên

**Base URL:** `http://localhost:5001/api/v1` (port 5001 để tránh xung đột macOS AirPlay chiếm 5000)
**Authentication (chốt thống nhất với `requirements.md` §8):** JWT Bearer là chính cho mọi API JSON (Header: `Authorization: Bearer <token>`, `expires_in = 1800` giây = 30 phút, trùng timeout session). Session cookie chỉ là fallback cho trình duyệt vào `/admin` (Flask-Admin). Logout = client xóa token + server hủy session; JWT ngắn hạn nên không cần bảng blacklist (mọi logout/login đều ghi `audit_logs`).
**Content-Type:** `application/json` (trừ các endpoint tải file multipart/form-data)
**ORM / Backend:** Python Flask + SQLAlchemy + MySQL 8.x

### Quy ước chung (áp dụng toàn bộ 79 endpoints)
* **Legend Role:** `Public` = không cần token; `All` = mọi role **đã đăng nhập** (`STAFF`, `TEACHER`, `ACADEMIC`); còn lại ghi rõ role.
* **Envelope thống nhất:** success → `{"success": true, "message": "...", "data": ...}`; lỗi → `{"error": "<CODE>", "message": "...", ...}` kèm đúng mã HTTP (`400/401/403/404/422/500` — xem §Chuẩn Mã Lỗi). `422` dành riêng cho vi phạm quy chế (`MIN_AGE/MAX_AGE/MAX_CLASS_SIZE/thang điểm`).
* **Phân trang thống nhất:** mọi endpoint list dùng `?page=1&limit=20` và trả `{total, page, limit, data}` (không trả mảng trần).
* **Thứ tự khai báo route (Flask):** route tĩnh (`/bulk`, `/export`, `/code/*`, `/grade/*`, `/current`, `/my`, `/batch`, `/yearly`, `/chart-data`, `/verify-token`) **phải khai báo trước** route `/{id}` cùng prefix, nếu không sẽ bị nuốt.
* **Múi giờ:** mọi timestamp ví dụ là giờ Việt Nam, format ISO 8601 `+07:00` (VD: `2026-11-11T10:30:00+07:00`).

---

## Tổng hợp Endpoints

| STT | Method | Endpoint | Role Cho Phép | Ánh Xạ Nghiệp Vụ / Sequence |
|:---:|:------:|----------|:-------------:|-----------------------------|
| | | **1. Authentication & Session** | | |
| 1 | POST | `/auth/login` | Public | Đăng nhập hệ thống, kiểm tra 5 lần khóa tài khoản (`SD01`). Trả `token` (30p) + `refresh_token` (7 ngày) + `must_change_password` |
| 2 | POST | `/auth/logout` | All | Đăng xuất, hủy phiên làm việc/thu hồi JWT |
| 1b | POST | `/auth/refresh` | Public (refresh token) | Đổi access token mới bằng refresh token (access hết 30p, không cần login lại) |
| 1c | POST | `/auth/forgot-password` | Public | Tự phục vụ quên MK: nhập email/username → nhận mail OTP 6 số (hết hạn 5p theo `OTP_EXPIRE_MINUTES`, 1 lần dùng, chống enumerate) |
| 1d | POST | `/auth/reset-password` | Public (OTP 6 số) | Đặt lại MK bằng OTP 6 số từ mail (`{email, otp_code, new_password, confirm_password}`) + MK mạnh, mở khóa luôn; giữ tương thích token dài cũ |
| 3 | GET | `/auth/me` | All | Lấy thông tin tài khoản và quyền hạn hiện tại |
| 4 | POST | `/auth/register` | — (đã khóa) | ĐÃ KHÓA đăng ký public — hệ thống quản lý sinh viên chỉ cho ACADEMIC cấp tài khoản ở `POST /admin/users` (`SD17`). Gọi luôn trả `403 FORBIDDEN`. |
| 5 | GET | `/auth/verify-token` | Public | Xác thực tính hợp lệ của Token/Phiên |
| | | **2. Profile Cá Nhân** | | |
| 6 | GET | `/profile` | All | Lấy thông tin hồ sơ cá nhân |
| 7 | PATCH | `/profile` | All | Cập nhật thông tin cá nhân (SĐT, Email) |
| 8 | POST | `/profile/change-password` | All | Đổi mật khẩu cá nhân (`SD02`) |
| | | **3. Cấu Hình Quy Chế Động (`system_rules`)** | | |
| 9 | GET | `/rules` | All | Lấy danh sách quy định hệ thống hiện hành (Tuổi, Sĩ số, Cột điểm) |
| 10 | GET | `/rules/{ruleKey}` | All | Lấy chi tiết một quy định động |
| 11 | PUT | `/rules/{ruleKey}` | ACADEMIC | Cập nhật giá trị quy chế (Yêu cầu 5 — `SD21`) |
| 12 | PUT | `/rules/bulk` | ACADEMIC | Cập nhật nhiều quy định cùng lúc (Yêu cầu 5 — `SD21`) |
| | | **4. Tiếp Nhận & Quản Lý Hồ Sơ Học Sinh** | | |
| 13 | GET | `/students` | STAFF, ACADEMIC | Danh sách học sinh (phân trang, tìm kiếm đa tiêu chí) |
| 14 | GET | `/students/{id}` | STAFF, TEACHER, ACADEMIC | Lấy chi tiết hồ sơ một học sinh |
| 15 | GET | `/students/code/{studentCode}` | STAFF, TEACHER, ACADEMIC | Tra cứu học sinh theo mã định danh duy nhất (`SD08`) |
| 16 | POST | `/students/admit` | STAFF | Tiếp nhận học sinh mới, kiểm tra tuổi 15-20 (Yêu cầu 1 — `SD03`) |
| 17 | PUT | `/students/{id}` | STAFF | Cập nhật thông tin hồ sơ học sinh (`SD07`) |
| 18 | PATCH | `/students/{id}/status` | STAFF, ACADEMIC | Cập nhật trạng thái học tập (Đang học, Thôi học, Chuyển trường) |
| 19 | DELETE | `/students/{id}` | ACADEMIC | Xóa/Vô hiệu hóa hồ sơ học sinh |
| 20 | POST | `/students/import-excel` | STAFF | Import danh sách học sinh từ file Excel/CSV (`SD04`) |
| 21 | GET | `/students/{id}/print` | STAFF, ACADEMIC | Xuất dữ liệu in hồ sơ học sinh chuẩn biểu mẫu (`SD08`) |
| | | **5. Lớp Sinh Hoạt & Phân Bổ Danh Sách Lớp** | | |
| 22 | GET | `/grades` | All | Danh sách khối lớp (Khối 10, 11, 12) |
| 23 | GET | `/grades/{gradeId}/classes` | All | Lấy danh sách lớp thuộc một khối |
| 24 | GET | `/classes` | All | Danh sách tất cả các lớp học |
| 25 | GET | `/classes/{id}` | All | Chi tiết thông tin lớp học và sĩ số hiện tại |
| 26 | POST | `/classes` | STAFF, ACADEMIC | Tạo mới một lớp học theo khối |
| 27 | PUT | `/classes/{id}` | STAFF, ACADEMIC | Chỉnh sửa tên lớp, GV chủ nhiệm |
| 28 | DELETE | `/classes/{id}` | ACADEMIC | Xóa lớp học (chỉ khi lớp chưa có học sinh) |
| 29 | GET | `/classes/{id}/students` | All | Danh sách học sinh trong lớp học |
| 30 | POST | `/classes/{id}/enroll` | STAFF | Phân bổ học sinh vào lớp, kiểm tra sĩ số $\le 40$ (Yêu cầu 2 — `SD05`) |
| 31 | POST | `/classes/transfer` | STAFF | Điều chuyển học sinh từ Lớp A sang Lớp B (Yêu cầu 2 — `SD06`) |
| 32 | GET | `/classes/{id}/export` | STAFF, ACADEMIC | Xuất danh sách lớp ra file Excel/PDF |
| | | **6. Niên Khóa & Học Kỳ** | | |
| 33 | GET | `/academic-years` | All | Danh sách các năm học/niên khóa |
| 34 | POST | `/academic-years` | ACADEMIC | Tạo năm học mới |
| 35 | GET | `/academic-years/current` | All | Lấy thông tin niên khóa hiện hành |
| 36 | GET | `/semesters` | All | Danh sách các học kỳ (HK1, HK2) |
| 37 | GET | `/semesters/current` | All | Lấy thông tin học kỳ hiện hành |
| | | **7. Danh Mục Môn Học** | | |
| 38 | GET | `/subjects` | All | Danh sách môn học toàn trường (Yêu cầu 5 — `SD22`) |
| 39 | GET | `/subjects/{id}` | All | Chi tiết thông tin môn học |
| 40 | GET | `/subjects/grade/{gradeId}` | All | Danh sách môn học theo khối lớp 10, 11, 12 |
| 41 | POST | `/subjects` | ACADEMIC | Thêm môn học mới (Yêu cầu 5 — `SD22`) |
| 42 | PUT | `/subjects/{id}` | ACADEMIC | Cập nhật môn học (Yêu cầu 5 — `SD22`) |
| 43 | DELETE | `/subjects/{id}` | ACADEMIC | Xóa môn học (Yêu cầu 5 — `SD22`) |
| | | **8. Phân Công Giảng Dạy & Khóa Bảng Điểm** | | |
| 44 | GET | `/assignments` | ACADEMIC | Danh sách phân công giảng dạy toàn trường |
| 45 | GET | `/assignments/my` | TEACHER | Danh sách các lớp bộ môn GV phụ trách (`SD09`) |
| 46 | GET | `/assignments/{id}` | TEACHER, ACADEMIC | Chi tiết một phân công giảng dạy |
| 47 | POST | `/assignments` | ACADEMIC | Phân công giáo viên dạy lớp theo môn học (`SD16`) |
| 48 | PUT | `/assignments/{id}` | ACADEMIC | Cập nhật phân công giảng dạy |
| 49 | DELETE | `/assignments/{id}` | ACADEMIC | Hủy phân công giảng dạy |
| 50 | PATCH | `/assignments/{id}/lock` | ACADEMIC | Khóa / Mở bảng điểm môn học (`SD18`) |
| | | **9. Điểm Danh Chuyên Cần** | | |
| 51 | GET | `/attendances/class/{classId}` | TEACHER, STAFF, ACADEMIC | Lấy sổ điểm danh lớp theo ngày |
| 52 | GET | `/attendances/student/{studentId}` | All | Lịch sử chuyên cần của một học sinh |
| 53 | POST | `/attendances/batch` | TEACHER | Lưu điểm danh cả lớp theo buổi (`SD10`) |
| | | **10. Điểm Số Môn Học (Khảo Thí)** | | |
| 54 | GET | `/scores/assignment/{assignmentId}` | TEACHER, ACADEMIC | Lấy toàn bộ bảng điểm lớp theo môn học |
| 55 | GET | `/scores/student/{studentId}` | All | Tra cứu toàn bộ bảng điểm của một học sinh |
| 56 | POST | `/scores/batch` | TEACHER | Nhập và lưu điểm lớp, tự tính ĐTB (Yêu cầu 3 — `SD11`) |
| 57 | PUT | `/scores/{id}` | TEACHER | Sửa trực tiếp điểm khi bảng điểm MỞ (Yêu cầu 3 — `SD14`) |
| 58 | GET | `/scores/class/{classId}/subject/{subjectId}/yearly` | TEACHER, ACADEMIC | Xem bảng điểm TB môn cả năm HK1 & HK2 (Yêu cầu 3 — `SD12`) |
| 59 | GET | `/scores/export` | TEACHER, ACADEMIC | Xuất bảng điểm môn học ra file Excel/PDF (Yêu cầu 3 — `SD13`) |
| | | **11. Phúc Khảo & Yêu Cầu Sửa Điểm** | | |
| 60 | GET | `/score-requests` | ACADEMIC | Danh sách đơn xin sửa điểm chờ duyệt |
| 61 | GET | `/score-requests/my` | TEACHER | Danh sách đơn sửa điểm do GV hiện tại đã nộp |
| 62 | GET | `/score-requests/{id}` | TEACHER, ACADEMIC | Chi tiết đơn xin sửa điểm |
| 63 | POST | `/score-requests` | TEACHER | Gửi yêu cầu sửa điểm khi bảng điểm ĐÃ KHÓA (`SD14`) |
| 64 | PUT | `/score-requests/{id}/approve` | ACADEMIC | Phê duyệt yêu cầu sửa điểm (`SD19`) |
| 65 | PUT | `/score-requests/{id}/reject` | ACADEMIC | Từ chối yêu cầu sửa điểm kèm lý do (`SD19`) |
| | | **12. Thống Kê, Báo Cáo & Biểu Đồ (Chart.js)** | | |
| 66 | GET | `/reports/subject-summary` | ACADEMIC | Báo cáo tổng kết môn học: Sĩ số, Số đạt, Tỷ lệ % (Yêu cầu 4) |
| 67 | GET | `/reports/chart-data` | ACADEMIC | Dữ liệu JSON vẽ biểu đồ cột/tròn cho Chart.js (Yêu cầu 4 — `SD20`) |
| 68 | GET | `/reports/grade-summary` | ACADEMIC | Báo cáo thống kê tổng kết chung theo khối lớp |
| 69 | GET | `/reports/export/excel` | ACADEMIC | Xuất báo cáo tổng kết môn học ra Excel chuẩn mẫu |
| 70 | GET | `/reports/export/pdf` | ACADEMIC | Xuất báo cáo tổng kết môn học ra file PDF |
| | | **13. Quản Trị Tài Khoản & Phân Quyền** | | |
| 71 | GET | `/admin/users` | ACADEMIC | Danh sách người dùng hệ thống (phân trang, lọc theo role) |
| 72 | GET | `/admin/users/{id}` | ACADEMIC | Chi tiết tài khoản người dùng |
| 73 | POST | `/admin/users` | ACADEMIC | Cấp tài khoản mới cho cán bộ/GV, gửi email (`SD17`) — chốt 1 admin: xin thêm ACADEMIC → `422` |
| 74 | PUT | `/admin/users/{id}` | ACADEMIC | Cập nhật thông tin tài khoản người dùng |
| 75 | PATCH | `/admin/users/{id}/lock` | ACADEMIC | Khóa hoặc mở khóa thủ công tài khoản người dùng |
| 76 | POST | `/admin/users/{id}/reset-password`| ACADEMIC | Đặt lại mật khẩu tạm thời cho người dùng |
| | | **14. Nhật Ký Kiểm Toán (Audit Logs)** | | |
| 77 | GET | `/admin/audit-logs` | ACADEMIC | Tra cứu lịch sử vết hoạt động của hệ thống (`SD15`) |
| 78 | GET | `/admin/audit-logs/{id}` | ACADEMIC | Xem chi tiết nội dung dữ liệu thay đổi trước/sau (JSON) |
| 79 | GET | `/admin/audit-logs/export` | ACADEMIC | Xuất file nhật ký kiểm toán ra Excel |

---

## Chi tiết các Endpoints

---

### 1. Authentication & Session

#### `POST /auth/login`
Đăng nhập vào hệ thống. Tích hợp cơ chế kiểm tra trạng thái khóa tài khoản (`is_locked`) và đếm số lần sai (`failed_attempts`). Nếu sai $\ge 5$ lần, tự động khóa tài khoản (`SD01`).

* **Quyền:** Public
* **Request Body:**
```json
{
  "username": "giaovien01",
  "password": "Password@123"
}
```
* **Response 200 (Thành công):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 1800,
  "user": {
    "id": 3,
    "username": "giaovien01",
    "full_name": "Trần Văn Giảng Viên",
    "email": "gv01@truongthpt.edu.vn",
    "role": "TEACHER"
  },
  "redirect_url": "/teacher/dashboard"
}
```
* **Response 401 (Mật khẩu sai):**
```json
{
  "error": "UNAUTHORIZED",
  "message": "Mật khẩu không chính xác. Bạn còn 3 lần thử!",
  "remaining_attempts": 3
}
```
* **Response 403 (Tài khoản bị khóa do sai $\ge 5$ lần):**
```json
{
  "error": "ACCOUNT_LOCKED",
  "message": "Tài khoản đã bị tạm khóa do nhập sai quá 5 lần liên tiếp. Vui lòng liên hệ Giáo vụ/Admin để mở khóa!"
}
```

---

#### `POST /auth/logout`
Hủy phiên làm việc trên server hoặc đưa token vào blacklist.
* **Quyền:** All (Đã xác thực)
* **Response 200:**
```json
{
  "message": "Đăng xuất thành công"
}
```

---

#### `GET /auth/me`
Lấy thông tin tài khoản hiện đang truy cập từ Token hoặc Session.
* **Quyền:** All
* **Response 200:**
```json
{
  "id": 1,
  "username": "admin",
  "full_name": "Quản trị viên Giáo vụ",
  "email": "admin@truongthpt.edu.vn",
  "role": "ACADEMIC",
  "is_locked": false,
  "created_at": "2026-09-01T08:00:00+07:00"
}
```

---

#### `POST /auth/register`
ĐÃ KHÓA đăng ký công khai (nghiệp vụ: hệ thống quản lý sinh viên chỉ cho ACADEMIC cấp tài khoản ở `POST /admin/users` — SD17; tài khoản admin đầu tiên seed từ DB/script deploy). Endpoint giữ lại để client cũ nhận thông báo rõ ràng.
* **Quyền:** — (khóa)
* **Response 403 (mọi request):** `{"error": "FORBIDDEN", "message": "Hệ thống không cho tự đăng ký. Vui lòng liên hệ Giáo vụ/Admin để được cấp tài khoản!"}`

#### `GET /auth/verify-token`
Xác thực JWT/session còn hiệu lực không (client gọi khi mở app).
* **Quyền:** Public (cần gửi token nếu có)
* **Response 200 (hợp lệ):** `{"success": true, "data": {"valid": true, "user_id": 3, "role": "TEACHER", "expires_in": 1234}}`
* **Response 401 (hết hạn/sai):** `{"error": "UNAUTHORIZED", "message": "Token không hợp lệ hoặc đã hết hạn."}`

#### `POST /auth/refresh`
Access token hết 30 phút → đổi token mới bằng refresh token (sống 7 ngày), không cần đăng nhập lại. Refresh token gửi ở header `Authorization: Bearer <refresh_token>`.
* **Quyền:** Public (refresh token còn hạn)
* **Response 200:** `{"success": true, "message": "Đã cấp access token mới.", "data": {"token": "eyJ...", "token_type": "Bearer", "expires_in": 1800}}`
* **Response 401:** `{"error": "UNAUTHORIZED", "message": "Refresh token không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại!"}`

#### `POST /auth/forgot-password`
Tự phục vụ quên mật khẩu: nhập email hoặc username → nhận mail chứa OTP 6 số (bảng `password_otps`, hết hạn `OTP_EXPIRE_MINUTES=5` phút, 1 lần dùng, nhập sai quá `OTP_MAX_ATTEMPTS=5` thì hủy mã). Chống enumerate: user không tồn tại vẫn trả 200 chung, không bắn mail.
* **Quyền:** Public — **Body:** `{"email": "gv01@truongthpt.edu.vn"}` (hoặc `{"username": "gv01"}`)
* **Response 200:** `{"success": true, "message": "Nếu thông tin đúng, email chứa mã OTP 6 số đã được gửi. Mã hết hạn sau 5 phút, 1 lần dùng.", "data": null}` + audit `OTP_REQUEST_FORGOT`

#### `POST /auth/reset-password`
Đặt lại mật khẩu bằng OTP 6 số từ mail + mật khẩu mạnh (≥8 ký tự, có Hoa + thường + số + ký tự đặc biệt). Thành công → mở khóa luôn (chứng minh chủ email), ghi audit `PASSWORD_RESET_SELF` + gửi mail cảnh báo đổi MK.
* **Quyền:** Public (OTP) — **Body:** `{"email": "gv01@truongthpt.edu.vn", "otp_code": "470172", "new_password": "MoiManh@123", "confirm_password": "MoiManh@123"}` (có thể dùng `username` thay `email`; luồng token dài cũ `{token, ...}` vẫn tương thích)
* **Response 200:** `{"success": true, "message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.", "data": {"username": "gv01"}}`
* **Response 400:** OTP sai (`"Mã OTP không đúng. Bạn còn 4 lần thử!"`), hết hạn/dùng rồi (`"Mã OTP không tồn tại hoặc đã dùng..."`), hoặc MK yếu

---

#### `POST /profile/change-password/request` (Bước 1, OTP)
Đã đăng nhập: gửi `{old_password, new_password, confirm_password}` — server check MK cũ + MK mạnh rồi gửi OTP 6 số về mail. Response 200: `{"success": true, "message": "Mã OTP 6 số đã được gửi về email...", "data": {"email_sent_status": ...}}` + audit `OTP_REQUEST_CHANGE`.

#### `POST /profile/change-password/confirm` (Bước 2, OTP)
Nhập `{otp_code, new_password, confirm_password}` → đổi MK thật + audit `CHANGE_PASSWORD` + mail cảnh báo. OTP sai/hết hạn → 400. Endpoint 1 bước cũ `POST /profile/change-password` giữ tương thích.

### 2. Profile Cá Nhân

#### `GET /profile`
Lấy hồ sơ cá nhân của chính mình.
* **Quyền:** All — **Response 200:** `{"success": true, "data": {"id": 3, "username": "giaovien01", "full_name": "Trần Văn Giảng Viên", "email": "gv01@truongthpt.edu.vn", "phone": "0911223344", "role": "TEACHER"}}`

#### `PATCH /profile`
Cập nhật SĐT/Email của chính mình (không được đổi role).
* **Quyền:** All — **Body:** `{"phone": "0911223344", "email": "moi@mail.com"}` — **Response 200:** `{"success": true, "message": "Đã cập nhật hồ sơ."}`

#### `POST /profile/change-password`
Đổi mật khẩu cá nhân. Bắt buộc kiểm tra mật khẩu cũ, mật khẩu mới phải MẠNH (≥8 ký tự, có chữ HOA + thường + số + ký tự đặc biệt) và băm mật khẩu bằng BCrypt (`SD02`). Sau khi đổi thành công: ghi audit `CHANGE_PASSWORD` + **gửi mail cảnh báo bảo mật** ("Mật khẩu của bạn vừa được thay đổi lúc ... (IP: ...). Nếu KHÔNG phải bạn, liên hệ ngay Giáo vụ!").
* **Quyền:** All
* **Request Body:**
```json
{
  "current_password": "Password@123",
  "new_password": "NewSecretPassword@456",
  "confirm_password": "NewSecretPassword@456"
}
```
* **Response 200:**
```json
{
  "message": "Đổi mật khẩu thành công. Vui lòng sử dụng mật khẩu mới cho lần đăng nhập kế tiếp."
}
```

---

### 3. Cấu Hình Quy Chế Động (`system_rules`)

#### `GET /rules`
Lấy toàn bộ tham số cấu hình quy chế hiện hành của nhà trường.
* **Quyền:** All
* **Response 200:**
```json
[
  { "rule_key": "MIN_AGE", "rule_value": "15", "data_type": "INT", "description": "Tuổi tối thiểu khi tiếp nhận học sinh" },
  { "rule_key": "MAX_AGE", "rule_value": "20", "data_type": "INT", "description": "Tuổi tối đa khi tiếp nhận học sinh" },
  { "rule_key": "MAX_CLASS_SIZE", "rule_value": "40", "data_type": "INT", "description": "Sĩ số tối đa trong một lớp học" },
  { "rule_key": "MIN_COL_15M", "rule_value": "1", "data_type": "INT", "description": "Số cột 15 phút tối thiểu" },
  { "rule_key": "MAX_COL_15M", "rule_value": "5", "data_type": "INT", "description": "Số cột 15 phút tối đa" },
  { "rule_key": "MIN_COL_45M", "rule_value": "1", "data_type": "INT", "description": "Số cột 1 tiết tối thiểu" },
  { "rule_key": "MAX_COL_45M", "rule_value": "3", "data_type": "INT", "description": "Số cột 1 tiết tối đa" },
  { "rule_key": "PASSING_SCORE", "rule_value": "5.0", "data_type": "FLOAT", "description": "Điểm chuẩn xếp loại Đạt môn học" }
]
```

---

#### `PUT /rules/{ruleKey}`
Giáo vụ cập nhật tham số quy định hệ thống (Yêu cầu 5 — `SD21`).
* **Quyền:** ACADEMIC
* **Request Body:**
```json
{
  "rule_value": "22",
  "description": "Nâng độ tuổi tối đa khi tiếp nhận lên 22 tuổi theo quy định mới"
}
```
* **Response 200:**
```json
{
  "message": "Cập nhật quy định thành công",
  "rule_key": "MAX_AGE",
  "new_value": "22",
  "updated_at": "2026-11-11T10:30:00+07:00"
}
```

---

#### `GET /rules/{ruleKey}`
Lấy chi tiết 1 quy định. * **Quyền:** All — **VD `GET /rules/MAX_CLASS_SIZE` → 200:** `{"success": true, "data": {"rule_key": "MAX_CLASS_SIZE", "rule_value": "40", "data_type": "INT", "description": "Sĩ số tối đa"}}` — **404** nếu key không tồn tại.

#### `PUT /rules/bulk`
Cập nhật nhiều quy định 1 lần trong 1 transaction (SD21). Validate toàn bộ trước khi commit.
* **Quyền:** ACADEMIC — **Body:** `{"rules": [{"rule_key": "MIN_AGE", "rule_value": "15"}, {"rule_key": "MAX_AGE", "rule_value": "20"}]}` — **Response 200:** `{"success": true, "message": "Đã cập nhật 2 quy định.", "data": {"updated": ["MIN_AGE", "MAX_AGE"]}}` — **422** nếu bất kỳ rule nào phi logic (rollback toàn bộ).

---

### 4. Tiếp Nhận & Quản Lý Hồ Sơ Học Sinh (Yêu cầu 1)

#### `GET /students`
Lấy danh sách học sinh có phân trang và lọc theo họ tên, mã số, trạng thái.
* **Quyền:** STAFF, ACADEMIC
* **Query Params:** `page=1`, `limit=20`, `keyword=Nguyen`, `status=DANG_HOC`
* **Response 200:**
```json
{
  "total": 120,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 101,
      "student_code": "HS20260001",
      "full_name": "Nguyễn Văn An",
      "gender": "NAM",
      "dob": "2010-05-14",
      "address": "123 Nguyễn Văn Cừ, Q.5, TP.HCM",
      "phone": "0912345678",
      "email": "an.nguyen@gmail.com",
      "status": "DANG_HOC"
    }
  ]
}
```

---

#### `POST /students/admit`
Tiếp nhận học sinh mới (Yêu cầu 1 — `SD03`).  
Hệ thống tự động tính tuổi: $\text{Tuổi} = \text{Năm tiếp nhận} - \text{Năm sinh}$. Truy vấn `MIN_AGE` và `MAX_AGE` từ bảng `system_rules`. Nếu vi phạm điều kiện, từ chối tiếp nhận và trả mã lỗi 422.
* **Quyền:** STAFF
* **Request Body:**
```json
{
  "student_code": "HS20260055",
  "full_name": "Lê Hoàng Yến",
  "gender": "NU",
  "dob": "2010-09-20",
  "address": "456 Võ Văn Tần, Q.3, TP.HCM",
  "phone": "0988776655",
  "email": "yen.le@gmail.com"
}
```
* **Response 201 (Thành công):**
```json
{
  "message": "Tiếp nhận học sinh mới thành công",
  "student": {
    "id": 155,
    "student_code": "HS20260055",
    "full_name": "Lê Hoàng Yến",
    "calculated_age": 16,
    "status": "DANG_HOC",
    "created_at": "2026-11-11T10:35:00+07:00"
  }
}
```
* **Response 422 (Vi phạm độ tuổi tiếp nhận):**
```json
{
  "error": "BUSINESS_RULE_VIOLATION",
  "message": "Tuổi của học sinh là 14 tuổi. Không hợp lệ với quy định tiếp nhận (Từ 15 đến 20 tuổi)!",
  "current_rules": { "min_age": 15, "max_age": 20 }
}
```

---

#### `POST /students/import-excel` (partial success — chốt thống nhất với SD04)
Import danh sách học sinh theo đợt từ file Excel/CSV (`SD04`).
* **Quyền:** STAFF
* **Content-Type:** `multipart/form-data`
* **Form-data:** `file`: `danh_sach_hoc_sinh.xlsx`
* **Response 200:**
```json
{
  "message": "Import danh sách học sinh hoàn tất",
  "total_rows": 50,
  "success_count": 48,
  "failed_count": 2,
  "errors": [
    { "row": 12, "student_name": "Trần Tuấn Khang", "reason": "Tuổi 13 vi phạm quy định nhỏ hơn 15 tuổi" },
    { "row": 35, "student_name": "Hoàng Minh Đức", "reason": "Mã học sinh HS20260012 đã tồn tại" }
  ]
}
```

---

#### `GET /students/{id}`
Chi tiết 1 hồ sơ. * **Quyền:** STAFF, TEACHER, ACADEMIC — **200:** `{"success": true, "data": {"id": 101, "student_code": "HS20260001", "full_name": "Nguyễn Văn An", "status": "DANG_HOC"}}` — **404** nếu không tồn tại.

#### `GET /students/code/{studentCode}`
Tra cứu theo mã định danh (SD08). Route tĩnh `/code` khai báo trước `/{id}`. * **Quyền:** STAFF, TEACHER, ACADEMIC.

#### `PUT /students/{id}`
Cập nhật hồ sơ (SD07): kiểm tra trùng email/phone/citizen_id với HS khác. * **Quyền:** STAFF — **409** `{"error": "DUPLICATE", "message": "Email/SĐT/CCCD đã thuộc học sinh khác."}`.

#### `PATCH /students/{id}/status`
Đổi trạng thái `DANG_HOC | THOI_HOC | CHUYEN_TRUONG | TOT_NGHIEP`. * **Quyền:** STAFF, ACADEMIC.

#### `DELETE /students/{id}`
Xóa mềm (chuyển `THOI_HOC`) nếu đã có điểm/enrollment; xóa cứng nếu chưa phát sinh dữ liệu. * **Quyền:** ACADEMIC.

#### `GET /students/{id}/print`
Trả dữ liệu in hồ sơ chuẩn biểu mẫu (SD08 `<<extend>>`). Query `?format=pdf|html`. * **Quyền:** STAFF, ACADEMIC — **200:** file binary (`application/pdf`) hoặc JSON biểu mẫu.

---

### 5. Lớp Sinh Hoạt & Phân Bổ Danh Sách Lớp (Yêu cầu 2)

#### `GET /classes/{id}/students`
Lấy danh sách học sinh đang theo học trong lớp sinh hoạt kèm sĩ số hiện tại.
* **Quyền:** All
* **Response 200:**
```json
{
  "class_id": 1,
  "class_name": "10A1",
  "grade_name": "Khối 10",
  "academic_year": "2026-2027",
  "current_size": 38,
  "max_size": 40,
  "students": [
    { "stt": 1, "student_code": "HS20260001", "full_name": "Nguyễn Văn An", "gender": "NAM", "dob": "2010-05-14", "address": "TP.HCM" }
  ]
}
```

---

#### `POST /classes/{id}/enroll`
Phân bổ học sinh vào lớp học (Yêu cầu 2 — `SD05`).  
Kiểm tra sĩ số tối đa từ `system_rules` (`MAX_CLASS_SIZE = 40`). Nếu $\text{Sĩ số hiện tại} + \text{Số lượng thêm} > 40$, từ chối lưu.
* **Quyền:** STAFF
* **Request Body:**
```json
{
  "student_ids": [101, 102, 103],
  "academic_year_id": 1
}
```
* **Response 200 (Thành công):**
```json
{
  "message": "Phân bổ học sinh vào lớp 10A1 thành công",
  "class_id": 1,
  "enrolled_count": 3,
  "new_current_size": 39
}
```
* **Response 422 (Vượt quá sĩ số tối đa):**
```json
{
  "error": "CLASS_SIZE_EXCEEDED",
  "message": "Không thể phân lớp! Lớp 10A1 hiện có 39 học sinh, thêm 3 học sinh sẽ vượt quá sĩ số tối đa cho phép (40 học sinh)!",
  "current_size": 39,
  "max_size": 40
}
```

---

#### `POST /classes/transfer`
Điều chuyển học sinh từ lớp cũ sang lớp mới (Yêu cầu 2 — `SD06`).  
Thực thi trong một Database Transaction: giảm sĩ số lớp nguồn, tăng sĩ số lớp đích (kiểm tra $< 40$), cập nhật trạng thái phân lớp.
* **Quyền:** STAFF
* **Request Body:**
```json
{
  "student_id": 105,
  "from_class_id": 1,
  "to_class_id": 2,
  "transfer_reason": "Chuyển sang lớp chuyên tự nhiên theo đơn phụ huynh"
}
```
* **Response 200:**
```json
{
  "message": "Điều chuyển học sinh thành công",
  "student_id": 105,
  "from_class": "10A1",
  "to_class": "10A2",
  "from_class_new_size": 37,
  "to_class_new_size": 39
}
```

---

#### `GET /grades`
Danh sách 3 khối 10/11/12. * **Quyền:** All — **200:** `{"success": true, "data": [{"id": 1, "grade_level": 10, "grade_name": "Khối 10"}]}` (list ngắn, không phân trang).

#### `GET /grades/{gradeId}/classes`
Lớp thuộc 1 khối (kèm `current_size`). * **Quyền:** All.

#### `GET /classes` / `GET /classes/{id}`
List có `?page&limit&grade_id&academic_year_id`; chi tiết kèm sĩ số + GVCN. * **Quyền:** All.

#### `POST /classes` / `PUT /classes/{id}` / `DELETE /classes/{id}`
Tạo/sửa/xóa lớp (SD05). Xóa chỉ khi `current_size = 0`. * **Quyền:** STAFF, ACADEMIC tạo/sửa; ACADEMIC xóa — **409** nếu trùng `uq_class_name_year`, **422** nếu xóa lớp còn HS.

#### `GET /classes/{id}/export`
Xuất danh sách lớp Excel/PDF. Query `?format=excel|pdf`. * **Quyền:** STAFF, ACADEMIC — **200:** file binary.

#### `GET /academic-years` / `POST /academic-years` / `GET /academic-years/current`
Danh mục + tạo niên khóa + lấy niên khóa `is_current = true`. * **Quyền:** All xem; ACADEMIC tạo.

#### `GET /semesters` / `GET /semesters/current`
Danh sách học kỳ (`?academic_year_id=`) + học kỳ hiện hành. Kèm `factor` (HK1 = 1, HK2 = 2) để tính điểm cả năm. * **Quyền:** All.

---

### 6. Danh Mục Môn Học (Yêu cầu 5)

#### `GET /subjects`
Lấy danh sách các môn học được phân chia theo khối (Khối 10, 11, 12).
* **Quyền:** All
* **Response 200:**
```json
[
  { "id": 1, "subject_code": "TOAN10", "subject_name": "Toán học 10", "grade_id": 1, "grade_name": "Khối 10", "periods_count": 90 },
  { "id": 2, "subject_code": "VAN10", "subject_name": "Ngữ văn 10", "grade_id": 1, "grade_name": "Khối 10", "periods_count": 90 }
]
```

---

#### `POST /subjects`
Tạo môn học mới (Yêu cầu 5 — `SD22`).
* **Quyền:** ACADEMIC
* **Request Body:**
```json
{
  "subject_code": "TIN10",
  "subject_name": "Tin học 10",
  "grade_id": 1,
  "periods_count": 45
}
```
* **Response 201:**
```json
{
  "message": "Thêm môn học mới thành công",
  "subject_id": 10,
  "subject_code": "TIN10"
}
```

---

#### `GET /subjects/{id}` / `GET /subjects/grade/{gradeId}`
Chi tiết 1 môn / list môn theo khối (`?is_active=true`). Route `/grade/*` khai báo trước `/{id}`. * **Quyền:** All.

#### `PUT /subjects/{id}` / `DELETE /subjects/{id}`
Sửa/xóa môn (SD22). Xóa chỉ khi chưa có `teaching_assignments`. * **Quyền:** ACADEMIC — **409** trùng mã / đã phát sinh phân công.

---

### 7. Phân Công Giảng Dạy & Khóa Bảng Điểm

#### `GET /assignments` / `GET /assignments/my` / `GET /assignments/{id}`
List toàn trường (ACADEMIC, `?teacher_id&semester_id`) / lớp GV hiện tại phụ trách (TEACHER, SD09) / chi tiết 1 phân công (TEACHER, ACADEMIC). List có `?page&limit`.

#### `POST /assignments` / `PUT /assignments/{id}` / `DELETE /assignments/{id}`
Phân công GV dạy lớp-môn-kỳ (SD16). Check unique `(class_id, subject_id, semester_id)` → **409** nếu lớp-môn-kỳ đã có GV. Xóa chỉ khi chưa phát sinh `scores`. * **Quyền:** ACADEMIC.

#### `PATCH /assignments/{id}/lock`
Khóa hoặc mở khóa bảng điểm môn học của một lớp (`SD18`). Khi bảng điểm bị khóa, giáo viên không thể trực tiếp sửa điểm mà phải làm đơn xin phê duyệt (`SD14`).
* **Quyền:** ACADEMIC
* **Request Body:**
```json
{
  "is_locked": true
}
```
* **Response 200:**
```json
{
  "message": "Đã khóa bảng điểm thành công. Giáo viên không thể chỉnh sửa điểm trực tiếp.",
  "assignment_id": 5,
  "is_locked": true,
  "locked_at": "2026-11-11T10:45:00+07:00"
}
```

---

### 8. Điểm Danh Chuyên Cần

#### `GET /attendances/class/{classId}` / `GET /attendances/student/{studentId}`
Sổ điểm danh lớp theo ngày (`?date=2026-11-11`) / lịch sử chuyên cần 1 HS (`?page&limit`). * **Quyền:** TEACHER, STAFF, ACADEMIC xem lớp; All xem 1 HS (HS xem chính mình).

#### `POST /attendances/batch`
Lưu bảng điểm danh của một lớp học theo ngày (`SD10`).
* **Quyền:** TEACHER
* **Request Body:**
```json
{
  "class_id": 1,
  "attendance_date": "2026-11-11",
  "records": [
    { "student_id": 101, "status": "CO_MAT", "note": "" },
    { "student_id": 102, "status": "VANG_CO_PHEP", "note": "Gia đình có việc tang" },
    { "student_id": 103, "status": "VANG_KHONG_PHEP", "note": "Không liên lạc được" }
  ]
}
```
* **Response 200:**
```json
{
  "message": "Ghi nhận điểm danh thành công",
  "class_id": 1,
  "total_records": 3
}
```

---

### 9. Quản Lý Điểm Số & Xuất Bảng Điểm (Yêu cầu 3)

#### `GET /scores/assignment/{assignmentId}`
Lấy toàn bộ bảng điểm của lớp theo đúng mẫu BẢNG ĐIỂM MÔN HỌC (Lớp, Môn, Học kỳ, Năm học, Điểm 15', Điểm 1 tiết, Điểm thi).
* **Quyền:** TEACHER, ACADEMIC
* **Response 200:**
```json
{
  "assignment_id": 5,
  "class_name": "10A1",
  "subject_name": "Toán học 10",
  "semester_name": "HK1",
  "academic_year": "2026-2027",
  "is_locked": false,
  "score_list": [
    {
      "student_id": 101,
      "student_code": "HS20260001",
      "full_name": "Nguyễn Văn An",
      "scores_15m": [8.0, 9.0],
      "scores_45m": [7.5],
      "score_final": 8.5,
      "average_score": 8.13,
      "is_passed": true
    }
  ]
}
```

---

#### `POST /scores/batch`
Nhập điểm môn học cho cả lớp (Yêu cầu 3 — `SD11`).  
Hệ thống tự động kiểm tra số cột theo quy chế (15' có 1-5 cột, 1 tiết có 1-3 cột, thi cuối kỳ có 1 cột). Tự động kích hoạt luồng bao hàm `<<include>> Tính điểm trung bình môn`:
$$\text{ĐTB} = \frac{\sum \text{Điểm 15'} \times 1 + \sum \text{Điểm 1 tiết} \times 2 + \text{Điểm thi} \times 3}{\text{Số cột 15'} + \text{Số cột 1 tiết} \times 2 + 3}$$
* **Quyền:** TEACHER
* **Request Body:**
```json
{
  "assignment_id": 5,
  "scores": [
    {
      "student_id": 101,
      "score_15m_1": 8.0,
      "score_15m_2": 9.0,
      "score_15m_3": null,
      "score_15m_4": null,
      "score_15m_5": null,
      "score_45m_1": 7.5,
      "score_45m_2": null,
      "score_45m_3": null,
      "score_final": 8.5
    }
  ]
}
```
* **Response 200 (Thành công):**
```json
{
  "message": "Lưu điểm và tính toán điểm trung bình môn thành công",
  "updated_count": 1,
  "data": [
    {
      "student_id": 101,
      "average_score": 8.13,
      "is_passed": true
    }
  ]
}
```
* **Response 422 (Điểm không hợp lệ):**
```json
{
  "error": "INVALID_SCORE_RANGE",
  "message": "Điểm số phải nằm trong khoảng từ 0.0 đến 10.0! Học sinh ID 101 có điểm 10.5 không hợp lệ."
}
```

---

#### `GET /scores/student/{studentId}`
Toàn bộ bảng điểm 1 HS (mọi môn/kỳ). * **Quyền:** All (HS xem chính mình; TEACHER/ACADEMIC xem tất cả).

#### `PUT /scores/{id}`
Sửa trực tiếp khi bảng điểm **MỞ** (`teaching_assignments.is_locked = false`, SD14). Server từ chối **423** nếu đã khóa → GV phải tạo `POST /score-requests`. * **Quyền:** TEACHER.

#### `GET /scores/class/{classId}/subject/{subjectId}/yearly`
Xem bảng điểm trung bình môn cả năm của lớp theo biểu mẫu quy định (Yêu cầu 3 — `SD12`): BẢNG ĐIỂM MÔN HỌC (STT, Họ tên, Lớp, Điểm TB HK1, Điểm TB HK2).
* **Quyền:** TEACHER, ACADEMIC
* **Response 200:**
```json
{
  "class_name": "10A1",
  "subject_name": "Toán học 10",
  "academic_year": "2026-2027",
  "records": [
    {
      "stt": 1,
      "student_code": "HS20260001",
      "full_name": "Nguyễn Văn An",
      "class_name": "10A1",
      "avg_hk1": 8.13,
      "avg_hk2": 8.50,
      "avg_yearly": 8.38
    }
  ]
}
```

---

#### `GET /scores/export`
Xuất bảng điểm môn học ra file Excel hoặc PDF (Yêu cầu 3 — `SD13`).
* **Quyền:** TEACHER, ACADEMIC
* **Query Params:** `assignment_id=5`, `format=excel` (hoặc `pdf`)
* **Response 200:** Trả về luồng file binary (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)

---

### 10. Phúc Khảo & Yêu Cầu Chỉnh Sửa Điểm (Quan hệ `<<extend>>`)

#### `GET /score-requests` / `GET /score-requests/my` / `GET /score-requests/{id}`
List đơn chờ duyệt (ACADEMIC, `?status=PENDING&page&limit`) / đơn do GV hiện tại nộp (TEACHER) / chi tiết 1 đơn (TEACHER, ACADEMIC).

#### `POST /score-requests`
Gửi đơn yêu cầu chỉnh sửa điểm khi bảng điểm đã bị khóa bởi Giáo vụ (Yêu cầu 3 — `SD14`).
* **Quyền:** TEACHER
* **Request Body:**
```json
{
  "score_id": 1001,
  "score_column": "score_final",
  "new_value": 9.0,
  "reason": "Chấm phúc khảo bài thi cuối kỳ: giáo viên chấm sót ý 3 của câu hình học (+0.5đ)"
}
```
* **Response 201:**
```json
{
  "message": "Đã gửi yêu cầu chỉnh sửa điểm tới Giáo vụ chờ phê duyệt",
  "request_id": 12,
  "status": "PENDING",
  "created_at": "2026-11-11T10:55:00+07:00"
}
```

---

#### `PUT /score-requests/{id}/approve`
Giáo vụ phê duyệt yêu cầu sửa điểm (`SD19`). Hệ thống tự động cập nhật điểm mới vào bảng `scores` và tự động tính lại Điểm Trung Bình Môn.
* **Quyền:** ACADEMIC
* **Response 200:**
```json
{
  "message": "Phê duyệt yêu cầu sửa điểm thành công. Điểm số mới đã được áp dụng và tính lại ĐTB.",
  "request_id": 12,
  "score_id": 1001,
  "new_score": 9.0,
  "new_average_score": 8.30
}
```

---

#### `PUT /score-requests/{id}/reject`
Giáo vụ từ chối yêu cầu sửa điểm kèm lý do (`SD19`).
* **Quyền:** ACADEMIC
* **Request Body:**
```json
{
  "rejection_note": "Bài làm không có sửa đổi sau khi rà soát lại bài thi gốc tại phòng khảo thí"
}
```
* **Response 200:**
```json
{
  "message": "Đã từ chối yêu cầu chỉnh sửa điểm",
  "request_id": 12,
  "status": "REJECTED"
}
```

---

### 11. Thống Kê, Báo Cáo & Dữ Liệu Biểu Đồ Chart.js (Yêu cầu 4)

#### `GET /reports/subject-summary`
Báo cáo tổng kết môn học theo các lớp (Yêu cầu 4).  
Biểu mẫu: BÁO CÁO TỔNG KẾT MÔN HỌC (Môn, Học kỳ, Năm học, Bảng gồm STT, Lớp, Sĩ số, Số lượng đạt, Tỷ lệ %).  
*Quy định đề bài:* Học sinh đạt nếu Điểm trung bình môn $\ge 5.0$.
* **Quyền:** ACADEMIC
* **Query Params:** `subject_id=1`, `semester_id=1`
* **Response 200:**
```json
{
  "subject_name": "Toán học 10",
  "semester_name": "HK1",
  "academic_year": "2026-2027",
  "passing_threshold": 5.0,
  "summary": [
    {
      "stt": 1,
      "class_id": 1,
      "class_name": "10A1",
      "class_size": 38,
      "passed_count": 35,
      "pass_rate": 92.11
    },
    {
      "stt": 2,
      "class_id": 2,
      "class_name": "10A2",
      "class_size": 40,
      "passed_count": 36,
      "pass_rate": 90.00
    }
  ]
}
```

---

#### `GET /reports/chart-data`
Đóng gói cấu trúc mảng JSON chuẩn để thư viện **Chart.js** phía Client gọi `new Chart(ctx, config)` vẽ biểu đồ cột/tròn ngay lập tức (Yêu cầu 4 — `SD20`).
* **Quyền:** ACADEMIC
* **Query Params:** `subject_id=1`, `semester_id=1`
* **Response 200:**
```json
{
  "chart_type": "bar",
  "data": {
    "labels": ["10A1", "10A2", "10A3", "10A4"],
    "datasets": [
      {
        "label": "Tỷ lệ Đạt (%)",
        "backgroundColor": "#3b82f6",
        "borderColor": "#1d4ed8",
        "borderWidth": 1,
        "data": [92.11, 90.00, 85.00, 95.00]
      },
      {
        "label": "Số lượng học sinh Đạt",
        "backgroundColor": "#10b981",
        "borderColor": "#047857",
        "borderWidth": 1,
        "data": [35, 36, 34, 38]
      }
    ]
  },
  "options": {
    "responsive": true,
    "scales": {
      "y": {
        "beginAtZero": true,
        "max": 100
      }
    }
  }
}
```

---

#### `GET /reports/grade-summary`
Thống kê tổng kết chung theo khối (sĩ số, số đạt, tỷ lệ %). Query `?grade_id&semester_id`. * **Quyền:** ACADEMIC.

#### `GET /reports/export/excel` / `GET /reports/export/pdf`
Xuất báo cáo tổng kết môn ra file chuẩn mẫu. Query `?subject_id&semester_id&format=`. * **Quyền:** ACADEMIC — **200:** file binary.

---

### 12. Quản Trị Tài Khoản & Phân Quyền (`SD17`)

#### `GET /admin/users` / `GET /admin/users/{id}`
List người dùng (`?page&limit&role&keyword`) / chi tiết 1 tài khoản. * **Quyền:** ACADEMIC.

#### `POST /admin/users`
Giáo vụ/Admin cấp tài khoản mới cho cán bộ/giáo viên. **Server TỰ SINH mật khẩu tạm** (admin không biết MK), băm BCrypt, gắn cờ `must_change_password=true`, phân quyền (`STAFF`, `TEACHER`, `ACADEMIC`) và tự động gửi email chứa tài khoản + MK tạm qua **Mail Server** (`SD17`). Người dùng bắt buộc đổi MK ở lần đăng nhập đầu (`POST /profile/change-password`).
* **Quyền:** ACADEMIC
* **Request Body (KHÔNG gửi password — server tự sinh):**
```json
{
  "username": "gv_nguyenvanb",
  "email": "vanb.nguyen@truongthpt.edu.vn",
  "full_name": "Nguyễn Văn B",
  "role": "TEACHER",
  "phone": "0911223344"
}
```
* **Response 201:**
```json
{
  "message": "Cấp tài khoản mới thành công. Email thông báo mật khẩu khởi tạo đã được gửi qua Mail Server.",
  "user_id": 15,
  "username": "gv_nguyenvanb",
  "email": "vanb.nguyen@truongthpt.edu.vn",
  "role": "TEACHER",
  "must_change_password": true,
  "email_sent_status": "SUCCESS"
}
```
* `email_sent_status`: `SUCCESS` (đã gửi SMTP) | `FAILED` (lỗi SMTP) | `LOGGED` (dev chưa cấu hình SMTP — xem console server).
* **Cấu hình SMTP:** biến môi trường `MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER` (xem `config.py`).
* **Response 400:** `{"error": "BAD_REQUEST", "message": "Role không hợp lệ (STAFF/TEACHER/ACADEMIC)."}` — **Response 409:** `{"error": "DUPLICATE", "message": "Username/Email đã tồn tại."}` — **Response 422 (xin thêm ACADEMIC thứ 2):** `{"error": "BUSINESS_RULE_VIOLATION", "message": "Hệ thống chỉ giữ 1 tài khoản Giáo vụ/Admin duy nhất! ..."}`

---

#### `PUT /admin/users/{id}`
Cập nhật thông tin tài khoản (không đổi password ở đây). * **Quyền:** ACADEMIC.

#### `PATCH /admin/users/{id}/lock`
Giáo vụ mở khóa tài khoản cho người dùng bị khóa do nhập sai mật khẩu $\ge 5$ lần (hoặc khóa chủ động khi cán bộ nghỉ việc).
**Chốt an toàn: không tự khóa chính mình (400 `BAD_REQUEST`), luôn giữ ≥ 1 ACADEMIC đang hoạt động (422 `BUSINESS_RULE_VIOLATION`) — hạ cấp/khóa/vô hiệu hóa ACADEMIC cuối cùng đều bị chặn. Phân cấp root: admin gốc (seed `SEED_ADMIN_USERNAME`, mặc định `giaovu`) bất khả xâm phạm qua API; admin thường không được khóa/vô hiệu/hạ cấp admin khác (403, chỉ root được) — chống A đẻ B rồi B thịt A.**
* **Quyền:** ACADEMIC
* **Request Body:**
```json
{
  "is_locked": false,
  "reset_failed_attempts": true
}
```
* **Response 200:**
```json
{
  "message": "Đã mở khóa tài khoản thành công và đặt lại số lần nhập sai về 0.",
  "user_id": 3,
  "is_locked": false,
  "failed_attempts": 0
}
```

---

### 13. Nhật Ký Kiểm Toán (Audit Logs — `SD15`)

#### `GET /admin/audit-logs`
Tra cứu nhật ký kiểm toán hệ thống (Audit Trail) để giám sát các hành vi nhạy cảm: thay đổi điểm số, sửa quy định, khóa/mở bảng điểm.
* **Quyền:** ACADEMIC
* **Query Params:** `action=UPDATE_SCORE`, `page=1`, `limit=20`
* **Response 200:**
```json
{
  "total": 350,
  "page": 1,
  "limit": 20,
  "logs": [
    {
      "id": 1250,
      "user_name": "Trần Văn Giảng Viên",
      "action": "UPDATE_SCORE",
      "ip_address": "192.168.1.45",
      "details": {
        "score_id": 1001,
        "student_code": "HS20260001",
        "column": "score_final",
        "old_value": 8.5,
        "new_value": 9.0,
        "approved_by": "admin"
      },
      "created_at": "2026-11-11T11:00:00+07:00"
    }
  ]
}
```

---

#### `GET /admin/audit-logs/{id}`
Chi tiết 1 vết (kèm `details` JSON trước/sau). * **Quyền:** ACADEMIC — **404** nếu không tồn tại.

#### `GET /admin/audit-logs/export`
Xuất nhật ký ra Excel (`?action&from&to`). * **Quyền:** ACADEMIC — **200:** file binary.

---

## Chuẩn Mã Lỗi Phản Hồi (Standard Error Responses)

Hệ thống tuân thủ cấu trúc phản hồi lỗi chuẩn RESTful JSON:

### 1. `400 Bad Request` — Sai cú pháp hoặc thiếu trường bắt buộc
```json
{
  "error": "BAD_REQUEST",
  "message": "Dữ liệu gửi lên không hợp lệ",
  "details": [
    { "field": "email", "message": "Email sai định dạng cú pháp" },
    { "field": "dob", "message": "Trường ngày sinh không được để trống" }
  ]
}
```

### 2. `401 Unauthorized` — Chưa đăng nhập hoặc Token hết hạn
```json
{
  "error": "UNAUTHORIZED",
  "message": "Phiên làm việc đã hết hạn hoặc Token không hợp lệ. Vui lòng đăng nhập lại!"
}
```

### 3. `403 Forbidden` — Không có quyền truy cập (RBAC chặn)
```json
{
  "error": "FORBIDDEN",
  "message": "Bạn không có quyền thực hiện thao tác này. Chức năng yêu cầu quyền: ACADEMIC!"
}
```

### 4. `404 Not Found` — Tài nguyên không tồn tại
```json
{
  "error": "NOT_FOUND",
  "message": "Không tìm thấy học sinh với mã định danh HS20269999!"
}
```

### 5. `422 Unprocessable Entity` — Vi phạm quy chế nghiệp vụ (Business Rule)
```json
{
  "error": "BUSINESS_RULE_VIOLATION",
  "message": "Lớp 10A1 đã đạt sĩ số tối đa 40 học sinh theo quy định. Không thể tiếp nhận thêm!",
  "rule_key": "MAX_CLASS_SIZE",
  "rule_value": "40"
}
```

### 6. `500 Internal Server Error` — Lỗi hệ thống máy chủ
```json
{
  "error": "INTERNAL_SERVER_ERROR",
  "message": "Đã xảy ra sự cố phía máy chủ. Vui lòng liên hệ bộ phận kỹ thuật để được hỗ trợ!"
}
```