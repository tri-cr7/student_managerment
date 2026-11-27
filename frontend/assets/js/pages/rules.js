/* ==========================================================================
   RULES — M19 cấu hình quy định hệ thống (tuổi, sĩ số, cột điểm, bảo mật)
   ========================================================================== */

import { catalogApi } from "../api.js";
import { initShell, pageContent } from "../app.js";
import {
  $,
  $$,
  icon,
  setLoading,
  toastSuccess,
  toastError,
  renderSkeletonRows,
  escapeHtml,
} from "../ui.js";

/* Nhóm quy định theo ý nghĩa nghiệp vụ */
const GROUPS = [
  {
    title: "Quy định về tuổi",
    desc: "Áp dụng khi tiếp nhận học sinh mới vào trường.",
    keys: ["MIN_AGE", "MAX_AGE"],
  },
  {
    title: "Quy định về lớp",
    desc: "Áp dụng khi phân bổ học sinh vào lớp.",
    keys: ["MAX_CLASS_SIZE"],
  },
  {
    title: "Quy định về điểm",
    desc: "Cấu trúc bảng điểm và ngưỡng xếp loại.",
    keys: [
      "MIN_COL_15M",
      "MAX_COL_15M",
      "MIN_COL_45M",
      "MAX_COL_45M",
      "NUM_COL_FINAL",
      "PASSING_SCORE",
      "RANK_AVERAGE",
      "RANK_FAIR",
      "RANK_GOOD",
    ],
  },
  {
    title: "Bảo mật & xác thực",
    desc: "Chính sách đăng nhập và mã xác thực một lần.",
    keys: ["MAX_LOGIN_ATTEMPTS", "OTP_EXPIRE_MINUTES", "OTP_MAX_ATTEMPTS"],
  },
];

const state = {
  rules: new Map(),
  groups: [],
};

let container = null;

initShell({
  active: "rules.html",
  roles: ["ACADEMIC"],
}).then(async () => {
  container = pageContent();
  renderPage();
  await loadRules();
});

function renderPage() {
  container.innerHTML = `
    <header class="page-header">
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">Quy định hệ thống</h1>
          <p class="page-header__subtitle">
            Cấu hình các tham số nghiệp vụ dùng chung cho toàn hệ thống.
          </p>
        </div>
        <div class="page-header__actions">
          <button type="button" class="btn btn--primary" id="btn-save-all">
            ${icon("check")} Lưu tất cả
          </button>
        </div>
      </div>
    </header>

    <div class="alert alert--info" style="margin-bottom:24px">
      <span class="alert__icon" data-info-icon></span>
      <div class="alert__body">
        <div class="alert__message">
          Các quy định này có hiệu lực ngay khi lưu và được áp dụng cho toàn hệ thống.
        </div>
      </div>
    </div>

    <div class="stack-4" id="rules-groups"></div>
  `;

  const infoIcon = container.querySelector("[data-info-icon]");
  if (infoIcon) infoIcon.innerHTML = icon("info");

  $("#btn-save-all")?.addEventListener("click", saveAll);
}

async function loadRules() {
  const wrap = $("#rules-groups");
  if (!wrap) return;

  wrap.innerHTML = `<div class="card"><div class="card__body">
    <div class="skeleton skeleton--text" style="height:120px"></div>
  </div></div>`;

  try {
    const res = await catalogApi.rules();
    const list = Array.isArray(res) ? res : res?.items || res?.data || [];

    state.rules = new Map();
    list.forEach((r) => state.rules.set(r.rule_key, r));

    /* Chỉ hiện nhóm có ít nhất 1 quy định tồn tại */
    state.groups = GROUPS.map((g) => ({
      ...g,
      keys: g.keys.filter((k) => state.rules.has(k)),
    })).filter((g) => g.keys.length);

    renderGroups();
  } catch (err) {
    wrap.innerHTML = `
      <div class="alert alert--danger">
        <span class="alert__icon">${icon("alert")}</span>
        <div class="alert__body">
          <div class="alert__message">${escapeHtml(err?.message || "Không tải được quy định.")}</div>
        </div>
      </div>`;
  }
}

