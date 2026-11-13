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
Chịu trách nhiệm về chuyên môn giảng dạy, tra cứu danh sách học sinh các lớp phụ trách, điểm danh, nhập các cột điểm thành phần (15 phút, 1 tiết, thi cuối kỳ) theo đúng quy chế số cột, xem và xuất bảng điểm trung bình. Khi bảng điểm đã bị khóa, giáo viên tạo đơn yêu cầu sửa điểm gửi Giáo vụ.

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
| 10 | `Điểm danh học sinh` | `SD10_DiemDanhHocSinh` | `GiaoVien` | Ghi nhận trạng thái chuyên cần (Có mặt, Vắng phép, Vắng không phép) theo từng buổi học. |
| 11 | `Nhập điểm môn học` | `SD11_NhapDiemMonHoc` | `GiaoVien` | **Yêu cầu 3:** 15 phút (1-5 cột), 1 tiết (1-3 cột), 1 điểm thi; chỉ khi bảng điểm **MỞ** (`is_locked = false`, khóa → SD14); `<<include>> Tính điểm trung bình môn`. |
| 12 | `Xem bảng điểm trung bình lớp` | `SD12_XemBangDiemTrungBinhLop` | `GiaoVien` | **Yêu cầu 3:** Tổng hợp bảng điểm học kỳ và cả năm học (HK1, HK2); `<<include>> Tính điểm trung bình môn`. |
| 13 | `Xuất bảng điểm trung bình lớp` | `SD13_XuatBangDiemTrungBinhLop` | `GiaoVien` | **Yêu cầu 3:** Xuất dữ liệu bảng điểm lớp ra file báo cáo chuẩn Excel/PDF theo mẫu quy định. |
| 14 | `Sửa điểm học sinh` | `SD14_SuaDiemHocSinh` | `GiaoVien` | **Yêu cầu 3:** Mở bảng điểm thì cho sửa; Đã khóa thì gọi `<<extend>> Gửi yêu cầu chỉnh điểm`. |
| **IV** | **Phân hệ Giáo vụ / Quản trị (Học vụ & Báo cáo)** | | | |
| 15 | `Xem nhật ký hệ thống` | `SD15_XemNhatKyHeThong` | `GiaoVu` | Audit log: Tra cứu lịch sử truy cập, sửa đổi điểm số và thay đổi quy định. |
| 16 | `Phân công giảng dạy` | `SD16_PhanCongGiangDay` | `GiaoVu` | Gán giáo viên giảng dạy bộ môn cho các lớp học theo từng năm học/học kỳ. |
| 17 | `Quản lý tài khoản và phân quyền` | `SD17_QuanLyTaiKhoanVaPhanQuyen` | `GiaoVu` | Cấp tài khoản (`STAFF`, `TEACHER`, `ACADEMIC`), băm BCrypt, tích hợp gửi mail kích hoạt qua `MailServer`; chốt an toàn: không tự khóa chính mình (400), giữ đúng 1 ACADEMIC duy nhất: xin thêm ACADEMIC → 422; không tự khóa chính mình (400); admin gốc bất khả xâm phạm qua API, admin thường không được động vào admin khác (403). |
| 18 | `Khoá mở bảng điểm` | `SD18_KhoaMoBangDiem` | `GiaoVu` | Đóng/mở trạng thái cho phép nhập điểm của một môn học/lớp học. |
| 19 | `Phê duyệt yêu cầu chỉnh điểm` | `SD19_PheDuyetYeuCauChinhDiem` | `GiaoVu` | Duyệt hoặc từ chối các đơn xin sửa điểm của Giáo viên; mở khóa tạm thời cho học sinh được duyệt. |
| 20 | `Xem báo cáo thống kê` | `SD20_XemBaoCaoThongKe` | `GiaoVu` | **Yêu cầu 4:** Điểm đạt $\ge 5.0$, tính số lượng đạt & tỷ lệ %; `<<include>> Vẽ biểu đồ báo cáo` (Chart.js). |
| 21 | `Thay đổi quy định` | `SD21_ThayDoiQuyDinh` | `GiaoVu` | **Yêu cầu 5:** Đổi quy chế (`system_rules`); validate logic: `MIN_AGE < MAX_AGE`, `MAX_CLASS_SIZE > 0`, `MIN_COL ≤ MAX_COL`, `0 ≤ PASSING_SCORE ≤ 10`, `MAX_LOGIN_ATTEMPTS > 0`. |
| 22 | `Quản lý danh mục môn học` | `SD22_QuanLyDanhMucMonHoc` | `GiaoVu` | **Yêu cầu 5:** Quản lý môn học các khối lớp (Thêm, Xóa, Cập nhật, Tìm kiếm môn học). |

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

