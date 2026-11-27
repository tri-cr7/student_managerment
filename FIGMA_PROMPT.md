# PROMPT THIẾT KẾ FIGMA — HỆ THỐNG QUẢN LÝ HỌC SINH (API-First)

> **Cách dùng:** Copy nguyên khối "PROMPT CHÍNH" bên dưới vào Figma AI (`Figma Make` / `First Draft` / plugin AI) hoặc dán vào Claude/GPT để sinh ra bộ frame Figma.
> Khối "PHỤ LỤC" là dữ liệu tham chiếu — có thể gửi kèm nếu AI cần ngữ cảnh đầy đủ về nghiệp vụ.

---

# PROMPT CHÍNH

## 0. Bối cảnh dự án

Tôi đang xây dựng một **hệ thống quản lý học sinh trường phổ thông Việt Nam**, viết bằng **Python Flask + SQLAlchemy + MySQL**, kiến trúc **thuần REST API** (không có server-side template, không có giao diện web cũ). Toàn bộ giao diện người dùng sẽ được dựng ở Figma để giao cho frontend (React/Next.js) cắm vào API.

Hệ thống có **3 vai trò người dùng**:
- **STAFF** (Nhân viên / Giáo vụ) — tiếp nhận hồ sơ học sinh, quản lý lớp, phân bổ học sinh
- **TEACHER** (Giáo viên) — nhập điểm, gửi đơn phúc khảo
- **ACADEMIC** (Giáo vụ / Admin) — quản trị toàn hệ thống, danh mục, quy định, phê duyệt

Ngôn ngữ giao diện: **Tiếng Việt (UTF-8, dấu đầy đủ)**. Không dùng tiếng Anh cho label hiển thị.

---

## 1. Yêu cầu phong cách (STYLE) — QUAN TRỌNG NHẤT

> **Phong cách: Đơn giản, phẳng, sạch, hệ thống hóa.** Đây là phần tôi muốn bạn ưu tiên tuyệt đối.

**Nguyên tắc thiết kế:**

1. **Flat design thuần** — KHÔNG gradient, KHÔNG drop-shadow mạnh, KHÔNG glassmorphism, KHÔNG neumorphism, KHÔNG hiệu ứng 3D/sketch. Tối đa 1 shadow rất nhạt (`0 1px 2px rgba(0,0,0,0.05)`) để tách lớp.
2. **Dùng đường viền (border) thay vì đổ bóng** để phân tách khối. Border chính: `1px solid #E5E7EB`.
3. **Bảng là trung tâm** — đây là ứng dụng quản lý dữ liệu, màn hình nào cũng xoay quanh bảng dữ liệu + form. Ưu tiên tối giản hoá bảng.
4. **Ít màu** — màu chỉ dùng để mang ý nghĩa trạng thái. Không trang trí.
5. **Nhiều khoảng trắng** — padding rộng rãi, thoáng, dễ đọc.
6. **Bo góc nhẹ** — bo góc 6px (card/button/input), 4px (chip nhỏ). Không bo tròn kiểu "pill" trừ khi là chip trạng thái.
7. **Không dùng ảnh minh hoạ, không icon phức tạp, không gradient text.** Icon tối giản dạng line (stroke 1.5px) hoặc bỏ hẳn.
8. **Tập trung vào khả năng đọc dữ liệu** hơn là trải nghiệm thị giác. Giống Linear / Notion / Vercel Dashboard hơn là Material Design.

---

## 2. Design System (Design Tokens)

### 2.1 Màu sắc — Bảng màu tối giản

**Màu nền & chữ:**
| Token | Hex | Dùng cho |
|---|---|---|
| `bg/page` | `#F9FAFB` | Nền trang ngoài cùng |
| `bg/surface` | `#FFFFFF` | Nền card, bảng, sidebar |
| `bg/subtle` | `#F3F4F6` | Nền header bảng, nền ô input readonly, zebra row |
| `border/default` | `#E5E7EB` | Đường viền mặc định |
| `border/strong` | `#D1D5DB` | Đường viền khi hover/focus |
| `text/primary` | `#111827` | Tiêu đề, dữ liệu chính |
| `text/secondary` | `#6B7280` | Nhãn phụ, placeholder, caption |
| `text/tertiary` | `#9CA3AF` | Icon, chữ rất nhỏ |

**Màu nhấn (chỉ 1 màu chủ đạo):**
| Token | Hex | Dùng cho |
|---|---|---|
| `primary/600` | `#2563EB` | Nút chính, link, focus ring, active nav |
| `primary/50` | `#EFF6FF` | Nền active nav item, badge info, row highlight |
| `primary/700` | `#1D4ED8` | Hover nút chính |

**Màu trạng thái (semantic — dùng cho chip & badge, KHÔNG dùng làm nền nút):**
| Token | Hex | Nền chip | Dùng cho |
|---|---|---|---|
| `success` | `#059669` | `#ECFDF5` | Thành công, `DANG_HOC`, Đã duyệt |
| `warning` | `#D97706` | `#FFFBEB` | Cảnh báo, `CHUYEN_TRUONG`, Chờ duyệt |
| `danger` | `#DC2626` | `#FEF2F2` | Lỗi, Xoá, `TOT_NGHIEP`, Từ chối |
| `info` | `#0891B2` | `#ECFEFF` | Thông tin, `THOI_HOC` |
| `neutral` | `#6B7280` | `#F3F4F6` | Mặc định, `DA_CHUYEN`, Nháp |

