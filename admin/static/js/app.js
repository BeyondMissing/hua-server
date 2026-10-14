import * as api from "../api/client.js";

const accountState = { page: 1, pageSize: 20, editing: null, total: 0 };
const clothingState = {
  userId: null,
  page: 1,
  pageSize: 10,
  total: 0,
  selected: null,
  typeNames: new Map(),
  optionsLoaded: false,
};
const profileState = {
  page: 1,
  pageSize: 20,
  total: 0,
  editing: null,
  clothingEditing: null,
  options: null,
};
const petState = { page: 1, pageSize: 20, total: 0, editing: null };
const petNames = { 1500001: "智慧花宝", 1500002: "美丽花宝", 1500003: "爱心花宝", 1500004: "古灵花宝", 1500005: "勇气花宝" };
const gardenState = {
  page: 1,
  pageSize: 10,
  total: 0,
  items: [],
  options: null,
  editing: null,
};
const houseGoodsState = {
  userId: null,
  items: [],
  page: 1,
  pageSize: 10,
  total: 0,
  catalog: [],
  catalogLoaded: false,
  editingNo: null,
};
const actionsState = {
  userId: null,
  items: [],
  catalog: [],
  catalogLoaded: false,
  editingActionId: null,
};
const tasksState = { userId: null, columns: [], items: [] };
const housesState = { userId: null, items: [] };
const inventoryStates = Object.fromEntries(["flowers", "seeds", "materials", "pet-supplies", "tools", "pollens"].map((kind) => [kind, {
  userId: null,
  items: [],
  page: 1,
  pageSize: 10,
  total: 0,
  catalog: [],
  catalogLoaded: false,
  editingItemId: null,
}]));
const inventoryLabels = { flowers: "花朵", seeds: "种子", materials: "材料", "pet-supplies": "宠物用品", tools: "工具", pollens: "花粉" };

const $ = (id) => document.getElementById(id);

function showApp(authenticated) {
  $("login").classList.toggle("hidden", authenticated);
  $("app").classList.toggle("hidden", !authenticated);
  if (authenticated) switchView("accounts");
}

function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  $("accounts-view").classList.toggle("hidden", view !== "accounts");
  $("profiles-view").classList.toggle("hidden", view !== "profiles");
  $("pets-view").classList.toggle("hidden", view !== "pets");
  $("gardens-view").classList.toggle("hidden", view !== "gardens");
  $("clothes-view").classList.toggle("hidden", view !== "clothes");
  $("house-goods-view").classList.toggle("hidden", view !== "house-goods");
  $("actions-view").classList.toggle("hidden", view !== "actions");
  $("houses-view").classList.toggle("hidden", view !== "houses");
  $("tasks-view").classList.toggle("hidden", view !== "tasks");
  for (const kind of Object.keys(inventoryStates)) {
    $(`${kind}-view`).classList.toggle("hidden", view !== kind);
  }
  const titles = {
    accounts: "/ 账号管理",
    profiles: "/ 玩家资料",
    pets: "/ 宠物管理",
    gardens: "/ 花园管理",
    clothes: "/ 服装管理",
    "house-goods": "/ 小屋物品管理",
    actions: "/ 动作管理",
    flowers: "/ 花朵管理",
    seeds: "/ 种子管理",
    materials: "/ 材料管理",
    "pet-supplies": "/ 宠物用品",
    tools: "/ 工具管理",
    pollens: "/ 花粉管理",
    houses: "/ 小屋管理",
    tasks: "/ 任务管理",
  };
  $("header-section").textContent = titles[view] || "";

  if (view === "accounts") {
    loadAccounts();
  } else if (view === "profiles") {
    loadProfiles();
  } else if (view === "pets") {
    loadPets();
  } else if (view === "gardens") {
    loadGardens();
  } else if (view === "clothes") {
    ensureClothingOptions().catch(handleRequestError);
  } else if (view === "house-goods") {
    ensureHouseGoodsOptions().catch(handleRequestError);
  } else if (view === "actions") {
    ensureActionOptions().catch(handleRequestError);
  } else if (view === "houses") {
    loadHouses();
  } else if (view === "tasks") {
    if (tasksState.userId) loadTasks();
  } else if (inventoryStates[view]) {
    ensureInventoryOptions(view).catch(handleRequestError);
  }
}

const weatherNames = { 1: "小雨", 2: "中雨", 6: "晴", 7: "阴", 8: "彩虹" };

async function ensureGardenOptions() {
  if (gardenState.options) return gardenState.options;
  gardenState.options = await api.getGardenOptions();
  return gardenState.options;
}

async function loadGardens() {
  try {
    const data = await api.listGardens({
      page: gardenState.page,
      pageSize: gardenState.pageSize,
      userId: $("garden-user-id-filter").value,
    });
    gardenState.items = data.items;
    gardenState.total = data.total;
    $("garden-rows").innerHTML = data.items.map((item) => `
      <tr>
        <td class="mono">${item.user_id}</td>
        <td>${escapeHtml(item.background_name || "未知")} <span class="muted">(${item.background_id})</span></td>
        <td>${escapeHtml(item.home_name)}</td>
        <td>${escapeHtml(weatherNames[item.weather] || String(item.weather))}</td>
        <td>${escapeHtml(item.temperature)}</td>
        <td>${item.item_id == null ? "-" : `${escapeHtml(item.house_name || "未知")} <span class="muted">(${item.item_id})</span>`}</td>
        <td>${item.x == null ? "-" : item.x}</td>
        <td>${item.y == null ? "-" : item.y}</td>
        <td>${item.open_flag == null ? "-" : badge(item.open_flag)}</td>
        <td><button class="link-button" data-garden-edit="${item.user_id}">编辑</button></td>
      </tr>`).join("");
    $("garden-empty").classList.toggle("hidden", data.items.length !== 0);
    const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    $("garden-summary").textContent = `${start}-${Math.min(data.page * data.page_size, data.total)} / 共 ${data.total} 条`;
    $("garden-prev").disabled = data.page <= 1;
    $("garden-next").disabled = data.page * data.page_size >= data.total;
  } catch (error) { handleRequestError(error); }
}