## 7. Toàn Bộ 22 Sơ Đồ Sequence Diagram Chi Tiết (Chuẩn Mô Hình BCE)

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

#### 7.10 Sơ đồ 10: `SD10_DiemDanhHocSinh` — Điểm danh học sinh
*Ánh xạ Use Case:* `Điểm danh học sinh`  
*Kịch bản:* Giáo viên chọn ngày, tích chọn trạng thái điểm danh cho từng học sinh (Có mặt, Có phép, Không phép); Controller kiểm tra dữ liệu và lưu thông tin vào thực thể `DiemDanh`.

```
GiaoVien (Actor)      DiemDanhView (Boundary)    DiemDanhController (Control)                         DiemDanh (Entity)
     |                           |                            |                                                |
     | 1: Chọn ngày & tích chọn  |                            |                                                |
     |    trạng thái chuyên cần  |                            |                                                |
     |-------------------------->|                            |                                                |
     |                           | 1.1: Gửi bảng điểm danh    |                                                |
     |                           |--------------------------->|                                                |
     |                           |                            | 1.2: saveAttendanceBatch(classId, date, data)  |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.3: Xác nhận lưu thành công (Commit OK)       |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 1.4: Báo lưu điểm danh OK  |                                                |
     |                           |< - - - - - - - - - - - - - |                                                |
     | 1.5: Hiển thị thông báo   |                            |                                                |
     |      điểm danh thành công |                            |                                                |
     |< - - - - - - - - - - - - -|                            |                                                |
```

