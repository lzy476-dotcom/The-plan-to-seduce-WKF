// 前端交互逻辑
const API = ""; // 同源，直接用相对路径

const $ = (sel) => document.querySelector(sel);

// 今天日期（本地时区，YYYY-MM-DD）
function today() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  const local = new Date(d.getTime() - off * 60000);
  return local.toISOString().slice(0, 10);
}

const dateInput = $("#date");

// 用 flatpickr 接管日期选择，显示中文完整日历
const fp = flatpickr(dateInput, {
  locale: "zh",
  defaultDate: today(),
  dateFormat: "Y-m-d",
  allowInput: false,
  position: "below",
  monthSelectorType: "static",   // 月份用纯文字 + 左右箭头，去掉下拉框
  showMonths: 1,
  prevArrow: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>',
  nextArrow: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
});

// 日期变化时刷新记录
fp.config.onChange = fp.config.onClose = function () {
  loadMeals();
};

// 打开时设置更高层级（偏移量已在 flatpickr.min.js 内修改）
fp.config.onOpen = function (selectedDates, dateStr, instance) {
  instance.calendarContainer.style.zIndex = "9999";
};

// 点击整条日期栏唤起日历
$("#date-box").addEventListener("click", () => {
  fp.open();
});

// 内存中的食物列表（id、name、每100g营养）
let foods = [];

// 营养锁定开关（默认 true，从后端读取）
let lockNutri = true;

// ---- 加载食物（填充下拉建议）----
async function loadFoods() {
  foods = await (await fetch(`${API}/api/foods`)).json();
  $("#food-suggest").innerHTML = foods
    .map((f) => `<option value="${f.name}"></option>`)
    .join("");
}

// ---- 加载锁定开关状态 ----
async function loadLock() {
  const res = await (await fetch(`${API}/api/settings/nutrition_lock`)).json();
  lockNutri = res.enabled;
  $("#lock-nutri").checked = lockNutri;
}

