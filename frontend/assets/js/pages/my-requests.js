/* ==========================================================================
   MY REQUESTS — M14 đơn phúc khảo do giáo viên hiện tại đã nộp
   ========================================================================== */

import { teacherApi, academicApi } from "../api.js";
import { initShell, pageContent, renderPageError } from "../app.js";
import {
  $,
  $$,
  icon,
  openModal,
  closeModal,
  bindBackdropClose,
  renderSkeletonRows,
  renderEmptyRow,
  renderPagination,
  escapeHtml,
} from "../ui.js";
import {
  formatDateTime,
  statusChip,
  scoreColumnLabel,
  formatScore,
} from "../format.js";

const state = {
  page: 1,
  limit: 20,
  status: "",
  items: [],
};

let container = null;

initShell({
  active: "my-requests.html",
  roles: ["TEACHER", "ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadRequests();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Đơn phúc khảo của tôi</h1>
          <p class="page-header__subtitle">
            Theo dõi trạng thái các đơn yêu cầu sửa điểm đã gửi tới Giáo vụ.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--ghost btn--icon" id="btn-refresh"
                  aria-label="Tải lại" title="Tải lại">${icon("refresh")}</button>
        </div>
      </div>
    </header>

    <div class="card">
      <div class="card__body card__body--tight">
        <div class="toolbar">
          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-status"
                    aria-label="Lọc theo trạng thái">
              <option value="">Tất cả trạng thái</option>
              <option value="PENDING">Chờ duyệt</option>
              <option value="APPROVED">Đã duyệt</option>
              <option value="PARTIALLY_APPROVED">Duyệt một phần</option>
              <option value="REJECTED">Từ chối</option>
            </select>
            <span class="field__chevron">▾</span>
          </div>
          <div class="toolbar__spacer"></div>
        </div>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead class="table__head">
            <tr>
              <th>Mã đơn</th>
              <th>Lớp</th>
              <th>Môn học</th>
              <th class="table__cell--center">Số ô</th>
              <th>Ngày gửi</th>
              <th>Trạng thái</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-requests"></tbody>
        </table>
      </div>

      <div class="pagination" id="pagination-requests"></div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  $("#filter-status")?.addEventListener("change", (e) => {
    state.status = e.target.value;
    state.page = 1;
    loadRequests();
  });

  $("#btn-refresh")?.addEventListener("click", () => loadRequests());

  $("#pagination-requests")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.page);
    loadRequests();
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-detail"));
}

async function loadRequests() {
  const tbody = $("#tbody-requests");
  if (!tbody) return;

  renderSkeletonRows(tbody, 7, 6);

  try {
    const params = { page: state.page, limit: state.limit };
    if (state.status) params.status = state.status;

    const res = await teacherApi.myChangeRequests();
    const raw = res?.items || res?.data || [];
    const all = Array.isArray(raw) ? raw : [];

    /* Backend đôi khi bọc trong { data: {...} } — chuẩn hoá lại */
    const list = Array.isArray(res?.items)
      ? res.items
      : Array.isArray(res?.data)
      ? res.data
      : all;

    const filtered = state.status
      ? list.filter((r) => String(r.status).toUpperCase() === state.status)
      : list;

    state.items = filtered;

    if (!filtered.length) {
      renderEmptyRow(
        tbody,
        7,
        state.status
          ? "Không có đơn nào ở trạng thái đã chọn."
          : "Bạn chưa gửi đơn phúc khảo nào.",
        `<a class="btn btn--secondary" href="teacher-classes.html">Quay lại lớp phụ trách</a>`
      );
      renderPagination($("#pagination-requests"), {
        page: 1,
        pages: 1,
        total: 0,
        limit: state.limit,
        label: "đơn",
      });
      return;
    }

    tbody.innerHTML = filtered.map(renderRow).join("");
    bindRowActions();

    renderPagination($("#pagination-requests"), {
      page: res?.page || 1,
      pages: res?.pages || 1,
      total: res?.total ?? filtered.length,
      limit: res?.per_page || state.limit,
      label: "đơn",
    });
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 7, err?.message || "Không tải được danh sách đơn phúc khảo.");
  }
}

