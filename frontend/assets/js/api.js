/* ==========================================================================
   API — fetch wrapper + JWT (access/refresh) + xử lý lỗi tập trung
   Backend: Flask + flask-jwt-extended, header "Authorization: Bearer <token>"
   ========================================================================== */

/* API_BASE: mặc định dùng cùng origin với trang hiện tại (khi Flask phục vụ
   giao diện). Có thể ghi đè bằng window.API_BASE khi chạy static server riêng. */
const API_BASE =
  window.API_BASE ||
  (location.port === "5500" ? "http://127.0.0.1:5001" : location.origin);
const API_PREFIX = "/api/v1";

const TOKEN_KEY = "sm_access_token";
const REFRESH_KEY = "sm_refresh_token";
const USER_KEY = "sm_user";

export const TOKEN = {
  get access() {
    return localStorage.getItem(TOKEN_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  get user() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  },
  set({ token, refresh_token, user }) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  },
  get role() {
    return TOKEN.user?.role || null;
  },
};

/* ------------------------------------------------------------------ */
/* Lỗi API — mang theo mã lỗi nghiệp vụ để UI biểu diễn đúng          */
/* ------------------------------------------------------------------ */
export class ApiError extends Error {
  constructor(message, { status, code, data } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.data = data || {};
  }

  /* Lỗi 422 kèm current_rules → UI hiển thị khoảng quy định động */
  get currentRules() {
    return this.data?.current_rules || null;
  }

  /* Lỗi vượt sĩ số → hiển thị current_size / max_size riêng */
  get classSize() {
    return {
      current: this.data?.current_size ?? null,
      max: this.data?.max_size ?? null,
    };
  }
}

function buildUrl(path, params) {
  let url = path.startsWith("http") ? path : API_BASE + API_PREFIX + path;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.append(k, v);
    });
    const s = qs.toString();
    if (s) url += (url.includes("?") ? "&" : "?") + s;
  }
  return url;
}

async function parseBody(res) {
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    try {
      return await res.json();
    } catch {
      return {};
    }
  }
  return {};
}

/* ------------------------------------------------------------------ */
/* Refresh token — chỉ 1 request đồng thời được refresh                */
/* ------------------------------------------------------------------ */
let refreshPromise = null;

