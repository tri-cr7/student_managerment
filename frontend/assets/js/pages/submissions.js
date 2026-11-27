/* ==========================================================================
   SUBMISSIONS — M15 Giáo vụ duyệt & chốt bảng điểm
   ========================================================================== */

import { academicApi } from "../api.js";
import { initShell, pageContent } from "../app.js";
import {
  $,
  $$,
  icon,
  openModal,
  closeModal,
  bindBackdropClose,
  setLoading,
  toastSuccess,
  toastError,
  renderSkeletonRows,
  renderEmptyRow,
  renderPagination,
  escapeHtml,
} from "../ui.js";
import { formatDateTime, statusChip, formatScore } from "../format.js";

const state = {
  page: 1,
  limit: 20,
  status: "PENDING",
  items: [],
  current: null,
};

let container = null;

initShell({
  active: "submissions.html",
  roles: ["ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadSubmissions();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Duyệt bảng điểm</h1>
          <p class="page-header__subtitle">
            Duyệt &amp; chốt các bảng điểm giáo viên đã gửi lên. Sau khi duyệt, bảng điểm
            được khoá và giáo viên phải gửi đơn phúc khảo nếu cần sửa.
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
              <option value="PENDING">Chờ duyệt</option>
              <option value="">Tất cả trạng thái</option>
              <option value="APPROVED">Đã duyệt</option>
              <option value="REJECTED">Từ chối</option>
              <option value="CANCELLED">Đã huỷ</option>
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
              <th>Giáo viên gửi</th>
              <th>Lớp</th>
              <th>Môn học</th>
              <th class="table__cell--center">Số HS</th>
              <th>Ngày gửi</th>
              <th>Trạng thái</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-subs"></tbody>
        </table>
      </div>

      <div class="pagination" id="pagination-subs"></div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  $("#filter-status")?.addEventListener("change", (e) => {
    state.status = e.target.value;
    state.page = 1;
    loadSubmissions();
  });

  $("#btn-refresh")?.addEventListener("click", () => loadSubmissions());

  $("#pagination-subs")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.page);
    loadSubmissions();
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-review"));

  $("#btn-approve")?.addEventListener("click", () => handleDecision("approve"));
  $("#btn-reject")?.addEventListener("click", () => handleDecision("reject"));
}

async function loadSubmissions() {
  const tbody = $("#tbody-subs");
  if (!tbody) return;

  renderSkeletonRows(tbody, 8, 6);

  try {
    const params = { page: state.page, limit: state.limit };
    if (state.status) params.status = state.status;

    const res = await academicApi.submissions(params);
    state.items = res?.items || [];

    if (!state.items.length) {
      renderEmptyRow(
        tbody,
        8,
        state.status === "PENDING"
          ? "Không có bảng điểm nào đang chờ duyệt."
          : "Không có bảng điểm nào phù hợp.",
        `<button type="button" class="btn btn--secondary" id="btn-empty-refresh">
           ${icon("refresh")} Tải lại
         </button>`
      );
      $("#btn-empty-refresh")?.addEventListener("click", loadSubmissions);
      renderPagination($("#pagination-subs"), {
        page: 1,
        pages: 1,
        total: 0,
        limit: state.limit,
        label: "bảng điểm",
      });
      return;
    }

    tbody.innerHTML = state.items.map(renderRow).join("");
    bindRowActions();

    renderPagination($("#pagination-subs"), {
      page: res.page || 1,
      pages: res.pages || 1,
      total: res.total || state.items.length,
      limit: res.per_page || state.limit,
      label: "bảng điểm",
    });
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 8, err?.message || "Không tải được danh sách bảng điểm.");
  }
}

function renderRow(r) {
  const teacher = r.teacher?.full_name || r.teacher_name || "—";
  return `
    <tr>
      <td class="table__cell--mono">#${escapeHtml(r.submission_id ?? r.id ?? "—")}</td>
      <td class="table__cell--name">${escapeHtml(teacher)}</td>
      <td>${escapeHtml(r.class_name || "—")}</td>
      <td>${escapeHtml(r.subject_name || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(r.total_students ?? "—")}</td>
      <td>${escapeHtml(formatDateTime(r.submitted_at))}</td>
      <td>${statusChip(r.status)}</td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--secondary btn--sm"
                  data-action="view" data-id="${r.submission_id ?? r.id}">
            ${icon("eye")} Xem &amp; duyệt
          </button>
        </div>
      </td>
    </tr>
  `;
}

function bindRowActions() {
  $$("#tbody-subs [data-action='view']").forEach((btn) => {
    btn.addEventListener("click", () => openReview(Number(btn.dataset.id)));
  });
}

async function openReview(id) {
  const dialog = $("#modal-review");
  const tbody = $("#review-tbody");
  tbody.innerHTML = `<tr><td colspan="6" style="padding:32px">
    <div class="skeleton skeleton--text"></div></td></tr>`;
  $("#review-note").value = "";
  openModal(dialog);

  try {
    const r = await academicApi.submission(id);
    state.current = r;
    renderReview(r);
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 6, err?.message || "Không tải được chi tiết bảng điểm.");
  }
}