function renderRow(r) {
  const details = r.details || [];
  const count = r.total_changes ?? details.length;
  const batch = r.is_batch ? `<span class="chip chip--neutral">Lô</span>` : "";

  return `
    <tr>
      <td class="table__cell--mono">#${escapeHtml(r.request_id ?? r.id ?? "—")}</td>
      <td class="table__cell--name">${escapeHtml(r.class_name || "—")}</td>
      <td>${escapeHtml(r.subject_name || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(count)}</td>
      <td>${escapeHtml(formatDateTime(r.created_at))}</td>
      <td>${statusChip(r.status)} ${batch}</td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--secondary btn--sm"
                  data-action="detail" data-id="${r.request_id ?? r.id}">
            ${icon("eye")} Xem chi tiết
          </button>
        </div>
      </td>
    </tr>
  `;
}

function bindRowActions() {
  $$("#tbody-requests [data-action='detail']").forEach((btn) => {
    btn.addEventListener("click", () => openDetail(Number(btn.dataset.id)));
  });
}

async function openDetail(id) {
  const dialog = $("#modal-detail");
  const tbody = $("#detail-tbody");
  tbody.innerHTML = `<tr><td colspan="6" style="padding:32px">
    <div class="skeleton skeleton--text"></div></td></tr>`;
  openModal(dialog);

  try {
    const detail = await academicApi.changeRequest(id);
    renderDetail(detail);
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 6, err?.message || "Không tải được chi tiết đơn.");
  }
}

function renderDetail(r) {
  $("#detail-title").textContent = `Đơn phúc khảo #${r.request_id ?? r.id}`;
  $("#detail-subtitle").textContent = `${r.class_name || ""} — ${r.subject_name || ""} · ${
    r.semester_name || ""
  }`;

  const summary = r.summary || {};
  $("#detail-meta").innerHTML = `
    <div class="alert alert--neutral">
      <span class="alert__icon">${icon("info")}</span>
      <div class="alert__body">
        <div class="alert__title">Lý do gửi đơn</div>
        <div class="alert__message">${escapeHtml(r.reason || "—")}</div>
      </div>
    </div>
    <div class="row row--wrap" style="gap:8px;margin-top:12px">
      ${statusChip(r.status)}
      <span class="chip chip--neutral">Tổng ô: ${escapeHtml(summary.total ?? r.total_changes ?? 0)}</span>
      <span class="chip chip--warning">Chờ duyệt: ${escapeHtml(summary.pending ?? 0)}</span>
      <span class="chip chip--success">Đã duyệt: ${escapeHtml(summary.approved ?? 0)}</span>
      <span class="chip chip--danger">Từ chối: ${escapeHtml(summary.rejected ?? 0)}</span>
    </div>
  `;

  const details = r.details || [];
  $("#detail-tbody").innerHTML = details.length
    ? details.map(renderDiffRow).join("")
    : `<tr><td colspan="6" class="table__empty-cell">
         <div class="empty-state">
           <span class="empty-state__icon">${icon("inbox")}</span>
           <div class="empty-state__title">Không có ô điểm nào</div>
         </div>
       </td></tr>`;
}

function renderDiffRow(d) {
  const oldV = Number(d.old_value);
  const newV = Number(d.new_value);
  let cls = "diff-same";
  if (!Number.isNaN(oldV) && !Number.isNaN(newV)) {
    if (newV > oldV) cls = "diff-up";
    else if (newV < oldV) cls = "diff-down";
  }

  const studentName = d.student_name || d.full_name || `HS #${d.student_id ?? "—"}`;

  return `
    <tr>
      <td class="table__cell--name">${escapeHtml(studentName)}</td>
      <td class="t-mono">${escapeHtml(scoreColumnLabel(d.score_column))}</td>
      <td class="table__cell--center t-mono ${cls}">
        ${escapeHtml(formatScore(d.old_value) ?? "–")}
      </td>
      <td class="table__cell--center t-mono ${cls}">
        ${escapeHtml(formatScore(d.new_value) ?? "–")}
      </td>
      <td class="t-caption">${escapeHtml(d.reason || d.note || "—")}</td>
      <td class="table__cell--center">${statusChip(d.status)}</td>
    </tr>
  `;
}
