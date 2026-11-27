/* ==========================================================================
   APPROVALS — M16 Giáo vụ phê duyệt đơn phúc khảo (duyệt từng ô điểm)
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
import { formatDateTime, statusChip, scoreColumnLabel, formatScore } from "../format.js";

const state = {
  page: 1,
  limit: 20,
  status: "PENDING",
  items: [],
  current: null,
  /* detail_id → { action: "APPROVE"|"REJECT", note: string } */
  decisions: new Map(),
};

let container = null;

initShell({
  active: "approvals.html",
  roles: ["ACADEMIC"],
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
          <h1 class="page-header__title">Phê duyệt phúc khảo</h1>
          <p class="page-header__subtitle">
            Xét duyệt các đơn yêu cầu sửa điểm. Quyết định được áp dụng từng ô điểm
            trong một giao dịch duy nhất và điểm trung bình được tính lại tự động.
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
              <th>Giáo viên gửi</th>
              <th>Lớp</th>
              <th>Môn học</th>
              <th class="table__cell--center">Số ô</th>
              <th>Ngày gửi</th>
              <th>Trạng thái</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-approvals"></tbody>
        </table>
      </div>

      <div class="pagination" id="pagination-approvals"></div>
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

  $("#pagination-approvals")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.page);
    loadRequests();
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-approval"));

  $("#btn-approve-all")?.addEventListener("click", () => setAllDecisions("APPROVE"));
  $("#btn-reject-all")?.addEventListener("click", () => setAllDecisions("REJECT"));
  $("#btn-submit-decisions")?.addEventListener("click", submitDecisions);
}

async function loadRequests() {
  const tbody = $("#tbody-approvals");
  if (!tbody) return;

  renderSkeletonRows(tbody, 8, 6);

  try {
    const params = { page: state.page, limit: state.limit };
    if (state.status) params.status = state.status;

    const res = await academicApi.changeRequests(params);
    state.items = res?.items || [];

    if (!state.items.length) {
      renderEmptyRow(
        tbody,
        8,
        state.status === "PENDING"
          ? "Không có đơn phúc khảo nào đang chờ duyệt."
          : "Không có đơn phúc khảo nào phù hợp."
      );
      renderPagination($("#pagination-approvals"), {
        page: 1,
        pages: 1,
        total: 0,
        limit: state.limit,
        label: "đơn",
      });
      return;
    }

    tbody.innerHTML = state.items.map(renderRow).join("");
    bindRowActions();

    renderPagination($("#pagination-approvals"), {
      page: res.page || 1,
      pages: res.pages || 1,
      total: res.total || state.items.length,
      limit: res.per_page || state.limit,
      label: "đơn",
    });
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 8, err?.message || "Không tải được danh sách đơn phúc khảo.");
  }
}

function renderRow(r) {
  const teacher = r.teacher?.full_name || "—";
  const count = r.total_changes ?? (r.details || []).length;
  return `
    <tr>
      <td class="table__cell--mono">#${escapeHtml(r.request_id ?? r.id ?? "—")}</td>
      <td class="table__cell--name">${escapeHtml(teacher)}</td>
      <td>${escapeHtml(r.class_name || "—")}</td>
      <td>${escapeHtml(r.subject_name || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(count)}</td>
      <td>${escapeHtml(formatDateTime(r.created_at))}</td>
      <td>${statusChip(r.status)}</td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--secondary btn--sm"
                  data-action="review" data-id="${r.request_id ?? r.id}">
            ${icon("approval")} Duyệt đơn
          </button>
        </div>
      </td>
    </tr>
  `;
}

function bindRowActions() {
  $$("#tbody-approvals [data-action='review']").forEach((btn) => {
    btn.addEventListener("click", () => openApproval(Number(btn.dataset.id)));
  });
}

