/* ==========================================================================
   GRADEBOOK — M12 bảng điểm + M13 đơn phúc khảo
   Quy tắc:
     • Ô NULL (chưa nhập) → không tính vào ĐTB (hiển thị "–")
     • Ô "v" (vắng) → lưu 0.00, vẫn tính vào ĐTB
     • Bảng điểm đã KHOÁ → không sửa trực tiếp, phải gửi đơn phúc khảo
     • Có đơn gửi duyệt PENDING → phải huỷ đơn mới sửa được
   ========================================================================== */

import { teacherApi, academicApi } from "../api.js";
import { initShell, ctx, pageContent } from "../app.js";
import {
  $,
  $$,
  icon,
  toastSuccess,
  toastError,
  toastWarning,
  openModal,
  closeModal,
  bindBackdropClose,
  confirmDialog,
  setLoading,
  setFieldError,
  clearFieldError,
  escapeHtml,
} from "../ui.js";
import {
  scoreColumnLabel,
  averageTone,
  formatScore,
} from "../format.js";

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */
const state = {
  assignmentId: null,
  meta: null,
  columns: [],
  groups: [],
  scores: [],
  /* Bản nháp chỉnh sửa cục bộ: { studentId: { column: value } } */
  draft: new Map(),
  /* Ô đang chọn trong modal phúc khảo: Set("studentId::column") */
  appealCells: new Set(),
  appealValues: new Map(),
};

let container = null;

/* ------------------------------------------------------------------ */
/* Khởi tạo                                                            */
/* ------------------------------------------------------------------ */
initShell({
  active: "teacher-classes.html",
  roles: ["TEACHER", "ACADEMIC"],
}).then(async () => {
  container = pageContent();

  const params = new URLSearchParams(location.search);
  state.assignmentId = Number(params.get("assignment"));

  if (!state.assignmentId) {
    renderError("Thiếu mã phân công giảng dạy. Vui lòng quay lại danh sách lớp.");
    return;
  }

  renderPage();
  await loadGradebook();
});

function renderError(message) {
  container.innerHTML = `
    <div class="empty-state">
      <span class="empty-state__icon">${icon("alert")}</span>
      <div class="empty-state__title">Không thể mở bảng điểm</div>
      <div class="empty-state__message">${escapeHtml(message)}</div>
      <div class="empty-state__action">
        <a class="btn btn--secondary" href="teacher-classes.html">Quay lại danh sách lớp</a>
      </div>
    </div>`;
}

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__breadcrumb">
        <nav class="breadcrumb" aria-label="Breadcrumb">
          <a href="teacher-classes.html">Lớp phụ trách</a>
          <span class="breadcrumb__sep">/</span>
          <span class="breadcrumb__current" id="crumb-title">Bảng điểm</span>
        </nav>
      </div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title" id="gb-title">Bảng điểm</h1>
          <p class="page-header__subtitle" id="gb-subtitle"></p>
        </div>
        <div class="page-header__actions" id="gb-actions"></div>
      </div>
    </header>

    <div id="gb-alert"></div>

    <div class="card">
      <div class="card__body card__body--tight">
        <div class="toolbar">
          <div class="toolbar__search">
            <span class="toolbar__search-icon">${icon("search")}</span>
            <input class="field__input" id="gb-search" type="search"
                   placeholder="Tìm học sinh trong lớp..." aria-label="Tìm học sinh">
          </div>
          <div class="toolbar__spacer"></div>
          <div class="row" id="gb-legend" style="gap:12px;font-size:12px;color:var(--text-secondary)">
            <span class="row" style="gap:4px">
              <span class="t-mono">–</span> chưa nhập
            </span>
            <span class="row" style="gap:4px">
              <span class="t-mono">0.00</span> vắng / 0 điểm
            </span>
          </div>
        </div>
      </div>

      <div class="gradebook-wrap">
        <table class="gradebook">
          <thead class="gradebook__head" id="gb-head"></thead>
          <tbody class="gradebook__body" id="gb-body"></tbody>
        </table>
      </div>

      <div class="gradebook__footer" id="gb-footer"></div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-appeal"));
  bindBackdropClose($("#modal-submit"));
  bindBackdropClose($("#modal-cancel"));

  $("#form-appeal")?.addEventListener("submit", onAppealSubmit);
  $("#form-submit")?.addEventListener("submit", onSubmitForApproval);
  $("#form-cancel")?.addEventListener("submit", onCancelSubmission);

  $("#gb-search")?.addEventListener("input", (e) => {
    renderTable(e.target.value.trim().toLowerCase());
  });
}