### 2.2 Typography

Font: **Inter** (fallback: `-apple-system, Segoe UI, Roboto, sans-serif`).

| Token | Size / Line-height | Weight | Dùng cho |
|---|---|---|---|
| `display` | 24 / 32 | 600 | Tiêu đề trang |
| `title` | 18 / 24 | 600 | Tiêu đề card, section |
| `subtitle` | 16 / 24 | 600 | Tiêu đề modal |
| `body` | 14 / 20 | 400 | Nội dung, text input |
| `body/medium` | 14 / 20 | 500 | Nhãn table header, nút |
| `caption` | 12 / 16 | 400 | Helper text, meta, badge |
| `mono` | 13 / 20 | 500 | Mã học sinh, mã lớp, mã môn (font: `JetBrains Mono`/`SF Mono`) |

### 2.3 Spacing & Shape

- **Spacing scale:** `4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 px` (chỉ dùng các giá trị này).
- **Border radius:** `4px` (chip, badge), `6px` (button, input, card), `8px` (modal, dropdown).
- **Shadow:** chỉ 1 cấp — `0 1px 2px rgba(0,0,0,0.05)`.

---

## 3. Quy tắc bố cục chung (LAYOUT SYSTEM)

### 3.1 App Shell

```
┌────────────────────────────────────────────────────────────────┐
│  TOPBAR (h=56px, bg #FFFFFF, border-bottom #E5E7EB)            │
│  Logo | Tên trường | ... | Năm học 2026-2027 ▾ | Học kỳ 1 ▾   │
│                       | 🔔 | Avatar ▾                            │
├──────────────┬─────────────────────────────────────────────────┤
│              │                                                  │
│  SIDEBAR     │   MAIN CONTENT (bg #F9FAFB, padding 24px)       │
│  (w=240px)   │                                                  │
│  bg #FFFFFF  │   ┌ PageHeader ─────────────────────────────┐  │
│  border-right│   │  Tiêu đề            [Nút phụ] [Nút chính]│  │
│              │   └──────────────────────────────────────────┘  │
│  - Điều hướng│   ┌ Card (bg #FFF, border, radius 8) ───────┐  │
│  theo vai trò│   │  [Toolbar: search | filter | actions]    │  │
│              │   │  ┌ Bảng dữ liệu ─────────────────────┐  │  │
│              │   │  │  ...                                │  │  │
│              │   │  └────────────────────────────────────┘  │  │
│              │   │  [Pagination]                          │  │
│              │   └──────────────────────────────────────────┘  │
└──────────────┴─────────────────────────────────────────────────┘
```

- **Sidebar 240px**, nền trắng, border-right `#E5E7EB`.
- **Topbar 56px** cố định, nền trắng, border-bottom.
- **Main content**: nền `#F9FAFB`, padding 24px, max-width 1440px (canh giữa).
- **Sidebar có thể thu gọn** (icon-only, 64px) — chỉ cần 1 frame minh hoạ trạng thái thu gọn.

### 3.2 Page Header (dùng lại cho MỌI trang)

- Tiêu đề (`display`, 24px/600) + mô tả nhỏ (`caption`, `#6B7280`) bên dưới.
- Bên phải: nút phụ (secondary/outline) rồi tới nút chính (primary).
- Có breadcrumb `caption` phía trên tiêu đề khi cần (cấp 2 trở lên).

### 3.3 Card

- `bg #FFFFFF`, `border 1px #E5E7EB`, `radius 8px`, padding 20-24px.
- Header card: tiêu đề `title` 18px + nút phụ ở bên phải, border-bottom, padding-bottom 16px, margin-bottom 16px.
- Không đổ bóng nặng.

### 3.4 Bảng dữ liệu (Table) — phần tập trung nhất

Cấu trúc:
- **Header row**: nền `#F3F4F6`, chữ `body/medium` 14px màu `#6B7280`, cao 40px, border-bottom `#E5E7EB`, text-transform không dùng (giữ nguyên tiếng Việt).
- **Body row**: cao 48px, border-bottom `#F3F4F6`. **Zebra striping rất nhẹ**: row lẻ nền `#FFFFFF`, row chẵn nền `#FCFCFD`.
- **Hover row**: nền `#F9FAFB`.
- **Cột**: STT (48px, căn giữa) · Mã (mono) · Họ tên (medium) · Các cột thông tin · Trạng thái (chip, 120px) · Thao tác (icon buttons, 100px, căn phải).
- **Row action**: icon button 32×32, radius 6px, hover nền `#F3F4F6`, icon `#6B7280`.
- **Phân trang**: nằm dưới bảng, căn phải. Text `caption` "Hiển thị 1–20 trên 137 học sinh" + nút `< >` + số trang dạng chip (trang hiện tại nền `#EFF6FF`, chữ `#2563EB`).

### 3.5 Form & Input

- **Label** `body/medium` 14px `#111827`, cách input 6px. Bắt buộc có dấu `*` màu `#DC2626`.
- **Input**: cao 38px, `bg #FFFFFF`, `border 1px #D1D5DB`, radius 6px, padding `0 12px`, placeholder `#9CA3AF`.
- **Focus**: `border #2563EB` + `ring 3px rgba(37,99,235,0.12)`.
- **Error**: `border #DC2626`, helper text 12px `#DC2626` dưới input.
- **Select**: giống input + chevron `▾` bên phải.
- **Textarea**: min-height 88px, resize vertical.
- **Checkbox / Radio**: 16px, bo góc 4px, checked nền `#2563EB` dấu trắng.
- **Bố cục form**: 2 cột (label 5 / field 7) trên desktop, 1 cột trên mobile. Field chiếm cả 2 cột khi là field đặc biệt (địa chỉ, ghi chú).
- **Nhóm field**: có `title` 14px/600 ở trên, cách nhóm 24px, giữa các nhóm có 1px divider `#F3F4F6`.

