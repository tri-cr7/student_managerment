# Phân tích Yêu Cầu — Hệ Thống Quản Lý Học Sinh / Sinh Viên

## 1. Tổng quan dự án

**Tên dự án:** Hệ Thống Quản Lý Học Sinh / Sinh Viên  
**Mô tả:** Hệ thống phần mềm web chuyên biệt phục vụ công tác tin học hóa quy trình quản lý học vụ tại các trường trung học phổ thông / cơ sở giáo dục, bao gồm: tiếp nhận hồ sơ đầu vào, phân bổ danh sách lớp theo khối, quản lý quy trình nhập điểm - tính điểm trung bình học kỳ tự động, xuất báo cáo thống kê trực quan bằng biểu đồ (Chart.js), quản lý phê duyệt sửa điểm và quản trị cấu hình quy chế động theo thông tư quy định.

**Bối cảnh:** Quy trình quản lý thủ công qua sổ sách hoặc bảng tính Excel phân tán gây ra nhiều sai sót trong tính toán điểm số, khó khăn trong việc kiểm soát các quy định thay đổi (độ tuổi tiếp nhận, sĩ số lớp tối đa), mất nhiều thời gian tổng hợp báo cáo học vụ cho ban giám hiệu, và tiềm ẩn nguy cơ chỉnh sửa điểm trái phép khi không có cơ chế khóa bảng điểm và phê duyệt sửa điểm chặt chẽ.

**Giải pháp:** Xây dựng ứng dụng web phân tầng theo kiến trúc MVC kết hợp nguyên lý Clean Code (Service - Repository Layer) và mô hình phân tích BCE (Boundary - Control - Entity). Hệ thống tích hợp bảng cấu hình quy chế linh hoạt (`system_rules`), cơ chế xác thực bảo mật đa tầng (chống Brute-force, phân quyền RBAC), quy trình phê duyệt sửa điểm bằng workflow, và hỗ trợ trực quan hóa dữ liệu bằng Chart.js trên nền tảng Python Flask và MySQL.

---

## 2. Công nghệ sử dụng

| Thành phần | Công nghệ / Thư viện | Phiên bản | Ghi chú kiến trúc |
|------------|----------------------|-----------|-------------------|
| **Backend Framework** | Python (Flask Framework) | 3.x | Kiến trúc phân tầng (Blueprints, Service, Repository) |
| **ORM / Data Access** | SQLAlchemy / PyMySQL | - | Trừu tượng hóa truy vấn, chống tấn công SQL Injection |
| **Database** | MySQL | 8.x | Chuẩn hóa dữ liệu 3NF, lưu trữ cấu hình quy chế động |
| **Frontend UI** | Jinja2 Templates, HTML5, CSS thuần | - | Giao diện chuẩn Semantic Web, tùy biến CSS không phụ thuộc framework |
| **Data Visualization** | Chart.js | - | Trực quan hóa dữ liệu thống kê môn học qua biểu đồ cột và tròn |
| **Bảo mật & Xác thực** | Flask-JWT-Extended (chính cho API) + Flask-Session (fallback `/admin`), BCrypt cost ≥ 12 | - | JWT Bearer `expires_in = 1800s` (30 phút, trùng timeout session); logout = xóa token client + hủy session, không cần blacklist; xem chốt thống nhất tại `API.md` §Quy ước chung |
| **External Service** | SMTP Mail Server | - | Gửi email thông báo cấp tài khoản và gửi mã xác nhận/kích hoạt |

### Kiến trúc tổng thể (Architecture Overview)

```
┌────────────────────────────────────────────────────────┐
│                   Giao diện (Frontend)                 │
│      Jinja2 Templates + Pure CSS + Chart.js (UI)       │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP Requests (Form / AJAX)
                            ▼
┌────────────────────────────────────────────────────────┐
│             Tầng Điều Hướng (Controller)               │
│   Flask Blueprints (Auth, Staff, Teacher, Academic)    │
└───────────────────────────┬────────────────────────────┘
                            │ Gọi phương thức nghiệp vụ
                            ▼
┌────────────────────────────────────────────────────────┐
│             Tầng Nghiệp Vụ (Service Layer)             │
│    Business Rules, Validation, Tính ĐTB, Thống Kê      │
└───────────────────────────┬────────────────────────────┘
                            │ Gọi phương thức truy xuất
                            ▼
┌────────────────────────────────────────────────────────┐
│           Tầng Truy Xuất (Repository Layer)            │
│       Data Access Objects / SQLAlchemy Models (Entity)  │
└───────────────────────────┬────────────────────────────┘
                            │ SQL Queries
                            ▼
┌───────────────────────────┴────────────────────────────┐
│                    MySQL Database                      │
│   (users, students, classes, scores, system_rules)     │
└────────────────────────────────────────────────────────┘
```

---

## 3. Đối tượng sử dụng (3 Roles kế thừa từ `Người dùng`)

Hệ thống thiết lập 3 Actor chuyên biệt cùng kế thừa từ Actor cha `Người dùng` để sử dụng chung cơ chế đăng nhập, đổi mật khẩu và bảo vệ phiên:

```
                  ┌──────────────────────┐
                  │      Người dùng      │
                  │ (Xác thực, Đổi MK)   │
                  └──────────▲───────────┘
                             │ Kế thừa (Generalization)
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────┴────────┐   ┌───────┴────────┐   ┌───────┴────────┐
│   Nhân viên    │   │   Giáo viên    │   │    Giáo vụ     │
│    (STAFF)     │   │   (TEACHER)    │   │(ACADEMIC/ADMIN)│
└────────────────┘   └────────────────┘   └────────────────┘
```

### 3.1 Người dùng (USER — Actor cha)
Đối tượng dùng chung cho tất cả các nhân sự trong trường học có tài khoản truy cập vào hệ thống. Thực hiện các thao tác xác thực cơ bản: Đăng nhập (với cơ chế đếm số lần sai và khóa tài khoản khi $\ge 5$ lần), Đăng xuất, và Đổi mật khẩu cá nhân.

### 3.2 Nhân viên giáo vụ hồ sơ (STAFF — Actor con)
Chịu trách nhiệm trực tiếp về tiếp nhận hồ sơ học sinh đầu vào, kiểm tra điều kiện độ tuổi theo quy định, lập danh sách lớp sinh hoạt theo các khối 10, 11, 12, điều chuyển lớp học khi cần thiết, cập nhật lý lịch, import danh sách từ Excel và tra cứu / in hồ sơ học sinh.

### 3.3 Giáo viên / Giảng viên (TEACHER — Actor con)
Chịu trách nhiệm về chuyên môn giảng dạy: tra cứu danh sách lớp phụ trách, nhập các cột điểm thành phần (15 phút, 1 tiết, thi cuối kỳ) cho học sinh của một lớp theo đúng quy chế số cột vào **bảng điểm tạm**, gửi bảng điểm lên Giáo vụ duyệt để **chốt thành điểm chính thức**, xem và xuất bảng điểm trung bình lớp theo năm học. Khi bảng điểm đã được chốt, giáo viên tạo đơn yêu cầu sửa điểm gửi Giáo vụ.

### 3.4 Giáo vụ / Quản trị viên (ACADEMIC / ADMIN — Actor con)
Người quản trị cao nhất của hệ thống học vụ: quản lý danh mục môn học, phân công giảng dạy, cấp phát tài khoản và phân quyền người dùng (gửi thông tin qua Mail Server), mở/khóa bảng điểm của các môn học, phê duyệt yêu cầu sửa điểm của giáo viên, xem báo cáo tổng kết môn học kèm biểu đồ Chart.js, xem nhật ký hệ thống và thay đổi các quy định hệ thống (`system_rules`).

---

## 4. Bảng ánh xạ 1:1 Toàn Bộ Use Case sang Sequence Diagram

Mỗi Use Case trên sơ đồ Use Case Astah được chuẩn hóa 1:1 tương ứng với một sơ đồ Sequence Diagram theo mô hình phân tích BCE (Boundary - Control - Entity):

