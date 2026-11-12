# API Documentation — Hệ Thống Quản Lý Học Sinh / Sinh Viên

**Base URL:** `http://localhost:5001/api/v1` (port 5001 để tránh xung đột macOS AirPlay chiếm 5000)
**Authentication (chốt thống nhất với `requirements.md` §8):** JWT Bearer là chính cho mọi API JSON (Header: `Authorization: Bearer <token>`, `expires_in = 1800` giây = 30 phút, trùng timeout session). Session cookie chỉ là fallback cho trình duyệt vào `/admin` (Flask-Admin). Logout = client xóa token + server hủy session; JWT ngắn hạn nên không cần bảng blacklist (mọi logout/login đều ghi `audit_logs`).
**Content-Type:** `application/json` (trừ các endpoint tải file multipart/form-data)
**ORM / Backend:** Python Flask + SQLAlchemy + MySQL 8.x

### Quy ước chung (áp dụng toàn bộ 85 endpoints)
* **Legend Role:** `Public` = không cần token; `All` = mọi role **đã đăng nhập** (`STAFF`, `TEACHER`, `ACADEMIC`); còn lại ghi rõ role.
* **Envelope thống nhất:** success → `{"success": true, "message": "...", "data": ...}`; lỗi → `{"error": "<CODE>", "message": "...", ...}` kèm đúng mã HTTP (`400/401/403/404/422/500` — xem §Chuẩn Mã Lỗi). `422` dành riêng cho vi phạm quy chế (`MIN_AGE/MAX_AGE/MAX_CLASS_SIZE/thang điểm`).
* **Phân trang thống nhất:** mọi endpoint list dùng `?page=1&limit=20` và trả `{total, page, limit, data}` (không trả mảng trần).
* **Thứ tự khai báo route (Flask):** route tĩnh (`/bulk`, `/export`, `/code/*`, `/grade/*`, `/current`, `/my`, `/batch`, `/yearly`, `/chart-data`, `/verify-token`) **phải khai báo trước** route `/{id}` cùng prefix, nếu không sẽ bị nuốt.
* **Múi giờ:** mọi timestamp ví dụ là giờ Việt Nam, format ISO 8601 `+07:00` (VD: `2026-11-11T10:30:00+07:00`).
* **Phân quyền 2 tầng cho role `TEACHER`:** ngoài kiểm tra role (`@teacher_required`), mọi endpoint của Giáo viên phải kiểm tra **phạm vi dữ liệu** — Giáo viên chỉ được thao tác trên lớp/môn mà mình được phân công trong `teaching_assignments`. Cụ thể:
  * `POST /scores/batch`, `PUT /scores/{id}`, `POST /score-requests` → `403` nếu `assignment.teacher_id != current_user.id`.
  * `GET /scores/assignment/{assignmentId}` → `403` nếu GV không phụ trách assignment.
  * `GET /scores/class/{classId}/subject/{subjectId}/yearly` → `403` nếu GV không phụ trách môn đó ở lớp đó.
  * `GET /scores/student/{studentId}` → `403` nếu học sinh không thuộc lớp GV phụ trách (trừ `ACADEMIC` xem toàn trường).
  * Việc kiểm tra phạm vi nằm ở **tầng Service** (cần truy vấn DB), còn kiểm tra role nằm ở **tầng Controller** (decorator).
* **Mã lỗi chuyên biệt:** `423 SCORE_TABLE_LOCKED` — bảng điểm đã chốt, Giáo viên phải gửi đơn qua `POST /score-requests` (xem §Chuẩn Mã Lỗi mục 6); `409 DUPLICATE_PENDING_SUBMISSION` — bảng điểm đã có bản ghi đang chờ duyệt; `422 NO_SCORES_TO_SUBMIT` — chưa nhập ô điểm nào để gửi duyệt; `422 INCOMPLETE_SCORES` — còn ô điểm `NULL` (chưa nhập) khi gửi duyệt; `422 INVALID_COLUMN_COUNT` — số cột điểm vi phạm `system_rules`; `422 DUPLICATE_STUDENT_IN_BATCH` — trùng `student_id` trong 1 request; `422 STUDENT_NOT_IN_ASSIGNMENT` — học sinh không thuộc lớp của bảng điểm; `422 INVALID_COLUMN_NAME` — cột điểm không thuộc whitelist 9 cột (`score_15m_1`..`score_15m_5`, `score_45m_1`..`score_45m_3`, `score_final`); `423 SCORE_SUBMISSION_PENDING` — đang có đơn gửi duyệt `PENDING`, GV phải hủy đơn trước khi sửa điểm; `409 INVALID_SUBMISSION_STATUS` — đơn không ở trạng thái `PENDING` (không hủy được); `409 SCORE_VALUE_CONFLICT` — điểm hiện tại đã khác với `old_value` GV gửi lên; `422 DECISIONS_REQUIRED` — duyệt đơn lô thiếu `decisions[]`; `422 INVALID_ATTACHMENT_TYPE` — file đính kèm sai định dạng; `413 FILE_TOO_LARGE` — file đính kèm vượt 10 MB.
* **Phân biệt điểm tạm & điểm chính thức (cờ `scores.is_draft`):** mọi lần Giáo viên bấm "Lưu" ở BẢNG ĐIỂM MÔN HỌC sẽ ghi vào bảng `scores` với `is_draft = TRUE` (**ghi đè** bản nháp trước). Hệ thống **vẫn tính `average_score`** ngay để Giáo viên tự kiểm tra, nhưng điểm này **chưa phải điểm chính thức**.
  * `is_draft = TRUE` → **bảng điểm tạm** — Giáo viên sửa thoải mái, không cần xin quyền.
  * `is_draft = FALSE` → **bảng điểm chính thức** — đã được Giáo vụ duyệt & chốt.
  * **Bắt buộc:** mọi truy vấn *đọc điểm chính thức* (báo cáo thống kê, xuất file ĐTB lớp, xem điểm học sinh) **phải lọc `WHERE is_draft = FALSE`** → điểm chưa duyệt không bao giờ lộ ra ngoài.
  * `GET /scores/assignment/{assignmentId}` là ngoại lệ: trả cả 2 loại kèm cờ `is_draft` để Giáo viên tiếp tục soạn bản nháp.
