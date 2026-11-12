# Ghi chú làm việc — Dự án Quản lý Học sinh / Điểm số

> **Mục đích:** File này là "bảng ghi" cho các phiên làm việc sau. Mỗi lần thay đổi thiết kế, ghi lại **quyết định đã chốt**, **lý do**, và **việc còn dang dở** — để không phải tra lại lịch sử chat.
>
> **Cập nhật:** khi có thay đổi mới trong `requirements.md` / `API.md` / `database-design.md`, cập nhật lại file này.

---

## 1. Trạng thái hiện tại (cập nhật lần cuối: 12/11/2026)

| Tài liệu | Nội dung | Số lượng |
|---|---|---|
| `requirements.md` | Use case ↔ Sequence diagram (BCE) | **24** sơ đồ (SD01–SD22, SD23, SD24, **SD25**) |
| `API.md` | RESTful endpoints | **85** endpoints / 14 nhóm logic |
| `database-design.md` | Bảng quan hệ chuẩn hóa (3NF) | **16** bảng |

**Đã loại bỏ khỏi phạm vi:** chức năng *điểm danh* (`SD10_DiemDanhHocSinh`, bảng `attendances`, 3 endpoint `/attendances/*`) — vì Yêu cầu 3 của đề bài chỉ quy định *nhập điểm* & *xuất điểm trung bình lớp*.

---

## 2. Quyết định thiết kế quan trọng (đã chốt)

### 2.1. Ba lớp dữ liệu điểm số — KHÔNG được lẫn

| Khái niệm | Cờ | Ý nghĩa |
|---|---|---|
| **Bảng điểm tạm** | `scores.is_draft = TRUE` | GV đang soạn. Sửa thoải mái, **không cần xin quyền**. ĐTB **vẫn được tính** để GV tự kiểm tra. |
| **Bảng điểm chính thức** | `scores.is_draft = FALSE` | Đã được Giáo vụ duyệt & chốt. **Đây mới là điểm thật.** |
| **Trạng thái bảng điểm** | `teaching_assignments.is_locked` | `FALSE` = đang mở (cho phép nhập tạm) · `TRUE` = **đã chốt** (không sửa trực tiếp được) |

> ⚠️ `is_locked` **KHÔNG còn** mang ý nghĩa "cổng chặn ghi nhập điểm" như thiết kế cũ. Nó giờ là **cờ "đã chốt"**.

### 2.2. Luồng chốt điểm 3 bước

```
GV nhập điểm (SD11)          → POST /scores/batch       → ghi vào BẢNG ĐIỂM TẠM (is_draft = TRUE)
GV bấm "Gửi duyệt" (SD23)   → POST /score-submissions  → tạo score_submissions (PENDING)
GV đổi ý (SD23)             → PUT .../cancel           → CANCELLED, giữ is_draft = TRUE → GV sửa & gửi lại
Giáo vụ duyệt (SD24)         → PUT .../approve          → is_draft = FALSE + is_locked = TRUE  (CÙNG 1 transaction ACID)
Giáo vụ từ chối (SD24)       → PUT .../reject           → giữ nguyên is_draft = TRUE, GV sửa & gửi lại
```

**Trong lúc đơn `PENDING`** → GV **không sửa được** ô điểm (bị chặn **423 `SCORE_SUBMISSION_PENDING`**) → phải **Hủy** đơn trước.

**Sau khi đã chốt (`APPROVED`)**, muốn sửa điểm → luồng phúc khảo **SD25** (`POST /score-requests` → SD19 Giáo vụ duyệt).

### 2.3. Ba bảng nghiệp vụ khác nhau — không gộp

| Bảng | Dùng cho | Đơn vị |
|---|---|---|
| `score_submissions` | Duyệt **cả bảng điểm** lớp môn học | 1 lớp môn học / 1 lần gửi |
| `score_change_requests` | Phúc khảo — **đơn cha** | 1 lần gửi yêu cầu sửa điểm (đơn lẻ hoặc đơn lô) |
| `score_change_details` | Phúc khảo — **đơn con** | 1 **ô điểm** được đề nghị sửa (có `status` riêng) |

