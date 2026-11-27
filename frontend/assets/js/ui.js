/* ==========================================================================
   UI — Toast, Modal, Confirm, Icons, helpers DOM
   ========================================================================== */

/* ------------------------------------------------------------------ */
/* Icons — SVG line 1.5px, tối giản, đồng bộ                           */
/* ------------------------------------------------------------------ */
const ICONS = {
  dashboard:
    '<path d="M3 3h7v7H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 14h7v7H3z"/>',
  students:
    '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  classes: '<path d="M3 3h18v18H3z"/><path d="M8 21v-4M16 21v-4M12 7v4M9 10h6"/>',
  gradebook:
    '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="M9 7h7M9 11h7"/>',
  approval:
    '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
  subjects:
    '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  assignments:
    '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M9 16h6"/>',
  reports:
    '<path d="M3 3v18h18"/><path d="M7 15l3-4 3 3 4-6"/>',
  settings:
    '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  audit:
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h6"/>',
  users:
    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  profile:
    '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
  logout:
    '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5M12 3v12"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/>',
  edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/>',
  trash:
    '<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
  printer:
    '<path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8" rx="1"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  chevronLeft: '<path d="M15 18l-6-6 6-6"/>',
  chevronRight: '<path d="M9 18l6-6-6-6"/>',
  chevronDown: '<path d="M6 9l6 6 6-6"/>',
  chevronsLeft: '<path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/>',
  chevronsRight: '<path d="M13 17l5-5-5-5M6 17l5-5-5-5"/>',
  eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff:
    '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><path d="M1 1l22 22"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  unlock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  send: '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>',
  filter: '<path d="M22 3H2l8 9.46V19l4 2v-8.54z"/>',
  refresh:
    '<path d="M23 4v6h-6M1 20v-6h6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>',
  swap: '<path d="M17 3l4 4-4 4"/><path d="M21 7H8a4 4 0 0 0-4 4v1"/><path d="M7 21l-4-4 4-4"/><path d="M3 17h13a4 4 0 0 0 4-4v-1"/>',
  menu: '<path d="M3 12h18M3 6h18M3 18h18"/>',
  panelLeft: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>',
  externalLink:
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6M10 14L21 3"/>',
  inbox:
    '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  chart: '<path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6" rx="1"/><rect x="12" y="8" width="3" height="10" rx="1"/><rect x="17" y="4" width="3" height="14" rx="1"/>',
  key: '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3L21 2l-3 3 2 2-3 3-2-2-2.3 2.3z"/>',
};

/* Trả về markup SVG đầy đủ */
export function icon(name, extraClass = "") {
  const path = ICONS[name];
  if (!path) return "";
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"${
    extraClass ? ` class="${extraClass}"` : ""
  }>${path}</svg>`;
}

export function iconButton(name, label, extraClass = "btn btn--icon") {
  return `<button type="button" class="${extraClass}" aria-label="${escapeHtml(
    label
  )}" title="${escapeHtml(label)}">${icon(name)}</button>`;
}

/* ------------------------------------------------------------------ */
/* DOM helpers                                                         */
/* ------------------------------------------------------------------ */
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function el(tag, attrs = {}, html = "") {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (v === null || v === undefined || v === false) return;
    if (k === "class") node.className = v;
    else if (k.startsWith("on") && typeof v === "function")
      node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v === true ? "" : v);
  });
  if (html) node.innerHTML = html;
  return node;
}

/* ------------------------------------------------------------------ */
/* Toast                                                               */
/* ------------------------------------------------------------------ */
const TOAST_ICONS = {
  success: "check",
  danger: "alert",
  warning: "alert",
  info: "info",
};

export function toast(message, { type = "info", title = null, duration = 4000 } = {}) {
  let container = $(".toast-container");
  if (!container) {
    container = el("div", {
      class: "toast-container",
      role: "status",
      "aria-live": "polite",
    });
    document.body.appendChild(container);
  }

  const node = el("div", {
    class: `toast toast--${type}`,
  });

  const defaultTitles = {
    success: "Thành công",
    danger: "Có lỗi xảy ra",
    warning: "Cảnh báo",
    info: "Thông báo",
  };

  node.innerHTML = `
    <span class="toast__icon">${icon(TOAST_ICONS[type] || "info")}</span>
    <div class="grow">
      <div class="toast__title">${escapeHtml(title || defaultTitles[type] || "Thông báo")}</div>
      ${message ? `<div class="toast__message">${escapeHtml(message)}</div>` : ""}
    </div>
  `;

  container.appendChild(node);

  const remove = () => {
    node.classList.add("is-leaving");
    setTimeout(() => node.remove(), 180);
  };
  const timer = setTimeout(remove, duration);
  node.addEventListener("click", () => {
    clearTimeout(timer);
    remove();
  });

  return node;
}

