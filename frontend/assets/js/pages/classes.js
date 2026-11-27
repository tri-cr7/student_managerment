/* ==========================================================================
   CLASSES — M7 danh sách lớp / M8 phân bổ HS / M9 điều chuyển lớp
   ========================================================================== */

import {
  classApi,
  studentApi,
  catalogApi,
  adminApi,
  API_BASE,
  API_PREFIX,
} from "../api.js";
import { initShell, ctx, renderPageError, pageContent } from "../app.js";
import {
  $,
  $$,
  icon,
  toastSuccess,
  toastError,
  toastWarning,
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
  toDateInput,
} from "../format.js";

/* ------------------------------------------------------------------ */
/* State                                                               */
/* ------------------------------------------------------------------ */
const state = {
  page: 1,
  limit: 20,
  gradeId: "",
  yearId: "",
  classes: [],
  grades: [],
  years: [],
  teachers: [],
  editing: null,
  detailClass: null,
  enroll: {
    classId: null,
    className: "",
    maxSize: 40,
    currentSize: 0,
    selected: new Set(),
    available: [],
    enrolled: [],
    search: "",
  },
};

let container = null;

/* ------------------------------------------------------------------ */
/* Khởi tạo                                                            */
/* ------------------------------------------------------------------ */
initShell({
  active: "classes.html",
  roles: ["STAFF", "ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadOptions();
  await loadClasses();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Quản lý lớp học</h1>
          <p class="page-header__subtitle">
            Tạo lớp, phân bổ học sinh và điều chuyển giữa các lớp.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--secondary" id="btn-transfer">
            ${icon("swap")} Điều chuyển lớp
          </button>
          <button type="button" class="btn btn--primary" id="btn-create-class">
            ${icon("plus")} Tạo lớp học
          </button>
        </div>
      </div>
    </header>

    <div class="card">
      <div class="card__body card__body--tight">
        <div class="toolbar">
          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-grade"
                    aria-label="Lọc theo khối">
              <option value="">Tất cả khối</option>
            </select>
            <span class="field__chevron">▾</span>
          </div>

          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-year"
                    aria-label="Lọc theo năm học">
              <option value="">Tất cả năm học</option>
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
              <th>Lớp</th>
              <th>Khối</th>
              <th>Năm học</th>
              <th>GV chủ nhiệm</th>
              <th style="width:150px">Sĩ số</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-classes"></tbody>
        </table>
      </div>

      <div class="pagination" id="pagination-classes"></div>
    </div>
  `;

  bindPageEvents();
}

/* ------------------------------------------------------------------ */
/* Tải dữ liệu danh mục                                                 */
/* ------------------------------------------------------------------ */
async function loadOptions() {
  try {
    const [grades, years, teachers] = await Promise.all([
      catalogApi.grades().catch(() => []),
      catalogApi.academicYears().catch(() => []),
      adminApi.users().catch(() => []),
    ]);

    state.grades = grades || [];
    state.years = years || [];
    state.teachers = (teachers || []).filter((u) => u.role === "TEACHER");

    fillSelect($("#filter-grade"), state.grades, (g) => g.grade_name || g.name);
    fillSelect($("#filter-year"), state.years, (y) => y.year_name || y.name);
    fillSelect($("#class-grade"), state.grades, (g) => g.grade_name || g.name);
    fillSelect($("#class-year"), state.years, (y) => y.year_name || y.name);
    fillSelect($("#class-teacher"), state.teachers, (t) => t.full_name, "Chưa phân công");

    /* Mặc định chọn năm học hiện hành */
    const yearSel = $("#class-year");
    if (yearSel && ctx.year?.id) yearSel.value = ctx.year.id;
    const filterYear = $("#filter-year");
    if (filterYear && ctx.year?.id) {
      filterYear.value = ctx.year.id;
      state.yearId = ctx.year.id;
    }
  } catch {
    /* Không chặn render danh sách */
  }
}

function fillSelect(select, items, labelFn, emptyLabel = null) {
  if (!select) return;
  if (emptyLabel) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = emptyLabel;
    select.appendChild(opt);
  }
  (items || []).forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = labelFn(item);
    select.appendChild(opt);
  });
}

/* ------------------------------------------------------------------ */
/* Tải danh sách lớp                                                    */
/* ------------------------------------------------------------------ */
async function loadClasses() {
  const tbody = $("#tbody-classes");
  if (!tbody) return;

  renderSkeletonRows(tbody, 6, 6);

  try {
    const res = await classApi.list({
      page: state.page,
      limit: state.limit,
      grade_id: state.gradeId,
      academic_year_id: state.yearId,
    });

    state.classes = res?.items || [];

    if (!state.classes.length) {
      renderEmptyRow(
        tbody,
        6,
        "Chưa có lớp học nào.",
        `<button type="button" class="btn btn--primary" id="btn-empty-create">
           ${icon("plus")} Tạo lớp học
         </button>`
      );
      $("#btn-empty-create")?.addEventListener("click", openClassModal);
      renderPagination($("#pagination-classes"), {
        page: 1,
        pages: 1,
        total: 0,
        limit: state.limit,
        label: "lớp",
      });
      return;
    }

    tbody.innerHTML = state.classes.map((c) => renderRow(c)).join("");
    bindRowActions();

    renderPagination($("#pagination-classes"), {
      page: res.page || state.page,
      pages: res.pages || 1,
      total: res.total || 0,
      limit: res.per_page || state.limit,
      label: "lớp",
    });
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 6, err?.message || "Không tải được danh sách lớp học.");
  }
}

function renderRow(c) {
  const current = c.current_size_live ?? c.current_size ?? 0;
  const max = c.max_size ?? ctx.maxClassSize;
  const pct = Math.min(100, Math.round((current / max) * 100));
  const tone = pct >= 100 ? "danger" : pct >= 80 ? "warning" : "";
  const gradeName = c.grade_name || gradeNameOf(c.grade_id);
  const yearName = c.academic_year_name || yearNameOf(c.academic_year_id);

  return `
    <tr>
      <td class="table__cell--name">${escapeHtml(c.class_name || "—")}</td>
      <td>${escapeHtml(gradeName)}</td>
      <td>${escapeHtml(yearName)}</td>
      <td>${escapeHtml(c.homeroom_teacher_name || "—")}</td>
      <td>
        <div class="class-size">
          <span class="class-size__text">
            <strong>${current}</strong> <span class="class-size__max">/ ${max}</span>
          </span>
          <span class="progress">
            <span class="progress__bar ${tone ? `progress__bar--${tone}` : ""}"
                  style="width:${pct}%"></span>
          </span>
        </div>
      </td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--icon" data-action="detail" data-id="${c.id}"
                  aria-label="Xem danh sách" title="Xem danh sách học sinh">${icon("eye")}</button>
          <button type="button" class="btn btn--icon" data-action="enroll" data-id="${c.id}"
                  aria-label="Phân bổ học sinh" title="Phân bổ học sinh">${icon("users")}</button>
          <button type="button" class="btn btn--icon" data-action="edit" data-id="${c.id}"
                  aria-label="Sửa" title="Sửa lớp">${icon("edit")}</button>
          <button type="button" class="btn btn--icon btn--danger" data-action="delete" data-id="${c.id}"
                  aria-label="Xoá" title="Xoá lớp">${icon("trash")}</button>
        </div>
      </td>
    </tr>
  `;
}

function gradeNameOf(id) {
  const g = state.grades.find((x) => x.id === id);
  return g ? g.grade_name || g.name : "—";
}

function yearNameOf(id) {
  const y = state.years.find((x) => x.id === id);
  return y ? y.year_name || y.name : "—";
}

/* ------------------------------------------------------------------ */
/* Sự kiện trang                                                        */
/* ------------------------------------------------------------------ */
function bindPageEvents() {
  $("#filter-grade")?.addEventListener("change", (e) => {
    state.gradeId = e.target.value;
    state.page = 1;
    loadClasses();
  });

  $("#filter-year")?.addEventListener("change", (e) => {
    state.yearId = e.target.value;
    state.page = 1;
    loadClasses();
  });

  $("#btn-refresh")?.addEventListener("click", () => loadClasses());
  $("#btn-create-class")?.addEventListener("click", () => openClassModal());
  $("#btn-transfer")?.addEventListener("click", () => openTransferModal());

  $("#pagination-classes")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.page);
    loadClasses();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-class"));
  bindBackdropClose($("#modal-enroll"));
  bindBackdropClose($("#modal-transfer"));
  bindBackdropClose($("#modal-class-detail"));

  $("#form-class")?.addEventListener("submit", onClassSubmit);
  $("#form-enroll")?.addEventListener("submit", onEnrollSubmit);
  $("#form-transfer")?.addEventListener("submit", onTransferSubmit);

  $("#enroll-search")?.addEventListener(
    "input",
    debounce((e) => {
      state.enroll.search = e.target.value.trim().toLowerCase();
      renderEnrollSource();
    }, 250)
  );

  $("#btn-enroll-add")?.addEventListener("click", moveSelectedToTarget);
  $("#transfer-student")?.addEventListener("change", onTransferStudentChange);
  $("#transfer-to")?.addEventListener("change", updateTransferHint);
}

/* ------------------------------------------------------------------ */
/* Thao tác dòng                                                        */
/* ------------------------------------------------------------------ */
function bindRowActions() {
  $$("#tbody-classes [data-action]").forEach((btn) => {
    const id = Number(btn.dataset.id);
    const action = btn.dataset.action;
    if (action === "detail") btn.addEventListener("click", () => openDetailModal(id));
    else if (action === "enroll") btn.addEventListener("click", () => openEnrollModal(id));
    else if (action === "edit") btn.addEventListener("click", () => openClassModal(id));
    else if (action === "delete") btn.addEventListener("click", () => handleDeleteClass(id));
  });
}

/* ------------------------------------------------------------------ */
/* Tạo / sửa lớp                                                        */
/* ------------------------------------------------------------------ */
function openClassModal(id = null) {
  const form = $("#form-class");
  form.reset();
  hideAlert("class-alert");
  $$(".field__input, .field__select", form).forEach(clearFieldError);

  state.editing = id ? state.classes.find((c) => c.id === id) : null;

  if (state.editing) {
    $("#class-modal-title").textContent = "Cập nhật lớp học";
    $("#class-modal-subtitle").textContent = state.editing.class_name;
    $("#btn-class").textContent = "Lưu thay đổi";
    $("#class-name").value = state.editing.class_name || "";
    $("#class-grade").value = state.editing.grade_id || "";
    $("#class-year").value = state.editing.academic_year_id || "";
    $("#class-teacher").value = state.editing.homeroom_teacher_id || "";
    /* Khi sửa: khối và năm học không đổi */
    $("#class-grade").disabled = true;
    $("#class-year").disabled = true;
  } else {
    $("#class-modal-title").textContent = "Tạo lớp học";
    $("#class-modal-subtitle").textContent = "Lớp mới bắt buộc thuộc một khối và năm học.";
    $("#btn-class").textContent = "Tạo lớp";
    $("#class-grade").disabled = false;
    $("#class-year").disabled = false;
    if (ctx.year?.id) $("#class-year").value = ctx.year.id;
  }

  openModal($("#modal-class"));
  setTimeout(() => $("#class-name")?.focus(), 60);
}

async function onClassSubmit(e) {
  e.preventDefault();
  hideAlert("class-alert");

  const form = e.target;
  const btn = $("#btn-class");
  const payload = Object.fromEntries(new FormData(form).entries());

  if (!payload.class_name?.trim()) {
    setFieldError(form.querySelector('[name="class_name"]'), "Tên lớp là bắt buộc.");
    return;
  }

  setLoading(btn, true, "Đang lưu...");
  try {
    let res;
    if (state.editing) {
      res = await classApi.update(state.editing.id, {
        class_name: payload.class_name,
        homeroom_teacher_id: payload.homeroom_teacher_id || null,
      });
    } else {
      res = await classApi.create({
        class_name: payload.class_name,
        grade_id: payload.grade_id,
        academic_year_id: payload.academic_year_id,
        homeroom_teacher_id: payload.homeroom_teacher_id || null,
      });
    }
    toastSuccess(res?.message || "Đã lưu lớp học.");
    closeModal($("#modal-class"));
    await loadClasses();
  } catch (err) {
    showApiError("class-alert", err);
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* Xoá lớp                                                              */
/* ------------------------------------------------------------------ */
async function handleDeleteClass(id) {
  const cls = state.classes.find((c) => c.id === id);
  if (!cls) return;

  const current = cls.current_size_live ?? cls.current_size ?? 0;
  const confirmed = await confirmDialog({
    title: "Xoá lớp học",
    message: `Bạn có chắc muốn xoá lớp "${cls.class_name}"?`,
    detail:
      current > 0
        ? `Lớp hiện có ${current} học sinh. Chỉ xoá được lớp chưa có học sinh nào.`
        : "Hành động này không thể hoàn tác.",
    confirmText: "Xoá lớp",
    danger: true,
  });
  if (!confirmed) return;

  try {
    const res = await classApi.remove(id);
    toastSuccess(res?.message || "Đã xoá lớp học.");
    await loadClasses();
  } catch (err) {
    toastError(err?.message || "Không thể xoá lớp học.");
  }
}

/* ------------------------------------------------------------------ */
/* M8 — Phân bổ học sinh                                                */
/* ------------------------------------------------------------------ */
async function openEnrollModal(id) {
  const cls = state.classes.find((c) => c.id === id);
  if (!cls) return;

  const max = cls.max_size ?? ctx.maxClassSize;
  const current = cls.current_size_live ?? cls.current_size ?? 0;

  state.enroll = {
    classId: id,
    className: cls.class_name,
    maxSize: max,
    currentSize: current,
    selected: new Set(),
    available: [],
    enrolled: [],
    search: "",
  };

  $("#enroll-subtitle").textContent = `Lớp ${cls.class_name}`;
  $("#enroll-target-name").textContent = cls.class_name;
  $("#enroll-search").value = "";
  hideAlert("enroll-alert");
  updateEnrollCounters();
  renderEnrollSource();

  openModal($("#modal-enroll"));
  await loadEnrollLists(id);
}

async function loadEnrollLists(classId) {
  const srcBox = $("#enroll-source");
  const tgtBox = $("#enroll-target-list");
  srcBox.innerHTML = `<div style="padding:16px"><div class="skeleton skeleton--text"></div></div>`;
  tgtBox.innerHTML = `<div style="padding:16px"><div class="skeleton skeleton--text"></div></div>`;

  try {
    /* Học sinh đang học chưa phân lớp + đã có trong lớp */
    const [unassignedRes, assignedRes] = await Promise.all([
      studentApi.list({ limit: 100, status: "DANG_HOC" }).catch(() => ({ items: [] })),
      studentApi.list({ limit: 100, class_id: classId }).catch(() => ({ items: [] })),
    ]);

    const assignedIds = new Set((assignedRes.items || []).map((s) => s.id));
    state.enroll.enrolled = assignedRes.items || [];
    state.enroll.available = (unassignedRes.items || []).filter((s) => !assignedIds.has(s.id));

    renderEnrollSource();
    renderEnrollTarget();
  } catch (err) {
    srcBox.innerHTML = `<div class="t-caption" style="padding:16px">Không tải được danh sách học sinh.</div>`;
    tgtBox.innerHTML = "";
  }
}

function renderEnrollSource() {
  const box = $("#enroll-source");
  if (!box) return;

  const keyword = state.enroll.search;
  const items = state.enroll.available.filter((s) => {
    if (!keyword) return true;
    return (
      (s.full_name || "").toLowerCase().includes(keyword) ||
      (s.student_code || "").toLowerCase().includes(keyword)
    );
  });

  $("#enroll-source-count").textContent = items.length;

  if (!items.length) {
    box.innerHTML = `<div class="t-caption" style="padding:24px;text-align:center">
      Không có học sinh phù hợp.</div>`;
    return;
  }

  box.innerHTML = items
    .map(
      (s) => `
    <label class="enroll-list__item">
      <input type="checkbox" data-student="${s.id}" ${state.enroll.selected.has(s.id) ? "checked" : ""}>
      <span class="avatar avatar--32">${escapeHtml(initials(s.full_name))}</span>
      <span class="enroll-list__item-meta">
        <span class="enroll-list__item-name">${escapeHtml(s.full_name || "—")}</span>
        <span class="t-caption t-mono">${escapeHtml(s.student_code || "—")}</span>
      </span>
    </label>`
    )
    .join("");

  $$("#enroll-source input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const id = Number(cb.dataset.student);
      if (cb.checked) state.enroll.selected.add(id);
      else state.enroll.selected.delete(id);
      updateEnrollCounters();
    });
  });
}

function renderEnrollTarget() {
  const box = $("#enroll-target-list");
  if (!box) return;

  if (!state.enroll.enrolled.length) {
    box.innerHTML = `<div class="t-caption" style="padding:24px;text-align:center">
      Lớp chưa có học sinh nào.</div>`;
    return;
  }

  box.innerHTML = state.enroll.enrolled
    .map(
      (s) => `
    <div class="enroll-list__item">
      <span class="avatar avatar--32">${escapeHtml(initials(s.full_name))}</span>
      <span class="enroll-list__item-meta">
        <span class="enroll-list__item-name">${escapeHtml(s.full_name || "—")}</span>
        <span class="t-caption t-mono">${escapeHtml(s.student_code || "—")}</span>
      </span>
    </div>`
    )
    .join("");
}

function updateEnrollCounters() {
  const target = $("#enroll-target-count");
  const note = $("#enroll-note");
  const info = $("#enroll-info-text");

  const projected = state.enroll.currentSize + state.enroll.selected.size;
  if (target) {
    target.textContent = `${projected} / ${state.enroll.maxSize}`;
    target.className =
      projected > state.enroll.maxSize ? "chip chip--danger" : "chip chip--primary";
  }

  if (note) {
    note.textContent = state.enroll.selected.size
      ? `Đã chọn ${state.enroll.selected.size} học sinh`
      : "Chưa chọn học sinh nào";
  }

  if (info) {
    if (projected > state.enroll.maxSize) {
      info.textContent = `Sau khi phân bổ, lớp sẽ có ${projected} học sinh — vượt quá sĩ số tối đa (${state.enroll.maxSize}).`;
      info.parentElement.className = "alert alert--danger";
    } else {
      info.textContent = `Sĩ số hiện tại ${state.enroll.currentSize}, tối đa ${state.enroll.maxSize}. Sau khi phân bổ: ${projected}.`;
      info.parentElement.className = "alert alert--info";
    }
  }
}

function moveSelectedToTarget() {
  if (!state.enroll.selected.size) {
    toastWarning("Vui lòng chọn ít nhất một học sinh.");
    return;
  }
  const ids = Array.from(state.enroll.selected);
  const picked = state.enroll.available.filter((s) => ids.includes(s.id));

  state.enroll.enrolled.push(...picked);
  state.enroll.available = state.enroll.available.filter((s) => !ids.includes(s.id));
  state.enroll.selected.clear();

  renderEnrollSource();
  renderEnrollTarget();
  updateEnrollCounters();
}

async function onEnrollSubmit(e) {
  e.preventDefault();
  hideAlert("enroll-alert");

  const btn = $("#btn-enroll");
  const ids = Array.from(state.enroll.selected);

  if (!ids.length) {
    showAlert(
      "enroll-alert",
      "danger",
      "Chưa chọn học sinh",
      "Vui lòng chọn ít nhất một học sinh để phân bổ."
    );
    return;
  }

  setLoading(btn, true, "Đang phân bổ...");
  try {
    const res = await classApi.enroll(state.enroll.classId, {
      student_ids: ids,
      academic_year_id: ctx.year?.id,
    });
    toastSuccess(
      res?.message || `Đã phân bổ ${ids.length} học sinh vào lớp ${state.enroll.className}.`
    );
    closeModal($("#modal-enroll"));
    await loadClasses();
  } catch (err) {
    /* Lỗi vượt sĩ số → hiển thị current_size / max_size động */
    const size = err?.classSize;
    if (size.current !== null && size.max !== null) {
      showAlert(
        "enroll-alert",
        "danger",
        "Vượt quá sĩ số lớp",
        `Lớp hiện có ${size.current} học sinh, tối đa cho phép ${size.max}. Vui lòng chọn ít học sinh hơn.`
      );
    } else {
      showApiError("enroll-alert", err);
    }
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* M9 — Điều chuyển lớp                                                 */
/* ------------------------------------------------------------------ */
async function openTransferModal() {
  hideAlert("transfer-alert");
  $("#transfer-student").innerHTML = `<option value="">-- Chọn học sinh --</option>`;
  $("#transfer-from").value = "";
  $("#transfer-to").innerHTML = `<option value="">-- Chọn lớp --</option>`;
  $("#transfer-reason").value = "";

  state.classes.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.class_name} (${c.current_size_live ?? c.current_size ?? 0}/${
      c.max_size ?? ctx.maxClassSize
    })`;
    opt.dataset.name = c.class_name;
    opt.dataset.current = c.current_size_live ?? c.current_size ?? 0;
    opt.dataset.max = c.max_size ?? ctx.maxClassSize;
    $("#transfer-to").appendChild(opt);
  });

  openModal($("#modal-transfer"));

  /* Danh sách học sinh đang học để chọn */
  try {
    const res = await studentApi.list({ limit: 200, status: "DANG_HOC" });
    (res.items || []).forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `${s.full_name} — ${s.student_code}`;
      opt.dataset.classId = s.class_id || "";
      opt.dataset.className = s.class_name || "";
      $("#transfer-student").appendChild(opt);
    });
  } catch {
    toastWarning("Không tải được danh sách học sinh.");
  }
}

