/* ==========================================================================
   PROFILE — M23 hồ sơ cá nhân & đổi mật khẩu
   ========================================================================== */

import { profileApi, TOKEN } from "../api.js";
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
  escapeHtml,
} from "../ui.js";
import { initials, statusInfo } from "../format.js";

const state = {
  profile: null,
  otpInputs: [],
};

let container = null;

initShell({
  active: "profile.html",
  roles: null,
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadProfile();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Hồ sơ cá nhân</h1>
          <p class="page-header__subtitle">
            Quản lý thông tin tài khoản và bảo mật mật khẩu của bạn.
          </p>
        </div>
      </div>
    </header>

    <div class="layout-split">
      <div class="stack-4">
        <div class="card">
          <div class="card__header">
            <div>
              <div class="card__title">Thông tin tài khoản</div>
              <div class="card__subtitle">Các thông tin dùng để đăng nhập hệ thống.</div>
            </div>
          </div>
          <div class="card__body">
            <form id="form-profile">
              <div id="profile-alert" class="hidden" style="margin-bottom:16px"></div>
              <div class="form-grid">
                <div class="field">
                  <label class="field__label" for="profile-name">Họ và tên</label>
                  <input class="field__input" id="profile-name" name="full_name"
                         placeholder="Nguyễn Văn A">
                </div>
                <div class="field">
                  <label class="field__label" for="profile-username">Tên đăng nhập</label>
                  <input class="field__input" id="profile-username" readonly>
                </div>
                <div class="field">
                  <label class="field__label" for="profile-email">Email</label>
                  <input class="field__input" id="profile-email" name="email" readonly>
                </div>
                <div class="field">
                  <label class="field__label" for="profile-phone">Số điện thoại</label>
                  <input class="field__input" id="profile-phone" name="phone"
                         placeholder="0911223344">
                </div>
              </div>
            </form>
          </div>
          <div class="card__footer">
            <button type="button" class="btn btn--primary" id="btn-save-profile">
              ${icon("check")} Lưu thay đổi
            </button>
          </div>
        </div>

        <div class="card">
          <div class="card__header">
            <div>
              <div class="card__title">Đổi mật khẩu</div>
              <div class="card__subtitle">
                Mật khẩu mới phải khác mật khẩu cũ và tối thiểu 6 ký tự.
              </div>
            </div>
          </div>
          <div class="card__body">
            <form id="form-password">
              <div id="password-alert" class="hidden" style="margin-bottom:16px"></div>
              <div class="form-grid">
                <div class="field">
                  <label class="field__label" for="old-password">
                    Mật khẩu hiện tại <span class="field__required">*</span>
                  </label>
                  <input class="field__input" id="old-password" name="old_password"
                         type="password" autocomplete="current-password">
                </div>
                <div class="field"></div>
                <div class="field">
                  <label class="field__label" for="new-password">
                    Mật khẩu mới <span class="field__required">*</span>
                  </label>
                  <input class="field__input" id="new-password" name="new_password"
                         type="password" autocomplete="new-password">
                </div>
                <div class="field">
                  <label class="field__label" for="confirm-password">
                    Xác nhận mật khẩu <span class="field__required">*</span>
                  </label>
                  <input class="field__input" id="confirm-password" name="confirm_password"
                         type="password" autocomplete="new-password">
                </div>
              </div>
            </form>
          </div>
          <div class="card__footer">
            <button type="button" class="btn btn--secondary" id="btn-otp">
              ${icon("key")} Đổi bằng mã OTP
            </button>
            <button type="button" class="btn btn--primary" id="btn-change-password">
              ${icon("check")} Đổi mật khẩu
            </button>
          </div>
        </div>
      </div>

      <div class="stack-4">
        <div class="card">
          <div class="card__body">
            <div class="profile-head">
              <span class="avatar avatar--96" id="profile-avatar">?</span>
              <div class="profile-head__meta">
                <div class="t-title" id="profile-display-name">—</div>
                <div class="t-caption t-mono" id="profile-display-username">—</div>
                <div style="margin-top:6px" id="profile-display-role"></div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card__header">
            <div class="card__title">Bảo mật</div>
          </div>
          <div class="card__body">
            <div class="kv-list">
              <div class="kv-list__key">Vai trò</div>
              <div class="kv-list__value" id="sec-role">—</div>
              <div class="kv-list__key">Trạng thái</div>
              <div class="kv-list__value" id="sec-status">—</div>
              <div class="kv-list__key">Đăng nhập lần cuối</div>
              <div class="kv-list__value" id="sec-login">—</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  $("#btn-save-profile")?.addEventListener("click", saveProfile);
  $("#btn-change-password")?.addEventListener("click", changePassword);
  $("#btn-otp")?.addEventListener("click", openOtpModal);

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-otp"));

  $("#form-otp")?.addEventListener("submit", submitOtp);
}

async function loadProfile() {
  try {
    const p = await profileApi.get();
    state.profile = p;
    fillProfile(p);
  } catch (err) {
    container.innerHTML = `
      <div class="alert alert--danger">
        <span class="alert__icon">${icon("alert")}</span>
        <div class="alert__body">
          <div class="alert__title">Không tải được hồ sơ</div>
          <div class="alert__message">${escapeHtml(err?.message || "Đã xảy ra sự cố.")}</div>
        </div>
      </div>`;
  }
}

function fillProfile(p) {
  const roleInfo = statusInfo(p.role);

  $("#profile-name").value = p.full_name || "";
  $("#profile-username").value = p.username || "";
  $("#profile-email").value = p.email || "";
  $("#profile-phone").value = p.phone || "";

  $("#profile-avatar").textContent = initials(p.full_name);
  $("#profile-display-name").textContent = p.full_name || "—";
  $("#profile-display-username").textContent = p.username || "";
  $("#profile-display-role").innerHTML = `<span class="chip chip--${roleInfo.tone}">
    <span class="chip__dot"></span>${escapeHtml(roleInfo.label)}
  </span>`;

  $("#sec-role").textContent = roleInfo.label;
  $("#sec-status").innerHTML = p.is_locked
    ? `<span class="chip chip--danger"><span class="chip__dot"></span>Đã khoá</span>`
    : `<span class="chip chip--success"><span class="chip__dot"></span>Hoạt động</span>`;
  $("#sec-login").textContent = p.last_login_at
    ? new Date(p.last_login_at).toLocaleString("vi-VN")
    : "—";
}

async function saveProfile() {
  const btn = $("#btn-save-profile");
  const payload = {
    full_name: $("#profile-name").value.trim(),
    phone: $("#profile-phone").value.trim(),
  };

  if (!payload.full_name) {
    showAlert("#profile-alert", "danger", "Họ và tên không được để trống.");
    return;
  }

  setLoading(btn, true, "Đang lưu...");

  try {
    const updated = await profileApi.update(payload);
    state.profile = updated || state.profile;
    fillProfile(state.profile);
    TOKEN.set({ user: { ...TOKEN.user, ...state.profile } });
    toastSuccess("Đã cập nhật hồ sơ cá nhân.");
  } catch (err) {
    showAlert("#profile-alert", "danger", err?.message || "Không lưu được hồ sơ.");
  } finally {
    setLoading(btn, false);
  }
}

async function changePassword() {
  const btn = $("#btn-change-password");
  const oldPw = $("#old-password").value;
  const newPw = $("#new-password").value;
  const confirmPw = $("#confirm-password").value;

  if (!oldPw || !newPw || !confirmPw) {
    showAlert("#password-alert", "danger", "Vui lòng điền đủ 3 trường mật khẩu.");
    return;
  }
  if (newPw !== confirmPw) {
    showAlert("#password-alert", "danger", "Mật khẩu mới và xác nhận không khớp.");
    return;
  }
  if (newPw.length < 6) {
    showAlert("#password-alert", "danger", "Mật khẩu mới phải có ít nhất 6 ký tự.");
    return;
  }

  setLoading(btn, true, "Đang đổi...");

  try {
    await profileApi.changePassword({
      old_password: oldPw,
      new_password: newPw,
      confirm_password: confirmPw,
    });
    /* Đã đổi mật khẩu tạm → gỡ cờ bắt buộc đổi */
    TOKEN.set({ user: { ...TOKEN.user, must_change_password: false } });
    toastSuccess("Đổi mật khẩu thành công.");
    $("#old-password").value = "";
    $("#new-password").value = "";
    $("#confirm-password").value = "";
    hideAlert("#password-alert");
  } catch (err) {
    showAlert("#password-alert", "danger", err?.message || "Không đổi được mật khẩu.");
  } finally {
    setLoading(btn, false);
  }
}

function openOtpModal() {
  const oldPw = $("#old-password").value;
  const newPw = $("#new-password").value;
  const confirmPw = $("#confirm-password").value;

  if (!oldPw || !newPw || !confirmPw) {
    showAlert("#password-alert", "danger", "Vui lòng điền đủ 3 trường mật khẩu trước.");
    return;
  }
  if (newPw !== confirmPw) {
    showAlert("#password-alert", "danger", "Mật khẩu mới và xác nhận không khớp.");
    return;
  }

  hideAlert("#otp-alert");
  $("#otp-password").value = newPw;
  $("#otp-hint").textContent = "Mã đã được gửi tới email của bạn.";
  buildOtpInputs();
  openModal($("#modal-otp"));
}

function buildOtpInputs() {
  const group = $("#otp-group");
  if (!group) return;

  group.innerHTML = "";
  state.otpInputs = [];

  for (let i = 0; i < 6; i++) {
    const input = document.createElement("input");
    input.className = "otp-input";
    input.type = "text";
    input.inputMode = "numeric";
    input.maxLength = 1;
    input.setAttribute("aria-label", `Chữ số ${i + 1} của mã xác thực`);
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "").slice(0, 1);
      if (input.value && i < 5) state.otpInputs[i + 1]?.focus();
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !input.value && i > 0) {
        state.otpInputs[i - 1]?.focus();
      }
    });
    input.addEventListener("paste", (e) => {
      e.preventDefault();
      const digits = (e.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, 6);
      digits.split("").forEach((d, idx) => {
        if (state.otpInputs[idx]) state.otpInputs[idx].value = d;
      });
      if (digits.length === 6) state.otpInputs[5].blur();
    });
    group.appendChild(input);
    state.otpInputs.push(input);
  }

  state.otpInputs[0]?.focus();
}

