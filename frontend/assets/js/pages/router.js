/* ==========================================================================
   ROUTER — Điểm vào: chưa đăng nhập → login, đã đăng nhập → trang chủ theo vai trò
   ========================================================================== */

import { TOKEN } from "../api.js";
import { HOME_BY_ROLE } from "../app.js";

const msg = document.getElementById("router-msg");

if (!TOKEN.access) {
  if (msg) msg.textContent = "Chuyển tới trang đăng nhập...";
  location.replace("/login.html");
} else if (TOKEN.user?.must_change_password) {
  /* Còn dùng mật khẩu tạm → buộc đổi mật khẩu trước */
  if (msg) msg.textContent = "Chuyển tới trang đổi mật khẩu...";
  location.replace("/pages/change-password.html");
} else {
  const target = HOME_BY_ROLE[TOKEN.role] || "login.html";
  if (msg) msg.textContent = `Chuyển tới ${target}...`;
  location.replace(`/${target}`);
}