// 保存锁定开关
async function saveLock(enabled) {
  lockNutri = enabled;
  await fetch(`${API}/api/settings/nutrition_lock`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  // 开关变化后刷新所有行的营养字段显隐
  $("#items").querySelectorAll(".item-row").forEach(refreshRowNutri);
}

$("#lock-nutri").addEventListener("change", (e) => saveLock(e.target.checked));

// 根据名字找食物
function findFood(name) {
  name = name.trim();
  return foods.find((f) => f.name === name) || null;
}

// ---- 动态食物行 ----
function addItemRow() {
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <input type="text" class="i-name" list="food-suggest" placeholder="食物名称" autocomplete="off" />
    <div class="nutri-wrap">
      <div class="grid nutri">
        <input type="number" class="i-protein" step="0.1" placeholder="蛋白 g" />
        <input type="number" class="i-carbs" step="0.1" placeholder="碳水 g" />
        <input type="number" class="i-fat" step="0.1" placeholder="脂肪 g" />
      </div>
    </div>
    <input type="number" class="i-grams" step="0.1" min="0.1" placeholder="吃了多少克(g)" />
    <button type="button" class="del-item" title="删除此行">✕</button>
  `;
  $("#items").appendChild(row);

  // 每个行内：输入食物名时带出/清空营养，并按锁定状态显隐营养字段
  row.querySelector(".i-name").addEventListener("input", (e) => {
    const food = findFood(e.target.value);
    if (food) {
      row.querySelector(".i-protein").value = food.protein_per_100g ?? "";
      row.querySelector(".i-carbs").value = food.carbs_per_100g ?? "";
      row.querySelector(".i-fat").value = food.fat_per_100g ?? "";
    } else {
      row.querySelector(".i-protein").value = "";
      row.querySelector(".i-carbs").value = "";
      row.querySelector(".i-fat").value = "";
    }
    refreshRowNutri(row);
  });

  // 删除行（至少保留一行）
  row.querySelector(".del-item").addEventListener("click", () => {
    if ($("#items").children.length > 1) {
      row.remove();
    } else {
      // 只剩一行时清空它
      row.querySelectorAll("input").forEach((i) => (i.value = ""));
      refreshRowNutri(row);
    }
  });
}

// 根据锁定状态和是否已有食物，决定该行营养字段是否显示
function refreshRowNutri(row) {
  const name = row.querySelector(".i-name").value.trim();
  const food = name ? findFood(name) : null;
  const wrap = row.querySelector(".nutri-wrap");
  // 锁定开启 + 已有食物 → 隐藏营养字段（只填克重）
  if (lockNutri && food) {
    wrap.style.display = "none";
  } else {
    wrap.style.display = "";
  }
}

// ---- 收集当前表单的 items ----
function collectItems() {
  const items = [];
  $("#items").querySelectorAll(".item-row").forEach((row) => {
    const name = row.querySelector(".i-name").value.trim();
    const grams = parseFloat(row.querySelector(".i-grams").value);
    if (!name || !grams || grams <= 0) return; // 跳过空行/无效行
    const food = findFood(name);
    const item = { grams: grams };
    if (lockNutri && food) {
      // 锁定 + 已有食物：只传 food_id，营养用库中锁定值
      item.food_id = food.id;
    } else {
      // 新食物（或未锁定）：带名字 + 营养（热量由后端自动算）
      item.food_name = name;
      item.protein_per_100g = parseFloat(row.querySelector(".i-protein").value) || 0;
      item.carbs_per_100g = parseFloat(row.querySelector(".i-carbs").value) || 0;
      item.fat_per_100g = parseFloat(row.querySelector(".i-fat").value) || 0;
    }
    items.push(item);
  });
  return items;
}

// ---- 汇总显示 ----
function setSummary(kcal, protein, carbs, fat) {
  $("#sum-kcal").textContent = kcal.toFixed(0);
  $("#sum-protein").textContent = protein.toFixed(1);
  $("#sum-carbs").textContent = carbs.toFixed(1);
  $("#sum-fat").textContent = fat.toFixed(1);
}

// ---- 加载今日餐 ----
async function loadMeals() {
  const date = dateInput.value;
  const meals = await (await fetch(`${API}/api/meals?date=${date}`)).json();
  const el = $("#meals");
  if (meals.length === 0) {
    el.innerHTML = `<div class="empty">
      <div class="empty-icon">🍽️</div>
      <div class="empty-text">这一天还没有记录</div>
      <div class="empty-sub">在右侧添加你的第一餐吧</div>
    </div>`;
    setSummary(0, 0, 0, 0);
    return;
  }
  el.innerHTML = meals
    .map((m) => {
      const itemsHtml = m.items
        .map((it) => {
          return `<div class="meal-item">
            <div class="meal-item-main">
              <span class="meal-item-name">${it.food_name}</span>
              <span class="meal-item-grams">${it.grams}g</span>
            </div>
            <div class="meal-item-meta">
              <span class="pill">蛋白 ${it.protein.toFixed(1)}g</span>
              <span class="pill">碳水 ${it.carbs.toFixed(1)}g</span>
              <span class="pill">脂肪 ${it.fat.toFixed(1)}g</span>
              <span class="pill pill-kcal">${it.kcal.toFixed(0)} kcal</span>
            </div>
          </div>`;
        })
        .join("");
      return `<div class="meal">
        <div class="meal-head">
          <div class="meal-head-left">
            <span class="meal-badge">一餐</span>
            ${m.note ? `<span class="meal-sub">${m.note}</span>` : ""}
          </div>
          <span class="meal-kcal">${m.kcal.toFixed(0)} <small>kcal</small></span>
          <button class="del" data-id="${m.id}" title="删除这一餐">✕</button>
        </div>
        ${itemsHtml}
      </div>`;
    })
    .join("");

  const totalKcal = meals.reduce((s, m) => s + m.kcal, 0);
  const totalProtein = meals.reduce((s, m) => s + m.protein, 0);
  const totalCarbs = meals.reduce((s, m) => s + m.carbs, 0);
  const totalFat = meals.reduce((s, m) => s + m.fat, 0);
  setSummary(totalKcal, totalProtein, totalCarbs, totalFat);
}

// ---- 提交一餐 ----
$("#meal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const items = collectItems();
  if (items.length === 0) {
    alert("请至少填写一个食物的名称和克重");
    return;
  }
  const payload = {
    date: dateInput.value,
    note: $("#note").value.trim(),
    items: items,
  };
  const res = await fetch(`${API}/api/meals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert("记录失败：" + (err.detail || "未知错误"));
    return;
  }
  // 重置：清空所有行，回到一行
  $("#items").innerHTML = "";
  addItemRow();
  $("#note").value = "";
  await loadFoods();
  await loadMeals();
});