#### 7.11 Sơ đồ 11: `SD11_NhapDiemMonHoc` — Nhập điểm môn học (Yêu cầu 3)
*Ánh xạ Use Case:* `Nhập điểm môn học` (chứa `<<include>> Tính điểm trung bình môn`)  
*Kịch bản:* Giáo viên nhập các cột điểm thành phần theo biểu mẫu BẢNG ĐIỂM MÔN HỌC (15' có 1-5 cột, 1 tiết có 1-3 cột, 1 điểm thi); Controller **kiểm tra `teaching_assignments.is_locked` trước — nếu ĐÃ KHÓA thì từ chối 423 và hướng sang SD14 (gửi yêu cầu sửa điểm)**; nếu MỞ thì lấy quy định cột từ `QuyDinh`, kiểm tra khoảng điểm $0.0 \le \text{Điểm} \le 10.0$, tự động thực hiện luồng bao hàm `<<include>> Tính điểm trung bình môn` cho từng học sinh và lưu vào thực thể `Diem`.

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
[Dữ liệu điểm hợp lệ]
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

#### 7.12 Sơ đồ 12: `SD12_XemBangDiemTrungBinhLop` — Xem bảng điểm trung bình lớp (Yêu cầu 3)
*Ánh xạ Use Case:* `Xem bảng điểm trung bình lớp` (chứa `<<include>> Tính điểm trung bình môn`)  
*Kịch bản:* Giáo viên chọn Lớp, Môn học, Năm học; Controller truy vấn điểm thành phần các học kỳ từ thực thể `Diem`, tự động tính điểm trung bình môn cả năm học và hiển thị theo biểu mẫu BẢNG ĐIỂM MÔN HỌC (STT, Họ tên, Lớp, Điểm TB HK1, Điểm TB HK2).

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

#### 7.13 Sơ đồ 13: `SD13_XuatBangDiemTrungBinhLop` — Xuất bảng điểm trung bình lớp (Yêu cầu 3)
*Ánh xạ Use Case:* `Xuất bảng điểm trung bình lớp`  
*Kịch bản:* Giáo viên bấm nút "Xuất bảng điểm"; Controller tổng hợp dữ liệu điểm trung bình từ thực thể `Diem`, đóng gói thành file Excel/PDF chuẩn biểu mẫu trường và gửi về cho trình duyệt tự động tải xuống.

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

#### 7.14 Sơ đồ 14: `SD14_SuaDiemHocSinh` — Sửa điểm & Gửi yêu cầu chỉnh điểm (Yêu cầu 3)
*Ánh xạ Use Case:* `Sửa điểm học sinh` (chứa quan hệ `<<extend>> Gửi yêu cầu chỉnh điểm`)  
*Kịch bản:* Giáo viên nhập điểm mới cần sửa; Controller kiểm tra trạng thái khóa của bảng điểm từ thực thể `BangDiem` (Extension Point). Nếu bảng điểm còn **Mở**, cập nhật trực tiếp; nếu **Đã khóa**, kích hoạt luồng mở rộng `<<extend>> Gửi yêu cầu chỉnh điểm` yêu cầu giáo viên nhập lý do và lưu đơn vào thực thể `YeuCauSuaDiem` để chờ Giáo vụ phê duyệt.

```
GiaoVien (Actor)       SuaDiemView (Boundary)     SuaDiemController (Control)   BangDiem (Entity)        YeuCauSuaDiem (Entity)
     |                           |                            |                        |                       |
     | 1: Nhập điểm mới cần sửa  |                            |                        |                       |
     |    và nhấn Lưu thay đổi   |                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 1.1: Gửi yêu cầu sửa điểm  |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 1.2: Lấy trạng thái    |                       |
     |                           |                            |      (is_locked)       |                       |
     |                           |                            |----------------------->|                       |
     |                           |                            | 1.3: Trả về trạng thái |                       |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           |                            |                        |                       |
====[ alt: Kiểm tra trạng thái khóa của Bảng điểm (Extension Point) ]==================================================
[Extension Condition: Bảng điểm ĐÃ BỊ KHÓA (is_locked == true)] -> <<extend>> Gửi yêu cầu chỉnh điểm
     |                           | 1.4: Báo bảng điểm đã khóa,|                        |                       |
     |                           |      yêu cầu nhập lý do    |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 1.5: Hiển thị form lý do  |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
     | 2: Nhập lý do & Gửi yêu cầu                            |                        |                       |
     |-------------------------->|                            |                        |                       |
     |                           | 2.1: Chuyển tiếp yêu cầu   |                        |                       |
     |                           |--------------------------->|                        |                       |
     |                           |                            | 2.2: Tạo đơn xin sửa điểm (chờ duyệt)          |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 2.3: Xác nhận đã ghi nhận yêu cầu              |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 2.4: Báo đã gửi duyệt      |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 2.5: Hiển thị thông báo:  |                            |                        |                       |
     | "Đã gửi yêu cầu tới Giáo vụ chờ phê duyệt"             |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Bảng điểm ĐANG MỞ (is_locked == false)]
     |                           |                            | 3: Cập nhật điểm trực tiếp                     |
     |                           |                            |----------------------->|                       |
     |                           |                            | 3.1: Xác nhận cập nhật thành công              |
     |                           |                            |< - - - - - - - - - - - |                       |
     |                           | 3.2: Báo sửa thành công    |                        |                       |
     |                           |< - - - - - - - - - - - - - |                        |                       |
     | 3.3: Hiển thị điểm mới    |                            |                        |                       |
     |< - - - - - - - - - - - - -|                            |                        |                       |
========================================================================================================================
```

---

### PHÂN HỆ IV: GIÁO VỤ, QUẢN TRỊ & BÁO CÁO (ACTOR: `GIAOVU`)

#### 7.15 Sơ đồ 15: `SD15_XemNhatKyHeThong` — Xem nhật ký hệ thống
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

#### 7.16 Sơ đồ 16: `SD16_PhanCongGiangDay` — Phân công giảng dạy
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

#### 7.17 Sơ đồ 17: `SD17_QuanLyTaiKhoanVaPhanQuyen` — Quản lý tài khoản và phân quyền
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

#### 7.18 Sơ đồ 18: `SD18_KhoaMoBangDiem` — Khóa / Mở bảng điểm
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

#### 7.19 Sơ đồ 19: `SD19_PheDuyetYeuCauChinhDiem` — Phê duyệt yêu cầu chỉnh điểm
*Ánh xạ Use Case:* `Phê duyệt yêu cầu chỉnh điểm`  
*Kịch bản:* Giáo vụ xem danh sách các đơn xin sửa điểm; nhấn "Duyệt" hoặc "Từ chối"; Controller cập nhật trạng thái đơn trong thực thể `YeuCauSuaDiem` và mở quyền cập nhật điểm cho học sinh tương ứng.

```
GiaoVu (Actor)       PheDuyetView (Boundary)     PheDuyetController (Control)  YeuCauSuaDiem (Entity)     Diem (Entity)
     |                           |                            |                       |                        |
     | 1: Xem đơn & bấm          |                            |                       |                        |
     |    "Duyệt" / "Từ chối"    |                            |                       |                        |
     |-------------------------->|                            |                       |                        |
     |                           | 1.1: Gửi quyết định duyệt  |                       |                        |
     |                           |--------------------------->|                       |                        |
     |                           |                            |                       |                        |
====[ alt: Xử lý theo quyết định của Giáo vụ ]=========================================================================
[Trường hợp: DUYỆT yêu cầu]
     |                           |                            | 1.2: updateRequestStatus(id, 'APPROVED')       |
     |                           |                            |---------------------->|                        |
     |                           |                            | 1.3: Xác nhận thành công                       |
     |                           |                            |< - - - - - - - - - - -|                        |
     |                           |                            | 1.4: applyNewScore(studentId, newScore)        |
     |                           |                            |----------------------------------------------->|
     |                           |                            | 1.5: Cập nhật điểm thành công                  |
     |                           |                            |< - - - - - - - - - - - - - - - - - - - - - - - |
     |                           | 1.6: Báo phê duyệt OK      |                       |                        |
     |                           |< - - - - - - - - - - - - - |                       |                        |
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
[Trường hợp: TỪ CHỐI yêu cầu]
     |                           |                            | 2: updateRequestStatus(id, 'REJECTED', reason) |
     |                           |                            |---------------------->|                        |
     |                           |                            | 2.1: Xác nhận thành công                       |
     |                           |                            |< - - - - - - - - - - -|                        |
     |                           | 2.2: Báo từ chối OK        |                       |                        |
     |                           |< - - - - - - - - - - - - - |                       |                        |
=======================================================================================================================
     | 2.3: Cập nhật giao diện   |                            |                       |                        |
     |      danh sách phê duyệt  |                            |                       |                        |
     |< - - - - - - - - - - - - -|                            |                       |                        |
```

#### 7.20 Sơ đồ 20: `SD20_XemBaoCaoThongKe` — Báo cáo thống kê & Biểu đồ Chart.js (Yêu cầu 4)
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

#### 7.21 Sơ đồ 21: `SD21_ThayDoiQuyDinh` — Thay đổi quy định (Yêu cầu 5)
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

#### 7.22 Sơ đồ 22: `SD22_QuanLyDanhMucMonHoc` — Quản lý danh mục môn học (Yêu cầu 5)
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