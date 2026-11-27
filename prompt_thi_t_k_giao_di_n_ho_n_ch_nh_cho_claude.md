# NHIỆM VỤ: NÂNG CẤP GIAO DIỆN (UI/UX) TOÀN DIỆN TỪ BẢN PHÁC THẢO LÊN SẢN PHẨM HOÀN CHỈNH

Bạn là một **Senior Product Designer & Frontend Architect** chuyên xây dựng các hệ thống EdTech và SaaS quản trị doanh nghiệp chuẩn mực.

Hiện tại, mã nguồn trong thư mục `src/` của dự án này mới chỉ là **bản phác thảo khung sườn (wireframe/prototype)** để chạy thử nghiệm luồng nghiệp vụ. Nhiệm vụ của bạn là **thiết kế lại và hoàn thiện toàn bộ giao diện (UI/UX)** cho tất cả các màn hình, modal và component dùng chung, biến dự án thành một ứng dụng **Hệ thống Quản lý Học sinh, Lớp học & Sổ điểm** hiện đại, tinh tế, chuyên nghiệp và sẵn sàng đưa vào sử dụng thực tế.

---

## 1. BỐI CẢNH KỸ THUẬT & RÀNG BUỘC BẮT BUỘC

Tuân thủ nghiêm ngặt các quy định trong `@AGENTS.md` và `@CLAUDE.md`:

1. **Công nghệ cốt lõi:** React 19, TypeScript 5.7, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`).
2. **Quy tắc Tailwind CSS v4 (`src/index.css`):**
   - Giữ nguyên `@import 'tailwindcss';` ở dòng đầu tiên.
   - Không tạo `tailwind.config.js` hay `postcss.config.js`.
   - Khai báo biến màu sắc, font chữ, shadow và animation tùy chỉnh thông qua `@theme { ... }` trong `src/index.css`.
   - Mọi style mặc định cho thẻ HTML (`body`, `button`, `input`, scrollbar...) bắt buộc đặt bên trong `@layer base { ... }` để không ghi đè các utility classes của Tailwind.
3. **Bảo toàn 100% logic nghiệp vụ:**
   - **KHÔNG** làm hỏng các luồng xử lý, phân quyền người dùng (Admin, Giáo viên, Học sinh), dữ liệu mẫu và hàm xử lý trong `src/context/AppContext.tsx`, `src/data/mockData.ts` và `src/types/index.ts`.
   - Kiểm tra `package.json` trước khi dùng icon hoặc thư viện bên ngoài (ưu tiên dùng thư viện đã cài sẵn như `lucide-react` nếu có, hoặc viết SVG icon sắc nét, đồng bộ).
4. **Ngôn ngữ giao diện:** 100% tiếng Việt tự nhiên, chuẩn xác theo thuật ngữ ngành giáo dục Việt Nam.

---

## 2. ĐỊNH HƯỚNG THẨM MỸ & HỆ THỐNG THIẾT KẾ (DESIGN SYSTEM)

Hãy xây dựng giao diện theo phong cách **Modern Academic SaaS** (tinh gọn, sáng sủa, đáng tin cậy, tối ưu cho việc đọc và nhập liệu mật độ cao tương tự Linear, Notion và Stripe Dashboard):

- **Typography (Chữ & Số):**
  - Tích hợp font Google Fonts hỗ trợ tiếng Việt hoàn hảo trong `index.html` và `src/index.css`: **`Be Vietnam Pro`** (cho tiêu đề và văn bản) kết hợp **`JetBrains Mono`** hoặc thuộc tính `tabular-nums` (cho mã học sinh, mã lớp và toàn bộ bảng điểm để các cột số thẳng hàng tuyệt đối).
  - Phân cấp thị giác (Visual Hierarchy) rõ ràng giữa tiêu đề trang, tiêu đề thẻ, nhãn trường dữ liệu và nội dung chính.
- **Bảng màu (Color Palette):**
  - **Nền tổng thể:** Xám nhạt dịu mắt (`#F8FAFC` / `slate-50`) giúp giảm mỏi mắt khi giáo viên và quản trị viên làm việc lâu.
  - **Bề mặt (Surface/Card):** Trắng tinh (`#FFFFFF`) kết hợp viền mảnh (`border-slate-200/80`) và đổ bóng nhẹ nhiều lớp (`shadow-xs`).
  - **Màu chủ đạo (Primary Brand):** Xanh Indigo / Royal Blue học thuật (`#2563EB` hoặc `#4F46E5`) có độ tương phản cao, trạng thái hover/active/focus rõ ràng.
  - **Màu ngữ nghĩa (Semantic Colors):**
    - *Thành công / Đạt / Đã duyệt:* Emerald (`emerald-600`, nền `emerald-50`, viền `emerald-200`).
    - *Cảnh báo / Chờ duyệt / Điểm cần lưu ý:* Amber (`amber-600`, nền `amber-50`, viền `amber-200`).
    - *Lỗi / Không đạt / Từ chối / Xóa:* Rose (`rose-600`, nền `rose-50`, viền `rose-200`).
    - *Thông tin / Đang xử lý:* Sky (`sky-600`, nền `sky-50`, viền `sky-200`).