export const toastSuccess = (msg, title) => toast(msg, { type: "success", title });
export const toastError = (msg, title) => toast(msg, { type: "danger", title });
export const toastWarning = (msg, title) => toast(msg, { type: "warning", title });
export const toastInfo = (msg, title) => toast(msg, { type: "info", title });

/* ------------------------------------------------------------------ */
/* Modal                                                               */
/* ------------------------------------------------------------------ */
export function openModal(dialog) {
  if (!dialog) return;
  if (typeof dialog.showModal === "function") {
    if (!dialog.open) dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
  document.body.style.overflow = "hidden";
}

export function closeModal(dialog) {
  if (!dialog) return;
  if (typeof dialog.close === "function") {
    if (dialog.open) dialog.close();
  } else {
    dialog.removeAttribute("open");
  }
  document.body.style.overflow = "";
}

/* Đóng modal khi bấm nền ngoài */
export function bindBackdropClose(dialog) {
  if (!dialog) return;
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) closeModal(dialog);
  });
}

/* ------------------------------------------------------------------ */
/* Confirm dialog — BẮT BUỘC cho hành động phá huỷ dữ liệu            */
/* ------------------------------------------------------------------ */
export function confirmDialog({
  title = "Xác nhận",
  message = "",
  detail = "",
  confirmText = "Xác nhận",
  cancelText = "Huỷ",
  danger = false,
} = {}) {
  return new Promise((resolve) => {
    const dialog = el("dialog", { class: "modal" });
    dialog.innerHTML = `
      <form method="dialog" class="modal__dialog">
        <header class="modal__header">
          <h2 class="modal__title">${escapeHtml(title)}</h2>
        </header>
        <div class="modal__body">
          <p class="t-body">${escapeHtml(message)}</p>
          ${
            detail
              ? `<div class="alert alert--${danger ? "danger" : "warning"}" style="margin-top:16px">
                   <span class="alert__icon">${icon("alert")}</span>
                   <div class="alert__body"><div class="alert__message">${escapeHtml(detail)}</div></div>
                 </div>`
              : ""
          }
        </div>
        <footer class="modal__footer">
          <button type="button" class="btn btn--secondary" data-act="cancel">${escapeHtml(
            cancelText
          )}</button>
          <button type="button" class="btn btn--${danger ? "danger" : "primary"}" data-act="ok">${escapeHtml(
            confirmText
          )}</button>
        </footer>
      </form>
    `;

    document.body.appendChild(dialog);
    openModal(dialog);

    const finish = (value) => {
      closeModal(dialog);
      setTimeout(() => dialog.remove(), 200);
      resolve(value);
    };

    dialog.querySelector('[data-act="cancel"]').addEventListener("click", () => finish(false));
    dialog.querySelector('[data-act="ok"]').addEventListener("click", () => finish(true));
    dialog.addEventListener("cancel", (e) => {
      e.preventDefault();
      finish(false);
    });
  });
}

/* ------------------------------------------------------------------ */
/* Form helpers                                                        */
/* ------------------------------------------------------------------ */
export function setFieldError(input, message) {
  if (!input) return;
  input.classList.add("is-error");
  const field = input.closest(".field");
  if (!field) return;
  let err = field.querySelector(".field__error");
  if (!err) {
    err = el("p", { class: "field__error", role: "alert" });
    field.appendChild(err);
  }
  err.textContent = message || "";
  err.hidden = !message;
  input.setAttribute("aria-invalid", message ? "true" : "false");
}

export function clearFieldError(input) {
  if (!input) return;
  input.classList.remove("is-error");
  input.removeAttribute("aria-invalid");
  const field = input.closest(".field");
  if (!field) return;
  const err = field.querySelector(".field__error");
  if (err) err.hidden = true;
}

export function clearFormErrors(form) {
  $$(".field__input, .field__select, .field__textarea", form).forEach(clearFieldError);
}

