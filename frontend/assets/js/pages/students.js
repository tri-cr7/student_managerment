/* ==========================================================================
   STUDENTS — M4 danh sách học sinh / M5 tiếp nhận / M6 sửa / M10 import Excel
   ========================================================================== */

import { studentApi, classApi, catalogApi, ApiError } from "../api.js";
import { initShell, ctx, renderPageError, pageContent } from "../app.js";
import {
  $,
  $$,
  icon,
  iconButton,
  toast,
  toastSuccess,
  toastError,
  openModal,
  closeModal,
  bindBackdropClose,
  confirmDialog,
  setLoading,
  setFieldError,
  clearFieldError,
  renderSkeletonRows,
  renderEmptyRow,
  renderPagination,
  debounce,
  escapeHtml,
} from "../ui.js";
import {
  formatDate,
  formatGender,
  initials,
  statusChip,
  statusInfo,
  toDateInput,
} from "../format.js";

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */
const state = {
  page: 1,
  limit: 20,
  q: "",
  status: "",
  classId: "",
  grades: [],
  classes: [],
  students: [],
  editing: null,
  statusTarget: null,
  importFile: null,
  importResult: { success: [], errors: [] },
  importTab: "success",
};

/* ------------------------------------------------------------------ */
/* Khởi tạo                                                            */
/* ------------------------------------------------------------------ */
let container = null;