/* ------------------------------------------------------------------ */
/* Tải bảng điểm                                                        */
/* ------------------------------------------------------------------ */
async function loadGradebook() {
  const body = $("#gb-body");
  body.innerHTML = `<tr><td colspan="12" style="padding:40px">
    <div class="skeleton skeleton--text"></div></td></tr>`;

  try {
    const data = await teacherApi.assignmentScores(state.assignmentId);

    state.meta = data;
    state.columns = data.column_config?.active_columns || [];
    state.groups = data.column_config?.groups || [];
    state.scores = data.score_list || [];
    state.draft = new Map();

    renderHeader();
    renderTable();
    renderActions();
    renderFooter();
  } catch (err) {
    body.innerHTML = "";
    const msg = err?.message || "Không tải được bảng điểm.";
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-state__icon">${icon("alert")}</span>
        <div class="empty-state__title">Không tải được bảng điểm</div>
        <div class="empty-state__message">${escapeHtml(msg)}</div>
        <div class="empty-state__action">
          <a class="btn btn--secondary" href="teacher-classes.html">Quay lại</a>
        </div>
      </div>`;
  }
}

/* ------------------------------------------------------------------ */
/* Header — nhóm cột điểm                                               */
/* ------------------------------------------------------------------ */
function renderHeader() {
  const head = $("#gb-head");
  const m = state.meta || {};

  $("#gb-title").textContent = `${m.class_name || ""} — ${m.subject_name || ""}`;
  $("#gb-subtitle").textContent = `${m.academic_year || ""}`;
  $("#crumb-title").textContent = m.class_name || "Bảng điểm";

  const groups = state.groups.length
    ? state.groups
    : [{ key: "all", label: "Điểm", columns: state.columns }];

  const groupCells = groups
    .map(
      (g) => `<th class="gradebook__group" colspan="${g.columns.length}">
        ${escapeHtml(g.label)}
      </th>`
    )
    .join("");

  const colCells = groups
    .map((g) =>
      g.columns
        .map(
          (col) => `<th title="${escapeHtml(col)}">
            <span class="gradebook__col-label">${escapeHtml(scoreColumnLabel(col))}</span>
          </th>`
        )
        .join("")
    )
    .join("");

  head.innerHTML = `
    <tr>
      <th class="gradebook__sticky">Học sinh</th>
      ${groupCells}
      <th style="min-width:80px">ĐTB</th>
    </tr>
    <tr>
      <th class="gradebook__sticky" style="height:32px;font-size:12px;color:var(--text-tertiary)">
        Mã · Họ tên
      </th>
      ${colCells}
      <th style="height:32px;font-size:12px;color:var(--text-tertiary)">0–10</th>
    </tr>
  `;
}

/* ------------------------------------------------------------------ */
/* Body — ma trận điểm                                                   */
/* ------------------------------------------------------------------ */
function renderTable(keyword = "") {
  const body = $("#gb-body");
  const locked = state.meta?.is_locked;
  const pending = state.meta?.pending_submission_id;
  const editable = !locked && !pending;

  const rows = state.scores.filter((s) => {
    if (!keyword) return true;
    return (
      (s.full_name || "").toLowerCase().includes(keyword) ||
      (s.student_code || "").toLowerCase().includes(keyword)
    );
  });

  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="${state.columns.length + 2}"
      class="t-center t-secondary" style="padding:40px">
      ${state.scores.length ? "Không có học sinh phù hợp." : "Lớp chưa có học sinh nào."}
    </td></tr>`;
    renderFooter();
    return;
  }

  body.innerHTML = rows.map((s) => renderRow(s, editable)).join("");
  bindInputs();

  const cols = state.columns.length + 2;
  if (keyword) {
    body.innerHTML += `<tr class="sr-only"><td colspan="${cols}"></td></tr>`;
  }
}