| STT | Use Case trên Astah | Sơ đồ Sequence Diagram (1:1) | Actor thực hiện | Ràng buộc nghiệp vụ theo Đề bài |
|:---:|---------------------|-------------------------------|-----------------|---------------------------------|
| **I** | **Phân hệ Người dùng (Xác thực)** | | | |
| 1 | `Đăng nhập` (đăng ký public ĐÃ KHÓA — chỉ ACADEMIC cấp ở SD17) | `SD01_DangNhap` | `NguoiDung` | Chống brute-force: sai $\ge 5$ lần thì khóa tài khoản; JWT Bearer access 30 phút + refresh token 7 ngày (`POST /auth/refresh`) + `redirect_url` theo Role; quên MK tự phục vụ qua mail OTP 6 số (`POST /auth/forgot-password` → `POST /auth/reset-password {email, otp_code, ...}`, hết hạn `OTP_EXPIRE_MINUTES=5`p, 1 lần dùng, sai quá `OTP_MAX_ATTEMPTS=5` thì hủy, chống enumerate); đổi MK đã đăng nhập 2 bước OTP (`POST /profile/change-password/request` → `/confirm`); tài khoản do ACADEMIC cấp (`POST /admin/users`), admin đầu tiên seed từ DB. |
| 2 | `Đổi mật khẩu` | `SD02_DoiMatKhau` | `NguoiDung` | Xác thực mật khẩu cũ, mật khẩu mới phải MẠNH (≥8 ký tự + Hoa + thường + số + đặc biệt, đồng chuẩn MK tạm admin sinh), băm BCrypt; đổi xong ghi audit `CHANGE_PASSWORD` + gửi mail cảnh báo. |
| **II** | **Phân hệ Nhân viên (Hồ sơ & Lớp học)** | | | |
| 3 | `Tiếp nhận hồ sơ học sinh` | `SD03_TiepNhanHoSoHocSinh` | `NhanVien` | **Yêu cầu 1:** Độ tuổi tiếp nhận từ 15 đến 20 tuổi ($15 \le \text{Tuổi} \le 20$) lấy từ `QuyDinh`. |
| 4 | `Import danh sách học sinh từ Excel` | `SD04_ImportHocSinhExcel` | `NhanVien` | Đọc file Excel/CSV, validate từng dòng (tuổi/trùng mã), lưu các dòng hợp lệ + trả `success_count/failed_count/errors[{row, reason}]` (partial success, chốt theo `API.md`). |
| 5 | `Lập danh sách lớp` | `SD05_LapDanhSachLop` | `NhanVien` | **Yêu cầu 2:** Có 3 khối (10, 11, 12); mỗi lớp có tối đa 40 học sinh ($\text{Sĩ số} \le 40$). |
| 6 | `Điều chỉnh danh sách lớp` | `SD06_DieuChinhDanhSachLop` | `NhanVien` | **Yêu cầu 2:** Chuyển lớp cho học sinh; kiểm tra sĩ số lớp tiếp nhận không vượt quá 40 học sinh. |
| 7 | `Cập nhật hồ sơ học sinh` | `SD07_CapNhatHoSoHocSinh` | `NhanVien` | Tìm kiếm học sinh, kiểm tra ràng buộc duy nhất (Email, CCCD/SĐT) và cập nhật thông tin. |
| 8 | `Tra cứu hồ sơ học sinh` | `SD08_TraCuuVaInHoSoHocSinh` | `NhanVien` | Tìm kiếm đa tiêu chí, tích hợp điểm mở rộng `<<extend>> In hồ sơ học sinh` xuất định dạng in ấn/PDF. |
| **III** | **Phân hệ Giáo viên (Giảng dạy & Điểm số)** | | | |
| 9 | `Tra cứu danh sách lớp phụ trách` | `SD09_TraCuuLopPhuTrach` | `GiaoVien` | Truy vấn các lớp học phần/lớp bộ môn được phân công giảng dạy trong học kỳ. |
| 10 | ~~`Điểm danh học sinh`~~ | ~~`SD10_DiemDanhHocSinh`~~ | ~~`GiaoVien`~~ | ~~*Đã loại bỏ khỏi phạm vi đề bài (Yêu cầu 3 chỉ quy định nhập điểm & xuất điểm trung bình lớp) — xem §4.1*~~ |
| 11 | `Nhập điểm môn học` | `SD11_NhapDiemMonHoc` | `GiaoVien` | **Yêu cầu 3:** 15 phút (1-5 cột), 1 tiết (1-3 cột), 1 điểm thi; chỉ khi bảng điểm **MỞ** (`is_locked = false`, chốt → SD25) & **không có đơn gửi duyệt `PENDING`** (đang có → GV phải Hủy đơn, xem SD23); ghi vào **bảng điểm tạm** (`is_draft = TRUE`); `<<include>> Tính điểm trung bình môn`. **Quy ước:** ô `NULL` = chưa nhập, ô `0.00` = đã nhập (vắng / thi 0 điểm, **vẫn tính vào ĐTB**). Ràng buộc Mức 1 (điểm 0–10, số cột theo `system_rules`, không trùng HS) → chặn ngay ở bước Lưu — xem §4.2. |
| 12 | `Xem bảng điểm trung bình lớp` | `SD12_XemBangDiemTrungBinhLop` | `GiaoVien` | **Yêu cầu 3:** Xem bảng điểm trung bình lớp theo năm học theo biểu mẫu **BẢNG ĐIỂM TRUNG BÌNH LỚP** (chỉ đọc điểm chính thức `is_draft = FALSE`); `<<include>> Tính điểm trung bình môn`. |
| 13 | `Xuất điểm trung bình lớp` | `SD13_XuatBangDiemTrungBinhLop` | `GiaoVien` | **Yêu cầu 3:** Xuất điểm trung bình lớp theo năm học ra file Excel/PDF đúng biểu mẫu **BẢNG ĐIỂM TRUNG BÌNH LỚP**. |
| 14 | `Sửa điểm học sinh` | `SD14_SuaDiemHocSinh` | `GiaoVien` | **Yêu cầu 3:** Sửa 1 ô điểm khi bảng điểm **đang MỞ** → ghi vào **bảng điểm tạm** (`is_draft = TRUE`); `<<include>> Tính điểm trung bình môn`. **Chặn** nếu bảng điểm đã CHỐT (→ SD25) hoặc đang có đơn gửi duyệt `PENDING` (**423 `SCORE_SUBMISSION_PENDING`** → GV phải Hủy đơn trước). |
| 23 | `Gửi bảng điểm lên duyệt` | `SD23_GuiBangDiemLenDuyet` | `GiaoVien` | **Bổ trợ cho SD11:** Sau khi nhập xong bảng điểm tạm, GV bấm "Gửi duyệt" → **kiểm tra không còn ô điểm `NULL` (chưa nhập)** → nếu còn thì chặn **422 `INCOMPLETE_SCORES`** kèm danh sách HS & cột bị thiếu → tạo bản ghi `score_submissions` (trạng thái `PENDING`) cho Giáo vụ. **Kèm `<<extend>> Hủy đơn gửi duyệt`** (`PUT /score-submissions/{id}/cancel`) → GV tự hủy để sửa lại bảng điểm tạm rồi gửi lại. Ràng buộc Mức 2 — xem §4.2. |
| 25 | `Gửi yêu cầu chỉnh điểm` | `SD25_GuiYeuCauChinhDiem` | `GiaoVien` | **Phúc khảo (bảng điểm đã CHỐT):** GV điền **biểu mẫu có cấu trúc** (Lớp → Học sinh → Môn học → Cột điểm), điểm hiện tại hiển thị **chỉ đọc**, nhập **điểm đề xuất** + **lý do (bắt buộc)**, **đính kèm ảnh/PDF tùy chọn**; hỗ trợ **đơn lẻ** & **đơn lô** (nhiều ô điểm). Server đối chiếu `old_value` (lệch → **409 `SCORE_VALUE_CONFLICT`**) → tạo đơn chờ **SD19** (Giáo vụ duyệt). |
| **IV** | **Phân hệ Giáo vụ / Quản trị (Học vụ & Báo cáo)** | | | |
| 15 | `Xem nhật ký hệ thống` | `SD15_XemNhatKyHeThong` | `GiaoVu` | Audit log: Tra cứu lịch sử truy cập, sửa đổi điểm số và thay đổi quy định. |
| 16 | `Phân công giảng dạy` | `SD16_PhanCongGiangDay` | `GiaoVu` | Gán giáo viên giảng dạy bộ môn cho các lớp học theo từng năm học/học kỳ. |
| 17 | `Quản lý tài khoản và phân quyền` | `SD17_QuanLyTaiKhoanVaPhanQuyen` | `GiaoVu` | Cấp tài khoản (`STAFF`, `TEACHER`, `ACADEMIC`), băm BCrypt, tích hợp gửi mail kích hoạt qua `MailServer`; chốt an toàn: không tự khóa chính mình (400), giữ đúng 1 ACADEMIC duy nhất: xin thêm ACADEMIC → 422; không tự khóa chính mình (400); admin gốc bất khả xâm phạm qua API, admin thường không được động vào admin khác (403). |
| 18 | `Khoá mở bảng điểm` | `SD18_KhoaMoBangDiem` | `GiaoVu` | Mở/Khoá bảng điểm của một môn học/lớp học. Cờ `is_locked` nay mang ý nghĩa **"đã chốt"** — Giáo vụ có thể mở lại để GV sửa & gửi duyệt lại (xem §4.1). |
| 19 | `Phê duyệt yêu cầu chỉnh điểm` | `SD19_PheDuyetYeuCauChinhDiem` | `GiaoVu` | Duyệt hoặc từ chối các đơn xin sửa điểm của Giáo viên — **duyệt từng ô** (đơn lô có thể duyệt 15/20 ô, từ chối 5 ô); **1 transaction ACID** ghi điểm mới vào bảng điểm chính thức + tính lại ĐTB + ghi `audit_logs` + enqueue `email_outbox` → **gửi mail thông báo tự động** cho GV. |
| 20 | `Xem báo cáo thống kê` | `SD20_XemBaoCaoThongKe` | `GiaoVu` | **Yêu cầu 4:** Điểm đạt $\ge 5.0$, tính số lượng đạt & tỷ lệ %; `<<include>> Vẽ biểu đồ báo cáo` (Chart.js). |
| 21 | `Thay đổi quy định` | `SD21_ThayDoiQuyDinh` | `GiaoVu` | **Yêu cầu 5:** Đổi quy chế (`system_rules`); validate logic: `MIN_AGE < MAX_AGE`, `MAX_CLASS_SIZE > 0`, `MIN_COL ≤ MAX_COL`, `0 ≤ PASSING_SCORE ≤ 10`, `MAX_LOGIN_ATTEMPTS > 0`. |
| 22 | `Quản lý danh mục môn học` | `SD22_QuanLyDanhMucMonHoc` | `GiaoVu` | **Yêu cầu 5:** Quản lý môn học các khối lớp (Thêm, Xóa, Cập nhật, Tìm kiếm môn học). |
| 24 | `Duyệt & chốt bảng điểm` | `SD24_DuyetVaChotBangDiem` | `GiaoVu` | **Bổ trợ:** Giáo vụ xem bảng điểm chờ duyệt → **duyệt** (`is_draft = FALSE` + `is_locked = TRUE`) hoặc **từ chối** (giữ bản nháp cho GV sửa lại). |

---

## 4.1 Phạm vi áp dụng cho Phân hệ Giáo viên (đối chiếu Yêu cầu 3 của đề bài)

**Bảng chiếu Use Case ↔ Biểu mẫu / Quy định áp dụng:**

| SD | Use Case | Biểu mẫu / Quy định áp dụng | Ghi chú |
|:---:|---|---|---|
| **SD09** | `Tra cứu danh sách lớp phụ trách` | — | **Bổ trợ**: điều kiện tiên quyết để GV biết lớp/môn/kỳ nào được nhập điểm (nguồn: `teaching_assignments`) |
| **SD11** | `Nhập điểm môn học` | **BẢNG ĐIỂM MÔN HỌC** — STT, Họ tên, Điểm 15' (1–5 cột), Điểm 1 tiết (1–3 cột), Điểm thi (1 cột) | **Trọng tâm Yêu cầu 3** — ghi vào bảng điểm tạm |
| **SD12** | `Xem bảng điểm trung bình lớp` | **BẢNG ĐIỂM TRUNG BÌNH LỚP** — Năm học, STT, Họ tên, Lớp, Điểm TB HK1, Điểm TB HK2 | **Trọng tâm Yêu cầu 3** |
| **SD13** | `Xuất điểm trung bình lớp` | **BẢNG ĐIỂM TRUNG BÌNH LỚP** (xuất Excel/PDF) | **Trọng tâm Yêu cầu 3** |
| **SD14** | `Sửa điểm học sinh` | Bảng điểm **MỞ** → sửa trực tiếp (vào bảng tạm) | **Bổ trợ** — sửa nháp, chỉ khi bảng điểm đang mở & không có đơn `PENDING` (đi kèm SD11, SD23, SD25) |
| **SD25** | `Gửi yêu cầu chỉnh điểm` | Bảng điểm **đã CHỐT** → biểu mẫu có cấu trúc + lý do (bắt buộc) + file đính kèm (tùy chọn) | **Bổ trợ** — cơ chế phúc khảo sau khi chốt (đi kèm SD19) |
| **SD23** | `Gửi bảng điểm lên duyệt` | Bảng điểm tạm (`scores.is_draft = TRUE`) — **không ô nào được để trống** | **Bổ trợ cho SD11** — điều kiện để điểm tạm trở thành điểm chính thức (đi kèm SD24). Ràng buộc "không được bỏ trống" — xem §4.2. Kèm `<<extend>> Hủy đơn gửi duyệt` |

**Endpoint hỗ trợ (không tách use case riêng — thao tác read-only):**
* `GET /score-submissions/my` → Giáo viên theo dõi trạng thái các bảng điểm mình đã gửi duyệt (`PENDING` / `APPROVED` / `REJECTED` / `CANCELLED`).
* `GET /score-requests/my` → Giáo viên theo dõi các đơn phúc khảo mình đã gửi.
* `GET /scores/assignment/{assignmentId}?draft=true` → Giáo viên xem lại bảng điểm tạm để soạn tiếp.

**Luồng chốt điểm đầy đủ (Giáo viên → Giáo vụ):**
```
GV nhập điểm (SD11)          → POST /scores/batch       → ghi vào BẢNG ĐIỂM TẠM (is_draft = TRUE), vẫn tính ĐTB để GV tự kiểm tra
GV bấm "Gửi duyệt" (SD23)   → POST /score-submissions  → tạo bản ghi score_submissions (PENDING) cho Giáo vụ
GV đổi ý (SD23)             → PUT .../cancel           → status = CANCELLED, giữ nguyên is_draft = TRUE → GV sửa lại được rồi gửi duyệt lại
Giáo vụ xem & duyệt (SD24)  → PUT .../approve          → is_draft = FALSE  +  teaching_assignments.is_locked = TRUE  (cùng 1 transaction ACID)
                                                                    ↓
                                                          ĐIỂM CHÍNH THỨC — báo cáo & xuất file mới đọc được điểm này
Giáo vụ từ chối (SD24)      → PUT .../reject           → giữ nguyên is_draft = TRUE, GV sửa tiếp rồi gửi lại
```

> **Vòng đời trạng thái đơn gửi duyệt:** `PENDING` → (`CANCELLED` do GV hủy | `REJECTED` do Giáo vụ từ chối | `APPROVED` do Giáo vụ duyệt).
> * Đang `PENDING` → GV **không sửa được** bảng điểm tạm (**423 `SCORE_SUBMISSION_PENDING`**) → phải **Hủy** trước.
> * Đã `APPROVED` → bảng điểm **đã khóa** → GV muốn sửa phải gửi **đơn phúc khảo** (SD25 → SD19).

**Ý nghĩa mới của cờ `teaching_assignments.is_locked`:**
* `is_locked = FALSE` → Bảng điểm **đang mở**: GV nhập điểm vào **bảng điểm tạm** và sửa thoải mái, **không cần xin quyền**.
* `is_locked = TRUE` → Bảng điểm **đã chốt**: điểm chính thức (`is_draft = FALSE`). GV **không** sửa trực tiếp nữa → phải gửi đơn phúc khảo qua `POST /score-requests` (bảng `score_change_requests`).

**Sau khi bảng điểm đã chốt**, muốn sửa điểm → GV dùng luồng phúc khảo **SD25** (`POST /score-requests` → SD19 Giáo vụ duyệt). Bảng `score_change_requests` giữ nguyên vai trò, không thay đổi.

### 4.2 Ràng buộc nhập điểm & điều kiện trước khi gửi duyệt

#### 🎯 Quy ước giá trị ô điểm — "NULL = chưa nhập, 0 = đã nhập" (đã chốt)

| Trạng thái ô | Giá trị DB | Tính vào ĐTB | Ý nghĩa nghiệp vụ |
|---|---|---|---|
| **Chưa nhập** | `NULL` (ô để trống trên form) | ❌ Không tính | GV chưa chấm ô này — **lỗi GV**, chặn bước "Gửi duyệt" |
| **Vắng** | `0.00` | ✅ Có tính | HS vắng kiểm tra → quy về **0 điểm** |
| **Thi = 0 điểm** | `0.00` | ✅ Có tính | HS có dự thi nhưng làm sai hết → **0 điểm** |
| **Đã chấm** | `0.00` – `10.00` | ✅ Có tính | Điểm thực tế |

* **Không** dùng giá trị đặc biệt (`-1`) và **không** cần cờ `is_absent` → đơn giản, dễ giải thích khi bảo vệ đồ án.
* Ô `NULL` **loại khỏi cả tử số & mẫu số** của ĐTB; ô `0.00` **vẫn được tính** → HS vắng bị trừ điểm đúng như thực tế.
* **Công thức DUY NHẤT (dùng ở mọi nơi):** mẫu số = **số ô CÓ GIÁ TRỊ** (× trọng số 1 / 2 / 3), **KHÔNG** dùng "số cột theo quy chế" — nếu dùng số cột, khi GV mới chấm dở (2/5 cột) ĐTB sẽ nhảy giữa các lần lưu.
* **Partial update khi lưu:** ô gửi lên với `null` → **giữ nguyên giá trị trong DB** (không xoá điểm đã chấm). Xoá điểm có chủ đích → `PUT /scores/{id}` với `clear: true` (có audit log).
* Giao diện: mỗi ô có checkbox **"Vắng"** → tự điền `0` (cách nhập nhanh cho GV, **không** làm thay đổi giá trị).

#### Ràng buộc Mức 1 — chặn ở bước "Lưu" (SD11)

> Ràng buộc **cấu trúc dữ liệu** → chặn ngay, vì lưu sai thì bảng điểm tạm cũng hỏng.