// ---- 删除一餐 ----
$("#meals").addEventListener("click", async (e) => {
  if (e.target.classList.contains("del")) {
    const id = e.target.dataset.id;
    await fetch(`${API}/api/meals/${id}`, { method: "DELETE" });
    await loadMeals();
  }
});

// ---- 添加食物行 ----
$("#add-item").addEventListener("click", addItemRow);

// ============================================================
// 左侧导航切换
// ============================================================
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
    item.classList.add("active");
    const view = item.dataset.view;
    document.querySelectorAll(".view").forEach((v) => {
      v.hidden = v.id !== "view-" + view;
    });
    if (view === "plan") {
      loadTodayPlan();
      loadPlans();
    }
  });
});

// ============================================================
// 饮食计划
// ============================================================
// 渲染「今日目标」对比卡片
async function loadTodayPlan() {
  const date = dateInput.value || today();
  let plan;
  try {
    plan = await (await fetch(`${API}/api/plans/today?date=${date}`)).json();
  } catch (e) {
    plan = { active: false };
  }
  const el = $("#today-plan");
  if (!plan.active) {
    el.innerHTML = `<div class="empty"><div class="empty-icon">🎯</div><div class="empty-text">今天没有生效的计划</div><div class="empty-sub">新建一个计划并设置今天所在的时间段</div></div>`;
    return;
  }
  // 拉取今日实际摄入
  let meals = [];
  try {
    meals = await (await fetch(`${API}/api/meals?date=${date}`)).json();
  } catch (e) {}
  const actual = {
    kcal: meals.reduce((s, m) => s + m.kcal, 0),
    protein: meals.reduce((s, m) => s + m.protein, 0),
    carbs: meals.reduce((s, m) => s + m.carbs, 0),
    fat: meals.reduce((s, m) => s + m.fat, 0),
  };
  const targets = [
    { key: "kcal", label: "热量", unit: "千卡", target: plan.kcal, val: actual.kcal, dec: 0 },
    { key: "protein", label: "蛋白质", unit: "g", target: plan.protein, val: actual.protein, dec: 1 },
    { key: "carbs", label: "碳水", unit: "g", target: plan.carbs, val: actual.carbs, dec: 1 },
    { key: "fat", label: "脂肪", unit: "g", target: plan.fat, val: actual.fat, dec: 1 },
  ];
  el.innerHTML = `
    <div class="plan-active-plan">${plan.plan_name}</div>
    <div class="plan-active-range">${plan.start_date} ~ ${plan.end_date}</div>
    <div class="plan-progress">
      ${targets.map((t) => {
        const pct = t.target > 0 ? Math.min(100, (t.val / t.target) * 100) : 0;
        const over = t.val > t.target && t.target > 0;
        return `<div class="plan-progress-row">
          <div class="plan-progress-head">
            <span>${t.label}</span>
            <span class="${over ? "over" : ""}">${t.val.toFixed(t.dec)} / ${t.target.toFixed(t.dec)} ${t.unit}</span>
          </div>
          <div class="plan-bar"><div class="plan-bar-fill ${over ? "over" : ""}" style="width:${pct}%"></div></div>
        </div>`;
      }).join("")}
    </div>`;
}