function renderRow(s, editable) {
  const draft = state.draft.get(s.student_id) || {};

  const cells = state.columns
    .map((col) => {
      const raw = draft[col] !== undefined ? draft[col] : s[col];
      const value = raw === null || raw === undefined ? "" : String(raw);
      const isAbsent = value === "0" || value === "0.0" || value === "0.00";
      const placeholder = raw === null || raw === undefined ? "–" : "";

      return `
        <td>
          <div class="gradebook__cell-wrap">
            <input class="gradebook__score-input" type="text"
                   inputmode="decimal" autocomplete="off"
                   data-student="${s.student_id}" data-col="${col}"
                   value="${escapeHtml(value)}"
                   placeholder="${placeholder}"
                   ${editable ? "" : "disabled"}
                   aria-label="Điểm ${escapeHtml(scoreColumnLabel(col))} của ${escapeHtml(
        s.full_name || ""
      )}">
            <button type="button" class="gradebook__absent-btn" data-absent="${col}"
                    data-student="${s.student_id}"
                    title="Đánh dấu vắng (v)"
                    ${editable ? "" : "disabled"}>v</button>
          </div>
        </td>`;
    })
    .join("");

  const avg = draftAvg(s);
  const tone = averageTone(avg, ctx.passingScore);

  return `
    <tr>
      <td class="gradebook__sticky">
        <div class="student-cell">
          <span class="avatar avatar--32">${escapeHtml(initialsOf(s.full_name))}</span>
          <span style="min-width:0">
            <span class="student-cell__name" style="display:block">${escapeHtml(
              s.full_name || "—"
            )}</span>
            <span class="t-caption t-mono">${escapeHtml(s.student_code || "")}</span>
          </span>
        </div>
      </td>
      ${cells}
      <td>
        <span class="gradebook__avg gradebook__avg--${tone}">
          ${avg === null ? "–" : escapeHtml(formatScore(avg))}
        </span>
      </td>
    </tr>
  `;
}

/* ĐTB hiển thị — tính tạm từ các ô đã nhập (NULL bỏ qua, 0.00 có tính) */
function draftAvg(s) {
  const draft = state.draft.get(s.student_id);
  const useDraft = draft && Object.keys(draft).length > 0;

  const values = state.columns
    .map((col) => {
      const raw = useDraft && draft[col] !== undefined ? draft[col] : s[col];
      if (raw === null || raw === undefined || raw === "") return null;
      const n = Number(raw);
      return Number.isNaN(n) ? null : n;
    })
    .filter((v) => v !== null);

  if (!values.length) return null;
  const sum = values.reduce((a, b) => a + b, 0);
  return sum / values.length;
}

/* ------------------------------------------------------------------ */
/* Nhập điểm                                                            */
/* ------------------------------------------------------------------ */
function bindInputs() {
  $$("#gb-body .gradebook__score-input").forEach((input) => {
    input.addEventListener("input", () => {
      const sid = Number(input.dataset.student);
      const col = input.dataset.col;
      const raw = input.value.trim();

      let draft = state.draft.get(sid);
      if (!draft) {
        draft = {};
        state.draft.set(sid, draft);
      }

      if (raw === "") {
        /* Ô xoá trắng → không gửi (backend giữ giá trị cũ) */
        delete draft[col];
      } else {
        draft[col] = raw;
      }

      /* Kiểm tra range 0–10 ngay */
      const n = Number(raw);
      if (raw !== "" && (Number.isNaN(n) || n < 0 || n > 10)) {
        input.classList.add("is-error");
      } else {
        input.classList.remove("is-error");
      }

      updateRowAverage(sid);
      updateFooter();
    });

    input.addEventListener("blur", () => {
      const raw = input.value.trim();
      if (raw === "") return;
      const n = Number(raw);
      if (Number.isNaN(n)) {
        input.classList.add("is-error");
        toastError(`Giá trị "${raw}" không hợp lệ. Chỉ nhập số từ 0 đến 10.`);
        return;
      }
      if (n < 0 || n > 10) {
        input.classList.add("is-error");
        toastError(`Điểm ${raw} nằm ngoài khoảng 0–10.`);
        return;
      }
      /* Chuẩn hoá: gõ "8,5" → "8.5" */
      input.value = String(Number(n.toFixed(2)));
    });

    /* Enter → xuống ô dưới */
    input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const col = input.dataset.col;
      const all = $$("#gb-body .gradebook__score-input").filter(
        (i) => i.dataset.col === col && !i.disabled
      );
      const idx = all.indexOf(input);
      all[idx + 1]?.focus();
      all[idx + 1]?.select();
    });
  });

  /* Nút đánh dấu vắng */
  $$("#gb-body [data-absent]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sid = Number(btn.dataset.student);
      const col = btn.dataset.absent;
      const input = $(`#gb-body input[data-student="${sid}"][data-col="${col}"]`);
      if (!input) return;

      let draft = state.draft.get(sid);
      if (!draft) {
        draft = {};
        state.draft.set(sid, draft);
      }
      draft[col] = "0";
      input.value = "0";
      input.classList.remove("is-error");
      updateRowAverage(sid);
      updateFooter();
    });
  });
}