- **Tương tác vi mô (Micro-interactions) & Trạng thái:**
  - Mọi nút bấm, thẻ tương tác, dòng trong bảng đều có hiệu ứng chuyển tiếp mượt (`transition-all duration-150`).
  - Có đầy đủ trạng thái: `hover`, `focus-visible` (vòng sáng focus rõ ràng), `disabled`, `loading` (`TableSkeleton`), và `empty` (`EmptyState` có minh họa icon và nút hành động gợi ý).

---

## 3. LỘ TRÌNH NÂNG CẤP CHI TIẾT TỪNG PHẦN

Hãy thực hiện lần lượt theo 4 giai đoạn dưới đây để đảm bảo tính đồng bộ tuyệt đối:

### Giai đoạn 1: Nền tảng Design Tokens & UI Primitives (`src/index.css` & `src/components/ui/*`)
Nâng cấp toàn bộ 11 component cơ sở để mọi màn hình kế thừa giao diện chuẩn xác:
- `Button.tsx`: Đầy đủ biến thể (`primary`, `secondary`, `outline`, `ghost`, `danger`), kích thước (`sm`, `md`, `lg`), hỗ trợ icon trái/phải và trạng thái `isLoading` với spinner mượt mà.
- `Card.tsx`: Thiết kế khung thẻ hiện đại, hỗ trợ header, footer, padding chuẩn và tùy chọn hiệu ứng hover.
- `Badge.tsx`: Thiết kế dạng pill hoặc bo góc mềm mại, có chấm trạng thái (status dot) tùy chọn cho trạng thái học sinh, trạng thái duyệt điểm.
- `FormField.tsx`: Chuẩn hóa `Input`, `Select`, `Textarea` với nhãn rõ ràng, dấu `*` cho trường bắt buộc, thông báo lỗi kèm icon cảnh báo và trạng thái focus sắc nét.
- `Modal.tsx`: Nền tối mờ (`backdrop-blur-xs`), hiệu ứng xuất hiện mượt mà, phân tách rõ Header (tiêu đề + nút đóng), Body (cuộn độc lập khi nội dung dài) và Footer (cụm nút hành động căn phải).
- `PageHeader.tsx`: Bố cục tiêu đề trang nhất quán gồm Breadcrumb, Tiêu đề chính, Mô tả ngắn gọn và khu vực nút thao tác chính (Primary Actions) bên phải.
- `Pagination.tsx`: Hiển thị thông tin số bản ghi đang xem (ví dụ: *"Hiển thị 1–10 trên tổng số 124 học sinh"*) và cụm nút chuyển trang gọn gàng.
- `TableSkeleton.tsx`, `EmptyState.tsx`, `Alert.tsx`, `ToastContainer.tsx`: Thiết kế lại tinh tế, trực quan, thân thiện với người dùng.

### Giai đoạn 2: Khung ứng dụng & Màn hình xác thực (`AppShell.tsx` & `AuthScreens.tsx`)
- `components/layout/AppShell.tsx`:
  - **Sidebar bên trái:** Logo hệ thống giáo dục chỉn chu, phân nhóm menu điều hướng rõ ràng (Tổng quan, Quản lý đào tạo, Điểm số & Phúc khảo, Báo cáo & Hệ thống). Làm nổi bật mục đang chọn (Active state), hiển thị badge đếm số yêu cầu phúc khảo/sửa điểm đang chờ duyệt. Hỗ trợ thu gọn sidebar trên desktop và mở dạng drawer mượt mà trên thiết bị di động.
  - **Topbar phía trên:** Hiển thị ngữ cảnh năm học/học kỳ hiện tại, thanh tìm kiếm nhanh, và thẻ thông tin người dùng đang đăng nhập kèm vai trò (Admin / Giáo viên / Học sinh) và bộ chuyển đổi tài khoản/vai trò (nếu đang có sẵn trong context) thật trực quan, dễ thao tác.
- `components/screens/AuthScreens.tsx`:
  - Thiết kế bố cục **Split-screen** hiện đại: Một bên là form đăng nhập/khôi phục mật khẩu sắc nét, một bên là khu vực giới thiệu nền tảng giáo dục với đồ họa/thẻ tính năng nổi bật và phần chọn nhanh tài khoản demo theo từng vai trò (nếu có) được trình bày gọn gàng.