initShell({
  active: "students.html",
  roles: ["STAFF", "ACADEMIC"],
}).then(async () => {
  /* #page-content chỉ tồn tại sau khi shell đã dựng xong */
  container = pageContent();
  renderPage();
  await loadFilterOptions();
  await loadStudents();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Danh sách học sinh</h1>
          <p class="page-header__subtitle">
            Quản lý hồ sơ học sinh, tiếp nhận và cập nhật thông tin cá nhân.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--secondary" id="btn-import">
            ${icon("upload")} Import Excel
          </button>
          <button type="button" class="btn btn--primary" id="btn-admit">
            ${icon("plus")} Tiếp nhận học sinh
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
                   placeholder="Tìm theo họ tên hoặc mã học sinh"
                   value="${escapeHtml(state.q)}" aria-label="Tìm kiếm học sinh">
          </div>

          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-class"
                    aria-label="Lọc theo lớp">
              <option value="">Tất cả lớp</option>
            </select>
            <span class="field__chevron">▾</span>
          </div>

          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-status"
                    aria-label="Lọc theo trạng thái">
              <option value="">Tất cả trạng thái</option>
              <option value="DANG_HOC">Đang học</option>
              <option value="THOI_HOC">Thôi học</option>
              <option value="CHUYEN_TRUONG">Chuyển trường</option>
              <option value="TOT_NGHIEP">Tốt nghiệp</option>
            </select>
            <span class="field__chevron">▾</span>
          </div>

          <div class="toolbar__spacer"></div>

          <button type="button" class="btn btn--ghost btn--icon" id="btn-refresh"
                  aria-label="Tải lại" title="Tải lại">${icon("refresh")}</button>
        </div>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead class="table__head">
            <tr>
              <th>Mã HS</th>
              <th>Học sinh</th>
              <th>Giới tính</th>
              <th>Ngày sinh</th>
              <th>Lớp</th>
              <th>Trạng thái</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-students"></tbody>
        </table>
      </div>

      <div class="pagination" id="pagination-students"></div>
    </div>
  `;

  bindPageEvents();
}

/* ------------------------------------------------------------------ */
/* Tải dữ liệu bộ lọc                                                  */
/* ------------------------------------------------------------------ */
async function loadFilterOptions() {
  try {
    const [grades, classes] = await Promise.all([
      catalogApi.grades().catch(() => []),
      classApi.list({ limit: 100 }).catch(() => ({ items: [] })),
    ]);
    state.grades = grades || [];
    state.classes = classes?.items || [];

    const gradeSel = $("#admit-grade");
    if (gradeSel) {
      state.grades.forEach((g) => {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = g.grade_name || g.name || `Khối ${g.id}`;
        gradeSel.appendChild(opt);
      });
    }

    const classSel = $("#admit-class");
    if (classSel) {
      state.classes.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.class_name || c.name || `Lớp ${c.id}`;
        opt.dataset.gradeId = c.grade_id || "";
        opt.dataset.current = c.current_size_live ?? c.current_size ?? "";
        opt.dataset.max = c.max_size ?? "";
        classSel.appendChild(opt);
      });
    }

    const filterClass = $("#filter-class");
    if (filterClass) {
      state.classes.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.class_name || c.name || `Lớp ${c.id}`;
        filterClass.appendChild(opt);
      });
    }

    updateClassSizeHint();
  } catch {
    /* Không chặn render danh sách nếu lỗi bộ lọc */
  }
}

/* ------------------------------------------------------------------ */
/* Tải danh sách học sinh                                              */
/* ------------------------------------------------------------------ */
async function loadStudents() {
  const tbody = $("#tbody-students");
  if (!tbody) return;

  renderSkeletonRows(tbody, 7, 8);

  try {
    const res = await studentApi.list({
      page: state.page,
      limit: state.limit,
      q: state.q,
      status: state.status,
      class_id: state.classId,
    });

    state.students = res?.items || [];

    if (!state.students.length) {
      renderEmptyRow(
        tbody,
        7,
        state.q || state.status || state.classId
          ? "Không tìm thấy học sinh phù hợp với bộ lọc."
          : "Chưa có học sinh nào trong hệ thống.",
        `<button type="button" class="btn btn--primary" id="btn-empty-admit">
           ${icon("plus")} Tiếp nhận học sinh
         </button>`
      );
      $("#btn-empty-admit")?.addEventListener("click", openAdmitModal);
      renderPagination($("#pagination-students"), {
        page: 1,
        pages: 1,
        total: 0,
        limit: state.limit,
        label: "học sinh",
      });
      return;
    }

    tbody.innerHTML = state.students.map((s) => renderRow(s)).join("");
    bindRowActions();

    renderPagination($("#pagination-students"), {
      page: res.page || state.page,
      pages: res.pages || 1,
      total: res.total || 0,
      limit: res.per_page || state.limit,
      label: "học sinh",
    });
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 7, err?.message || "Không tải được danh sách học sinh.");
  }
}

function renderRow(s) {
  const info = statusInfo(s.status);
  return `
    <tr>
      <td class="table__cell--mono">${escapeHtml(s.student_code || "—")}</td>
      <td>
        <div class="student-cell">
          <span class="avatar avatar--32">${escapeHtml(initials(s.full_name))}</span>
          <span class="student-cell__name">${escapeHtml(s.full_name || "—")}</span>
        </div>
      </td>
      <td>${escapeHtml(formatGender(s.gender))}</td>
      <td>${escapeHtml(formatDate(s.date_of_birth))}</td>
      <td>${escapeHtml(s.class_name || "—")}</td>
      <td>${statusChip(s.status)}</td>
      <td>
        <div class="table__actions">
          <a class="btn btn--icon" href="student-detail.html?id=${s.id}"
             aria-label="Xem hồ sơ" title="Xem hồ sơ">${icon("eye")}</a>
          <button type="button" class="btn btn--icon" data-action="edit" data-id="${s.id}"
                  aria-label="Sửa" title="Sửa">${icon("edit")}</button>
          <button type="button" class="btn btn--icon" data-action="status" data-id="${s.id}"
                  aria-label="Đổi trạng thái" title="Đổi trạng thái">${icon("refresh")}</button>
          <button type="button" class="btn btn--icon btn--danger" data-action="delete" data-id="${s.id}"
                  aria-label="Xoá" title="Xoá">${icon("trash")}</button>
        </div>
      </td>
    </tr>
  `;
}

/* ------------------------------------------------------------------ */
/* Sự kiện trang                                                        */
/* ------------------------------------------------------------------ */
function bindPageEvents() {
  const search = $("#filter-q");
  search?.addEventListener(
    "input",
    debounce((e) => {
      state.q = e.target.value.trim();
      state.page = 1;
      loadStudents();
    }, 400)
  );

  $("#filter-class")?.addEventListener("change", (e) => {
    state.classId = e.target.value;
    state.page = 1;
    loadStudents();
  });

  $("#filter-status")?.addEventListener("change", (e) => {
    state.status = e.target.value;
    state.page = 1;
    loadStudents();
  });

  $("#btn-refresh")?.addEventListener("click", () => loadStudents());
  $("#btn-admit")?.addEventListener("click", openAdmitModal);
  $("#btn-import")?.addEventListener("click", openImportModal);

  /* Phân trang */
  $("#pagination-students")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.page);
    loadStudents();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  /* Đóng modal */
  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-admit"));
  bindBackdropClose($("#modal-edit"));
  bindBackdropClose($("#modal-import"));
  bindBackdropClose($("#modal-status"));

  /* Form: tiếp nhận */
  $("#form-admit")?.addEventListener("submit", onAdmitSubmit);

  /* Form: sửa */
  $("#form-edit")?.addEventListener("submit", onEditSubmit);

  /* Form: đổi trạng thái */
  $("#form-status")?.addEventListener("submit", onStatusSubmit);

  /* Form: import */
  setupImport();
}

/* ------------------------------------------------------------------ */
/* Thao tác trên dòng                                                  */
/* ------------------------------------------------------------------ */
function bindRowActions() {
  $$("#tbody-students [data-action]").forEach((btn) => {
    const id = Number(btn.dataset.id);
    const action = btn.dataset.action;

    if (action === "edit") {
      btn.addEventListener("click", () => openEditModal(id));
    } else if (action === "status") {
      btn.addEventListener("click", () => openStatusModal(id));
    } else if (action === "delete") {
      btn.addEventListener("click", () => handleDelete(id));
    }
  });
}

/* ------------------------------------------------------------------ */
/* M5 — Tiếp nhận học sinh                                             */
/* ------------------------------------------------------------------ */
function openAdmitModal() {
  const form = $("#form-admit");
  form.reset();
  clearAllErrors(form);
  hideAlert("admit-alert");
  updateClassSizeHint();

  const note = $("#admit-note");
  if (note) {
    note.textContent = `Tuổi tiếp nhận: ${ctx.minAge} – ${ctx.maxAge} tuổi`;
  }

  openModal($("#modal-admit"));
  setTimeout(() => $("#admit-name")?.focus(), 60);
}

function updateClassSizeHint() {
  const classSel = $("#admit-class");
  const hint = $("#hint-class-size");
  if (!classSel || !hint) return;

  const opt = classSel.selectedOptions[0];
  if (!opt || !opt.value) {
    hint.textContent = "Học sinh sẽ được phân lớp sau nếu chưa chọn lớp.";
    return;
  }
  const current = opt.dataset.current;
  const max = opt.dataset.max;
  const limit = max || ctx.maxClassSize;
  const cur = current === "" || current === undefined ? "0" : current;
  hint.textContent = `Sĩ số lớp: ${cur} / ${limit}`;
}

/* Kiểm tra tuổi theo quy định động */
function checkAgeHint() {
  const dob = $("#admit-dob")?.value;
  const hint = $("#hint-age");
  if (!hint) return;

  if (!dob) {
    hint.textContent = "";
    clearFieldError($("#admit-dob"));
    return;
  }

  const birth = new Date(dob);
  if (Number.isNaN(birth.getTime())) return;

  const now = new Date();
  let age = now.getFullYear() - birth.getFullYear();
  const m = now.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age -= 1;

  const min = ctx.minAge;
  const max = ctx.maxAge;

  if (age < min || age > max) {
    hint.textContent = `Tuổi hiện tại: ${age} tuổi — ngoài khoảng cho phép (${min}–${max}).`;
    setFieldError($("#admit-dob"), `Tuổi phải từ ${min} đến ${max} tuổi.`);
  } else {
    hint.textContent = `Tuổi hiện tại: ${age} tuổi — hợp lệ.`;
    clearFieldError($("#admit-dob"));
  }
}

async function onAdmitSubmit(e) {
  e.preventDefault();
  hideAlert("admit-alert");

  const form = e.target;
  const btn = $("#btn-admit");
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.gender = payload.gender || null;
  payload.email = payload.email || null;
  payload.phone = payload.phone || null;
  payload.address = payload.address || null;

  let ok = true;
  ["full_name", "student_code", "date_of_birth", "gender", "grade_id"].forEach((name) => {
    const input = form.querySelector(`[name="${name}"]`);
    if (!input) return;
    if (!input.value.trim()) {
      setFieldError(input, "Trường này là bắt buộc.");
      ok = false;
    } else {
      clearFieldError(input);
    }
  });
  if (!ok) return;

  setLoading(btn, true, "Đang lưu...");
  try {
    const res = await studentApi.admit(payload);
    toastSuccess(res?.message || `Đã tiếp nhận học sinh ${payload.full_name}.`);
    closeModal($("#modal-admit"));
    await loadStudents();
    await loadFilterOptions();
  } catch (err) {
    showApiError("admit-alert", err);
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* M6 — Sửa hồ sơ                                                      */
/* ------------------------------------------------------------------ */
async function openEditModal(id) {
  const student = state.students.find((s) => s.id === id);
  if (!student) return;

  state.editing = student;
  hideAlert("edit-alert");

  $("#edit-title").textContent = "Cập nhật hồ sơ học sinh";
  $("#edit-subtitle").textContent = `${student.full_name} — ${student.student_code}`;

  const fields = $("#edit-fields");
  fields.innerHTML = `
    <div class="field">
      <label class="field__label" for="edit-name">Họ và tên <span class="field__required">*</span></label>
      <input class="field__input" id="edit-name" name="full_name"
             value="${escapeHtml(student.full_name || "")}" required>
    </div>
    <div class="field">
      <label class="field__label" for="edit-dob">Ngày sinh</label>
      <input class="field__input" id="edit-dob" name="date_of_birth" type="date"
             value="${escapeHtml(toDateInput(student.date_of_birth))}">
    </div>
    <div class="field">
      <label class="field__label" for="edit-gender">Giới tính</label>
      <div class="field__select-wrap">
        <select class="field__select" id="edit-gender" name="gender">
          <option value="">-- Chưa cập nhật --</option>
          <option value="NAM" ${student.gender === "NAM" ? "selected" : ""}>Nam</option>
          <option value="NU" ${student.gender === "NU" ? "selected" : ""}>Nữ</option>
          <option value="KHAC" ${student.gender === "KHAC" ? "selected" : ""}>Khác</option>
        </select>
        <span class="field__chevron">▾</span>
      </div>
    </div>
    <div class="field">
      <label class="field__label" for="edit-phone">Số điện thoại</label>
      <input class="field__input" id="edit-phone" name="phone" inputmode="tel"
             value="${escapeHtml(student.phone || "")}">
    </div>
    <div class="field">
      <label class="field__label" for="edit-email">Email</label>
      <input class="field__input" id="edit-email" name="email" type="email"
             value="${escapeHtml(student.email || "")}">
    </div>
    <div class="field">
      <label class="field__label" for="edit-cid">Số CCCD/CMND</label>
      <input class="field__input t-mono" id="edit-cid" name="citizen_id"
             value="${escapeHtml(student.citizen_id || "")}">
    </div>
    <div class="field">
      <label class="field__label" for="edit-parent">Tên phụ huynh</label>
      <input class="field__input" id="edit-parent" name="parent_name"
             value="${escapeHtml(student.parent_name || "")}">
    </div>
    <div class="field">
      <label class="field__label" for="edit-parent-phone">Điện thoại phụ huynh</label>
      <input class="field__input" id="edit-parent-phone" name="parent_phone" inputmode="tel"
             value="${escapeHtml(student.parent_phone || "")}">
    </div>
    <div class="field field--full">
      <label class="field__label" for="edit-address">Địa chỉ</label>
      <input class="field__input" id="edit-address" name="address"
             value="${escapeHtml(student.address || "")}">
    </div>
  `;

  openModal($("#modal-edit"));
}

async function onEditSubmit(e) {
  e.preventDefault();
  hideAlert("edit-alert");

  const form = e.target;
  const btn = $("#btn-edit");
  const payload = Object.fromEntries(new FormData(form).entries());

  if (!payload.full_name?.trim()) {
    setFieldError(form.querySelector('[name="full_name"]'), "Họ tên là bắt buộc.");
    return;
  }

  setLoading(btn, true, "Đang lưu...");
  try {
    const res = await studentApi.update(state.editing.id, payload);
    toastSuccess(res?.message || "Đã cập nhật hồ sơ học sinh.");
    closeModal($("#modal-edit"));
    await loadStudents();
  } catch (err) {
    showApiError("edit-alert", err);
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* Đổi trạng thái                                                       */
/* ------------------------------------------------------------------ */
function openStatusModal(id) {
  const student = state.students.find((s) => s.id === id);
  if (!student) return;

  state.statusTarget = student;
  hideAlert("status-alert");
  $("#status-subtitle").textContent = `${student.full_name} — ${student.student_code}`;
  $("#status-select").value = student.status || "DANG_HOC";

  openModal($("#modal-status"));
}

async function onStatusSubmit(e) {
  e.preventDefault();
  hideAlert("status-alert");

  const btn = $("#btn-status");
  const status = $("#status-select").value;

  setLoading(btn, true, "Đang cập nhật...");
  try {
    const res = await studentApi.updateStatus(state.statusTarget.id, status);
    toastSuccess(res?.message || "Đã cập nhật trạng thái học sinh.");
    closeModal($("#modal-status"));
    await loadStudents();
  } catch (err) {
    showApiError("status-alert", err);
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* Xoá hồ sơ — phân biệt HARD / SOFT                                   */
/* ------------------------------------------------------------------ */
async function handleDelete(id) {
  const student = state.students.find((s) => s.id === id);
  if (!student) return;

  const confirmed = await confirmDialog({
    title: "Xoá hồ sơ học sinh",
    message: `Bạn có chắc muốn xoá hồ sơ của "${student.full_name}" (${student.student_code})?`,
    detail:
      "Nếu học sinh đã có phân bổ lớp hoặc điểm, hệ thống chuyển hồ sơ sang trạng thái " +
      "'Thôi học' thay vì xoá vĩnh viễn. Hành động này không thể hoàn tác.",
    confirmText: "Tiếp tục",
    danger: true,
  });
  if (!confirmed) return;

  try {
    const res = await studentApi.remove(id);
    toastSuccess(res?.message || "Đã xử lý yêu cầu xoá hồ sơ.");
    await loadStudents();
  } catch (err) {
    toastError(err?.message || "Không thể xoá hồ sơ.");
  }
}

/* ------------------------------------------------------------------ */
/* M10 — Import Excel                                                   */
/* ------------------------------------------------------------------ */
function openImportModal() {
  const form = $("#form-import");
  form.reset();
  state.importFile = null;
  state.importResult = { success: [], errors: [] };
  state.importTab = "success";

  hideAlert("import-alert");
  $("#import-result").classList.add("hidden");
  $("#btn-import").disabled = true;
  $("#dropzone-title").textContent = "Kéo thả file .xlsx vào đây";
  $("#dropzone-sub").textContent = "hoặc bấm để chọn file (tối đa 10MB)";
  $("#import-note").textContent = "";

  openModal($("#modal-import"));
}

function setupImport() {
  const dropzone = $("#dropzone");
  const fileInput = $("#file-input");
  if (!dropzone || !fileInput) return;

  $("#dropzone-icon").innerHTML = icon("upload");

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("is-over");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("is-over");
    })
  );

  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFileSelected(file);
  });

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelected(file);
  });

  $("#btn-import")?.addEventListener("click", runImport);

  $$("[data-tab]").forEach((tab) =>
    tab.addEventListener("click", () => {
      state.importTab = tab.dataset.tab;
      $$("[data-tab]").forEach((t) => t.classList.toggle("is-active", t === tab));
      renderImportRows();
    })
  );
}

function handleFileSelected(file) {
  const valid = /\.(xlsx|xls)$/i.test(file.name);
  if (!valid) {
    toastError("Định dạng file không hợp lệ. Vui lòng chọn file .xlsx hoặc .xls.");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    toastError("Dung lượng file vượt quá 10MB.");
    return;
  }

  state.importFile = file;
  $("#dropzone-title").textContent = file.name;
  $("#dropzone-sub").textContent = `${(file.size / 1024).toFixed(0)} KB — sẵn sàng import`;
  $("#btn-import").disabled = false;
}

async function runImport() {
  if (!state.importFile) return;

  const btn = $("#btn-import");
  hideAlert("import-alert");
  setLoading(btn, true, "Đang import...");

  try {
    const res = await studentApi.importExcel(state.importFile);
    const success = res?.success_items || res?.success || [];
    const errors = res?.errors || res?.error_items || [];

    state.importResult = { success, errors };
    state.importTab = errors.length ? "errors" : "success";

    $("#count-success").textContent = success.length;
    $("#count-errors").textContent = errors.length;
    $$("[data-tab]").forEach((t) =>
      t.classList.toggle("is-active", t.dataset.tab === state.importTab)
    );
    renderImportRows();
    $("#import-result").classList.remove("hidden");

    if (!errors.length) {
      toastSuccess(`Đã import thành công ${success.length} học sinh.`);
    } else {
      toastWarning(
        `Import xong: ${success.length} thành công, ${errors.length} dòng lỗi.`,
        "Import có lỗi"
      );
    }

    await loadStudents();
  } catch (err) {
    showApiError("import-alert", err);
  } finally {
    setLoading(btn, false);
  }
}

function renderImportRows() {
  const tbody = $("#import-tbody");
  if (!tbody) return;

  const rows =
    state.importTab === "success" ? state.importResult.success : state.importResult.errors;

  if (!rows.length) {
    tbody.innerHTML = `
      <tr><td colspan="4" class="t-center t-secondary" style="padding:24px">
        ${state.importTab === "success"
          ? "Không có bản ghi thành công."
          : "Không có dòng lỗi nào."}
      </td></tr>`;
    return;
  }

  tbody.innerHTML = rows
    .map((r, i) => {
      const err = r.error || r.message || r.reason || "";
      return `
        <tr>
          <td class="table__cell--num">${escapeHtml(r.row ?? r.row_number ?? i + 1)}</td>
          <td class="table__cell--mono">${escapeHtml(r.student_code || r.code || "—")}</td>
          <td>${escapeHtml(r.full_name || r.name || "—")}</td>
          <td class="${err ? "t-danger" : "t-secondary"}">${escapeHtml(err || "—")}</td>
        </tr>`;
    })
    .join("");
}

/* ------------------------------------------------------------------ */
/* Helpers dùng chung                                                   */
/* ------------------------------------------------------------------ */
function clearAllErrors(form) {
  $$(".field__input, .field__select, .field__textarea", form).forEach(clearFieldError);
  const ageHint = $("#hint-age");
  if (ageHint) ageHint.textContent = "";
}

function showAlert(containerId, type, title, message) {
  const box = $("#" + containerId);
  if (!box) return;
  box.className = `alert alert--${type}`;
  box.innerHTML = `
    <span class="alert__icon">${icon(type === "danger" ? "alert" : "info")}</span>
    <div class="alert__body">
      <div class="alert__title">${escapeHtml(title)}</div>
      ${message ? `<div class="alert__message">${escapeHtml(message)}</div>` : ""}
    </div>`;
  box.classList.remove("hidden");
}

function hideAlert(containerId) {
  const box = $("#" + containerId);
  if (box) {
    box.classList.add("hidden");
    box.innerHTML = "";
  }
}

/* Hiển thị lỗi API — kèm khoảng quy định động nếu có */
function showApiError(containerId, err) {
  const message = err?.message || "Đã xảy ra sự cố. Vui lòng thử lại.";
  const rules = err?.currentRules;

  let extra = "";
  if (rules) {
    const parts = [];
    if (rules.MIN_AGE !== undefined) parts.push(`Tuổi tối thiểu: ${rules.MIN_AGE}`);
    if (rules.MAX_AGE !== undefined) parts.push(`Tuổi tối đa: ${rules.MAX_AGE}`);
    if (parts.length) extra = ` (${parts.join(" — ")})`;
  }

  showAlert(containerId, "danger", "Không thực hiện được", message + extra);
}

/* Bind kiểm tra tuổi khi mở modal */
document.addEventListener("input", (e) => {
  if (e.target?.id === "admit-dob") checkAgeHint();
});
document.addEventListener("change", (e) => {
  if (e.target?.id === "admit-class") updateClassSizeHint();
});