function updateRowAverage(sid) {
  const row = state.scores.find((s) => s.student_id === sid);
  if (!row) return;
  const avg = draftAvg(row);
  const tone = averageTone(avg, ctx.passingScore);
  const cell = $$(`#gb-body tr`).find((tr) =>
    tr.querySelector(`input[data-student="${sid}"]`)
  );
  const span = cell?.querySelector(".gradebook__avg");
  if (!span) return;
  span.textContent = avg === null ? "–" : formatScore(avg);
  span.className = `gradebook__avg gradebook__avg--${tone}`;
}

/* ------------------------------------------------------------------ */
/* Thanh chân trang + hành động                                          */
/* ------------------------------------------------------------------ */
function renderActions() {
  const box = $("#gb-actions");
  if (!box) return;

  const locked = state.meta?.is_locked;
  const pending = state.meta?.pending_submission_id;
  const hasDraft = state.draft.size > 0;

  const alertBox = $("#gb-alert");
  let alertHtml = "";
  if (pending) {
    alertHtml = `
      <div class="alert alert--warning" style="margin-bottom:16px">
        <span class="alert__icon">${icon("clock")}</span>
        <div class="alert__body">
          <div class="alert__title">Bảng điểm đang được gửi duyệt</div>
          <div class="alert__message">
            Bạn không thể sửa điểm khi đơn đang chờ Giáo vụ xử lý.
            Huỷ đơn để tiếp tục chấm điểm.
          </div>
        </div>
      </div>`;
  } else if (locked) {
    alertHtml = `
      <div class="alert alert--neutral" style="margin-bottom:16px">
        <span class="alert__icon">${icon("lock")}</span>
        <div class="alert__body">
          <div class="alert__title">Bảng điểm đã khoá</div>
          <div class="alert__message">
            Bảng điểm đã được chốt. Muốn sửa điểm, hãy gửi đơn phúc khảo
            cho từng ô điểm cần điều chỉnh.
          </div>
        </div>
      </div>`;
  }
  if (alertBox) alertBox.innerHTML = alertHtml;

  box.innerHTML = `
    ${hasDraft ? `<button type="button" class="btn btn--ghost" id="btn-discard">
        ${icon("refresh")} Bỏ thay đổi
      </button>` : ""}
    ${locked
      ? /* Bảng điểm đã khoá → chỉ được gửi đơn phúc khảo */
        `<button type="button" class="btn btn--primary" id="btn-appeal">
           ${icon("send")} Gửi đơn phúc khảo
         </button>`
      : pending
      ? /* Đang chờ duyệt → chỉ được huỷ đơn */
        `<button type="button" class="btn btn--danger-outline" id="btn-cancel-sub">
           ${icon("x")} Huỷ đơn gửi duyệt
         </button>`
      : /* Đang mở → lưu điểm & gửi duyệt */
        `<button type="button" class="btn btn--secondary" id="btn-submit-approval"
           ${hasDraft ? "" : "disabled"}>
           ${icon("send")} Gửi duyệt
         </button>
         <button type="button" class="btn btn--primary" id="btn-save"
           ${hasDraft ? "" : "disabled"}>
           ${icon("check")} Lưu điểm
         </button>`}
  `;

  $("#btn-save")?.addEventListener("click", saveScores);
  $("#btn-discard")?.addEventListener("click", discardDraft);
  $("#btn-appeal")?.addEventListener("click", openAppealModal);
  $("#btn-submit-approval")?.addEventListener("click", openSubmitModal);
  $("#btn-cancel-sub")?.addEventListener("click", openCancelModal);
}

