/* ==========================================================================
   FORMAT — Định dạng dữ liệu hiển thị (tiếng Việt, số, ngày, trạng thái)
   ========================================================================== */
import {
  AUDIT_ACTION_LABELS,
  AUDIT_DETAIL_LABELS,
  AUDIT_VALUE_LABELS,
} from "./audit-labels.js";

const MONTHS = [
  "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
  "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
];

/* Ngày ISO "2010-05-14" → "14/05/2010" */
export function formatDate(iso) {
  if (!iso) return "—";
  const s = String(iso).slice(0, 10);
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return s;
  return `${m[3]}/${m[2]}/${m[1]}`;
}

/* Ngày ISO kèm giờ → "14/05/2010 08:30" */
export function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return formatDate(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}

/* "2010-05-14" → "2010-05-14" cho input date */
export function toDateInput(iso) {
  if (!iso) return "";
  return String(iso).slice(0, 10);
}

/* Số thập phân: 8.50 → "8.5" */
export function formatScore(value, digits = 2) {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n)) return null;
  return Number(n.toFixed(digits)).toString();
}

/* Số nguyên có dấu phân cách nghìn */
export function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("vi-VN");
}

/* Phần trăm: 0.856 → "85.6%" */
export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return `${Number(n.toFixed(digits))}%`;
}

/* Chữ cái đầu của họ tên làm avatar: "Nguyễn Văn An" → "NA" */
export function initials(fullName) {
  if (!fullName) return "?";
  const parts = String(fullName).trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/* Chuẩn hoá giới tính từ DB → Nam/Nữ/Khác */
export function formatGender(value) {
  const v = String(value || "").trim().toUpperCase();
  if (!v) return "—";
  if (v === "NAM" || v === "M" || v === "MALE") return "Nam";
  if (v === "NU" || v === "F" || v === "FEMALE") return "Nữ";
  if (v === "KHAC" || v === "OTHER") return "Khác";
  return value;
}

/* ------------------------------------------------------------------ */
/* Mapping trạng thái → nhãn + màu chip                                */
/* ------------------------------------------------------------------ */
const STATUS_MAP = {
  DANG_HOC: { label: "Đang học", tone: "success" },
  THOI_HOC: { label: "Thôi học", tone: "info" },
  CHUYEN_TRUONG: { label: "Chuyển trường", tone: "warning" },
  TOT_NGHIEP: { label: "Tốt nghiệp", tone: "danger" },
  DA_CHUYEN: { label: "Đã chuyển", tone: "neutral" },
  PENDING: { label: "Chờ duyệt", tone: "warning" },
  APPROVED: { label: "Đã duyệt", tone: "success" },
  REJECTED: { label: "Từ chối", tone: "danger" },
  PARTIALLY_APPROVED: { label: "Duyệt một phần", tone: "warning" },
  CANCELLED: { label: "Đã huỷ", tone: "neutral" },
  DANG_DUNG: { label: "Đang dùng", tone: "success" },
  NGUNG_DUNG: { label: "Ngừng dùng", tone: "neutral" },
  STAFF: { label: "Nhân viên", tone: "info" },
  TEACHER: { label: "Giáo viên", tone: "neutral" },
  ACADEMIC: { label: "Giáo vụ", tone: "primary" },
  MO: { label: "Mở", tone: "success" },
  DA_KHOA: { label: "Đã khoá", tone: "neutral" },
  BGD_NHAP: { label: "Bản nháp", tone: "neutral" },
  CHINH_THUC: { label: "Chính thức", tone: "success" },
};

export function statusInfo(value, fallbackLabel) {
  const key = String(value || "").trim().toUpperCase();
  if (STATUS_MAP[key]) return STATUS_MAP[key];
  return { label: fallbackLabel || value || "—", tone: "neutral" };
}

/* Render chip trạng thái (dot + chữ — không chỉ dựa vào màu) */
export function statusChip(value, fallbackLabel) {
  const info = statusInfo(value, fallbackLabel);
  return `<span class="chip chip--${info.tone}"><span class="chip__dot"></span>${escapeHtml(
    info.label
  )}</span>`;
}

/* ------------------------------------------------------------------ */
/* Escape HTML — chống XSS khi render dữ liệu từ API                   */
/* ------------------------------------------------------------------ */
export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/* ------------------------------------------------------------------ */
/* Tên cột điểm: score_15m_1 → 15p.1                                   */
/* ------------------------------------------------------------------ */
export const SCORE_LABELS = {
  score_15m_1: "15p.1",
  score_15m_2: "15p.2",
  score_15m_3: "15p.3",
  score_15m_4: "15p.4",
  score_15m_5: "15p.5",
  score_45m_1: "1T.1",
  score_45m_2: "1T.2",
  score_45m_3: "1T.3",
  score_final: "Thi",
};

export function scoreColumnLabel(column) {
  return SCORE_LABELS[column] || column;
}

/* Màu ĐTB theo ngưỡng đạt */
export function averageTone(average, passingScore = 5.0) {
  if (average === null || average === undefined) return "none";
  const n = Number(average);
  if (Number.isNaN(n)) return "none";
  if (n < Number(passingScore)) return "fail";
  if (n < 8.0) return "mid";
  return "pass";
}

/* ------------------------------------------------------------------ */
/* Nhãn tiếng Việt cho audit log                                        */
/* DB lưu mã tiếng Anh; toàn bộ việc hiển thị nằm ở tầng frontend.  */
/* ------------------------------------------------------------------ */
/* Mã hành động → nhãn tiếng Việt */
export function auditActionLabel(action) {
  if (!action) return "—";
  return AUDIT_ACTION_LABELS[action] || action;
}

/* Key của `details` → nhãn tiếng Việt */
export function auditDetailKeyLabel(key) {
  return AUDIT_DETAIL_LABELS[key] || key;
}

/* Giá trị enum / boolean → nhãn tiếng Việt */
export function auditDetailValueLabel(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  const s = String(value);
  return AUDIT_VALUE_LABELS[s.toUpperCase()] || s;
}

export { MONTHS };