| # | Ràng buộc | Kiểm tra | Mã lỗi |
|---|---|---|---|
| A1 | Điểm nằm trong khoảng $[0.0, 10.0]$ | Mọi ô có giá trị | `422 INVALID_SCORE_RANGE` |
| A2 | Số cột điểm 15' trong `[MIN_COL_15M, MAX_COL_15M]` | `system_rules` | `422 INVALID_COLUMN_COUNT` |
| A3 | Số cột điểm 1 tiết trong `[MIN_COL_45M, MAX_COL_45M]` | `system_rules` | `422 INVALID_COLUMN_COUNT` |
| A4 | Số cột điểm thi = `NUM_COL_FINAL` (1) | `system_rules` | `422 INVALID_COLUMN_COUNT` |
| A5 | Không trùng `student_id` trong 1 request | Set uniqueness | `422 DUPLICATE_STUDENT_IN_BATCH` |
| A6 | `student_id` thuộc lớp của assignment | `class_enrollments` | `422 STUDENT_NOT_IN_ASSIGNMENT` |
| A7 | GV là người phụ trách assignment | `assignment.teacher_id` | `403 FORBIDDEN` |
| A8 | Bảng điểm đang mở | `is_locked == false` | `423 SCORE_TABLE_LOCKED` |
| A9 | Ô chưa nhập (`NULL`) | **Được phép** ở bước này | — |
| A10 | Không có đơn gửi duyệt đang `PENDING` cho assignment | `score_submissions.status = 'PENDING'` | `423 SCORE_SUBMISSION_PENDING` (GV phải **Hủy** đơn trước rồi mới sửa được) |
| A11 | GV là người phụ trách **đúng** assignment chứa dòng điểm | `teaching_assignments.teacher_id` (khớp `scores.assignment_id`) | `403 FORBIDDEN` (chống GV sửa điểm lớp khác) |

#### Ràng buộc Mức 2 — chặn ở bước "Gửi duyệt" (SD23)

> Ràng buộc **nghiệp vụ** → GV có thể lưu dở để soạn tiếp, nhưng **không được gửi duyệt** khi dữ liệu chưa hoàn chỉnh.

| # | Ràng buộc | Kiểm tra | Mã lỗi |
|---|---|---|---|
| B1 | **Mọi ô phải được điền** — không ô nào được để trống (`NULL`) | Quét toàn bộ `scores` của assignment | `422 INCOMPLETE_SCORES` |
| B2 | Phải có ít nhất 1 học sinh có điểm | Đếm ô có giá trị | `422 NO_SCORES_TO_SUBMIT` |
| B3 | Chưa có bản ghi `PENDING` cho cùng `assignment_id` | `score_submissions` | `409 DUPLICATE_PENDING_SUBMISSION` |
| B4 | Bảng điểm đang mở | `is_locked == false` | `423 SCORE_TABLE_LOCKED` |
| B5 | GV là người phụ trách assignment | `assignment.teacher_id` | `403 FORBIDDEN` |
| B6 | Chưa có đơn gửi duyệt `PENDING` cho assignment (để tránh gửi trùng) | `score_submissions.status = 'PENDING'` | `409 DUPLICATE_PENDING_SUBMISSION` (GV phải **Hủy** đơn cũ trước) |

> **B1 là ràng buộc "không được bỏ trống"** — GV có thể **lưu dở** nhiều lần để soạn tiếp, nhưng **không thể gửi duyệt** khi còn ô trống.

> **A11 — "Chặn GV sửa điểm lớp khác":** mọi thao tác ghi (`POST /scores/batch`, `PUT /scores/{id}`) phải kiểm tra `scores.assignment_id → teaching_assignments.teacher_id = user.id` hiện tại. GV phụ trách 3 lớp → chỉ sửa được điểm của 3 lớp đó, **không** sửa được điểm lớp của GV khác dù có biết `scores.id`.
>
> **A10 — "Đang có đơn PENDING thì không sửa được":** Trong lúc bảng điểm đang chờ Giáo vụ duyệt, GV **không được** sửa ô điểm — vì nếu sửa, Giáo vụ sẽ duyệt một bản điểm **không còn khớp với những gì GV đã gửi**. Muốn sửa → GV bấm **"Hủy đơn gửi duyệt"** (`PUT /score-submissions/{id}/cancel`) → đơn chuyển `CANCELLED`, bảng điểm vẫn `is_draft = TRUE` → GV sửa thoải mái rồi gửi duyệt lại.
> Server **quét toàn bộ** bảng điểm của lớp môn học (không chỉ dòng vừa lưu) → không thể lách bằng cách gửi từng phần.

**Quy tắc bắt buộc cho luồng phúc khảo (SD19 — tránh bug điểm chính thức bị "hạ" về bản nháp):**
* Khi Giáo vụ **duyệt** đơn phúc khảo → điểm mới ghi thẳng vào **điểm chính thức**, **giữ nguyên `scores.is_draft = FALSE`**; tuyệt đối **không** ghi vào bảng điểm tạm.
* Đồng thời **không** thay đổi `teaching_assignments.is_locked` → bảng điểm vẫn **ĐÃ CHỐT** sau khi phúc khảo được duyệt.
* Tính lại `average_score` & `is_passed` trong **cùng transaction** (ACID) với `UPDATE scores`.
* Khi Giáo vụ **từ chối** → không thay đổi bất kỳ dữ liệu điểm nào.

**Biểu mẫu gửi yêu cầu sửa điểm (SD25 — bắt buộc):**
* GV chọn theo thứ tự **Lớp → Học sinh → Môn học → Cột điểm** (15 phút / 1 tiết / cuối kỳ).
* Hệ thống **tự động hiển thị Điểm hiện tại ở chế độ chỉ đọc** — GV **không** sửa trực tiếp được điểm đã chốt (đảm bảo trung thực); mọi thay đổi phải qua đơn kèm lý do.
* `reason` (lý do) là **BẮT BUỘC** — GV chọn trong danh mục (gõ nhầm số, chấm sót ý bài tự luận, phúc khảo, chấm lại bài giấy…) hoặc tự nhập.
* File đính kèm (ảnh bài đã chấm lại / biên bản phúc khảo) **LUÔN TÙY CHỌN** — hệ thống **không** bắt buộc theo loại lý do. Với lý do đơn giản như "gõ nhầm 7.5 thành 5.7" thì không cần đính kèm.
* Hỗ trợ **2 mức**: **đơn lẻ** (1 ô điểm) và **đơn lô** (nhiều ô điểm của nhiều học sinh) — cùng 1 luồng nghiệp vụ, khác nhau ở bảng chi tiết `score_change_details`.

**Duyệt từng ô & Outbox Pattern (điểm nhấn Transaction & Data Consistency):**
* Trạng thái thật của mỗi ô nằm ở `score_change_details.status`; `score_change_requests.status` chỉ là **tóm tắt** (`APPROVED` / `REJECTED` / `PARTIALLY_APPROVED`).
* Toàn bộ xử lý duyệt chạy trong **1 transaction ACID duy nhất**: cập nhật trạng thái đơn cha → cập nhật trạng thái từng ô con → `UPDATE scores` (giữ `is_draft = FALSE`) → tính lại `average_score` & `is_passed` → ghi `audit_logs` → `INSERT INTO email_outbox`.
* **Lỗi ở bất kỳ bước nào → ROLLBACK toàn bộ** → không tồn tại trạng thái "đơn đã duyệt nhưng điểm chưa sửa".
* **Mail KHÔNG gửi bên trong transaction.** Mail được ghi vào `email_outbox` trong cùng transaction, sau `COMMIT` worker mới gửi → **gửi mail thông báo tự động** mà không cần thao tác tay, và không bao giờ có tình huống GV nhận mail "đã duyệt" trong khi DB đã rollback.

**Quy tắc đọc điểm (chống lộ điểm chưa duyệt):**
* Mọi truy vấn đọc **điểm chính thức** phải lọc `WHERE is_draft = FALSE`: báo cáo thống kê (SD20), xuất ĐTB lớp (SD13), xem ĐTB lớp (SD12), và **xem điểm học sinh** (`GET /scores/student/{studentId}` — đường hở rò rỉ nếu bỏ qua vì học sinh tự xem điểm của chính mình).
* Ngoại lệ: `GET /scores/assignment/{assignmentId}` trả cả 2 loại kèm cờ `is_draft` (GV cần thấy nháp để tiếp tục soạn — SD11); Giáo vụ mặc định chỉ đọc điểm chính thức.

**Điểm đã loại bỏ khỏi phạm vi:**
* `SD10_DiemDanhHocSinh` — chức năng điểm danh chuyên cần **không được nêu trong Yêu cầu 3** của đề bài. Đã gỡ bỏ khỏi bảng ánh xạ §4, sơ đồ §7.10, danh mục endpoint `API.md` và bảng `attendances` trong `database-design.md`.

**Quy ước hiển thị biểu mẫu BẢNG ĐIỂM MÔN HỌC:**
* Cột **"Điểm 15'"** trên biểu mẫu được mở rộng thành **nhiều ô nhập** (`score_15m_1` … `score_15m_5`) theo quy định `MIN_COL_15M` / `MAX_COL_15M`.
* Cột **"Điểm 1 tiết"** được mở rộng thành **nhiều ô nhập** (`score_45m_1` … `score_45m_3`) theo quy định `MIN_COL_45M` / `MAX_COL_45M`.
* Cột **"Điểm thi"** là **1 ô** (`score_final`) cố định theo quy định `NUM_COL_FINAL`.

---

## 5. Cấu hình Quy định động (Dynamic System Rules)

Hệ thống tuân thủ triệt để nguyên tắc không hard-code bất kỳ tham số ràng buộc nào vào mã nguồn. Tất cả các quy định được quản lý tại bảng `system_rules` trong MySQL và được tải động vào tầng Service khi thực thi nghiệp vụ:

| Khóa quy định (`rule_key`) | Giá trị mặc định (`rule_value`) | Diễn giải quy chế nghiệp vụ | Áp dụng tại chức năng |
|-----------------------------|---------------------------------|-----------------------------|-----------------------|
| `MIN_AGE` | `15` | Độ tuổi tối thiểu khi tiếp nhận học sinh vào trường | Tiếp nhận hồ sơ học sinh (YC 1) |
| `MAX_AGE` | `20` | Độ tuổi tối đa khi tiếp nhận học sinh vào trường | Tiếp nhận hồ sơ học sinh (YC 1) |
| `MAX_CLASS_SIZE` | `40` | Sĩ số học sinh tối đa cho phép trong một lớp học | Lập & Điều chỉnh danh sách lớp (YC 2) |
| `MIN_COL_15M` | `1` | Số cột điểm 15 phút tối thiểu của mỗi môn học | Nhập điểm môn học (YC 3) |
| `MAX_COL_15M` | `5` | Số cột điểm 15 phút tối đa của mỗi môn học | Nhập điểm môn học (YC 3) |
| `MIN_COL_45M` | `1` | Số cột điểm 1 tiết tối thiểu của mỗi môn học | Nhập điểm môn học (YC 3) |
| `MAX_COL_45M` | `3` | Số cột điểm 1 tiết tối đa của mỗi môn học | Nhập điểm môn học (YC 3) |
| `NUM_COL_FINAL` | `1` | Số cột điểm thi cuối kỳ bắt buộc | Nhập điểm môn học (YC 3) |
| `PASSING_SCORE` | `5.0` | Điểm chuẩn tối thiểu để xếp loại Đạt môn học | Báo cáo thống kê & Biểu đồ (YC 4) |
| `MAX_LOGIN_ATTEMPTS` | `5` | Số lần nhập sai mật khẩu tối đa trước khi tự động khóa tài khoản | Xác thực đăng nhập hệ thống |

---

## 6. Yêu cầu phi chức năng

| STT | Tiêu chí kỹ thuật | Chỉ số & Phương án triển khai chi tiết |
|:---:|-------------------|----------------------------------------|
| 1 | **Hiệu năng hệ thống** | Thời gian phản hồi trang web $< 500\text{ ms}$; thời gian tính toán bảng điểm và kết xuất báo cáo Chart.js $< 1\text{ s}$ với 100 người dùng đồng thời. |
| 2 | **Bảo mật xác thực** | Mật khẩu được mã hóa một chiều bằng giải thuật `bcrypt` kết hợp chuỗi muối (salt) tự sinh với hệ số phức tạp $\ge 12$; chính sách MK mạnh (≥8 ký tự + Hoa + thường + số + đặc biệt) áp dụng cho đổi MK/tự đặt lại/admin reset. Chống tấn công Brute-force qua cơ chế khóa tài khoản sau 5 lần nhập sai (ngưỡng đọc từ `system_rules`). |
| 3 | **Toàn vẹn dữ liệu** | Sử dụng cơ chế Transaction của cơ sở dữ liệu (`db.session.commit()`) cho các thao tác ghi dữ liệu danh sách (nhập điểm theo lớp, import Excel, chuyển lớp); đảm bảo tính nguyên tố (Atomicity), rollback toàn bộ khi có lỗi. |
| 4 | **Phân quyền truy cập (RBAC)** | Kiểm soát phân quyền nghiêm ngặt tại tầng Controller bằng Custom Python Decorators (`@role_required('STAFF')`); người dùng chỉ được phép truy xuất đúng các chức năng tương ứng với quyền hạn của mình. |
| 5 | **Tính mở rộng & Bảo trì** | Tách rời 4 tầng theo mô hình BCE; các quy định nghiệp vụ được quản lý độc lập tại `system_rules`, cho phép thay đổi tức thì mà không cần biên dịch hay khởi động lại hệ thống. |

---

## 7. Toàn Bộ 23 Sơ Đồ Sequence Diagram Chi Tiết (Chuẩn Mô Hình BCE)

