# BÁO CÁO THIẾT KẾ GIAO DIỆN
## Hệ thống Quản lý Học sinh, Lớp học & Sổ điểm

> **Công nghệ giao diện:** HTML5 + CSS thuần (không framework UI, không Bootstrap)
> **Kiến trúc backend:** Flask + SQLAlchemy + MySQL — **thuần REST API** (không server-side template)
> **Phong cách:** Minimalist — phẳng, sạch, nhiều khoảng trắng, ưu tiên đọc dữ liệu
> **Ngôn ngữ hiển thị:** Tiếng Việt (UTF-8, đầy đủ dấu)
> **Ngày lập:** 24/11/2026 · **Nguồn:** đối chiếu trực tiếp với API hiện có trong `studentmanagementapp/studentapp/controllers/`

---

## MỤC LỤC

1. [Nguyên tắc thiết kế](#1-nguyên-tắc-thiết-kế)
2. [Design System (Design Tokens)](#2-design-system-design-tokens)
3. [Cấu trúc App Shell](#3-cấu-trúc-app-shell)
4. [Bộ component dùng chung](#4-bộ-component-dùng-chung)
5. [Màn hình Xác thực](#5-màn-hình-xác-thực)
6. [Màn hình Nhân viên / Giáo vụ (STAFF)](#6-màn-hình-nhân-viên--giáo-vụ-staff)
7. [Màn hình Giáo viên (TEACHER)](#7-màn-hình-giáo-viên-teacher)
8. [Màn hình Giáo vụ / Admin (ACADEMIC)](#8-màn-hình-giáo-vụ--admin-academic)
9. [Màn hình dùng chung](#9-màn-hình-dùng-chung)
10. [Quy ước kỹ thuật HTML/CSS](#10-quy-ước-kỹ-thuật-htmlcss)
11. [Mapping API → Màn hình](#11-mapping-api--màn-hình)
12. [Ma trận phân quyền](#12-ma-trận-phân-quyền)
13. [Bảng lỗi cần biểu diễn trong UI](#13-bảng-lỗi-cần-biểu-diễn-trong-ui)
14. [Checklist bàn giao](#14-checklist-bàn-giao)

---

## 1. NGUYÊN TẮC THIẾT KẾ

### 1.1 Bốn luật bất di bất dịch

| # | Luật | Giải thích thực tế |
|---|---|---|
| 1 | **Phẳng tuyệt đối** | Không gradient, không đổ bóng đậm, không glassmorphism, không hiệu ứng 3D. Tối đa 1 shadow rất nhạt `0 1px 2px rgba(0,0,0,.05)` để tách lớp. |
| 2 | **Đường viền thay đổ bóng** | Mọi khối được phân tách bằng `1px solid #E5E7EB`. Không dùng `box-shadow` làm công cụ phân tách chính. |
| 3 | **Bảng dữ liệu là trung tâm** | Đây là ứng dụng quản lý dữ liệu mật độ cao — mọi màn hình xoay quanh **bảng + form**. Ưu tiên tối giản hoá bảng. |
| 4 | **Màu chỉ mang ý nghĩa** | Màu chỉ dùng cho trạng thái nghiệp vụ & hành động chính. Không trang trí màu. |

### 1.2 Nguyên tắc bổ sung (rút từ chính business logic của backend)

Đây là các ràng buộc **bắt buộc** phát sinh từ code backend, không phải lựa chọn thẩm mỹ:

| Ràng buộc | Nguồn trong backend | Hệ quả bắt buộc cho UI |
|---|---|---|
| Quy định là **động** | `system_rules` (`MAX_AGE`, `MAX_CLASS_SIZE`, `MAX_COL_15M`…) | **Không hardcode** `15–20 tuổi`, `40 học sinh/lớp`. Mọi chỗ hiển thị phải đọc từ `GET /api/v1/rules`. |
| Ô điểm trống ≠ điểm 0 | `models/score.py` — `NULL` = chưa nhập, loại khỏi cả tử & mẫu số | Ô trống hiển thị `–` (màu `#9CA3AF`). Ô `0.00` hiển thị `0.00` và **vẫn tính**. |
| Điểm hợp lệ `[0.0, 10.0]` | `MIN_SCORE`/`MAX_SCORE` | Input validate ngay, viền đỏ khi ngoài khoảng. |
| Nhập `"v"` = vắng | `score_service.ABSENT_ALIASES` | UI có nút/checkbox điền nhanh `0` cho ô vắng. |
| Bảng điểm có 2 trạng thái khoá | `teaching_assignments.is_locked` | Chip `MỞ` / `ĐÃ KHOÁ` ở header bảng điểm. |
| Có đơn `PENDING` → GV khoá ô nhập | `SCORE_SUBMISSION_PENDING` (423) | Disable ô nhập + banner "Đang chờ duyệt". |
| Phúc khảo duyệt **từng ô** | `score_change_details.status` | Bảng so sánh có radio Duyệt/Từ chối **trên từng dòng**, không phải 1 quyết định cho cả đơn. |
| Xoá hồ sơ có 2 chế độ | `delete_student` → `mode: HARD` / `mode: SOFT` | Confirm dialog phải nêu rõ: "xoá vĩnh viễn" hay "chuyển sang Thôi học". |
| Sĩ số lớp có `current_size` + `max_size` | `ClassSizeExceededError` | Hiển thị `28 / 40` với `40` là biến động từ API. |
| Cột điểm gọn theo 3 nhóm | `SCORE_GROUPS` (`15m` / `45m` / `final`) | Header 2 tầng: `Điểm 15'` (5) · `Điểm 1 tiết` (3) · `Điểm thi` (1) · `ĐTB`. |

### 1.3 Nguyên tắc đặt tên

- **Tiêu đề bảng:** tiếng Việt nghiệp vụ (`Mã học sinh`, `Họ và tên`, `Ngày sinh`, `Số điện thoại`) — **không** dùng tên cột kỹ thuật (`student_code`, `date_of_birth`).
- **Nhãn trạng thái:** hiển thị tiếng Việt (`Đang học`, `Chờ duyệt`, `Đã khoá`), giá trị API (`DANG_HOC`, `PENDING`) chỉ dùng nội bộ trong code.
- **Số liệu:** luôn kèm đơn vị — `Sĩ số: 28/40`, `Điểm: 8.5/10`, `Tiết: 5`.

---

## 2. DESIGN SYSTEM (DESIGN TOKENS)

### 2.1 Bảng màu

#### Nền & chữ

| Token | Hex | Dùng cho |
|---|---|---|
| `--bg-page` | `#F9FAFB` | Nền trang ngoài cùng (vùng main content) |
| `--bg-surface` | `#FFFFFF` | Nền card, bảng, sidebar, topbar |
| `--bg-subtle` | `#F3F4F6` | Nền header bảng, ô input readonly, zebra row |
| `--bg-hover` | `#F9FAFB` | Nền khi hover dòng bảng / nút ghost |
| `--border-default` | `#E5E7EB` | Đường viền mặc định |
| `--border-strong` | `#D1D5DB` | Đường viền input, hover |
| `--border-subtle` | `#F3F4F6` | Đường viền nhẹ giữa các dòng bảng |
| `--text-primary` | `#111827` | Tiêu đề, dữ liệu chính |
| `--text-secondary` | `#6B7280` | Nhãn phụ, placeholder, caption |
| `--text-tertiary` | `#9CA3AF` | Icon, chữ rất nhỏ, dấu `–` (vắng) |

#### Màu nhấn (chỉ 1 màu chủ đạo)

| Token | Hex | Dùng cho |
|---|---|---|
| `--primary-600` | `#2563EB` | Nút chính, link, focus ring, active nav, ĐTB đạt |
| `--primary-500` | `#3B82F6` | Progress bar sĩ số |
| `--primary-700` | `#1D4ED8` | Hover nút chính |
| `--primary-50` | `#EFF6FF` | Nền active nav item, badge info, highlight lớp đích |
| `--primary-ring` | `rgba(37,99,235,.12)` | Focus ring 3px quanh input |

#### Màu trạng thái (semantic)

> Chỉ dùng cho **chip / badge / alert**. **Không** dùng làm nền nút.

| Token | Chữ | Nền chip | Dùng cho |
|---|---|---|---|
| `--success` | `#059669` | `#ECFDF5` | Thành công, `ĐANG_HOC`, `Đã duyệt`, `MỞ`, `Đạt` |
| `--warning` | `#D97706` | `#FFFBEB` | Cảnh báo, `CHUYEN_TRUONG`, `Chờ duyệt`, sĩ số ≥ 90% |
| `--danger` | `#DC2626` | `#FEF2F2` | Lỗi, `TOT_NGHIEP`, `Từ chối`, `Xoá`, ĐTB < 5.0 |
| `--info` | `#0891B2` | `#ECFEFF` | Thông tin, `THOI_HOC`, `Đã chuyển` |
| `--neutral` | `#6B7280` | `#F3F4F6` | Mặc định, `ĐÃ KHOÁ`, `Nháp`, `Hủy` |

### 2.2 Mapping trạng thái nghiệp vụ → màu

| API value | Hiển thị | Màu chip |
|---|---|---|
| `DANG_HOC` | Đang học | success |
| `THOI_HOC` | Thôi học | info |
| `CHUYEN_TRUONG` | Chuyển trường | warning |
| `TOT_NGHIEP` | Tốt nghiệp | danger |
| `DA_CHUYEN` | Đã chuyển | neutral |
| `PENDING` | Chờ duyệt | warning |
| `APPROVED` | Đã duyệt | success |
| `REJECTED` | Từ chối | danger |
| `PARTIALLY_APPROVED` | Duyệt một phần | warning |
| `CANCELLED` | Đã huỷ | neutral |
| `LOCKED` / `is_locked = true` | Đã khoá | neutral |
| `is_locked = false` | Mở | success |
| `is_draft = true` | Bản nháp | neutral |

### 2.3 Typography

Font: **Inter** — fallback `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
Font mono: **JetBrains Mono** — fallback `SFMono-Regular, Menlo, monospace`.

| Token | Size / Line-height | Weight | Dùng cho |
|---|---|---|---|
| `--text-display` | 24px / 32px | 600 | Tiêu đề trang |
| `--text-title` | 18px / 24px | 600 | Tiêu đề card, section |
| `--text-subtitle` | 16px / 24px | 600 | Tiêu đề modal |
| `--text-body` | 14px / 20px | 400 | Nội dung, text input |
| `--text-body-medium` | 14px / 20px | 500 | Nhãn table header, nút |
| `--text-caption` | 12px / 16px | 400 | Helper text, meta, badge |
| `--text-mono` | 13px / 20px | 500 | Mã HS, mã lớp, mã môn, **toàn bộ ô điểm** |

> **Bắt buộc:** mọi cột chứa **số** (điểm, ĐTB, sĩ số, STT) phải dùng `font-variant-numeric: tabular-nums` để chữ thẳng hàng tuyệt đối.

### 2.4 Spacing, Shape, Shadow

- **Spacing scale:** `4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 px` — chỉ dùng các giá trị này.
- **Border radius:** `4px` (chip, badge) · `6px` (button, input, card nhỏ) · `8px` (card, modal, dropdown).
- **Shadow:** chỉ 1 cấp — `--shadow-sm: 0 1px 2px rgba(0,0,0,.05)`.
- **Transition:** `150ms ease` cho hover/focus. `200ms ease` cho mở/đóng modal.

---

## 3. CẤU TRÚC APP SHELL

### 3.1 Bố cục tổng thể

```
┌──────────────────────────────────────────────────────────────────────┐
│ TOPBAR  h = 56px · bg #FFFFFF · border-bottom 1px #E5E7EB           │
│ [Logo] [Tên trường]        [Năm học 2026-2027 ▾] [Học kỳ 1 ▾]  🔔  [Avatar ▾] │
├───────────────┬──────────────────────────────────────────────────────┤
│ SIDEBAR       │  MAIN CONTENT · bg #F9FAFB · padding 24px             │
│ w = 240px     │  max-width 1440px · canh giữa                        │
│ bg #FFFFFF    │                                                      │
│ border-right  │  ┌ PageHeader ─────────────────────────────────────┐  │
│ 1px #E5E7EB   │  │ Tiêu đề 24/600              [Nút phụ] [Nút chính]│  │
│               │  │ caption mô tả                                 │  │
│ ─ Nhóm 1 ─    │  └──────────────────────────────────────────────────┘  │
│ ─ Nhóm 2 ─    │  ┌ Card · bg #FFF · border · radius 8px ────────────┐  │
│ ─ Nhóm 3 ─    │  │ [Toolbar: tìm kiếm | filter | actions]           │  │
│               │  │ ┌ Bảng dữ liệu ───────────────────────────────┐  │  │
│ ─ Nhóm 4 ─    │  │ │ ...                                         │  │  │
│               │  │ └──────────────────────────────────────────────┘  │  │
│ ─ Nhóm 5 ─    │  │ [Pagination]                                   │  │  │
│               │  └──────────────────────────────────────────────────┘  │
│ [Thu gọn ◀]   │                                                      │
└───────────────┴──────────────────────────────────────────────────────┘
```

**Quy tắc bố cục:**
- Topbar `position: sticky; top: 0; z-index: 20`.
- Sidebar `position: sticky; top: 56px; height: calc(100vh - 56px); overflow-y: auto`.
- Main content: `max-width: 1440px; margin: 0 auto`.
- Sidebar thu gọn: `64px`, chỉ hiện icon, `title` attribute để hover.
- **Mobile (≤ 768px):** sidebar biến thành drawer trượt, topbar rút gọn, bảng cuộn ngang trong wrapper `overflow-x: auto`.

### 3.2 Điều hướng theo vai trò

Sidebar đổi nội dung theo `role` trong JWT (claim `role`):

**STAFF — Nhân viên / Giáo vụ**

| Nhóm | Mục | Endpoint chính |
|---|---|---|
| Học sinh | Danh sách học sinh | `GET /api/v1/students` |
| | Tra cứu theo mã | `GET /api/v1/students/code/{code}` |
| Lớp học | Quản lý lớp | `GET /api/v1/classes` |
| | Danh sách học sinh trong lớp | `GET /api/v1/classes/{id}/students` |
| Tiện ích | Nhập ký hệ thống | `GET /api/v1/admin/audit-logs` *(read)* |

**TEACHER — Giáo viên**

| Nhóm | Mục | Endpoint chính |
|---|---|---|
| Giảng dạy | Lớp phụ trách | `GET /api/v1/assignments/my` |
| Điểm số | Sổ điểm | `GET /api/v1/scores/assignment/{id}` |
| | Đơn gửi duyệt | `GET /api/v1/score-submissions/my` |
| | Đơn phúc khảo | `GET /api/v1/score-requests/my` |

**ACADEMIC — Giáo vụ / Admin**

| Nhóm | Mục | Endpoint chính |
|---|---|---|
| Đào tạo | Phân công giảng dạy | `GET /api/v1/assignments` |
| | Quản lý lớp | `GET /api/v1/classes` |
| | Danh mục môn học | `GET /api/v1/subjects` |
| Điểm số | Duyệt bảng điểm | `GET /api/v1/score-submissions` |
| | Phê duyệt phúc khảo | `GET /api/v1/score-requests` |
| Báo cáo | Thống kê & xuất file | `GET /api/v1/reports/*` |
| Hệ thống | Quy định | `GET /api/v1/rules` |
| | Người dùng | `GET /api/v1/admin/users` |
| | Nhật ký hệ thống | `GET /api/v1/admin/audit-logs` |

### 3.3 Page Header (dùng lại cho MỌI trang)

```
┌────────────────────────────────────────────────────────────────────┐
│ Học sinh / HS20260001 / Hồ sơ        ← breadcrumb (caption, cấp ≥ 2)│
│ Nguyễn Văn An                        ← display 24/600              │
│ Mã: HS20260001 · Lớp: 10A1           ← caption #6B7280              │
│                              [🖨 In hồ sơ]  [Lưu thay đổi]         │
└────────────────────────────────────────────────────────────────────┘
```

- Tiêu đề + mô tả bên trái, cụm nút bên phải (nút phụ trước, nút chính sau).
- Chỉ có **tối đa 1 nút primary** trong mỗi vùng.
- Breadcrumb chỉ hiện từ cấp 2 trở lên.

---

## 4. BỘ COMPONENT DÙNG CHUNG

### 4.1 Button

| Loại | Nền | Chữ | Border | Dùng khi |
|---|---|---|---|---|
| `primary` | `#2563EB` | `#FFFFFF` | — | Hành động chính (1 nút/vùng) |
| `secondary` | `#FFFFFF` | `#111827` | `1px #D1D5DB` | Hành động phụ |
| `ghost` | transparent | `#6B7280` | — | Icon action, hành động nhẹ, "Xoá lọc" |
| `danger` | `#DC2626` | `#FFFFFF` | — | Xoá, Từ chối |
| `danger-outline` | `#FFFFFF` | `#DC2626` | `1px #FCA5A5` | Xoá trong bảng/dialog |

- **Cao:** 38px (mặc định) · 32px (`sm`, trong bảng) · 44px (`lg`, form mobile).
- **Padding ngang:** 16px (mặc định) · 12px (`sm`).
- **Radius:** 6px · **Chữ:** 14px/500.
- **Trạng thái:** hover đậm 1 bậc · `disabled`: nền `#F3F4F6`, chữ `#9CA3AF`, `cursor: not-allowed` · `loading`: spinner 16px + disable.
- Nút chính có **icon 16px bên trái** khi hành động dễ nhận biết (`+ Tiếp nhận`, `↑ Import`, `↓ Xuất`).

### 4.2 Input / Form

- **Label:** 14px/500 `#111827`, cách input 6px. Dấu `*` màu `#DC2626` cho trường bắt buộc.
- **Input:** cao 38px · `bg #FFFFFF` · `border 1px #D1D5DB` · radius 6px · padding `0 12px` · placeholder `#9CA3AF`.
- **Focus:** `border-color #2563EB` + `box-shadow: 0 0 0 3px rgba(37,99,235,.12)`.
- **Error:** `border-color #DC2626` + helper text 12px `#DC2626` bên dưới.
- **Disabled:** nền `#F3F4F6`, chữ `#9CA3AF`, không focus.
- **Select:** giống input + chevron `▾` bên phải (nền trong suốt, `pointer-events: none`).
- **Textarea:** min-height 88px, `resize: vertical`.
- **Checkbox / Radio:** 16px, bo góc 4px, checked nền `#2563EB` dấu trắng.
- **Bố cục:** 2 cột (label 5 / field 7) desktop, 1 cột mobile. Field đặc biệt (địa chỉ, ghi chú) chiếm cả 2 cột.
- **Nhóm field:** tiêu đề nhóm 14px/600, cách nhóm 24px, divider `1px #F3F4F6` giữa các nhóm.

### 4.3 Table

```
┌────┬─────────────┬──────────────┬────────────┬─────────────┬─────────┐
│ STT│ Mã học sinh │ Họ và tên    │ Ngày sinh  │ Lớp         │ Trạng... │  ← header #F3F4F6, 40px
├────┼─────────────┼──────────────┼────────────┼─────────────┼─────────┤
│ 1  │ HS20260001  │ Nguyễn Văn An│ 14/05/2010 │ 10A1        │ ●Đang học│  ← body 48px
│ 2  │ HS20260002  │ Trần Thị Bình│ 22/08/2010 │ 10A1        │ ●Đang học│  ← zebra #FCFCFD
└────┴─────────────┴──────────────┴────────────┴─────────────┴─────────┘
                                     [Hiển thị 1–20 trên 137 học sinh]  [< 1 2 3 >]
```

- **Header row:** nền `#F3F4F6`, chữ 14px/500 `#6B7280`, cao 40px, border-bottom `#E5E7EB`. Không `text-transform` (giữ nguyên tiếng Việt).
- **Body row:** cao 48px, border-bottom `1px #F3F4F6`. **Zebra rất nhẹ:** lẻ `#FFFFFF`, chẵn `#FCFCFD`.
- **Hover row:** nền `#F9FAFB`.
- **Cột:** STT (48px, giữa) · Mã (mono) · Họ tên (500) · Thông tin · Trạng thái (chip, 120px) · Thao tác (icon button, 100px, phải).
- **Row action:** nút icon 32×32, radius 6px, hover nền `#F3F4F6`, icon `#6B7280`; nút xoá đổi `#DC2626` khi hover.
- **Phân trang:** dưới bảng, căn phải. Text caption "Hiển thị 1–20 trên 137 học sinh" + nút `‹` `›` + số trang dạng chip (trang hiện tại nền `#EFF6FF`, chữ `#2563EB`).

### 4.4 Chip / Badge trạng thái

- Cao 22px · radius 4px · padding `0 8px` · chữ 12px/500 · **dot tròn 6px** bên trước.
- Nền + chữ theo bảng màu trạng thái §2.1.
- Đặc biệt: chip **vai trò** của user (Nhân viên / Giáo viên / Giáo vụ) dùng bảng màu `info` / `neutral` / `primary`.

### 4.5 Card

- `bg #FFFFFF` · `border 1px #E5E7EB` · radius 8px · padding 20–24px.
- **Header card:** tiêu đề 18px/600 + nút phụ bên phải, border-bottom, padding-bottom 16px, margin-bottom 16px.
- Không đổ bóng nặng.

### 4.6 Modal / Dialog

- **Overlay:** `rgba(17,24,39,.45)`.
- **Width:** 480px (form đơn giản) · 720px (bảng trong modal) · 960px (form phức tạp 2 cột / so sánh điểm).
- **Header:** tiêu đề 16px/600 + nút `×` 32×32 ghost góc phải · border-bottom.
- **Body:** padding 24px · `max-height: 70vh` · overflow auto.
- **Footer:** border-top · padding 16px 24px · cảnh báo hủy ở **TRÁI**, nút hành động **PHẢI** (canh phải).

### 4.7 Thông báo & trạng thái

| Thành phần | Quy cách |
|---|---|
| **Toast** | Góc trên phải (dưới topbar 16px). Nền trắng, **border trái 3px** theo màu trạng thái, radius 8px, shadow nhẹ, tự ẩn 4s. Icon + tiêu đề 14px/500 + mô tả 13px `#6B7280`. |
| **Alert banner** | Trong card: nền màu trạng thái ở dạng 5–8%, border 1px cùng màu 30%, radius 6px, padding 12–16px, có icon + nút đóng. |
| **Empty state** | Icon line 40px `#9CA3AF` giữa · tiêu đề 16px/600 · mô tả 14px `#6B7280` · nút hành động. Khoảng cách dọc 64px. |
| **Loading** | Skeleton xám `#F3F4F6` có shimmer nhẹ (opacity .5→1.0, 1.5s loop). Không dùng spinner to. |
| **Confirm dialog** | Bắt buộc cho mọi hành động phá huỷ dữ liệu — nội dung phải nêu rõ đối tượng bị ảnh hưởng. |

### 4.8 Các component khác

- **Avatar:** tròn, chữ cái đầu của họ tên, nền `#EFF6FF`, chữ `#2563EB`. Size 32 (bảng) / 40 (header) / 48 (hồ sơ) / 96 (trang cá nhân).
- **Progress (sĩ số):** thanh 4px, bo tròn. Xanh `#2563EB` < 90% · cam `#D97706` ≥ 90% · đỏ `#DC2626` khi đầy.
- **Timeline (lịch sử trạng thái):** dot 8px + đường nối 1px dọc. Mỗi mốc: thời gian + mô tả + người thực hiện.
- **Tabs (hồ sơ học sinh):** dưới tiêu đề, active có border-bottom 2px `#2563EB`.
- **Dropzone:** viền đứt `2px #D1D5DB`, radius 8px, cao 180px, icon upload 32px.
- **Breadcrumb:** caption `#6B7280`, phân tách bằng `/`, mục cuối đậm `#111827`.

---

## 5. MÀN HÌNH XÁC THỰC

> Không sidebar, không topbar. Nền trang `--bg-page`.

### M1 — Đăng nhập

- Card 400px, `bg #FFFFFF`, radius 8px, border, shadow nhẹ, canh giữa theo chiều dọc.
- Logo (hình vuông 40px, nền `#EFF6FF`, chữ `#2563EB`) + tên hệ thống.
- Tiêu đề "Đăng nhập" 20px/600.
- Field: `Tên đăng nhập`*, `Mật khẩu`* (có icon mắt toggle, `aria-label="Hiện mật khẩu"`).
- Checkbox "Ghi nhớ đăng nhập".
- Nút primary full-width "Đăng nhập" — gọi `POST /api/v1/auth/login`.
- Link phụ "Quên mật khẩu?" căn phải → M2.
- **Trạng thái lỗi:** field sai đổi viền đỏ + alert đỏ phía trên form: *"Tên đăng nhập hoặc mật khẩu không đúng. Bạn còn 4 lần thử."* — số lần còn lại đọc từ `MAX_LOGIN_ATTEMPTS`.
- **Trạng thái khoá tài khoản** (`ACCOUNT_LOCKED`, 403): alert **cảnh báo** (vàng, icon ổ khoá) *"Tài khoản đã bị tạm khóa do nhập sai quá 5 lần liên tiếp. Tự động mở khoá sau 25 phút nữa."* + link phụ **"Đặt lại mật khẩu ngay"** → mở thẳng M2 (không cần admin khác can thiệp). Số phút còn lại lấy từ `lock_duration_minutes` trong response.
- **Trạng thái `must_change_password = true`:** sau khi đăng nhập thành công → chuyển thẳng sang **M23b** (đổi mật khẩu bắt buộc) thay vì vào dashboard.

### M2 — Quên mật khẩu (bước 1: nhập email)

> Trang độc lập `pages/login.html` (view `view-forgot`), cùng card auth như M1.

- Card 400px, tiêu đề "Quên mật khẩu", subtitle: *"Nhập email hoặc tên đăng nhập để nhận mã OTP đặt lại mật khẩu."*
- Field "Email hoặc tên đăng nhập"\* → nút primary full-width "Gửi mã OTP" → `POST /api/v1/auth/forgot-password`.
- Thành công → alert success *"Đã gửi mã OTP"* + sau 1.2s **chuyển hẳn sang trang M2b** (`/pages/reset-otp.html?email=...`).
- Link phụ "← Quay lại đăng nhập".

> Lưu ý API: `/forgot-password` luôn trả 200 kể cả khi không tìm thấy tài khoản → **không** hiển thị thông báo khác biệt, luôn hiện thông báo trung tính.

### M2b — Xác thực mã OTP (bước 2)

> Trang độc lập `pages/reset-otp.html` — **tách riêng** khỏi bước đặt mật khẩu.

- Card 400px, tiêu đề "Xác thực mã OTP", subtitle: *"Nhập mã 6 số đã gửi tới email của bạn để tiếp tục đặt lại mật khẩu."*
- Field "Email hoặc tên đăng nhập"\* (pre-fill từ query param `?email=`).
- **Ô OTP tách ô:** 6 ô, mỗi ô rộng 44px, cao 44px, cách nhau 8px, font mono 18px, canh giữa. Tự nhảy focus ô kế tiếp, hỗ trợ paste 6 số vào ô đầu, hỗ trợ phím mũi tên.
- Helper: *"Mã hết hạn sau 5 phút và chỉ dùng được 1 lần."*
- Nút primary full-width "Xác thực mã OTP" → `POST /api/v1/auth/verify-reset-otp` → nhận `reset_token` → **chuyển sang trang M3**.
- Nút ghost "Gửi lại mã" → `POST /api/v1/auth/forgot-password` (gửi lại OTP mới).
- Link phụ "← Quay lại đăng nhập".
- **Trạng thái lỗi:** alert đỏ phía trên form — *"Mã OTP không đúng. Bạn còn 4 lần thử!"* / *"Mã OTP đã hết hạn..."*; xoá 6 ô sau khi sai.

### M3 — Đặt lại mật khẩu mới (bước 3)

> Trang độc lập `pages/reset-password.html` — **tách riêng** khỏi bước nhập OTP.
> Yêu cầu `reset_token` trong `sessionStorage`; không có → tự quay lại M2b.

- Card 400px, tiêu đề "Đặt lại mật khẩu", subtitle: *"Mã OTP đã được xác thực. Vui lòng đặt mật khẩu mới cho tài khoản của bạn."*
- Box thông tin tài khoản (nền `--bg-subtle`): avatar tròn 40px (chữ cái đầu) · username · email.
- Field: **Mật khẩu mới**\* (icon mắt toggle) · **Xác nhận mật khẩu**\* (icon mắt toggle).
- **Thanh độ mạnh mật khẩu** (4px, 4 mức yếu/trung bình/khá/mạnh) + danh sách 5 điều kiện có tick: ≥8 ký tự · chữ thường · chữ HOA · chữ số · ký tự đặc biệt.
- Nút primary full-width "Đặt lại mật khẩu" → `POST /api/v1/auth/reset-password` (header `Bearer <reset_token>`).
- Link phụ "← Quay lại nhập mã OTP".
- **Thành công:** toast success → tự quay lại M1 sau 900ms để đăng nhập bằng mật khẩu mới.
- **Lỗi phiên hết hạn:** tự quay lại M2b kèm cảnh báo yêu cầu mã OTP mới.

**Sơ đồ luồng 3 trang:**

```
M1 (login) ──"Quên mật khẩu?"──► M2 (login.html #view-forgot)
                                      │ POST /forgot-password
                                      ▼
                              M2b (reset-otp.html) ──OTP sai──► alert đỏ
                                      │ POST /verify-reset-otp → reset_token
                                      ▼
                              M3 (reset-password.html)
                                      │ POST /reset-password (Bearer reset_token)
                                      ▼
                              M1 (login) — đăng nhập lại
```

---

## 6. MÀN HÌNH NHÂN VIÊN / GIÁO VỤ (STAFF)

### M4 — Danh sách học sinh ★ (màn hình trọng tâm)

**Page header**
- Breadcrumb: `Học sinh` · Tiêu đề "Danh sách học sinh" (display) · caption "Quản lý hồ sơ học sinh của trường".
- Nút phụ `↑ Import Excel` · nút chính `+ Tiếp nhận học sinh`.

**Toolbar card** (1 hàng, gap 12px, wrap)
| Ô | Query param | Ghi chú |
|---|---|---|
| Ô tìm kiếm (w 320px) | `q` | placeholder "Tìm theo tên, mã học sinh…" |
| Select "Khối lớp" | `grade_id` | từ `GET /api/v1/grades` |
| Select "Lớp" | `class_id` | từ `GET /api/v1/classes` |
| Select "Trạng thái" | `status` | 4 giá trị học sinh |
| Select "Năm học" | `academic_year_id` | từ `GET /api/v1/academic-years` |
| Nút ghost "Xoá lọc" | — | reset toàn bộ filter |
| spacer | | |
| Nút ghost `↓ Xuất Excel` | — | |

**Bảng** — `GET /api/v1/students?page&limit&q&class_id&status&academic_year_id`

| STT | Mã học sinh | Họ và tên | Ngày sinh | Giới tính | Số điện thoại | Lớp | Trạng thái | Thao tác |
|---|---|---|---|---|---|---|---|---|
| 48px | mono 130px | 180px | 110px | 80px | 120px | 80px | chip 120px | 100px |

- Mã HS dùng font mono (`HS20260001`).
- Giới tính hiển thị `Nam` / `Nữ` / `Khác` (viết tắt chứ không phải `NAM`/`NU`).
- Trạng thái: chip theo §2.2.
- Thao tác: icon `Sửa` (bút chì) · icon `In hồ sơ` (máy in) · icon `Xoá` (thùng, đỏ khi hover).
- **Phân trang:** "Hiển thị 1–20 trên 137 học sinh" (dùng `total` / `page` / `pages` / `per_page` từ API).

**Empty state:** icon nhóm người 40px · "Chưa có học sinh nào" · mô tả "Hồ sơ học sinh sẽ hiển thị tại đây." · nút chính "Tiếp nhận học sinh đầu tiên".
**Loading:** 8 dòng skeleton trong bảng.

### M5 — Tiếp nhận học sinh mới (modal 720px)

`POST /api/v1/students/admit` → 201 / 400 / 409 / 422

**Alert info ở đầu form** — nội dung động:
> "Quy định tuổi tiếp nhận: **{min_age}–{max_age} tuổi** (theo Quy định hiện hành)."
— `min_age`/`max_age` đọc từ `GET /api/v1/rules` (`MIN_AGE`/`MAX_AGE`), **không hardcode**.

**Nhóm 1 — Thông tin học sinh**
| Field | Tên hiển thị | Bắt buộc | Ghi chú |
|---|---|---|---|
| `student_code` | Mã học sinh | ✓ | mono, full width |
| `full_name` | Họ và tên | ✓ | |
| `date_of_birth` | Ngày sinh | ✓ | date picker, `YYYY-MM-DD` |
| `gender` | Giới tính | ✓ | select Nam / Nữ / Khác |
| `phone` | Số điện thoại | ✓ | max 15 ký tự |
| `email` | Email | | validate định dạng |

**Nhóm 2 — Giấy tờ & liên hệ**
`citizen_id` (Số CCCD) · `address` (Địa chỉ, full width).

**Nhóm 3 — Người bảo hộ**
`parent_name` (Họ tên phụ huynh) · `parent_phone` (Số điện thoại phụ huynh).

**Footer:** nút "Huỷ" (secondary) · nút "Tiếp nhận" (primary).

**Trạng thái lỗi** (map từ API):
| Lỗi API | Hiển thị trong UI |
|---|---|
| `BUSINESS_RULE_VIOLATION` (422) kèm `current_rules` | Alert đỏ đầu form: *"Tuổi của học sinh là 14 tuổi. Không hợp lệ với quy định tiếp nhận (Từ 15 đến 20 tuổi)!"* + đánh dấu đỏ field Ngày sinh |
| `DUPLICATE_CODE` (400) | Lỗi dưới field Mã học sinh: *"Mã học sinh 'HS20260001' đã tồn tại trong hệ thống."* |
| `DUPLICATE` (409) | Lỗi dưới field tương ứng (Email/SĐT/CCCD): *"Email đã thuộc học sinh khác."* |
| `INVALID_EMAIL` | Lỗi dưới field Email |
| `MISSING_FIELDS` | Highlight các field thiếu + helper đỏ |

### M6 — Chi tiết / Sửa hồ sơ học sinh (trang đầy đủ)

`GET /api/v1/students/{id}` · `PUT /api/v1/students/{id}`

**Page header:** avatar tròn 48px (chữ cái đầu, nền `#EFF6FF`) + tên `title` 18px + chip trạng thái + caption "Mã: HS20260001 · Lớp: 10A1 · Tuổi: 16".
Nút phụ `🖨 In hồ sơ` (`GET /students/{id}/print?format=pdf`) · nút chính "Lưu thay đổi".

**Bố cục 2 cột (2/3 – 1/3):**

**Cột trái**
| Card | Nội dung |
|---|---|
| Thông tin cá nhân | Các field như M5 ở chế độ edit, 2 cột |
| Phụ huynh | Họ tên + SĐT phụ huynh |
| Lịch sử trạng thái | Timeline dọc: dot 8px + đường 1px; mỗi mốc có thời gian + mô tả + người thực hiện |

**Cột phải**
| Card | Nội dung |
|---|---|
| Đơn vị phân lớp | Lớp hiện tại, khối, niên khóa, GV chủ nhiệm |
| Hành động | Nút `Chuyển lớp` (primary) · nút outline `Đánh dấu thôi học` · nút outline `Xoá hồ sơ` (viền đỏ, chữ đỏ) |

**Tabs** (tùy chọn, phía dưới header): `Thông tin cá nhân` · `Điểm số` (`GET /scores/student/{id}`) · `Lịch sử thay đổi`.

### M7 — Quản lý lớp học

`GET /api/v1/classes?page&limit&grade_id&academic_year_id`

**Toolbar:** select "Khối lớp" · select "Năm học" · ô tìm kiếm · nút chính `+ Tạo lớp mới`.

**Bảng:** STT · Tên lớp · Khối · Niên khóa · GV chủ nhiệm · **Sĩ số** · Thao tác

**Cột sĩ số — đặc biệt quan trọng:**
```
28 / 40   ▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░
```
- `28` = `current_size`, `40` = `max_size` đọc từ `MAX_CLASS_SIZE` — **biến động, không hardcode**.
- Progress 4px: xanh `#2563EB` < 90% · cam `#D97706` ≥ 90% · đỏ `#DC2626` khi đầy + chip "Đầy".

**Thao tác:** icon `Sửa` · icon `Xuất Excel` · icon `Xuất PDF` (`GET /classes/{id}/export`) · icon `Xoá`.

**Modal tạo/sửa lớp:** field `Tên lớp`*, `Khối lớp`*, `Niên khóa`*, `GV chủ nhiệm`, và hiển thị read-only "Sĩ số tối đa cho phép: 40" (đọc từ rules).

### M8 — Phân bổ học sinh vào lớp (modal 960px)

`POST /api/v1/classes/{id}/enroll` với `{ student_ids: [...], academic_year_id: N }`

- **Header:** "Phân bổ học sinh vào lớp 10A1" + caption "Sĩ số hiện tại: 28 / 40".
- **Thân modal — 2 cột:**
  - **Trái:** danh sách học sinh chưa phân lớp — ô tìm kiếm + checkbox; hiển thị dạng **list** (avatar 32px + mã mono + tên + lớp hiện tại), cuộn độc lập `max-height: 320px`.
  - **Phải:** lớp đích — nền highlight `#EFF6FF`, border `#2563EB`, danh sách học sinh đã chọn dạng chip xoá được (mỗi chip có `×`).
  - **Giữa:** nút mũi tên `→` để chuyển sang.
- **Footer:** caption "Đã chọn (3) học sinh" + nút primary "Phân bổ 3 học sinh" (số 3 là động).

**Trạng thái lỗi vượt sĩ số** (`CLASS_SIZE_EXCEEDED`, 422 — API trả kèm `current_size` & `max_size`):
> Alert đỏ trong modal: *"Không thể phân lớp! Lớp 10A1 hiện có 39 học sinh, thêm 3 học sinh sẽ vượt quá sĩ số tối đa cho phép (40 học sinh)!"*
> Hiển thị riêng 2 ô: `Sĩ số hiện tại: 39` và `Sĩ số tối đa: 40`.

### M9 — Chuyển lớp cho học sinh (modal 480px)

`POST /api/v1/classes/transfer`

- Select "Lớp hiện tại" (readonly, hiển thị "10A1 — 28/40").
- Select "Lớp mới" — chỉ hiện lớp **chưa đầy**, kèm sĩ số trong ngoặc: `10A2 (39/40)`.
- Textarea "Lý do chuyển lớp"* (bắt buộc).
- **Preview box** nền `#F9FAFB`, border `#E5E7EB`, radius 6px, padding 12px:
  > "Sau khi chuyển: 10A1 → 27/40 · 10A2 → 39/40"
- Footer: "Huỷ" · nút primary "Chuyển lớp".

### M10 — Import học sinh từ Excel/CSV (modal 720px)

`POST /api/v1/students/import-excel` (multipart) → **partial success**

- **Vùng dropzone:** viền đứt `2px #D1D5DB`, radius 8px, cao 180px, icon upload 32px, text "Kéo thả file .xlsx / .csv vào đây" + link "hoặc chọn từ máy" màu primary + caption "Tối đa 5MB".
- Chỉ nhận `.xlsx, .xls, .xlsm, .csv` (khớp `INVALID_FILE_TYPE` của API).
- **Sau khi upload — 2 tab:**
  - Tab "Thành công (23)" — active, màu primary.
  - Tab "Thất bại (2)" — badge đỏ `2`.
- **Bảng thất bại:** Dòng · Mã HS · Họ tên · Lý do — cột "Lý do" chữ đỏ. (API trả `errors[]` với `{row, student_name, reason}`)
- **Footer:** caption "Tổng: 25 dòng — Thành công: 23 — Thất bại: 2" + nút ghost "Tải file mẫu" + nút "Đóng".

---

## 7. MÀN HÌNH GIÁO VIÊN (TEACHER)

### M11 — Danh sách lớp phụ trách

`GET /api/v1/assignments/my` → mỗi item có `class_name`, `subject_name`, `semester_name`, `academic_year_name`, `is_locked`, `has_pending_submission`.

- Grid 3 cột, gap 16px.
- Mỗi card: tên lớp `title` 18px · môn học `body` · chip học kỳ · dòng "GV chủ nhiệm: …" · nút "Nhập điểm" secondary full-width.
- **Badge trạng thái trên card:**
  - `ĐÃ KHOÁ` (neutral) → bảng điểm đã chốt, nút đổi thành "Xem bảng điểm" + "Gửi đơn phúc khảo".
  - `ĐANG CHỜ DUYỆT` (warning) khi `has_pending_submission = true` → nút "Nhập điểm" disabled.

### M12 — Nhập điểm lớp (bảng điểm) ★ (màn hình phức tạp nhất)

`GET /api/v1/scores/assignment/{id}` · `GET /api/v1/scores/columns/config` · `POST /api/v1/scores/batch`

**Page header:** breadcrumb `Lớp phụ trách / Toán Học — 10A1` · tiêu đề "Bảng điểm Toán — Lớp 10A1" · chip trạng thái bảng điểm (`MỞ` success / `ĐÃ KHOÁ` neutral) · nút chính "Lưu bảng điểm".

**Card bảng điểm — header 2 tầng:**

```
┌──────┬───────────────┬──────────────────────────┬────────────┬──────────┐
│      │               │      Điểm 15'            │ Điểm thi   │          │
│ STT  │   Họ và tên   ├────┬────┬────┬────┬──────┼────────────┤   ĐTB    │
│      │               │15p1│15p2│15p3│15p4│ 15p5 │   Thi      │          │
│      │               ├────┼────┼────┼────┼──────┼────────────┤          │
│      │               │1T.1│1T.2│1T.3                    │          │
├──────┼───────────────┼────┼────┼────┼────┼──────┼────────────┼──────────┤
│  1   │ Nguyễn Văn An│ 8.0│ 7.5│ 9.0│ 8.5│ 8.0  │   8.0      │  8.23    │
│  2   │ Trần Thị Bình│  —  │  —  │ 9.5│ 8.0│ 7.5  │   8.0      │  8.28    │
└──────┴───────────────┴────┴────┴────┴────┴──────┴────────────┴──────────┘
```

- **Cột đầu cố định (sticky):** STT · Họ và tên (w 220px).
- **Ô nhập điểm:** w 64px · h 32px · căn giữa · font mono 13px · `text-align: center`.
  - Để trống = **vắng** → hiển thị placeholder `–` màu `#9CA3AF`, **không tính vào ĐTB**.
  - Ô `0.00` = có điểm 0 → **vẫn tính** vào ĐTB.
  - Validate ngay: ngoài `[0.0, 10.0]` → viền đỏ + helper "Điểm phải nằm trong khoảng 0.0 – 10.0".
- **Nút "Vắng"** nhỏ 14px cạnh ô để điền nhanh `0` (API chấp nhận nhập `"v"`).
- **Cột ĐTB:** font mono 14px/600, màu theo ngưỡng:
  - `< 5.0` → đỏ `#DC2626`
  - `5.0 – < 8.0` → cam `#D97706`
  - `≥ 8.0` → xanh `#059669`
  - `null` → `–` màu `#9CA3AF`
- **Footer bảng:** nút ghost `+ Thêm cột điểm` · spacer · nút secondary "Tính lại ĐTB" · nút primary "Lưu bảng điểm".

**Trạng thái bảng điểm:**

| Điều kiện | Hiển thị |
|---|---|
| `is_locked = false` | Ô nhập **mở**. Nút "Gửi duyệt" bật. |
| `is_locked = true` | Ô nhập **disable** (nền `#F3F4F6`). Alert neutral: *"Bảng điểm đã được chốt. Bạn cần gửi đơn phúc khảo để đề nghị sửa điểm."* + nút primary nhỏ "Gửi đơn phúc khảo". |
| `has_pending_submission = true` | Ô nhập **disable**. Alert warning: *"Bảng điểm đang được gửi duyệt. Vui lòng hủy đơn gửi duyệt trước khi sửa điểm!"* (mã `SCORE_SUBMISSION_PENDING`, 423) + nút "Huỷ đơn gửi duyệt". |
| Ô chưa nhập đủ | Nút "Gửi duyệt" **disabled** + helper đỏ: *"Còn ô điểm chưa được nhập. Vui lòng nhập đủ điểm trước khi gửi duyệt!"* (`INCOMPLETE_SCORES`, 422). |

**Tooltip khi hover cột điểm:** hiển thị trọng số — `Điểm 15' ×1` · `Điểm 1 tiết ×2` · `Điểm thi ×3`.

### M13 — Gửi đơn phúc khảo (modal 720px)

`POST /api/v1/score-requests` — chỉ tạo được khi `is_locked = true`.

- Bảng 3 cột: **Điểm hiện tại** (readonly, mono) · **Điểm đề nghị** (input) · **Lý do** (input).
- Mỗi dòng = 1 ô điểm cần sửa.
- **Bắt buộc nhập lý do cho từng dòng** → thiếu bất kỳ dòng nào thì nút "Gửi đơn" **disabled** + helper đỏ "Vui lòng nhập lý do cho tất cả các ô điểm."
- Validate điểm đề nghị trong `[0.0, 10.0]`.
- Footer: "Huỷ" · nút primary "Gửi đơn".

### M14 — Đơn phúc khảo của tôi

`GET /api/v1/score-requests/my` → mỗi đơn có `status`, `total_changes`, `is_batch`, `details[]`.

**Bảng:** Mã đơn · Lớp · Môn · Số ô điểm đề nghị sửa · Ngày gửi · Trạng thái · Thao tác

- Chip trạng thái: `Chờ duyệt` warning · `Đã duyệt` success · `Từ chối` danger · `Duyệt một phần` warning.
- Nút "Xem chi tiết" mở modal bảng so sánh:

| Học sinh | Cột điểm | Điểm hiện tại | Điểm đề nghị | Lý do | Trạng thái |
|---|---|---|---|---|---|
| Nguyễn Văn An | 15p.3 | 7.0 | 8.0 | Chấm nhầm | ● Chờ duyệt |

- Ô điểm tăng → nền `#ECFDF5`; giảm → nền `#FEF2F2`; không đổi → nền trắng.

---

## 8. MÀN HÌNH GIÁO VỤ / ADMIN (ACADEMIC)

### M15 — Duyệt bảng điểm (đơn gửi duyệt)

`GET /api/v1/score-submissions?status=PENDING` · `PUT /score-submissions/{id}/approve` · `/reject`

**Bảng:** Mã đơn · Giáo viên gửi · Lớp · Môn · Số học sinh · Ngày gửi · Thao tác
- Chỉ hiện mặc định `status=PENDING` (đơn chờ duyệt).
- Chip trạng thái nếu bật filter tất cả.

**Modal 960px "Xem & duyệt":**
- Bảng điểm tạm (chỉ đọc) kèm ĐTB.
- Khu vực "Quyết định": textarea "Lý do" (bắt buộc khi **Từ chối**) + 2 nút `Duyệt & chốt` (primary) · `Từ chối` (danger).
- Sau khi duyệt → bảng điểm chốt (`is_locked = true`), GV không sửa trực tiếp được.

### M16 — Phê duyệt đơn phúc khảo ★

`GET /api/v1/score-requests` · `GET /score-requests/{id}/diff` · `PUT /score-requests/{id}/approve|reject`

**Bảng đơn chờ duyệt:** Mã đơn · Giáo viên gửi · Lớp · Môn · Số ô · Ngày gửi · Thao tác

**Modal 960px — bảng so sánh điểm, duyệt TỪNG Ô:**

| ☐ | Học sinh | Cột điểm | Điểm hiện tại | Điểm đề nghị | Lý do | Quyết định |
|---|---|---|---|---|---|---|
| ☑ | Nguyễn Văn An | 15p.3 | 7.0 | 8.0 | Chấm nhầm | ○ Duyệt  ○ Từ chối |
| ☑ | Trần Thị Bình | 1T.2 | 8.0 | 7.5 | Nhầm đề | ○ Duyệt  ○ Từ chối |

- Mỗi dòng có **radio Duyệt / Từ chối** độc lập (backend duyệt từng ô qua `details[].status`).
- Nếu chọn "Từ chối" → hiện ô nhập "Lý do từ chối" bắt buộc **trên dòng đó**.
- Footer: nút ghost "Duyệt tất cả" (chọn hàng loạt) · nút secondary "Từ chối tất cả" · nút primary "Gửi quyết định".
- Lỗi `DECISIONS_REQUIRED` (422): *"Đơn sửa điểm có nhiều ô, vui lòng gửi quyết định duyệt/từ chối cho từng ô!"*

### M17 — Quản lý danh mục môn học

`GET/POST/PUT/DELETE /api/v1/subjects`

**Bảng:** Mã môn (mono) · Tên môn · Khối · Số tiết · Trạng thái · Thao tác · nút chính `+ Thêm môn học`
- Chip: `Đang dùng` success / `Ngừng dùng` neutral.

**Modal thêm/sửa:** `subject_code`*, `subject_name`*, `grade_id`*, `periods_count`, `is_active`.

### M18 — Phân công giảng dạy

`GET/POST/PUT/DELETE /api/v1/assignments` · `PATCH /assignments/{id}/lock`

**Bảng:** STT · Giáo viên · Lớp · Môn · Học kỳ · Trạng thái bảng điểm · Thao tác
- Chip bảng điểm: `Mở` success / `Đã khoá` neutral.
- Thao tác: nút secondary/outline "Khoá bảng điểm" / "Mở khoá".
- Confirm dialog khi khoá: *"Khoá bảng điểm Toán — Lớp 10A1? Sau khi khoá, giáo viên không thể sửa điểm và phải gửi đơn phúc khảo."*

**Modal phân công:** `teacher_id`* · `class_id`* · `subject_id`* · `semester_id`*.

### M19 — Quy định hệ thống

`GET /api/v1/rules` · `PUT /api/v1/rules/{key}` · `PUT /api/v1/rules/bulk`

**Alert info đầu trang:** *"Các quy định này có hiệu lực ngay khi lưu và được áp dụng cho toàn hệ thống."*

**Card "Quy định về tuổi"**
| Trường | Rule key | Kiểu | Mặc định |
|---|---|---|---|
| Tuổi tối thiểu | `MIN_AGE` | INT | 15 |
| Tuổi tối đa | `MAX_AGE` | INT | 20 |

**Card "Quy định về lớp"**
| Trường | Rule key | Kiểu | Mặc định |
|---|---|---|---|
| Sĩ số tối đa mỗi lớp | `MAX_CLASS_SIZE` | INT | 40 |

**Card "Quy định về điểm"**
| Trường | Rule key | Kiểu | Mặc định |
|---|---|---|---|
| Số cột điểm 15' tối thiểu | `MIN_COL_15M` | INT | 1 |
| Số cột điểm 15' tối đa | `MAX_COL_15M` | INT | 5 |
| Số cột điểm 1 tiết tối thiểu | `MIN_COL_45M` | INT | 1 |
| Số cột điểm 1 tiết tối đa | `MAX_COL_45M` | INT | 3 |
| Số cột điểm thi | `NUM_COL_FINAL` | INT | 1 |
| Điểm đạt | `PASSING_SCORE` | FLOAT | 5.0 |

**Card "Bảo mật & xác thực"**
| Trường | Rule key | Kiểu | Mặc định |
|---|---|---|---|
| Số lần nhập sai tối đa | `MAX_LOGIN_ATTEMPTS` | INT | 5 |
| Thời hạn OTP (phút) | `OTP_EXPIRE_MINUTES` | INT | 5 |
| Số lần sai OTP tối đa | `OTP_MAX_ATTEMPTS` | INT | 5 |

- Mỗi card có nút "Lưu" secondary ở góc phải → `PUT /rules/{key}`.
- Có nút "Lưu tất cả" (primary) → `PUT /rules/bulk`.
- Kiểu dữ liệu đọc từ trường `data_type` của API để chọn `input type` (number / text).

### M20 — Quản lý người dùng

`GET/POST/PUT /api/v1/admin/users` · `POST /users/{id}/lock|unlock|reset-password` · `PUT /users/{id}/role`

**Bảng:** Tên đăng nhập · Họ và tên · Email · Vai trò · Trạng thái · Thao tác
- Chip vai trò: `Nhân viên` (info) · `Giáo viên` (neutral) · `Giáo vụ` (primary).
- Chip trạng thái: `Hoạt động` success · `Đã khoá` danger.
- Thao tác: khoá/mở khoá · đặt lại mật khẩu · đổi vai trò.
- **Modal tạo tài khoản:** username*, họ tên*, email*, vai trò*, phone. Hệ thống **tự sinh mật khẩu tạm** và gửi qua email (Gmail SMTP) — không hiển thị mật khẩu trên UI. API trả `must_change_password: true` và `email_sent_status` (`SUCCESS` / `FAILED` / `LOGGED`). Nếu `FAILED` → hiện cảnh báo "Không gửi được email, liên hệ quản trị viên để lấy mật khẩu tạm".

### M21 — Nhật ký hệ thống

`GET /api/v1/admin/audit-logs?page&limit&action` · `GET /export`

**Bảng:** Thời gian · Người thực hiện · Hành động · Đối tượng · Địa chỉ IP · Kết quả
- Filter: chọn ngày, chọn hành động, ô tìm kiếm.
- Hành động dùng chip neutral; kết quả `Thành công` success / `Thất bại` danger.
- Nút ghost `↓ Xuất Excel` → `GET /audit-logs/export`.
- **Modal chi tiết:** hiển thị JSON `details` dạng key-value đẹp (mã học sinh, trạng thái cũ → mới, số lần thay đổi).

### M22 — Báo cáo & Thống kê

`GET /api/v1/reports/subject-summary|chart-data|grade-summary` · `GET /reports/export/excel|pdf`

- **Filter đầu trang:** select "Môn học"* · select "Học kỳ"* (bắt buộc — API trả 400 nếu thiếu).
- **4 card KPI:** Tổng học sinh · Số lớp có điểm · Tỷ lệ đạt (%) · Số môn đang dùy.
- **2 card biểu đồ:** "Tỷ lệ đạt theo lớp" (bar chart — dùng màu primary `#2563EB`) · "Số lượng học sinh đạt" (cùng chart, màu success `#059669`). API đã trả sẵn `chart_type` + `datasets` cho Chart.js.
- **Card bảng "Tổng hợp theo lớp":** Lớp · Sĩ số · Số đạt · Tỷ lệ đạt (%) · ĐTB cao nhất.
- Nút `↓ Xuất Excel` (secondary) · `↓ Xuất PDF` (secondary).

---

## 9. MÀN HÌNH DÙNG CHUNG

### M23 — Hồ sơ cá nhân

`GET /api/v1/profile` · `PATCH /api/v1/profile` · `POST /api/v1/profile/change-password`
- Card avatar 96px (chữ cái đầu) · họ tên `title` · username · chip vai trò.
- Form thông tin: họ tên, email, số điện thoại (read-only email nếu không cho tự đổi).
- Form đổi mật khẩu: mật khẩu hiện tại* · mật khẩu mới* · xác nhận mật khẩu* → `POST /profile/change-password`.
- Hoặc luồng OTP: `POST /profile/change-password/request` → nhập mã 6 số → `POST /profile/change-password/confirm`.

### M23b — Đổi mật khẩu bắt buộc (tài khoản dùng mật khẩu tạm)

> Trang độc lập, **không có sidebar / topbar** — cùng nền `--bg-page` & card auth như M1–M3.
> Trigger: `must_change_password = true` (Giáo vụ cấp tài khoản hoặc đặt lại mật khẩu).

- Card 480px, tiêu đề "Đổi mật khẩu", subtitle: *"Tài khoản của bạn đang dùng mật khẩu tạm do Giáo vụ cấp. Vui lòng đặt mật khẩu mới để tiếp tục sử dụng hệ thống."*
- Box thông tin tài khoản (nền `--bg-subtle`): avatar tròn 40px (chữ cái đầu) · họ tên · username (mono) · email.
- Field: **Mật khẩu hiện tại**\* (nhãn phụ: "Đây là mật khẩu tạm Giáo vụ đã gửi qua email cho bạn.") · **Mật khẩu mới**\* · **Xác nhận mật khẩu**\* — cả 3 có icon mắt toggle.
- **Thanh độ mạnh mật khẩu** (4px) + danh sách 5 điều kiện có tick: ≥8 ký tự · chữ thường · chữ HOA · chữ số · ký tự đặc biệt.
- Nút primary full-width "Đổi mật khẩu và tiếp tục" → `POST /profile/change-password`.
- Nút secondary full-width "Xác thực bằng mã OTP" → `POST /profile/change-password/request` → modal 6 ô OTP → `POST /profile/change-password/confirm`.
- Chân card: nút ghost "Đăng xuất" (không có lối về dashboard — người dùng **bắt buộc** đổi mật khẩu).
- **Guard toàn cục:** mọi trang trong app đều kiểm tra `must_change_password` → tự chuyển về M23b. Sau khi đổi xong mới vào dashboard theo vai trò.

### M24 — 404 / 403 / Lỗi

| Mã | HTTP | Màn hình |
|---|---|---|
| `NOT_FOUND` | 404 | Icon file 48px `#9CA3AF` · "Không tìm thấy trang" · mô tả · nút "Về trang chủ" |
| `FORBIDDEN` | 403 | Icon khoá 48px · "Bạn không có quyền truy cập" · mô tả · nút "Quay lại" |
| `UNAUTHORIZED` | 401 | Tự redirect về M1 kèm toast "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại!" |

---

## 10. QUY ƯỚC KỸ THUẬT HTML/CSS

### 10.1 Cấu trúc file đề xuất

```
frontend/
├── index.html                  ← Trang chủ / điểm vào SPA
├── pages/
│   ├── login.html
│   ├── forgot-password.html
│   ├── reset-password.html
│   ├── students.html           ← M4
│   ├── student-detail.html     ← M6
│   ├── classes.html            ← M7
│   ├── teacher-classes.html    ← M11
│   ├── gradebook.html          ← M12
│   ├── submissions.html        ← M14/M15
│   ├── approvals.html          ← M16
│   ├── subjects.html           ← M17
│   ├── assignments.html        ← M18
│   ├── rules.html              ← M19
│   ├── users.html              ← M20
│   ├── audit-logs.html         ← M21
│   ├── reports.html            ← M22
│   └── profile.html            ← M23
│   └── change-password.html    ← M23b (đổi mật khẩu bắt buộc)
│   └── reset-otp.html          ← M2b (xác thực OTP)
│   └── reset-password.html     ← M3 (đặt mật khẩu mới)
├── partials/
│   ├── sidebar.html
│   ├── topbar.html
│   ├── page-header.html
│   ├── table.html
│   ├── pagination.html
│   └── modal.html
└── assets/
    ├── css/
    │   ├── tokens.css          ← Toàn bộ CSS variables
    │   ├── base.css            ← Reset + typography + @layer base
    │   ├── layout.css          ← App shell, sidebar, topbar
    │   ├── components.css      ← Button, Card, Input, Table, Chip, Modal…
    │   └── pages.css           ← Style riêng cho từng màn hình
    └── js/
        ├── api.js              ← fetch wrapper + JWT + refresh token
        ├── format.js           ← Ngày tháng, số, tiếng Việt
        ├── ui.js               ← Mở/đóng modal, toast, confirm
        └── main.js
```

### 10.2 Bảng CSS variables (tokens.css)

```css
:root {
  /* Nền & chữ */
  --bg-page: #F9FAFB;
  --bg-surface: #FFFFFF;
  --bg-subtle: #F3F4F6;
  --bg-hover: #F9FAFB;
  --border-default: #E5E7EB;
  --border-strong: #D1D5DB;
  --border-subtle: #F3F4F6;
  --text-primary: #111827;
  --text-secondary: #6B7280;
  --text-tertiary: #9CA3AF;

  /* Màu nhấn */
  --primary-50: #EFF6FF;
  --primary-500: #3B82F6;
  --primary-600: #2563EB;
  --primary-700: #1D4ED8;
  --primary-ring: rgba(37, 99, 235, .12);

  /* Trạng thái */
  --success: #059669;      --success-bg: #ECFDF5;
  --warning: #D97706;      --warning-bg: #FFFBEB;
  --danger:  #DC2626;      --danger-bg:  #FEF2F2;
  --info:    #0891B2;      --info-bg:    #ECFEFF;
  --neutral: #6B7280;      --neutral-bg: #F3F4F6;

  /* Typography */
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", SFMono-Regular, Menlo, monospace;
  --text-display: 24px;  --text-title: 18px;  --text-subtitle: 16px;
  --text-body: 14px;     --text-caption: 12px;

  /* Spacing */
  --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px; --sp-4: 16px;
  --sp-5: 20px; --sp-6: 24px; --sp-8: 32px; --sp-10: 40px; --sp-12: 48px;

  /* Shape */
  --radius-sm: 4px; --radius-md: 6px; --radius-lg: 8px;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, .05);

  /* Layout */
  --topbar-h: 56px;
  --sidebar-w: 240px;
  --sidebar-w-collapsed: 64px;
}
```

### 10.3 Quy ước class (BEM-lite)

| Component | Ví dụ |
|---|---|
| Layout | `.app-shell` · `.topbar` · `.sidebar` · `.sidebar__item` · `.sidebar__item--active` · `.main` |
| Trang | `.page-header` · `.page-header__title` · `.page-header__actions` · `.breadcrumb` |
| Card | `.card` · `.card__header` · `.card__title` · `.card__body` · `.card__footer` |
| Button | `.btn` · `.btn--primary` · `.btn--secondary` · `.btn--ghost` · `.btn--danger` · `.btn--sm` · `.btn--icon` |
| Form | `.field` · `.field__label` · `.field__input` · `.field__error` · `.field__hint` · `.form-grid` |
| Table | `.table-wrap` · `.table` · `.table__head` · `.table__row` · `.table__cell` · `.table__cell--mono` |
| Chip | `.chip` · `.chip--success` · `.chip--warning` · `.chip--danger` · `.chip--info` · `.chip--neutral` |
| Modal | `.modal` · `.modal__overlay` · `.modal__dialog` · `.modal__header` · `.modal__body` · `.modal__footer` |
| Feedback | `.toast` · `.toast--success` · `.alert` · `.alert--danger` · `.empty-state` · `.skeleton` |
| Khác | `.pagination` · `.avatar` · `.progress` · `.timeline` · `.tabs` · `.dropzone` |

### 10.4 Semantic HTML bắt buộc

```html
<!-- Bảng dữ liệu: luôn có <caption> cho screen-reader -->
<table class="table">
  <caption class="sr-only">Danh sách học sinh</caption>
  <thead>
    <tr>
      <th scope="col">Mã học sinh</th>
      <th scope="col">Họ và tên</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="table__cell--mono">HS20260001</td>
      <td>Nguyễn Văn An</td>
    </tr>
  </tbody>
</table>
```

```html
<!-- Form: luôn có <label for>, dấu * được đặt trong <span aria-hidden> -->
<div class="field">
  <label class="field__label" for="full_name">
    Họ và tên <span class="field__required" aria-hidden="true">*</span>
  </label>
  <input class="field__input" id="full_name" name="full_name"
         required autocomplete="name">
  <p class="field__error" id="full_name-error" role="alert" hidden>
    Vui lòng nhập họ và tên.
  </p>
</div>
```

```html
<!-- Modal: dùng <dialog> để có sẵn focus-trap + Esc -->
<dialog class="modal" id="modal-admit">
  <form method="dialog" class="modal__dialog">
    <header class="modal__header">
      <h2 class="modal__title">Tiếp nhận học sinh mới</h2>
      <button class="btn btn--ghost btn--icon" value="cancel" aria-label="Đóng">×</button>
    </header>
    <div class="modal__body">…</div>
    <footer class="modal__footer">
      <button class="btn btn--secondary" value="cancel">Huỷ</button>
      <button class="btn btn--primary" id="btn-admit-submit">Tiếp nhận</button>
    </footer>
  </form>
</dialog>
```

### 10.5 Accessibility

- Tất cả icon-button có `aria-label` bằng tiếng Việt.
- Bảng dùng `<th scope="col">`; cột hành động dùng `<th scope="col" class="sr-only">Thao tác</th>`.
- Trạng thái không chỉ dựa vào màu — chip luôn có **dot + chữ**.
- Focus ring luôn hiển thị: `:focus-visible { outline: 2px solid var(--primary-600); outline-offset: 2px; }`.
- Vùng `.sr-only` cho nhãn ẩn.
- Toast dùng `role="status"` `aria-live="polite"`; lỗi form dùng `role="alert"`.

### 10.6 Responsive

| Breakpoint | Hành vi |
|---|---|
| `≥ 1440px` | Sidebar 240px · main max-width 1440px · bảng đầy đủ |
| `1024–1439px` | Sidebar 240px · main fluid · bảng cuộn ngang nếu cần |
| `768–1023px` | Sidebar thu gọn 64px · toolbar wrap 2 dòng · form 1 cột |
| `≤ 767px` | Sidebar thành drawer · nút 44px (`btn--lg`) · bảng cuộn ngang · modal full-width, bo góc trên 12px, `max-height: 90vh` |

### 10.7 Hiệu ứng chuyển tiến

```css
/* Mặc định */
.btn, .chip, .table__row, .nav-item, .field__input {
  transition: background-color 150ms ease, border-color 150ms ease,
              color 150ms ease, opacity 150ms ease;
}

/* Modal */
dialog.modal { opacity: 0; transition: opacity 200ms ease, transform 200ms ease; }
dialog.modal[open] { opacity: 1; transform: translateY(0); }

/* Skeleton shimmer */
.skeleton {
  background: var(--bg-subtle);
  animation: shimmer 1.5s ease-in-out infinite;
}
@keyframes shimmer {
  0%, 100% { opacity: .5; }
  50%      { opacity: 1; }
}
```

> `@media (prefers-reduced-motion: reduce)` → tắt toàn bộ animation & transition.

---

## 11. MAPPING API → MÀN HÌNH

### 11.1 Xác thực

| Màn hình | Method | Endpoint | Vai trò |
|---|---|---|---|
| M1 | `POST` | `/api/v1/auth/login` | Tất cả |
| M1 | `GET` | `/api/v1/auth/verify-token` | Tất cả |
| M1 | `GET` | `/api/v1/auth/me` | Tất cả |
| M1 | `POST` | `/api/v1/auth/logout` | Tất cả |
| M2 | `POST` | `/api/v1/auth/forgot-password` | Tất cả |
| M2b | `POST` | `/api/v1/auth/verify-reset-otp` | Tất cả (bước 1 — xác thực OTP → `reset_token`) |
| M3 | `POST` | `/api/v1/auth/reset-password` | Tất cả (bước 2 — đặt MK mới bằng `reset_token`) |
| M1 | `POST` | `/api/v1/auth/register` | → luôn 403 (hệ thống không cho tự đăng ký) |
| M1 | `GET` | `/api/v1/auth/login` → `must_change_password` | → chuyển sang **M23b** |

### 11.2 Nhân viên / Giáo vụ

| Màn hình | Method | Endpoint | Vai trò |
|---|---|---|---|
| M4 | `GET` | `/api/v1/students` | STAFF, ACADEMIC |
| M4 | `GET` | `/api/v1/grades` | Tất cả |
| M4 | `GET` | `/api/v1/classes` | Tất cả |
| M4 | `GET` | `/api/v1/academic-years` | Tất cả |
| M5 | `POST` | `/api/v1/students/admit` | STAFF |
| M6 | `GET` | `/api/v1/students/{id}` | STAFF, TEACHER, ACADEMIC |
| M6 | `PUT` | `/api/v1/students/{id}` | STAFF |
| M6 | `PATCH` | `/api/v1/students/{id}/status` | STAFF, ACADEMIC |
| M6 | `DELETE` | `/api/v1/students/{id}` | ACADEMIC |
| M6 | `GET` | `/api/v1/students/{id}/print?format=pdf` | STAFF, ACADEMIC |
| M6 | `GET` | `/api/v1/students/code/{code}` | STAFF, TEACHER, ACADEMIC |
| M10 | `POST` | `/api/v1/students/import-excel` | STAFF |
| M7 | `GET/POST/PUT/DELETE` | `/api/v1/classes` | ACADEMIC (POST/PUT/DELETE) |
| M7 | `GET` | `/api/v1/classes/{id}/students` | Tất cả |
| M7 | `GET` | `/api/v1/classes/{id}/export` | STAFF, ACADEMIC |
| M8 | `POST` | `/api/v1/classes/{id}/enroll` | STAFF, ACADEMIC |
| M9 | `POST` | `/api/v1/classes/transfer` | STAFF, ACADEMIC |
| M7 | `PUT` | `/api/v1/classes/{id}/homeroom` | ACADEMIC |

### 11.3 Giáo viên

| Màn hình | Method | Endpoint | Vai trò |
|---|---|---|---|
| M11 | `GET` | `/api/v1/assignments/my` | TEACHER |
| M12 | `GET` | `/api/v1/scores/assignment/{id}` | TEACHER |
| M12 | `GET` | `/api/v1/scores/columns/config` | TEACHER |
| M12 | `POST` | `/api/v1/scores/batch` | TEACHER |
| M12 | `PUT` | `/api/v1/scores/{id}` | TEACHER |
| M12 | `GET` | `/api/v1/students/search` | TEACHER |
| M12 | `GET` | `/api/v1/scores/student/{id}` | TEACHER |
| M14 | `GET` | `/api/v1/score-submissions/my` | TEACHER |
| M14 | `POST` | `/api/v1/score-submissions` | TEACHER |
| M14 | `PUT` | `/api/v1/score-submissions/{id}/cancel` | TEACHER |
| M13/M14 | `GET` | `/api/v1/score-requests/my` | TEACHER |
| M13/M14 | `POST` | `/api/v1/score-requests` | TEACHER |

### 11.4 Giáo vụ / Admin

| Màn hình | Method | Endpoint | Vai trò |
|---|---|---|---|
| M15 | `GET` | `/api/v1/score-submissions` | ACADEMIC |
| M15 | `GET` | `/api/v1/score-submissions/{id}` | ACADEMIC |
| M15 | `PUT` | `/api/v1/score-submissions/{id}/approve` | ACADEMIC |
| M15 | `PUT` | `/api/v1/score-submissions/{id}/reject` | ACADEMIC |
| M16 | `GET` | `/api/v1/score-requests` | ACADEMIC |
| M16 | `GET` | `/api/v1/score-requests/{id}` | ACADEMIC |
| M16 | `GET` | `/api/v1/score-requests/{id}/diff` | ACADEMIC |
| M16 | `PUT` | `/api/v1/score-requests/{id}/approve` | ACADEMIC |
| M16 | `PUT` | `/api/v1/score-requests/{id}/reject` | ACADEMIC |
| M17 | `GET/POST/PUT/DELETE` | `/api/v1/subjects` | ACADEMIC (ghi) |
| M18 | `GET/POST/PUT/DELETE` | `/api/v1/assignments` | ACADEMIC |
| M18 | `PATCH` | `/api/v1/assignments/{id}/lock` | ACADEMIC |
| M19 | `GET` | `/api/v1/rules` | Tất cả |
| M19 | `PUT` | `/api/v1/rules/{key}` · `/rules/bulk` | ACADEMIC |
| M20 | `GET/POST/PUT` | `/api/v1/admin/users` | ACADEMIC |
| M20 | `POST` | `/api/v1/admin/users/{id}/lock` · `/unlock` · `/reset-password` | ACADEMIC |
| M20 | `PUT` | `/api/v1/admin/users/{id}/role` | ACADEMIC |
| M21 | `GET` | `/api/v1/admin/audit-logs` · `/{id}` · `/export` | ACADEMIC |
| M22 | `GET` | `/api/v1/reports/subject-summary` · `/chart-data` · `/grade-summary` | ACADEMIC |
| M22 | `GET` | `/api/v1/reports/export/excel` · `/export/pdf` | ACADEMIC |

### 11.5 Dùng chung

| Màn hình | Method | Endpoint | Vai trò |
|---|---|---|---|
| M23 | `GET/PATCH` | `/api/v1/profile` | Tất cả |
| M23 | `POST` | `/api/v1/profile/change-password` | Tất cả |
| M23 | `POST` | `/api/v1/profile/change-password/request` · `/confirm` | Tất cả |
| M23b | `POST` | `/api/v1/profile/change-password` · `/change-password/request` · `/confirm` | Tất cả (bắt buộc khi `must_change_password`) |
| Danh mục | `GET` | `/api/v1/semesters` · `/semesters/current` | Tất cả |
| Danh mục | `GET/POST/PUT` | `/api/v1/academic-years` · `/current` | Tất cả (ghi: ACADEMIC) |

---

## 12. MA TRẬN PHÂN QUYỀN

| Chức năng | STAFF | TEACHER | ACADEMIC |
|---|:---:|:---:|:---:|
| Xem danh sách học sinh | ✅ | ❌ | ✅ |
| Xem chi tiết 1 học sinh | ✅ | ✅ | ✅ |
| Tiếp nhận học sinh | ✅ | ❌ | ❌ |
| Sửa hồ sơ học sinh | ✅ | ❌ | ❌ |
| Xoá hồ sơ học sinh | ❌ | ❌ | ✅ |
| Đổi trạng thái học sinh | ✅ | ❌ | ✅ |
| Import Excel học sinh | ✅ | ❌ | ❌ |
| In hồ sơ học sinh | ✅ | ❌ | ✅ |
| Tạo / sửa / xoá lớp | ❌ | ❌ | ✅ |
| Phân bổ / chuyển lớp | ✅ | ❌ | ✅ |
| Xuất danh sách lớp | ✅ | ❌ | ✅ |
| Nhập / sửa điểm | ❌ | ✅ | ❌ |
| Gửi bảng điểm duyệt | ❌ | ✅ | ❌ |
| Huỷ đơn gửi duyệt | ❌ | ✅ | ❌ |
| Gửi đơn phúc khảo | ❌ | ✅ | ❌ |
| Duyệt bảng điểm | ❌ | ❌ | ✅ |
| Phê duyệt phúc khảo | ❌ | ❌ | ✅ |
| Phân công giảng dạy | ❌ | ❌ | ✅ |
| Khoá / mở khoá bảng điểm | ❌ | ❌ | ✅ |
| Quản lý môn học | ❌ | ❌ | ✅ |
| Quản lý quy định | ❌ | ❌ | ✅ |
| Quản lý người dùng | ❌ | ❌ | ✅ |
| Nhật ký hệ thống | ❌ | ❌ | ✅ |
| Báo cáo & thống kê | ❌ | ❌ | ✅ |

> **UI phải phản ánh đúng:** ẩn/disabled nút theo bảng trên (không chỉ ẩn sau khi API trả 403).

---

## 13. BẢNG LỖI CẦN BIỂU DIỄN TRONG UI

| Mã lỗi | HTTP | Nơi hiển thị | Nội dung |
|---|---|---|---|
| `CLASS_SIZE_EXCEEDED` | 422 | Alert đỏ trong modal M8/M9 | "Không thể phân lớp! Lớp {X} hiện có {cur} học sinh, thêm {add} học sinh sẽ vượt quá sĩ số tối đa cho phép ({max} học sinh)!" + hiển thị riêng `current_size` / `max_size` |
| `BUSINESS_RULE_VIOLATION` | 422 | Alert đỏ đầu form M5/M6 + đỏ field Ngày sinh | "Tuổi của học sinh là 14 tuổi. Không hợp lệ với quy định tiếp nhận (Từ 15 đến 20 tuổi)!" |
| `DUPLICATE` | 409 | Helper đỏ dưới field tương ứng | "Email/SĐT/CCCD đã thuộc học sinh khác." |
| `DUPLICATE_CODE` | 400 | Helper đỏ dưới field Mã học sinh | "Mã học sinh 'HS20260001' đã tồn tại trong hệ thống." |
| `NOT_FOUND` | 404 | Màn hình 404 hoặc toast | "Không tìm thấy dữ liệu yêu cầu." |
| `FORBIDDEN` | 403 | Màn hình 403 | "Bạn không có quyền thực hiện tác vụ này." |
| `UNAUTHORIZED` | 401 | Toast + redirect M1 | "Phiên làm việc đã hết hạn hoặc Token không hợp lệ. Vui lòng đăng nhập lại!" |
| `ACCOUNT_LOCKED` | 403 | Alert cảnh báo ở M1 + link "Đặt lại mật khẩu ngay" | "Tài khoản đã bị tạm khóa do nhập sai quá 5 lần liên tiếp. Tự động mở khóa sau 25 phút nữa." |
| `SCORE_TABLE_LOCKED` | 423 | Alert trung tính ở M12 | "Bảng điểm đã được chốt. Bạn không thể sửa trực tiếp điểm số!" + nút "Gửi đơn phúc khảo" |
| `SCORE_SUBMISSION_PENDING` | 423 | Alert cảnh báo ở M12 | "Bảng điểm đang được gửi duyệt. Vui lòng hủy đơn gửi duyệt trước khi sửa điểm!" + nút "Huỷ đơn" |
| `INVALID_SCORE_RANGE` | 422 | Viền đỏ ô điểm | "Điểm phải nằm trong khoảng từ 0.0 đến 10.0!" |
| `INCOMPLETE_SCORES` | 422 | Helper đỏ dưới nút "Gửi duyệt" | "Còn ô điểm chưa được nhập. Vui lòng nhập đủ điểm trước khi gửi duyệt!" |
| `SCORE_TABLE_NOT_LOCKED` | 422 | Alert ở M13 | "Bảng điểm đang mở. Bạn hãy sửa điểm trực tiếp thay vì gửi đơn phúc khảo!" |
| `SCORE_VALUE_CONFLICT` | 409 | Toast cảnh báo ở M13 | "Điểm hiện tại đã thay đổi so với lúc bạn gửi đơn. Vui lòng tải lại điểm!" + nút "Tải lại" |
| `DECISIONS_REQUIRED` | 422 | Alert đỏ ở M16 | "Đơn sửa điểm có nhiều ô, vui lòng gửi quyết định duyệt/từ chối cho từng ô!" |
| `DUPLICATE_PENDING_SUBMISSION` | 409 | Toast ở M12/M15 | "Bảng điểm này đã được gửi duyệt và đang chờ Giáo vụ xử lý." |
| `INVALID_SUBMISSION_STATUS` | 409 | Toast ở M14 | "Chỉ có thể hủy đơn đang ở trạng thái chờ duyệt!" |
| `INVALID_COLUMN_NAME` | 422 | Toast ở M12 | "Cột điểm không hợp lệ!" |
| `INVALID_COLUMN_COUNT` | 422 | Toast ở M19/M12 | "Số cột điểm vượt quá quy định cho phép!" |
| `INVALID_FILE_TYPE` | 400 | Helper đỏ dưới dropzone M10 | "Chỉ hỗ trợ file định dạng .xlsx, .xls hoặc .csv" |
| `INVALID_DATE_FORMAT` | 400 | Helper đỏ dưới field Ngày sinh | "Định dạng ngày sinh không hợp lệ. Vui lòng dùng YYYY-MM-DD." |
| `INVALID_EMAIL` | 400 | Helper đỏ dưới field Email | "Định dạng email không hợp lệ." |
| `INVALID_STATUS` | 400 | Toast | "Trạng thái không hợp lệ. Các giá trị cho phép: DANG_HOC, THOI_HOC, CHUYEN_TRUONG, TOT_NGHIEP" |

---

## 14. CHECKLIST BÀN GIAO

### 14.1 Về mặt kỹ thuật

- [ ] Dùng **HTML5 semantic** (`<header> <main> <nav> <section> <table> <dialog> <form>`), không dùng `<div>` cho mọi thứ.
- [ ] Tách CSS theo `tokens.css` / `base.css` / `layout.css` / `components.css` / `pages.css`.
- [ ] **Không** dùng framework UI, không CDN Bootstrap/Tailwind (trừ khi chủ đích xác nhận).
- [ ] Mọi giá trị màu / khoảng cách / bo góc đều lấy từ CSS variable — **không hardcode** trong file khác.
- [ ] Mọi giá trị nghiệp vụ (tuổi, sĩ số, số cột điểm, ngưỡng đạt) đọc từ `GET /api/v1/rules` — **không hardcode trong HTML/JS**.
- [ ] Xử lý `401` → refresh token → retry 1 lần → nếu fail thì redirect M1.
- [ ] Xử lý `403` → hiển thị màn hình 403.
- [ ] Tất cả fetch có trạng thái `loading` (skeleton) + `empty` + `error`.
- [ ] Xử lý `resize` / cuộn ngang bảng điểm: cột đầu `position: sticky; left: 0`.
- [ ] Form: validate client-side trước khi gọi API, nhưng vẫn render lỗi từ server.

### 14.2 Về mặt thiết kế

- [ ] Mọi bảng có `caption` (sr-only) + `<th scope="col">`.
- [ ] Mọi icon-button có `aria-label` tiếng Việt.
- [ ] Focus ring hiển thị rõ trên mọi phần tử tương tác.
- [ ] Trạng thái không chỉ dựa vào màu — chip luôn có dot + chữ.
- [ ] Mọi hành động phá huỷ dữ liệu có confirm dialog nêu rõ đối tượng bị ảnh hưởng.
- [ ] Modal: focus trap, `Esc` đóng, focus trả về nút mở.
- [ ] Số trong bảng dùng `font-variant-numeric: tabular-nums`.
- [ ] Cột mã (mã HS, mã lớp, mã môn) dùng font mono.
- [ ] Tiêu đề bảng tiếng Việt nghiệp vụ — không dùng tên cột kỹ thuật.
- [ ] Mọi màn hình dữ liệu có trạng thái rỗng & trạng thái loading.
- [ ] Mọi bảng có phân trang (kể cả bảng ngắn — vẫn hiện mẫu phân trang để nhất quán).
- [ ] Text không bị tràn/cắt ở bất kỳ frame nào — đặc biệt cột tiếng Việt dài & bảng điểm 10+ cột.
- [ ] Responsive đúng ở 1440px / 1024px / 768px / 375px.
- [ ] `prefers-reduced-motion` được tôn trọng.

---

## PHỤ LỤC A — Dữ liệu mẫu để dựng giao diện

| Loại | Giá trị mẫu |
|---|---|
| **Học sinh** | `HS20260001` · Nguyễn Văn An · 14/05/2010 · Nam · `0912345678` · `an.nguyen@student.school.edu` · `079001001234` · Lớp 10A1 |
| **Học sinh** | `HS20260002` · Trần Thị Bình · 22/08/2010 · Nữ · `0912345679` · `binh.tran@student.school.edu` · Lớp 10A1 |
| **Lớp** | `10A1` · Khối 10 · 2026-2027 · GV chủ nhiệm: Nguyễn Thu Hà · Sĩ số `28 / 40` |
| **Môn học** | `TOAN` Toán Học (Khối 10, 5 tiết) · `VAN` Ngữ Văn (Khối 10, 5 tiết) · `ANH` Tiếng Anh (Khối 10, 4 tiết) |
| **Giáo viên** | `gv01` · Trần Văn Giáo · `giaovu@school.edu` · Giáo viên |
| **Niên khóa / Học kỳ** | `2026-2027` · Học kỳ `1` |
| **Quy định** | `MIN_AGE` 15 · `MAX_AGE` 20 · `MAX_CLASS_SIZE` 40 · `MAX_COL_15M` 5 · `MAX_COL_45M` 3 · `NUM_COL_FINAL` 1 · `PASSING_SCORE` 5.0 · `MAX_LOGIN_ATTEMPTS` 5 · `LOCK_DURATION_MINUTES` 30 · `OTP_EXPIRE_MINUTES` 5 · `OTP_MAX_ATTEMPTS` 5 |

---

## PHỤ LỤC A2 — Cấu hình Mail (Gmail SMTP)

Hệ thống gửi 3 loại mail qua SMTP:

| Loại mail | Trigger | Hàm backend |
|---|---|---|
| Cấp tài khoản (kèm mật khẩu tạm) | `POST /admin/users` | `mail_service.send_account_email` |
| Mã OTP (quên MK / đổi MK) | `POST /auth/forgot-password`, `POST /profile/change-password/request` | `mail_service.send_otp_email` |
| Thông báo mật khẩu đã đổi | Sau khi đổi mật khẩu thành công | `mail_service.send_password_changed_email` |

### Cách cấu hình

1. Tạo file `.env` trong `studentmanagementapp/` (file này **đã nằm trong `.gitignore`** — không được commit):

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=abcd efgh ijkl mnop
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

2. Gmail **không** cho phép đăng nhập SMTP bằng mật khẩu thường. Vào <https://myaccount.google.com/apppasswords> → bật 2FA → tạo App Password (16 ký tự, giữ nguyên dấu cách).
3. Restart server — `config.py` tự nạp `.env` qua `python-dotenv`.

### Hành vi khi không cấu hình / gửi lỗi

| Tình huống | `email_sent_status` | Hành vi |
|---|---|---|
| Không có `MAIL_*` | `LOGGED` | Nội dung mail in ra console, hệ thống vẫn chạy (dev mode) |
| Gửi thất bại (SMTP lỗi) | `FAILED` | Tài khoản **vẫn được tạo**, UI hiện cảnh báo cần liên hệ quản trị viên |
| Thành công | `SUCCESS` | Tài khoản + mật khẩu tạm đã gửi qua email |

> `TestingConfig` cố tình đặt `MAIL_SERVER = ""` → mọi test chạy ở chế độ `LOGGED`, không gửi mail thật.

---

## PHỤ LỤC B — Quy ước mã trạng thái trong UI

| Mã API | Nhãn hiển thị | Màu chip |
|---|---|---|
| `DANG_HOC` | Đang học | success |
| `THOI_HOC` | Thôi học | info |
| `CHUYEN_TRUONG` | Chuyển trường | warning |
| `TOT_NGHIEP` | Tốt nghiệp | danger |
| `DA_CHUYEN` | Đã chuyển | neutral |
| `PENDING` | Chờ duyệt | warning |
| `APPROVED` | Đã duyệt | success |
| `PARTIALLY_APPROVED` | Duyệt một phần | warning |
| `REJECTED` | Từ chối | danger |
| `CANCELLED` | Đã huỷ | neutral |
| `is_locked = true` | Đã khoá | neutral |
| `is_locked = false` | Mở | success |
| `is_draft = true` | Bản nháp | neutral |
| `is_draft = false` | Chính thức | success |
| `STAFF` | Nhân viên | info |
| `TEACHER` | Giáo viên | neutral |
| `ACADEMIC` | Giáo vụ | primary |
| `is_active = true` | Đang dùng | success |
| `is_active = false` | Ngừng dùng | neutral |

---

> **Tài liệu này được đối chiếu với mã nguồn backend hiện tại** (`studentmanagementapp/studentapp/controllers/`, `services/`, `models/`). Khi backend thay đổi contract (thêm endpoint, đổi tên trạng thái, đổi công thức ĐTB), cần cập nhật lại §11 Mapping API và §13 Bảng lỗi.