// 渲染计划列表
async function loadPlans() {
  const plans = await (await fetch(`${API}/api/plans`)).json();
  const el = $("#plans-list");
  if (plans.length === 0) {
    el.innerHTML = `<div class="empty"><div class="empty-icon">📋</div><div class="empty-text">还没有计划</div></div>`;
    return;
  }
  el.innerHTML = plans.map((p) => `
    <div class="plan-card">
      <div class="plan-card-head">
        <span class="plan-name">${p.name}</span>
        <div class="plan-card-tools">
          <button class="plan-edit" data-plan-id="${p.id}" title="编辑计划">✎</button>
          <button class="del" data-plan-id="${p.id}" title="删除计划">✕</button>
        </div>
      </div>
      ${p.phases.map((ph) => `
        <div class="plan-phase">
          <div class="plan-phase-range">${ph.start_date} ~ ${ph.end_date}</div>
          <div class="plan-phase-targets">
            <span class="pill">🔥 ${ph.kcal} 千卡</span>
            <span class="pill">蛋白 ${ph.protein}g</span>
            <span class="pill">碳水 ${ph.carbs}g</span>
            <span class="pill">脂肪 ${ph.fat}g</span>
          </div>
        </div>
      `).join("")}
    </div>
  `).join("");
}

// 计划列表点击：编辑 / 删除
$("#plans-list").addEventListener("click", async (e) => {
  const t = e.target;
  const id = t.dataset.planId;
  if (t.classList.contains("plan-edit")) {
    // 编辑：拉取完整计划并回填表单
    try {
      const plan = await (await fetch(`${API}/api/plans/${id}`)).json();
      openPlanFormEdit(plan);
    } catch (err) {
      alert("加载计划失败");
    }
    return;
  }
  if (t.classList.contains("del")) {
    if (!confirm("确定删除这个计划吗？")) return;
    await fetch(`${API}/api/plans/${id}`, { method: "DELETE" });
    await loadPlans();
    await loadTodayPlan();
  }
});

// ============================================================
// 计划表单（内嵌，新建/编辑共用）
// ============================================================
// 当前编辑的计划 id；为 null 时表示「新建」
let editingPlanId = null;

// 添加一个时间段行（可带初始值，用于编辑回填）
function addPhaseRow(init = {}) {
  const row = document.createElement("div");
  row.className = "phase-row";
  row.innerHTML = `
    <div class="phase-row-head">
      <span class="phase-row-index"></span>
      <button type="button" class="del-phase" title="删除该时间段">✕</button>
    </div>
    <div class="phase-row-dates">
      <input type="text" class="ph-start" placeholder="开始日期" readonly />
      <span class="phase-arrow">→</span>
      <input type="text" class="ph-end" placeholder="结束日期" readonly />
    </div>
    <div class="grid nutri">
      <input type="number" class="ph-kcal" step="1" min="0" placeholder="热量 kcal" />
      <input type="number" class="ph-protein" step="0.1" min="0" placeholder="蛋白 g" />
      <input type="number" class="ph-carbs" step="0.1" min="0" placeholder="碳水 g" />
      <input type="number" class="ph-fat" step="0.1" min="0" placeholder="脂肪 g" />
    </div>
  `;
  $("#plan-phases").appendChild(row);

  // 日期输入用 flatpickr 选择
  const start = row.querySelector(".ph-start");
  const end = row.querySelector(".ph-end");
  flatpickr(start, {
    locale: "zh", dateFormat: "Y-m-d", allowInput: false,
    defaultDate: init.start_date || null,
  });
  flatpickr(end, {
    locale: "zh", dateFormat: "Y-m-d", allowInput: false,
    defaultDate: init.end_date || null,
  });

  // 回填营养目标
  row.querySelector(".ph-kcal").value = init.kcal ?? "";
  row.querySelector(".ph-protein").value = init.protein ?? "";
  row.querySelector(".ph-carbs").value = init.carbs ?? "";
  row.querySelector(".ph-fat").value = init.fat ?? "";

  // 删除时间段（至少保留一个）
  row.querySelector(".del-phase").addEventListener("click", () => {
    if ($("#plan-phases").children.length > 1) {
      row.remove();
    } else {
      resetPhaseRow(row);
    }
    renumberPhases();
  });

  renumberPhases();
}

