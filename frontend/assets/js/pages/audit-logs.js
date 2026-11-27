/* ==========================================================================
   AUDIT LOGS — M21 tra cứu nhật ký hệ thống
   ========================================================================== */

import { adminApi } from "../api.js";
import { initShell, pageContent } from "../app.js";
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
  auditActionLabel,
  auditDetailKeyLabel,
  auditDetailValueLabel,
  scoreColumnLabel,
} from "../format.js";

const state = {
  page: 1,
  limit: 20,
  action: "",
  keyword: "",
  logs: [],
};

let container = null;

initShell({
  active: "audit-logs.html",
  roles: ["ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadLogs();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Nhật ký hệ thống</h1>
          <p class="page-header__subtitle">
            Lịch sử vết hoạt động của người dùng trên hệ thống: đăng nhập, thay đổi điểm,
            cập nhật quy định, khoá bảng điểm...
          </p>
        </div>
        <div class="page-header__actions">
          <a class="btn btn--secondary" id="btn-export" href="#" download>
            ${icon("download")} Xuất Excel
          </a>
        </div>
      </div>
    </header>

    <div class="card">
      <div class="card__body card__body--tight">
        <div class="toolbar">
          <div class="toolbar__search">
            <span class="toolbar__search-icon">${icon("search")}</span>
            <input class="field__input" id="filter-q" type="search"
                   placeholder="Tìm theo người thực hiện hoặc địa chỉ IP"
                   aria-label="Tìm nhật ký">
          </div>
          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-action"
                    aria-label="Lọc theo hành động">
              <option value="">Tất cả hành động</option>
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
              <th>Thời gian</th>
              <th>Người thực hiện</th>
              <th>Hành động</th>
              <th>Địa chỉ IP</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-logs"></tbody>
        </table>
      </div>

      <div class="pagination" id="pagination-logs"></div>
    </div>
  `;

  fillActionFilter();
  bindPageEvents();
}

/* Sinh dropdown lọc từ danh sách action thực sự có trong nhật ký (API). */
async function fillActionFilter() {
  const sel = $("#filter-action");
  if (!sel) return;

  let items = [];
  try {
    items = await adminApi.auditActions();
  } catch (err) {
    console.warn("Không tải được danh sách hành động:", err);
    return;
  }

  items.forEach(({ action, count }) => {
    const opt = document.createElement("option");
    opt.value = action;
    opt.textContent = `${auditActionLabel(action)} (${count})`;
    sel.appendChild(opt);
  });
}

function bindPageEvents() {
  $("#filter-action")?.addEventListener("change", (e) => {
    state.action = e.target.value;
    state.page = 1;
    loadLogs();
  });

  $("#filter-q")?.addEventListener("input", (e) => {
    state.keyword = e.target.value.trim().toLowerCase();
    renderLogs();
  });

  $("#pagination-logs")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.page);
    loadLogs();
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-audit"));
}

async function loadLogs() {
  const tbody = $("#tbody-logs");
  if (!tbody) return;

  renderSkeletonRows(tbody, 5, 10);

  try {
    const params = { page: state.page, limit: state.limit };
    if (state.action) params.action = state.action;

    const res = await adminApi.auditLogs(params);
    state.logs = res?.items || [];

    updateExportUrl();
    renderLogs(res);
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 5, err?.message || "Không tải được nhật ký hệ thống.");
  }
}

function renderLogs(res) {
  const tbody = $("#tbody-logs");

  const list = state.keyword
    ? state.logs.filter((l) => {
        const haystack = [l.user_name, l.ip_address, l.action]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(state.keyword);
      })
    : state.logs;

  if (!list.length) {
    renderEmptyRow(
      tbody,
      5,
      state.keyword ? "Không có vết nào khớp từ khoá." : "Chưa có vết nhật ký nào."
    );
    renderPagination($("#pagination-logs"), {
      page: 1,
      pages: 1,
      total: 0,
      limit: state.limit,
      label: "vết",
    });
    return;
  }

  tbody.innerHTML = list.map(renderRow).join("");
  bindRowActions();

  renderPagination($("#pagination-logs"), {
    page: res?.page || 1,
    pages: res?.pages || 1,
    total: res?.total || list.length,
    limit: res?.per_page || state.limit,
    label: "vết",
  });
}

function renderRow(l) {
  const failed = String(l.action || "").toUpperCase().includes("FAILED");
  return `
    <tr>
      <td>${escapeHtml(formatDateTime(l.created_at))}</td>
      <td class="table__cell--name">${escapeHtml(l.user_name || "—")}</td>
      <td>
        <span class="chip chip--${failed ? "danger" : "neutral"}">
          <span class="chip__dot"></span>${escapeHtml(auditActionLabel(l.action))}
        </span>
      </td>
      <td class="t-mono">${escapeHtml(l.ip_address || "—")}</td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--icon" data-action="detail" data-id="${l.id}"
                  aria-label="Xem chi tiết" title="Xem chi tiết">${icon("eye")}</button>
        </div>
      </td>
    </tr>
  `;
}

function bindRowActions() {
  $$("#tbody-logs [data-action='detail']").forEach((btn) => {
    btn.addEventListener("click", () => openDetail(Number(btn.dataset.id)));
  });
}

async function openDetail(id) {
  const dialog = $("#modal-audit");
  $("#audit-details").innerHTML = `<div class="skeleton skeleton--text" style="height:80px"></div>`;
  openModal(dialog);

  try {
    const log = await adminApi.auditLog(id);
    renderDetail(log);
  } catch (err) {
    $("#audit-details").innerHTML = `
      <div class="alert alert--danger">
        <span class="alert__icon">${icon("alert")}</span>
        <div class="alert__body">
          <div class="alert__message">${escapeHtml(err?.message || "Không tải được chi tiết.")}</div>
        </div>
      </div>`;
  }
}

function renderDetail(log) {
  $("#audit-title").textContent = `Vết #${log.id}`;
  $("#audit-subtitle").textContent = auditActionLabel(log.action);

  $("#audit-meta").innerHTML = `
    <div class="kv-list__key">Thời gian</div>
    <div class="kv-list__value">${escapeHtml(formatDateTime(log.created_at))}</div>

    <div class="kv-list__key">Người thực hiện</div>
    <div class="kv-list__value">${escapeHtml(log.user_name || "—")}</div>

    <div class="kv-list__key">Hành động</div>
    <div class="kv-list__value">${escapeHtml(auditActionLabel(log.action))}</div>

    <div class="kv-list__key">Địa chỉ IP</div>
    <div class="kv-list__value t-mono">${escapeHtml(log.ip_address || "—")}</div>
  `;

  const details = log.details;
  if (!details || typeof details !== "object" || !Object.keys(details).length) {
    $("#audit-details").innerHTML = `
      <div class="empty-state">
        <span class="empty-state__icon">${icon("inbox")}</span>
        <div class="empty-state__title">Không có dữ liệu thay đổi</div>
      </div>`;
    return;
  }

  const entries = Object.entries(details);
  $("#audit-details").innerHTML = `
    <div class="kv-list">
      ${entries.map(renderDetailEntry).join("")}
    </div>
  `;
}

/* Một dòng key/value trong "Dữ liệu thay đổi".
   - Key tiếng Anh → nhãn tiếng Việt.
   - Field có "from"/"to" → hiển thị diff "cũ → mới".
   - Object lồng → render bảng con thay vì JSON.stringify. */
function renderDetailEntry([key, value], nested = false) {
  const label = escapeHtml(auditDetailKeyLabel(key));

  // --- Field so sánh giá trị: { from, to } ---
  if (isDiffObject(value)) {
    const { old: oldVal, next: newVal } = diffValues(value);
    return `
      <div class="kv-list__key">${label}</div>
      <div class="kv-list__value">
        <span class="diff">
          <span class="diff__old">${escapeHtml(auditDetailValueLabel(oldVal))}</span>
          <span class="diff__arrow">→</span>
          <span class="diff__new">${escapeHtml(auditDetailValueLabel(newVal))}</span>
        </span>
      </div>`;
  }

  // --- Object lồng (changes, sync, ...) → bảng con, đệ quy ---
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const sub = Object.entries(value)
      .map(([k, v]) => renderDetailEntry([k, v], true))
      .join("");
    return `
      <div class="kv-list__key">${label}</div>
      <div class="kv-list__value">
        <div class="kv-list kv-list--nested">${sub}</div>
      </div>`;
  }

  // --- Mảng chứa object → render bảng con thay vì JSON thô ---
  if (Array.isArray(value) && value.some((v) => v && typeof v === "object")) {
    const sub = value
      .map((v) =>
        Object.entries(v)
          .map(([k, sv]) => renderDetailEntry([k, sv], true))
          .join("")
      )
      .join("");
    return `
      <div class="kv-list__key">${label}</div>
      <div class="kv-list__value">
        <div class="kv-list kv-list--nested">${sub}</div>
      </div>`;
  }

  // --- Mảng giá trị đơn → hiển thị dạng chip, ví dụ changed_fields ---
  if (Array.isArray(value)) {
    const items = value
      .map((v) => {
        // Mảng chứa tên field (changed_fields) → dịch theo key
        const text = escapeHtml(
          key === "changed_fields"
            ? auditDetailKeyLabel(v)
            : auditDetailValueLabel(v)
        );
        return `<span class="chip chip--neutral">${text}</span>`;
      })
      .join("");
    return `
      <div class="kv-list__key">${label}</div>
      <div class="kv-list__value">${items || "—"}</div>`;
  }

  // --- Cột điểm: score_15m_1 → "15p.1" ---
  if (key === "score_column") {
    return `
      <div class="kv-list__key">${label}</div>
      <div class="kv-list__value">${escapeHtml(scoreColumnLabel(value))}</div>`;
  }

  // --- Giá trị đơn ---
  return `
    <div class="kv-list__key">${label}</div>
    <div class="kv-list__value">${escapeHtml(auditDetailValueLabel(value))}</div>`;
}

/* Object dạng so sánh giá trị → phải render diff.
   Backend dùng 3 biến thể:
     { from, to }            (student_service, score_service)
     { old, new }            (user_service)
     { old_value, new_value} (score_service) */
function isDiffObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  if (keys.length > 4) return false;
  return (
    keys.includes("from") ||
    keys.includes("to") ||
    keys.includes("old") ||
    keys.includes("new") ||
    keys.includes("old_value") ||
    keys.includes("new_value")
  );
}

/* Lấy giá trị cũ / mới từ object diff (hỗ trợ cả 3 biến thể) */
function diffValues(value) {
  return {
    old: value.from ?? value.old ?? value.old_value ?? null,
    next: value.to ?? value.new ?? value.new_value ?? null,
  };
}

function updateExportUrl() {
  const link = $("#btn-export");
  if (!link) return;
  const params = {};
  if (state.action) params.action = state.action;
  link.href = adminApi.auditLogExportUrl(params);
}