* **Luồng chốt điểm 3 bước (Giáo viên → Giáo vụ):**
  1. `POST /scores/batch` → lưu bảng điểm tạm (`is_draft = TRUE`).
  2. `POST /score-submissions` → gửi bảng điểm lên Giáo vụ (tạo bản ghi `PENDING`).
  3. `PUT /score-submissions/{id}/approve` → Giáo vụ duyệt: hệ thống chuyển `is_draft = FALSE` **và** đặt `teaching_assignments.is_locked = TRUE` trong **cùng một transaction** (ACID) → điểm chính thức & khóa bảng điểm.
  * Sau khi khóa, Giáo viên muốn sửa điểm → dùng luồng phúc khảo `POST /score-requests` (bảng `score_change_requests`).

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
| | | **9. Điểm Số Môn Học (Khảo Thí)** | | |
| 51 | GET | `/scores/assignment/{assignmentId}` | TEACHER, ACADEMIC | Lấy toàn bộ bảng điểm lớp theo môn học |
| 52 | GET | `/scores/student/{studentId}` | All | Tra cứu toàn bộ bảng điểm của một học sinh |
| 53 | POST | `/scores/batch` | TEACHER | Nhập và lưu điểm lớp, tự tính ĐTB (Yêu cầu 3 — `SD11`) |
| 54 | PUT | `/scores/{id}` | TEACHER | Sửa trực tiếp điểm khi bảng điểm MỞ (Yêu cầu 3 — `SD14`) |
| 55 | GET | `/scores/class/{classId}/subject/{subjectId}/yearly` | TEACHER, ACADEMIC | Xem bảng điểm TB môn cả năm HK1 & HK2 (Yêu cầu 3 — `SD12`) |
| 56 | GET | `/scores/export` | TEACHER, ACADEMIC | Xuất **điểm trung bình lớp theo năm học** ra file Excel/PDF — biểu mẫu BẢNG ĐIỂM TRUNG BÌNH LỚP (Yêu cầu 3 — `SD13`) |
| | | **10. Phúc Khảo & Yêu Cầu Sửa Điểm** | | |
| 57 | GET | `/score-requests` | ACADEMIC | Danh sách đơn xin sửa điểm chờ duyệt |
| 58 | GET | `/score-requests/my` | TEACHER | Danh sách đơn sửa điểm do GV hiện tại đã nộp |
| 59 | GET | `/score-requests/{id}` | TEACHER, ACADEMIC | Chi tiết đơn xin sửa điểm |
| 60 | POST | `/score-requests` | TEACHER | Gửi yêu cầu sửa điểm khi bảng điểm ĐÃ KHÓA (`SD25`) — hỗ trợ **đơn lẻ** & **đơn lô**, file đính kèm tùy chọn |
| 61 | POST | `/score-requests/attachment` | TEACHER | Tải file đính kèm (ảnh/PDF, tối đa 10 MB) trước khi gửi đơn |
| 62 | GET | `/score-requests/{id}/diff` | TEACHER, ACADEMIC | Bảng so sánh điểm cũ ↔ điểm mới (đơn lô) cho Giáo vụ duyệt |
| 63 | PUT | `/score-requests/{id}/approve` | ACADEMIC | Phê duyệt yêu cầu sửa điểm — **duyệt từng ô**, 1 transaction ACID + email tự động (`SD19`) |
| 64 | PUT | `/score-requests/{id}/reject` | ACADEMIC | Từ chối yêu cầu sửa điểm kèm lý do (`SD19`) |
| | | **11. Gửi Duyệt Bảng Điểm (Chốt Điểm Chính Thức)** | | |
| 65 | POST | `/score-submissions` | TEACHER | Gửi bảng điểm tạm lên Giáo vụ để duyệt & chốt (`SD23`) |
| 66 | GET | `/score-submissions` | ACADEMIC | Danh sách bảng điểm đang chờ duyệt (`?status=PENDING&page&limit`) |
| 67 | GET | `/score-submissions/my` | TEACHER | Danh sách bảng điểm GV hiện tại đã gửi |
| 68 | GET | `/score-submissions/{id}` | TEACHER, ACADEMIC | Chi tiết 1 bảng điểm chờ duyệt (kèm điểm tạm & điểm đã chốt) |
| 69 | PUT | `/score-submissions/{id}/approve` | ACADEMIC | Duyệt & chốt bảng điểm → điểm chính thức (`SD24`) |
| 70 | PUT | `/score-submissions/{id}/reject` | ACADEMIC | Từ chối bảng điểm kèm lý do (`SD24`) |
| 71 | PUT | `/score-submissions/{id}/cancel` | TEACHER | **Hủy** đơn gửi duyệt để sửa lại bảng điểm tạm (`SD23`) |
| | | **12. Thống Kê, Báo Cáo & Biểu Đồ (Chart.js)** | | |
| 72 | GET | `/reports/subject-summary` | ACADEMIC | Báo cáo tổng kết môn học: Sĩ số, Số đạt, Tỷ lệ % (Yêu cầu 4) |
| 73 | GET | `/reports/chart-data` | ACADEMIC | Dữ liệu JSON vẽ biểu đồ cột/tròn cho Chart.js (Yêu cầu 4 — `SD20`) |
| 74 | GET | `/reports/grade-summary` | ACADEMIC | Báo cáo thống kê tổng kết chung theo khối lớp |
| 75 | GET | `/reports/export/excel` | ACADEMIC | Xuất báo cáo tổng kết môn học ra Excel chuẩn mẫu |
| 76 | GET | `/reports/export/pdf` | ACADEMIC | Xuất báo cáo tổng kết môn học ra file PDF |
| | | **13. Quản Trị Tài Khoản & Phân Quyền** | | |
| 77 | GET | `/admin/users` | ACADEMIC | Danh sách người dùng hệ thống (phân trang, lọc theo role) |
| 78 | GET | `/admin/users/{id}` | ACADEMIC | Chi tiết tài khoản người dùng |
| 79 | POST | `/admin/users` | ACADEMIC | Cấp tài khoản mới cho cán bộ/GV, gửi email (`SD17`) — chốt 1 admin: xin thêm ACADEMIC → `422` |
| 80 | PUT | `/admin/users/{id}` | ACADEMIC | Cập nhật thông tin tài khoản người dùng |
| 81 | PATCH | `/admin/users/{id}/lock` | ACADEMIC | Khóa hoặc mở khóa thủ công tài khoản người dùng |
| 82 | PUT | `/admin/users/{id}/reset-password` | ACADEMIC | Đặt lại mật khẩu tạm thời cho người dùng |
| | | **14. Nhật Ký Kiểm Toán (Audit Logs)** | | |
| 83 | GET | `/admin/audit-logs` | ACADEMIC | Tra cứu lịch sử vết hoạt động của hệ thống (`SD15`) |
| 84 | GET | `/admin/audit-logs/{id}` | ACADEMIC | Xem chi tiết nội dung dữ liệu thay đổi trước/sau (JSON) |
| 85 | GET | `/admin/audit-logs/export` | ACADEMIC | Xuất file nhật ký kiểm toán ra Excel |

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
Khóa hoặc mở khóa bảng điểm môn học của một lớp (`SD18`). Khi bảng điểm bị khóa, giáo viên không thể trực tiếp sửa điểm mà phải làm đơn xin phê duyệt (`SD25`).
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

### 8. Quản Lý Điểm Số & Xuất Bảng Điểm (Yêu cầu 3)

> **🎯 Quy ước giá trị ô điểm — "NULL = chưa nhập, 0 = đã nhập" (đã chốt):**
>
> | Trạng thái ô | Giá trị DB | Tính vào ĐTB | Ý nghĩa |
> |---|---|---|---|
> | **Chưa nhập** | `NULL` (ô để trống) | ❌ Không tính | GV chưa chấm ô này — **lỗi GV**, chặn bước "Gửi duyệt" |
> | **Vắng** | `0.00` | ✅ Có tính | HS vắng kiểm tra → quy về **0 điểm** |
> | **Thi = 0 điểm** | `0.00` | ✅ Có tính | HS có dự thi nhưng làm sai hết → **0 điểm** |
> | **Đã chấm** | `0.00` – `10.00` | ✅ Có tính | Điểm thực tế |
>
> * Không dùng giá trị đặc biệt (`-1`), không cần cờ `is_absent` → đơn giản, dễ giải thích khi bảo vệ.
> * Ô `NULL` **loại khỏi cả tử số & mẫu số** của ĐTB; ô `0.00` **vẫn được tính** → HS vắng bị trừ điểm đúng như thực tế.
> * Giao diện: mỗi ô có checkbox **"Vắng"** → tự điền `0` (cách nhập nhanh, **không** đổi giá trị).

#### Bảng ràng buộc kiểm tra dữ liệu đầu vào (Validation Matrix)

**Mức 1 — Chặn ở bước "Lưu" (`POST /scores/batch`, `PUT /scores/{id}`):**
> Đây là ràng buộc **cấu trúc dữ liệu** → chặn ngay, vì lưu sai thì bảng điểm tạm cũng hỏng.

| # | Ràng buộc | Kiểm tra | Mã lỗi |
|---|---|---|---|
| A1 | Điểm nằm trong khoảng $[0.0, 10.0]$ | Mọi ô có giá trị | `422 INVALID_SCORE_RANGE` |
| A2 | Số cột điểm 15' trong `[MIN_COL_15M, MAX_COL_15M]` | So với `system_rules` | `422 INVALID_COLUMN_COUNT` |
| A3 | Số cột điểm 1 tiết trong `[MIN_COL_45M, MAX_COL_45M]` | So với `system_rules` | `422 INVALID_COLUMN_COUNT` |
| A4 | Số cột điểm thi = `NUM_COL_FINAL` (1) | So với `system_rules` | `422 INVALID_COLUMN_COUNT` |
| A5 | Không trùng `student_id` trong 1 request | Set uniqueness | `422 DUPLICATE_STUDENT_IN_BATCH` |
| A6 | `student_id` thuộc lớp của assignment | Query `class_enrollments` | `422 STUDENT_NOT_IN_ASSIGNMENT` |
| A7 | GV là người phụ trách assignment | `assignment.teacher_id == current_user.id` | `403 FORBIDDEN` |
| A8 | Bảng điểm đang mở | `teaching_assignments.is_locked == false` | `423 SCORE_TABLE_LOCKED` |
| A9 | Ô chưa nhập (`NULL`) | **Được phép** ở bước này | — |