function getOtpCode() {
  return state.otpInputs.map((i) => i.value).join("");
}

async function submitOtp(e) {
  e.preventDefault();

  const btn = $("#btn-otp");
  const code = getOtpCode();
  const newPw = $("#otp-password").value;
  const oldPw = $("#old-password").value;
  const confirmPw = $("#confirm-password").value;

  if (code.length !== 6) {
    showAlert("#otp-alert", "danger", "Vui lòng nhập đủ 6 số mã xác thực.");
    return;
  }

  setLoading(btn, true, "Đang xác nhận...");

  try {
    /* Bước 1: yêu cầu mã OTP (kiểm tra mật khẩu cũ trước) */
    await profileApi.requestOtp({
      old_password: oldPw,
      new_password: newPw,
      confirm_password: confirmPw,
    });

    /* Bước 2: xác nhận bằng mã */
    await profileApi.confirmPassword({
      new_password: newPw,
      confirm_password: confirmPw,
      otp_code: code,
    });

    /* Đã đổi mật khẩu tạm → gỡ cờ bắt buộc đổi */
    TOKEN.set({ user: { ...TOKEN.user, must_change_password: false } });
    toastSuccess("Đổi mật khẩu thành công.");
    closeModal($("#modal-otp"));
    $("#old-password").value = "";
    $("#new-password").value = "";
    $("#confirm-password").value = "";
  } catch (err) {
    showAlert("#otp-alert", "danger", err?.message || "Không đổi được mật khẩu.");
  } finally {
    setLoading(btn, false);
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