### 3.6 Nút (Button)

| Loại | Nền | Chữ | Border | Dùng khi |
|---|---|---|---|---|
| Primary | `#2563EB` | `#FFFFFF` | — | Hành động chính, 1 nút duy nhất mỗi vùng |
| Secondary | `#FFFFFF` | `#111827` | `1px #D1D5DB` | Hành động phụ |
| Ghost | trong suốt | `#6B7280` | — | Icon action, hành động nhẹ |
| Danger | `#DC2626` | `#FFFFFF` | — | Xoá, từ chối |
| Danger-outline | `#FFFFFF` | `#DC2626` | `1px #FCA5A5` | Xoá trong bảng/dialog |

- Cao **38px** (mặc định) / **32px** (size `sm`, trong bảng) / **44px** (size `lg`, form mobile).
- Padding ngang 16px (mặc định), 12px (sm).
- Radius 6px, chữ 14px/500.
- **Trạng thái**: hover đậm 1 bậc, disabled `#F3F4F6` + chữ `#9CA3AF` + không cursor.
- Luôn có **icon tối giản 16px** bên trái nút chính khi hành động dễ nhận biết (VD: `+ Tiếp nhận`, `↑ Import`, `↓ Xuất`).

### 3.7 Chip / Badge trạng thái

- Cao 22px, radius 4px, padding `0 8px`, chữ 12px/500, có dot tròn 6px bên trước.
- Nền + chữ theo bảng màu trạng thái ở §2.1.

**Mapping trạng thái nghiệp vụ (dùng đúng màu này):**
| Status | Màu |
|---|---|
| `DANG_HOC` (Đang học) | success |
| `THOI_HOC` (Thôi học) | info |
| `CHUYEN_TRUONG` (Chuyển trường) | warning |
| `TOT_NGHIEP` (Tốt nghiệp) | danger |
| `DA_CHUYEN` (Đã chuyển) | neutral |
| `PENDING` (Chờ duyệt) | warning |
| `APPROVED` (Đã duyệt) | success |
| `REJECTED` (Từ chối) | danger |
| `LOCKED` (Đã khoá) | neutral |

### 3.8 Modal / Dialog

- Overlay `rgba(17,24,39,0.45)`.
- Modal: `bg #FFFFFF`, radius 8px, **width 480px** (form đơn giản) / **720px** (bảng trong modal) / **960px** (form phức tạp, 2 cột).
- Header: tiêu đề `subtitle` 16px + nút `×` 32×32 ghost ở góc phải. Border-bottom.
- Body: padding 24px, `max-height: 70vh`, overflow auto.
- Footer: border-top, padding 16px 24px, cảnh báo hành động phá huỷ ở TRÁI, nút hành động ở PHẢI (canh phải).

### 3.9 Thông báo & trạng thái rỗng

- **Toast** (góc trên phải, dưới topbar 16px): nền trắng, border trái 3px theo màu trạng thái, radius 8px, shadow nhẹ, tự ẩn 4s. Nội dung: icon + tiêu đề 14px/500 + mô tả 13px `#6B7280`.
- **Alert banner** (trong card): nền theo màu trạng thái ở dạng 5-8%, border 1px cùng màu 30%, radius 6px, padding 12-16px, có icon + nút đóng.
- **Empty state**: icon line 40px `#9CA3AF` ở giữa, tiêu đề 16px/600, mô tả 14px `#6B7280`, nút hành động. Khoảng cách dọc 64px.
- **Loading**: skeleton xám `#F3F4F6` có shimmer nhẹ (opacity 0.5–1.0, 1.5s loop). Không dùng spinner tròn to.
- **Pagination**: như §3.4.

---

## 4. Các màn hình cần thiết kế (SCREENS)

> Bố cục đề xuất trong Figma: mỗi màn hình 1 Frame `1440 × 1024` (desktop), cạnh nhau theo hàng, đặt trong Section tên `Screens`. Frame đầu tiên chứa Design System.

### 4.1 Authentication

**M1 — Đăng nhập** (không sidebar, không topbar)
- Căn giữa card 400×480, `bg #FFFFFF`, radius 8px, border, shadow nhẹ.
- Logo + tên hệ thống, tiêu đề "Đăng nhập" 20px/600.
- Field: `Tên đăng nhập`, `Mật khẩu` (có icon mắt toggle).
- Checkbox "Ghi nhớ đăng nhập".
- Nút Primary full-width "Đăng nhập".
- Link phụ: "Quên mật khẩu?" căn phải.
- Thêm 1 frame nhỏ (variant) cho trạng thái lỗi: field sai đổi viền đỏ + alert đỏ "Tên đăng nhập hoặc mật khẩu không đúng. Bạn còn 4 lần thử."

**M2 — Quên mật khẩu**
- Card 400px: input email/username → nút "Gửi mã OTP" → trạng thái "Đã gửi mã 6 số, hết hạn sau 5 phút" (alert success) + field nhập OTP + field mật khẩu mới.

