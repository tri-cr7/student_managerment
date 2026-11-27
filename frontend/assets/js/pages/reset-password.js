/* ==========================================================================
   RESET PASSWORD — Bước 2/2 của luồng quên mật khẩu
   Nhập mật khẩu mới + xác nhận → đặt lại mật khẩu bằng reset_token đã có.
   ========================================================================== */

import { authApi, RESET_FLOW } from "../api.js";
import {
  $,
  $$,
  icon,
  toastSuccess,
  setLoading,
  clearFieldError,
  setFieldError,
  escapeHtml,
} from "../ui.js";
import { initials } from "../format.js";

const SPECIAL_CHARS = /[!@#$%^&*()\-_=+[\]{};:,.<>?/|~]/;
const RESET_OTP_PATH = "/pages/reset-otp.html";

const flow = RESET_FLOW.get();

/* Chưa có phiên đặt lại mật khẩu → quay lại bước 1 */
if (!flow?.reset_token) {
  location.replace(RESET_OTP_PATH);
}

/* ------------------------------------------------------------------ */
/* Alert helpers                                                       */
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
/* Hiển thị thông tin tài khoản                                       */
/* ------------------------------------------------------------------ */
$("#rp-avatar").textContent = initials(flow.username || flow.ident || "?");
$("#rp-username").textContent = flow.username || flow.ident || "—";
$("#rp-ident").textContent = flow.ident || "—";

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

const elPassword = $("#rp-password");
const elConfirm = $("#rp-confirm");

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
    li.classList.toggle("is-ok", !!r[li.dataset.rule]);
  });
}

elPassword?.addEventListener("input", () => renderStrength(elPassword.value));

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
bindToggle("#rp-toggle-password", elPassword);
bindToggle("#rp-toggle-confirm", elConfirm);

/* ------------------------------------------------------------------ */
/* Quay lại nhập mã OTP                                                */
/* ------------------------------------------------------------------ */
$("#link-back-otp")?.addEventListener("click", (e) => {
  e.preventDefault();
  location.href = RESET_OTP_PATH + "?email=" + encodeURIComponent(flow.ident || "");
});

/* ------------------------------------------------------------------ */
/* Bước 2 — Đặt lại mật khẩu mới                                      */
/* ------------------------------------------------------------------ */
const form = $("#form-reset-password");

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("rp-alert");

  const password = elPassword.value;
  const confirm = elConfirm.value;
  let ok = true;

  const r = checkRules(password);
  if (!r.length || !r.lower || !r.upper || !r.digit || !r.special) {
    setFieldError(
      elPassword,
      "Mật khẩu mới phải có tối thiểu 8 ký tự, gồm chữ HOA, chữ thường, chữ số và ký tự đặc biệt."
    );
    ok = false;
  } else clearFieldError(elPassword);

  if (!confirm) {
    setFieldError(elConfirm, "Vui lòng xác nhận mật khẩu mới.");
    ok = false;
  } else if (confirm !== password) {
    setFieldError(elConfirm, "Mật khẩu xác nhận không khớp.");
    ok = false;
  } else clearFieldError(elConfirm);

  if (!ok) return;

  const btn = $("#btn-reset-password");
  setLoading(btn, true, "Đang đặt lại...");

  try {
    await authApi.resetPassword({
      reset_token: flow.reset_token,
      new_password: password,
      confirm_password: confirm,
    });

    RESET_FLOW.clear();
    toastSuccess("Đặt lại mật khẩu thành công. Vui lòng đăng nhập.");
    setTimeout(() => {
      location.href = "/pages/login.html";
    }, 900);
  } catch (err) {
    const msg = err?.message || "Không đặt lại được mật khẩu.";
    showAlert("rp-alert", "danger", "Đặt lại mật khẩu thất bại", msg);

    /* Phiên đặt lại mật khẩu hết hạn → yêu cầu xin mã OTP mới */
    if (/hết hạn|không hợp lệ|không tồn tại/i.test(msg)) {
      RESET_FLOW.clear();
      setTimeout(() => {
        location.href = RESET_OTP_PATH + "?email=" + encodeURIComponent(flow.ident || "");
      }, 1600);
    }
  } finally {
    setLoading(btn, false);
  }
});

setTimeout(() => elPassword?.focus(), 100);
