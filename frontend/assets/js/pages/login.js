/* ==========================================================================
   LOGIN — M1 đăng nhập / M2 quên mật khẩu
   (M2 dẫn sang trang /pages/reset-otp.html — xác thực OTP;
    sau đó sang /pages/reset-password.html — đặt mật khẩu mới)
   ========================================================================== */

import { authApi, TOKEN } from "../api.js";
import {
  $,
  icon,
  toastSuccess,
  setLoading,
  clearFieldError,
  setFieldError,
  escapeHtml,
} from "../ui.js";

const HOME_BY_ROLE = {
  STAFF: "students.html",
  TEACHER: "teacher-classes.html",
  ACADEMIC: "students.html",
};

/* Trang bắt buộc đổi mật khẩu (tài khoản dùng mật khẩu tạm) */
const CHANGE_PASSWORD_PATH = "/pages/change-password.html";

/* ------------------------------------------------------------------ */
/* Chuyển view                                                         */
/* ------------------------------------------------------------------ */
const views = {
  login: $("#view-login"),
  forgot: $("#view-forgot"),
};

function showView(name) {
  Object.entries(views).forEach(([key, node]) => {
    if (!node) return;
    node.classList.toggle("hidden", key !== name);
  });
  const title = {
    login: "Đăng nhập",
    forgot: "Quên mật khẩu",
  }[name];
  document.title = `${title} — Hệ thống Quản lý Học sinh`;
  const first = views[name]?.querySelector("input");
  setTimeout(() => first?.focus(), 50);
}

