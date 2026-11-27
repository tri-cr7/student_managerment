/* ==========================================================================
   REPORTS — M22 báo cáo tổng kết môn học + biểu đồ + xuất file
   ========================================================================== */

import { reportApi, catalogApi } from "../api.js";
import { initShell, pageContent } from "../app.js";
import {
  $,
  icon,
  toastError,
  renderEmptyRow,
  escapeHtml,
} from "../ui.js";
import { formatNumber, formatPercent } from "../format.js";

const state = {
  subjects: [],
  semesters: [],
  subjectId: "",
  semesterId: "",
  summary: null,
  chartData: null,
  charts: {},
};

let container = null;

initShell({
  active: "reports.html",
  roles: ["ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadOptions();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Báo cáo &amp; Thống kê</h1>
          <p class="page-header__subtitle">
            Tổng kết kết quả học tập theo môn học và học kỳ. Học sinh được tính là
            <strong>Đạt</strong> khi Điểm trung bình môn ≥ 5.0.
          </p>
        </div>
        <div class="page-header__actions">
          <a class="btn btn--secondary" id="btn-export-excel" href="#" download>
            ${icon("download")} Xuất Excel
          </a>
          <a class="btn btn--secondary" id="btn-export-pdf" href="#" download>
            ${icon("download")} Xuất PDF
          </a>
        </div>
      </div>
    </header>

    <div class="card" style="margin-bottom:24px">
      <div class="card__body card__body--tight">
        <div class="toolbar">
          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-subject"
                    aria-label="Chọn môn học">
              <option value="">-- Chọn môn học --</option>
            </select>
            <span class="field__chevron">▾</span>
          </div>
          <div class="field__select-wrap">
            <select class="field__select toolbar__select" id="filter-semester"
                    aria-label="Chọn học kỳ">
              <option value="">-- Chọn học kỳ --</option>
            </select>
            <span class="field__chevron">▾</span>
          </div>
          <div class="toolbar__spacer"></div>
          <button type="button" class="btn btn--primary" id="btn-load" disabled>
            ${icon("search")} Xem báo cáo
          </button>
        </div>
      </div>
    </div>

    <div id="report-body">
      <div class="empty-state">
        <span class="empty-state__icon">${icon("chart")}</span>
        <div class="empty-state__title">Chọn môn học và học kỳ</div>
        <div class="empty-state__message">
          Chọn môn học, học kỳ rồi bấm "Xem báo cáo" để tải số liệu tổng kết.
        </div>
      </div>
    </div>
  `;

  bindPageEvents();
}

function bindPageEvents() {
  const subjectSel = $("#filter-subject");
  const semesterSel = $("#filter-semester");
  const loadBtn = $("#btn-load");

  const syncEnabled = () => {
    loadBtn.disabled = !(subjectSel.value && semesterSel.value);
  };

  subjectSel?.addEventListener("change", syncEnabled);
  semesterSel?.addEventListener("change", syncEnabled);
  loadBtn?.addEventListener("click", loadReport);
}

async function loadOptions() {
  try {
    const [subjects, semesters] = await Promise.all([
      catalogApi.subjects().catch(() => []),
      catalogApi.semesters().catch(() => []),
    ]);

    state.subjects = Array.isArray(subjects) ? subjects : subjects?.items || [];
    state.semesters = Array.isArray(semesters) ? semesters : semesters?.items || [];

    const subjectSel = $("#filter-subject");
    state.subjects.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `${s.subject_name}${s.grade_name ? ` — ${s.grade_name}` : ""}`;
      subjectSel?.appendChild(opt);
    });

    const semesterSel = $("#filter-semester");
    state.semesters.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.semester_name || `HK ${s.id}`;
      semesterSel?.appendChild(opt);
    });

    /* Mặc định chọn môn đầu tiên & học kỳ hiện hành */
    if (state.subjects.length) subjectSel.value = state.subjects[0].id;
    const current = state.semesters.find((s) => s.is_current) || state.semesters[0];
    if (current) semesterSel.value = current.id;

    $("#btn-load").disabled = false;
  } catch (err) {
    toastError(err?.message || "Không tải được danh mục môn học / học kỳ.");
  }
}

async function loadReport() {
  const subjectId = $("#filter-subject").value;
  const semesterId = $("#filter-semester").value;

  if (!subjectId || !semesterId) {
    toastError("Vui lòng chọn cả môn học và học kỳ.");
    return;
  }

  state.subjectId = subjectId;
  state.semesterId = semesterId;

  const body = $("#report-body");
  body.innerHTML = `<div class="card"><div class="card__body">
    <div class="skeleton skeleton--text" style="height:160px"></div>
  </div></div>`;

  try {
    const [summary, chartData] = await Promise.all([
      reportApi.subjectSummary(subjectId, semesterId),
      reportApi.chartData(subjectId, semesterId, "bar").catch(() => null),
    ]);

    state.summary = summary;
    state.chartData = chartData;
    renderReport();
    updateExportLinks();
  } catch (err) {
    body.innerHTML = "";
    body.innerHTML = `
      <div class="alert alert--danger">
        <span class="alert__icon">${icon("alert")}</span>
        <div class="alert__body">
          <div class="alert__title">Không tải được báo cáo</div>
          <div class="alert__message">${escapeHtml(err?.message || "Đã xảy ra sự cố.")}</div>
        </div>
      </div>`;
  }
}

function renderReport() {
  const body = $("#report-body");
  const summary = state.summary || {};
  const rows = summary.summary || [];

  const totalStudents = rows.reduce((acc, r) => acc + (r.class_size || 0), 0);
  const totalPassed = rows.reduce((acc, r) => acc + (r.passed_count || 0), 0);
  const passRate = totalStudents ? (totalPassed / totalStudents) * 100 : 0;
  const activeSubjects = state.subjects.filter((s) => s.is_active !== false).length;

  body.innerHTML = `
    <div class="grid grid-4" style="margin-bottom:24px">
      ${kpiCard("Tổng học sinh", formatNumber(totalStudents), "Theo các lớp có điểm")}
      ${kpiCard("Số lớp có điểm", formatNumber(rows.length), summary.subject_name || "")}
      ${kpiCard("Tỷ lệ đạt", formatPercent(passRate), `Ngưỡng đạt ≥ ${summary.passing_threshold ?? 5.0}`)}
      ${kpiCard("Số môn đang dùng", formatNumber(activeSubjects), "Toàn trường")}
    </div>

    <div class="grid grid-2" style="margin-bottom:24px">
      <div class="card">
        <div class="card__header">
          <div>
            <div class="card__title">Tỷ lệ đạt theo lớp</div>
            <div class="card__subtitle">${escapeHtml(summary.subject_name || "")} · ${escapeHtml(summary.semester_name || "")}</div>
          </div>
        </div>
        <div class="card__body">
          <div class="chart-box">
            <canvas id="chart-pass-rate"></canvas>
          </div>
          <div class="chart-legend" id="legend-pass-rate"></div>
        </div>
      </div>

      <div class="card">
        <div class="card__header">
          <div>
            <div class="card__title">Số lượng học sinh đạt</div>
            <div class="card__subtitle">So sánh giữa các lớp</div>
          </div>
        </div>
        <div class="card__body">
          <div class="chart-box">
            <canvas id="chart-passed"></canvas>
          </div>
          <div class="chart-legend" id="legend-passed"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card__header">
        <div>
          <div class="card__title">Tổng hợp theo lớp</div>
          <div class="card__subtitle">Năm học ${escapeHtml(summary.academic_year || "—")}</div>
        </div>
      </div>
      <div class="card__body card__body--flush">
        <div class="table-wrap">
          <table class="table">
            <thead class="table__head">
              <tr>
                <th style="width:56px">STT</th>
                <th>Lớp</th>
                <th class="table__cell--center">Sĩ số</th>
                <th class="table__cell--center">Số đạt</th>
                <th class="table__cell--center">Tỷ lệ đạt (%)</th>
              </tr>
            </thead>
            <tbody id="tbody-report"></tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  renderTable(rows);
  renderCharts(rows);
}

function kpiCard(label, value, hint) {
  return `
    <div class="kpi-card">
      <div class="kpi-card__label">${escapeHtml(label)}</div>
      <div class="kpi-card__value">${escapeHtml(value)}</div>
      <div class="kpi-card__hint">${escapeHtml(hint)}</div>
    </div>
  `;
}

function renderTable(rows) {
  const tbody = $("#tbody-report");
  if (!tbody) return;

  if (!rows.length) {
    renderEmptyRow(tbody, 5, "Chưa có dữ liệu tổng kết cho môn học & học kỳ này.");
    return;
  }

  tbody.innerHTML = rows
    .map(
      (r) => `
    <tr>
      <td class="table__cell--center t-mono">${escapeHtml(r.stt ?? "")}</td>
      <td class="table__cell--name">${escapeHtml(r.class_name || "—")}</td>
      <td class="table__cell--center t-mono">${escapeHtml(r.class_size ?? 0)}</td>
      <td class="table__cell--center t-mono">${escapeHtml(r.passed_count ?? 0)}</td>
      <td class="table__cell--center">
        <div class="row" style="justify-content:center;gap:8px">
          <span class="t-mono">${escapeHtml(Number(r.pass_rate ?? 0).toFixed(2))}%</span>
          <div class="progress" style="width:80px">
            <div class="progress__bar ${rateTone(r.pass_rate)}"
                 style="width:${Math.min(100, Number(r.pass_rate ?? 0))}%"></div>
          </div>
        </div>
      </td>
    </tr>`
    )
    .join("");
}

function rateTone(rate) {
  const n = Number(rate ?? 0);
  if (n >= 80) return "";
  if (n >= 50) return "progress__bar--warning";
  return "progress__bar--danger";
}

function renderCharts(rows) {
  if (typeof window.Chart === "undefined") return;

  const labels = rows.map((r) => r.class_name || "");
  const passRates = rows.map((r) => Number(r.pass_rate ?? 0));
  const passedCounts = rows.map((r) => Number(r.passed_count ?? 0));

  drawChart("chart-pass-rate", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Tỷ lệ Đạt (%)",
          data: passRates,
          backgroundColor: "#2563EB",
          borderColor: "#1D4ED8",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { callback: (v) => `${v}%` } },
        x: { grid: { display: false } },
      },
    },
  });

  drawChart("chart-passed", {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Số lượng học sinh Đạt",
          data: passedCounts,
          backgroundColor: "#059669",
          borderColor: "#047857",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true },
        x: { grid: { display: false } },
      },
    },
  });

  renderLegend("#legend-pass-rate", [
    { color: "#2563EB", label: "Tỷ lệ đạt (%)" },
  ]);
  renderLegend("#legend-passed", [
    { color: "#059669", label: "Số lượng học sinh đạt" },
  ]);
}

function drawChart(canvasId, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  state.charts[canvasId]?.destroy();
  state.charts[canvasId] = new window.Chart(canvas.getContext("2d"), config);
}

function renderLegend(sel, items) {
  const box = $(sel);
  if (!box) return;
  box.innerHTML = items
    .map(
      (i) => `
    <span class="chart-legend__item">
      <span class="chart-legend__swatch" style="background:${i.color}"></span>
      ${escapeHtml(i.label)}
    </span>`
    )
    .join("");
}

function updateExportLinks() {
  const excel = $("#btn-export-excel");
  const pdf = $("#btn-export-pdf");
  if (excel) excel.href = reportApi.exportUrl("excel", state.subjectId, state.semesterId);
  if (pdf) pdf.href = reportApi.exportUrl("pdf", state.subjectId, state.semesterId);
}