function renderFooter() {
  const footer = $("#gb-footer");
  if (!footer) return;

  const changed = state.draft.size;
  const cells = Array.from(state.draft.values()).reduce(
    (sum, d) => sum + Object.keys(d).length,
    0
  );

  footer.innerHTML = `
    <span class="t-caption">
      ${changed
        ? `Đang chờ lưu: <strong>${cells}</strong> ô điểm của <strong>${changed}</strong> học sinh.`
        : "Chưa có thay đổi nào chưa lưu."}
    </span>
    <div class="toolbar__spacer"></div>
    <span class="t-caption">
      Điểm đạt: từ ${escapeHtml(String(ctx.passingScore))} · Sĩ số lớp: ${state.scores.length}
    </span>
  `;
}

function updateFooter() {
  renderFooter();
  renderActions();
}

/* ------------------------------------------------------------------ */
/* Lưu điểm                                                            */
/* ------------------------------------------------------------------ */
async function saveScores() {
  const rows = [];
  state.draft.forEach((cols, studentId) => {
    if (!Object.keys(cols).length) return;
    rows.push({ student_id: studentId, ...cols });
  });

  if (!rows.length) {
    toastWarning("Không có thay đổi nào để lưu.");
    return;
  }

  const btn = $("#btn-save");
  setLoading(btn, true, "Đang lưu...");
  try {
    const res = await teacherApi.saveBatch({
      assignment_id: state.assignmentId,
      scores: rows,
    });
    toastSuccess(res?.message || `Đã lưu điểm cho ${rows.length} học sinh.`);
    state.draft = new Map();
    await loadGradebook();
  } catch (err) {
    toastError(err?.message || "Không lưu được điểm.");
    handleScoreError(err);
  } finally {
    setLoading(btn, false);
  }
}

function discardDraft() {
  state.draft = new Map();
  renderTable($("#gb-search")?.value.trim().toLowerCase() || "");
  renderActions();
  renderFooter();
}

/* Lỗi 423 — bảng khoá hoặc đang chờ duyệt → hướng dẫn hành động */
function handleScoreError(err) {
  const box = $("#gb-alert");
  if (!box) return;

  if (err?.code === "SCORE_TABLE_LOCKED") {
    box.innerHTML = `
      <div class="alert alert--neutral" style="margin-bottom:16px">
        <span class="alert__icon">${icon("lock")}</span>
        <div class="alert__body">
          <div class="alert__title">Bảng điểm đã khoá</div>
          <div class="alert__message">
            Hãy gửi đơn phúc khảo cho từng ô điểm cần điều chỉnh.
          </div>
        </div>
      </div>`;
  } else if (err?.code === "SCORE_SUBMISSION_PENDING") {
    box.innerHTML = `
      <div class="alert alert--warning" style="margin-bottom:16px">
        <span class="alert__icon">${icon("clock")}</span>
        <div class="alert__body">
          <div class="alert__title">Đang có đơn gửi duyệt</div>
          <div class="alert__message">
            Vui lòng huỷ đơn gửi duyệt trước khi sửa điểm.
          </div>
        </div>
      </div>`;
  }
}

/* ------------------------------------------------------------------ */
/* Gửi bảng điểm duyệt                                                   */
/* ------------------------------------------------------------------ */
async function openSubmitModal() {
  const m = state.meta || {};
  $("#submit-subtitle").textContent = `${m.class_name || ""} — ${m.subject_name || ""}`;

  /* Kiểm tra còn ô chưa nhập → backend sẽ báo lỗi, cảnh báo trước */
  const missing = countMissingCells();
  const info = $("#submit-info-text");
  const infoBox = $("#submit-summary");
  const btn = $("#btn-submit");

  if (missing > 0) {
    info.textContent = `Còn ${missing} ô điểm chưa nhập. Hệ thống sẽ yêu cầu nhập đủ trước khi gửi duyệt.`;
    infoBox.className = "alert alert--warning";
    btn.disabled = false;
  } else {
    info.textContent = `Đủ ${state.scores.length} học sinh với đầy đủ điểm. Sẵn sàng gửi duyệt.`;
    infoBox.className = "alert alert--info";
    btn.disabled = false;
  }

  hideAlert("submit-alert");
  openModal($("#modal-submit"));
}

