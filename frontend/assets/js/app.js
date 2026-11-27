/* ==========================================================================
   APP — App Shell (topbar + sidebar theo vai trò) + guard + ngữ cảnh chung
   Mọi màn hình đều import `initShell()` để dựng khung chung.
   ========================================================================== */

import { TOKEN, catalogApi, API_BASE } from "./api.js";
import {
  $,
  $$,
  el,
  icon,
  openModal,
  closeModal,
  bindBackdropClose,
  escapeHtml,
} from "./ui.js";
import { initials, statusInfo } from "./format.js";

/* ------------------------------------------------------------------ */
/* Menu theo vai trò                                                    */
/* ------------------------------------------------------------------ */
const MENUS = {
  STAFF: [
    {
      title: "Học sinh",
      items: [{ href: "students.html", label: "Danh sách học sinh", icon: "students" }],
    },
    {
      title: "Lớp học",
      items: [{ href: "classes.html", label: "Quản lý lớp học", icon: "classes" }],
    },
  ],
  TEACHER: [
    {
      title: "Giảng dạy",
      items: [
        { href: "teacher-classes.html", label: "Lớp phụ trách", icon: "classes" },
        { href: "my-requests.html", label: "Đơn phúc khảo", icon: "approval" },
      ],
    },
  ],
  ACADEMIC: [
    {
      title: "Đào tạo",
      items: [
        { href: "students.html", label: "Học sinh", icon: "students" },
        { href: "classes.html", label: "Quản lý lớp học", icon: "classes" },
        { href: "subjects.html", label: "Danh mục môn học", icon: "subjects" },
        { href: "assignments.html", label: "Phân công giảng dạy", icon: "assignments" },
      ],
    },
    {
      title: "Điểm số",
      items: [
        { href: "submissions.html", label: "Duyệt bảng điểm", icon: "gradebook" },
        { href: "approvals.html", label: "Phê duyệt phúc khảo", icon: "approval" },
      ],
    },
    {
      title: "Báo cáo",
      items: [{ href: "reports.html", label: "Thống kê & xuất file", icon: "reports" }],
    },
    {
      title: "Hệ thống",
      items: [
        { href: "rules.html", label: "Quy định", icon: "settings" },
        { href: "users.html", label: "Người dùng", icon: "users" },
        { href: "audit-logs.html", label: "Nhật ký hệ thống", icon: "audit" },
      ],
    },
  ],
};

/* Trang mặc định theo vai trò */
export const HOME_BY_ROLE = {
  STAFF: "students.html",
  TEACHER: "teacher-classes.html",
  ACADEMIC: "students.html",
};

/* ------------------------------------------------------------------ */
/* Ngữ cảnh dùng chung — năm học, học kỳ, quy định                   */
/* ------------------------------------------------------------------ */
export const ctx = {
  user: null,
  role: null,
  year: null,
  semester: null,
  rules: {},
  maxClassSize: 40,
  minAge: 15,
  maxAge: 20,
  passingScore: 5.0,
};

/* Nạp quy định động (tuổi, sĩ số, ngưỡng đạt) */
export async function loadRules() {
  try {
    const rules = await catalogApi.rules();
    const map = {};
    (rules || []).forEach((r) => {
      map[r.rule_key] = r;
    });
    ctx.rules = map;
    ctx.maxClassSize = Number(map.MAX_CLASS_SIZE?.rule_value ?? 40);
    ctx.minAge = Number(map.MIN_AGE?.rule_value ?? 15);
    ctx.maxAge = Number(map.MAX_AGE?.rule_value ?? 20);
    ctx.passingScore = Number(map.PASSING_SCORE?.rule_value ?? 5.0);
  } catch {
    /* Giữ giá trị mặc định nếu API lỗi */
  }
  return ctx.rules;
}

/* Trang buộc đổi mật khẩu (không được bỏ qua) */
export const CHANGE_PASSWORD_PATH = "/pages/change-password.html";

/* ------------------------------------------------------------------ */
/* Guard — chưa đăng nhập / sai vai trò / bắt buộc đổi mật khẩu      */
/* ------------------------------------------------------------------ */
export function requireAuth(allowedRoles = null) {
  if (!TOKEN.access) {
    location.href = "/pages/login.html?redirect=" + encodeURIComponent(location.pathname);
    return false;
  }

  /* Tài khoản đang dùng mật khẩu tạm → bắt buộc đổi trước khi dùng hệ thống */
  if (
    TOKEN.user?.must_change_password &&
    !location.pathname.includes("change-password")
  ) {
    location.replace(CHANGE_PASSWORD_PATH);
    return false;
  }

  const role = TOKEN.role;
  if (allowedRoles && role && !allowedRoles.includes(role)) {
    location.href = "/pages/403.html";
    return false;
  }
  return true;
}