async function openGardenModal(item) {
  const options = await api.getGardenOptions(item.user_id);
  gardenState.editing = item.user_id;
  $("garden-user-id").value = item.user_id;
  $("garden-background").innerHTML = options.backgrounds.map((entry) =>
    `<option value="${entry.id}">${escapeHtml(entry.name)} (${entry.id})</option>`).join("");
  $("garden-house").innerHTML = options.houses.map((entry) =>
    `<option value="${entry.id}">${escapeHtml(entry.name)} (${entry.id})</option>`).join("");
  $("garden-weather").innerHTML = options.weather.map((value) =>
    `<option value="${value}">${weatherNames[value]} (${value})</option>`).join("");
  $("garden-background").value = String(item.background_id);
  $("garden-house").value = String(item.item_id ?? "");
  $("garden-weather").value = String(item.weather);
  $("garden-home-name").value = item.home_name;
  $("garden-temperature").value = item.temperature;
  $("garden-x").value = item.x ?? 0;
  $("garden-y").value = item.y ?? 0;
  $("garden-form").elements.open_flag.value = String(item.open_flag ?? 0);
  $("garden-form-error").textContent = "";
  $("garden-modal").classList.remove("hidden");
}

function closeGardenModal() {
  $("garden-modal").classList.add("hidden");
  gardenState.editing = null;
}

const nationalityNames = { 1: "智慧国", 2: "美丽国", 3: "爱心国", 5: "勇气国" };
const clothingTypeNames = {
  1: "工具", 2: "头饰", 3: "面具", 4: "头发", 5: "耳环", 6: "项链",
  7: "腰带", 8: "衣服", 9: "手镯", 10: "鞋子", 11: "脚链", 12: "裙子", 13: "翅膀",
};

function formatProfileTime(value) {
  if (!value) return "-";
  const date = new Date(Number(value) * 1000);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN", { hour12: false });
}

function setSelectOptions(element, items, selected, emptyLabel = "无") {
  element.innerHTML = [
    `<option value="0">${escapeHtml(emptyLabel)}</option>`,
    ...items.map((item) => `<option value="${item.id}">${escapeHtml(item.name)} (${item.id})</option>`),
  ].join("");
  element.value = String(selected ?? 0);
}

async function loadProfiles() {
  try {
    const data = await api.listProfiles({
      page: profileState.page,
      pageSize: profileState.pageSize,
      userId: $("profile-user-id-filter").value,
      nickname: $("profile-nickname-filter").value.trim(),
      nationality: $("profile-nationality-filter").value,
    });
    profileState.total = data.total;
    $("profile-rows").innerHTML = data.items.map((profile) => `
      <tr>
        <td class="mono">${profile.user_id}</td>
        <td><strong>${escapeHtml(profile.nickname)}</strong></td>
        <td>${escapeHtml(nationalityNames[profile.nationality] || String(profile.nationality))}</td>
        <td>${escapeHtml(formatProfileTime(profile.reg_time))}</td>
        <td>${escapeHtml(formatProfileTime(profile.login_last))}</td>
        <td><div class="row-actions">
          <button class="link-button" data-profile-edit="${profile.user_id}">编辑</button>
          <button class="link-button" data-profile-clothing="${profile.user_id}">编辑服装</button>
        </div></td>
      </tr>`).join("");
    $("profile-empty").classList.toggle("hidden", data.items.length !== 0);
    const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    $("profile-summary").textContent = `${start}-${Math.min(data.page * data.page_size, data.total)} / 共 ${data.total} 条`;
    $("profile-prev").disabled = data.page <= 1;
    $("profile-next").disabled = data.page * data.page_size >= data.total;
  } catch (error) { handleRequestError(error); }
}

async function loadPets() {
  try {
    const data = await api.listPets({ page: petState.page, pageSize: petState.pageSize, userId: $("pet-user-id-filter").value });
    petState.total = data.total;
    $("pet-rows").innerHTML = data.items.map((pet) => `
      <tr><td class="mono">${pet.user_id}</td><td>${escapeHtml(petNames[pet.pet_id] || pet.pet_name)}</td>
      <td>${escapeHtml(formatPetDate(pet.age))}</td><td class="mono">${pet.love_energy}</td>
      <td><strong>${escapeHtml(pet.nickname)}</strong></td><td>${badge(pet.is_vip)}</td>
      <td><button class="link-button" data-pet-edit-user="${pet.user_id}" data-pet-edit-id="${pet.pet_id}">编辑</button></td></tr>`).join("");
    $("pet-empty").classList.toggle("hidden", data.items.length !== 0);
    const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    $("pet-summary").textContent = `${start}-${Math.min(data.page * data.page_size, data.total)} / 共 ${data.total} 条`;
    $("pet-prev").disabled = data.page <= 1;
    $("pet-next").disabled = data.page * data.page_size >= data.total;
  } catch (error) { handleRequestError(error); }
}

function formatPetDate(value) {
  const date = new Date(Number(value) * 1000);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString("zh-CN");
}

