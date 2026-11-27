/* ==========================================================================
   SUBJECTS — M17 quản lý danh mục môn học
   ========================================================================== */

import { catalogApi } from "../api.js";
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
  escapeHtml,
} from "../ui.js";
import { statusChip } from "../format.js";

const state = {
  subjects: [],
  grades: [],
  gradeFilter: "",
  editing: null,
};

let container = null;

initShell({
  active: "subjects.html",
  roles: ["ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadCatalog();
  await loadSubjects();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Danh mục môn học</h1>
          <p class="page-header__subtitle">
            Quản lý các môn học theo khối lớp. Môn đang ngừng dùng vẫn giữ nguyên dữ liệu lịch sử.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--primary" id="btn-add">
            ${icon("plus")} Thêm môn học
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
          <div class="toolbar__spacer"></div>
          <span class="chip chip--neutral" id="count-subjects">0 môn</span>
        </div>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead class="table__head">
            <tr>
              <th>Mã môn</th>
              <th>Tên môn</th>
              <th>Khối</th>
              <th class="table__cell--center">Số tiết</th>
              <th>Trạng thái</th>
              <th style="text-align:right">Thao tác</th>
            </tr>
          </thead>
          <tbody id="tbody-subjects"></tbody>
        </table>
      </div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  $("#btn-add")?.addEventListener("click", () => openSubjectModal(null));

  $("#filter-grade")?.addEventListener("change", (e) => {
    state.gradeFilter = e.target.value;
    renderSubjects();
  });

  $$("[data-close]").forEach((btn) =>
    btn.addEventListener("click", () => closeModal(btn.closest("dialog")))
  );
  bindBackdropClose($("#modal-subject"));

  $("#form-subject")?.addEventListener("submit", onSubmit);
}

async function loadCatalog() {
  try {
    const grades = await catalogApi.grades();
    state.grades = grades || [];

    const gradeSel = $("#subject-grade");
    const filterSel = $("#filter-grade");
    state.grades.forEach((g) => {
      const label = g.grade_name || g.name || `Khối ${g.id}`;
      if (gradeSel) {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = label;
        gradeSel.appendChild(opt);
      }
      if (filterSel) {
        const opt = document.createElement("option");
        opt.value = g.id;
        opt.textContent = label;
        filterSel.appendChild(opt);
      }
    });
  } catch {
    /* Không chặn trang nếu API lỗi */
  }
}

async function loadSubjects() {
  const tbody = $("#tbody-subjects");
  if (!tbody) return;

  renderSkeletonRows(tbody, 6, 6);

  try {
    const res = await catalogApi.subjects();
    state.subjects = Array.isArray(res) ? res : res?.items || res?.data || [];
    renderSubjects();
  } catch (err) {
    tbody.innerHTML = "";
    renderEmptyRow(tbody, 6, err?.message || "Không tải được danh mục môn học.");
  }
}

function renderSubjects() {
  const tbody = $("#tbody-subjects");
  const list = state.gradeFilter
    ? state.subjects.filter((s) => String(s.grade_id) === String(state.gradeFilter))
    : state.subjects;

  $("#count-subjects").textContent = `${list.length} môn`;

  if (!list.length) {
    renderEmptyRow(
      tbody,
      6,
      state.gradeFilter ? "Không có môn học nào thuộc khối đã chọn." : "Chưa có môn học nào.",
      `<button type="button" class="btn btn--primary" id="btn-empty-add">
         ${icon("plus")} Thêm môn học
       </button>`
    );
    $("#btn-empty-add")?.addEventListener("click", () => openSubjectModal(null));
    return;
  }

  tbody.innerHTML = list.map(renderRow).join("");
  bindRowActions();
}

function renderRow(s) {
  return `
    <tr>
      <td class="table__cell--mono">${escapeHtml(s.subject_code || "—")}</td>
      <td class="table__cell--name">${escapeHtml(s.subject_name || "—")}</td>
      <td>${escapeHtml(s.grade_name || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(s.periods_count ?? "—")}</td>
      <td>${
        s.is_active
          ? statusChip("DANG_DUNG")
          : statusChip("NGUNG_DUNG")
      }</td>
      <td>
        <div class="table__actions">
          <button type="button" class="btn btn--icon" data-action="edit" data-id="${s.id}"
                  aria-label="Sửa" title="Sửa">${icon("edit")}</button>
          <button type="button" class="btn btn--icon btn--danger" data-action="delete" data-id="${s.id}"
                  aria-label="Xoá" title="Xoá">${icon("trash")}</button>
        </div>
      </td>
    </tr>
  `;
}

function bindRowActions() {
  $$("#tbody-subjects [data-action]").forEach((btn) => {
    const id = Number(btn.dataset.id);
    if (btn.dataset.action === "edit") {
      btn.addEventListener("click", () => openSubjectModal(id));
    } else {
      btn.addEventListener("click", () => handleDelete(id));
    }
  });
}

function openSubjectModal(id) {
  const form = $("#form-subject");
  form.reset();
  hideAlert();

  const subject = id ? state.subjects.find((s) => s.id === id) : null;
  state.editing = subject || null;

  $("#subject-modal-title").textContent = subject ? "Sửa môn học" : "Thêm môn học";
  $("#subject-modal-subtitle").textContent = subject
    ? subject.subject_name
    : "Mã môn và tên môn là bắt buộc.";
  $("#btn-subject").textContent = subject ? "Lưu thay đổi" : "Thêm môn học";

  if (subject) {
    $("#subject-code").value = subject.subject_code || "";
    $("#subject-name").value = subject.subject_name || "";
    $("#subject-grade").value = subject.grade_id || "";
    $("#subject-periods").value = subject.periods_count ?? "";
    $("#subject-active").checked = !!subject.is_active;
  } else {
    $("#subject-active").checked = true;
  }

  openModal($("#modal-subject"));
}

async function onSubmit(e) {
  e.preventDefault();

  const btn = $("#btn-subject");
  const payload = {
    subject_code: $("#subject-code").value.trim(),
    subject_name: $("#subject-name").value.trim(),
    grade_id: Number($("#subject-grade").value) || null,
    periods_count: Number($("#subject-periods").value) || 0,
    is_active: $("#subject-active").checked,
  };

  if (!payload.subject_code || !payload.subject_name || !payload.grade_id) {
    showAlert("danger", "Vui lòng điền đủ mã môn, tên môn và khối lớp.");
    return;
  }

  setLoading(btn, true, "Đang lưu...");

  try {
    if (state.editing) {
      await catalogApi.updateSubject(state.editing.id, payload);
      toastSuccess("Đã cập nhật môn học.");
    } else {
      await catalogApi.createSubject(payload);
      toastSuccess("Đã thêm môn học mới.");
    }
    closeModal($("#modal-subject"));
    await loadSubjects();
  } catch (err) {
    showAlert("danger", err?.message || "Không lưu được môn học.");
  } finally {
    setLoading(btn, false);
  }
}

async function handleDelete(id) {
  const subject = state.subjects.find((s) => s.id === id);
  if (!subject) return;

  const ok = await confirmDialog({
    title: "Xoá môn học",
    message: `Xoá môn học "${subject.subject_name}"?`,
    detail:
      "Nếu môn đã được dùng trong phân công giảng dạy, hệ thống sẽ từ chối xoá.",
    confirmText: "Xoá",
    danger: true,
  });
  if (!ok) return;

  try {
    await catalogApi.removeSubject(id);
    toastSuccess("Đã xoá môn học.");
    await loadSubjects();
  } catch (err) {
    toastError(err?.message || "Không xoá được môn học.");
  }
}

function showAlert(tone, message) {
  const box = $("#subject-alert");
  if (!box) return;
  box.className = `alert alert--${tone}`;
  box.innerHTML = `
    <span class="alert__icon">${icon("alert")}</span>
    <div class="alert__body"><div class="alert__message">${escapeHtml(message)}</div></div>
  `;
}

function hideAlert() {
  const box = $("#subject-alert");
  if (box) {
    box.className = "hidden";
    box.innerHTML = "";
  }
}