function onTransferStudentChange() {
  const sel = $("#transfer-student");
  const opt = sel.selectedOptions[0];
  $("#transfer-from").value = opt?.dataset.className
    ? `${opt.dataset.className}`
    : "Chưa phân lớp";
  updateTransferHint();
}

function updateTransferHint() {
  const toSel = $("#transfer-to");
  const opt = toSel.selectedOptions[0];
  const alertBox = $("#transfer-alert");
  if (!opt || !opt.value) {
    alertBox.classList.add("hidden");
    return;
  }
  const current = Number(opt.dataset.current || 0);
  const max = Number(opt.dataset.max || ctx.maxClassSize);
  if (current >= max) {
    showAlert(
      "transfer-alert",
      "danger",
      "Lớp đích đã đầy",
      `Lớp ${opt.dataset.name} hiện có ${current}/${max} học sinh — không thể chuyển thêm vào.`
    );
  } else {
    alertBox.classList.add("hidden");
  }
}

async function onTransferSubmit(e) {
  e.preventDefault();
  hideAlert("transfer-alert");

  const btn = $("#btn-transfer");
  const studentId = $("#transfer-student").value;
  const toClassId = $("#transfer-to").value;
  const fromClassId = $("#transfer-student").selectedOptions[0]?.dataset.classId;

  if (!studentId || !toClassId) {
    showAlert(
      "transfer-alert",
      "danger",
      "Thiếu thông tin",
      "Vui lòng chọn học sinh và lớp chuyển đến."
    );
    return;
  }

  setLoading(btn, true, "Đang chuyển...");
  try {
    const res = await classApi.transfer({
      student_id: Number(studentId),
      from_class_id: fromClassId ? Number(fromClassId) : null,
      to_class_id: Number(toClassId),
      transfer_reason: $("#transfer-reason").value.trim() || null,
      academic_year_id: ctx.year?.id,
    });
    toastSuccess(res?.message || "Đã điều chuyển học sinh.");
    closeModal($("#modal-transfer"));
    await loadClasses();
  } catch (err) {
    const size = err?.classSize;
    if (size.current !== null && size.max !== null) {
      showAlert(
        "transfer-alert",
        "danger",
        "Vượt quá sĩ số lớp đích",
        `Lớp đích hiện có ${size.current} học sinh, tối đa ${size.max}.`
      );
    } else {
      showApiError("transfer-alert", err);
    }
  } finally {
    setLoading(btn, false);
  }
}