function countMissingCells() {
  let count = 0;
  state.scores.forEach((s) => {
    state.columns.forEach((col) => {
      const draft = state.draft.get(s.student_id);
      const raw = draft && draft[col] !== undefined ? draft[col] : s[col];
      if (raw === null || raw === undefined || raw === "") count += 1;
    });
  });
  return count;
}

async function onSubmitForApproval(e) {
  e.preventDefault();
  hideAlert("submit-alert");

  const btn = $("#btn-submit");
  setLoading(btn, true, "Đang gửi...");

  try {
    const res = await teacherApi.createSubmission({
      assignment_id: state.assignmentId,
      note: $("#submit-note")?.value?.trim() || null,
    });
    toastSuccess(res?.message || "Đã gửi bảng điểm đi duyệt.");
    closeModal($("#modal-submit"));
    await loadGradebook();
  } catch (err) {
    const msg = err?.message || "Không gửi được bảng điểm.";
    showAlert(
      "submit-alert",
      err?.code === "INCOMPLETE_SCORES" ? "warning" : "danger",
      "Không thể gửi duyệt",
      msg
    );
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* Huỷ đơn gửi duyệt                                                    */
/* ------------------------------------------------------------------ */
function openCancelModal() {
  const m = state.meta || {};
  $("#cancel-subtitle").textContent = `${m.class_name || ""} — ${m.subject_name || ""}`;
  $("#cancel-reason").value = "";
  hideAlert("cancel-alert");
  openModal($("#modal-cancel"));
}

async function onCancelSubmission(e) {
  e.preventDefault();
  hideAlert("cancel-alert");

  const btn = $("#btn-cancel");
  const pendingId = state.meta?.pending_submission_id;
  if (!pendingId) {
    showAlert("cancel-alert", "danger", "Không tìm thấy đơn", "Vui lòng tải lại trang.");
    return;
  }

  setLoading(btn, true, "Đang huỷ...");
  try {
    const res = await teacherApi.cancelSubmission(pendingId, {
      reason: $("#cancel-reason").value.trim() || null,
    });
    toastSuccess(res?.message || "Đã huỷ đơn gửi duyệt.");
    closeModal($("#modal-cancel"));
    await loadGradebook();
  } catch (err) {
    showAlert("cancel-alert", "danger", "Không huỷ được", err?.message || "Vui lòng thử lại.");
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* M13 — Đơn phúc khảo                                                   */
/* ------------------------------------------------------------------ */
function openAppealModal() {
  const m = state.meta || {};
  $("#appeal-subtitle").textContent = `${m.class_name || ""} — ${m.subject_name || ""}`;
  $("#appeal-warn-icon").innerHTML = icon("alert");
  $("#appeal-reason").value = "";
  hideAlert("appeal-alert");

  state.appealCells = new Set();
  state.appealValues = new Map();

  renderAppealRows();
  openModal($("#modal-appeal"));
}

function renderAppealRows() {
  const tbody = $("#appeal-tbody");
  if (!tbody) return;

  const rows = [];
  state.scores.forEach((s) => {
    state.columns.forEach((col) => {
      const raw = s[col];
      if (raw === null || raw === undefined) return;
      rows.push({ student: s, col, value: raw });
    });
  });

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="t-center t-secondary" style="padding:24px">
      Bảng điểm chưa có dữ liệu để phúc khảo.</td></tr>`;
    $("#appeal-count").textContent = "";
    return;
  }

  tbody.innerHTML = rows
    .map((r) => {
      const key = `${r.student.student_id}::${r.col}`;
      const checked = state.appealCells.has(key);
      const proposed = state.appealValues.get(key) ?? "";
      return `
      <tr>
        <td>
          <input type="checkbox" data-appeal="${key}" ${checked ? "checked" : ""}
                 aria-label="Chọn ô điểm">
        </td>
        <td>
          <div class="student-cell">
            <span class="avatar avatar--32">${escapeHtml(initialsOf(r.student.full_name))}</span>
            <span class="student-cell__name">${escapeHtml(r.student.full_name || "—")}</span>
          </div>
        </td>
        <td>${escapeHtml(scoreColumnLabel(r.col))}</td>
        <td class="table__cell--mono">${escapeHtml(formatScore(r.value) ?? "—")}</td>
        <td>
          <input class="field__input" type="text" inputmode="decimal" style="height:32px;width:90px"
                 data-appeal-value="${key}" value="${escapeHtml(proposed)}"
                 placeholder="VD: 7.5" ${checked ? "" : "disabled"}
                 aria-label="Điểm đề xuất">
        </td>
      </tr>`;
    })
    .join("");

  $$("#appeal-tbody input[data-appeal]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const key = cb.dataset.appeal;
      if (cb.checked) state.appealCells.add(key);
      else {
        state.appealCells.delete(key);
        state.appealValues.delete(key);
      }
      const valueInput = $(`#appeal-tbody input[data-appeal-value="${CSS.escape(key)}"]`);
      if (valueInput) valueInput.disabled = !cb.checked;
      updateAppealCount();
    });
  });

  $$("#appeal-tbody input[data-appeal-value]").forEach((input) => {
    input.addEventListener("input", () => {
      state.appealValues.set(input.dataset.appealValue, input.value.trim());
    });
  });

  updateAppealCount();
}

