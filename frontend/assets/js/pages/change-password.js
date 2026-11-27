/* ==========================================================================
   CHANGE PASSWORD (FORCED) — M23b
   Trang bắt buộc đổi mật khẩu khi tài khoản đang dùng mật khẩu tạm
   (must_change_password = true do Giáo vụ cấp tài khoản).
   ========================================================================== */

import { profileApi, authApi, TOKEN } from "../api.js";
import {
  $,
  $$,
  icon,
  toastSuccess,
  setLoading,
  clearFieldError,
  setFieldError,
  escapeHtml,
  openModal,
  closeModal,
  bindBackdropClose,
} from "../ui.js";
import { initials } from "../format.js";

const SPECIAL_CHARS = /[!@#$%^&*()\-_=+[\]{};:,.<>?/|~]/;

const HOME_BY_ROLE = {
  STAFF: "students.html",
  TEACHER: "teacher-classes.html",
  ACADEMIC: "students.html",
};

const state = {
  otpInputs: [],
  otpSent: false,
};

const elOld = $("#cp-old-password");
const elNew = $("#cp-new-password");
const elConfirm = $("#cp-confirm-password");

/* ------------------------------------------------------------------ */
/* Chặn nếu chưa đăng nhập                                            */
/* ------------------------------------------------------------------ */
if (!TOKEN.access) {
  location.replace("/pages/login.html?redirect=" + encodeURIComponent(location.pathname));
}

const user = TOKEN.user || {};

/* ------------------------------------------------------------------ */
/* Hiển thị thông tin tài khoản                                        */
/* ------------------------------------------------------------------ */
function fillAccount() {
  $("#cp-avatar").textContent = initials(user.full_name);
  $("#cp-name").textContent = user.full_name || "—";
  $("#cp-username").textContent = user.username || "—";
  $("#cp-email").textContent = user.email || "—";
}
fillAccount();

/* ------------------------------------------------------------------ */
/* Alert helpers                                                        */
/* ------------------------------------------------------------------ */
function showAlert(containerId, type, title, message) {
  const box = $("#" + containerId);
  if (!box) return;
  box.className = `alert alert--${type}`;
  box.innerHTML = `
    <span class="alert__icon">${icon(type === "danger" ? "alert" : "info")}</span>
    <div class="alert__body">
      <div class="alert__title">${escapeHtml(title)}</div>
      ${message ? `<div class="alert__message">${escapeHtml(message)}</div>` : ""}
    </div>
  `;
  box.classList.remove("hidden");
}

function hideAlert(containerId) {
  const box = $("#" + containerId);
  if (box) {
    box.classList.add("hidden");
    box.innerHTML = "";
  }
}

/* ------------------------------------------------------------------ */
/* Đánh giá độ mạnh mật khẩu                                           */
/* ------------------------------------------------------------------ */
function checkRules(pw) {
  return {
    length: (pw || "").length >= 8,
    lower: /[a-z]/.test(pw || ""),
    upper: /[A-Z]/.test(pw || ""),
    digit: /[0-9]/.test(pw || ""),
    special: SPECIAL_CHARS.test(pw || ""),
  };
}

function renderStrength(pw) {
  const box = $("#pw-strength");
  const fill = $("#pw-strength-fill");
  const text = $("#pw-strength-text");
  if (!box) return;

  if (!pw) {
    box.hidden = true;
    return;
  }
  box.hidden = false;

  const r = checkRules(pw);
  const passed = Object.values(r).filter(Boolean).length;

  fill.className = "pw-strength__fill";
  if (passed <= 2) {
    fill.classList.add("is-weak");
    text.textContent = "Mật khẩu yếu — cần đủ 5 điều kiện.";
  } else if (passed === 3) {
    fill.classList.add("is-fair");
    text.textContent = "Mật khẩu trung bình — cần đủ 5 điều kiện.";
  } else if (passed === 4) {
    fill.classList.add("is-good");
    text.textContent = "Mật khẩu khá — cần đủ 5 điều kiện.";
  } else {
    fill.classList.add("is-strong");
    text.textContent = "Mật khẩu mạnh.";
  }

  $$("#pw-rules li").forEach((li) => {
    const key = li.dataset.rule;
    li.classList.toggle("is-ok", !!r[key]);
  });
}

/* ------------------------------------------------------------------ */
/* Hiện / ẩn mật khẩu                                                  */
/* ------------------------------------------------------------------ */
function bindToggle(btnId, input) {
  const btn = $(btnId);
  if (!btn) return;
  btn.innerHTML = icon("eye");
  btn.addEventListener("click", () => {
    const isText = input.type === "text";
    input.type = isText ? "password" : "text";
    btn.setAttribute("aria-label", isText ? "Hiện mật khẩu" : "Ẩn mật khẩu");
    btn.setAttribute("title", isText ? "Hiện mật khẩu" : "Ẩn mật khẩu");
    btn.innerHTML = icon(isText ? "eye" : "eyeOff");
    input.focus();
  });
}
bindToggle("#cp-toggle-old", elOld);
bindToggle("#cp-toggle-new", elNew);
bindToggle("#cp-toggle-confirm", elConfirm);

elNew?.addEventListener("input", () => renderStrength(elNew.value));

/* ------------------------------------------------------------------ */
/* Validate form                                                       */
/* ------------------------------------------------------------------ */
function validate() {
  let ok = true;

  if (!elOld.value) {
    setFieldError(elOld, "Vui lòng nhập mật khẩu hiện tại.");
    ok = false;
  } else clearFieldError(elOld);

  const r = checkRules(elNew.value);
  if (!r.length || !r.lower || !r.upper || !r.digit || !r.special) {
    setFieldError(
      elNew,
      "Mật khẩu mới phải có tối thiểu 8 ký tự, gồm chữ HOA, chữ thường, chữ số và ký tự đặc biệt."
    );
    ok = false;
  } else clearFieldError(elNew);

  if (!elConfirm.value) {
    setFieldError(elConfirm, "Vui lòng xác nhận mật khẩu mới.");
    ok = false;
  } else if (elConfirm.value !== elNew.value) {
    setFieldError(elConfirm, "Mật khẩu xác nhận không khớp.");
    ok = false;
  } else clearFieldError(elConfirm);

  return ok;
}

function payload() {
  return {
    old_password: elOld.value,
    new_password: elNew.value,
    confirm_password: elConfirm.value,
  };
}

function clearForm() {
  elOld.value = "";
  elNew.value = "";
  elConfirm.value = "";
  renderStrength("");
}

/* ------------------------------------------------------------------ */
/* Đổi mật khẩu (1 bước)                                              */
/* ------------------------------------------------------------------ */
const form = $("#form-change-password");

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("cp-alert");

  if (!validate()) return;

  const btn = $("#btn-change-password");
  setLoading(btn, true, "Đang đổi mật khẩu...");

  try {
    await profileApi.changePassword(payload());
    toastSuccess("Đổi mật khẩu thành công.");
    finish();
  } catch (err) {
    showAlert(
      "cp-alert",
      "danger",
      "Đổi mật khẩu thất bại",
      err?.message || "Vui lòng kiểm tra lại thông tin."
    );
  } finally {
    setLoading(btn, false);
  }
});

