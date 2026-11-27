/* ==========================================================================
   RESET OTP — Bước 1/2 của luồng quên mật khẩu
   Nhập email + mã OTP 6 số → xác thực → chuyển sang trang đặt mật khẩu mới.
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

const RESET_PASSWORD_PATH = "/pages/reset-password.html";

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
/* Khởi tạo từ query param (?email=...) hoặc state của bước trước      */
/* ------------------------------------------------------------------ */
const params = new URLSearchParams(location.search);
const flow = RESET_FLOW.get();

const identInput = $("#otp-ident");
identInput.value = params.get("email") || flow?.ident || "";

if (!identInput.value) {
  /* Không có email → không xác định được tài khoản → quay lại đăng nhập */
  location.replace("/pages/login.html");
}

/* ------------------------------------------------------------------ */
/* Điều hướng focus giữa các ô OTP                                    */
/* ------------------------------------------------------------------ */
const otpInputs = $$("#otp-group .otp-input");

otpInputs.forEach((input, index) => {
  input.addEventListener("input", () => {
    input.value = input.value.replace(/\D/g, "").slice(0, 1);
    if (input.value && index < otpInputs.length - 1) {
      otpInputs[index + 1].focus();
    }
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Backspace" && !input.value && index > 0) {
      otpInputs[index - 1].focus();
    }
    if (e.key === "ArrowLeft" && index > 0) otpInputs[index - 1].focus();
    if (e.key === "ArrowRight" && index < otpInputs.length - 1) otpInputs[index + 1].focus();
  });
  input.addEventListener("paste", (e) => {
    e.preventDefault();
    const digits = (e.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, 6);
    digits.split("").forEach((d, i) => {
      if (otpInputs[i]) otpInputs[i].value = d;
    });
    otpInputs[Math.min(digits.length, otpInputs.length - 1)]?.focus();
  });
});

function getOtp() {
  return otpInputs.map((i) => i.value).join("");
}

/* ------------------------------------------------------------------ */
/* Quay lại đăng nhập                                                  */
/* ------------------------------------------------------------------ */
$("#link-back-login")?.addEventListener("click", (e) => {
  e.preventDefault();
  RESET_FLOW.clear();
  location.href = "/pages/login.html";
});

/* ------------------------------------------------------------------ */
/* Gửi lại mã OTP                                                      */
/* ------------------------------------------------------------------ */
$("#btn-resend")?.addEventListener("click", async () => {
  hideAlert("otp-alert");

  const ident = identInput.value.trim();
  if (!ident) {
    setFieldError(identInput, "Vui lòng nhập email hoặc tên đăng nhập.");
    return;
  }
  clearFieldError(identInput);

  const btn = $("#btn-resend");
  setLoading(btn, true, "Đang gửi...");

  try {
    await authApi.forgotPassword(ident);
    toastSuccess(
      "Đã gửi lại mã OTP mới. Vui lòng kiểm tra email của bạn."
    );
    otpInputs.forEach((i) => (i.value = ""));
    otpInputs[0]?.focus();
  } catch (err) {
    showAlert(
      "otp-alert",
      "danger",
      "Không gửi được mã OTP",
      err?.message || "Vui lòng thử lại."
    );
  } finally {
    setLoading(btn, false);
  }
});

/* ------------------------------------------------------------------ */
/* Bước 1 — Xác thực OTP                                              */
/* ------------------------------------------------------------------ */
const form = $("#form-verify-otp");

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("otp-alert");

  const ident = identInput.value.trim();
  const otp = getOtp();
  let ok = true;

  if (!ident) {
    setFieldError(identInput, "Vui lòng nhập email hoặc tên đăng nhập.");
    ok = false;
  } else clearFieldError(identInput);

  if (otp.length !== 6) {
    showAlert("otp-alert", "danger", "Mã OTP không hợp lệ", "Vui lòng nhập đủ 6 số.");
    return;
  }

  if (!ok) return;

  const btn = $("#btn-verify-otp");
  setLoading(btn, true, "Đang xác thực...");

  try {
    const res = await authApi.verifyResetOtp(ident, otp);
    /* api.post đã unwrap envelope {success, message, data} → res chính là data */
    const resetToken = res?.reset_token;

    if (!resetToken) {
      throw new Error("Không nhận được phiên đặt lại mật khẩu. Vui lòng thử lại.");
    }

    /* Lưu state để trang bước 2 dùng */
    RESET_FLOW.set({
      ident,
      reset_token: resetToken,
      username: res?.username,
    });

    toastSuccess("Mã OTP hợp lệ. Vui lòng đặt mật khẩu mới.");
    location.href = RESET_PASSWORD_PATH;
  } catch (err) {
    showAlert(
      "otp-alert",
      "danger",
      "Xác thực thất bại",
      err?.message || "Mã OTP có thể đã hết hạn. Vui lòng thử lại."
    );
    otpInputs.forEach((i) => (i.value = ""));
    otpInputs[0]?.focus();
  } finally {
    setLoading(btn, false);
  }
});

/* Focus ô OTP đầu tiên */
setTimeout(() => otpInputs[0]?.focus(), 100);