async function openApproval(id) {
  const dialog = $("#modal-approval");
  const tbody = $("#ap-tbody");
  tbody.innerHTML = `<tr><td colspan="6" style="padding:32px">
    <div class="skeleton skeleton--text"></div></td></tr>`;
  $("#ap-note").value = "";
  state.decisions = new Map();
  openModal(dialog);

  try {
    const diff = await academicApi.changeDiff(id);
    state.current = diff;
    renderApproval(diff);
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 6, err?.message || "Không tải được bảng so sánh điểm.");
  }
}

function renderApproval(diff) {
  const summary = diff.summary || {};
  $("#ap-title").textContent = `Đơn phúc khảo #${diff.request_id}`;
  $("#ap-subtitle").textContent = diff.is_batch
    ? "Đơn lô — nhiều ô điểm, quyết định từng ô."
    : "Đơn đơn lẻ — 1 ô điểm.";

  $("#ap-meta").innerHTML = `
    <div class="row row--wrap" style="gap:8px">
      <span class="chip chip--neutral">Tổng ô: ${escapeHtml(summary.total ?? 0)}</span>
      <span class="chip chip--warning">Chờ duyệt: ${escapeHtml(summary.pending ?? 0)}</span>
      <span class="chip chip--success">Đã duyệt: ${escapeHtml(summary.approved ?? 0)}</span>
      <span class="chip chip--danger">Từ chối: ${escapeHtml(summary.rejected ?? 0)}</span>
    </div>
    ${
      diff.attachment?.attachment_name
        ? `<div class="alert alert--info" style="margin-top:12px">
             <span class="alert__icon">${icon("file")}</span>
             <div class="alert__body">
               <div class="alert__title">File đính kèm</div>
               <div class="alert__message">${escapeHtml(diff.attachment.attachment_name)}</div>
             </div>
           </div>`
        : ""
    }
  `;

  const changes = diff.changes || [];
  $("#ap-tbody").innerHTML = changes.length
    ? changes.map(renderChangeRow).join("")
    : `<tr><td colspan="6" class="table__empty-cell">
         <div class="empty-state">
           <span class="empty-state__icon">${icon("inbox")}</span>
           <div class="empty-state__title">Đơn không có ô điểm nào</div>
         </div>
       </td></tr>`;

  const editable = changes.some((c) => String(c.status).toUpperCase() === "PENDING");
  $("#btn-submit-decisions").disabled = !editable;
  $("#btn-approve-all").disabled = !editable;
  $("#btn-reject-all").disabled = !editable;

  bindDecisionRows();
}

function renderChangeRow(c) {
  const oldV = Number(c.old_value);
  const newV = Number(c.new_value);
  let cls = "diff-same";
  if (!Number.isNaN(oldV) && !Number.isNaN(newV)) {
    if (newV > oldV) cls = "diff-up";
    else if (newV < oldV) cls = "diff-down";
  }

  const pending = String(c.status).toUpperCase() === "PENDING";
  const decision = state.decisions.get(c.detail_id);
  const checked = decision ? decision.action : "APPROVE";

  const studentName = c.student_name || `HS #${c.student_id ?? "—"}`;

  return `
    <tr data-detail="${c.detail_id}">
      <td class="table__cell--name">${escapeHtml(studentName)}</td>
      <td class="t-mono">${escapeHtml(scoreColumnLabel(c.score_column))}</td>
      <td class="table__cell--center t-mono ${cls}">
        ${escapeHtml(formatScore(c.old_value) ?? "–")}
      </td>
      <td class="table__cell--center t-mono ${cls}">
        ${escapeHtml(formatScore(c.new_value) ?? "–")}
      </td>
      <td class="t-caption">${escapeHtml(c.reason || c.note || "—")}</td>
      <td>
        ${
          pending
            ? `<div class="stack-1">
                 <label class="field__checkbox">
                   <input type="radio" name="dec-${c.detail_id}" value="APPROVE"
                          ${checked === "APPROVE" ? "checked" : ""}
                          data-act="approve" data-detail="${c.detail_id}">
                   Duyệt
                 </label>
                 <label class="field__checkbox">
                   <input type="radio" name="dec-${c.detail_id}" value="REJECT"
                          ${checked === "REJECT" ? "checked" : ""}
                          data-act="reject" data-detail="${c.detail_id}">
                   Từ chối
                 </label>
                 <input class="field__input hidden" data-note-input="${c.detail_id}"
                        placeholder="Lý do từ chối (bắt buộc)">
               </div>`
            : statusChip(c.status)
        }
      </td>
    </tr>
  `;
}