/* Hiển thị alert trong form */
function showAlert(containerId, type, title, message) {
  const box = $("#" + containerId);
  if (!box) return;
  const iconName =
    type === "danger" ? "alert" : type === "warning" ? "lock" : "info";
  box.className = `alert alert--${type}`;
  box.innerHTML = `
    <span class="alert__icon">${icon(iconName)}</span>
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
/* Nếu đã đăng nhập → chuyển thẳng                                   */
/* ------------------------------------------------------------------ */
if (TOKEN.access) {
  /* Còn dùng mật khẩu tạm → buộc đổi trước khi vào hệ thống */
  if (TOKEN.user?.must_change_password) {
    location.replace(CHANGE_PASSWORD_PATH);
  } else {
    const role = TOKEN.role;
    location.replace(HOME_BY_ROLE[role] || "index.html");
  }
}

/* ------------------------------------------------------------------ */
/* Điều hướng dựa trên query param                                    */
/* ------------------------------------------------------------------ */
const params = new URLSearchParams(location.search);
const redirectTarget = params.get("redirect");

function goHome(user) {
  const role = user?.role || TOKEN.role;

  /* Tài khoản dùng mật khẩu tạm → buộc đổi mật khẩu, không vào dashboard */
  if (user?.must_change_password ?? TOKEN.user?.must_change_password) {
    location.href = CHANGE_PASSWORD_PATH;
    return;
  }

  if (redirectTarget && redirectTarget.startsWith("/") && !redirectTarget.includes("login")) {
    location.href = redirectTarget;
    return;
  }
  location.href = HOME_BY_ROLE[role] || "index.html";
}

/* ------------------------------------------------------------------ */
/* Hiện/ẩn mật khẩu                                                    */
/* ------------------------------------------------------------------ */
const toggleBtn = $("#btn-toggle-password");
const passwordInput = $("#login-password");
toggleBtn?.addEventListener("click", () => {
  const isText = passwordInput.type === "text";
  passwordInput.type = isText ? "password" : "text";
  toggleBtn.setAttribute("aria-label", isText ? "Hiện mật khẩu" : "Ẩn mật khẩu");
  toggleBtn.setAttribute("title", isText ? "Hiện mật khẩu" : "Ẩn mật khẩu");
  toggleBtn.innerHTML = icon(isText ? "eye" : "eyeOff");
  passwordInput.focus();
});
toggleBtn && (toggleBtn.innerHTML = icon("eye"));

/* ------------------------------------------------------------------ */
/* M1 — Đăng nhập                                                       */
/* ------------------------------------------------------------------ */
const loginForm = $("#form-login");

loginForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("login-alert");

  const username = $("#login-username");
  const password = $("#login-password");
  let ok = true;

  if (!username.value.trim()) {
    setFieldError(username, "Vui lòng nhập tên đăng nhập.");
    ok = false;
  } else clearFieldError(username);

  if (!password.value) {
    setFieldError(password, "Vui lòng nhập mật khẩu.");
    ok = false;
  } else clearFieldError(password);

  if (!ok) return;

  const btn = $("#btn-login");
  setLoading(btn, true, "Đang đăng nhập...");

  try {
    const data = await authApi.login(username.value.trim(), password.value);
    TOKEN.set({
      token: data.token,
      refresh_token: data.refresh_token,
      user: data.user,
    });

    if (data.must_change_password || data.user?.must_change_password) {
      toastSuccess(
        `Xin chào, ${data.user?.full_name || data.user?.username}!`,
        "Vui lòng đổi mật khẩu tạm"
      );
    } else {
      toastSuccess(`Xin chào, ${data.user?.full_name || data.user?.username}!`);
    }
    setTimeout(() => goHome(data.user), 400);
  } catch (err) {
    const msg = err?.message || "Đăng nhập thất bại.";

    /* Tài khoản bị tạm khóa → hiển thị hướng dẫn + link quên mật khẩu
       (đây là đường dự phòng duy nhất khi tài khoản là admin duy nhất). */
    if (err?.code === "ACCOUNT_LOCKED") {
      showAlert("login-alert", "warning", "Tài khoản đang tạm khóa", msg);
      const box = $("#login-alert");
      if (box && !$("#link-forgot-locked")) {
        const link = document.createElement("a");
        link.id = "link-forgot-locked";
        link.href = "#";
        link.className = "alert__link";
        link.textContent = "Đặt lại mật khẩu ngay";
        link.addEventListener("click", (e) => {
          e.preventDefault();
          hideAlert("login-alert");
          showView("forgot");
          prefillForgot(username?.value?.trim());
        });
        box.querySelector(".alert__body")?.appendChild(link);
      }
    } else {      showAlert("login-alert", "danger", "Đăng nhập thất bại", msg);
    }
    password.value = "";
    password.focus();
  } finally {
    setLoading(btn, false);
  }
});

/* Prefill ô "Quên mật khẩu" với tên đăng nhập đã nhập (khi bị khoá tài khoản) */
function prefillForgot(username) {
  const field = $("#forgot-ident");
  if (field && username) field.value = username;
}

/* ------------------------------------------------------------------ */
/* M2 — Quên mật khẩu                                                  */
/* ------------------------------------------------------------------ */
$("#link-forgot")?.addEventListener("click", (e) => {
  e.preventDefault();
  hideAlert("login-alert");
  hideAlert("forgot-alert");
  showView("forgot");
});

$("#link-back-login")?.addEventListener("click", (e) => {
  e.preventDefault();
  showView("login");
});

const forgotForm = $("#form-forgot");

forgotForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("forgot-alert");

  const ident = $("#forgot-ident");
  if (!ident.value.trim()) {
    setFieldError(ident, "Vui lòng nhập email hoặc tên đăng nhập.");
    return;
  }
  clearFieldError(ident);

  const btn = $("#btn-forgot");
  setLoading(btn, true, "Đang gửi...");

  try {
    await authApi.forgotPassword(ident.value.trim());
    showAlert(
      "forgot-alert",
      "success",
      "Đã gửi mã OTP",
      "Vui lòng kiểm tra email của bạn để lấy mã OTP đặt lại mật khẩu."
    );
    /* Chuyển sang trang nhập OTP (bước 1/2) */
    setTimeout(() => {
      location.href =
        "/pages/reset-otp.html?email=" + encodeURIComponent(ident.value.trim());
    }, 1200);
  } catch (err) {
    showAlert(
      "forgot-alert",
      "danger",
      "Không gửi được mã OTP",
      err?.message || "Vui lòng thử lại."
    );
  } finally {
    setLoading(btn, false);
  }
});