**Mức 2 — Chặn ở bước "Gửi duyệt" (`POST /score-submissions`):**
> Đây là ràng buộc **nghiệp vụ** → GV có thể lưu dở để soạn tiếp, nhưng **không được gửi duyệt** khi dữ liệu chưa hoàn chỉnh.

| # | Ràng buộc | Kiểm tra | Mã lỗi |
|---|---|---|---|
| B1 | **Mọi ô phải được điền** — không ô nào được để trống (`NULL`) | Quét toàn bộ `scores` của assignment | `422 INCOMPLETE_SCORES` |
| B2 | Phải có ít nhất 1 học sinh có điểm | Đếm ô có giá trị | `422 NO_SCORES_TO_SUBMIT` |
| B3 | Chưa có bản ghi `PENDING` cho cùng `assignment_id` | Query `score_submissions` | `409 DUPLICATE_PENDING_SUBMISSION` |
| B4 | Bảng điểm đang mở | `teaching_assignments.is_locked == false` | `423 SCORE_TABLE_LOCKED` |
| B5 | GV là người phụ trách assignment | `assignment.teacher_id == current_user.id` | `403 FORBIDDEN` |

> **B1 là ràng buộc "không được bỏ trống"** — nó áp dụng ở bước **Gửi duyệt**, không phải bước Lưu.
> GV có thể lưu dở để soạn tiếp, nhưng **không thể gửi duyệt** khi còn ô trống.