**M3 — Đặt lại mật khẩu (OTP)**
- Field "Mã OTP" (6 chữ số, ô nhập tách ô, rộng 44px mỗi ô, cách nhau 8px) + "Mật khẩu mới" + "Xác nhận mật khẩu" → nút "Đặt lại mật khẩu".

### 4.2 Nhân viên / Giáo vụ (STAFF) — module trọng tâm

**M4 — Danh sách học sinh**
- Page header: "Danh sách học sinh" + caption "Quản lý hồ sơ học sinh của trường".
- Nút phụ `↑ Import Excel`, nút chính `+ Tiếp nhận học sinh`.
- Toolbar card: ô tìm kiếm (icon 🔍 + placeholder "Tìm theo tên, mã học sinh…", w=320px) · Select "Khối lớp" · Select "Lớp" · Select "Trạng thái" · nút "Lọc" ghost · nút "Xoá lọc" ghost · spacer · nút `↓ Xuất Excel`.
- Bảng cột: **STT · Mã HS · Họ tên · Ngày sinh · Giới tính · SĐT · Lớp · Trạng thái · Thao tác**
  - Mã HS dùng font mono, ví dụ `HS20260001`.
  - Giới tính hiển thị `Nam` / `Nữ` (viết tắt chứ không phải `NAM`/`NU`).
  - Trạng thái dùng chip theo §3.7.
  - Thao tác: icon `Sửa` (pencil) + icon `In hồ sơ` (printer) + icon `Xoá` (trash, màu `#DC2626` khi hover).
- Phân trang: "Hiển thị 1–20 trên 137 học sinh".
- Thêm 1 frame variant: **Empty state** "Chưa có học sinh nào" + nút "Tiếp nhận học sinh đầu tiên".

**M5 — Tiếp nhận học sinh mới (modal 720px)**
- Nhóm "Thông tin học sinh": Mã học sinh* (mono, w=full), Họ và tên*, Ngày sinh* (date picker), Giới tính* (select Nam/Nữ/Khác), Số điện thoại*, Email.
- Nhóm "Giấy tờ & liên hệ": Số CCCD, Địa chỉ (full width).
- Nhóm "Người bảo hộ": Họ tên phụ huynh, Điện thoại phụ huynh.
- **Alert info ở đầu form**: "Quy định tuổi tiếp nhận: 15–20 tuổi (theo Quy định hiện hành)." — nêu rõ giá trị động.
- Nút: "Huỷ" (secondary) + "Tiếp nhận" (primary).
- Thêm 1 frame variant: **form lỗi** — hiển thị lỗi tuổi: "Ngày sinh không hợp lệ: học sinh phải từ 15 đến 20 tuổi (theo Quy định hiện hành)." kèm alert đỏ.

**M6 — Chi tiết / Sửa hồ sơ học sinh (trang đầy đủ, không phải modal)**
- Breadcrumb: `Học sinh / HS20260001 / Hồ sơ`.
- Page header: avatar tròn 48px (chữ cái đầu, nền `#EFF6FF`) + "Nguyễn Văn An" `title` + chip trạng thái + caption "Mã: HS20260001 · Lớp: 10A1".
- Nút phụ `🖨 In hồ sơ`, nút chính `Lưu thay đổi`.
- Cột trái (2/3): card "Thông tin cá nhân" (các field như M5 ở chế độ edit) · card "Phụ huynh" · card "Lịch sử trạng thái" (timeline dọc: dot 8px + đường 1px, mỗi mốc có thời gian + mô tả + người thực hiện).
- Cột phải (1/3): card "Đơn vị phân lớp" (lớp hiện tại, khối, niên khóa, GV chủ nhiệm) · card "Hành động" (nút `Chuyển lớp`, nút outline `Đánh dấu thôi học`, nút outline `Xoá hồ sơ` màu đỏ).

**M7 — Quản lý lớp học**
- Toolbar: select "Khối lớp" + ô tìm kiếm + nút `+ Tạo lớp mới`.
- Bảng: **STT · Tên lớp · Khối · Niên khóa · GV chủ nhiệm · Sĩ số · Thao tác**
  - **Cột sĩ số** hiển thị dạng `28 / 40` — phần `40` là giá trị động từ Quy định, KHÔNG hardcode trong UI. Khi `28 / 40` hiển thị thanh progress 4px, màu `#2563EB`; khi ≥90% thì màu `#D97706`; khi đầy thì `#DC2626` + chip "Đầy".
- Nút `↓ Xuất` trong menu thao tác của từng lớp (Excel/PDF).

**M8 — Phân bổ học sinh vào lớp (modal 960px)**
- Header: "Phân bổ học sinh vào lớp 10A1" + caption sĩ số "Sĩ số hiện tại: 28 / 40".
- Trên cùng: 2 cột — trái là **danh sách học sinh chưa phân lớp** (checkbox + tìm kiếm, hiển thị dạng list có avatar nhỏ + mã + tên + lớp hiện tại), phải là **lớp đích** (highlight xanh nhạt `#EFF6FF`).
- Giữa: nút mũi tên `→` để chuyển sang.
- Chân modal: bảng "Đã chọn (3)" dạng chip xóa được (mỗi chip có `×`) + nút Primary "Phân bổ 3 học sinh".
- Thêm 1 frame variant: **lỗi vượt sĩ số** — alert đỏ trong modal: "Không thể phân lớp! Lớp 10A1 hiện có 39 học sinh, thêm 3 học sinh sẽ vượt quá sĩ số tối đa cho phép (40 học sinh)." + hiển thị `current_size` và `max_size` riêng.