> **Ghi chú:** `SD10_DiemDanhHocSinh` đã được gỡ bỏ khỏi phạm vi đề bài (xem §4.1) — các sơ đồ còn lại được đánh số lại liên tục từ `7.1` đến `7.21`; thêm mới `7.22` (SD23) và `7.23` (SD24) cho luồng **Gửi duyệt & Chốt bảng điểm**.

Mỗi sơ đồ dưới đây gồm đầy đủ 4 đối tượng phân tích:
* **`Actor` (👤):** Người dùng tương tác trực tiếp (`NguoiDung`, `NhanVien`, `GiaoVien`, `GiaoVu`).
* **`Boundary` (┠○):** Giao diện View / Template tiếp nhận sự kiện và hiển thị.
* **`Control` (🔄):** Controller điều phối luồng và kiểm soát nghiệp vụ.
* **`Entity` (⭕):** Thực thể dữ liệu tương ứng với bảng trong MySQL.
* *(Trường hợp đặc biệt có kết nối dịch vụ ngoài: `MailServer`)*.

---

### PHÂN HỆ I: XÁC THỰC & NGƯỜI DÙNG (ACTOR: `NGUOIDUNG`)

#### 7.1 Sơ đồ 1: `SD01_DangNhap` — Đăng ký / Đăng nhập
*Ánh xạ Use Case:* `Đăng ký / Đăng nhập`  
*Kịch bản:* Tìm kiếm username duy nhất; nếu tài khoản đang bị khóa (`is_locked == true`) thì chặn ngay; nếu sai mật khẩu thì tăng `failed_attempts` (sai $\ge 5$ lần thì khóa tài khoản); nếu đúng thì đặt lại số lần sai về 0 và chuyển hướng theo vai trò (`role`).

```
NguoiDung (Actor)        LoginView (Boundary)       AuthController (Control)        User (Entity)
     |                             |                            |                         |
     | 1: Nhập username, password  |                            |                         |
     |---------------------------->|                            |                         |
     |                             | 1.1: Gửi thông tin         |                         |
     |                             |--------------------------->|                         |
     |                             |                            | 1.2: findByUsername     |
     |                             |                            |      (username)         |
     |                             |                            |------------------------>|
     |                             |                            | 1.3: Trả về kết quả     |
     |                             |                            |      (User hoặc null)   |
     |                             |                            |< - - - - - - - - - - - -|
     |                             |                            |                         |
====[ alt 1: Kiểm tra tài khoản có tồn tại không ]============================================
[Trường hợp: Kết quả là null (Không tồn tại tài khoản)]
     |                             | 1.4: Báo tài khoản không có|                         |
     |                             |< - - - - - - - - - - - - - |                         |
     | 1.5: Hiển thị lỗi           |                            |                         |
     |< - - - - - - - - - - - - - -|                            |                         |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Trường hợp: Tìm thấy User]
     |                             |                            |                         |
----[ alt 2: Kiểm tra trạng thái khóa ]------------------------------------------------------
    [Tài khoản đang bị khóa (is_locked == true)]
     |                             | 1.6: Báo tài khoản bị khóa |                         |
     |                             |< - - - - - - - - - - - - - |                         |
     | 1.7: Hiển thị lỗi khóa      |                            |                         |
     |< - - - - - - - - - - - - - -|                            |                         |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    [Tài khoản hoạt động bình thường (is_locked == false)]
     |                             |                            | 2: So khớp hash mật khẩu|
     |                             |                            |----+                    |
     |                             |                            |    | (bcrypt.checkpw)   |
     |                             |                            |<---+                    |
     |                             |                            |                         |
----[ alt 3: Kết quả so khớp mật khẩu ]--------------------------------------------------
    [Mật khẩu SAI]
     |                             |                            | 2.1: Tăng số lần sai +1 |
     |                             |                            |------------------------>|
     |                             |                            | 2.2: Xác nhận cập nhật  |
     |                             |                            |< - - - - - - - - - - - -|
     |                             |                            |                         |
----[ alt 4: Đánh giá số lần sai ]---------------------------------------------------
    [Số lần sai >= 5 lần]
     |                             |                            | 2.3a: Khóa tài khoản    |
     |                             |                            |------------------------>|
     |                             | 2.4a: Báo khóa do sai 5 lần|                         |
     |                             |< - - - - - - - - - - - - - |                         |
     | 2.5a: Hiển thị lỗi khóa     |                            |                         |
     |< - - - - - - - - - - - - - -|                            |                         |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    [Số lần sai < 5 lần]
     |                             | 2.3b: Báo sai mật khẩu     |                         |
     |                             |< - - - - - - - - - - - - - |                         |
     | 2.4b: Hiển thị số lần còn lại                            |                         |
     |< - - - - - - - - - - - - - -|                            |                         |
-------------------------------------------------------------------------------------
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    [Mật khẩu ĐÚNG]
     |                             |                            | 3: Xóa số lần sai về 0  |
     |                             |                            |------------------------>|
     |                             |                            | 3.1: Xác nhận cập nhật  |
     |                             |                            |< - - - - - - - - - - - -|
     |                             |                            | 3.2: Kiểm tra vai trò   |
     |                             |                            |----+ (Staff / Teacher / |
     |                             |                            |    |  Academic)         |
     |                             |                            |<---+                    |
     |                             | 3.3: Chuyển hướng theo Role|                         |
     |                             |< - - - - - - - - - - - - - |                         |
     | 3.4: Hiển thị trang tương ứng                            |                         |
     |< - - - - - - - - - - - - - -|                            |                         |
=============================================================================================
```

#### 7.2 Sơ đồ 2: `SD02_DoiMatKhau` — Đổi mật khẩu cá nhân
*Ánh xạ Use Case:* `Đổi mật khẩu`  
*Kịch bản:* Người dùng nhập mật khẩu hiện tại và mật khẩu mới; Controller kiểm tra so khớp mật khẩu cũ, kiểm tra độ mạnh mật khẩu mới, băm BCrypt và cập nhật vào thực thể `User`.

```
NguoiDung (Actor)       DoiMKView (Boundary)        AuthController (Control)        User (Entity)
     |                            |                             |                         |
     | 1: Nhập MK cũ, MK mới      |                             |                         |
     |    & xác nhận MK mới       |                             |                         |
     |--------------------------->|                             |                         |
     |                            | 1.1: Gửi yêu cầu đổi MK     |                         |
     |                            |---------------------------->|                         |
     |                            |                             | 1.2: Lấy thông tin user |
     |                            |                             |      hiện tại từ phiên  |
     |                            |                             |------------------------>|
     |                            |                             | 1.3: Trả về userRecord  |
     |                            |                             |< - - - - - - - - - - - -|
     |                            |                             |                         |
     |                            |                             | 1.4: So khớp MK hiện tại|
     |                            |                             |----+ (bcrypt.checkpw)   |
     |                            |                             |    |                    |
     |                            |                             |<---+                    |
     |                            |                             |                         |
====[ alt: Kiểm tra mật khẩu cũ & tính hợp lệ của mật khẩu mới ]=============================
[Mật khẩu cũ không đúng HOẶC Mật khẩu mới không khớp/quá ngắn]
     |                            | 1.5: Báo thông tin đổi MK   |                         |
     |                            |      không hợp lệ           |                         |
     |                            |< - - - - - - - - - - - - - -|                         |
     | 1.6: Hiển thị lỗi form     |                             |                         |
     |< - - - - - - - - - - - - - |                             |                         |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Mật khẩu cũ đúng & Mật khẩu mới hợp lệ]
     |                            |                             | 2: Băm mật khẩu mới     |
     |                            |                             |----+ (bcrypt.hashpw)    |
     |                            |                             |    |                    |
     |                            |                             |<---+                    |
     |                            |                             | 2.1: Cập nhật mật khẩu  |
     |                            |                             |------------------------>|
     |                            |                             | 2.2: Xác nhận thành công|
     |                            |                             |< - - - - - - - - - - - -|
     |                            | 2.3: Báo đổi MK thành công  |                         |
     |                            |< - - - - - - - - - - - - - -|                         |
     | 2.4: Hiển thị thông báo    |                             |                         |
     |      đổi mật khẩu thành công                             |                         |
     |< - - - - - - - - - - - - - |                             |                         |
=============================================================================================
```

---

### PHÂN HỆ II: QUẢN LÝ HỒ SƠ & LỚP HỌC (ACTOR: `NHANVIEN`)

#### 7.3 Sơ đồ 3: `SD03_TiepNhanHoSoHocSinh` — Tiếp nhận học sinh (Yêu cầu 1)
*Ánh xạ Use Case:* `Tiếp nhận hồ sơ học sinh`  
*Kịch bản:* Nhân viên nhập hồ sơ (Họ tên, Giới tính, Ngày sinh, Địa chỉ, Số điện thoại, Email); Controller truy vấn quy định tuổi từ `QuyDinh` (`MIN_AGE = 15`, `MAX_AGE = 20`), tính tuổi và kiểm tra điều kiện $15 \le \text{Tuổi} \le 20$. Nếu vi phạm thì từ chối; nếu hợp lệ thì lưu vào thực thể `HocSinh`.

```
NhanVien (Actor)     TiepNhanView (Boundary)     TiepNhanController (Control)   QuyDinh (Entity)        HocSinh (Entity)
     |                           |                            |                        |                       |
     | 1: Nhập hồ sơ học sinh    |                            |                        |                       |
     |    (hoTen, gioiTinh,      |                            |                        |                       |
     |     ngaySinh, diaChi, sdt)|                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Gửi yêu cầu tiếp nhận |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy quy định tuổi |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về quy định   |                       |
     |                           |                            |      (tuoiMin, tuoiMax)|                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
     |                           |                            | 1.4: Tính tuổi học sinh|                       |
     |                           |                            |----+ (namHienTai -     |                       |
     |                           |                            |    |  namSinh)         |                       |
     |                           |                            |<---+                   |                       |
     |                           |                            |                        |                       |
====[ alt: Kiểm tra độ tuổi theo quy định (15 <= Tuổi <= 20) ]==========================================================
[Tuổi < tuoiMin HOẶC Tuổi > tuoiMax]
     |                           | 1.5: Báo lỗi vi phạm tuổi  |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 1.6: Hiển thị thông báo:  |                            |                        |                       |
     |  "Tuổi phải từ 15 đến 20" |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Độ tuổi hợp lệ (15 <= Tuổi <= 20)]
     |                           |                            | 2: Lưu hồ sơ học sinh  |                       |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Xác nhận lưu thành công (maHocSinh)       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Báo tiếp nhận OK      |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 2.3: Hiển thị thông báo   |                            |                        |                       |
     |      tiếp nhận thành công |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
========================================================================================================================
```

#### 7.4 Sơ đồ 4: `SD04_ImportHocSinhExcel` — Import danh sách học sinh từ Excel
*Ánh xạ Use Case:* `Import danh sách học sinh từ Excel`  
*Kịch bản (partial success — chốt thống nhất với `API.md POST /students/import-excel`):* Nhân viên tải lên file `.xlsx`/`.csv`; Controller đọc file, lấy quy chế tuổi từ `QuyDinh`, vòng lặp `loop` validate từng dòng (tuổi 15–20, trùng `student_code`); commit các dòng hợp lệ (batch insert 1 transaction), thu thập `errors[{row, reason}]`; trả `{total_rows, success_count, failed_count, errors}`.

```
NhanVien (Actor)       ImportView (Boundary)       ImportController (Control)   QuyDinh (Entity)        HocSinh (Entity)
     |                           |                            |                        |                       |
     | 1: Chọn file Excel & Gửi  |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Upload file Excel     |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy quy định tuổi |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về (min, max) |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
====[ loop: Duyệt từng dòng học sinh trong file Excel ]================================================================
     |                           |                            | 1.4: Đọc dòng & tính tuổi                      |
     |                           |                            |----+                                           |
     |                           |                            |    | validateAge(dob, min, max)                |
     |                           |                            |<---+                                           |
=======================================================================================================================
     |                           |                            |                        |                       |
====[ alt: Partial success — commit dòng hợp lệ, thu thập errors ]==================================================
     |                           |                            | 2: batchInsert(dongHopLe) trong 1 transaction  |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Commit OK (successCount) + errors[]       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Trả {total, success_count, failed_count, errors[{row, reason}]}        |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 2.3: Hiển thị số lượng    |                            |                        |                       |
     |      + danh sách dòng lỗi |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
=======================================================================================================================
```

#### 7.5 Sơ đồ 5: `SD05_LapDanhSachLop` — Lập danh sách lớp (Yêu cầu 2)
*Ánh xạ Use Case:* `Lập danh sách lớp`  
*Kịch bản:* Nhân viên chọn khối (10, 11, 12), chọn lớp và danh sách học sinh; Controller lấy sĩ số tối đa từ `QuyDinh` (`MAX_CLASS_SIZE = 40`), kiểm tra sĩ số hiện tại từ thực thể `Lop` đảm bảo không vượt quá 40 học sinh trước khi phân bổ vào lớp.