/* Gắn validate cho mọi field trong form */
export function bindFormValidation(form, rules) {
  if (!form) return;
  Object.entries(rules || {}).forEach(([name, rule]) => {
    const input = form.querySelector(`[name="${name}"]`);
    if (!input) return;
    const validate = () => {
      const value = (input.value || "").trim();
      if (rule.required && !value) {
        setFieldError(input, rule.requiredMessage || "Trường này là bắt buộc.");
        return false;
      }
      if (rule.pattern && value && !rule.pattern.test(value)) {
        setFieldError(input, rule.message || "Định dạng không hợp lệ.");
        return false;
      }
      if (rule.minLength && value && value.length < rule.minLength) {
        setFieldError(input, rule.message || `Tối thiểu ${rule.minLength} ký tự.`);
        return false;
      }
      clearFieldError(input);
      return true;
    };
    input.addEventListener("blur", validate);
    input.addEventListener("input", () => {
      if (input.classList.contains("is-error")) validate();
    });
    input._validate = validate;
  });
}

export function validateForm(form, rules) {
  const names = Object.keys(rules || {});
  let ok = true;
  names.forEach((name) => {
    const input = form.querySelector(`[name="${name}"]`);
    if (input?._validate && !input._validate()) ok = false;
  });
  return ok;
}

/* Nút loading */
export function setLoading(button, loading, loadingText = null) {
  if (!button) return;
  if (loading) {
    button.dataset.originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="btn__spinner"></span>${
      loadingText ? `<span>${escapeHtml(loadingText)}</span>` : ""
    }`;
  } else {
    button.disabled = false;
    if (button.dataset.originalHtml) {
      button.innerHTML = button.dataset.originalHtml;
      delete button.dataset.originalHtml;
    }
  }
}

/* ------------------------------------------------------------------ */
/* Render helpers                                                      */
/* ------------------------------------------------------------------ */
export function renderSkeletonRows(tbody, cols = 8, rows = 8) {
  const html = Array.from({ length: rows })
    .map(
      () =>
        `<tr><td colspan="${cols}" style="padding:12px 16px">
          <div class="skeleton skeleton--text"></div>
        </td></tr>`
    )
    .join("");
  tbody.innerHTML = html;
}

export function renderEmptyRow(tbody, cols, message, actionHtml = "") {
  tbody.innerHTML = `
    <tr>
      <td colspan="${cols}" class="table__empty-cell">
        <div class="empty-state">
          <span class="empty-state__icon">${icon("inbox")}</span>
          <div class="empty-state__title">${escapeHtml(message)}</div>
          ${actionHtml ? `<div class="empty-state__action">${actionHtml}</div>` : ""}
        </div>
      </td>
    </tr>
  `;
}

export function renderPagination(container, { page, pages, total, limit, label = "bản ghi" }) {
  if (!container) return;
  if (!total || total === 0) {
    container.innerHTML = "";
    return;
  }

  const from = (page - 1) * limit + 1;
  const to = Math.min(page * limit, total);
  const current = Number(page) || 1;
  const totalPages = Number(pages) || 1;

  const nums = [];
  const push = (v) => nums.push(v);
  push(1);
  if (current > 3) push("…");
  for (let i = Math.max(2, current - 1); i <= Math.min(totalPages - 1, current + 1); i++) {
    push(i);
  }
  if (current < totalPages - 2) push("…");
  if (totalPages > 1) push(totalPages);

  const seen = new Set();
  const pageButtons = nums
    .filter((n) => (seen.has(n) ? false : (seen.add(n), true)))
    .map((n) =>
      n === "…"
        ? `<span class="pagination__ellipsis">…</span>`
        : `<button type="button" class="pagination__page ${
            n === current ? "is-active" : ""
          }" data-page="${n}">${n}</button>`
    )
    .join("");

  container.innerHTML = `
    <span class="pagination__info">Hiển thị ${from}–${to} trên ${total} ${escapeHtml(label)}</span>
    <div class="pagination__pages">
      <button type="button" class="pagination__page" data-page="${
        current - 1
      }" ${current <= 1 ? "disabled" : ""} aria-label="Trang trước">${icon(
    "chevronLeft"
  )}</button>
      ${pageButtons}
      <button type="button" class="pagination__page" data-page="${
        current + 1
      }" ${current >= totalPages ? "disabled" : ""} aria-label="Trang sau">${icon(
    "chevronRight"
  )}</button>
    </div>
  `;
}

/* Debounce cho ô tìm kiếm */
export function debounce(fn, wait = 350) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

/* Đóng dropdown khi click ra ngoài */
export function bindDropdown(dropdown) {
  if (!dropdown) return;
  const toggle = dropdown.querySelector("[data-dropdown-toggle]");
  if (toggle) {
    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("is-open");
    });
  }
  document.addEventListener("click", () => dropdown.classList.remove("is-open"));
}