**M9 — Chuyển lớp cho học sinh (modal 480px)**
- Field select "Lớp hiện tại" (readonly, hiển thị "10A1 — 28/40"), select "Lớp mới" (chỉ hiện lớp chưa đầy, kèm sĩ số trong ngoặc), textarea "Lý do chuyển lớp"*.
- Preview box nền `#F9FAFB` border `#E5E7EB` radius 6px: "Sau khi chuyển: 10A1 → 27/40 · 10A2 → 39/40".

**M10 — Import học sinh từ Excel/CSV (modal 720px)**
- Vùng dropzone: viền đứt 2px `#D1D5DB`, radius 8px, cao 180px, icon upload 32px, text "Kéo thả file .xlsx / .csv vào đây" + link "hoặc chọn từ máy" màu primary, caption "Tối đa 5MB".
- Sau khi upload: bảng kết quả gồm 2 tab — "Thành công (23)" (tab active, màu primary) và "Thất bại (2)" (tab có badge đỏ `2`).
- Bảng thất bại: **Dòng · Mã HS · Họ tên · Lý do** — lý do chữ đỏ.
- Footer: "Tổng: 25 dòng — Thành công: 23 — Thất bại: 2" (caption) + nút "Tải file mẫu" ghost + nút "Đóng".

### 4.3 Giáo viên (TEACHER)

**M11 — Danh sách lớp phụ trách**
- Card grid 3 cột, gap 16px. Mỗi card: tên lớp `title` 18px + môn học `body` + chip học kỳ + dòng "GV chủ nhiệm: ..." + nút "Nhập điểm" secondary full-width.
- Card có badge khi bảng điểm đã khoá.

**M12 — Nhập điểm lớp (bảng điểm — màn hình phức tạp nhất)**
- Page header: "Bảng điểm Toán — Lớp 10A1" + breadcrumb; chip trạng thái bảng điểm (`MỞ` màu success / `ĐÃ KHOÁ` màu neutral).
- Card chứa bảng điểm với **header 2 tầng**:
  - Tầng 1 (group row): cột gộp — `Điểm 15'` (span 5 cột) · `Điểm 1 tiết` (span 3 cột) · `Điểm thi` (span 1 cột) · `ĐTB` (span 1 cột).
  - Tầng 2: `15p.1 · 15p.2 · 15p.3 · 15p.4 · 15p.5 · 1T.1 · 1T.2 · 1T.3 · Thi · ĐTB`.
  - Cột đầu cố định (sticky): STT · Họ tên (w=220px).
- Ô nhập điểm: width 64px, cao 32px, căn giữa, font mono, `text-align: center`. **Để trống = vắng** (hiển thị placeholder "–" màu `#9CA3AF`, không tính vào ĐTB). Ô nhập có **checkbox "Vắng"** nhỏ 14px cạnh bên để điền nhanh 0.
- Cột ĐTB: chữ mono 14px/600, **màu theo ngưỡng**: `< 5.0` đỏ `#DC2626`, `5.0–< 8.0` cam `#D97706`, `≥ 8.0` xanh `#059669`.
- Footer bảng: nút `+ Thêm cột điểm` ghost · spacer · nút "Tính lại ĐTB" secondary · nút "Lưu bảng điểm" primary.
- Banner cảnh báo khi bảng đã khoá: alert neutral "Bảng điểm đã được chốt. Bạn cần gửi đơn phúc khảo để đề nghị sửa điểm." + nút primary nhỏ "Gửi đơn phúc khảo".

**M13 — Gửi đơn phúc khảo (modal 720px)**
- Bảng 2 cột: **Cột điểm** (readonly, mono) · **Điểm đề nghị** (input) · **Lý do** (input) — mỗi dòng là 1 ô điểm cần sửa.
- Bắt buộc điền lý do cho từng dòng → nếu thiếu thì nút "Gửi đơn" disabled + helper text đỏ.

**M14 — Đơn phúc khảo (danh sách đơn tôi gửi)**
- Bảng: **Mã đơn · Lớp · Môn · Số ô điểm đề nghị sửa · Ngày gửi · Trạng thái · Thao tác**
- Chip trạng thái: `Chờ duyệt` warning · `Đã duyệt` success · `Từ chối` danger.
- Nút "Xem chi tiết" mở modal bảng so sánh: cột `Điểm hiện tại` vs `Điểm đề nghị` (ô đổi màu `#FEF2F2` nếu giảm, `#ECFDF5` nếu tăng) + cột `Lý do`.

### 4.4 Giáo vụ / Admin (ACADEMIC)

**M15 — Phê duyệt đơn phúc khảo**
- Bảng đơn chờ duyệt: **Mã đơn · Giáo viên gửi · Lớp · Môn · Số ô · Ngày gửi · Thao tác**
- Nút "Xem & duyệt" → modal 960px: bảng so sánh điểm + khu vực "Quyết định" gồm radio `Duyệt` / `Từ chối` + textarea "Lý do" (bắt buộc khi chọn Từ chối).

**M16 — Quản lý danh mục môn học**
- Bảng: **Mã môn · Tên môn · Khối · Số tiết · Trạng thái · Thao tác** + nút `+ Thêm môn học`.
- Trạng thái: chip `Đang dùng` success / `Ngừng dùng` neutral.