```
NhanVien (Actor)      LapLopView (Boundary)       LapLopController (Control)    QuyDinh (Entity)          Lop (Entity)
     |                           |                            |                        |                       |
     | 1: Chọn khối (10/11/12)   |                            |                        |                       |
     |    & danh sách học sinh   |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Gửi yêu cầu xếp lớp   |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy sĩ số tối đa  |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về siSoToiDa  |                       |
     |                           |                            |      (40 học sinh)     |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
     |                           |                            | 1.4: Lấy sĩ số hiện tại|                       |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.5: Trả về siSoHienTai|                       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                        |                       |
     |                           |                            | 1.6: Kiểm tra sĩ số mới|                       |
     |                           |                            |----+ (siSoHienTai +    |                       |
     |                           |                            |    |  soLuongThem)     |                       |
     |                           |                            |<---+                   |                       |
     |                           |                            |                        |                       |
====[ alt: Kiểm tra giới hạn sĩ số lớp học ]============================================================================
[Tổng sĩ số > siSoToiDa (vượt quá 40)]
     |                           | 1.7: Báo lớp đã vượt sĩ số |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 1.8: Hiển thị lỗi:        |                            |                        |                       |
     |  "Vượt quá sĩ số tối đa"  |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Tổng sĩ số <= siSoToiDa (hợp lệ)]
     |                           |                            | 2: Thêm học sinh vào lớp                       |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Cập nhật sĩ số thành công                 |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Báo phân lớp OK       |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 2.3: Hiển thị danh sách   |                            |                        |                       |
     |      lớp mới hoàn tất     |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
========================================================================================================================
```

#### 7.6 Sơ đồ 6: `SD06_DieuChinhDanhSachLop` — Điều chỉnh danh sách lớp (Yêu cầu 2)
*Ánh xạ Use Case:* `Điều chỉnh danh sách lớp`  
*Kịch bản:* Nhân viên chọn học sinh cần chuyển từ Lớp A sang Lớp B; Controller kiểm tra sĩ số lớp B; nếu lớp B chưa đầy ($< 40$), thực hiện chuyển lớp trong một Database Transaction: giảm sĩ số lớp A, tăng sĩ số lớp B, cập nhật `class_id` của học sinh.

```
NhanVien (Actor)     DieuChinhView (Boundary)   DieuChinhController (Control)   QuyDinh (Entity)          Lop (Entity)
     |                           |                            |                        |                       |
     | 1: Chọn học sinh, lớp cũ  |                            |                        |                       |
     |    và lớp mới cần chuyển  |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Gửi yêu cầu chuyển lớp|                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy sĩ số tối đa  |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về siSoToiDa  |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
     |                           |                            | 1.4: Lấy sĩ số lớp mới |                       |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.5: Trả về siSoLopMoi |                       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                        |                       |
====[ alt: Kiểm tra sĩ số lớp mới tiếp nhận ]===========================================================================
[siSoLopMoi >= siSoToiDa (Lớp đích đã đủ 40 học sinh)]
     |                           | 1.6: Báo lớp đích đã đầy   |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 1.7: Hiển thị cảnh báo:   |                            |                        |                       |
     | "Lớp đích đã đạt tối đa"  |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[siSoLopMoi < siSoToiDa (Hợp lệ)]
     |                           |                            | 2: Transaction: Chuyển lớp học sinh            |
     |                           |                            |----+ (Giảm sĩ số lớp cũ,                       |
     |                           |                            |    |  Tăng sĩ số lớp mới,                      |
     |                           |                            |    |  Đổi class_id của học sinh)               |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Transaction Commit OK                     |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Báo điều chỉnh OK     |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 2.3: Hiển thị thông báo   |                            |                        |                       |
     |      chuyển lớp thành công|                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
========================================================================================================================
```

#### 7.7 Sơ đồ 7: `SD07_CapNhatHoSoHocSinh` — Cập nhật hồ sơ học sinh
*Ánh xạ Use Case:* `Cập nhật hồ sơ học sinh`  
*Kịch bản:* Nhân viên tra cứu học sinh, sửa đổi thông tin (địa chỉ, số điện thoại, email, CCCD); Controller kiểm tra trùng lặp email/SĐT/`citizen_id` với học sinh khác (cột `citizen_id UNIQUE` — xem `database-design.md` §8) và ghi nhận cập nhật vào thực thể `HocSinh`.

```
NhanVien (Actor)       HoSoView (Boundary)        HoSoController (Control)                             HocSinh (Entity)
     |                           |                            |                                                |
     | 1: Nhập thông tin mới     |                            |                                                |
     |    & nhấn Lưu cập nhật    |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi thông tin cập nhật|                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: checkDuplicateContact(email, phone)       |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về kết quả (isDuplicate)              |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                                                |
====[ alt: Kiểm tra trùng lặp thông tin liên lạc ]======================================================================
[isDuplicate == true (Email hoặc SĐT đã thuộc học sinh khác)]
     |                           | 1.4: Báo trùng lặp dữ liệu |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.5: Hiển thị lỗi form    |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[isDuplicate == false (Hợp lệ)]
     |                           |                            | 2: update(studentId, updatedData)              |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Xác nhận cập nhật thành công              |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Báo cập nhật hồ sơ OK |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 2.3: Hiển thị thông báo   |                            |                                                |
     |      cập nhật thành công  |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
========================================================================================================================
```

#### 7.8 Sơ đồ 8: `SD08_TraCuuVaInHoSoHocSinh` — Tra cứu & In hồ sơ học sinh
*Ánh xạ Use Case:* `Tra cứu hồ sơ học sinh` (chứa quan hệ `<<extend>> In hồ sơ học sinh`)  
*Kịch bản:* Nhân viên nhập từ khóa tìm kiếm (Tên, Mã, Lớp); Controller tìm kiếm trong thực thể `HocSinh` và trả kết quả hiển thị; nếu nhân viên bấm nút "In hồ sơ" (Extension Point), Boundary kích hoạt trình tạo file PDF / in ấn.

```
NhanVien (Actor)       TraCuuView (Boundary)      TraCuuController (Control)                           HocSinh (Entity)
     |                           |                            |                                                |
     | 1: Nhập từ khóa tìm kiếm  |                            |                                                |
     |    (hoTen / maHS / lop)   |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi yêu cầu tìm kiếm  |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: searchStudents(queryKeyword)              |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về danh sách học sinh khớp            |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 1.4: Hiển thị kết quả bảng |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.5: Xem danh sách hồ sơ  |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
     |                           |                            |                                                |
====[ opt: <<extend>> In hồ sơ học sinh (Extension Point: Người dùng chọn In hồ sơ) ]===================================
     | 2: Nhấn nút "In hồ sơ"    |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 2.1: window.print()        |                                                |
     |                           |      hoặc exportPDF()      |                                                |
     |                           |----+                       |                                                |
     |                           |    | Xuất bản in hồ sơ     |                                                |
     |                           |<---+                       |                                                |
     | 2.2: Hiển thị bản in / PDF|                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
========================================================================================================================
```

---

### PHÂN HỆ III: GIẢNG DẠY & ĐIỂM SỐ (ACTOR: `GIAOVIEN`)

#### 7.9 Sơ đồ 9: `SD09_TraCuuLopPhuTrach` — Tra cứu danh sách lớp phụ trách
*Ánh xạ Use Case:* `Tra cứu danh sách lớp phụ trách`  
*Kịch bản:* Giáo viên chọn học kỳ / năm học; Controller truy vấn thực thể `PhanCong` để lấy danh sách các lớp học phần/lớp bộ môn mà giáo viên được giao, sau đó hiển thị danh sách lớp kèm sĩ số.

```
GiaoVien (Actor)      LopDayView (Boundary)       LopDayController (Control)                          PhanCong (Entity)
     |                           |                            |                                                |
     | 1: Chọn Học kỳ, Năm học   |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi yêu cầu lấy lớp   |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: findClassesByTeacher(teacherId, semester) |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về danh sách lớp được phân công       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 1.4: Trả về kết quả lớp dạy|                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.5: Hiển thị danh sách   |                            |                                                |
     |      lớp phụ trách        |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
```