/* ------------------------------------------------------------------ */
/* Dựng App Shell                                                      */
/* ------------------------------------------------------------------ */
export async function initShell({
  active = null,
  roles = null,
  onContextLoaded = null,
} = {}) {
  if (!requireAuth(roles)) return null;

  ctx.user = TOKEN.user;
  ctx.role = TOKEN.role;

  const shell = $("#app-shell");
  if (!shell) return ctx;

  const current = active || guessActive();

  shell.innerHTML = `
    <header class="topbar">
      <button type="button" class="topbar__icon-btn" id="btn-mobile-menu"
              aria-label="Mở menu" style="display:none">${icon("menu")}</button>
      <div class="topbar__brand">
        <span class="topbar__logo">TH</span>
        <span class="topbar__name">Trường THPT</span>
      </div>
      <div class="topbar__spacer"></div>
      <div class="topbar__ctx" id="topbar-context"></div>
      <div class="topbar__actions">
        <a class="topbar__icon-btn" href="profile.html" aria-label="Hồ sơ cá nhân"
           title="Hồ sơ cá nhân">${icon("profile")}</a>
        <button type="button" class="topbar__icon-btn" id="btn-logout"
                aria-label="Đăng xuất" title="Đăng xuất">${icon("logout")}</button>
      </div>
    </header>

    <div class="app-body">
      <aside class="sidebar" id="sidebar">
        <nav class="sidebar__nav" aria-label="Điều hướng chính">
          ${renderMenu(current)}
        </nav>
        <div class="sidebar__footer">
          <button type="button" class="sidebar__collapse" id="btn-collapse">
            ${icon("panelLeft")}<span>Thu gọn</span>
          </button>
        </div>
      </aside>

      <main class="main" id="main-content">
        <div class="main__inner" id="page-content"></div>
      </main>
    </div>
  `;

  bindShellEvents();
  await renderTopbarContext();

  /* Nạp quy định động (tuổi, sĩ số, ngưỡng đạt) */
  await loadRules();
  if (onContextLoaded) onContextLoaded(ctx);

  return ctx;
}

function guessActive() {
  const file = location.pathname.split("/").pop() || "index.html";
  return file;
}

function renderMenu(current) {
  const groups = MENUS[ctx.role] || MENUS.STAFF;
  return groups
    .map(
      (group) => `
    <div class="sidebar__group">
      <div class="sidebar__group-title">${escapeHtml(group.title)}</div>
      ${group.items
        .map(
          (item) => `
        <a class="sidebar__item ${
          current === item.href ? "is-active" : ""
        }" href="${item.href}" title="${escapeHtml(item.label)}">
          ${icon(item.icon)}
          <span class="sidebar__item-label">${escapeHtml(item.label)}</span>
        </a>`
        )
        .join("")}
    </div>`
    )
    .join("");
}

async function renderTopbarContext() {
  const box = $("#topbar-context");
  if (!box) return;

  try {
    const [year, semester] = await Promise.all([
      catalogApi.currentYear().catch(() => null),
      catalogApi.currentSemester().catch(() => null),
    ]);
    ctx.year = year;
    ctx.semester = semester;

    const yName = year?.year_name || year?.name || "—";
    const sName = semester?.semester_name || semester?.name || "—";

    box.innerHTML = `
      <span class="chip chip--neutral" title="Năm học hiện hành">${escapeHtml(yName)}</span>
      <span class="chip chip--neutral" title="Học kỳ hiện hành">${escapeHtml(sName)}</span>
    `;
  } catch {
    box.innerHTML = "";
  }
}

function bindShellEvents() {
  /* Thu gọn sidebar */
  const collapse = $("#btn-collapse");
  const sidebar = $("#sidebar");
  if (collapse && sidebar) {
    const saved = localStorage.getItem("sm_sidebar_collapsed") === "1";
    if (saved) sidebar.classList.add("is-collapsed");
    collapse.addEventListener("click", () => {
      const isCollapsed = sidebar.classList.toggle("is-collapsed");
      localStorage.setItem("sm_sidebar_collapsed", isCollapsed ? "1" : "0");
      collapse.querySelector("span").textContent = isCollapsed ? "Mở rộng" : "Thu gọn";
    });
  }

  /* Menu mobile */
  const mobileBtn = $("#btn-mobile-menu");
  if (mobileBtn && sidebar) {
    mobileBtn.style.display = window.innerWidth <= 767 ? "" : "none";
    mobileBtn.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("is-open");
      if (isOpen) {
        const backdrop = el("div", { class: "sidebar-backdrop" });
        backdrop.addEventListener("click", () => {
          sidebar.classList.remove("is-open");
          backdrop.remove();
        });
        document.body.appendChild(backdrop);
      } else {
        $$(".sidebar-backdrop").forEach((b) => b.remove());
      }
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 767) {
        sidebar.classList.remove("is-open");
        $$(".sidebar-backdrop").forEach((b) => b.remove());
      }
    });
  }

  /* Đăng xuất */
  const logoutBtn = $("#btn-logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        const { authApi } = await import("./api.js");
        await authApi.logout();
      } catch {
        /* Bỏ qua lỗi mạng — vẫn đăng xuất phía client */
      }
      TOKEN.clear();
      location.href = "/pages/login.html";
    });
  }
}

/* ------------------------------------------------------------------ */
/* Trợ giúp dùng chung cho màn hình                                    */
/* ------------------------------------------------------------------ */
export function pageContent() {
  return $("#page-content");
}

export function currentFile() {
  return location.pathname.split("/").pop() || "index.html";
}

/* Trang quay lại theo vai trò */
export function backLink() {
  return HOME_BY_ROLE[ctx.role] || "index.html";
}

/* Hiển thị lỗi API lên đầu nội dung trang */
export function renderPageError(container, err) {
  const message = err?.message || "Đã xảy ra sự cố khi tải dữ liệu.";
  const code = err?.code
    ? ` <span class="t-mono t-tertiary">${escapeHtml(err.code)}</span>`
    : "";
  container.innerHTML = `
    <div class="alert alert--danger" style="margin-bottom:24px">
      <span class="alert__icon">${icon("alert")}</span>
      <div class="alert__body">
        <div class="alert__title">Không tải được dữ liệu</div>
        <div class="alert__message">${escapeHtml(message)}${code}</div>
      </div>
      <button type="button" class="alert__close" data-reload
              aria-label="Tải lại">${icon("refresh")}</button>
    </div>
  `;
  container.querySelector("[data-reload]")?.addEventListener("click", () => location.reload());
}

export { TOKEN, API_BASE, statusInfo, initials, openModal, closeModal, bindBackdropClose };