**M17 — Phân công giảng dạy**
- Bảng: **STT · Giáo viên · Lớp · Môn · Học kỳ · Trạng thái bảng điểm · Thao tác**
- Chip bảng điểm: `Mở` success / `Đã khoá` neutral.
- Nút trong thao tác: "Khoá bảng điểm" / "Mở khoá" (secondary/outline).

**M18 — Quy định hệ thống (System Rules)**
- Card "Quy định về tuổi": 2 input number `Tuổi tối thiểu` = 15, `Tuổi tối đa` = 20.
- Card "Quy định về lớp": input `Sĩ số tối đa mỗi lớp` = 40.
- Card "Quy định về điểm": các input số cột `Điểm 15'` (5), `Điểm 1 tiết` (3), `Số cột điểm thi` (1), `Điểm đạt` (5.0).
- Mỗi card có nút "Lưu" secondary ở góc phải.
- Alert info đầu trang: "Các quy định này có hiệu lực ngay khi lưu và được áp dụng cho toàn hệ thống."

**M19 — Quản lý người dùng**
- Bảng: **Username · Họ tên · Email · Vai trò · Trạng thái · Đăng nhập gần nhất · Thao tác**
- Vai trò dùng chip: `Nhân viên` (info) · `Giáo viên` (neutral) · `Giáo vụ` (primary).
- Trạng thái: `Hoạt động` success · `Đã khoá` danger.
- Thao tác: khoá/mở khoá, đặt lại mật khẩu, đổi vai trò.

**M20 — Nhật ký hệ thống (Audit Log)**
- Bảng: **Thời gian · Người thực hiện · Hành động · Đối tượng · IP · Kết quả**
- Filter: chọn ngày, chọn hành động, ô tìm kiếm.
- Hành động dùng chip màu neutral; kết quả `Thành công` success / `Thất bại` danger.

**M21 — Báo cáo & Thống kê**
- 4 card số liệu (KPI) 1 hàng: Tổng học sinh (137) · Đang học (128) · Sĩ số TB/lớp (34) · Tỉ lệ thôi học (6.6%).
- 2 card biểu đồ: "Sĩ số theo khối" (bar chart, dùng màu primary + neutral cho phần còn lại) · "Phân bố trạng thái học sinh" (donut, 4 màu theo §3.7).
- Card bảng "Tổng hợp theo lớp": Lớp · Sĩ số · Trung bình · ĐTB cao nhất · ĐTB thấp nhất.

### 4.5 Màn hình chung (Shared)

**M22 — Hồ sơ cá nhân**
- Card avatar 96px + tên + username + vai trò; form đổi mật khẩu (3 field: mật khẩu hiện tại, mật khẩu mới, xác nhận).

**M23 — 404 / Không có quyền truy cập**
- 2 frame: 404 (icon file 48px, "Không tìm thấy trang", mô tả, nút "Về trang chủ") và 403 (icon lock, "Bạn không có quyền truy cập", nút "Quay lại").

---

## 5. Yêu cầu về Component & Auto Layout

1. **Tạo Component Library** trước, đặt trong Section tên `Design System`:
   - `Button` (biến thể: Primary / Secondary / Ghost / Danger / Danger-outline × Size: sm/md/lg)
   - `Input` (biến thể: Default / Filled / Error / Disabled) + `Textarea` + `Select` + `Checkbox` + `Radio`
   - `Table` (component gồm header row + 1 body row, dùng Auto Layout dọc)
   - `Badge` / `Chip` (biến thể theo 5 màu trạng thái)
   - `Card` · `Modal` · `Alert` (4 biến thể) · `Toast` · `Empty State` · `Skeleton`
   - `Pagination` · `Avatar` · `Page Header` · `Sidebar Item` (active/inactive) · `Topbar`
2. **Bắt buộc dùng Auto Layout** (không dùng absolute position trừ khi thật sự cần overlay/popover):
   - Mọi dùng cột: `Vertical auto-layout`, gap theo spacing scale, `padding` theo spacing scale.
   - Mọi dùng hàng: `Horizontal auto-layout`, gap 8/12/16px, `align: center`.
   - Bảng: dùng **horizontal auto-layout cho từng hàng**, các cột có `fixed width` + `layoutSizingHorizontal: FIXED` để các hàng luôn thẳng nhau. Header row là instance con của cùng component.
   - Input/Button: `layoutSizingHorizontal: FILL` khi nằm trong form, `HUG` khi nằm trong toolbar.
3. **Dùng Component Properties / Variants** thay vì copy-paste: Button có thể đổi `variant` và `size`; Badge có thể đổi `status`; Alert có thể đổi `type`.
4. **Đặt tên layer rõ ràng**, dùng tiếng Anh hoặc Việt thống nhất (khuyến nghị tiếng Anh cho tên component, tiếng Việt cho nội dung hiển thị).
5. **Tạo hết 1 bộ Component + 1 Section `Styles`** với đủ các style đã nêu ở §2.

---

## 6. Quy trình thực hiện (LÀM THEO THỨ TỰ)

**BƯỚC 1 — Design System**
Tạo Section `Design System`. Tạo đầy đủ: màu (dạng Style/Variable), typography (dạng Text Style), spacing, rồi các Component cơ bản với Auto Layout đúng chuẩn. **Chỉ khi xong bước này mới sang bước 2.**

