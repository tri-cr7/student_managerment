/* ==========================================================================
   ASSIGNMENTS — M18 phân công giảng dạy + khoá / mở khoá bảng điểm
   ========================================================================== */

import { academicApi, catalogApi, classApi, adminApi } from "../api.js";
import { initShell, pageContent } from "../app.js";
import {
  $,
  $$,
  icon,
  openModal,
  closeModal,
  bindBackdropClose,
  confirmDialog,
  setLoading,
  toastSuccess,
  toastError,
  renderSkeletonRows,
  renderEmptyRow,
  renderPagination,
  escapeHtml,
} from "../ui.js";
import { statusChip } from "../format.js";

const state = {
  page: 1,
  limit: 20,
  items: [],
  teachers: [],
  classes: [],
  subjects: [],
  semesters: [],
  editing: null,
};

let container = null;

initShell({
  active: "assignments.html",
  roles: ["ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadOptions();
  await loadAssignments();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Phân công giảng dạy</h1>
          <p class="page-header__subtitle">
            Gán giáo viên phụ trách lớp - môn - học kỳ và khoá / mở khoá bảng điểm.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--primary" id="btn-add">
            ${icon("plus")} Phân công giảng dạy
          </button>
        </div>
      </div>
    </header>

    <div class="card">
      <div class="table-wrap">
        <table class="table">
          <thead class="table__head">
            <tr>
              <th style="width:48px">STT</th>
              <th>Giáo viên</th>
              <th>Lớp</th>
              <th>Môn học</th>
              <th>Học kỳ</th>
              <th>Bảng điểm</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-assignments"></tbody>
        </table>
      </div>

      <div class="pagination" id="pagination-assignments"></div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  $("#btn-add")?.addEventListener("click", () => openAssignmentModal(null));

  $("#pagination-assignments")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-page]");
    if (!btn || btn.disabled) return;
    state.page = Number(btn.dataset.page);
    loadAssignments();
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-assignment"));

  $("#form-assignment")?.addEventListener("submit", onSubmit);
}

async function loadOptions() {
  const [users, classes, subjects, semesters] = await Promise.all([
    adminApi.users().catch(() => ({ items: [] })),
    classApi.list({ limit: 200 }).catch(() => ({ items: [] })),
    catalogApi.subjects().catch(() => []),
    catalogApi.semesters().catch(() => []),
  ]);

  state.teachers = (users?.items || []).filter((u) => u.role === "TEACHER");
  state.classes = classes?.items || [];
  state.subjects = Array.isArray(subjects) ? subjects : subjects?.items || [];
  state.semesters = Array.isArray(semesters) ? semesters : semesters?.items || [];

  fillSelect(
    $("#as-teacher"),
    state.teachers.map((t) => ({ value: t.id, label: `${t.full_name} (${t.username})` }))
  );
  fillSelect(
    $("#as-class"),
    state.classes.map((c) => ({ value: c.id, label: c.class_name || `Lớp ${c.id}` }))
  );
  fillSelect(
    $("#as-subject"),
    state.subjects.map((s) => ({
      value: s.id,
      label: `${s.subject_name}${s.grade_name ? ` — ${s.grade_name}` : ""}`,
    }))
  );
  fillSelect(
    $("#as-semester"),
    state.semesters.map((s) => ({ value: s.id, label: s.semester_name || `HK ${s.id}` }))
  );
}

function fillSelect(select, options) {
  if (!select) return;
  options.forEach((o) => {
    const opt = document.createElement("option");
    opt.value = o.value;
    opt.textContent = o.label;
    select.appendChild(opt);
  });
}

async function loadAssignments() {
  const tbody = $("#tbody-assignments");
  if (!tbody) return;

  renderSkeletonRows(tbody, 7, 8);

  try {
    const res = await academicApi.assignments({ page: state.page, limit: state.limit });
    state.items = res?.items || [];

    if (!state.items.length) {
      renderEmptyRow(
        tbody,
        7,
        "Chưa có phân công giảng dạy nào.",
        `<button type="button" class="btn btn--primary" id="btn-empty-add">
           ${icon("plus")} Phân công giảng dạy
         </button>`
      );
      $("#btn-empty-add")?.addEventListener("click", () => openAssignmentModal(null));
      renderPagination($("#pagination-assignments"), {
        page: 1,
        pages: 1,
        total: 0,
        limit: state.limit,
        label: "phân công",
      });
      return;
    }

    tbody.innerHTML = state.items.map(renderRow).join("");
    bindRowActions();

    renderPagination($("#pagination-assignments"), {
      page: res.page || 1,
      pages: res.pages || 1,
      total: res.total || state.items.length,
      limit: res.per_page || state.limit,
      label: "phân công",
    });
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 7, err?.message || "Không tải được danh sách phân công.");
  }
}

function renderRow(a, index) {
  const stt = (state.page - 1) * state.limit + index + 1;
  const locked = !!a.is_locked;
  const pending = !!a.has_pending_submission;

  return `
    <tr>
      <td class="table__cell--center t-mono">${escapeHtml(stt)}</td>
      <td class="table__cell--name">${escapeHtml(a.teacher_name || "—")}</td>
      <td>${escapeHtml(a.class_name || "—")}</td>
      <td>${escapeHtml(a.subject_name || "—")}</td>
      <td>${escapeHtml(a.semester_name || "—")}</td>
      <td>
        ${locked ? statusChip("DA_KHOA") : statusChip("MO")}
        ${
          pending
            ? `<span class="chip chip--warning" style="margin-left:4px">Chờ duyệt</span>`
            : ""
        }
      </td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--icon" data-action="edit" data-id="${a.id}"
                  aria-label="Sửa" title="Sửa phân công">${icon("edit")}</button>
          <button type="button" class="btn btn--icon ${locked ? "" : "btn--danger"}"
                  data-action="lock" data-id="${a.id}" data-locked="${locked}"
                  aria-label="${locked ? "Mở khoá" : "Khoá"}"
                  title="${locked ? "Mở khoá bảng điểm" : "Khoá bảng điểm"}">
            ${icon(locked ? "unlock" : "lock")}
          </button>
          <button type="button" class="btn btn--icon btn--danger" data-action="delete" data-id="${a.id}"
                  aria-label="Xoá" title="Hủy phân công">${icon("trash")}</button>
        </div>
      </td>
    </tr>
  `;
}

