/* ==========================================================================
   USERS — M20 quản lý người dùng hệ thống
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
  confirmDialog,
  setLoading,
  toastSuccess,
  toastError,
  toastWarning,
  renderSkeletonRows,
  renderEmptyRow,
  escapeHtml,
} from "../ui.js";
import { statusChip, formatDateTime } from "../format.js";

const state = {
  users: [],
  roleFilter: "",
  keyword: "",
  roleTarget: null,
  passwordTarget: null,
};

let container = null;

initShell({
  active: "users.html",
  roles: ["ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadUsers();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Quản lý người dùng</h1>
          <p class="page-header__subtitle">
            Cấp tài khoản cho cán bộ và giáo viên, quản lý vai trò và trạng thái tài khoản.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--primary" id="btn-add">
            ${icon("plus")} Cấp tài khoản
          </button>
        </div>
      </div>
    </header>

    <div class="card">
      <div class="card__body card__body--tight">
        <div class="toolbar">
          <div class="toolbar__search">
            <span class="toolbar__search-icon">${icon("search")}</span>
            <input class="field__input" id="filter-q" type="search"
                   placeholder="Tìm theo tên đăng nhập, họ tên hoặc email"
                   aria-label="Tìm người dùng">
          </div>
          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-role"
                    aria-label="Lọc theo vai trò">
              <option value="">Tất cả vai trò</option>
              <option value="STAFF">Nhân viên</option>
              <option value="TEACHER">Giáo viên</option>
              <option value="ACADEMIC">Giáo vụ</option>
            </select>
            <span class="field__chevron">▾</span>
          </div>
          <div class="toolbar__spacer"></div>
          <span class="chip chip--neutral" id="count-users">0 tài khoản</span>
        </div>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead class="table__head">
            <tr>
              <th>Tên đăng nhập</th>
              <th>Họ và tên</th>
              <th>Email</th>
              <th>Vai trò</th>
              <th>Trạng thái</th>
              <th>Ngày tạo</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-users"></tbody>
        </table>
      </div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  $("#btn-add")?.addEventListener("click", () => openUserModal());

  $("#filter-role")?.addEventListener("change", (e) => {
    state.roleFilter = e.target.value;
    renderUsers();
  });

  $("#filter-q")?.addEventListener("input", (e) => {
    state.keyword = e.target.value.trim().toLowerCase();
    renderUsers();
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-user"));
  bindBackdropClose($("#modal-role"));
  bindBackdropClose($("#modal-password"));

  $("#form-user")?.addEventListener("submit", onCreateUser);
  $("#form-role")?.addEventListener("submit", onChangeRole);
  $("#form-password")?.addEventListener("submit", onResetPassword);

  const warnIcon = container.querySelector("[data-warn-icon]");
  if (warnIcon) warnIcon.innerHTML = icon("alert");
}

async function loadUsers() {
  const tbody = $("#tbody-users");
  if (!tbody) return;

  renderSkeletonRows(tbody, 7, 8);

  try {
    const res = await adminApi.users();
    const list = Array.isArray(res) ? res : res?.items || [];
    state.users = list;
    renderUsers();
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 7, err?.message || "Không tải được danh sách người dùng.");
  }
}

function renderUsers() {
  const tbody = $("#tbody-users");

  const list = state.users.filter((u) => {
    if (state.roleFilter && u.role !== state.roleFilter) return false;
    if (!state.keyword) return true;
    const haystack = [u.username, u.full_name, u.email]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(state.keyword);
  });

  $("#count-users").textContent = `${list.length} tài khoản`;

  if (!list.length) {
    renderEmptyRow(
      tbody,
      7,
      state.keyword || state.roleFilter
        ? "Không có tài khoản nào phù hợp với bộ lọc."
        : "Chưa có tài khoản nào.",
      `<button type="button" class="btn btn--primary" id="btn-empty-add">
         ${icon("plus")} Cấp tài khoản
       </button>`
    );
    $("#btn-empty-add")?.addEventListener("click", () => openUserModal());
    return;
  }

  tbody.innerHTML = list.map(renderRow).join("");
  bindRowActions();
}

function renderRow(u) {
  const locked = !!u.is_locked;
  const inactive = u.is_active === false;

  return `
    <tr>
      <td class="table__cell--mono">${escapeHtml(u.username || "—")}</td>
      <td class="table__cell--name">${escapeHtml(u.full_name || "—")}</td>
      <td>${escapeHtml(u.email || "—")}</td>
      <td>${statusChip(u.role)}</td>
      <td>${
        locked
          ? `<span class="chip chip--danger"><span class="chip__dot"></span>Đã khoá</span>`
          : inactive
          ? `<span class="chip chip--neutral"><span class="chip__dot"></span>Ngừng hoạt động</span>`
          : `<span class="chip chip--success"><span class="chip__dot"></span>Hoạt động</span>`
      }</td>
      <td>${escapeHtml(formatDateTime(u.created_at))}</td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--icon" data-action="role" data-id="${u.id}"
                  aria-label="Đổi vai trò" title="Đổi vai trò">${icon("swap")}</button>
          <button type="button" class="btn btn--icon" data-action="password" data-id="${u.id}"
                  aria-label="Đặt lại mật khẩu" title="Đặt lại mật khẩu">${icon("key")}</button>
          <button type="button" class="btn btn--icon ${locked ? "" : "btn--danger"}"
                  data-action="lock" data-id="${u.id}" data-locked="${locked}"
                  aria-label="${locked ? "Mở khoá" : "Khoá"}"
                  title="${locked ? "Mở khoá tài khoản" : "Khoá tài khoản"}">
            ${icon(locked ? "unlock" : "lock")}
          </button>
        </div>
      </td>
    </tr>
  `;
}

function bindRowActions() {
  $$("#tbody-users [data-action]").forEach((btn) => {
    const id = Number(btn.dataset.id);
    const action = btn.dataset.action;

    if (action === "role") btn.addEventListener("click", () => openRoleModal(id));
    else if (action === "password") btn.addEventListener("click", () => openPasswordModal(id));
    else btn.addEventListener("click", () => handleToggleLock(id, btn.dataset.locked === "true"));
  });
}

function openUserModal() {
  const form = $("#form-user");
  form.reset();
  hideAlert("#user-alert");

  $("#user-modal-title").textContent = "Cấp tài khoản mới";
  $("#user-modal-subtitle").textContent =
    "Hệ thống tự sinh mật khẩu tạm và gửi qua email. Người dùng phải đổi mật khẩu ở lần đăng nhập đầu.";
  $("#btn-user").textContent = "Cấp tài khoản";

  openModal($("#modal-user"));
}

async function onCreateUser(e) {
  e.preventDefault();

  const btn = $("#btn-user");
  const payload = {
    username: $("#user-username").value.trim(),
    full_name: $("#user-name").value.trim(),
    email: $("#user-email").value.trim(),
    role: $("#user-role").value,
    phone: $("#user-phone").value.trim() || null,
  };

  if (!payload.username || !payload.full_name || !payload.email || !payload.role) {
    showAlert("#user-alert", "danger", "Vui lòng điền đủ tên đăng nhập, họ tên, email và vai trò.");
    return;
  }

  setLoading(btn, true, "Đang tạo...");

  try {
    const res = await adminApi.createUser(payload);
    const emailStatus = res?.email_sent_status;
    closeModal($("#modal-user"));
    await loadUsers();

    if (emailStatus === "FAILED") {
      toastWarning(
        "Đã tạo tài khoản nhưng KHÔNG gửi được email.",
        "Hãy liên hệ quản trị viên để lấy mật khẩu tạm."
      );
    } else if (emailStatus === "LOGGED") {
      toastWarning(
        "Đã tạo tài khoản.",
        "Chưa cấu hình Mail Server — mật khẩu tạm chỉ có trong log server."
      );
    } else {
      toastSuccess(
        res?.message || "Đã cấp tài khoản mới.",
        "Mật khẩu tạm đã được gửi qua email."
      );
    }
  } catch (err) {
    showAlert("#user-alert", "danger", err?.message || "Không tạo được tài khoản.");
  } finally {
    setLoading(btn, false);
  }
}

function openRoleModal(id) {
  const u = state.users.find((x) => x.id === id);
  if (!u) return;

  state.roleTarget = u;
  hideAlert("#role-alert");
  $("#role-subtitle").textContent = `${u.full_name || u.username} — vai trò hiện tại: ${u.role}`;
  $("#role-select").value = u.role;
  openModal($("#modal-role"));
}

async function onChangeRole(e) {
  e.preventDefault();

  const btn = $("#btn-role");
  const role = $("#role-select").value;

  setLoading(btn, true, "Đang đổi...");

  try {
    await adminApi.setRole(state.roleTarget.id, role);
    toastSuccess("Đã đổi vai trò tài khoản.");
    closeModal($("#modal-role"));
    await loadUsers();
  } catch (err) {
    showAlert("#role-alert", "danger", err?.message || "Không đổi được vai trò.");
  } finally {
    setLoading(btn, false);
  }
}

function openPasswordModal(id) {
  const u = state.users.find((x) => x.id === id);
  if (!u) return;

  state.passwordTarget = u;
  hideAlert("#password-alert");
  $("#password-subtitle").textContent = `${u.full_name || u.username} (${u.username})`;
  $("#new-password").value = "DoiMK@123";
  openModal($("#modal-password"));
}

async function onResetPassword(e) {
  e.preventDefault();

  const btn = $("#btn-password");
  const newPassword = $("#new-password").value.trim();

  if (!newPassword) {
    showAlert("#password-alert", "danger", "Vui lòng nhập mật khẩu mới.");
    return;
  }

  setLoading(btn, true, "Đang đặt lại...");

  try {
    await adminApi.resetPassword(state.passwordTarget.id, newPassword);
    toastSuccess("Đã đặt lại mật khẩu tài khoản.");
    closeModal($("#modal-password"));
    await loadUsers();
  } catch (err) {
    showAlert("#password-alert", "danger", err?.message || "Không đặt lại được mật khẩu.");
  } finally {
    setLoading(btn, false);
  }
}

async function handleToggleLock(id, isLocked) {
  const u = state.users.find((x) => x.id === id);
  if (!u) return;

  const ok = await confirmDialog({
    title: isLocked ? "Mở khoá tài khoản" : "Khoá tài khoản",
    message: isLocked
      ? `Mở khoá tài khoản "${u.username}"?`
      : `Khoá tài khoản "${u.username}"?`,
    detail: isLocked
      ? "Số lần nhập sai mật khẩu cũng được đặt lại về 0."
      : "Người dùng sẽ không thể đăng nhập cho tới khi tài khoản được mở khoá.",
    confirmText: isLocked ? "Mở khoá" : "Khoá",
    danger: !isLocked,
  });
  if (!ok) return;

  try {
    await adminApi.lockUser(id, !isLocked);
    toastSuccess(isLocked ? "Đã mở khoá tài khoản." : "Đã khoá tài khoản.");
    await loadUsers();
  } catch (err) {
    toastError(err?.message || "Không thực hiện được thao tác.");
  }
}

function showAlert(sel, tone, message) {
  const box = $(sel);
  if (!box) return;
  box.className = `alert alert--${tone}`;
  box.innerHTML = `
    <span class="alert__icon">${icon("alert")}</span>
    <div class="alert__body"><div class="alert__message">${escapeHtml(message)}</div></div>
  `;
}

function hideAlert(sel) {
  const box = $(sel);
  if (box) {
    box.className = "hidden";
    box.innerHTML = "";
  }
}