#### 7.10 Sơ đồ 10: `SD11_NhapDiemMonHoc` — Nhập điểm môn học (Yêu cầu 3)
*Ánh xạ Use Case:* `Nhập điểm môn học` (chứa `<<include>> Tính điểm trung bình môn`)  
*Kịch bản:* Giáo viên nhập các cột điểm thành phần theo biểu mẫu BẢNG ĐIỂM MÔN HỌC (15' có 1-5 cột, 1 tiết có 1-3 cột, 1 điểm thi); Controller kiểm tra **2 điều kiện trước khi ghi**: (1) **bảng điểm ĐÃ CHỐT** → từ chối **423 `SCORE_TABLE_LOCKED`** và hướng sang **SD25** (gửi đơn phúc khảo); (2) **đang có đơn gửi duyệt `PENDING`** → từ chối **423 `SCORE_SUBMISSION_PENDING`** → GV phải **Hủy** đơn (`PUT /score-submissions/{id}/cancel`) trước rồi mới sửa được. Nếu cả 2 OK thì lấy quy định cột từ `QuyDinh`, kiểm tra khoảng điểm $0.0 \le \text{Điểm} \le 10.0$, tự động thực hiện luồng bao hàm `<<include>> Tính điểm trung bình môn` cho từng học sinh và lưu vào thực thể `Diem` với cờ **`is_draft = TRUE` (BẢNG ĐIỂM TẠM)** — ghi đè bản nháp trước. Điểm tạm **chưa phải điểm chính thức**; muốn chốt phải qua **SD23 (Gửi bảng điểm lên duyệt)** → **SD24 (Giáo vụ duyệt & chốt)**.
>
> **Quy ước giá trị ô điểm (đã chốt):** ô **`NULL` (để trống) = CHƯA NHẬP** → lỗi GV, được phép ở bước "Lưu" nhưng **bị chặn** ở bước "Gửi duyệt"; ô **`0.00` = ĐÃ NHẬP** → học sinh **vắng** hoặc **thi 0 điểm** → quy về 0 điểm và **vẫn được tính vào ĐTB**. Ô `NULL` bị loại khỏi cả tử số & mẫu số của ĐTB; ô `0.00` vẫn được tính.

```
GiaoVien (Actor)      NhapDiemView (Boundary)     DiemController (Control)      QuyDinh (Entity)         Diem (Entity)
     |                           |                            |                        |                       |
     | 1: Chọn Lớp, Môn, Học kỳ  |                            |                        |                       |
     |    nhập điểm & bấm Lưu    |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Gửi danh sách điểm    |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy quy định cột  |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về (min/max   |                       |
     |                           |                            |      15p, 1tiet, thi)  |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
====[ alt 1: Kiểm tra tính hợp lệ số cột và thang điểm (0 <= điểm <= 10) ]=============================================
[Số cột không đủ quy định HOẶC Điểm < 0 HOẶC Điểm > 10]
     |                           | 1.4: Báo dữ liệu điểm sai  |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 1.5: Hiển thị lỗi cột     |                            |                        |                       |
     |      hoặc khoảng điểm     |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
====[ alt 1b: Kiểm tra trạng thái bảng điểm & đơn gửi duyệt ]=================================================
[Bảng điểm ĐÃ CHỐT (is_locked == true)]
     |                           | 1.4b: Từ chối 423 SCORE_TABLE_LOCKED             |                       |
     |                           |      & hướng sang SD25 (gửi đơn phúc khảo)       |                       |
     |                           |< - - - - - - - - - - - - - - - - - - - - - - - -|                       |
     | 1.5b: Thông báo bảng điểm |                            |                        |                       |
     |      đã chốt, hãy gửi đơn  |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Đang có đơn gửi duyệt PENDING]
     |                           | 1.4c: Từ chối 423 SCORE_SUBMISSION_PENDING        |                       |
     |                           |      (GV phải Hủy đơn trước)                    |                       |
     |                           |< - - - - - - - - - - - - - - - - - - - - - - - -|                       |
     | 1.5c: Thông báo: hãy hủy  |                            |                        |                       |
     |      đơn gửi duyệt trước   |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Dữ liệu điểm hợp lệ & bảng điểm đang mở & không có đơn PENDING]
     |                           |                            |                        |                       |
====[ loop: Duyệt từng học sinh (<<include>> Tính điểm trung bình môn) ]==============================================
     |                           |                            | 2: calculateAverage()  |                       |
     |                           |                            |----+ (ĐTB = (Đ_15' +   |                       |
     |                           |                            |    |  Đ_1tiet*2 +      |                       |
     |                           |                            |    |  Đ_thi*3) / tongHS|                       |
     |                           |                            |<---+                   |                       |
======================================================================================================================
     |                           |                            | 2.1: Lưu bảng điểm & ĐTB                       |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.2: Xác nhận lưu thành công                   |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.3: Báo lưu điểm OK       |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 2.4: Hiển thị bảng điểm   |                            |                        |                       |
     |      đã tính ĐTB thành công                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
======================================================================================================================
```

#### 7.11 Sơ đồ 11: `SD12_XemBangDiemTrungBinhLop` — Xem bảng điểm trung bình lớp (Yêu cầu 3)
*Ánh xạ Use Case:* `Xem bảng điểm trung bình lớp` (chứa `<<include>> Tính điểm trung bình môn`)  
*Kịch bản:* Giáo viên chọn Lớp, Môn học, Năm học; Controller truy vấn điểm thành phần các học kỳ từ thực thể `Diem` (**chỉ đọc điểm chính thức: `is_draft = FALSE`**), tự động tính điểm trung bình môn cả năm học và hiển thị theo biểu mẫu **BẢNG ĐIỂM TRUNG BÌNH LỚP** (Năm học, STT, Họ tên, Lớp, Điểm TB HK1, Điểm TB HK2). API trả kèm thêm `avg_yearly` (ĐTB cả năm) để phục vụ xếp loại — biểu mẫu xuất file theo mẫu đề bài không đưa cột này vào (xem §4.1).

```
GiaoVien (Actor)     XemBangDiemView (Boundary)   DiemController (Control)                             Diem (Entity)
     |                           |                            |                                                |
     | 1: Chọn Lớp, Môn, Năm học |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi yêu cầu xem điểm  |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: getScoresByClassAndYear(classId, subject) |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về danh sách điểm HK1, HK2            |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                                                |
====[ loop: <<include>> Tính điểm trung bình môn (HK1, HK2 & Cả năm) ]=================================================
     |                           |                            | 1.4: calculateYearlyAverage()                  |
     |                           |                            |----+ (ĐTB_CN = (ĐTB_HK1 + ĐTB_HK2 * 2) / 3)    |
     |                           |                            |    |                                           |
     |                           |                            |<---+                                           |
=======================================================================================================================
     |                           | 1.5: Trả về bảng điểm tổng |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.6: Hiển thị bảng điểm   |                            |                                                |
     |      trung bình cả năm    |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
```

#### 7.12 Sơ đồ 12: `SD13_XuatBangDiemTrungBinhLop` — Xuất bảng điểm trung bình lớp (Yêu cầu 3)
*Ánh xạ Use Case:* `Xuất bảng điểm trung bình lớp`  
*Kịch bản:* Giáo viên bấm nút "Xuất điểm trung bình lớp"; Controller tổng hợp dữ liệu điểm trung bình từ thực thể `Diem` (**chỉ đọc điểm chính thức: `is_draft = FALSE`**), đóng gói thành file Excel/PDF đúng biểu mẫu **BẢNG ĐIỂM TRUNG BÌNH LỚP** (Năm học, STT, Họ tên, Lớp, Điểm TB HK1, Điểm TB HK2) và gửi về cho trình duyệt tự động tải xuống.

```
GiaoVien (Actor)      XuatDiemView (Boundary)     DiemController (Control)                             Diem (Entity)
     |                           |                            |                                                |
     | 1: Nhấn "Xuất bảng điểm"  |                            |                                                |
     |    (chọn Excel / PDF)     |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: GET /scores/export    |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: fetchScoreSheetData(classId, subjectId)   |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về dữ liệu điểm thô                   |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                                                |
     |                           |                            | 1.4: generateExportFile(data, format)          |
     |                           |                            |----+ (Tạo file .xlsx hoặc .pdf)                |
     |                           |                            |    |                                           |
     |                           |                            |<---+                                           |
     |                           | 1.5: HTTP File Download    |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.6: Tự động tải file     |                            |                                                |
     |      bảng điểm về máy     |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
```

#### 7.13 Sơ đồ 13: `SD14_SuaDiemHocSinh` — Sửa điểm học sinh (bảng điểm đang MỞ) (Yêu cầu 3)
*Ánh xạ Use Case:* `Sửa điểm học sinh`  
*Kịch bản:* Giáo viên sửa một ô điểm khi bảng điểm đang **MỞ** (`teaching_assignments.is_locked = false`). Controller kiểm tra 2 điều kiện trước khi ghi: (1) bảng điểm **chưa chốt** — nếu đã chốt thì hướng sang **SD25 (Gửi yêu cầu chỉnh điểm)**; (2) lớp môn học **không có đơn gửi duyệt đang `PENDING`** — nếu có thì trả **423 `SCORE_SUBMISSION_PENDING`** để Giáo viên **Hủy** đơn trước. Nếu hợp lệ: cập nhật giá trị vào **bảng điểm tạm** (`is_draft = TRUE`), tự động thực hiện `<<include>> Tính điểm trung bình môn` (loại ô `NULL` khỏi cả tử số & mẫu số, giữ ô `0.00` → học sinh vắng vẫn bị trừ điểm đúng thực tế) và ghi `audit_logs`.

```
GiaoVien (Actor)       SuaDiemView (Boundary)     SuaDiemController (Control)   BangDiem (Entity)        Diem (Entity)
     |                           |                            |                        |                       |
     | 1: Chọn lớp/môn & bấm    |                            |                        |                       |
     |    vào ô điểm cần sửa     |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Gửi yêu cầu sửa điểm  |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy trạng thái    |                       |
     |                           |                            |      (is_locked)       |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về trạng thái |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
====[ alt: Kiểm tra điều kiện ghi điểm ]=========================================================================
[Điều kiện 1: Bảng điểm ĐÃ CHỐT (is_locked == true)]
     |                           | 1.4: Từ chối 423 SCORE_TABLE_LOCKED |               |                       |
     |                           |      & hướng sang SD25               |               |                       |
     |                           |< - - - - - - - - - - - - - - - - - -|               |                       |
     | 1.5: Thông báo: bảng điểm |                            |                        |                       |
     |    đã chốt, hãy gửi đơn    |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Điều kiện 2: Đang có đơn gửi duyệt PENDING]
     |                           | 1.6: Từ chối 423 SCORE_SUBMISSION_PENDING           |                       |
     |                           |      (GV phải Hủy đơn trước)                        |                       |
     |                           |< - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
     | 1.7: Thông báo: hãy hủy   |                            |                        |                       |
     |    đơn gửi duyệt trước    |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Cả 2 điều kiện OK]
     | 2: Nhập điểm mới & Lưu     |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 2.1: Chuyển tiếp yêu cầu   |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 2.2: Kiểm tra 0.0 <= Điểm <= 10.0               |
     |                           |                            |----------------------->|                       |
     |                           |                            | 2.3: Cập nhật điểm vào BẢNG ĐIỂM TẠM             |
     |                           |                            |     (is_draft = TRUE)                          |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.4: <<include>> Tính điểm trung bình môn        |
     |                           |                            |     (loại ô NULL khỏi cả tử & mẫu số)          |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.5: Ghi audit log (SỬA ĐIỂM)                 |
     |                           |                            | 2.6: Xác nhận cập nhật thành công              |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.7: Báo sửa thành công    |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
     | 2.8: Hiển thị điểm mới    |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
=======================================================================================================================
```

> **Lưu ý:** nhánh "Đã chốt" **không** xử lý trong sơ đồ này — nó chuyển sang use case **`SD25_GuiYeuCauChinhDiem`** (xem §7.24). Việc tách 2 use case giúp mỗi sơ đồ chỉ có **một luồng nghiệp vụ** rõ ràng.

---

### PHÂN HỆ IV: GIÁO VỤ, QUẢN TRỊ & BÁO CÁO (ACTOR: `GIAOVU`)

#### 7.14 Sơ đồ 14: `SD15_XemNhatKyHeThong` — Xem nhật ký hệ thống
*Ánh xạ Use Case:* `Xem nhật ký hệ thống`  
*Kịch bản:* Giáo vụ lọc lịch sử hoạt động theo mốc thời gian, loại hành động (Sửa điểm, Đổi quy định); Controller truy vấn bảng audit log trong thực thể `NhatKy` và trả kết quả hiển thị.

```
GiaoVu (Actor)        NhatKyView (Boundary)       NhatKyController (Control)                           NhatKy (Entity)
     |                           |                            |                                                |
     | 1: Chọn khoảng thời gian  |                            |                                                |
     |    & loại hành động       |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi bộ lọc nhật ký    |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: fetchSystemLogs(timeRange, actionType)    |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về danh sách nhật ký kiểm toán        |
     |                           |< - - - - - - - - - - - - - |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 1.4: Hiển thị bảng nhật ký |                                                |
     | 1.5: Xem chi tiết vết     |                            |                                                |
     |      hoạt động hệ thống   |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
```

#### 7.15 Sơ đồ 15: `SD16_PhanCongGiangDay` — Phân công giảng dạy
*Ánh xạ Use Case:* `Phân công giảng dạy`  
*Kịch bản:* Giáo vụ chọn giáo viên, môn học, lớp học và học kỳ; Controller kiểm tra xem giáo viên có bị trùng lịch hay lớp đã có người dạy chưa, sau đó ghi dữ liệu vào thực thể `PhanCong`.

```
GiaoVu (Actor)       PhanCongView (Boundary)     PhanCongController (Control)                         PhanCong (Entity)
     |                           |                            |                                                |
     | 1: Chọn GV, Môn, Lớp, HK  |                            |                                                |
     |    và nhấn Lưu phân công  |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi thông tin phân công|                                               |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: checkAssignmentConflict(class, subject)   |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về kết quả (isConflict)               |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                                                |
====[ alt: Kiểm tra trùng lặp phân công ]===============================================================================
[isConflict == true (Lớp môn học này đã có giáo viên phụ trách)]
     |                           | 1.4: Báo lỗi trùng phân công                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.5: Hiển thị cảnh báo    |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[isConflict == false (Hợp lệ)]
     |                           |                            | 2: saveAssignment(teacherId, class, subject)   |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Xác nhận lưu phân công thành công         |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Báo phân công OK      |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 2.3: Hiển thị thông báo   |                            |                                                |
     |      phân công thành công |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
========================================================================================================================
```

#### 7.16 Sơ đồ 16: `SD17_QuanLyTaiKhoanVaPhanQuyen` — Quản lý tài khoản và phân quyền
*Ánh xạ Use Case:* `Quản lý tài khoản và phân quyền` (kết nối `MailServer`)  
*Kịch bản:* Giáo vụ nhập thông tin (username, email, họ tên, role) — KHÔNG nhập mật khẩu; Controller kiểm tra trùng lặp username/email, TỰ SINH mật khẩu tạm, băm BCrypt, lưu vào thực thể `User` kèm cờ `must_change_password=true`, và gọi dịch vụ ngoài `MailServer` gửi email chứa tài khoản + mật khẩu tạm. Người dùng bắt buộc đổi mật khẩu ở lần đăng nhập đầu (`SD02`).

```
GiaoVu (Actor)       TaiKhoanView (Boundary)     TaiKhoanController (Control)   User (Entity)         MailServer (External)
     |                           |                            |                       |                        |
     | 1: Nhập thông tin User    |                            |                       |                        |
     |    (user, email, role)    |                            |                       |                        |
     |-------------------------->|                            |                       |                        |
     |                           | 1.1: Gửi yêu cầu tạo User  |                       |                        |
     |                           |--------------------------->|                       |                        |
     |                           |                            | 1.2: checkExists()    |                        |
     |                           |                            |---------------------->|                        |
     |                           |                            | 1.3: Trả về kết quả   |                        |
     |                           |                            |< - - - - - - - - - - -|                        |
     |                           |                            |                       |                        |
====[ alt: Kiểm tra tính duy nhất của tài khoản ]======================================================================
[Tài khoản hoặc Email đã tồn tại]
     |                           | 1.4: Báo lỗi trùng lặp     |                       |                        |
     |                           |< - - - - - - - - - - - - - |                       |                        |
     | 1.5: Hiển thị lỗi form    |                            |                       |                        |
     |< - - - - - - - - - - - - -|                            |                       |                        |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Thông tin hợp lệ]
     |                           |                            | 2: genTempPassword()  |                        |
     |                           |                            | (Hoa+thường+số+!@#$%)|                       |
     |                           |                            | 2.1: hashPassword()   |                        |
     |                           |                            |----+ (Bcrypt)         |                        |
     |                           |                            |    |                  |                        |
     |                           |                            |<---+                  |                        |
     |                           |                            | 2.2: save(newUser, must_change_password=true) |                        |
     |                           |                            |---------------------->|                        |
     |                           |                            | 2.3: Xác nhận (newId) |                        |
     |                           |                            |< - - - - - - - - - - -|                        |
     |                           |                            |                       |                        |
     |                           |                            | 2.4: sendAccountEmail(email, tempPassword)     |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.5: Phản hồi kết quả gửi mail (Sent OK)       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.6: Báo cấp tài khoản OK  |                       |                        |
     |                           |< - - - - - - - - - - - - - |                       |                        |
     | 2.7: Hiển thị thông báo:  |                            |                       |                        |
     | "Cấp tài khoản & gửi email thành công" (+ bắt đổi MK lần đầu) |           |                        |
     |< - - - - - - - - - - - - -|                            |                       |                        |
=======================================================================================================================
```

#### 7.17 Sơ đồ 17: `SD18_KhoaMoBangDiem` — Khóa / Mở bảng điểm
*Ánh xạ Use Case:* `Khoá mở bảng điểm`  
*Kịch bản:* Giáo vụ chọn Lớp, Môn học và gạt công tắc chuyển trạng thái Khóa/Mở; Controller cập nhật cờ `is_locked` vào thực thể `BangDiem` để kiểm soát quyền sửa điểm của giáo viên.

```
GiaoVu (Actor)       KhoaDiemView (Boundary)     KhoaDiemController (Control)                         BangDiem (Entity)
     |                           |                            |                                                |
     | 1: Chọn Lớp, Môn học      |                            |                                                |
     |    & chọn Khóa / Mở       |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi yêu cầu đổi cờ    |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: updateLockStatus(classId, subject, status)|
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Xác nhận cập nhật thành công (Commit OK)  |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 1.4: Báo cập nhật cờ OK    |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.5: Hiển thị trạng thái  |                            |                                                |
     |      bảng điểm mới        |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
```

#### 7.18 Sơ đồ 18: `SD19_PheDuyetYeuCauChinhDiem` — Phê duyệt yêu cầu chỉnh điểm
*Ánh xạ Use Case:* `Phê duyệt yêu cầu chỉnh điểm`  
*Kịch bản:* Giáo vụ xem danh sách các đơn xin sửa điểm; đối với **đơn lô** hiển thị bảng so sánh điểm cũ ↔ điểm mới (`GET /score-requests/{id}/diff`) và **duyệt/từ chối từng ô**; đối với **đơn lẻ** duyệt/từ chối toàn bộ. Controller thực hiện toàn bộ xử lý trong **1 transaction ACID duy nhất**: cập nhật trạng thái đơn cha + trạng thái từng ô con → ghi điểm mới vào **điểm chính thức** (giữ nguyên `is_draft = FALSE`, **không** đụng tới `is_locked`) → tính lại `average_score` & `is_passed` → ghi `audit_logs` → `INSERT INTO email_outbox` để **gửi mail thông báo tự động** cho Giáo viên sau khi COMMIT. Lỗi ở bất kỳ bước nào → **ROLLBACK toàn bộ**.

```
GiaoVu (Actor)       PheDuyetView (Boundary)     PheDuyetController (Control)  YeuCauSuaDiem (Entity)     Diem (Entity)         AuditLog/EmailOutbox
     |                           |                            |                       |                        |                       |
     | 1: Xem đơn & chọn Duyệt / |                            |                       |                        |                       |
     |    Từ chối cho từng ô     |                            |                       |                        |                       |
     |-------------------------->|                            |                       |                        |                       |
     |                           | 1.1: Gửi quyết định duyệt  |                       |                        |                       |
     |                           |   (decisions[])           |                       |                        |                       |
     |                           |--------------------------->|                       |                        |                       |
     |                           |                            |                       |                        |                       |
====[ alt: Xử lý trong 1 TRANSACTION ACID duy nhất ]==============================================================
[Trường hợp: DUYỆT ô điểm]
     |                           |                            | 1.2: BEGIN TRANSACTION          |                        |                       |
     |                           |                            | 1.3: updateDetailStatus(id, 'APPROVED')             |                       |
     |                           |                            |---------------------->|                        |                       |
     |                           |                            | 1.4: applyNewScore(studentId, col, newValue)        |                       |
     |                           |                            |     GIỮ NGUYÊN is_draft = FALSE (điểm chính thức)  |                       |
     |                           |                            |     KHÔNG đụng tới is_locked (vẫn ĐÃ CHỐT)         |                       |
     |                           |                            |----------------------------------------------->|                       |
     |                           |                            | 1.5: Tính lại ĐTB & is_passed (cùng transaction)    |                       |
     |                           |                            |----------------------------------------------->|                       |
     |                           |                            | 1.6: Ghi audit log + enqueue email_outbox            |                       |
     |                           |                            |-------------------------------------------------------------------------->|
     |                           |                            | 1.7: updateRequestStatus(id, status tổng hợp)     |                       |
     |                           |                            |---------------------->|                        |                       |
     |                           |                            | 1.8: COMMIT (thành công → worker gửi mail)          |                       |
     |                           |                            |                                                                        |                       |
[Trường hợp: LỖI ở bất kỳ bước nào]
     |                           |                            | 1.9: ROLLBACK toàn bộ (không đổi điểm, đơn vẫn PENDING)           |                       |
=======================================================================================================================
[Trường hợp: TỪ CHỐI ô điểm]
     |                           |                            | 2.1: updateDetailStatus(id, 'REJECTED', note)    |                       |
     |                           |                            |---------------------->|                        |                       |
     |                           |                            | 2.2: KHÔNG thay đổi bất kỳ dữ liệu điểm nào (is_draft vẫn FALSE)      |                       |
     |                           |                            | 2.3: Ghi audit log + enqueue email_outbox            |                       |
     |                           |                            |-------------------------------------------------------------------------->|
     |                           | 2.4: Báo kết quả        |                       |                        |                       |
     |                           |< - - - - - - - - - - - - -|                       |                        |                       |
     | 2.5: Cập nhật danh sách &   |                            |                       |                        |                       |
     |    thông báo kết quả        |                            |                       |                        |                       |
     |< - - - - - - - - - - - - -|                            |                       |                        |                       |
```

#### 7.19 Sơ đồ 19: `SD20_XemBaoCaoThongKe` — Báo cáo thống kê & Biểu đồ Chart.js (Yêu cầu 4)
*Ánh xạ Use Case:* `Xem báo cáo thống kê` (chứa `<<include>> Vẽ biểu đồ báo cáo`)  
*Kịch bản:* Giáo vụ lọc báo cáo theo Môn, Học kỳ, Năm học; Controller truy vấn điểm chuẩn từ thực thể `QuyDinh` (`PASSING_SCORE = 5.0`), lấy danh sách điểm từ thực thể `Diem`, đếm số học sinh có $\text{ĐTB} \ge 5.0$, tính tỷ lệ phần trăm đạt và trả dữ liệu JSON để giao diện gọi hàm `new Chart()` của thư viện **Chart.js** vẽ biểu đồ trực quan (`<<include>> Vẽ biểu đồ báo cáo`).

```
GiaoVu (Actor)       BaoCaoView (Boundary)       BaoCaoController (Control)    QuyDinh (Entity)          Diem (Entity)
     |                           |                            |                        |                       |
     | 1: Chọn Môn, Học kỳ,      |                            |                        |                       |
     |    Năm học & bấm Lọc      |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Gửi yêu cầu báo cáo   |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy điểm chuẩn đạt|                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về diemDat    |                       |
     |                           |                            |      (diemDat = 5.0)   |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
     |                           |                            | 1.4: Lấy danh sách điểm các lớp                |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.5: Trả về bảng điểm thô các lớp              |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                        |                       |
     |                           |                            | 1.6: Tính toán thống kê|                       |
     |                           |                            |----+ (Đếm ĐTB >= 5.0,  |                       |
     |                           |                            |    |  tính Tỷ lệ %)    |                       |
     |                           |                            |<---+                   |                       |
     |                           |                            |                        |                       |
     |                           | 1.7: Trả về dữ liệu JSON   |                        |                       |
     |                           |      (bảng số liệu + data) |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     |                           |                            |                        |                       |
====[ <<include>> Vẽ biểu đồ báo cáo ]==================================================================================
     |                           | 1.8: new Chart(ctx, config)|                        |                       |
     |                           |----+ (Gọi thư viện Chart.js|                        |                       |
     |                           |    |  vẽ biểu đồ cột/tròn) |                        |                       |
     |                           |<---+                       |                        |                       |
========================================================================================================================
     | 1.9: Hiển thị Bảng số liệu|                            |                        |                       |
     |      kèm Biểu đồ trực quan|                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
```

#### 7.20 Sơ đồ 20: `SD21_ThayDoiQuyDinh` — Thay đổi quy định (Yêu cầu 5)
*Ánh xạ Use Case:* `Thay đổi quy định`  
*Kịch bản:* Giáo vụ nhập các tham số mới; Controller kiểm tra tính logic đầy đủ (`MIN_AGE < MAX_AGE`, `MAX_CLASS_SIZE > 0`, `MIN_COL_15M ≤ MAX_COL_15M`, `MIN_COL_45M ≤ MAX_COL_45M`, `0 ≤ PASSING_SCORE ≤ 10`, `MAX_LOGIN_ATTEMPTS > 0`), cập nhật giá trị mới vào thực thể `QuyDinh` (`system_rules`, 1 transaction cho bulk) và phản hồi kết quả ra giao diện.

```
GiaoVu (Actor)       QuyDinhView (Boundary)      QuyDinhController (Control)                           QuyDinh (Entity)
     |                           |                            |                                                |
     | 1: Nhập giá trị mới       |                            |                                                |
     |    (tuoiMin, tuoiMax,     |                            |                                                |
     |     siSoToiDa) & bấm Lưu  |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi tham số quy định  |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: Kiểm tra tính hợp lệ logic               |
     |                           |                            |----+ (tuoiMin < tuoiMax,                       |
     |                           |                            |    |  siSoToiDa > 0)                           |
     |                           |                            |<---+                                           |
     |                           |                            |                                                |
====[ alt: Kiểm tra tính hợp lệ logic của quy định ]====================================================================
[Quy định phi logic (VD: tuoiMin >= tuoiMax)]
     |                           | 1.3: Báo tham số không hợp lệ                                               |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.4: Hiển thị lỗi form    |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Tham số hợp lệ]
     |                           |                            | 2: Cập nhật giá trị vào bảng system_rules      |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Xác nhận cập nhật thành công (Commit OK)  |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Báo đổi quy định OK   |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 2.3: Hiển thị thông báo:  |                            |                                                |
     | "Đã cập nhật quy định mới"|                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
========================================================================================================================
```

#### 7.21 Sơ đồ 21: `SD22_QuanLyDanhMucMonHoc` — Quản lý danh mục môn học (Yêu cầu 5)
*Ánh xạ Use Case:* `Quản lý danh mục môn học`  
*Kịch bản:* Giáo vụ thực hiện Thêm mới, Sửa hoặc Xóa môn học của các khối lớp; Controller kiểm tra ràng buộc mã môn học duy nhất và cập nhật vào thực thể `MonHoc`.

```
GiaoVu (Actor)       MonHocView (Boundary)       MonHocController (Control)                            MonHoc (Entity)
     |                           |                            |                                                |
     | 1: Nhập thông tin môn học |                            |                                                |
     |    (maMon, tenMon, khoi)  |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi yêu cầu lưu môn   |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: checkDuplicateSubjectCode(maMon)          |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Trả về kết quả (isDuplicate)              |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            |                                                |
====[ alt: Kiểm tra tính duy nhất của mã môn học ]======================================================================
[isDuplicate == true (Mã môn học đã tồn tại)]
     |                           | 1.4: Báo mã môn đã tồn tại |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.5: Hiển thị cảnh báo lỗi|                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[isDuplicate == false (Hợp lệ)]
     |                           |                            | 2: saveSubject(maMon, tenMon, khoi)            |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.1: Xác nhận lưu môn học thành công           |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.2: Báo lưu môn học OK    |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 2.3: Hiển thị thông báo   |                            |                                                |
     |      thêm môn thành công  |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
========================================================================================================================
```

---

#### 7.22 Sơ đồ 22: `SD23_GuiBangDiemLenDuyet` — Gửi bảng điểm lên duyệt
*Ánh xạ Use Case:* `Gửi bảng điểm lên duyệt`  
*Kịch bản:* Sau khi nhập xong BẢNG ĐIỂM MÔN HỌC (SD11), Giáo viên bấm nút "Gửi duyệt"; Controller kiểm tra bảng điểm đang MỞ (`teaching_assignments.is_locked = false`), **quét toàn bộ `scores` của lớp môn học để bảo đảm không còn ô điểm `NULL` (chưa nhập)** — nếu còn ô trống thì từ chối **422 `INCOMPLETE_SCORES`** kèm danh sách học sinh & cột bị thiếu để GV điền bổ sung (ô trống là lỗi GV; ô `0.00` là hợp lệ — HS vắng hoặc thi 0 điểm). Sau đó đếm số học sinh & số ô điểm đã nhập, tạo bản ghi `score_submissions` ở trạng thái `PENDING` và đóng dấu `scores.submitted_at`. Bảng điểm vẫn giữ cờ `is_draft = TRUE` — **điểm chưa chính thức** cho tới khi Giáo vụ duyệt (SD24).
>
> **Ràng buộc bắt buộc tại bước này (không được bỏ trống):** mọi ô điểm của mọi học sinh trong lớp phải có giá trị (`NOT NULL`) — GV có thể **lưu dở** nhiều lần để soạn tiếp, nhưng **không thể gửi duyệt** khi còn ô trống. Server quét **toàn bộ** bảng điểm của lớp môn học (không chỉ dòng vừa lưu) → không thể lách bằng cách gửi từng phần.
>
> **Nhánh Hủy đơn (`<<extend>> Hủy đơn gửi duyệt`):** Trong lúc đơn đang `PENDING`, GV **không sửa được** ô điểm (bị chặn **423 `SCORE_SUBMISSION_PENDING`** — xem §4.2) → nếu phát hiện sai thì GV bấm **"Hủy"**: `PUT /score-submissions/{id}/cancel` → đơn chuyển `CANCELLED`, `is_draft` & `is_locked` **giữ nguyên** → GV sửa lại bảng điểm tạm rồi **gửi duyệt lại** (tạo đơn `PENDING` mới). Bản ghi cũ giữ lại làm lịch sử audit.
>
> **Sau khi đã duyệt (`APPROVED`):** bảng điểm **đã khóa** → GV **không** sửa được, kể cả không hủy được. Muốn sửa → gửi **đơn phúc khảo** qua **`SD25_GuiYeuCauChinhDiem`** → Giáo vụ duyệt theo **SD19**.

```
GiaoVien (Actor)      GuiDuyetView (Boundary)    GuiDuyetController (Control)   BangDiem (Entity)    BangDiemChoDuyet (Entity)
     |                           |                            |                        |                       |
     | 1: Chọn lớp môn học &    |                            |                        |                       |
     |    nhấn "Gửi duyệt"      |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: POST /score-submissions                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy trạng thái   |                       |
     |                           |                            |      (is_locked)      |                       |
     |                           |                            |---------------------->|                       |
     |                           |                            | 1.3: Trả về trạng thái|                       |
     |                           |                            |< - - - - - - - - - - -|                       |
     |                           |                            |                        |                       |
====[ alt: Kiểm tra điều kiện gửi duyệt ]=======================================================================
[Bảng điểm ĐÃ CHỐT (is_locked == true) HOẶC đã có bản ghi PENDING HOẶC chưa nhập ô điểm nào]
     |                           | 1.4: Báo lỗi (423 / 409 / 422)                   |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 1.5: Hiển thị lỗi,       |                            |                        |                       |
     |     không gửi được        |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Điều kiện hợp lệ]
     |                           |                            | 2: createSubmission(  |                       |
     |                           |                            |    assignmentId, note) |                       |
     |                           |                            |---------------------->|                       |
     |                           |                            | 2.1: Đếm số HS & số ô điểm                    |
     |                           |                            |---------------------------------------------->|
     |                           |                            | 2.2: Tạo bản ghi PENDING |                       |
     |                           |                            |    (total_students,     |                       |
     |                           |                            |     total_scores)       |                       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           |                            | 2.3: Đóng dấu          |                       |
     |                           |                            |     submitted_at trên   |                       |
     |                           |                            |     các dòng scores    |                       |
     |                           |                            |     (is_draft = TRUE)   |                       |
     |                           |                            |---------------------------------------------->|
     |                           | 1.6: Trả về thông báo    |                        |                       |
     |                           |     đã gửi duyệt           |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 1.7: Hiển thị "Đã gửi    |                            |                        |                       |
     |     duyệt, chờ Giáo vụ"   |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Đơn đang PENDING — GV phát hiện sai & bấm "Hủy đơn gửi duyệt"]
     | 1.8: Bấm "Hủy đơn" &      |                            |                        |                       |
     |    nhập lý do hủy         |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.9: PUT /score-submissions/{id}/cancel               |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.10: Kiểm tra status == 'PENDING'          |
     |                           |                            |        & thuộc GV hiện tại                 |
     |                           |                            |---------------------------------------------->|
     |                           |                            | 1.11: status = 'CANCELLED'                 |
     |                           |                            |        + ghi cancelled_at, cancel_note      |
     |                           |                            |        (GIỮ NGUYÊN is_draft = TRUE)          |
     |                           |                            |---------------------------------------------->|
     |                           |                            | 1.12: Xác nhận hủy thành công               |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 1.13: Báo đã hủy, đã mở |                        |                       |
     |    quyền sửa bảng điểm    |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
     | 1.14: Hiển thị: "Đã hủy |                            |                        |                       |
     |     đơn. Bạn có thể sửa  |                            |                        |                       |
     |     lại bảng điểm tạm."   |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
========================================================================================================================
```

---

#### 7.23 Sơ đồ 23: `SD24_DuyetVaChotBangDiem` — Duyệt & Chốt bảng điểm
*Ánh xạ Use Case:* `Duyệt & chốt bảng điểm`  
*Kịch bản:* Giáo vụ xem danh sách bảng điểm chờ duyệt, mở chi tiết để đối chiếu với sổ đạo bì rồi **duyệt** hoặc **từ chối**. Khi **duyệt**, hệ thống thực hiện **trong cùng một transaction (ACID)**: chuyển toàn bộ `scores` của lớp môn học từ `is_draft = TRUE` → `FALSE` (điểm chính thức) **và** đặt `teaching_assignments.is_locked = TRUE` (khóa bảng điểm — Giáo viên không sửa trực tiếp được nữa). Khi **từ chối**, giữ nguyên bản nháp để Giáo viên sửa và gửi lại.

```
GiaoVu (Actor)      DuyetBangDiemView (Boundary)  DuyetBangDiemController (Control)  BangDiem (Entity)  BangDiemChoDuyet (Entity)
     |                           |                            |                        |                     |
     | 1: Xem danh sách bảng     |                            |                        |                     |
     |    điểm chờ duyệt        |                            |                        |                     |
     |-------------------------->|                            |                        |                     |
     |                           | 1.1: GET /score-submissions?status=PENDING             |                     |
     |                           |--------------------------->|                        |                     |
     |                           |                            | 1.2: Trả về danh sách |                     |
     |                           |                            |<---------------------|                     |
     | 1.3: Hiển thị danh sách  |                            |                        |                     |
     |< - - - - - - - - - - - - -|                            |                        |                     |
     |                           |                            |                        |                     |
     | 2: Chọn 1 bảng điểm &    |                            |                        |                     |
     |    nhấn "Duyệt"          |                            |                        |                     |
     |-------------------------->|                            |                        |                     |
     |                           | 1.4: PUT /score-submissions/{id}/approve                |                     |
     |                           |--------------------------->|                        |                     |
     |                           |                            | 2: BEGIN TRANSACTION    |                     |
     |                           |                            | 2.1: updateScoresToOfficial(assignmentId)      |                     |
     |                           |                            |     SET is_draft = FALSE |                     |
     |                           |                            |-------------------->|                     |
     |                           |                            | 2.2: lockScoreTable(assignmentId)            |                     |
     |                           |                            |     SET is_locked = TRUE |                     |
     |                           |                            |-------------------->|                     |
     |                           |                            | 2.3: writeAuditLog(SCORE_TABLE_APPROVED)      |                     |
     |                           |                            |-------------------->|                     |
     |                           |                            | 2.4: COMMIT TRANSACTION |                     |
     |                           |                            | 2.5: Trả về kết quả      |                     |
     |                           |                            |<--------------------|                     |
     |                           | 1.5: Trả về thông báo     |                        |                     |
     |                           |     chốt điểm thành công |                        |                     |
     |                           |< - - - - - - - - - - - - - |                        |                     |
     | 1.6: Hiển thị "Đã chốt   |                            |                        |                     |
     |     bảng điểm"            |                            |                        |                     |
     |< - - - - - - - - - - - - -|                            |                        |                     |
     |                           |                            |                        |                     |
====[ alt: Giáo vụ TỪ CHỐI bảng điểm ]=====================================================================
[Giáo vụ nhấn "Từ chối" kèm lý do -> PUT /score-submissions/{id}/reject]
     |                           |                            | 3: rejectSubmission(id, note)                   |                     |
     |                           |                            |    (giữ nguyên is_draft = TRUE,                |                     |
     |                           |                            |     is_locked vẫn = FALSE)                     |                     |
     |                           |                            |------------------------------------------>|                     |
     |                           | 1.7: Trả về thông báo từ chối, GV sửa & gửi lại   |                     |
     |                           |< - - - - - - - - - - - - - |                        |                     |
========================================================================================================================
```

---

#### 7.24 Sơ đồ 24: `SD25_GuiYeuCauChinhDiem` — Gửi yêu cầu chỉnh điểm (bảng điểm đã CHỐT)
*Ánh xạ Use Case:* `Gửi yêu cầu chỉnh điểm` (phúc khảo)  
*Kịch bản:* Bảng điểm đã **CHỐT** (`teaching_assignments.is_locked = true`) → Giáo viên **không** sửa trực tiếp được. GV dùng **biểu mẫu có cấu trúc trên Web**: chọn **Lớp → Học sinh → Môn học → Cột điểm**; hệ thống hiển thị **Điểm hiện tại ở chế độ CHỈ ĐỌC**; GV nhập **Điểm đề xuất sửa** + **Lý do (bắt buộc)** và **đính kèm ảnh/PDF (tùy chọn)** rồi gửi. Server đối chiếu `old_value` với điểm thực tế (lệch → **409 `SCORE_VALUE_CONFLICT`**), lưu đơn vào `YeuCauSuaDiem` (đơn cha) kèm các dòng `ChiTietSuaDiem` (đơn con) → chờ **SD19** (Giáo vụ duyệt). Hỗ trợ **đơn lẻ** (1 ô điểm) và **đơn lô** (nhiều ô điểm của nhiều học sinh).

```
GiaoVien (Actor)       YeuCauSuaDiemView (B)     YeuCauSuaDiemController (C) BangDiem (Entity)        YeuCauSuaDiem (Entity)
     |                           |                            |                       |                       |
     | 1: Chọn Lớp -> Học sinh   |                            |                       |                       |
     |    -> Môn học -> Cột điểm |                            |                       |                       |
     |-------------------------->|                            |                       |                       |
     |                           | 1.1: Gửi yêu cầu sửa điểm  |                       |                       |
     |                           |--------------------------->|                       |                       |
     |                           |                            | 1.2: Lấy trạng thái    |                       |
     |                           |                            |      (is_locked)       |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về trạng thái |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            | 1.4: Lấy ĐIỂM HIỆN TẠI |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.5: Trả về điểm cũ   |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           | 1.6: Hiển thị ĐIỂM HIỆN TẠI (CHỈ ĐỌC)            |                       |
     |< - - - - - - - - - - - - -|                            |                       |                       |
     | 2: Nhập ĐIỂM ĐỀ XUẤT + LÝ DO (bắt buộc)              |                       |                       |
     |    + file ảnh/PDF (TÙY CHỌN) & Gửi yêu cầu            |                       |                       |
     |-------------------------->|                            |                       |                       |
     |                           | 2.1: Chuyển tiếp yêu cầu   |                       |                       |
     |                           |--------------------------->|                       |                       |
     |                           |                            | 2.2: Đối chiếu old_value|                      |
     |                           |                            |      vs điểm thực tế    |                      |
     |                           |                            |----------------------->|                       |
     |                           |                            | 2.3: Nếu lệch -> 409     |                      |
     |                           |                            |      SCORE_VALUE_CONFLICT                      |
     |                           |                            | 2.4: Tạo đơn xin sửa điểm (chờ duyệt)          |
     |                           |                            |      + chi tiết từng ô điểm                |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.5: Xác nhận đã ghi nhận yêu cầu              |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.6: Báo đã gửi duyệt      |                       |                       |
     |< - - - - - - - - - - - - -|                            |                       |                       |
     | 2.7: Hiển thị thông báo:  |                            |                       |                       |
     | "Đã gửi yêu cầu tới Giáo vụ chờ phê duyệt"             |                       |                       |
     |< - - - - - - - - - - - - -|                            |                       |                       |
=======================================================================================================================
```

> **Vì sao tách khỏi SD14?** `SD14` (sửa bảng điểm tạm, bảng điểm đang MỞ) và `SD25` (gửi đơn phúc khảo, bảng điểm đã CHỐT) là **2 nghiệp vụ khác nhau về bản chất**:
> * Khác **dữ liệu đầu ra**: ghi vào bảng điểm tạm vs tạo đơn chờ duyệt.
> * Khác **cơ chế kiểm duyệt**: tự quyết định (không cần ai duyệt) vs bắt buộc Giáo vụ duyệt.
> * Khác **mức độ rủi ro**: sửa nháp vs thay đổi điểm chính thức đã công bố.
>
> Tách ra giúp mỗi sơ đồ chỉ có **một luồng** dễ đọc, và ánh xạ 1–1 với use case trong bảng §4.

---

## 8. Tiêu chuẩn An toàn & Bảo mật (Security Requirements)

| Hạng mục an toàn | Biện pháp kỹ thuật triển khai chi tiết |
|------------------|----------------------------------------|
| **Lưu trữ mật khẩu** | Mật khẩu được băm một chiều bằng giải thuật `bcrypt` kết hợp chuỗi muối (salt) tự sinh với hệ số phức tạp $\ge 12$. Tuyệt đối không lưu mật khẩu thô trong database. |
| **Bảo vệ chống Brute-force** | Lưu trữ trường `failed_attempts` và `is_locked` trong bảng `users`. Hệ thống tự động kích hoạt cờ khóa tài khoản khi số lần nhập sai liên tiếp đạt ngưỡng $\ge 5$. Chỉ có Giáo vụ/Admin mới có quyền mở khóa tài khoản. |
| **Quản lý phiên làm việc** | Sử dụng Session phía máy chủ có ký số mật mã bí mật (`SECRET_KEY`); tự động thu hồi phiên sau 30 phút không phát sinh thao tác từ người dùng. |
| **Kiểm soát truy cập (RBAC)** | Đính kèm vai trò người dùng vào Session (`STAFF`, `TEACHER`, `ACADEMIC`); kiểm tra quyền hạn ở từng route bằng Custom Decorators để ngăn chặn việc leo thang đặc quyền (Privilege Escalation). |
| **Chống SQL Injection** | Sử dụng ORM SQLAlchemy với kỹ thuật tham số hóa câu truy vấn (Parameterized Queries); nghiêm cấm hoàn toàn việc cộng chuỗi SQL thô. |
| **Chống XSS & CSRF** | Escape ký tự đầu ra mặc định bằng Template Engine Jinja2; nhúng và xác thực mã CSRF Token đối với tất cả các thao tác gửi form qua giao thức `POST`. |

---

## 9. Tính mở rộng & Quy chuẩn thiết kế (Architecture & Design Principles)

| Nguyên lý áp dụng | Giải pháp kiến trúc chi tiết trong hệ thống |
|-------------------|---------------------------------------------|
| **Service - Repository Pattern** | Phân tách rạch ròi giữa logic nghiệp vụ (Service) và câu lệnh truy xuất dữ liệu (Repository). Khi cần đổi từ cơ sở dữ liệu MySQL sang PostgreSQL hoặc Oracle, chỉ cần thay đổi tầng Repository mà không làm ảnh hưởng đến mã nguồn tầng Controller và Service. |
| **Cấu hình động (Soft Rules)** | Không hard-code các giới hạn quy chế vào code. Toàn bộ các thông số quy chế được quản lý tập trung tại bảng `system_rules`. Nhà trường có thể điều chỉnh quy chế ngay trên giao diện mà không cần biên dịch hay khởi động lại server. |
| **Mô hình phân tích BCE** | Các lớp giao diện Boundary được tách biệt hoàn toàn khỏi logic điều khiển Control. Trong tương lai, hệ thống có thể dễ dàng bổ sung ứng dụng di động (Mobile App) hoặc giao diện Single Page Application (React/Vue) bằng cách tái sử dụng 100% tầng Controller và Service thông qua các RESTful API endpoints. |
| **Nguyên lý SOLID (SRP, DIP)** | Mỗi lớp đảm nhiệm một trách nhiệm duy nhất; các Controller phụ thuộc vào interface của Service thông qua cơ chế Dependency Injection, tạo điều kiện thuận lợi cho việc viết Unit Test và tích hợp kiểm thử tự động (CI/CD). |