function updateAppealCount() {
  const count = state.appealCells.size;
  const el = $("#appeal-count");
  if (el) {
    el.textContent = count
      ? `Đã chọn ${count} ô điểm. Nhập điểm đề xuất cho từng ô (bắt buộc).`
      : "Chọn ít nhất một ô điểm cần phúc khảo.";
  }
  const btn = $("#btn-appeal");
  if (btn) btn.disabled = count === 0;
}

async function onAppealSubmit(e) {
  e.preventDefault();
  hideAlert("appeal-alert");

  if (!state.appealCells.size) {
    showAlert("appeal-alert", "danger", "Chưa chọn ô điểm", "Vui lòng chọn ít nhất một ô.");
    return;
  }

  /* Kiểm tra mọi ô đã chọn đều có điểm đề xuất hợp lệ */
  const changes = [];
  for (const key of state.appealCells) {
    const [sid, col] = key.split("::");
    const proposed = state.appealValues.get(key);
    if (proposed === undefined || proposed === "") {
      showAlert(
        "appeal-alert",
        "danger",
        "Thiếu điểm đề xuất",
        "Vui lòng nhập điểm đề xuất cho mọi ô đã chọn."
      );
      return;
    }
    const n = Number(proposed);
    if (Number.isNaN(n) || n < 0 || n > 10) {
      showAlert(
        "appeal-alert",
        "danger",
        "Điểm đề xuất không hợp lệ",
        `Ô ${scoreColumnLabel(col)}: điểm phải là số từ 0 đến 10.`
      );
      return;
    }
    changes.push({
      student_id: Number(sid),
      column_name: col,
      old_value: state.scores.find((s) => s.student_id === Number(sid))?.[col] ?? null,
      new_value: n,
    });
  }

  const reason = $("#appeal-reason").value.trim();
  if (!reason) {
    setFieldError($("#appeal-reason"), "Vui lòng nhập lý do phúc khảo.");
    return;
  }
  clearFieldError($("#appeal-reason"));

  const btn = $("#btn-appeal");
  setLoading(btn, true, "Đang gửi...");

  try {
    const res = await teacherApi.createChangeRequest({
      assignment_id: state.assignmentId,
      reason,
      changes,
    });
    toastSuccess(res?.message || `Đã gửi đơn phúc khảo với ${changes.length} ô điểm.`);
    closeModal($("#modal-appeal"));
  } catch (err) {
    showAlert("appeal-alert", "danger", "Không gửi được đơn", err?.message || "Vui lòng thử lại.");
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* Helpers                                                              */
/* ------------------------------------------------------------------ */
function initialsOf(name) {
  if (!name) return "?";
  const parts = String(name).trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function showAlert(containerId, type, title, message) {
  const box = $("#" + containerId);
  if (!box) return;
  box.className = `alert alert--${type}`;
  box.innerHTML = `
    <span class="alert__icon">${icon(type === "danger" ? "alert" : "info")}</span>
    <div class="alert__body">
      <div class="alert__title">${escapeHtml(title)}</div>
      ${message ? `<div class="alert__message">${escapeHtml(message)}</div>` : ""}
    </div>`;
  box.classList.remove("hidden");
}

function hideAlert(containerId) {
  const box = $("#" + containerId);
  if (box) {
    box.classList.add("hidden");
    box.innerHTML = "";
  }
}