> ⚠️ **Trạng thái thật nằm ở bảng con** `score_change_details.status`. `score_change_requests.status` chỉ là **tóm tắt** (`APPROVED` / `REJECTED` / `PARTIALLY_APPROVED`) để lọc nhanh — code cần biết "ô nào được áp dụng" thì **luôn query bảng con**.

### 2.3b. Biểu mẫu gửi yêu cầu sửa điểm (đã chốt 12/11/2026)

* Thứ tự chọn: **Lớp → Học sinh → Môn học → Cột điểm** (15' / 1 tiết / cuối kỳ).
* **Điểm hiện tại hiển thị CHỈ ĐỌC** — GV không sửa trực tiếp được điểm đã chốt (đảm bảo trung thực).
* **Lý do (`reason`) là BẮT BUỘC** — chọn trong danh mục (gõ nhầm số, chấm sót ý bài tự luận, phúc khảo, chấm lại bài giấy…) hoặc tự nhập.
* **File đính kèm (ảnh/PDF) LUÔN TÙY CHỌN** — KHÔNG bắt buộc theo loại lý do (quyết định của user 12/11/2026). GV tự quyết định; với lý do "gõ nhầm 7.5 thành 5.7" thì không cần đính kèm.
* Hỗ trợ **2 mức**: **đơn lẻ** (1 ô) & **đơn lô** (nhiều ô của nhiều HS) — cùng 1 endpoint `POST /score-requests`, body chứa mảng `changes[]`.

### 2.3c. Outbox Pattern — mail không được gửi bên trong transaction

> **Vì sao:** nếu gửi mail trong transaction mà SMTP lỗi *sau khi* đã gửi mail nhưng *trước khi* commit → GV nhận mail "đã duyệt" trong khi DB rollback → **mất tính nhất quán dữ liệu** (đúng thứ đồ án muốn chứng minh là **giải quyết được**).

**Cách làm đúng:** `INSERT INTO email_outbox` **trong cùng transaction** → sau `COMMIT`, worker đọc outbox & gửi mail. Kết quả: **gửi mail thông báo tự động, không cần thao tác tay**, và không bao giờ có mail/DB lệch nhau.

### 2.3d. 🎯 Quy ước giá trị ô điểm — "NULL = chưa nhập, 0 = đã nhập" (đã chốt 12/11/2026)

| Trạng thái ô | Giá trị DB | Tính vào ĐTB | Ý nghĩa |
|---|---|---|---|
| **Chưa nhập** | `NULL` (ô để trống) | ❌ Không tính | GV chưa chấm → **lỗi GV**, chặn bước "Gửi duyệt" |
| **Vắng** | `0.00` | ✅ Có tính | HS vắng kiểm tra → quy về **0 điểm** |
| **Thi = 0 điểm** | `0.00` | ✅ Có tính | HS dự thi nhưng làm sai hết → **0 điểm** |
| **Đã chấm** | `0.00` – `10.00` | ✅ Có tính | Điểm thực tế |

* **Không** dùng giá trị đặc biệt (`-1`), **không** cần cờ `is_absent` → đơn giản, dễ giải thích khi bảo vệ.
* Ô `NULL` **loại khỏi cả tử số & mẫu số** của ĐTB; ô `0.00` **vẫn được tính** → HS vắng bị trừ điểm đúng như thực tế.
* HS chưa có ô điểm nào → `average_score = NULL`, `is_passed = NULL` → không tính vào tỷ lệ đạt.
* UI: mỗi ô có checkbox **"Vắng"** → tự điền `0` (cách nhập nhanh, **không** đổi giá trị).
* **Công thức ĐTB DUY NHẤT:** mẫu số = **số ô CÓ GIÁ TRỊ** (× trọng số 1/2/3) — **KHÔNG** dùng "số cột theo quy chế" (sẽ làm ĐTB nhảy khi GV mới chấm dở).
* **Partial update (đã chốt 12/11/2026):** ô gửi lên với `null` → **giữ nguyên giá trị trong DB**, KHÔNG xoá điểm đã chấm → chống mất dữ liệu khi form chưa render kịp. Xoá điểm có chủ đích → `PUT /scores/{id}` với `clear: true` (có audit log).

### 2.3e. Ràng buộc nhập điểm — 2 mức (đã chốt 12/11/2026)

| Mức | Bước | Tính chất | Chặn cái gì |
|---|---|---|---|
| **1** | **"Lưu"** (`POST /scores/batch`) | Cấu trúc dữ liệu | Điểm ngoài `[0, 10]` · số cột vi phạm `system_rules` · trùng `student_id` · HS không thuộc lớp · sai phân công · bảng điểm đã chốt |
| **2** | **"Gửi duyệt"** (`POST /score-submissions`) | Nghiệp vụ | **Ô nào còn `NULL` → `422 INCOMPLETE_SCORES`** · chưa có điểm nào · trùng đơn `PENDING` · bảng điểm đã chốt · sai phân công |

### 2.3f. 🎯 Vòng đời đơn gửi duyệt — `PENDING` / `APPROVED` / `REJECTED` / `CANCELLED` (đã chốt 12/11/2026)

```
   (chưa gửi) ──GV bấm "Gửi duyệt"──> PENDING ──┬── Giáo vụ DUYỆT ─────> APPROVED  (điểm chính thức, KHÓA bảng điểm)
                                              │
                                              ├── Giáo vụ TỪ CHỐI ──> REJECTED  (giữ is_draft=TRUE, GV sửa & gửi lại)
                                              │
                                              └── GV bấm "Hủy" ────> CANCELLED (giữ is_draft=TRUE, GV sửa & gửi lại)
```

| Trạng thái đơn | GV sửa bảng điểm tạm? | Cách đi tiếp |
|---|---|---|
| Chưa gửi | ✅ Tự do | Nhập điểm rồi bấm "Gửi duyệt" |
| **`PENDING`** | ❌ **423 `SCORE_SUBMISSION_PENDING`** | Phải **Hủy** đơn trước (`PUT /score-submissions/{id}/cancel`) |
| **`CANCELLED`** | ✅ Tự do | Sửa lại rồi gửi duyệt lại (tạo đơn `PENDING` mới) |
| **`REJECTED`** | ✅ Tự do | Sửa lại theo lý do Giáo vụ rồi gửi lại |
| **`APPROVED`** | ❌ **423 `SCORE_TABLE_LOCKED`** | Bảng điểm đã chốt → gửi **đơn phúc khảo** (SD25 → SD19) |

**Vì sao chặn sửa khi `PENDING`?** Nếu GV sửa được sau khi gửi → Giáo vụ duyệt một bản điểm **không còn khớp với những gì GV đã gửi** → mất tính trung thực của luồng duyệt.

**Vì sao giữ bản ghi `CANCELLED` thay vì xóa?** Để **audit trail** đầy đủ: biết GV đã gửi → hủy → gửi lại bao nhiêu lần, và mỗi lần vì lý do gì.

**DB:** `score_submissions.status` ENUM thêm `CANCELLED` + 2 cột `cancelled_at`, `cancel_note`.
**Unique index:** phải là **partial unique** (`assignment_id` WHERE `status = 'PENDING'`) — nếu UNIQUE thuần trên `assignment_id` thì lần gửi thứ 2 sẽ **không insert được**.

> **Ràng buộc "không được bỏ trống"** nằm ở **Mức 2**, KHÔNG phải Mức 1 → GV có thể **lưu dở** để soạn tiếp nhưng **không thể gửi duyệt** khi còn ô trống.
> Server **quét toàn bộ** `scores` của lớp môn học (không chỉ dòng vừa lưu) → không thể lách bằng cách gửi từng phần.

### 2.4. Quy tắc ACID bắt buộc

* `PUT /score-submissions/{id}/approve`: `UPDATE scores SET is_draft=FALSE` **và** `UPDATE teaching_assignments SET is_locked=TRUE` **phải chạy trong CÙNG một transaction** → không bao giờ có trạng thái nửa vời (điểm đã chính thức nhưng bảng vẫn mở, hoặc ngược lại).
* `PUT /score-requests/{id}/approve`: tính lại `average_score` & `is_passed` **cùng transaction** với `UPDATE scores`.

**Chuỗi lệnh của 1 transaction duyệt phúc khảo (đơn lô — N ô):**
```
BEGIN
  ├─ UPDATE score_change_requests  SET status, approved_by, approval_note, resolved_at
  ├─ UPDATE score_change_details  SET status='APPROVED'  (cho từng ô được duyệt)
  ├─ UPDATE scores                SET <score_column>=new_value, is_draft=FALSE  (từng ô)
  ├─ UPDATE scores                SET average_score=?, is_passed=?  (từng học sinh)
  ├─ INSERT INTO audit_logs       (action='APPROVE_SCORE_CHANGE', ...)
  └─ INSERT INTO email_outbox     (to_email=<email GV>, subject, body)
COMMIT   → worker gửi mail
```
Lỗi ở bất kỳ bước nào → **ROLLBACK toàn bộ** → không tồn tại trạng thái "đơn đã duyệt nhưng điểm chưa sửa".

### 2.5. ⚠️ Bug đã sửa — phúc khảo KHÔNG được ghi vào bảng tạm

Khi Giáo vụ duyệt đơn phúc khảo:
* Điểm mới ghi thẳng vào **điểm chính thức** → **giữ nguyên `scores.is_draft = FALSE`**. Nếu ghi `is_draft = TRUE` → điểm đã chốt bị "hạ" về bản nháp → **biến mất khỏi báo cáo**.
* **Không** đụng tới `is_locked` — bảng điểm vẫn phải **ĐÃ CHỐT**.

*(Đã sửa đồng bộ trong cả 3 file: `requirements.md` §7.18 + §4.1, `API.md` §9 + §Mã lỗi, `database-design.md` §13.)*

### 2.6. ⚠️ Quy tắc lọc điểm khi ĐỌC

Mọi truy vấn đọc **điểm chính thức** → **bắt buộc** `WHERE is_draft = FALSE`:
`SD20` báo cáo thống kê · `SD13` xuất ĐTB lớp · `SD12` xem ĐTB lớp · `GET /scores/student/{studentId}`

> ⚠️ `GET /scores/student/{studentId}` là **đường hở rò rỉ** vì học sinh tự xem điểm của chính mình.
> **Ngoại lệ:** `GET /scores/assignment/{assignmentId}` dùng query param `draft=true|false|all`
> (TEACHER mặc định `all` để soạn tiếp; ACADEMIC mặc định `false`).

---

## 3. Mã lỗi nghiệp vụ đã định nghĩa

| Mã | Ý nghĩa | Dùng ở đâu |
|---|---|---|
| `423 SCORE_TABLE_LOCKED` | Bảng điểm đã chốt, GV không sửa trực tiếp được | `POST /scores/batch`, `PUT /scores/{id}`, `POST /score-submissions` |
| `409 DUPLICATE_PENDING_SUBMISSION` | Lớp môn học đã có bản ghi đang chờ duyệt (GV phải Hủy đơn cũ trước) | `POST /score-submissions` |
| `423 SCORE_SUBMISSION_PENDING` | Đang có đơn gửi duyệt `PENDING` → GV phải Hủy đơn trước khi sửa điểm | `POST /scores/batch`, `PUT /scores/{id}` |
| `409 INVALID_SUBMISSION_STATUS` | Đơn không ở trạng thái `PENDING` → không hủy được | `PUT /score-submissions/{id}/cancel` |
| `422 NO_SCORES_TO_SUBMIT` | Chưa nhập ô điểm nào để gửi duyệt | `POST /score-submissions` |
| `422 SCORE_TABLE_NOT_LOCKED` | Bảng điểm đang mở → phải sửa trực tiếp, không gửi đơn phúc khảo | `POST /score-requests` |
| `409 SCORE_VALUE_CONFLICT` | `old_value` GV gửi lên không khớp điểm hiện tại trong `scores` | `POST /score-requests` |
| `422 DECISIONS_REQUIRED` | Duyệt đơn lô thiếu `decisions[]` | `PUT /score-requests/{id}/approve` |
| `422 INVALID_ATTACHMENT_TYPE` | File đính kèm không phải ảnh (png/jpeg/webp) hoặc PDF | `POST /score-requests/attachment` |
| `413 FILE_TOO_LARGE` | File đính kèm vượt 10 MB | `POST /score-requests/attachment` |
| `422 INCOMPLETE_SCORES` | Còn ô điểm `NULL` (chưa nhập) khi gửi duyệt | `POST /score-submissions` |
| `422 INVALID_COLUMN_COUNT` | Số cột điểm vi phạm `system_rules` | `POST /scores/batch` |
| `422 DUPLICATE_STUDENT_IN_BATCH` | Trùng `student_id` trong 1 request | `POST /scores/batch` |
| `422 STUDENT_NOT_IN_ASSIGNMENT` | HS không thuộc lớp của bảng điểm | `POST /scores/batch` |

---

## 4. Mô hình dữ liệu chuẩn hóa (16 bảng)

| # | Bảng | Nhóm |
|---|---|---|
| 1 | `users` | Core & Security |
| 2 | `system_rules` | Core & Security |
| 3 | `audit_logs` | Core & Security |
| 4 | `academic_years` | Học vụ & Tổ chức lớp |
| 5 | `semesters` | Học vụ & Tổ chức lớp |
| 6 | `grades` | Học vụ & Tổ chức lớp |
| 7 | `classes` | Học vụ & Tổ chức lớp |
| 8 | `class_enrollments` | Học vụ & Tổ chức lớp |
| 9 | `students` | Hồ sơ học sinh |
| 10 | `subjects` | Danh mục môn học |
| 11 | `teaching_assignments` | Phân công giảng dạy |
| 12 | `scores` | Kết quả học tập (có `is_draft`) |
| 13 | `score_change_requests` | Phúc khảo — đơn cha |
| 14 | `score_change_details` | Phúc khảo — đơn con (từng ô điểm) |
| 15 | `email_outbox` | Hạ tầng thông báo (Outbox Pattern) |
| 16 | `score_submissions` | Gửi duyệt bảng điểm |

**Cột đáng chú ý:** `scores.is_draft` (BOOLEAN, DEFAULT TRUE) + `scores.submitted_at` (TIMESTAMP) + index `idx_scores_draft(assignment_id, is_draft)`.

---

## 5. Phân hệ Giáo viên — 6 use case / 16 endpoint

| SD | Use Case | Endpoint chính |
|---|---|---|
| SD09 | Tra cứu danh sách lớp phụ trách | `GET /assignments/my` |
| SD11 | Nhập điểm môn học (BẢNG ĐIỂM MÔN HỌC) | `POST /scores/batch` |
| SD12 | Xem bảng điểm trung bình lớp (BẢNG ĐIỂM TRUNG BÌNH LỚP) | `GET /scores/class/{classId}/subject/{subjectId}/yearly` |
| SD13 | Xuất điểm trung bình lớp | `GET /scores/export` |
| SD14 | Sửa điểm học sinh (bảng điểm đang MỞ) | `PUT /scores/{id}` |
| SD23 | Gửi bảng điểm lên duyệt | `POST /score-submissions`, `PUT /score-submissions/{id}/cancel`, `GET /score-submissions/my` |
| SD25 | Gửi yêu cầu chỉnh điểm (bảng điểm đã CHỐT) | `POST /score-requests`, `POST /score-requests/attachment`, `GET /score-requests/my` |

**Endpoint phụ trợ phúc khảo (Giáo vụ):** `GET /score-requests/{id}/diff` (bảng so sánh điểm cũ ↔ mới cho đơn lô), `PUT /score-requests/{id}/approve` (duyệt **từng ô** qua `decisions[]`), `PUT /score-requests/{id}/reject`.

**Biểu mẫu bắt buộc theo đề bài (YC3):**
* **BẢNG ĐIỂM MÔN HỌC** — STT, Họ tên, Điểm 15' (1–5 cột), Điểm 1 tiết (1–3 cột), Điểm thi (1 cột).
* **BẢNG ĐIỂM TRUNG BÌNH LỚP** — Năm học, STT, Họ tên, Lớp, Điểm TB HK1, Điểm TB HK2.
  → Cột **ĐTB cả năm** (`avg_yearly`) chỉ có trong API để phục vụ xếp loại, **KHÔNG** đưa vào file xuất.

---

## 6. Việc còn dang dở / ghi chú cho phiên sau

- [ ] **Chưa có code thực thi** — hiện chỉ có 3 file tài liệu thiết kế. Cần dựng app theo `studentmanagementapp/` (đã có sẵn khung `studentapp/exceptions.py`).
- [ ] Chưa viết **migration** cho `scores.is_draft`. Nếu có dữ liệu cũ: `UPDATE scores SET is_draft = FALSE` cho các bảng điểm đã chốt **trước khi deploy**, nếu không mọi điểm cũ sẽ bị coi là nháp và biến mất khỏi báo cáo.
- [ ] Chưa sinh **file Excel/PDF** thực tế — cần thư viện (`openpyxl` / `reportlab`) theo đúng mẫu đề bài.
- [ ] Chưa viết **migration** cho 2 bảng mới: `score_change_details` + `email_outbox`.
- [ ] Chưa có **worker gửi mail** đọc `email_outbox` (nền dùng Celery/RQ/APScheduler; có thể dùng cron job đơn giản cho đồ án).
- [ ] Chưa viết **service validate điểm** — cần 2 tầng: `validate_scores_payload()` (Mức 1, lúc Lưu) & `validate_completeness()` (Mức 2, lúc Gửi duyệt) trả về danh sách `missing_columns` theo từng học sinh.
- [ ] Chưa viết hàm **tính ĐTB theo quy ước NULL/0** — phải loại ô `NULL` khỏi cả tử số & mẫu số, giữ ô `0.00` trong cả hai.
- [ ] Chưa có **upload endpoint thực thi** (`POST /score-requests/attachment`) — cần cấu hình `MAX_CONTENT_LENGTH=10MB` + thư mục `uploads/score_requests/YYYY/MM/` + sanitize tên file.
- [ ] Cần xác nhận: **học sinh có xem điểm qua hệ thống không?** Hiện `GET /scores/student/{studentId}` cho phép, nhưng role `HS` chưa có mục rõ trong §4 của `requirements.md`.
- [ ] Cân nhắc thêm **use case xem hồ sơ học sinh trong phạm vi lớp mình dạy** — *hiện quyết định KHÔNG thêm* (tránh tràn phạm vi YC3), nhưng có thể thêm sau nếu đề bài yêu cầu mở rộng.

---

## 7. Quy ước làm việc với 3 file tài liệu

| Khi sửa | Phải cập nhật đồng bộ |
|---|---|
| Thêm/bớt endpoint | `API.md` (bảng tổng hợp + chi tiết + số lượng ở đầu file) → `requirements.md` (SD liên quan) → `database-design.md` (bảng liên quan) |
| Đổi ý nghĩa cờ/column | `database-design.md` (mô tả cột) → `API.md` (quy ước chung + mô tả endpoint) → `requirements.md` (kịch bản SD) |
| Thêm use case | `requirements.md` (§4 bảng ánh xạ + §4.1 + sơ đồ sequence **đánh số lại liên tục**) → `API.md` (endpoint) |

**Bẫy đã gặp — tránh lặp lại:**
1. **Đánh số lại sơ đồ sequence:** sửa bằng script theo **anchor cụ thể** (`SDxx_Yyy`), đừng dùng regex số thứ tự → dễ làm cascade ảnh hưởng các heading sau.
2. **Cột bảng Markdown:** luôn giữ định dạng `| STT | Method | Endpoint | Role | Mô tả |`. Regex `\| (\d+) \|` có thể nuốt mất cột Method.
3. **Tiếng Việt có dấu:** khi viết `old_string` bằng tay rất dễ gõ sai dấu → nên dùng script Python đọc/ghi theo dòng (line-based) thay vì thay thế chuỗi.
4. **Vị trí chèn:** luôn chèn theo **anchor nội dung** (`| 14 | \`Sửa điểm học sinh\``) chứ không theo số thứ tự, để tránh rơi vào nhóm sai.

---

## 8. Nguồn đề bài — đối chiếu Yêu cầu 3

> "Giáo viên tra cứu danh sách lớp phụ trách, nhập điểm thành phần theo biểu mẫu **BẢNG ĐIỂM MÔN HỌC** (điểm 15 phút, điểm 1 tiết, điểm thi), xem và xuất **BẢNG ĐIỂM TRUNG BÌNH LỚP** theo năm học."

→ Đó là toàn bộ phạm vi chức năng giáo viên được yêu cầu. Mọi chức năng khác (điểm danh, duyệt bảng điểm, phúc khảo) là **bổ trợ hợp lý** phục vụ cho luồng đó.