async function refreshAccessToken() {
  if (!TOKEN.refresh) return false;
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await fetch(API_BASE + API_PREFIX + "/auth/refresh", {
        method: "POST",
        headers: { Authorization: "Bearer " + TOKEN.refresh },
      });
      if (!res.ok) return false;
      const body = await parseBody(res);
      if (body?.data?.token) {
        localStorage.setItem(TOKEN_KEY, body.data.token);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/* ------------------------------------------------------------------ */
/* Request chính                                                       */
/* ------------------------------------------------------------------ */
/* Các endpoint xác thực: 401 ở đây là "sai thông tin", không phải hết phiên. */
function isAuthEntry(path) {
  return /\/auth\/(login|refresh|forgot-password|reset-password|verify-reset-otp)/.test(path);
}

async function request(path, { method = "GET", body, params, headers, raw } = {}) {
  const opts = {
    method,
    headers: { Accept: "application/json", ...(headers || {}) },
  };

  if (TOKEN.access) {
    opts.headers.Authorization = "Bearer " + TOKEN.access;
  }

  if (raw) {
    opts.body = raw;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  const hadAuth = !!TOKEN.access;
  let res = await fetch(buildUrl(path, params), opts);

  /* Token hết hạn → thử refresh 1 lần rồi retry.
     Chỉ refresh khi request có gửi Authorization header; nếu không (ví dụ
     đăng nhập sai mật khẩu) thì 401 là lỗi xác thực, không phải hết phiên. */
  if (res.status === 401 && hadAuth && TOKEN.refresh && !isAuthEntry(path)) {
    const ok = await refreshAccessToken();
    if (ok) {
      opts.headers.Authorization = "Bearer " + TOKEN.access;
      res = await fetch(buildUrl(path, params), opts);
    }
  }

  if (res.status === 401) {
    const payload401 = await parseBody(res);
    const isLoginAttempt = isAuthEntry(path);

    /* Chỉ xoá phiên khi thực sự đang gọi API có bảo vệ. */
    if (hadAuth && !isLoginAttempt) {
      TOKEN.clear();
      if (!location.pathname.includes("login")) {
        location.href = "/login.html?redirect=" + encodeURIComponent(location.pathname);
      }
    }

    throw new ApiError(
      payload401?.message || "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại!",
      {
        status: 401,
        code: payload401?.error || "UNAUTHORIZED",
        data: payload401,
      }
    );
  }

  const payload = await parseBody(res);

  if (!res.ok) {
    throw new ApiError(payload?.message || "Đã xảy ra sự cố. Vui lòng thử lại.", {
      status: res.status,
      code: payload?.error || "UNKNOWN",
      data: payload,
    });
  }

  /* Nhiều endpoint bọc trong { success, message, data } */
  if (payload && typeof payload === "object" && "data" in payload && "success" in payload) {
    return payload.data;
  }
  return payload;
}

export const api = {
  get: (path, params) => request(path, { method: "GET", params }),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  del: (path, body) => request(path, { method: "DELETE", body }),
  upload: (path, formData) => request(path, { method: "POST", raw: formData }),
  raw: request,
};

/* ------------------------------------------------------------------ */
/* Chuẩn hoá response dạng danh sách phân trang                        */
/*                                                                    */
/* Backend trả về 3 kiểu khác nhau:                                   */
/*   { items, total, page, pages, per_page }   ← /students             */
/*   { data: [...], total, page, limit }       ← /classes, /assignments */
/*   { logs, total, page, limit }              ← /admin/audit-logs      */
/* Hàm này gom về 1 shape: { items, total, page, pages, per_page }     */
/* ------------------------------------------------------------------ */
export function normalizeList(res, itemsKey = null) {
  if (Array.isArray(res)) {
    return {
      items: res,
      total: res.length,
      page: 1,
      pages: 1,
      per_page: res.length || 20,
    };
  }
  if (!res || typeof res !== "object") {
    return { items: [], total: 0, page: 1, pages: 1, per_page: 20 };
  }

  let items = res.items;
  if (!items) {
    if (itemsKey && Array.isArray(res[itemsKey])) items = res[itemsKey];
    else if (Array.isArray(res.data)) items = res.data;
  }
  items = Array.isArray(items) ? items : [];

  const total = res.total ?? items.length;
  const perPage = res.per_page ?? res.limit ?? 20;
  const page = res.page ?? 1;
  const pages = res.pages ?? Math.max(1, Math.ceil(total / perPage));

  return { items, total, page, pages, per_page: perPage };
}

/* ------------------------------------------------------------------ */
/* Endpoint helpers — gom theo màn hình                               */
/* ------------------------------------------------------------------ */
export const authApi = {
  login: (username, password) =>
    api.post("/auth/login", { username, password }),
  me: () => api.get("/auth/me"),
  logout: () => api.post("/auth/logout"),
  forgotPassword: (ident) => api.post("/auth/forgot-password", { email: ident }),
  /* Bước 1 — xác thực OTP, trả reset_token dùng cho bước 2 */
  verifyResetOtp: (ident, otpCode) =>
    api.post("/auth/verify-reset-otp", { email: ident, otp_code: otpCode }),
  resetPassword: (payload) => api.post("/auth/reset-password", payload),
};

/* ------------------------------------------------------------------ */
/* State luồng quên mật khẩu (2 bước) — dùng sessionStorage           */
/* Session tự mất khi đóng tab → không lưu secret lâu dài.            */
/* ------------------------------------------------------------------ */
const RESET_FLOW_KEY = "sm_reset_flow";

export const RESET_FLOW = {
  get() {
    try {
      return JSON.parse(sessionStorage.getItem(RESET_FLOW_KEY) || "null");
    } catch {
      return null;
    }
  },
  set(data) {
    sessionStorage.setItem(RESET_FLOW_KEY, JSON.stringify(data));
  },
  clear() {
    sessionStorage.removeItem(RESET_FLOW_KEY);
  },
};

export const studentApi = {
  list: (params) => api.get("/students", params).then((r) => normalizeList(r)),
  detail: (id) => api.get(`/students/${id}`),
  byCode: (code) => api.get(`/students/code/${encodeURIComponent(code)}`),
  admit: (payload) => api.post("/students/admit", payload),
  update: (id, payload) => api.put(`/students/${id}`, payload),
  remove: (id) => api.del(`/students/${id}`),
  updateStatus: (id, status) => api.patch(`/students/${id}/status`, { status }),
  importExcel: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.upload("/students/import-excel", fd);
  },
  printUrl: (id, fmt = "pdf") =>
    `${API_BASE}${API_PREFIX}/students/${id}/print?format=${fmt}`,
  /* Bảng điểm toàn bộ của 1 học sinh (chỉ điểm chính thức) */
  scores: (id, includeDraft = false) =>
    api.get(`/scores/student/${id}`, includeDraft ? { include_draft: true } : null),
};

export const classApi = {
  list: (params) => api.get("/classes", params).then((r) => normalizeList(r)),
  detail: (id) => api.get(`/classes/${id}`),
  create: (payload) => api.post("/classes", payload),
  update: (id, payload) => api.put(`/classes/${id}`, payload),
  remove: (id) => api.del(`/classes/${id}`),
  enroll: (id, payload) => api.post(`/classes/${id}/enroll`, payload),
  transfer: (payload) => api.post("/classes/transfer", payload),
  students: (id) => api.get(`/classes/${id}/students`),
  setHomeroom: (id, teacherId) => api.put(`/classes/${id}/homeroom`, { teacher_id: teacherId }),
};

export const teacherApi = {
  myAssignments: () => api.get("/assignments/my"),
  assignmentScores: (id) => api.get(`/scores/assignment/${id}`),
  columnConfig: () => api.get("/scores/columns/config"),
  saveBatch: (payload) => api.post("/scores/batch", payload),
  updateScore: (id, payload) => api.put(`/scores/${id}`, payload),
  searchStudents: (params) => api.get("/students/search", params),
  mySubmissions: () => api.get("/score-submissions/my"),
  createSubmission: (payload) => api.post("/score-submissions", payload),
  cancelSubmission: (id, payload) => api.put(`/score-submissions/${id}/cancel`, payload),
  myChangeRequests: () => api.get("/score-requests/my"),
  createChangeRequest: (payload) => api.post("/score-requests", payload),
};

export const academicApi = {
  assignments: (params) => api.get("/assignments", params).then((r) => normalizeList(r)),
  assignment: (id) => api.get(`/assignments/${id}`),
  createAssignment: (p) => api.post("/assignments", p),
  updateAssignment: (id, p) => api.put(`/assignments/${id}`, p),
  removeAssignment: (id) => api.del(`/assignments/${id}`),
  setLock: (id, isLocked) => api.patch(`/assignments/${id}/lock`, { is_locked: isLocked }),
  submissions: (params) => api.get("/score-submissions", params).then((r) => normalizeList(r)),
  submission: (id) => api.get(`/score-submissions/${id}`),
  approveSubmission: (id, p) => api.put(`/score-submissions/${id}/approve`, p),
  rejectSubmission: (id, p) => api.put(`/score-submissions/${id}/reject`, p),
  changeRequests: (params) => api.get("/score-requests", params).then((r) => normalizeList(r)),
  changeRequest: (id) => api.get(`/score-requests/${id}`),
  changeDiff: (id) => api.get(`/score-requests/${id}/diff`),
  approveChangeRequest: (id, p) => api.put(`/score-requests/${id}/approve`, p),
  rejectChangeRequest: (id, p) => api.put(`/score-requests/${id}/reject`, p),
};

export const catalogApi = {
  rules: () => api.get("/rules"),
  rule: (key) => api.get(`/rules/${key}`),
  updateRule: (key, value) => api.put(`/rules/${key}`, { rule_value: value }),
  bulkRules: (rules) => api.put("/rules/bulk", { rules }),
  subjects: (params) => api.get("/subjects", params),
  subject: (id) => api.get(`/subjects/${id}`),
  subjectsByGrade: (gradeId) => api.get(`/subjects/grade/${gradeId}`),
  createSubject: (p) => api.post("/subjects", p),
  updateSubject: (id, p) => api.put(`/subjects/${id}`, p),
  removeSubject: (id) => api.del(`/subjects/${id}`),
  grades: () => api.get("/grades"),
  academicYears: () => api.get("/academic-years"),
  currentYear: () => api.get("/academic-years/current"),
  semesters: (params) => api.get("/semesters", params),
  currentSemester: () => api.get("/semesters/current"),
};

export const adminApi = {
  users: (params) => api.get("/admin/users", params).then((r) => normalizeList(r)),
  user: (id) => api.get(`/admin/users/${id}`),
  createUser: (p) => api.post("/admin/users", p),
  updateUser: (id, p) => api.put(`/admin/users/${id}`, p),
  lockUser: (id, isLocked) =>
    api.patch(`/admin/users/${id}/lock`, {
      is_locked: isLocked,
      reset_failed_attempts: !isLocked,
    }),
  resetPassword: (id, newPassword) =>
    api.post(`/admin/users/${id}/reset-password`, { new_password: newPassword }),
  setRole: (id, role) => api.put(`/admin/users/${id}/role`, { role }),
  auditLogs: (params) => api.get("/admin/audit-logs", params).then((r) => normalizeList(r, "logs")),
  auditActions: () => api.get("/admin/audit-logs/actions").then((r) => r?.actions || []),
  auditLog: (id) => api.get(`/admin/audit-logs/${id}`),
  auditLogExportUrl: (params) =>
    `${API_BASE}${API_PREFIX}/admin/audit-logs/export${
      params && Object.keys(params).length
        ? "?" + new URLSearchParams(params).toString()
        : ""
    }`,
};

export const reportApi = {
  subjectSummary: (subjectId, semesterId) =>
    api.get("/reports/subject-summary", { subject_id: subjectId, semester_id: semesterId }),
  chartData: (subjectId, semesterId, type = "bar") =>
    api.get("/reports/chart-data", {
      subject_id: subjectId,
      semester_id: semesterId,
      chart_type: type,
    }),
  gradeSummary: (gradeId, semesterId) =>
    api.get("/reports/grade-summary", { grade_id: gradeId, semester_id: semesterId }),
  exportUrl: (fmt, subjectId, semesterId) =>
    `${API_BASE}${API_PREFIX}/reports/export/${fmt}?subject_id=${subjectId}&semester_id=${semesterId}`,
};

export const profileApi = {
  get: () => api.get("/profile"),
  update: (p) => api.patch("/profile", p),
  changePassword: (p) => api.post("/profile/change-password", p),
  requestOtp: (p) => api.post("/profile/change-password/request", p),
  confirmPassword: (p) => api.post("/profile/change-password/confirm", p),
};

export { API_BASE, API_PREFIX };