function renderReview(r) {
  const teacher = r.teacher?.full_name || "—";
  $("#review-title").textContent = `Bảng điểm #${r.submission_id ?? r.id}`;
  $("#review-subtitle").textContent = `${r.class_name || ""} — ${r.subject_name || ""} · ${
    r.semester_name || ""
  } · ${r.academic_year || ""}`;

  $("#review-meta").innerHTML = `
    <div class="row row--wrap" style="gap:8px">
      ${statusChip(r.status)}
      <span class="chip chip--neutral">Giáo viên: ${escapeHtml(teacher)}</span>
      <span class="chip chip--neutral">Học sinh: ${escapeHtml(r.total_students ?? 0)}</span>
      <span class="chip chip--neutral">Ô điểm: ${escapeHtml(r.total_scores ?? 0)}</span>
      <span class="chip chip--neutral">Gửi lúc: ${escapeHtml(formatDateTime(r.submitted_at))}</span>
    </div>
    ${
      r.note
        ? `<div class="alert alert--info" style="margin-top:12px">
             <span class="alert__icon">${icon("info")}</span>
             <div class="alert__body">
               <div class="alert__title">Ghi chú từ giáo viên</div>
               <div class="alert__message">${escapeHtml(r.note)}</div>
             </div>
           </div>`
        : ""
    }
  `;

  const list = r.draft_score_list || [];
  $("#review-tbody").innerHTML = list.length
    ? list.map(renderScoreRow).join("")
    : `<tr><td colspan="6" class="table__empty-cell">
         <div class="empty-state">
           <span class="empty-state__icon">${icon("inbox")}</span>
           <div class="empty-state__title">Không có điểm tạm</div>
         </div>
       </td></tr>`;

  const pending = String(r.status).toUpperCase() === "PENDING";
  $("#btn-approve").disabled = !pending;
  $("#btn-reject").disabled = !pending;
  $("#review-note-hint").textContent = pending
    ? "Khi duyệt: điểm tạm chuyển thành điểm chính thức và bảng điểm bị khoá. Khi từ chối: bắt buộc nhập lý do."
    : "Bảng điểm này đã được xử lý nên không thể duyệt/từ chối lại.";
}

function renderScoreRow(s) {
  const arr = (v) => (Array.isArray(v) ? v : []).map((x) => formatScore(x) ?? "–").join(" · ");
  return `
    <tr>
      <td class="table__cell--mono">${escapeHtml(s.student_code || "—")}</td>
      <td class="table__cell--name">${escapeHtml(s.full_name || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(arr(s.scores_15m) || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(arr(s.scores_45m) || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(formatScore(s.score_final) ?? "–")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(formatScore(s.average_score) ?? "–")}</td>
    </tr>
  `;
}

async function handleDecision(action) {
  if (!state.current) return;

  const id = state.current.submission_id ?? state.current.id;
  const note = $("#review-note").value.trim();
  const btn = action === "approve" ? $("#btn-approve") : $("#btn-reject");

  if (action === "reject" && !note) {
    toastError("Vui lòng nhập lý do từ chối.");
    $("#review-note").focus();
    return;
  }

  const confirmed = await confirmAction(action, state.current, note);
  if (!confirmed) return;

  setLoading(btn, true, action === "approve" ? "Đang duyệt..." : "Đang từ chối...");

  try {
    if (action === "approve") {
      await academicApi.approveSubmission(id, { review_note: note });
      toastSuccess("Đã duyệt & chốt bảng điểm. Bảng điểm đã khoá.");
    } else {
      await academicApi.rejectSubmission(id, { review_note: note });
      toastSuccess("Đã từ chối bảng điểm. Giáo viên có thể sửa và gửi lại.");
    }
    closeModal($("#modal-review"));
    await loadSubmissions();
  } catch (err) {
    toastError(err?.message || "Không thực hiện được thao tác.");
  } finally {
    setLoading(btn, false);
  }
}

async function confirmAction(action, r, note) {
  const { confirmDialog } = await import("../ui.js");
  const title = action === "approve" ? "Duyệt & chốt bảng điểm" : "Từ chối bảng điểm";
  const message =
    action === "approve"
      ? `Duyệt bảng điểm ${r.class_name} — ${r.subject_name}?`
      : `Từ chối bảng điểm ${r.class_name} — ${r.subject_name}?`;
  const detail =
    action === "approve"
      ? "Điểm tạm sẽ trở thành điểm chính thức và bảng điểm sẽ bị khoá. Giáo viên không thể sửa trực tiếp nữa."
      : `Lý do: ${note || "(không có)"}`;

  return confirmDialog({
    title,
    message,
    detail,
    confirmText: action === "approve" ? "Duyệt & chốt" : "Từ chối",
    danger: action === "reject",
  });
}