**BƯỚC 2 — App Shell**
Tạo Section `App Shell`. Frame `Desktop` 1440×1024 với Topbar + Sidebar + vùng content rỗng. Tạo thêm frame `Desktop — Sidebar thu gọn` (64px) và `Mobile` (390×844) để làm mẫu responsive.

**BƯỚC 3 — Screens**
Tạo Section `Screens`. Dựng lần lượt **M1 → M23** theo danh sách §4. Ưu tiên dựng đầy đủ và chuẩn xác các màn hình trọng tâm trước:
> Ưu tiên 1: **M4** (danh sách HS) · **M5** (tiếp nhận) · **M6** (hồ sơ) · **M7** (lớp) · **M8** (phân bổ) · **M12** (bảng điểm) · **M18** (quy định)
> Ưu tiên 2: các màn hình còn lại.

**BƯỚC 4 — States & Variants**
Bổ sung các biến thể trạng thái quan trọng dưới dạng frame riêng đặt cạnh frame chính:
- M4: empty state · loading skeleton
- M5: form lỗi (sai tuổi) · form đang submit
- M8: lỗi vượt sĩ số
- M12: bảng điểm đã khoá
- M14: đơn chờ duyệt / đã duyệt / bị từ chối
- M1: đăng nhập sai

**BƯỚC 5 — Prototype**
Nối prototype luồng chính: Đăng nhập → Danh sách học sinh → Tiếp nhận (modal) → Hồ sơ chi tiết → Quản lý lớp → Phân bổ (modal). Dùng transition `Smart Animate` (200ms) cho mở/đóng modal, `Instant` cho chuyển trang.

---

## 7. Ràng buộc bắt buộc (KHÔNG ĐƯỢC VI PHẠM)

1. **KHÔNG dùng gradient, không drop-shadow đậm, không ảnh, không illustration, không mascot.**
2. **KHÔNG dùng màu nào ngoài bảng màu ở §2.1.** Nếu cần thêm sắc độ, chỉ dùng biến thể sáng/tối của chính màu đó.
3. **KHÔNG hardcode số liệu quy định trong UI.** Các giá trị `15–20 tuổi`, `40 học sinh/lớp`, `5 cột điểm 15'`, `3 cột điểm 1 tiết` là dữ liệu động từ API (`/api/v1/rules`) — trong thiết kế chỉ hiển thị giá trị mẫu, và mọi chỗ hiển thị sĩ số phải có **chỗ dành riêng cho giá trị động** (VD cột sĩ số ghi `28 / 40` với `40` là biến).
4. **Tiếng Việt có dấu đầy đủ** ở toàn bộ nội dung hiển thị. Không viết tắt không cần thiết.
5. **Mọi màn hình dữ liệu phải có trạng thái rỗng** và **trạng thái loading**.
6. **Mọi bảng phải có phân trang** (kể cả bảng ngắn dưới 20 bản ghi thì vẫn hiển thị mẫu phân trang cho nhất quán).
7. **Tiêu đề bảng phải là tiếng Việt** (`Mã học sinh`, `Họ và tên`, `Ngày sinh`, `Số điện thoại`), KHÔNG dùng tên cột kỹ thuật (`student_code`, `date_of_birth`).
8. **Mọi nút hành động phá huỷ dữ liệu (xoá) phải có confirm dialog** với nội dung nêu rõ đối tượng bị ảnh hưởng.
9. **Ô nhập điểm để trống = vắng**, hiển thị "–" — không được hiển thị `0` nhầm.
10. **Đơn vị đo hiển thị rõ ràng**: `Sĩ số: 28/40`, `Điểm: 8.5/10`, `Tiết: 5`.
11. Frame desktop dùng **1440×1024**, mobile dùng **390×844**. Grid 12 cột, gutter 24px, margin 24px.
12. **Không để text bị tràn hoặc cắt chữ** trong bất kỳ frame nào — đặc biệt ở cột tiếng Việt dài và ở bảng điểm nhiều cột.

---

## 8. Output mong muốn

- **Một file Figma** với 4 Section: `Design System` · `App Shell` · `Screens` · `Prototype Flow`.
- Toàn bộ component dùng **Auto Layout** + **Variants** (không phải ảnh chụp).
- Có bảng **Design Tokens** ở Section `Design System` (màu / typography / spacing / components / trạng thái) để dev dùng làm tham chiếu.
- Tất cả màn hình đều dùng **chung 1 bộ component**, không tự vẽ lại.

---

# PHỤ LỤC — Dữ liệu tham chiếu nghiệp vụ (đính kèm khi cần)

## A. Danh sách endpoint chính (dùng để gợi ý dữ liệu hiển thị)

**Nhân viên / Giáo vụ:**
- `GET /api/v1/students` · `GET /api/v1/students/{id}` · `GET /api/v1/students/code/{code}`
- `POST /api/v1/students/admit` · `PUT /api/v1/students/{id}` · `DELETE /api/v1/students/{id}`
- `PATCH /api/v1/students/{id}/status` · `POST /api/v1/students/import-excel` · `GET /api/v1/students/{id}/print`
- `GET /api/v1/classes` · `POST /api/v1/classes` · `GET /api/v1/classes/{id}` · `PUT /api/v1/classes/{id}` · `DELETE /api/v1/classes/{id}`
- `POST /api/v1/classes/{id}/enroll` · `POST /api/v1/classes/transfer` · `GET /api/v1/classes/{id}/export`
- `GET /api/v1/grades` · `GET /api/v1/grades/{id}/classes` · `GET /api/v1/classes/{id}/students`