function toDateTimeLocal(timestamp) {
  const date = new Date(Number(timestamp) * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

async function openPetModal(userId, petId) {
  const editing = userId !== undefined && petId !== undefined;
  const pet = editing ? await api.getPet(userId, petId) : {
    user_id: $("pet-user-id-filter").value,
    pet_id: 1500001, age: Math.floor(Date.now() / 1000), nickname: "宠物",
    love_energy: 0, hungry_index: 5000000, clean_index: 5000000, mood_index: 5000000,
    health_state: 0, is_vip: 0, wonderful_value: 0, rest_at: 0,
  };
  petState.editing = editing ? { userId: Number(userId), petId: Number(petId) } : null;
  $("pet-modal-title").textContent = editing ? "编辑宠物" : "添加宠物";
  $("pet-user-id").disabled = editing;
  $("pet-user-id").value = pet.user_id;
  $("pet-type").innerHTML = Object.entries(petNames).map(([id, name]) => `<option value="${id}">${name}</option>`).join("");
  $("pet-type").value = String(pet.pet_id);
  $("pet-age").value = toDateTimeLocal(pet.age);
  $("pet-nickname").value = pet.nickname;
  for (const [id, field] of [["pet-love-energy", "love_energy"], ["pet-hungry", "hungry_index"], ["pet-clean", "clean_index"], ["pet-mood", "mood_index"], ["pet-health", "health_state"], ["pet-vip", "is_vip"], ["pet-wonderful", "wonderful_value"], ["pet-rest", "rest_at"]]) $(id).value = pet[field];
  $("pet-form-error").textContent = "";
  $("pet-modal").classList.remove("hidden");
}

function closePetModal() { $("pet-modal").classList.add("hidden"); petState.editing = null; }

function fillProfileOptionFilters() {
  $("profile-nationality-filter").innerHTML = '<option value="">全部国籍</option>'
    + Object.entries(nationalityNames).map(([id, name]) => `<option value="${id}">${name}</option>`).join("");
}

async function openProfileModal(userId) {
  const response = await api.getProfile(userId);
  const profile = response.profile || response;
  const options = response.options;
  if (!options) throw new Error("玩家资料选项加载失败");
  profileState.options = options;
  profileState.editing = Number(userId);
  $("profile-user-id").value = profile.user_id;
  $("profile-nickname").value = profile.nickname;
  const simple = {
    "profile-nationality": options.nationalities,
    "profile-birthday": options.birthdays,
  };
  for (const [id, items] of Object.entries(simple)) {
    const select = $(id);
    select.innerHTML = items.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("");
  }
  $("profile-nationality").value = profile.nationality;
  $("profile-birthday").value = profile.birthday;
  ["love", "beautiful", "wisdom", "plant_grade", "faerie_grade", "money"].forEach((field) => {
    $(`profile-${field.replaceAll("_", "-")}`).value = profile[field];
  });
  setSelectOptions($("profile-face-color"), options.face_colors, profile.face_color);
  for (const field of ["face", "eye", "eyebrow", "lip"]) {
    const type = { face: 105, eye: 103, eyebrow: 102, lip: 104 }[field];
    setSelectOptions($("profile-" + field), options.icons.filter((item) => item.cloth_type === type), profile[field]);
  }
  $("profile-form-error").textContent = "";
  $("profile-modal").classList.remove("hidden");
}

function closeProfileModal() { $("profile-modal").classList.add("hidden"); profileState.editing = null; }

async function openProfileClothingModal(userId) {
  const response = await api.getProfile(userId);
  const profile = response.profile || response;
  const options = response.options;
  if (!options) throw new Error("玩家资料选项加载失败");
  profileState.options = options;
  profileState.clothingEditing = Number(userId);
  $("profile-clothing-description").textContent = `玩家 ${userId} 的已拥有服装`;
  const clothing = profile.clothing || {};
  $("profile-clothing-fields").innerHTML = options.slots.map((slot) => {
    const items = options.clothes.filter((item) => item.cloth_type === slot.cloth_type);
    return `<div><label for="profile-clothing-${slot.name}">${escapeHtml(clothingTypeNames[slot.cloth_type] || slot.name)}</label>
      <select id="profile-clothing-${slot.name}" data-clothing-slot="${slot.name}">
        <option value="0">不穿</option>${items.map((item) => `<option value="${item.id}">${escapeHtml(item.name)} (${item.id})</option>`).join("")}
      </select></div>`;
  }).join("");
  options.slots.forEach((slot) => {
    const select = $(`profile-clothing-${slot.name}`);
    if (select) select.value = String(clothing[slot.name] || 0);
  });
  $("profile-clothing-form-error").textContent = "";
  $("profile-clothing-modal").classList.remove("hidden");
}

function closeProfileClothingModal() { $("profile-clothing-modal").classList.add("hidden"); profileState.clothingEditing = null; }

function badge(value) {
  return `<span class="badge ${value ? "on" : ""}">${value ? "是" : "否"}</span>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}

function handleRequestError(error) {
  alert(error.message);
  if (error.message === "login required") showApp(false);
}

async function loadAccounts() {
  try {
    const data = await api.listAccounts({
      page: accountState.page,
      pageSize: accountState.pageSize,
      search: $("search").value,
    });
    accountState.total = data.total;

    $("account-rows").innerHTML = data.items.map((account) => `
      <tr>
        <td class="mono">${account.user_id}</td>
        <td><strong>${escapeHtml(account.login_name)}</strong></td>
        <td class="mono" title="${account.password_hash}">
          ${account.password_hash.slice(0, 12)}…
        </td>
        <td>${badge(account.role_created)}</td>
        <td>${badge(account.banned)}</td>
        <td>${badge(account.enable_friends_application)}</td>
        <td>
          <div class="row-actions">
            <button class="link-button" data-edit="${account.user_id}">编辑</button>
            <button class="link-button delete" data-delete="${account.user_id}">删除</button>
          </div>
        </td>
      </tr>
    `).join("");

    $("empty").classList.toggle("hidden", data.items.length !== 0);
    const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    $("summary").textContent = `${start}-${Math.min(data.page * data.page_size, data.total)} / 共 ${data.total} 条`;
    $("prev").disabled = data.page <= 1;
    $("next").disabled = data.page * data.page_size >= data.total;
  } catch (error) {
    handleRequestError(error);
  }
}

async function ensureClothingOptions() {
  if (clothingState.optionsLoaded) return;
  const data = await api.getClothingOptions();
  clothingState.typeNames = new Map(
    data.cloth_types.map((item) => [Number(item.value), item.name]),
  );
  $("clothes-type").innerHTML = [
    '<option value="">全部</option>',
    ...data.cloth_types.map((item) => (
      `<option value="${item.value}">${escapeHtml(item.name)}</option>`
    )),
  ].join("");
  clothingState.optionsLoaded = true;
}

function sexName(value) {
  return { 0: "未知", 1: "女", 2: "男" }[value] || `未知 (${value})`;
}

async function loadClothes() {
  if (!clothingState.userId) return;
  try {
    await ensureClothingOptions();
    const data = await api.listClothes({
      userId: clothingState.userId,
      page: clothingState.page,
      pageSize: clothingState.pageSize,
      name: $("clothes-name").value.trim(),
      sex: $("clothes-sex").value,
      clothType: $("clothes-type").value,
    });
    clothingState.total = data.total;
    $("clothes-workspace").classList.remove("hidden");
    $("clothes-prompt").classList.add("hidden");
    $("clothes-rows").innerHTML = data.items.map((clothing) => {
      const typeName = clothingState.typeNames.get(clothing.cloth_type)
        || `未知 (${clothing.cloth_type})`;
      const action = clothing.acquired
        ? `<button class="link-button delete" data-discard="${clothing.id}">丢弃</button>`
        : `<button class="link-button" data-acquire="${clothing.id}" data-name="${escapeHtml(clothing.name)}">获得</button>`;
      return `
        <tr>
          <td class="mono">${clothing.id}</td>
          <td><strong>${escapeHtml(clothing.name)}</strong></td>
          <td>${sexName(clothing.sex)}</td>
          <td>${escapeHtml(typeName)}</td>
          <td>${clothing.acquired_at ? escapeHtml(clothing.acquired_at) : '<span class="muted">未获得</span>'}</td>
          <td>${action}</td>
        </tr>
      `;
    }).join("");

    $("clothes-empty").classList.toggle("hidden", data.items.length !== 0);
    const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    $("clothes-summary").textContent = `${start}-${Math.min(data.page * data.page_size, data.total)} / 共 ${data.total} 条`;
    $("clothes-prev").disabled = data.page <= 1;
    $("clothes-next").disabled = data.page * data.page_size >= data.total;
  } catch (error) {
    $("clothes-workspace").classList.add("hidden");
    $("clothes-prompt").classList.remove("hidden");
    $("clothes-prompt").textContent = error.message === "account not found"
      ? "未找到该账号，请检查 User ID。"
      : "服装列表加载失败。";
    handleRequestError(error);
  }
}

async function ensureHouseGoodsOptions() {
  if (houseGoodsState.catalogLoaded) return;
  const data = await api.getHouseGoodsOptions();
  houseGoodsState.catalog = data.items;
  $("house-goods-item-id").innerHTML = data.items.map((item) => (
    `<option value="${item.id}">${escapeHtml(item.name)} (${item.id})</option>`
  )).join("");
  houseGoodsState.catalogLoaded = true;
}

async function loadHouseGoods() {
  if (!houseGoodsState.userId) return;
  try {
    const data = await api.listHouseGoods({
      userId: houseGoodsState.userId,
      page: houseGoodsState.page,
      pageSize: houseGoodsState.pageSize,
    });
    houseGoodsState.items = data.items;
    houseGoodsState.total = data.total;
    $("house-goods-workspace").classList.remove("hidden");
    $("house-goods-prompt").classList.add("hidden");
    $("house-goods-owner").textContent = `玩家 ${houseGoodsState.userId}`;
    const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
    $("house-goods-summary").textContent = data.total
      ? `${start}-${Math.min(data.page * data.page_size, data.total)} / 共 ${data.total} 条`
      : "共 0 条";
    $("house-goods-prev").disabled = data.page <= 1;
    $("house-goods-next").disabled = data.page * data.page_size >= data.total;
    $("house-goods-rows").innerHTML = data.items.map((item) => `
      <tr>
        <td class="mono">${item.item_id}</td>
        <td><strong>${escapeHtml(item.name || "未知物品")}</strong></td>
        <td class="mono">${item.no}</td>
        <td>${item.x}</td>
        <td>${item.y}</td>
        <td>${item.m === 2 ? "镜像" : "正常"}</td>
        <td>${item.z}</td>
        <td><span class="badge ${item.is_set ? "on" : ""}">${item.is_set ? "放置" : "收回"}</span></td>
        <td><div class="row-actions">
          <button class="link-button" data-house-goods-edit="${item.no}">编辑</button>
          <button class="link-button delete" data-house-goods-delete="${item.no}">删除</button>
        </div></td>
      </tr>
    `).join("");
    $("house-goods-empty").classList.toggle("hidden", data.items.length !== 0);
  } catch (error) {
    houseGoodsState.items = [];
    $("house-goods-workspace").classList.add("hidden");
    $("house-goods-prompt").classList.remove("hidden");
    $("house-goods-prompt").textContent = error.message === "account not found"
      ? "未找到该账号，请检查 User ID。"
      : "小屋物品列表加载失败。";
    handleRequestError(error);
  }
}

async function ensureActionOptions() {
  if (actionsState.catalogLoaded) return;
  const data = await api.getActionOptions();
  actionsState.catalog = data.items;
  actionsState.catalogLoaded = true;
}

async function loadActions() {
  if (!actionsState.userId) return;
  try {
    const data = await api.listActions(actionsState.userId);
    actionsState.items = data.items;
    $("actions-workspace").classList.remove("hidden");
    $("actions-prompt").classList.add("hidden");
    $("actions-owner").textContent = `玩家 ${actionsState.userId}`;
    $("actions-rows").innerHTML = data.items.map((item) => `
      <tr>
        <td class="mono">${item.action_id}</td>
        <td><strong>${escapeHtml(item.name || "未知动作")}</strong></td>
        <td class="mono">${item.amount}</td>
        <td><button class="link-button" data-action-edit="${item.action_id}">编辑</button></td>
      </tr>
    `).join("");
    $("actions-empty").classList.toggle("hidden", data.items.length !== 0);
  } catch (error) {
    actionsState.items = [];
    $("actions-workspace").classList.add("hidden");
    $("actions-prompt").classList.remove("hidden");
    $("actions-prompt").textContent = error.message === "account not found"
      ? "未找到该账号，请检查 User ID。"
      : "动作列表加载失败。";
    handleRequestError(error);
  }
}

async function loadTasks() {
  if (!tasksState.userId) return;
  try {
    const data = await api.listTasks(tasksState.userId);
    tasksState.columns = data.columns;
    tasksState.items = data.items;
    $("tasks-workspace").classList.remove("hidden");
    $("tasks-prompt").classList.add("hidden");
    $("tasks-owner").textContent = `玩家 ${tasksState.userId}`;
    $("tasks-head").innerHTML = `<tr>${data.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}<th>阶段</th><th>阶段内进度</th><th>阶段内目标</th><th>操作</th></tr>`;
    $("tasks-rows").innerHTML = data.items.map((item) => `
      <tr>${data.columns.map((column) => `<td class="${column === "main_id" ? "mono" : ""}">${escapeHtml(item[column] ?? "-")}</td>`).join("")}<td>${item.step ?? "-"}</td>
      <td>${item.process ?? "-"}</td><td>${item.total_process ?? "-"}</td>
      <td><button class="link-button delete" data-task-reset="${escapeHtml(item.main_id)}">重置</button></td></tr>`).join("");
    $("tasks-empty").classList.toggle("hidden", data.items.length !== 0);
  } catch (error) {
    $("tasks-workspace").classList.add("hidden"); $("tasks-prompt").classList.remove("hidden");
    $("tasks-prompt").textContent = "任务列表加载失败。"; handleRequestError(error);
  }
}

async function openActionModal(item = null) {
  await ensureActionOptions();
  actionsState.editingActionId = item ? item.action_id : null;
  $("action-form").reset();
  $("action-modal-title").textContent = item ? "编辑动作" : "新增动作";
  $("action-catalog-field").classList.toggle("hidden", Boolean(item));
  $("action-id").disabled = Boolean(item);
  if (!item) {
    $("action-id").innerHTML = actionsState.catalog.map((action) =>
      `<option value="${action.id}">${escapeHtml(action.name)} (${action.id})</option>`
    ).join("");
    $("action-modal-description").textContent = `为玩家 ${actionsState.userId} 新增动作；已有动作会累加数量。`;
  } else {
    $("action-modal-description").textContent = `${item.name || "未知动作"}（Action ID: ${item.action_id}）`;
  }
  $("action-amount").value = item ? item.amount : 1;
  $("action-form-error").textContent = "";
  $("action-modal").classList.remove("hidden");
}

function closeActionModal() {
  $("action-modal").classList.add("hidden");
  actionsState.editingActionId = null;
}

async function ensureInventoryOptions(kind) {
  const state = inventoryStates[kind];
  if (state.catalogLoaded) return;
  const data = await api.getInventoryOptions(kind);
  state.catalog = data.items;
  state.catalogLoaded = true;
}

async function loadInventory(kind) {
  const state = inventoryStates[kind];
  if (!state.userId) return;
  try {
    const data = await api.listInventory(kind, {
      userId: state.userId,
      page: state.page,
      pageSize: state.pageSize,
      name: $(`${kind}-name`).value.trim(),
    });
    state.items = data.items;
    state.total = data.total;
    $(`${kind}-workspace`).classList.remove("hidden");
    $(`${kind}-prompt`).classList.add("hidden");
    $(`${kind}-owner`).textContent = `玩家 ${state.userId}`;
    if (kind === "pet-supplies") {
      $(`${kind}-rows`).innerHTML = data.items.map((item) => `
        <tr><td><strong>${escapeHtml(item.name || "未知用品")}</strong></td><td>${escapeHtml(item.grade ?? "-")}</td><td>${escapeHtml(item.hungry ?? "-")}</td><td>${escapeHtml(item.sanitary ?? "-")}</td><td>${escapeHtml(item.spirit ?? "-")}</td><td class="mono">${item.amount}</td><td><button class="link-button" data-inventory-edit="${item.item_id}">编辑</button></td></tr>
      `).join("");
    } else {
      $(`${kind}-rows`).innerHTML = data.items.map((item) => `
        <tr><td class="mono">${item.item_id}</td><td><strong>${escapeHtml(item.name || "未知物品")}</strong></td><td class="mono">${item.amount}</td><td><button class="link-button" data-inventory-edit="${item.item_id}">编辑</button></td></tr>
      `).join("");
    }
    $(`${kind}-empty`).classList.toggle("hidden", data.items.length !== 0);
    if (kind === "pet-supplies" || kind === "tools") {
      $(`${kind}-summary`).textContent = `共 ${data.total} 条`;
    } else {
      const start = data.total ? (data.page - 1) * data.page_size + 1 : 0;
      $(`${kind}-summary`).textContent = data.total
        ? `${start}-${Math.min(data.page * data.page_size, data.total)} / 共 ${data.total} 条`
        : "共 0 条";
      $(`${kind}-prev`).disabled = data.page <= 1;
      $(`${kind}-next`).disabled = data.page * data.page_size >= data.total;
    }
  } catch (error) {
    state.items = [];
    $(`${kind}-workspace`).classList.add("hidden");
    $(`${kind}-prompt`).classList.remove("hidden");
    $(`${kind}-prompt`).textContent = error.message === "account not found"
      ? "未找到该账号，请检查 User ID。"
      : `${inventoryLabels[kind]}列表加载失败。`;
    handleRequestError(error);
  }
}

async function loadHouses() {
  if (!housesState.userId) return;
  try {
    const data = await api.listHouses(housesState.userId);
    housesState.items = data.items;
    $("houses-workspace").classList.remove("hidden");
    $("houses-prompt").classList.add("hidden");
    $("houses-owner").textContent = `玩家 ${housesState.userId}`;
    $("houses-rows").innerHTML = data.items.map((item) => `<tr><td class="mono">${item.id}</td><td><strong>${escapeHtml(item.name)}</strong></td><td>${item.owned ? "已拥有" : "未拥有"}</td><td><button class="link-button ${item.owned ? "delete" : ""}" data-house-toggle="${item.id}">${item.owned ? "丢弃" : "获得"}</button></td></tr>`).join("");
  } catch (error) {
    $("houses-workspace").classList.add("hidden");
    $("houses-prompt").classList.remove("hidden");
    $("houses-prompt").textContent = error.message === "account not found" ? "未找到该账号，请检查 User ID。" : "小屋列表加载失败。";
    handleRequestError(error);
  }
}

async function openInventoryModal(kind, item = null) {
  const state = inventoryStates[kind];
  await ensureInventoryOptions(kind);
  state.editingItemId = item ? item.item_id : null;
  $("inventory-form").reset();
  $("inventory-modal-title").textContent = item ? `编辑${inventoryLabels[kind]}` : `新增${inventoryLabels[kind]}`;
  $("inventory-catalog-field").classList.toggle("hidden", Boolean(item));
  $("inventory-item-id").disabled = Boolean(item);
  if (!item) {
    $("inventory-item-id").innerHTML = state.catalog.map((entry) =>
      `<option value="${entry.id}">${escapeHtml(entry.name)}${kind === "pet-supplies" ? "" : ` (${entry.id})`}</option>`
    ).join("");
    $("inventory-modal-description").textContent = `为玩家 ${state.userId} 新增${inventoryLabels[kind]}；已有条目会累加数量。`;
  } else {
    $("inventory-modal-description").textContent = `${item.name || "未知物品"}（Item ID: ${item.item_id}）`;
  }
  $("inventory-amount").value = item ? item.amount : 1;
  $("inventory-form-error").textContent = "";
  $("inventory-modal").classList.remove("hidden");
  $("inventory-modal").dataset.kind = kind;
}

function closeInventoryModal() {
  $("inventory-modal").classList.add("hidden");
  const kind = $("inventory-modal").dataset.kind;
  if (kind && inventoryStates[kind]) inventoryStates[kind].editingItemId = null;
}

async function openHouseGoodsModal(item = null) {
  await ensureHouseGoodsOptions();
  houseGoodsState.editingNo = item ? item.no : null;
  $("house-goods-form").reset();
  $("house-goods-modal-title").textContent = item ? "编辑物品" : "新增物品";
  $("house-goods-catalog-field").classList.toggle("hidden", Boolean(item));
  $("house-goods-item-id").disabled = Boolean(item);
  $("house-goods-modal-description").textContent = item
    ? `${item.name || "未知物品"}（Item ID: ${item.item_id}，序号: ${item.no}）`
    : `为玩家 ${houseGoodsState.userId} 新增小屋物品，序号将自动生成。`;
  $("house-goods-x").value = item ? item.x : 0;
  $("house-goods-y").value = item ? item.y : 0;
  $("house-goods-z").value = item ? item.z : 0;
  $("house-goods-form").elements.m.value = String(item ? item.m : 0);
  $("house-goods-form").elements.is_set.value = String(item ? item.is_set : 0);
  $("house-goods-form-error").textContent = "";
  $("house-goods-modal").classList.remove("hidden");
}

function closeHouseGoodsModal() {
  $("house-goods-modal").classList.add("hidden");
  houseGoodsState.editingNo = null;
}

function openAccountModal(account = null) {
  accountState.editing = account && account.user_id;
  $("modal-title").textContent = account ? "编辑账号" : "新增账号";
  $("account-form").reset();
  $("user-id").disabled = Boolean(account);

  if (account) {
    $("user-id").value = account.user_id;
    $("login-name").value = account.login_name;
    ["role_created", "banned", "enable_friends_application"].forEach((name) => {
      $("account-form").elements[name].checked = Boolean(account[name]);
    });
  } else {
    $("account-form").elements.enable_friends_application.checked = true;
  }
  $("form-error").textContent = "";
  $("modal").classList.remove("hidden");
}

function closeAccountModal() {
  $("modal").classList.add("hidden");
}

function openClothingModal(clothId, name) {
  clothingState.selected = { clothId, name };
  $("clothing-modal-name").textContent = name;
  $("clothing-form-error").textContent = "";
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  $("acquired-at").value = now.toISOString().slice(0, 19);
  $("clothing-modal").classList.remove("hidden");
}

function closeClothingModal() {
  $("clothing-modal").classList.add("hidden");
  clothingState.selected = null;
}

fillProfileOptionFilters();

document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("login-error").textContent = "";
  try {
    await api.login($("admin-user").value, $("admin-password").value);
    showApp(true);
  } catch (error) {
    $("login-error").textContent = error.message;
  }
});

$("logout").addEventListener("click", async () => {
  await api.logout();
  showApp(false);
});

$("refresh").addEventListener("click", loadAccounts);
$("search").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    accountState.page = 1;
    loadAccounts();
  }
});
$("new-account").addEventListener("click", () => openAccountModal());
$("close-modal").addEventListener("click", closeAccountModal);
$("cancel").addEventListener("click", closeAccountModal);
$("prev").addEventListener("click", () => {
  accountState.page -= 1;
  loadAccounts();
});
$("next").addEventListener("click", () => {
  accountState.page += 1;
  loadAccounts();
});

$("profile-apply").addEventListener("click", () => { profileState.page = 1; loadProfiles(); });
$("profile-refresh").addEventListener("click", loadProfiles);
["profile-user-id-filter", "profile-nickname-filter"].forEach((id) => $(id).addEventListener("keydown", (event) => {
  if (event.key === "Enter") { profileState.page = 1; loadProfiles(); }
}));
$("profile-nationality-filter").addEventListener("change", () => { profileState.page = 1; loadProfiles(); });
$("profile-page-size").addEventListener("change", (event) => { profileState.pageSize = Number(event.target.value); profileState.page = 1; loadProfiles(); });
$("profile-prev").addEventListener("click", () => { profileState.page -= 1; loadProfiles(); });
$("profile-next").addEventListener("click", () => { profileState.page += 1; loadProfiles(); });
$("profile-rows").addEventListener("click", async (event) => {
  const edit = event.target.dataset.profileEdit;
  const clothing = event.target.dataset.profileClothing;
  try {
    if (edit) await openProfileModal(edit);
    if (clothing) await openProfileClothingModal(clothing);
  } catch (error) { handleRequestError(error); }
});
$("pet-apply").addEventListener("click", () => { petState.page = 1; loadPets(); });
$("pet-refresh").addEventListener("click", loadPets);
$("pet-add").addEventListener("click", () => openPetModal().catch(handleRequestError));
$("pet-user-id-filter").addEventListener("keydown", (event) => { if (event.key === "Enter") { petState.page = 1; loadPets(); } });
$("pet-page-size").addEventListener("change", (event) => { petState.pageSize = Number(event.target.value); petState.page = 1; loadPets(); });
$("pet-prev").addEventListener("click", () => { petState.page -= 1; loadPets(); });
$("pet-next").addEventListener("click", () => { petState.page += 1; loadPets(); });
$("pet-rows").addEventListener("click", (event) => {
  const button = event.target.closest("[data-pet-edit-user]");
  if (button) openPetModal(button.dataset.petEditUser, button.dataset.petEditId).catch(handleRequestError);
});
$("close-pet-modal").addEventListener("click", closePetModal);
$("cancel-pet").addEventListener("click", closePetModal);
$("pet-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("pet-form-error").textContent = "";
  const form = new FormData(event.target);
  const payload = Object.fromEntries(form.entries());
  ["pet_id", "love_energy", "hungry_index", "clean_index", "mood_index", "health_state", "is_vip", "wonderful_value", "rest_at"].forEach((field) => { payload[field] = Number(payload[field]); });
  payload.age = Math.floor(new Date(payload.age).getTime() / 1000);
  if (!petState.editing) payload.user_id = Number(payload.user_id);
  const submitButton = event.target.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  try {
    if (petState.editing) {
      await api.updatePet(petState.editing.userId, petState.editing.petId, payload);
    } else {
      await api.createPet(payload);
      $("pet-user-id-filter").value = payload.user_id;
      petState.page = 1;
    }
    closePetModal();
    await loadPets();
  }
  catch (error) { $("pet-form-error").textContent = error.message; }
  finally { submitButton.disabled = false; }
});
$("garden-apply").addEventListener("click", () => { gardenState.page = 1; loadGardens(); });
$("garden-reset").addEventListener("click", () => {
  $("garden-user-id-filter").value = "";
  gardenState.page = 1;
  loadGardens();
});
$("garden-user-id-filter").addEventListener("keydown", (event) => {
  if (event.key === "Enter") { gardenState.page = 1; loadGardens(); }
});
$("garden-page-size").addEventListener("change", (event) => {
  gardenState.pageSize = Number(event.target.value);
  gardenState.page = 1;
  loadGardens();
});
$("garden-prev").addEventListener("click", () => { gardenState.page -= 1; loadGardens(); });
$("garden-next").addEventListener("click", () => { gardenState.page += 1; loadGardens(); });
$("garden-rows").addEventListener("click", async (event) => {
  const userId = event.target.dataset.gardenEdit;
  if (!userId) return;
  const item = gardenState.items.find((candidate) => candidate.user_id === Number(userId));
  if (item) openGardenModal(item).catch(handleRequestError);
});
$("close-garden-modal").addEventListener("click", closeGardenModal);
$("cancel-garden").addEventListener("click", closeGardenModal);
$("garden-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("garden-form-error").textContent = "";
  const form = new FormData(event.target);
  const payload = {
    background_id: Number(form.get("background_id")),
    home_name: form.get("home_name"),
    weather: Number(form.get("weather")),
    temperature: form.get("temperature"),
    item_id: Number(form.get("item_id")),
    x: Number(form.get("x")),
    y: Number(form.get("y")),
    open_flag: Number(form.get("open_flag")),
  };
  try {
    await api.updateGarden(gardenState.editing, payload);
    closeGardenModal();
    loadGardens();
  } catch (error) { $("garden-form-error").textContent = error.message; }
});
$("close-profile-modal").addEventListener("click", closeProfileModal);
$("cancel-profile").addEventListener("click", closeProfileModal);
$("profile-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("profile-form-error").textContent = "";
  const form = new FormData(event.target);
  const payload = Object.fromEntries(form.entries());
  ["nationality", "birthday", "love", "beautiful", "wisdom", "plant_grade", "faerie_grade", "money", "face_color", "face", "eye", "eyebrow", "lip"]
    .forEach((field) => { payload[field] = Number(payload[field]); });
  try { await api.updateProfile(profileState.editing, payload); closeProfileModal(); loadProfiles(); }
  catch (error) { $("profile-form-error").textContent = error.message; }
});
$("close-profile-clothing-modal").addEventListener("click", closeProfileClothingModal);
$("cancel-profile-clothing").addEventListener("click", closeProfileClothingModal);
$("profile-clothing-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("profile-clothing-form-error").textContent = "";
  const clothing = {};
  event.target.querySelectorAll("[data-clothing-slot]").forEach((select) => { clothing[select.dataset.clothingSlot] = Number(select.value); });
  try { await api.updateProfileClothing(profileState.clothingEditing, clothing); closeProfileClothingModal(); loadProfiles(); }
  catch (error) { $("profile-clothing-form-error").textContent = error.message; }
});

$("account-rows").addEventListener("click", async (event) => {
  const edit = event.target.dataset.edit;
  const remove = event.target.dataset.delete;
  if (edit) {
    try {
      openAccountModal(await api.getAccount(edit));
    } catch (error) {
      handleRequestError(error);
    }
  }
  if (remove && confirm("确定删除这个账号吗？此操作不可撤销。")) {
    try {
      await api.deleteAccount(remove);
      loadAccounts();
    } catch (error) {
      handleRequestError(error);
    }
  }
});

$("account-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("form-error").textContent = "";
  const form = new FormData(event.target);
  const payload = {
    login_name: form.get("login_name"),
    password: form.get("password"),
    role_created: form.has("role_created") ? 1 : 0,
    banned: form.has("banned") ? 1 : 0,
    enable_friends_application: form.has("enable_friends_application") ? 1 : 0,
  };
  if (!accountState.editing) payload.user_id = Number(form.get("user_id"));

  try {
    if (accountState.editing) {
      await api.updateAccount(accountState.editing, payload);
    } else {
      await api.createAccount(payload);
    }
    closeAccountModal();
    loadAccounts();
  } catch (error) {
    $("form-error").textContent = error.message;
  }
});

$("clothes-user-form").addEventListener("submit", (event) => {
  event.preventDefault();
  clothingState.userId = Number($("clothes-user-id").value);
  clothingState.page = 1;
  loadClothes();
});

$("apply-clothes-filters").addEventListener("click", () => {
  clothingState.page = 1;
  loadClothes();
});
$("clothes-name").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    clothingState.page = 1;
    loadClothes();
  }
});
$("reset-clothes-filters").addEventListener("click", () => {
  $("clothes-name").value = "";
  $("clothes-sex").value = "";
  $("clothes-type").value = "";
  clothingState.page = 1;
  loadClothes();
});
$("clothes-page-size").addEventListener("change", (event) => {
  clothingState.pageSize = Number(event.target.value);
  clothingState.page = 1;
  loadClothes();
});
$("clothes-prev").addEventListener("click", () => {
  clothingState.page -= 1;
  loadClothes();
});
$("clothes-next").addEventListener("click", () => {
  clothingState.page += 1;
  loadClothes();
});

$("clothes-rows").addEventListener("click", async (event) => {
  const acquire = event.target.dataset.acquire;
  const discard = event.target.dataset.discard;
  if (acquire) {
    openClothingModal(Number(acquire), event.target.dataset.name);
  } else if (discard) {
    try {
      await api.discardClothing(clothingState.userId, discard);
      loadClothes();
    } catch (error) {
      handleRequestError(error);
    }
  }
});

$("close-clothing-modal").addEventListener("click", closeClothingModal);
$("cancel-clothing").addEventListener("click", closeClothingModal);
$("clothing-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("clothing-form-error").textContent = "";
  try {
    await api.acquireClothing({
      user_id: clothingState.userId,
      cloth_id: clothingState.selected.clothId,
      acquired_at: $("acquired-at").value,
    });
    closeClothingModal();
    loadClothes();
  } catch (error) {
    $("clothing-form-error").textContent = error.message;
  }
});

$("house-goods-user-form").addEventListener("submit", (event) => {
  event.preventDefault();
  houseGoodsState.userId = Number($("house-goods-user-id").value);
  houseGoodsState.page = 1;
  loadHouseGoods();
});

$("house-goods-page-size").addEventListener("change", (event) => {
  houseGoodsState.pageSize = Number(event.target.value);
  houseGoodsState.page = 1;
  loadHouseGoods();
});
$("house-goods-prev").addEventListener("click", () => {
  houseGoodsState.page -= 1;
  loadHouseGoods();
});
$("house-goods-next").addEventListener("click", () => {
  houseGoodsState.page += 1;
  loadHouseGoods();
});

$("new-house-goods").addEventListener("click", () => {
  openHouseGoodsModal().catch(handleRequestError);
});

$("house-goods-rows").addEventListener("click", (event) => {
  const no = event.target.dataset.houseGoodsEdit;
  const remove = event.target.dataset.houseGoodsDelete;
  if (no) {
    const item = houseGoodsState.items.find((candidate) => candidate.no === Number(no));
    if (item) openHouseGoodsModal(item).catch(handleRequestError);
  } else if (remove && confirm("确定删除这条小屋物品吗？此操作不可撤销。")) {
    api.deleteHouseGoods(houseGoodsState.userId, Number(remove))
      .then(() => {
        const lastPage = Math.max(1, Math.ceil((houseGoodsState.total - 1) / houseGoodsState.pageSize));
        houseGoodsState.page = Math.min(houseGoodsState.page, lastPage);
        loadHouseGoods();
      })
      .catch(handleRequestError);
  }
});

$("close-house-goods-modal").addEventListener("click", closeHouseGoodsModal);
$("cancel-house-goods").addEventListener("click", closeHouseGoodsModal);
$("house-goods-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("house-goods-form-error").textContent = "";
  const form = new FormData(event.target);
  const payload = {
    x: Number(form.get("x")),
    y: Number(form.get("y")),
    m: Number(form.get("m")),
    z: Number(form.get("z")),
    is_set: Number(form.get("is_set")),
  };
  try {
    if (houseGoodsState.editingNo === null) {
      payload.user_id = houseGoodsState.userId;
      payload.item_id = Number(form.get("item_id"));
      await api.createHouseGoods(payload);
    } else {
      await api.updateHouseGoods(
        houseGoodsState.userId,
        houseGoodsState.editingNo,
        payload,
      );
    }
    closeHouseGoodsModal();
    loadHouseGoods();
  } catch (error) {
    $("house-goods-form-error").textContent = error.message;
  }
});

$("actions-user-form").addEventListener("submit", (event) => {
  event.preventDefault();
  actionsState.userId = Number($("actions-user-id").value);
  loadActions();
});

$("new-action").addEventListener("click", () => {
  openActionModal().catch(handleRequestError);
});

$("actions-rows").addEventListener("click", (event) => {
  const actionId = event.target.dataset.actionEdit;
  if (!actionId) return;
  const item = actionsState.items.find((candidate) => candidate.action_id === Number(actionId));
  if (item) openActionModal(item).catch(handleRequestError);
});

$("close-action-modal").addEventListener("click", closeActionModal);
$("cancel-action").addEventListener("click", closeActionModal);
$("action-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("action-form-error").textContent = "";
  const amount = Number($("action-amount").value);
  try {
    if (actionsState.editingActionId === null) {
      await api.createAction({
        user_id: actionsState.userId,
        action_id: Number($("action-id").value),
        amount,
      });
    } else {
      await api.updateAction(actionsState.userId, actionsState.editingActionId, { amount });
    }
    closeActionModal();
    loadActions();
  } catch (error) {
    $("action-form-error").textContent = error.message;
  }
});

for (const kind of Object.keys(inventoryStates)) {
  const state = inventoryStates[kind];
  $(`${kind}-user-form`).addEventListener("submit", (event) => {
    event.preventDefault();
    state.userId = Number($(`${kind}-user-id`).value);
    state.page = 1;
    loadInventory(kind);
  });
  $(`${kind}-apply`).addEventListener("click", () => {
    state.page = 1;
    loadInventory(kind);
  });
  $(`${kind}-name`).addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      state.page = 1;
      loadInventory(kind);
    }
  });
  $(`${kind}-reset`).addEventListener("click", () => {
    $(`${kind}-name`).value = "";
    state.page = 1;
    loadInventory(kind);
  });
  if (kind !== "pet-supplies" && kind !== "tools") {
    $(`${kind}-page-size`).addEventListener("change", (event) => {
      state.pageSize = Number(event.target.value);
      state.page = 1;
      loadInventory(kind);
    });
    $(`${kind}-prev`).addEventListener("click", () => {
      state.page -= 1;
      loadInventory(kind);
    });
    $(`${kind}-next`).addEventListener("click", () => {
      state.page += 1;
      loadInventory(kind);
    });
  }
  $(`${kind}-rows`).addEventListener("click", (event) => {
    const itemId = event.target.dataset.inventoryEdit;
    if (!itemId) return;
    const item = state.items.find((candidate) => candidate.item_id === Number(itemId));
    if (item) openInventoryModal(kind, item).catch(handleRequestError);
  });
  $(`new-${kind}`).addEventListener("click", () => openInventoryModal(kind).catch(handleRequestError));
}

$("houses-user-form").addEventListener("submit", (event) => {
  event.preventDefault();
  housesState.userId = Number($("houses-user-id").value);
  loadHouses();
});
$("houses-rows").addEventListener("click", async (event) => {
  const houseId = event.target.dataset.houseToggle;
  if (!houseId) return;
  try { await api.toggleHouse(housesState.userId, Number(houseId)); loadHouses(); }
  catch (error) { handleRequestError(error); }
});

$("tasks-user-form").addEventListener("submit", (event) => {
  event.preventDefault(); tasksState.userId = Number($("tasks-user-id").value); loadTasks();
});
$("tasks-rows").addEventListener("click", async (event) => {
  const jobId = event.target.dataset.taskReset;
  if (!jobId) return;
  if (!confirm(`确认重置任务 ${jobId}？该玩家的任务进度、完成记录和任务物品将被删除。`)) return;
  try { await api.resetTask(tasksState.userId, Number(jobId)); await loadTasks(); alert("任务已重置"); }
  catch (error) { handleRequestError(error); }
});

$("close-inventory-modal").addEventListener("click", closeInventoryModal);
$("cancel-inventory").addEventListener("click", closeInventoryModal);
$("inventory-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const kind = $("inventory-modal").dataset.kind;
  const state = inventoryStates[kind];
  $("inventory-form-error").textContent = "";
  try {
    const amount = Number($("inventory-amount").value);
    if (state.editingItemId === null) {
      await api.createInventory(kind, {
        user_id: state.userId,
        item_id: Number($("inventory-item-id").value),
        amount,
      });
    } else {
      await api.updateInventory(kind, state.userId, state.editingItemId, { amount });
    }
    closeInventoryModal();
    loadInventory(kind);
  } catch (error) {
    $("inventory-form-error").textContent = error.message;
  }
});
  
api.getSession()
  .then((data) => showApp(data.authenticated))
  .catch(() => showApp(false));