function bindRowActions() {
  $$("#tbody-assignments [data-action]").forEach((btn) => {
    const id = Number(btn.dataset.id);
    const action = btn.dataset.action;

    if (action === "edit") btn.addEventListener("click", () => openAssignmentModal(id));
    else if (action === "lock") btn.addEventListener("click", () => handleToggleLock(id, btn.dataset.locked === "true"));
    else btn.addEventListener("click", () => handleDelete(id));
  });
}

function openAssignmentModal(id) {
  const form = $("#form-assignment");
  form.reset();
  hideAlert();

  const item = id ? state.items.find((a) => a.id === id) : null;
  state.editing = item || null;

  $("#as-modal-title").textContent = item ? "Sửa phân công giảng dạy" : "Phân công giảng dạy";
  $("#as-modal-subtitle").textContent = item
    ? `${item.class_name || ""} — ${item.subject_name || ""}`
    : "Chọn giáo viên, lớp, môn học và học kỳ.";
  $("#btn-assignment").textContent = item ? "Lưu thay đổi" : "Phân công";

  if (item) {
    $("#as-teacher").value = item.teacher_id || "";
    $("#as-class").value = item.class_id || "";
    $("#as-subject").value = item.subject_id || "";
    $("#as-semester").value = item.semester_id || "";
  }

  openModal($("#modal-assignment"));
}

async function onSubmit(e) {
  e.preventDefault();

  const btn = $("#btn-assignment");
  const payload = {
    teacher_id: Number($("#as-teacher").value) || null,
    class_id: Number($("#as-class").value) || null,
    subject_id: Number($("#as-subject").value) || null,
    semester_id: Number($("#as-semester").value) || null,
  };

  if (!payload.teacher_id || !payload.class_id || !payload.subject_id || !payload.semester_id) {
    showAlert("danger", "Vui lòng chọn đầy đủ giáo viên, lớp, môn học và học kỳ.");
    return;
  }

  setLoading(btn, true, "Đang lưu...");

  try {
    if (state.editing) {
      await academicApi.updateAssignment(state.editing.id, payload);
      toastSuccess("Đã cập nhật phân công giảng dạy.");
    } else {
      await academicApi.createAssignment(payload);
      toastSuccess("Đã tạo phân công giảng dạy.");
    }
    closeModal($("#modal-assignment"));
    await loadAssignments();
  } catch (err) {
    showAlert("danger", err?.message || "Không lưu được phân công.");
  } finally {
    setLoading(btn, false);
  }
}

async function handleToggleLock(id, isLocked) {
  const item = state.items.find((a) => a.id === id);
  if (!item) return;

  const ok = await confirmDialog({
    title: isLocked ? "Mở khoá bảng điểm" : "Khoá bảng điểm",
    message: isLocked
      ? `Mở khoá bảng điểm ${item.subject_name} — Lớp ${item.class_name}?`
      : `Khoá bảng điểm ${item.subject_name} — Lớp ${item.class_name}?`,
    detail: isLocked
      ? "Sau khi mở khoá, giáo viên có thể sửa điểm trực tiếp trên bảng điểm."
      : "Sau khi khoá, giáo viên không thể sửa điểm và phải gửi đơn phúc khảo.",
    confirmText: isLocked ? "Mở khoá" : "Khoá",
    danger: !isLocked,
  });
  if (!ok) return;

  try {
    await academicApi.setLock(id, !isLocked);
    toastSuccess(isLocked ? "Đã mở khoá bảng điểm." : "Đã khoá bảng điểm.");
    await loadAssignments();
  } catch (err) {
    toastError(err?.message || "Không thực hiện được thao tác.");
  }
}

async function handleDelete(id) {
  const item = state.items.find((a) => a.id === id);
  if (!item) return;

  const ok = await confirmDialog({
    title: "Hủy phân công giảng dạy",
    message: `Hủy phân công ${item.teacher_name} — ${item.class_name} — ${item.subject_name}?`,
    detail: "Chỉ hủy được khi phân công chưa phát sinh điểm.",
    confirmText: "Hủy phân công",
    danger: true,
  });
  if (!ok) return;

  try {
    await academicApi.removeAssignment(id);
    toastSuccess("Đã hủy phân công giảng dạy.");
    await loadAssignments();
  } catch (err) {
    toastError(err?.message || "Không hủy được phân công.");
  }
}

function showAlert(tone, message) {
  const box = $("#as-alert");
  if (!box) return;
  box.className = `alert alert--${tone}`;
  box.innerHTML = `
    <span class="alert__icon">${icon("alert")}</span>
    <div class="alert__body"><div class="alert__message">${escapeHtml(message)}</div></div>
  `;
}

function hideAlert() {
  const box = $("#as-alert");
  if (box) {
    box.className = "hidden";
    box.innerHTML = "";
  }
}