/* ------------------------------------------------------------------ */
/* Modal xem danh sách học sinh trong lớp                               */
/* ------------------------------------------------------------------ */
async function openDetailModal(id) {
  const cls = state.classes.find((c) => c.id === id);
  if (!cls) return;

  state.detailClass = cls;
  $("#detail-title").textContent = `Lớp ${cls.class_name}`;
  $("#detail-subtitle").textContent =
    `Sĩ số: ${cls.current_size_live ?? cls.current_size ?? 0} / ${cls.max_size ?? ctx.maxClassSize}`;
  $("#btn-export-class").href = `${API_BASE}${API_PREFIX}/classes/${id}/export?format=excel`;

  const tbody = $("#detail-tbody");
  tbody.innerHTML = `<tr><td colspan="5"><div class="skeleton skeleton--text"></div></td></tr>`;

  openModal($("#modal-class-detail"));

  try {
    const res = await studentApi.list({ limit: 100, class_id: id });
    const items = res?.items || [];
    if (!items.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="t-center t-secondary" style="padding:24px">
        Lớp chưa có học sinh nào.</td></tr>`;
      return;
    }
    tbody.innerHTML = items
      .map(
        (s) => `
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
        <td>
          <div class="table__actions">
            <a class="btn btn--icon" href="student-detail.html?id=${s.id}"
               aria-label="Xem hồ sơ" title="Xem hồ sơ">${icon("eye")}</a>
          </div>
        </td>
      </tr>`
      )
      .join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="t-center t-danger" style="padding:24px">
      ${escapeHtml(err?.message || "Không tải được danh sách.")}</td></tr>`;
  }
}

/* ------------------------------------------------------------------ */
/* Helpers                                                              */
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

function showApiError(containerId, err) {
  showAlert(
    containerId,
    "danger",
    "Không thực hiện được",
    err?.message || "Đã xảy ra sự cố. Vui lòng thử lại."
  );
}