### Giai đoạn 3: Các màn hình nghiệp vụ cốt lõi & Dữ liệu mật độ cao
- `GradebookScreen.tsx` (Sổ điểm — Màn hình quan trọng nhất):
  - Thiết kế bảng điểm chuyên nghiệp: Cố định (`sticky left-0`) cột Mã học sinh và Họ tên khi cuộn ngang trên màn hình nhỏ.
  - Phân nhóm tiêu đề cột rõ ràng (Điểm thường xuyên, Giữa kỳ, Cuối kỳ, Điểm trung bình môn, Xếp loại).
  - Ô nhập điểm trực tiếp trên bảng có viền tinh tế, tự động highlight khi đang nhập, cảnh báo trực quan nếu nhập sai thang điểm, và làm nổi bật các điểm dưới trung bình hoặc điểm đang có yêu cầu phúc khảo.
  - Thanh công cụ phía trên cho phép lọc Lớp học, Môn học, Học kỳ và nút Lưu điểm / Xuất dữ liệu nổi bật.
- `StudentListScreen.tsx` & `StudentDetailScreen.tsx`:
  - Danh sách học sinh: Thanh tìm kiếm kết hợp bộ lọc Lớp, Khối, Trạng thái học tập; cột thông tin học sinh kèm Avatar tạo từ chữ cái đầu (Initials Avatar) hài hòa; menu thao tác nhanh trên từng dòng.
  - Chi tiết học sinh: Thiết kế Header hồ sơ học sinh (Avatar lớn, Mã HS, Lớp hiện tại, Trạng thái, Chỉ số GPA/Hạnh kiểm tóm tắt) kết hợp điều hướng dạng Tabs (Thông tin cá nhân, Bảng điểm tổng hợp, Lịch sử thay đổi & Phúc khảo).
- `ApproveRequestsScreen.tsx`, `MyScoreRequestsScreen.tsx` & `ScoreAppealModal.tsx`:
  - Trình bày rõ ràng thông tin yêu cầu sửa điểm/phúc khảo: Học sinh, Môn học, Cột điểm, **So sánh trực quan Điểm cũ sang Điểm mới**, Lý do đề nghị và Trạng thái xử lý.
  - Nút Phê duyệt / Từ chối rõ ràng với xác nhận thao tác an toàn.
- `ReportsScreen.tsx`:
  - Thiết kế các thẻ chỉ số KPI đầu trang (Tổng số học sinh, Số lớp học, Tỷ lệ đạt yêu cầu, Số yêu cầu chờ xử lý) kèm biểu đồ trực quan (phân bố học lực Giỏi/Khá/Trung bình/Yếu, so sánh điểm trung bình giữa các lớp) bằng SVG/CSS sạch sẽ, dễ đọc.

### Giai đoạn 4: Các màn hình quản trị & Modal chức năng
Nâng cấp đồng bộ toàn bộ các màn hình và modal còn lại để không có bất kỳ màn hình nào bị lệch tông:
- **Quản lý đào tạo:** `ClassManagementScreen.tsx`, `SubjectsScreen.tsx`, `AssignmentsScreen.tsx`, `TeacherClassesScreen.tsx`.
- **Quản trị hệ thống:** `UsersScreen.tsx`, `SystemRulesScreen.tsx` (trình bày các quy tắc tính điểm, hệ số, ngưỡng đạt dưới dạng các thẻ cấu hình trực quan dễ chỉnh sửa), `AuditLogsScreen.tsx` (bảng/timeline nhật ký hệ thống có gắn nhãn hành động và người thực hiện rõ ràng), `SharedScreens.tsx`.
- **Các Modal nghiệp vụ:** `AdmitStudentModal.tsx`, `EnrollStudentsModal.tsx`, `ImportExcelModal.tsx` (thiết kế vùng kéo-thả file upload chuyên nghiệp, kèm bảng xem trước dữ liệu hợp lệ/lỗi trực quan), `TransferClassModal.tsx`.

---

## 4. QUY TẮC THỰC THI

1. **Khảo sát trước khi viết code:** Đọc `package.json`, `src/index.css`, `src/types/index.ts`, `src/context/AppContext.tsx` và các file trong `src/components/ui/` trước để nắm trọn vẹn props và dữ liệu hiện có.
2. **Không viết tắt hay bỏ sót:** Viết đầy đủ code hoàn chỉnh cho từng file, tuyệt đối không dùng comment dạng `// ... giữ nguyên code cũ` làm mất tính năng.
3. **Kiểm tra chéo sau khi hoàn tất:** Đảm bảo không có lỗi TypeScript, các import đều chính xác, giao diện hiển thị tốt trên cả màn hình Desktop (`1440px`) và Tablet/Mobile (`768px` / `375px`).