// 清空一个时间段行（保留该行但清空值）
function resetPhaseRow(row) {
  row.querySelectorAll("input").forEach((i) => (i.value = ""));
}

// 重排时间段序号
function renumberPhases() {
  $("#plan-phases").querySelectorAll(".phase-row").forEach((row, idx) => {
    row.querySelector(".phase-row-index").textContent = "时间段 " + (idx + 1);
  });
}

// 收集表单里的时间段
function collectPhases() {
  const phases = [];
  $("#plan-phases").querySelectorAll(".phase-row").forEach((row) => {
    const start = row.querySelector(".ph-start").value.trim();
    const end = row.querySelector(".ph-end").value.trim();
    const kcal = parseFloat(row.querySelector(".ph-kcal").value) || 0;
    const protein = parseFloat(row.querySelector(".ph-protein").value) || 0;
    const carbs = parseFloat(row.querySelector(".ph-carbs").value) || 0;
    const fat = parseFloat(row.querySelector(".ph-fat").value) || 0;
    if (!start || !end) return; // 忽略没填日期的时间段
    phases.push({ start_date: start, end_date: end, kcal, protein, carbs, fat });
  });
  return phases;
}

// 显示表单，进入「新建」模式
function openPlanFormNew() {
  editingPlanId = null;
  $("#plan-form-title").textContent = "新建计划";
  $("#plan-name").value = "";
  $("#plan-phases").innerHTML = "";
  addPhaseRow();
  $("#plan-form-wrap").hidden = false;
  $("#new-plan").hidden = true;
  $("#plan-name").focus();
}

// 显示表单，进入「编辑」模式并回填
function openPlanFormEdit(plan) {
  editingPlanId = plan.id;
  $("#plan-form-title").textContent = "编辑计划";
  $("#plan-name").value = plan.name;
  $("#plan-phases").innerHTML = "";
  (plan.phases || []).forEach((ph) => addPhaseRow(ph));
  if ($("#plan-phases").children.length === 0) addPhaseRow();
  $("#plan-form-wrap").hidden = false;
  $("#new-plan").hidden = true;
}

// 关闭表单
function closePlanForm() {
  $("#plan-form-wrap").hidden = true;
  $("#new-plan").hidden = false;
  editingPlanId = null;
}

// 打开新建表单
$("#new-plan").addEventListener("click", openPlanFormNew);

// 添加时间段
$("#add-phase").addEventListener("click", () => addPhaseRow());

// 取消
$("#plan-cancel").addEventListener("click", closePlanForm);

// 保存（新建或编辑）
$("#plan-save").addEventListener("click", async () => {
  const name = $("#plan-name").value.trim();
  if (!name) { alert("请填写计划名称"); return; }
  const phases = collectPhases();
  if (phases.length === 0) { alert("请至少填写一个时间段（起止日期）"); return; }

  // 前端兜底校验：起止日期合法性
  for (const ph of phases) {
    if (ph.start_date > ph.end_date) {
      alert(`时间段起止日期不合法：${ph.start_date} ~ ${ph.end_date}`);
      return;
    }
  }

  const isEdit = editingPlanId !== null;
  const url = isEdit ? `${API}/api/plans/${editingPlanId}` : `${API}/api/plans`;
  const method = isEdit ? "PUT" : "POST";
  const payload = { name, phases };

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert("保存失败：" + (err.detail || "未知错误"));
    return;
  }
  closePlanForm();
  await loadPlans();
  await loadTodayPlan();
});

// ---- 初始化 ----
(async function init() {
  await loadLock();
  await loadFoods();
  addItemRow(); // 初始一行
  await loadMeals();
})();