/* ------------------------------------------------------------------ */
/* Luồng OTP: gửi mã -> nhập mã -> xác nhận                            */
/* ------------------------------------------------------------------ */
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
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "Backspace" && !input.value && i > 0) {
        state.otpInputs[i - 1]?.focus();
      }
      if (ev.key === "ArrowLeft" && i > 0) state.otpInputs[i - 1]?.focus();
      if (ev.key === "ArrowRight" && i < 5) state.otpInputs[i + 1]?.focus();
    });
    input.addEventListener("paste", (ev) => {
      ev.preventDefault();
      const digits = (ev.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, 6);
      digits.split("").forEach((d, idx) => {
        if (state.otpInputs[idx]) state.otpInputs[idx].value = d;
      });
      if (digits.length === 6) state.otpInputs[5]?.blur();
    });
    group.appendChild(input);
    state.otpInputs.push(input);
  }
  state.otpInputs[0]?.focus();
}

function getOtp() {
  return state.otpInputs.map((i) => i.value).join("");
}

$("#btn-change-otp")?.addEventListener("click", async () => {
  hideAlert("cp-alert");
  hideAlert("otp-alert");

  if (!elOld.value) {
    setFieldError(elOld, "Vui lòng nhập mật khẩu hiện tại.");
    return;
  }
  clearFieldError(elOld);

  const r = checkRules(elNew.value);
  if (!r.length || !r.lower || !r.upper || !r.digit || !r.special) {
    setFieldError(
      elNew,
      "Mật khẩu mới phải có tối thiểu 8 ký tự, gồm chữ HOA, chữ thường, chữ số và ký tự đặc biệt."
    );
    return;
  }
  clearFieldError(elNew);

  if (!elConfirm.value || elConfirm.value !== elNew.value) {
    setFieldError(elConfirm, "Mật khẩu xác nhận không khớp.");
    return;
  }
  clearFieldError(elConfirm);

  const btn = $("#btn-change-otp");
  setLoading(btn, true, "Đang gửi mã...");

  try {
    /* Bước 1: server kiểm tra MK cũ + độ mạnh rồi gửi mã OTP về email */
    const res = await profileApi.requestOtp(payload());
    state.otpSent = true;
    $("#otp-hint").textContent =
      res?.message || "Mã OTP 6 số đã được gửi tới email của bạn.";
    buildOtpInputs();
    openModal($("#modal-otp"));
  } catch (err) {
    showAlert(
      "cp-alert",
      "danger",
      "Không gửi được mã xác thực",
      err?.message || "Vui lòng thử lại."
    );
  } finally {
    setLoading(btn, false);
  }
});