**Công thức ĐTB (đã tính theo quy ước NULL/0):**
$$\text{ĐTB} = \frac{\sum_{\text{ô có giá trị, 15'}} \text{Điểm} \times 1 + \sum_{\text{ô có giá trị, 1 tiết}} \text{Điểm} \times 2 + \sum_{\text{ô có giá trị, thi}} \text{Điểm} \times 3}{\text{Số ô có giá trị, 15'} + \text{Số ô có giá trị, 1 tiết} \times 2 + 3_{\text{(nếu ô thi có giá trị)}}}$$
* Ô `NULL` → loại khỏi **cả tử số lẫn mẫu số** (không ảnh hưởng ĐTB).
* Ô `0.00` (vắng / thi 0 điểm) → **vẫn được tính** → HS vắng bị trừ điểm đúng như thực tế.
* Học sinh chưa có ô điểm nào → `average_score = NULL`, `is_passed = NULL` → không tính vào tỷ lệ đạt.


#### `GET /scores/assignment/{assignmentId}`
Lấy toàn bộ bảng điểm của lớp theo đúng mẫu BẢNG ĐIỂM MÔN HỌC (Lớp, Môn, Học kỳ, Năm học, Điểm 15', Điểm 1 tiết, Điểm thi).
* **Quyền:** TEACHER, ACADEMIC
* **Query Params:** `draft` (`true` | `false` | `all`, mặc định `all`)
  * `TEACHER` → mặc định `all` (cần thấy cả bản nháp để tiếp tục soạn — SD11).
  * `ACADEMIC` → mặc định `false` (chỉ xem điểm chính thức đã chốt — tránh đối chiếu nhầm với bản nháp của GV).
  * `draft=false` → **luôn** lọc `WHERE is_draft = FALSE`.
* **Response 200:**
```json
{
  "assignment_id": 5,
  "class_name": "10A1",
  "subject_name": "Toán học 10",
  "semester_name": "HK1",
  "academic_year": "2026-2027",
  "is_locked": false,
  "is_draft": true,
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
**Lưu vào BẢNG ĐIỂM TẠM:** mọi lần bấm "Lưu" ghi vào bảng `scores` với cờ `is_draft = TRUE`. Hệ thống **vẫn tính `average_score`** ngay để Giáo viên tự kiểm tra, nhưng điểm này **chưa phải điểm chính thức** — chỉ sau khi Giáo vụ duyệt (SD24) mới thành điểm chính thức (`is_draft = FALSE`).

> **🎯 Cơ chế PARTIAL UPDATE — `null` nghĩa là "KHÔNG đụng tới ô này" (đã chốt 12/11/2026):**
> * Mỗi ô điểm trong request là **tuỳ chọn**. Server chỉ `UPDATE` **những ô có giá trị khác `NULL`** trong body.
> * Ô gửi lên với giá trị `null` → **giữ nguyên giá trị đang có trong DB** (không ghi `NULL`, không xoá).
> * **Mục đích:** chống mất dữ liệu. Nếu hiểu `null` là "xoá", thì chỉ cần 1 cột chưa render kịp trên form là **xoá im lặng điểm đã chấm** → ĐTB nhảy vọt (vì ô `NULL` bị loại khỏi mẫu số).
> * Ô **chưa từng** có giá trị và gửi `null` → vẫn là `NULL` (đúng ý nghĩa "chưa nhập") → bị chặn ở bước "Gửi duyệt" bằng `422 INCOMPLETE_SCORES`.
> * **Nếu GV thực sự muốn xoá một ô đã chấm** → không làm trực tiếp ở đây; dùng `PUT /scores/{id}` với trường `clear: true` (xem bên dưới) để có audit log.
>
> Tóm lại: **`null` = "không thay đổi"**, còn **"xoá điểm đã chấm"** là hành động riêng, có ghi log.
>
> ⚠️ **Ghi chè `is_draft`:** Khi dòng điểm đã được duyệt một lần rồi Giáo vụ mở lại bảng điểm (`SD18`), server phải **giữ nguyên `is_draft = TRUE`** khi GV lưu lại — tuyệt đối không ghi đè điểm chính thức (`is_draft = FALSE`) bằng bản nháp.  
Hệ thống tự động kiểm tra số cột theo quy chế (15' có 1-5 cột, 1 tiết có 1-3 cột, thi cuối kỳ có 1 cột). Tự động kích hoạt luồng bao hàm `<<include>> Tính điểm trung bình môn`:
$$\text{ĐTB} = \frac{\sum_{\text{ô có giá trị, 15'}} \text{Điểm} \times 1 + \sum_{\text{ô có giá trị, 1 tiết}} \text{Điểm} \times 2 + \sum_{\text{ô có giá trị, thi}} \text{Điểm} \times 3}{\text{Số ô có giá trị, 15'} + \text{Số ô có giá trị, 1 tiết} \times 2 + 3_{\text{(nếu ô thi có giá trị)}}}$$

> **Công thức DUY NHẤT (áp dụng mọi nơi: lưu nháp, tính lại sau phúc khảo, báo cáo, xuất file):**
> * **Tử số** = tổng điểm của **các ô CÓ GIÁ TRỊ** (bỏ qua ô `NULL`), nhân trọng số: 15' × 1, 1 tiết × 2, thi × 3.
> * **Mẫu số** = **số ô CÓ GIÁ TRỊ** tương ứng, nhân cùng trọng số — **KHÔNG** dùng số cột theo quy chế.
> * Ô `0.00` là ô **CÓ GIÁ TRỊ** → vẫn nằm trong cả tử số và mẫu số → học sinh vắng **bị trừ điểm đúng thực tế**.
> * Ô `NULL` bị loại khỏi **cả hai** → không ảnh hưởng ĐTB, nhưng **vẫn chặn** ở bước "Gửi duyệt" (`422 INCOMPLETE_SCORES`).
> * Mọi ô đều `NULL` → `average_score = NULL`, `is_passed = NULL` → HS chưa có điểm, không tính vào tỷ lệ đạt.
>
> ⚠️ **Không dùng "số cột theo quy chế" làm mẫu số** — vì khi GV mới chấm dở (VD mới có 2/5 cột), công thức đó sẽ chia cho 5 thay vì 2 → ĐTB nhảy không kiểm soát giữa các lần lưu.
* **Quyền:** TEACHER
* **Điều kiện:** `teaching_assignments.is_locked = false`. Nếu bảng điểm đã **chốt** → **423 `SCORE_TABLE_LOCKED`**, GV phải gửi đơn phúc khảo qua `POST /score-requests`.
* **Ràng buộc kiểm tra (Mức 1 — chặn ngay ở bước "Lưu"):**
  * Mỗi điểm có giá trị phải nằm trong $[0.0, 10.0]$ → nếu sai → **422 `INVALID_SCORE_RANGE`**.
  * Số cột 15' / 1 tiết / thi phải tuân thủ `system_rules` (`MIN_COL_15M`, `MAX_COL_15M`, `MIN_COL_45M`, `MAX_COL_45M`, `NUM_COL_FINAL`) → nếu sai → **422 `INVALID_COLUMN_COUNT`**.
  * Không trùng `student_id` trong 1 request → **422 `DUPLICATE_STUDENT_IN_BATCH`**.
  * `student_id` phải thuộc lớp của assignment → **422 `STUDENT_NOT_IN_ASSIGNMENT`**.
  * GV phải là người phụ trách assignment → **403 `FORBIDDEN`**.
  * **Ô `NULL` (chưa nhập) được phép** ở bước này — GV có thể lưu dở để soạn tiếp. Ràng buộc "không được bỏ trống" chỉ áp dụng khi **Gửi duyệt** (xem `POST /score-submissions`).
  * **Partial update:** ô gửi lên với `null` → **giữ nguyên giá trị trong DB** (không xoá điểm đã chấm). Chỉ những ô **có giá trị** mới được `UPDATE`. Xem giải thích đầy đủ ở trên.
  * Ô `null` mà **chưa từng** có giá trị → vẫn `NULL` → sẽ bị chặn khi **Gửi duyệt** (`422 INCOMPLETE_SCORES`).
  * **Không được sửa khi đang có đơn gửi duyệt `PENDING`** → nếu có → **423 `SCORE_SUBMISSION_PENDING`**. GV phải **Hủy** đơn (`PUT /score-submissions/{id}/cancel`) trước rồi mới sửa được — tránh tình huống Giáo vụ duyệt một bản điểm đã bị thay đổi sau khi gửi.
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
  "message": "Lưu bảng điểm tạm và tính toán điểm trung bình môn thành công",
  "updated_count": 1,
  "is_draft": true,
  "message_hint": "Điểm đã lưu vào bảng điểm TẠM. Bấm 'Gửi duyệt' để Giáo vụ duyệt & chốt thành điểm chính thức.",
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
  "message": "Điểm số phải nằm trong khoảng từ 0.0 đến 10.0! Học sinh ID 101 có điểm 10.5 không hợp lệ.",
  "details": [
    { "student_id": 101, "column": "score_45m_1", "value": 10.5, "message": "Điểm vượt quá giới hạn 10.0" }
  ]
}
```
* **Response 422 (Số cột không hợp lệ):**
```json
{
  "error": "INVALID_COLUMN_COUNT",
  "message": "Số cột điểm 15 phút phải nằm trong khoảng 1 đến 5 cột! Hiện tại nhập 7 cột.",
  "rule_key": "MAX_COL_15M",
  "rule_value": "5",
  "received": 7
}
```
* **Response 422 (Trùng học sinh trong request):**
```json
{
  "error": "DUPLICATE_STUDENT_IN_BATCH",
  "message": "Học sinh ID 101 bị trùng trong cùng một yêu cầu lưu điểm!",
  "student_id": 101
}
```
* **Response 422 (Học sinh không thuộc lớp):**
```json
{
  "error": "STUDENT_NOT_IN_ASSIGNMENT",
  "message": "Học sinh ID 999 không thuộc lớp của lớp môn học này!",
  "student_id": 999,
  "assignment_id": 5
}
```

---

#### `GET /scores/student/{studentId}`
Toàn bộ bảng điểm 1 HS (mọi môn/kỳ). * **Quyền:** All (HS xem chính mình; TEACHER/ACADEMIC xem tất cả).

> **⚠️ Bắt buộc lọc `WHERE is_draft = FALSE`.** Đây là endpoint mà **học sinh** tự xem điểm của chính mình → nếu không lọc, học sinh có thể thấy điểm tạm (bản nháp GV đang soạn, có thể còn ô trống hoặc là điểm cũ chưa chốt). Chỉ trả về **điểm chính thức đã được Giáo vụ duyệt**.
> * Ngoại lệ: `TEACHER` xem học sinh **thuộc lớp mình phụ trách** → có thể yêu cầu `?include_draft=true` để xem cả bản nháp (cần thiết khi GV đang soạn, hỗ trợ SD11). `ACADEMIC` xem toàn trường, không cần tham số này.
> * Phân quyền phạm vi: `403` nếu HS không thuộc lớp GV phụ trách (trừ `ACADEMIC` xem toàn trường).

#### `PUT /scores/{id}`
Sửa **một ô điểm** của **một học sinh** khi bảng điểm **đang mở** (`teaching_assignments.is_locked = false`, SD14). Server từ chối **423 `SCORE_TABLE_LOCKED`** nếu bảng điểm đã **chốt** → GV phải tạo `POST /score-requests` (SD25). Bản sửa ghi vào bảng điểm tạm (`is_draft = TRUE`) & tự động tính lại `average_score` / `is_passed` (`<<include>> Tính điểm trung bình môn`).
* **Quyền:** TEACHER
* **Quyền sở hữu (chống GV sửa điểm lớp khác):**
  * `403 FORBIDDEN` nếu GV **không phải** `teaching_assignments.teacher_id` của assignment chứa dòng điểm `scores.id` này.
  * `404 NOT_FOUND` nếu `scores.id` không tồn tại.
  * `422 STUDENT_NOT_IN_ASSIGNMENT` nếu học sinh không thuộc lớp của assignment.
* **Ràng buộc bổ sung:** nếu lớp môn học đang có đơn gửi duyệt `status = PENDING` → **423 `SCORE_SUBMISSION_PENDING`** → GV phải **Hủy** đơn (`PUT /score-submissions/{id}/cancel`) trước rồi mới sửa được.
* **Kiểm tra giá trị:** `new_value` phải nằm trong $[0.0, 10.0]$ → nếu sai → **422 `INVALID_SCORE_RANGE`**. `score_column` phải thuộc **whitelist 9 cột** (`score_15m_1`..`score_15m_5`, `score_45m_1`..`score_45m_3`, `score_final`) → nếu sai → **422 `INVALID_COLUMN_NAME`**.
* **Request Body:**
```json
{
  "score_column": "score_15m_3",
  "new_value": 8.5,
  "clear": false
}
```
  * `score_column` (bắt buộc) — cột cần sửa.
  * `new_value` (bắt buộc khi `clear = false`) — giá trị mới.
  * `clear` (tuỳ chọn, mặc định `false`) — nếu `true` → **XOÁ** giá trị ô (set `NULL`) → ô đó quay lại trạng thái "chưa nhập" → sẽ chặn ở bước "Gửi duyệt". Dùng cơ chế này (thay vì gửi `null` trong `POST /scores/batch`) để **xoá điểm đã chấm có chủ đích** & để lại audit log.
* **Response 200:**
```json
{
  "message": "Cập nhật điểm thành công",
  "score_id": 901,
  "score_column": "score_15m_3",
  "old_value": 5.7,
  "new_value": 8.5,
  "average_score": 8.13,
  "is_passed": true,
  "is_draft": true
}
```

#### `GET /scores/class/{classId}/subject/{subjectId}/yearly`
Xem bảng điểm trung bình môn cả năm của lớp theo biểu mẫu quy định (Yêu cầu 3 — `SD12`): **BẢNG ĐIỂM TRUNG BÌNH LỚP** (Năm học, STT, Họ tên, Lớp, Điểm TB HK1, Điểm TB HK2). API trả kèm `avg_yearly` (ĐTB cả năm) để phục vụ xếp loại — cột này **không** đưa vào file xuất theo mẫu đề bài (xem `GET /scores/export`).
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
Xuất **điểm trung bình của lớp theo năm học** ra file Excel hoặc PDF (Yêu cầu 3 — `SD13`). File bám đúng biểu mẫu **BẢNG ĐIỂM TRUNG BÌNH LỚP** của đề bài: `Năm học | STT | Họ tên | Lớp | Điểm TB HK1 | Điểm TB HK2` — **không có cột ĐTB cả năm** trong file xuất.
* **Quyền:** TEACHER, ACADEMIC
* **Query Params:** `assignment_id=5`, `format=excel` (hoặc `pdf`)
* **Response 200:** Trả về luồng file binary (`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) kèm header `Content-Disposition: attachment`. Tên file gợi ý: `BangDiemTrungBinhLop_<Lớp>_<Môn>_<NămHọc>.xlsx`.

---

### 9. Phúc Khảo & Yêu Cầu Chỉnh Sửa Điểm (Quan hệ `<<extend>>`)

#### `GET /score-requests` / `GET /score-requests/my` / `GET /score-requests/{id}`
List đơn chờ duyệt (ACADEMIC, `?status=PENDING&page&limit`) / đơn do GV hiện tại nộp (TEACHER) / chi tiết 1 đơn (TEACHER, ACADEMIC).

#### `POST /score-requests`
Gửi đơn yêu cầu chỉnh sửa điểm khi bảng điểm đã được **CHỐT** (`teaching_assignments.is_locked = true`) (Yêu cầu 3 — `SD25`).

> **Thiết kế biểu mẫu có cấu trúc trên Web (bắt buộc):**
> Giáo viên chọn theo thứ tự **Lớp → Học sinh → Môn học → Cột điểm** (15 phút / 1 tiết / cuối kỳ). Hệ thống **tự động hiển thị Điểm hiện tại ở chế độ chỉ đọc** (không cho sửa trực tiếp) để đảm bảo trung thực. Giáo viên nhập **Điểm đề xuất sửa** + **Lý do** (chọn hoặc tự nhập) rồi gửi đơn.
>
> Hỗ trợ **2 mức** trên cùng 1 endpoint, cùng 1 luồng nghiệp vụ:
> * **Đơn lẻ** — 1 ô điểm → `changes[]` có đúng 1 phần tử.
> * **Đơn lô** — nhiều ô điểm của nhiều học sinh → `changes[]` có nhiều phần tử (mỗi học sinh 1 lần gửi, không giới hạn số lượng).

* **Quyền:** TEACHER
* **Điều kiện:** `teaching_assignments.is_locked = true` — nếu bảng điểm đang mở, GV phải sửa trực tiếp qua `PUT /scores/{id}` chứ không gửi đơn. Nếu `is_locked = false` → **422 `SCORE_TABLE_NOT_LOCKED`**.
* **Định dạng request:** hỗ trợ **2 kiểu** trong cùng 1 endpoint:
  * `application/json` — đơn không kèm file.
  * `multipart/form-data` — đơn có kèm file (trường `attachment` là file, trường `changes` là JSON string).
* **Request Body (JSON):**
```json
{
  "changes": [
    {
      "student_id": 45,
      "subject_id": 3,
      "score_column": "score_final",
      "old_value": 8.50,
      "new_value": 9.00,
      "reason": "Chấm sót ý 3 của câu hình học (+0.5đ)"
    },
    {
      "student_id": 46,
      "subject_id": 3,
      "score_column": "score_45m_2",
      "old_value": 7.00,
      "new_value": 8.00,
      "reason": "Gõ nhầm 7.0 thành 5.7 khi nhập bảng điểm"
    }
  ],
  "reason": "Chấm lại bài thi cuối kỳ môn Toán theo phúc khảo",
  "attachment_path": null,
  "attachment_type": null,
  "attachment_name": null
}
```
* **Request Body (multipart/form-data) — có file đính kèm (luôn tùy chọn):**
  * `changes` → JSON string, cùng cấu trúc như trên.
  * `reason` → lý do chung của cả đơn (áp dụng cho mọi ô trong `changes[]`).
  * `attachment` → file ảnh (`image/png`, `image/jpeg`, `image/webp`) hoặc PDF (`application/pdf`), **tối đa 10 MB**.
  * Có thể dùng `POST /score-requests/attachment` để tải file trước rồi truyền `attachment_path` trong body JSON.

> **Lưu ý về lý do & file đính kèm:**
> * `reason` là **BẮT BUỘC** ở cả 2 cấp (cấp đơn và cấp ô). Lý do nằm ở cấp đơn (`reason` của request) áp dụng cho mọi ô; lý do ở cấp ô (`changes[].reason`) ghi đè lý do chung cho ô đó — dùng khi cần giải thích riêng từng ô.
> * File đính kèm **luôn tùy chọn** — hệ thống **không** bắt buộc theo loại lý do. GV tự quyết định có cần đính kèm ảnh bài đã chấm lại hay biên bản phúc khảo để đối chiếu hay không. Với lý do đơn giản như "gõ nhầm 7.5 thành 5.7" thì không cần đính kèm.
> * `old_value` do GV gửi lên là **giá trị GV nhìn thấy**; server sẽ đối chiếu với giá trị thực tế trong `scores`. Nếu lệch → **409 `SCORE_VALUE_CONFLICT`** (có thể GV gửi trước khi GV khác sửa, hoặc đơn cũ chưa được cập nhật). Vì bảng điểm đã **CHỐT** nên `old_value` **luôn có giá trị** (không bao giờ `NULL`) — không cần xử lý nhánh "ô chưa từng nhập".
>
> * **Kịch bản thực tế gây lỗi này:** GV mở form phúc khảo lúc 8h (thấy điểm 8.5) → để đó, sang 10h Giáo vụ duyệt một đơn khác đã đổi ô đó thành 8.0 → GV submit đơn cũ (ghi `old_value = 8.5`) → server thấy giá trị hiện tại là 8.0 ≠ 8.5 → **409** → GV phải tải lại form & gửi đơn mới. Cơ chế này chống việc **ghi đè điểm mới theo thông tin đã lỗi thời**.
đơn cũ chưa cập nhật).

* **Response 201:**
```json
{
  "message": "Đã gửi yêu cầu chỉnh sửa điểm tới Giáo vụ chờ phê duyệt",
  "request_id": 12,
  "status": "PENDING",
  "is_batch": true,
  "total_changes": 2,
  "changes": [
    {
      "detail_id": 101,
      "student_id": 45,
      "student_name": "Nguyễn Văn An",
      "score_column": "score_final",
      "old_value": 8.50,
      "new_value": 9.00,
      "status": "PENDING"
    },
    {
      "detail_id": 102,
      "student_id": 46,
      "student_name": "Trần Thị Bình",
      "score_column": "score_45m_2",
      "old_value": 7.00,
      "new_value": 8.00,
      "status": "PENDING"
    }
  ],
  "attachment": null,
  "created_at": "2026-11-11T10:55:00+07:00"
}
```

---

#### `POST /score-requests/attachment`
Tải file đính kèm (ảnh/PDF) **trước** khi gửi đơn — dùng cho các client không gửi `multipart/form-data` trực tiếp.
* **Quyền:** TEACHER
* **Request:** `multipart/form-data` với trường `file`.
* **Ràng buộc:** chỉ `IMAGE` (`png`, `jpeg`, `webp`) hoặc `PDF`; tối đa **10 MB**; tên file được sanitize.
* **Response 201:**
```json
{
  "message": "Đã tải lên file đính kèm thành công",
  "attachment_path": "uploads/score_requests/2026/11/req_12_8f3a1c2.png",
  "attachment_type": "IMAGE",
  "attachment_name": "bai_thi_nguyen_van_an.png"
}
```
* **Lỗi:** `422 INVALID_ATTACHMENT_TYPE` (sai định dạng), `413 FILE_TOO_LARGE` (vượt 10 MB).

---

#### `GET /score-requests/{id}/diff`
Bảng so sánh điểm cũ ↔ điểm mới cho Giáo vụ duyệt đơn lô (nhiều ô điểm).
* **Quyền:** ACADEMIC, TEACHER (chỉ đơn của chính GV)
* **Query:** `?status=PENDING|APPROVED|REJECTED` — lọc theo trạng thái từng ô.
* **Response 200:**
```json
{
  "request_id": 12,
  "is_batch": true,
  "summary": { "total": 2, "pending": 2, "approved": 0, "rejected": 0 },
  "changes": [
    {
      "detail_id": 101,
      "student_id": 45,
      "student_name": "Nguyễn Văn An",
      "score_column": "score_final",
      "old_value": 8.50,
      "new_value": 9.00,
      "delta": 0.50,
      "status": "PENDING"
    }
  ],
  "attachment": {
    "attachment_path": "uploads/score_requests/2026/11/req_12_8f3a1c2.png",
    "attachment_type": "IMAGE",
    "attachment_name": "bai_thi.png"
  }
}
```

---

#### `PUT /score-requests/{id}/approve`
Giáo vụ phê duyệt yêu cầu sửa điểm (`SD19`). Hệ thống tự động cập nhật điểm mới và tự động tính lại Điểm Trung Bình Môn.

> **⚠️ Quy tắc bắt buộc (điểm chính thức):**
> * Điểm mới được ghi thẳng vào **điểm chính thức** → **giữ nguyên `scores.is_draft = FALSE`**. Tuyệt đối **KHÔNG** ghi vào bảng điểm tạm, nếu không điểm đã chốt sẽ bị "hạ" về bản nháp và biến mất khỏi báo cáo.
> * **KHÔNG** đụng tới `teaching_assignments.is_locked` — bảng điểm vẫn ở trạng thái **ĐÃ CHỐT** sau khi phúc khảo được duyệt.
> * Việc tính lại `average_score` & `is_passed` diễn ra trong **cùng transaction** với `UPDATE scores` (ACID).

* **Quyền:** ACADEMIC
* **Duyệt từng ô (đơn lô):** request body có `decisions[]` — mỗi phần tử là `{ "detail_id": 101, "action": "APPROVE" }` hoặc `{ "detail_id": 102, "action": "REJECT", "note": "..." }`.
  * **Đơn lẻ** (1 ô) → có thể bỏ `decisions[]`, coi như duyệt toàn bộ.
  * **Đơn lô** → `decisions[]` **bắt buộc**, nếu thiếu → **422 `DECISIONS_REQUIRED`**.
  * Ô không có trong `decisions[]` → giữ nguyên `PENDING` (Giáo vụ có thể duyệt tiếp sau).
* **Request Body (đơn lô):**
```json
{
  "decisions": [
    { "detail_id": 101, "action": "APPROVE" },
    { "detail_id": 102, "action": "REJECT", "note": "Không có bằng chứng hỗ trợ, giữ nguyên điểm cũ" }
  ],
  "approval_note": "Đã đối chiếu bài thi gốc"
}
```

> **🔒 Cơ chế Transaction & Data Consistency (điểm nhấn chính cho đồ án):**
> Toàn bộ xử lý duyệt chạy trong **một transaction ACID** duy nhất (cấp Service, dùng `db.session.begin()`):
>
> ```
> BEGIN
>   ├─ UPDATE score_change_requests SET status=?, approved_by=?, approval_note=?, resolved_at=NOW()
>   ├─ UPDATE score_change_details SET status='APPROVED', approved_by=?, resolved_at=NOW()
>   │      (cho TỪNG ô được duyệt)
>   ├─ UPDATE scores SET score_column = new_value, is_draft = FALSE
>   │      (cho TỪNG ô được duyệt — giữ nguyên is_draft = FALSE)
>   ├─ UPDATE scores SET average_score = ?, is_passed = ?
>   │      (tính lại ĐTB & trạng thái đạt/không đạt cho học sinh tương ứng)
>   ├─ INSERT INTO audit_logs (action='APPROVE_SCORE_CHANGE', ...)
>   └─ INSERT INTO email_outbox (to_email=<email GV>, subject=..., body=...)
> COMMIT
> ```
>
> * **Atomicity** — nếu 1 ô điểm lỗi (vd: tranh chấp giá trị cũ), **toàn bộ** đơn được rollback → không tồn tại trạng thái "đơn đã duyệt nhưng điểm chưa sửa".
> * **Consistency** — `scores.average_score` & `is_passed` luôn khớp với các cột điểm con; `score_change_requests.status` luôn khớp tổng hợp trạng thái các ô con.
> * **Durability** — sau `COMMIT`, dữ liệu tồn tại vĩnh viễn.
>
> **📧 Về email thông báo tự động — Outbox Pattern:**
> Mail **KHÔNG** được gửi bên trong transaction (nếu SMTP lỗi sau khi đã gửi mail nhưng trước khi commit → GV nhận mail "đã duyệt" trong khi DB rollback → mất tính nhất quán). Thay vào đó, mail được **ghi vào bảng `email_outbox` trong cùng transaction**, sau `COMMIT` worker mới gửi. Kết quả: **gửi mail tự động mà không cần thao tác tay**, và không bao giờ có mail/DB lệch nhau.

* **Response 200:**
```json
{
  "message": "Phê duyệt yêu cầu sửa điểm thành công. Điểm số mới đã được áp dụng và tính lại ĐTB.",
  "request_id": 12,
  "status": "PARTIALLY_APPROVED",
  "approved_count": 1,
  "rejected_count": 1,
  "changes": [
    {
      "detail_id": 101,
      "student_id": 45,
      "student_name": "Nguyễn Văn An",
      "score_column": "score_final",
      "old_value": 8.50,
      "new_value": 9.00,
      "applied": true,
      "new_average_score": 8.30,
      "is_passed": true,
      "is_draft": false,
      "is_locked": true
    },
    {
      "detail_id": 102,
      "student_id": 46,
      "student_name": "Trần Thị Bình",
      "score_column": "score_45m_2",
      "old_value": 7.00,
      "new_value": 8.00,
      "applied": false,
      "status": "REJECTED"
    }
  ],
  "email_queued": true
}
```

---

#### `PUT /score-requests/{id}/reject`
Giáo vụ từ chối yêu cầu sửa điểm kèm lý do (`SD19`).
* **Quyền:** ACADEMIC
* **Lưu ý:** Từ chối **không** thay đổi bất kỳ dữ liệu điểm nào (`scores` giữ nguyên `is_draft = FALSE`) và không thay đổi `is_locked`.
* **Từ chối cả đơn:** `PUT /score-requests/{id}/reject` từ chối **toàn bộ** đơn (mọi ô `PENDING` → `REJECTED`), giống như duyệt cả đơn.
* **Từ chối từng ô (đơn lô):** dùng `PUT /score-requests/{id}/approve` với `decisions[]` trong đó có phần tử `{"action": "REJECT", "note": "..."}` — hỗ trợ trạng thái `PARTIALLY_APPROVED` (có ô duyệt, có ô từ chối trong cùng đơn).
* **Transaction:** từ chối cũng chạy trong **1 transaction** (cập nhật trạng thái đơn cha + các ô con + `audit_logs` + enqueue `email_outbox` thông báo cho GV) → rollback toàn bộ nếu có lỗi.
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

### 10. Gửi Duyệt Bảng Điểm (Chốt Điểm Chính Thức)

> **Luồng nghiệp vụ:** Giáo viên nhập điểm vào **bảng điểm tạm** (`scores.is_draft = TRUE`) → bấm **"Gửi duyệt"** → Giáo vụ xem & duyệt → hệ thống chuyển điểm tạm thành **điểm chính thức** (`is_draft = FALSE`) và **khóa bảng điểm** (`teaching_assignments.is_locked = TRUE`).

#### `POST /score-submissions`
Giáo viên gửi bảng điểm tạm của một lớp môn học lên Giáo vụ để duyệt & chốt (`SD23`).
* **Quyền:** TEACHER
* **Điều kiện:**
  * `teaching_assignments.is_locked = false` — bảng điểm đang mở. Nếu đã chốt → **423 `SCORE_TABLE_LOCKED`**.
  * Không có bản ghi `PENDING` nào khác cho cùng `assignment_id` → nếu có → **409 `DUPLICATE_PENDING_SUBMISSION`** (GV phải **Hủy** đơn cũ trước: `PUT /score-submissions/{id}/cancel`).
  * Phải có ít nhất 1 dòng điểm đã nhập → nếu không → **422 `NO_SCORES_TO_SUBMIT`**.
* **⚠️ Ràng buộc bắt buộc — "không được bỏ trống" (Mức 2):**
  * **Mọi ô điểm của mọi học sinh trong lớp phải có giá trị (`NOT NULL`)** trước khi gửi duyệt. Ô nào còn `NULL` → **422 `INCOMPLETE_SCORES`**, kèm danh sách chi tiết học sinh & cột bị thiếu để GV biết chính xác cần điền gì.
  * Nhớ quy ước: ô `NULL` = **chưa nhập** (lỗi GV) · ô `0.00` = **đã nhập** (HS vắng hoặc thi 0 điểm → vẫn hợp lệ, vẫn tính vào ĐTB).
  * GV có thể **lưu dở** nhiều lần (`POST /scores/batch`) để soạn tiếp — chỉ khi bấm **"Gửi duyệt"** mới bắt buộc đầy đủ.
  * Server **quét toàn bộ** `scores` của `assignment_id` (không chỉ dòng vừa lưu) → không thể lách bằng cách gửi từng phần.
* **Request Body:**
```json
{
  "assignment_id": 5,
  "note": "Đã chấm xong 3 cột điểm 15 phút và 2 bài kiểm tra 1 tiết, điểm thi chấm ngày mai"
}
```
* **Response 201:**
```json
{
  "message": "Đã gửi bảng điểm tạm lên Giáo vụ chờ duyệt & chốt",
  "submission_id": 7,
  "assignment_id": 5,
  "status": "PENDING",
  "total_students": 38,
  "total_scores": 296,
  "submitted_at": "2026-11-11T11:20:00+07:00"
}
```
* **Response 422 (Còn ô điểm chưa nhập — chặn gửi duyệt):**
```json
{
  "error": "INCOMPLETE_SCORES",
  "message": "Còn 3 ô điểm chưa được nhập. Vui lòng nhập đủ điểm (hoặc nhập 0 nếu học sinh vắng) trước khi gửi duyệt!",
  "assignment_id": 5,
  "total_students": 38,
  "incomplete_count": 3,
  "incomplete_students": [
    {
      "student_id": 101,
      "student_name": "Nguyễn Văn An",
      "missing_columns": ["score_15m_3", "score_45m_2"]
    },
    {
      "student_id": 105,
      "student_name": "Trần Thị Bình",
      "missing_columns": ["score_final"]
    }
  ]
}
```

#### `PUT /score-submissions/{id}/cancel`
Giáo viên **hủy** đơn gửi duyệt để sửa lại bảng điểm tạm (`SD23`).
* **Quyền:** TEACHER (chỉ đơn của chính mình, và `status = PENDING`)
* **Ý nghĩa:** Khi đang có đơn `PENDING`, GV **không sửa được** bảng điểm tạm (để tránh Giáo vụ duyệt một bản đã thay đổi). Muốn sửa → **Hủy đơn** trước.
* **Hiệu lực:**
  * `score_submissions.status` → `CANCELLED`, ghi `cancelled_at` + `cancel_note`.
  * **Giữ nguyên** `scores.is_draft = TRUE` và `teaching_assignments.is_locked = FALSE` → GV sửa bảng điểm tạm rồi gửi duyệt lại được.
  * Bản ghi cũ **giữ lại làm lịch sử** (không xóa) → audit trail đầy đủ.
* **Request Body:**
```json
{
  "cancel_note": "Phát hiện chấm nhầm cột điểm 15 phút số 3, cần sửa lại trước khi gửi duyệt"
}
```
* **Response 200:**
```json
{
  "message": "Đã hủy đơn gửi duyệt. Bạn có thể sửa lại bảng điểm tạm và gửi duyệt lại.",
  "submission_id": 7,
  "status": "CANCELLED",
  "cancelled_at": "2026-11-11T11:35:00+07:00"
}
```
* **Lỗi:** `409 INVALID_SUBMISSION_STATUS` (đơn không ở trạng thái `PENDING` — ví dụ đã được duyệt/từ chối), `403 FORBIDDEN` (đơn không thuộc GV hiện tại), `404 NOT_FOUND`.

---

#### `GET /score-submissions` / `GET /score-submissions/my` / `GET /score-submissions/{id}`
List bảng điểm chờ duyệt (ACADEMIC, `?status=PENDING&page&limit`) / bảng điểm GV hiện tại đã gửi (TEACHER) / chi tiết 1 bản ghi (TEACHER, ACADEMIC).
* **Response 200 (chi tiết):**
```json
{
  "submission_id": 7,
  "assignment_id": 5,
  "class_name": "10A1",
  "subject_name": "Toán học 10",
  "semester_name": "HK1",
  "academic_year": "2026-2027",
  "teacher": { "id": 3, "full_name": "Trần Văn Giảng Viên" },
  "status": "PENDING",
  "total_students": 38,
  "total_scores": 296,
  "submitted_at": "2026-11-11T11:20:00+07:00",
  "draft_score_list": [
    {
      "student_id": 101,
      "student_code": "HS20260001",
      "full_name": "Nguyễn Văn An",
      "scores_15m": [8.0, 9.0],
      "scores_45m": [7.5],
      "score_final": 8.5,
      "average_score": 8.13
    }
  ]
}
```

#### `PUT /score-submissions/{id}/approve`
Giáo vụ **duyệt & chốt** bảng điểm (`SD24`). Hệ thống thực hiện **trong một transaction**:
1. `UPDATE scores SET is_draft = FALSE WHERE assignment_id = :assignment_id` — điểm tạm → điểm chính thức.
2. `UPDATE teaching_assignments SET is_locked = TRUE, locked_at = NOW() WHERE id = :assignment_id` — khóa bảng điểm (GV không sửa trực tiếp được nữa).
3. Ghi `audit_logs` với action `SCORE_TABLE_APPROVED`.

* **Quyền:** ACADEMIC
* **Request Body:**
```json
{
  "review_note": "Đã đối chiếu với sổ đạo bì, điểm chính thức"
}
```
* **Response 200:**
```json
{
  "message": "Đã duyệt & chốt bảng điểm. Điểm chính thức đã được công bố và bảng điểm đã khóa.",
  "submission_id": 7,
  "status": "APPROVED",
  "assignment_id": 5,
  "is_locked": true,
  "approved_students": 38,
  "reviewed_at": "2026-11-12T08:15:00+07:00"
}
```

#### `PUT /score-submissions/{id}/reject`
Giáo vụ **từ chối** bảng điểm kèm lý do (`SD24`). Hệ thống **giữ nguyên** `scores.is_draft = TRUE` và `teaching_assignments.is_locked = FALSE` → Giáo viên sửa tiếp rồi gửi lại.
* **Quyền:** ACADEMIC
* **Request Body:**
```json
{
  "review_note": "Cột điểm 15 phút thứ 2 của 5 học sinh còn trống, vui lòng nhập bổ sung rồi gửi lại"
}
```
* **Response 200:**
```json
{
  "message": "Đã từ chối bảng điểm. Giáo viên có thể chỉnh sửa và gửi lại.",
  "submission_id": 7,
  "status": "REJECTED",
  "is_draft_kept": true
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

### 13. Quản Trị Tài Khoản & Phân Quyền (`SD17`)

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

### 14. Nhật Ký Kiểm Toán (Audit Logs — `SD15`)

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

### 6. `423 Locked` — Bảng điểm đã chốt (Giáo viên)
Dùng cho `POST /scores/batch`, `PUT /scores/{id}` và `POST /score-submissions` khi `teaching_assignments.is_locked = true` — GV phải tạo `POST /score-requests` để xin sửa điểm (SD25).
```json
{
  "error": "SCORE_TABLE_LOCKED",
  "message": "Bảng điểm đã được chốt. Vui lòng gửi yêu cầu chỉnh sửa điểm qua POST /score-requests!",
  "assignment_id": 5,
  "locked_at": "2026-11-11T10:45:00+07:00"
}
```

### 7. `409 Conflict` — Trùng lặp bản ghi chờ duyệt
Dùng cho `POST /score-submissions` khi lớp môn học đã có một bản ghi đang chờ Giáo vụ duyệt.
```json
{
  "error": "DUPLICATE_PENDING_SUBMISSION",
  "message": "Bảng điểm này đã được gửi duyệt và đang chờ Giáo vụ xử lý (submission #7).",
  "assignment_id": 5,
  "pending_submission_id": 7
}
```

### 8. `422 Unprocessable Entity` — Chưa có điểm để gửi duyệt
Dùng cho `POST /score-submissions` khi Giáo viên chưa nhập ô điểm nào.
```json
{
  "error": "NO_SCORES_TO_SUBMIT",
  "message": "Chưa có điểm nào được nhập cho bảng điểm này. Vui lòng nhập điểm trước khi gửi duyệt!"
}
```

### 9. `422 Unprocessable Entity` — Bảng điểm chưa chốt nên không gửi phúc khảo
Dùng cho `POST /score-requests` khi bảng điểm đang mở (`is_locked = false`) — Giáo viên phải sửa trực tiếp qua `PUT /scores/{id}`.
```json
{
  "error": "SCORE_TABLE_NOT_LOCKED",
  "message": "Bảng điểm hiện đang mở. Vui lòng sửa điểm trực tiếp thay vì gửi yêu cầu chỉnh sửa điểm!",
  "assignment_id": 5
}
```

### 10. `409 Conflict` — Điểm hiện tại đã thay đổi so với lúc gửi đơn
Dùng cho `POST /score-requests` khi `old_value` GV gửi lên **không khớp** với giá trị thực tế trong `scores` (GV khác đã sửa trước, hoặc đơn cũ chưa được cập nhật). Tránh ghi đè điểm mới theo thông tin đã lỗi thời.
```json
{
  "error": "SCORE_VALUE_CONFLICT",
  "message": "Điểm hiện tại của học sinh đã thay đổi so với lúc bạn gửi đơn. Vui lòng tải lại điểm và gửi yêu cầu mới!",
  "student_id": 45,
  "score_column": "score_final",
  "submitted_old_value": 8.50,
  "current_value": 8.00
}
```

### 11. `422 Unprocessable Entity` — Thiếu quyết định duyệt từng ô (đơn lô)
Dùng cho `PUT /score-requests/{id}/approve` khi đơn chứa nhiều ô điểm (`is_batch = true`) nhưng body **không** có `decisions[]`.
```json
{
  "error": "DECISIONS_REQUIRED",
  "message": "Đơn sửa điểm có nhiều ô, vui lòng gửi quyết định duyệt/từ chối cho từng ô!",
  "request_id": 12,
  "total_changes": 2
}
```

### 12. `422 Unprocessable Entity` — File đính kèm sai định dạng
Dùng cho `POST /score-requests/attachment` (và `POST /score-requests` dạng multipart) khi file không phải ảnh (png/jpeg/webp) hoặc PDF.
```json
{
  "error": "INVALID_ATTACHMENT_TYPE",
  "message": "Chỉ chấp nhận file ảnh (PNG, JPEG, WEBP) hoặc file PDF!",
  "allowed_types": ["image/png", "image/jpeg", "image/webp", "application/pdf"],
  "received_type": "application/zip"
}
```

### 13. `413 Payload Too Large` — File đính kèm vượt quá 10 MB
Dùng cho `POST /score-requests/attachment` khi file tải lên lớn hơn 10 MB.
```json
{
  "error": "FILE_TOO_LARGE",
  "message": "Kích thước file đính kèm vượt quá giới hạn 10 MB!",
  "max_size_mb": 10
}
```

### 14. `422 Unprocessable Entity` — Còn ô điểm chưa nhập (chặn gửi duyệt)
Dùng cho `POST /score-submissions` khi còn ô điểm `NULL` (chưa nhập) trong bảng điểm tạm của lớp môn học. Áp dụng quy ước **NULL = chưa nhập, 0 = đã nhập**.
```json
{
  "error": "INCOMPLETE_SCORES",
  "message": "Còn 3 ô điểm chưa được nhập. Vui lòng nhập đủ điểm (hoặc nhập 0 nếu học sinh vắng) trước khi gửi duyệt!",
  "assignment_id": 5,
  "total_students": 38,
  "incomplete_count": 3,
  "incomplete_students": [
    {
      "student_id": 101,
      "student_name": "Nguyễn Văn An",
      "missing_columns": ["score_15m_3", "score_45m_2"]
    }
  ]
}
```

### 15. `422 Unprocessable Entity` — Số cột điểm không hợp lệ
Dùng cho `POST /scores/batch` khi số cột điểm 15' / 1 tiết / thi vi phạm `system_rules` (`MIN_COL_15M`, `MAX_COL_15M`, `MIN_COL_45M`, `MAX_COL_45M`, `NUM_COL_FINAL`).
```json
{
  "error": "INVALID_COLUMN_COUNT",
  "message": "Số cột điểm 15 phút phải nằm trong khoảng 1 đến 5 cột! Hiện tại nhập 7 cột.",
  "rule_key": "MAX_COL_15M",
  "rule_value": "5",
  "received": 7
}
```

### 16. `422 Unprocessable Entity` — Trùng học sinh trong 1 request
Dùng cho `POST /scores/batch` khi body chứa trùng `student_id`.
```json
{
  "error": "DUPLICATE_STUDENT_IN_BATCH",
  "message": "Học sinh ID 101 bị trùng trong cùng một yêu cầu lưu điểm!",
  "student_id": 101
}
```

### 17. `422 Unprocessable Entity` — Học sinh không thuộc lớp của bảng điểm
Dùng cho `POST /scores/batch` khi `student_id` không có trong `class_enrollments` của lớp môn học.
```json
{
  "error": "STUDENT_NOT_IN_ASSIGNMENT",
  "message": "Học sinh ID 999 không thuộc lớp của lớp môn học này!",
  "student_id": 999,
  "assignment_id": 5
}
```

### 18. `423 Locked` — Đang có đơn gửi duyệt, chưa thể sửa điểm
Dùng cho `POST /scores/batch` và `PUT /scores/{id}` khi lớp môn học đang có bản ghi `score_submissions` với `status = 'PENDING'`. GV phải **Hủy** đơn (`PUT /score-submissions/{id}/cancel`) rồi mới sửa được — tránh tình huống Giáo vụ duyệt một bản điểm đã bị thay đổi sau khi gửi.
```json
{
  "error": "SCORE_SUBMISSION_PENDING",
  "message": "Bảng điểm đang được gửi duyệt. Vui lòng hủy đơn gửi duyệt trước khi sửa điểm!",
  "assignment_id": 5,
  "pending_submission_id": 7,
  "cancel_url": "/api/v1/score-submissions/7/cancel"
}
```

### 19. `409 Conflict` — Không hủy được đơn gửi duyệt
Dùng cho `PUT /score-submissions/{id}/cancel` khi đơn không ở trạng thái `PENDING` (ví dụ đã được duyệt hoặc đã bị từ chối).
```json
{
  "error": "INVALID_SUBMISSION_STATUS",
  "message": "Chỉ có thể hủy đơn đang ở trạng thái chờ duyệt! Đơn hiện tại đã được duyệt.",
  "submission_id": 7,
  "current_status": "APPROVED"
}
```

### 20. `500 Internal Server Error` — Lỗi hệ thống máy chủ
Xảy ra khi lỗi không thuộc các trường hợp đã được xử lý ở trên (lỗi DB, lỗi không lường trước).
```json
{
  "error": "SCORE_TABLE_LOCKED",
  "message": "Bảng điểm đã khóa. Vui lòng gửi yêu cầu chỉnh sửa điểm qua POST /score-requests!",
  "assignment_id": 5,
  "locked_at": "2026-11-11T10:45:00+07:00"
}
```

```json
{
  "error": "INTERNAL_SERVER_ERROR",
  "message": "Đã xảy ra sự cố phía máy chủ. Vui lòng liên hệ bộ phận kỹ thuật để được hỗ trợ!"
}
```