function bindDecisionRows() {
  $$("#ap-tbody input[type='radio']").forEach((radio) => {
    radio.addEventListener("change", () => {
      const detailId = Number(radio.dataset.detail);
      const action = radio.dataset.act;
      const noteInput = $(`[data-note-input="${detailId}"]`);

      const prev = state.decisions.get(detailId) || {};
      state.decisions.set(detailId, {
        action,
        note: action === "REJECT" ? prev.note || "" : "",
      });

      if (noteInput) noteInput.classList.toggle("hidden", action !== "REJECT");
    });
  });

  $$("#ap-tbody [data-note-input]").forEach((input) => {
    input.addEventListener("input", () => {
      const detailId = Number(input.dataset.noteInput);
      const prev = state.decisions.get(detailId) || { action: "REJECT" };
      state.decisions.set(detailId, { ...prev, note: input.value });
    });
  });
}

function setAllDecisions(action) {
  const changes = state.current?.changes || [];
  changes.forEach((c) => {
    if (String(c.status).toUpperCase() !== "PENDING") return;
    state.decisions.set(c.detail_id, { action, note: action === "REJECT" ? "" : "" });
    const radio = $(`input[name="dec-${c.detail_id}"][value="${action}"]`);
    if (radio) radio.checked = true;
    const noteInput = $(`[data-note-input="${c.detail_id}"]`);
    if (noteInput) noteInput.classList.toggle("hidden", action !== "REJECT");
  });
  toastSuccess(
    action === "APPROVE"
      ? "Đã chọn duyệt cho tất cả ô đang chờ."
      : "Đã chọn từ chối cho tất cả ô đang chờ. Nhập lý do cho từng ô."
  );
}

async function submitDecisions() {
  const changes = (state.current?.changes || []).filter(
    (c) => String(c.status).toUpperCase() === "PENDING"
  );

  if (!changes.length) {
    toastError("Đơn này không còn ô điểm nào chờ duyệt.");
    return;
  }

  const decisions = [];
  for (const c of changes) {
    const d = state.decisions.get(c.detail_id);
    if (!d) {
      toastError("Vui lòng chọn Duyệt hoặc Từ chối cho tất cả các ô điểm.");
      return;
    }
    if (d.action === "REJECT" && !(d.note || "").trim()) {
      toastError("Ô bị từ chối phải có lý do từ chối.");
      const input = $(`[data-note-input="${c.detail_id}"]`);
      input?.classList.remove("hidden");
      input?.focus();
      return;
    }
    decisions.push({
      detail_id: c.detail_id,
      action: d.action,
      ...(d.action === "REJECT" ? { note: d.note.trim() } : {}),
    });
  }

  const note = $("#ap-note").value.trim();
  const btn = $("#btn-submit-decisions");
  setLoading(btn, true, "Đang gửi...");

  try {
    const res = await academicApi.approveChangeRequest(state.current.request_id, {
      decisions,
      approval_note: note,
    });
    toastSuccess(
      res?.message ||
        `Đã xử lý đơn: duyệt ${res?.approved_count ?? 0} ô, từ chối ${
          res?.rejected_count ?? 0
        } ô.`
    );
    closeModal($("#modal-approval"));
    await loadRequests();
  } catch (err) {
    toastError(err?.message || "Không gửi được quyết định.");
  } finally {
    setLoading(btn, false);
  }
}