$("#form-otp")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("otp-alert");

  const code = getOtp();
  if (code.length !== 6) {
    showAlert("otp-alert", "danger", "Mã OTP không hợp lệ", "Vui lòng nhập đủ 6 số.");
    return;
  }

  const btn = $("#btn-otp-submit");
  setLoading(btn, true, "Đang xác nhận...");

  try {
    await profileApi.confirmPassword({
      otp_code: code,
      new_password: elNew.value,
      confirm_password: elConfirm.value,
    });
    toastSuccess("Đổi mật khẩu thành công.");
    closeModal($("#modal-otp"));
    finish();
  } catch (err) {
    showAlert(
      "otp-alert",
      "danger",
      "Xác thực thất bại",
      err?.message || "Mã OTP có thể đã hết hạn. Vui lòng thử lại."
    );
  } finally {
    setLoading(btn, false);
  }
});

bindBackdropClose($("#modal-otp"));
$$("#modal-otp [data-close]").forEach((btn) =>
  btn.addEventListener("click", () => closeModal($("#modal-otp")))
);

/* ------------------------------------------------------------------ */
/* Hoàn tất — cập nhật cờ và sang trang chủ theo vai trò                */
/* ------------------------------------------------------------------ */
function finish() {
  TOKEN.set({ user: { ...TOKEN.user, must_change_password: false } });
  clearForm();
  const role = TOKEN.role;
  setTimeout(() => {
    location.href = HOME_BY_ROLE[role] || "index.html";
  }, 700);
}

/* ------------------------------------------------------------------ */
/* Đăng xuất                                                           */
/* ------------------------------------------------------------------ */
$("#btn-logout")?.addEventListener("click", async () => {
  try {
    await authApi.logout();
  } catch {
    /* Bỏ qua lỗi mạng — vẫn đăng xuất phía client */
  }
  TOKEN.clear();
  location.href = "/pages/login.html";
});