**Giáo viên:** `GET /api/v1/assignments/my` · `GET /api/v1/scores/assignment/{id}` · `POST /api/v1/scores/batch` · `PUT /api/v1/scores/{id}` · `POST /api/v1/score-submissions` · `GET /api/v1/score-requests/my`

**Giáo vụ:** `GET/PUT /api/v1/rules` · `GET/PUT /api/v1/admin/users` · `GET /api/v1/admin/audit-logs` · `GET/POST/PUT/DELETE /api/v1/subjects` · `GET/POST/PUT/DELETE /api/v1/assignments` · `PATCH /api/v1/assignments/{id}/lock` · `GET /api/v1/reports/*`

**Xác thực:** `POST /api/v1/auth/login` · `POST /api/v1/auth/refresh` · `POST /api/v1/auth/logout` · `POST /api/v1/auth/forgot-password` · `POST /api/v1/auth/reset-password` · `GET /api/v1/auth/me`

## B. Trạng thái học sinh

`DANG_HOC` (Đang học) · `THOI_HOC` (Thôi học) · `CHUYEN_TRUONG` (Chuyển trường) · `TOT_NGHIEP` (Tốt nghiệp)

## C. Vai trò

`STAFF` (Nhân viên) · `TEACHER` (Giáo viên) · `ACADEMIC` (Giáo vụ)

## D. Cấu trúc bảng điểm (9 cột, gồm 3 nhóm)

| Nhóm | Cột | Trọng số |
|---|---|---|
| **Điểm 15'** | `15p.1` `15p.2` `15p.3` `15p.4` `15p.5` | ×1 |
| **Điểm 1 tiết** | `1T.1` `1T.2` `1T.3` | ×2 |
| **Điểm thi** | `Thi` | ×3 |
| — | `ĐTB` (tự tính) | — |

Ô trống = vắng (không tính vào tử số & mẫu số). Ô `0.00` = có điểm 0 (vẫn tính). Khoảng điểm hợp lệ: `0.0 – 10.0`.

## E. Quy định động (hiển thị trong UI, không hardcode)

| Mã | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `MIN_AGE` | 15 | Tuổi tối thiểu tiếp nhận |
| `MAX_AGE` | 20 | Tuổi tối đa tiếp nhận |
| `MAX_CLASS_SIZE` | 40 | Sĩ số tối đa mỗi lớp |
| `MAX_COL_15M` | 5 | Số cột điểm 15' |
| `MAX_COL_45M` | 3 | Số cột điểm 1 tiết |
| `NUM_COL_FINAL` | 1 | Số cột điểm thi |
| `PASSING_SCORE` | 5.0 | Điểm đạt |
| `MAX_LOGIN_ATTEMPTS` | 5 | Số lần sai trước khi khoá |
| `OTP_EXPIRE_MINUTES` | 5 | Thời hạn mã OTP |

## F. Mã lỗi cần biểu diễn trong UI

| Mã | HTTP | Nội dung nên hiển thị |
|---|---|---|
| `CLASS_SIZE_EXCEEDED` | 422 | "Không thể phân lớp! Lớp {X} hiện có {cur} học sinh, thêm {add} học sinh sẽ vượt quá sĩ số tối đa cho phép ({max} học sinh)!" |
| `BUSINESS_RULE_VIOLATION` | 422 | Vi phạm quy chế (VD: tuổi ngoài khoảng cho phép) |
| `DUPLICATE` | 409 | Email / SĐT / CCCD đã thuộc học sinh khác |
| `DUPLICATE_CODE` | 400 | Mã học sinh đã tồn tại |
| `NOT_FOUND` | 404 | Không tìm thấy dữ liệu yêu cầu |
| `FORBIDDEN` | 403 | Bạn không có quyền thực hiện tác vụ này |
| `UNAUTHORIZED` | 401 | Phiên làm việc đã hết hạn hoặc Token không hợp lệ |
| `SCORE_TABLE_LOCKED` | 423 | Bảng điểm đã được chốt. Bạn không thể sửa trực tiếp điểm số! |
| `INVALID_SCORE_RANGE` | 422 | Điểm phải nằm trong khoảng từ 0.0 đến 10.0! |
| `INCOMPLETE_SCORES` | 422 | Còn ô điểm chưa nhập. Vui lòng nhập đủ điểm trước khi gửi duyệt! |

## G. Dữ liệu mẫu (để điền vào frame)

**Học sinh:** `HS20260001` — Nguyễn Văn An — 14/05/2010 — Nam — `0912345678` — `an.nguyen@student.school.edu` — `079001001234` — Lớp 10A1
**Học sinh:** `HS20260002` — Trần Thị Bình — 22/08/2010 — Nữ — `0912345679` — `binh.tran@student.school.edu` — Lớp 10A1
**Lớp:** `10A1` — Khối 10 — 2026-2027 — GV chủ nhiệm: Nguyễn Thu Hà — Sĩ số `28 / 40`
**Môn học:** `TOAN` — Toán Học — Khối 10 — 5 tiết · `VAN` — Ngữ Văn — Khối 10 — 5 tiết · `ANH` — Tiếng Anh — Khối 10 — 4 tiết
**Giáo viên:** `gv01` — Trần Văn Giáo — `giaovu@school.edu` — Giáo viên
**Niên khóa:** `2026-2027` — Học kỳ `1`
