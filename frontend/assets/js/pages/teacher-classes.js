/* ==========================================================================
   TEACHER-CLASSES — M11 danh sách lớp môn học được phân công
   ========================================================================== */

import { teacherApi, academicApi, normalizeList } from "../api.js";
import { initShell, ctx, pageContent } from "../app.js";
import {
  $,
  $$,
  icon,
  toastSuccess,
  toastError,
  toastWarning,
  renderSkeletonRows,
  renderEmptyRow,
  escapeHtml,
} from "../ui.js";
import { formatDateTime } from "../format.js";

const state = {
  assignments: [],
  filter: "ALL",
};

let container = null;

initShell({
  active: "teacher-classes.html",
  roles: ["TEACHER", "ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadAssignments();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Lớp phụ trách</h1>
          <p class="page-header__subtitle">
            Các lớp môn học được phân công. Bấm vào lớp để mở bảng điểm.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--ghost btn--icon" id="btn-refresh"
                  aria-label="Tải lại" title="Tải lại">${icon("refresh")}</button>
        </div>
      </div>
    </header>

    <div class="tabs" id="tabs-filter" role="tablist">
      <button type="button" class="tabs__item is-active" data-filter="ALL" role="tab">
        Tất cả
      </button>
      <button type="button" class="tabs__item" data-filter="OPEN" role="tab">
        Đang mở
      </button>
      <button type="button" class="tabs__item" data-filter="LOCKED" role="tab">
        Đã khoá
      </button>
      <button type="button" class="tabs__item" data-filter="PENDING" role="tab">
        Chờ duyệt
      </button>
    </div>

    <div class="grid grid-3" id="card-grid"></div>
  `;

  $("#btn-refresh")?.addEventListener("click", () => loadAssignments());
  $("#tabs-filter")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-filter]");
    if (!btn) return;
    state.filter = btn.dataset.filter;
    $$("#tabs-filter .tabs__item").forEach((t) =>
      t.classList.toggle("is-active", t === btn)
    );
    renderCards();
  });
}

/* ------------------------------------------------------------------ */
/* Tải dữ liệu                                                          */
/* ------------------------------------------------------------------ */
async function loadAssignments() {
  const grid = $("#card-grid");
  if (!grid) return;

  grid.innerHTML = Array.from({ length: 6 })
    .map(
      () => `
    <div class="card"><div class="card__body">
      <div class="skeleton skeleton--text" style="height:20px;width:60%"></div>
      <div class="skeleton skeleton--text" style="margin-top:12px;width:80%"></div>
      <div class="skeleton skeleton--text" style="margin-top:8px;width:40%"></div>
    </div></div>`
    )
    .join("");

  try {
    const res = await teacherApi.myAssignments();
    state.assignments = Array.isArray(res) ? res : normalizeList(res).items;
    renderCards();
  } catch (err) {
    grid.innerHTML = "";
    grid.innerHTML = `
      <div class="card" style="grid-column:1/-1">
        <div class="card__body">
          <div class="empty-state">
            <span class="empty-state__icon">${icon("inbox")}</span>
            <div class="empty-state__title">Không tải được danh sách lớp</div>
            <div class="empty-state__message">${escapeHtml(
              err?.message || "Vui lòng thử lại."
            )}</div>
          </div>
        </div>
      </div>`;
  }
}

/* ------------------------------------------------------------------ */
/* Lọc theo trạng thái                                                    */
/* ------------------------------------------------------------------ */
function statusOf(a) {
  if (a.has_pending_submission) return "PENDING";
  if (a.is_locked) return "LOCKED";
  return "OPEN";
}

const STATUS_META = {
  OPEN: { label: "Đang mở", tone: "success" },
  LOCKED: { label: "Đã khoá", tone: "neutral" },
  PENDING: { label: "Chờ duyệt", tone: "warning" },
};

function renderCards() {
  const grid = $("#card-grid");
  if (!grid) return;

  const items = state.assignments.filter((a) => {
    if (state.filter === "ALL") return true;
    return statusOf(a) === state.filter;
  });

  if (!items.length) {
    grid.innerHTML = `
      <div class="card" style="grid-column:1/-1">
        <div class="card__body">
          <div class="empty-state">
            <span class="empty-state__icon">${icon("classes")}</span>
            <div class="empty-state__title">${
              state.assignments.length
                ? "Không có lớp nào ở trạng thái này."
                : "Bạn chưa được phân công lớp môn học nào."
            }</div>
            <div class="empty-state__message">
              ${
                state.assignments.length
                  ? "Thử chọn trạng thái khác ở thanh lọc phía trên."
                  : "Liên hệ Giáo vụ để được phân công giảng dạy."
              }
            </div>
          </div>
        </div>
      </div>`;
    return;
  }

  grid.innerHTML = items.map((a) => renderCard(a)).join("");

  $$("#card-grid [data-open]").forEach((card) =>
    card.addEventListener("click", () => {
      location.href = `gradebook.html?assignment=${card.dataset.open}`;
    })
  );
}

function renderCard(a) {
  const key = statusOf(a);
  const meta = STATUS_META[key];
  const scoreCount = a.scores_count ?? 0;

  return `
    <div class="card card--hover" data-open="${a.id}"
         style="cursor:pointer" role="button" tabindex="0"
         aria-label="Mở bảng điểm ${escapeHtml(a.class_name)}">
      <div class="card__body">
        <div class="row row--between" style="align-items:flex-start">
          <div style="min-width:0">
            <div class="t-title">${escapeHtml(a.class_name || "—")}</div>
            <div class="t-caption" style="margin-top:2px">
              ${escapeHtml(a.subject_name || "—")}
            </div>
          </div>
          <span class="chip chip--${meta.tone}">
            <span class="chip__dot"></span>${escapeHtml(meta.label)}
          </span>
        </div>

        <hr class="divider" style="margin:16px 0">

        <div class="kv-list" style="grid-template-columns:100px 1fr;gap:8px 12px;font-size:13px">
          <span class="kv-list__key">Học kỳ</span>
          <span class="kv-list__value">${escapeHtml(a.semester_name || "—")}</span>
          <span class="kv-list__key">Năm học</span>
          <span class="kv-list__value">${escapeHtml(a.academic_year_name || "—")}</span>
          <span class="kv-list__key">Số điểm</span>
          <span class="kv-list__value t-mono">${scoreCount}</span>
          ${a.locked_at ? `<span class="kv-list__key">Khoá lúc</span>
            <span class="kv-list__value">${escapeHtml(formatDateTime(a.locked_at))}</span>` : ""}
        </div>

        <div style="margin-top:16px">
          <span class="btn btn--secondary btn--sm" style="pointer-events:none">
            ${icon("gradebook")} Mở bảng điểm
          </span>
        </div>
      </div>
    </div>
  `;
}
