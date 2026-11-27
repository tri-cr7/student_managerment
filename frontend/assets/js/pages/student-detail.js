/* ==========================================================================
   STUDENT DETAIL — M6 hồ sơ chi tiết học sinh (thông tin + bảng điểm + in)
   ========================================================================== */

import { studentApi, TOKEN } from "../api.js";
import { initShell, ctx, pageContent, renderPageError } from "../app.js";
import { $, icon, toastError, escapeHtml } from "../ui.js";
import {
  formatDate,
  formatGender,
  initials,
  statusChip,
  scoreColumnLabel,
  averageTone,
  formatScore,
} from "../format.js";

let container = null;
let studentId = null;

initShell({
  active: "students.html",
  roles: ["STAFF", "ACADEMIC", "TEACHER"],
}).then(async () => {
  container = pageContent();

  const params = new URLSearchParams(location.search);
  studentId = Number(params.get("id"));

  if (!studentId) {
    renderPageError(container, { message: "Thiếu mã học sinh trong đường dẫn." });
    return;
  }

  renderSkeleton();
  await loadDetail();
});

function renderSkeleton() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div style="flex:1;max-width:520px">
          <div class="skeleton skeleton--text" style="height:24px;width:60%"></div>
          <div class="skeleton skeleton--text" style="height:14px;width:40%;margin-top:10px"></div>
        </div>
      </div>
    </header>
    <div class="card">
      <div class="card__body">
        <div class="skeleton skeleton--text" style="height:80px"></div>
      </div>
    </div>
  `;
}

async function loadDetail() {
  try {
    const [student, scoresRes] = await Promise.all([
      studentApi.detail(studentId),
      studentApi.scores(studentId).catch(() => null),
    ]);
    renderDetail(student, scoresRes);
  } catch (err) {
    renderPageError(container, err);
  }
}

function renderDetail(s, scoresRes) {
  const rows = scoresRes?.scores || [];

  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__breadcrumb">
        <nav class="breadcrumb" aria-label="Breadcrumb">
          <a href="students.html">Danh sách học sinh</a>
          <span class="breadcrumb__sep">/</span>
          <span class="breadcrumb__current">${escapeHtml(s.full_name || "Hồ sơ")}</span>
        </nav>
      </div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">${escapeHtml(s.full_name || "Hồ sơ học sinh")}</h1>
          <p class="page-header__subtitle">
            Mã học sinh <span class="t-mono">${escapeHtml(s.student_code || "—")}</span>
            · Hồ sơ chi tiết & kết quả học tập
          </p>
        </div>
        <div class="page-header__actions">
          <a class="btn btn--secondary" href="students.html">
            ${icon("chevronLeft")} Quay lại
          </a>
          <a class="btn btn--secondary" id="btn-print" target="_blank" rel="noopener">
            ${icon("printer")} In hồ sơ
          </a>
        </div>
      </div>
    </header>

    <div class="layout-split">
      <div class="stack-4">
        <div class="card">
          <div class="card__header">
            <div>
              <div class="card__title">Thông tin cá nhân</div>
              <div class="card__subtitle">Thông tin hồ sơ được lưu trong hệ thống.</div>
            </div>
            ${statusChip(s.status)}
          </div>
          <div class="card__body">
            <div class="kv-list">
              <div class="kv-list__key">Họ và tên</div>
              <div class="kv-list__value">${escapeHtml(s.full_name || "—")}</div>

              <div class="kv-list__key">Mã học sinh</div>
              <div class="kv-list__value t-mono">${escapeHtml(s.student_code || "—")}</div>

              <div class="kv-list__key">Giới tính</div>
              <div class="kv-list__value">${escapeHtml(formatGender(s.gender))}</div>

              <div class="kv-list__key">Ngày sinh</div>
              <div class="kv-list__value">${escapeHtml(formatDate(s.date_of_birth))}</div>

              <div class="kv-list__key">Số điện thoại</div>
              <div class="kv-list__value t-mono">${escapeHtml(s.phone || "—")}</div>

              <div class="kv-list__key">Email</div>
              <div class="kv-list__value">${escapeHtml(s.email || "—")}</div>

              <div class="kv-list__key">Địa chỉ</div>
              <div class="kv-list__value">${escapeHtml(s.address || "—")}</div>

              <div class="kv-list__key">CMND/CCCD</div>
              <div class="kv-list__value t-mono">${escapeHtml(s.citizen_id || "—")}</div>

              <div class="kv-list__key">Người thân</div>
              <div class="kv-list__value">${escapeHtml(s.parent_name || "—")}</div>

              <div class="kv-list__key">SĐT người thân</div>
              <div class="kv-list__value t-mono">${escapeHtml(s.parent_phone || "—")}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card__header">
            <div>
              <div class="card__title">Kết quả học tập</div>
              <div class="card__subtitle">Chỉ hiển thị điểm chính thức đã được Giáo vụ duyệt.</div>
            </div>
            <span class="chip chip--neutral">${rows.length} môn</span>
          </div>
          <div class="card__body card__body--flush">
            ${
              rows.length
                ? `<div class="table-wrap">
                     <table class="table">
                       <thead class="table__head">
                         <tr>
                           <th>Môn học</th>
                           <th>Học kỳ</th>
                           <th>Năm học</th>
                           <th class="table__cell--center">ĐTB</th>
                           <th class="table__cell--center">Kết quả</th>
                         </tr>
                       </thead>
                       <tbody>${rows.map(renderScoreRow).join("")}</tbody>
                     </table>
                   </div>`
                : `<div class="empty-state">
                     <span class="empty-state__icon">${icon("gradebook")}</span>
                     <div class="empty-state__title">Chưa có điểm chính thức</div>
                     <div class="empty-state__message">
                       Học sinh chưa có kết quả học tập nào được công bố.
                     </div>
                   </div>`
            }
          </div>
        </div>
      </div>

      <div class="stack-4">
        <div class="card">
          <div class="card__body">
            <div class="profile-head">
              <span class="avatar avatar--96">${escapeHtml(initials(s.full_name))}</span>
              <div class="profile-head__meta">
                <div class="t-title">${escapeHtml(s.full_name || "—")}</div>
                <div class="t-caption t-mono">${escapeHtml(s.student_code || "")}</div>
                <div style="margin-top:6px">${statusChip(s.status)}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card__header">
            <div class="card__title">Tóm tắt</div>
          </div>
          <div class="card__body">
            <div class="kv-list">
              <div class="kv-list__key">Môn đã có điểm</div>
              <div class="kv-list__value">${rows.length}</div>
              <div class="kv-list__key">Môn đạt</div>
              <div class="kv-list__value">${rows.filter((r) => r.is_passed !== false).length}</div>
              <div class="kv-list__key">Môn không đạt</div>
              <div class="kv-list__value">${rows.filter((r) => r.is_passed === false).length}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  const printBtn = $("#btn-print");
  if (printBtn) {
    printBtn.href = studentApi.printUrl(studentId, "pdf");
  }
}

function renderScoreRow(r) {
  const avg = r.average_score;
  const tone = averageTone(avg, ctx.passingScore);
  const passed = r.is_passed !== false;
  const subject = r.subject_name || r.subject_code || "—";
  const semester = r.semester_name || "—";
  const year = r.academic_year || r.academic_year_name || "—";

  return `
    <tr>
      <td class="table__cell--name">${escapeHtml(subject)}</td>
      <td>${escapeHtml(semester)}</td>
      <td class="t-mono">${escapeHtml(year)}</td>
      <td class="table__cell--center">
        <span class="t-mono gradebook__avg gradebook__avg--${tone}">
          ${avg === null || avg === undefined ? "–" : escapeHtml(formatScore(avg) ?? "–")}
        </span>
      </td>
      <td class="table__cell--center">
        ${
          passed
            ? `<span class="chip chip--success"><span class="chip__dot"></span>Đạt</span>`
            : `<span class="chip chip--danger"><span class="chip__dot"></span>Chưa đạt</span>`
        }
      </td>
    </tr>
  `;
}