function renderGroups() {
  const wrap = $("#rules-groups");
  wrap.innerHTML = state.groups.map(renderGroupCard).join("");
  bindGroupEvents();
}

function renderGroupCard(group) {
  return `
    <div class="rule-card">
      <div class="rule-card__header">
        <div>
          <div class="card__title">${escapeHtml(group.title)}</div>
          <div class="card__subtitle">${escapeHtml(group.desc || "")}</div>
        </div>
        <button type="button" class="btn btn--secondary btn--sm"
                data-save-group="${escapeHtml(group.title)}">
          ${icon("check")} Lưu
        </button>
      </div>
      <div class="rule-card__body">
        ${group.keys.map(renderRuleField).join("")}
      </div>
    </div>
  `;
}

function renderRuleField(key) {
  const rule = state.rules.get(key);
  const type = String(rule.data_type || "INT").toUpperCase();
  const isFloat = type === "FLOAT" || type === "DECIMAL";
  const step = isFloat ? "0.1" : "1";
  const label = rule.description || key;

  return `
    <div class="field">
      <label class="field__label" for="rule-${escapeHtml(key)}">
        ${escapeHtml(label)}
      </label>
      <input class="field__input" id="rule-${escapeHtml(key)}"
             data-rule-key="${escapeHtml(key)}"
             data-original="${escapeHtml(rule.rule_value ?? "")}"
             type="number" step="${step}" value="${escapeHtml(rule.rule_value ?? "")}">
      <p class="field__hint">
        <span class="rule-card__key">${escapeHtml(key)}</span> · Kiểu ${escapeHtml(type)}
      </p>
    </div>
  `;
}

function bindGroupEvents() {
  $$("[data-save-group]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".rule-card");
      const keys = Array.from(card.querySelectorAll("[data-rule-key]")).map(
        (i) => i.dataset.ruleKey
      );
      saveGroup(keys, btn);
    });
  });
}

async function saveGroup(keys, btn) {
  const payload = [];
  for (const key of keys) {
    const input = $(`[data-rule-key="${key}"]`);
    if (!input) continue;
    const value = input.value.trim();
    if (value === "") continue;
    if (value === input.dataset.original) continue;
    payload.push({ rule_key: key, rule_value: value });
  }

  if (!payload.length) {
    toastSuccess("Không có thay đổi nào để lưu.");
    return;
  }

  setLoading(btn, true, "Đang lưu...");

  try {
    for (const p of payload) {
      await catalogApi.updateRule(p.rule_key, p.rule_value);
    }
    payload.forEach((p) => {
      const input = $(`[data-rule-key="${p.rule_key}"]`);
      if (input) input.dataset.original = p.rule_value;
    });
    toastSuccess(`Đã lưu ${payload.length} quy định.`);
  } catch (err) {
    toastError(err?.message || "Không lưu được quy định.");
  } finally {
    setLoading(btn, false);
  }
}

async function saveAll() {
  const inputs = $$("[data-rule-key]");
  const payload = [];

  inputs.forEach((input) => {
    const value = input.value.trim();
    if (value === "" || value === input.dataset.original) return;
    payload.push({ rule_key: input.dataset.ruleKey, rule_value: value });
  });

  if (!payload.length) {
    toastSuccess("Không có thay đổi nào để lưu.");
    return;
  }

  const btn = $("#btn-save-all");
  setLoading(btn, true, "Đang lưu...");

  try {
    await catalogApi.bulkRules(payload);
    payload.forEach((p) => {
      const input = $(`[data-rule-key="${p.rule_key}"]`);
      if (input) input.dataset.original = p.rule_value;
    });
    toastSuccess(`Đã lưu ${payload.length} quy định.`);
  } catch (err) {
    toastError(err?.message || "Không lưu được quy định.");
  } finally {
    setLoading(btn, false);
  }
}
