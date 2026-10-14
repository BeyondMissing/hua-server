async function request(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

export function getSession() {
  return request("/api/session");
}

export function login(username, password) {
  return request("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout() {
  return request("/api/logout", { method: "POST" });
}

export function listAccounts({ page, pageSize, search }) {
  const query = new URLSearchParams({
    page,
    page_size: pageSize,
    search,
  });
  return request(`/api/accounts?${query}`);
}

export function getAccount(userId) {
  return request(`/api/accounts/${userId}`);
}

export function createAccount(payload) {
  return request("/api/accounts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAccount(userId, payload) {
  return request(`/api/accounts/${userId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAccount(userId) {
  return request(`/api/accounts/${userId}`, { method: "DELETE" });
}

export function getClothingOptions() {
  return request("/api/player-clothes/options");
}

export function listClothes({ userId, page, pageSize, name, sex, clothType }) {
  const query = new URLSearchParams({
    user_id: userId,
    page,
    page_size: pageSize,
  });
  if (name) query.set("name", name);
  if (sex !== "") query.set("sex", sex);
  if (clothType !== "") query.set("cloth_type", clothType);
  return request(`/api/player-clothes?${query}`);
}

export function acquireClothing(payload) {
  return request("/api/player-clothes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function discardClothing(userId, clothId) {
  return request(`/api/player-clothes/${userId}/${clothId}`, { method: "DELETE" });
}

export function listHouseGoods({ userId, page, pageSize }) {
  const query = new URLSearchParams({ user_id: userId, page, page_size: pageSize });
  return request(`/api/player-house-goods?${query}`);
}

export function getHouseGoodsOptions() {
  return request("/api/player-house-goods/options");
}

export function createHouseGoods(payload) {
  return request("/api/player-house-goods", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateHouseGoods(userId, no, payload) {
  return request(`/api/player-house-goods/${userId}/${no}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteHouseGoods(userId, no) {
  return request(`/api/player-house-goods/${userId}/${no}`, { method: "DELETE" });
}

export function listActions(userId) {
  const query = new URLSearchParams({ user_id: userId });
  return request(`/api/player-actions?${query}`);
}

export function getActionOptions() {
  return request("/api/player-actions/options");
}

export function createAction(payload) {
  return request("/api/player-actions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAction(userId, actionId, payload) {
  return request(`/api/player-actions/${userId}/${actionId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function listInventory(kind, { userId, page, pageSize, name }) {
  const query = new URLSearchParams({ user_id: userId, page, page_size: pageSize });
  if (name) query.set("name", name);
  return request(`/api/player-${kind}?${query}`);
}

export function getInventoryOptions(kind) {
  return request(`/api/player-${kind}/options`);
}

export function createInventory(kind, payload) {
  return request(`/api/player-${kind}`, { method: "POST", body: JSON.stringify(payload) });
}

export function updateInventory(kind, userId, itemId, payload) {
  return request(`/api/player-${kind}/${userId}/${itemId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function listProfiles({ page, pageSize, userId, nickname, nationality }) {
  const query = new URLSearchParams({ page, page_size: pageSize });
  if (userId) query.set("user_id", userId);
  if (nickname) query.set("nickname", nickname);
  if (nationality !== "") query.set("nationality", nationality);
  return request(`/api/player-profiles?${query}`);
}

export function listPets({ page, pageSize, userId }) {
  const query = new URLSearchParams({ page, page_size: pageSize });
  if (userId) query.set("user_id", userId);
  return request(`/api/player-pets?${query}`);
}

export function getPet(userId, petId) {
  return request(`/api/player-pets/${userId}/${petId}`);
}

export function updatePet(userId, petId, payload) {
  return request(`/api/player-pets/${userId}/${petId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export function createPet(payload) {
  return request("/api/player-pets", { method: "POST", body: JSON.stringify(payload) });
}

export function getProfile(userId) {
  return request(`/api/player-profiles/${userId}`);
}

export function getProfileOptions(userId) {
  return request(`/api/player-profiles/${userId}/options`);
}

export function updateProfile(userId, payload) {
  return request(`/api/player-profiles/${userId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export function updateProfileClothing(userId, clothing) {
  return request(`/api/player-profiles/${userId}/clothing`, {
    method: "PUT",
    body: JSON.stringify({ clothing }),
  });
}

export function listGardens({ page, pageSize, userId }) {
  const query = new URLSearchParams({ page, page_size: pageSize });
  if (userId) query.set("user_id", userId);
  return request(`/api/player-homes?${query}`);
}

export function getGardenOptions(userId) {
  const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request(`/api/player-homes/options${query}`);
}

export function listHouses(userId) {
  return request(`/api/player-houses?user_id=${encodeURIComponent(userId)}`);
}

export function toggleHouse(userId, houseId) {
  return request(`/api/player-houses/${userId}/${houseId}`, { method: "POST" });
}

export function updateGarden(userId, payload) {
  return request(`/api/player-homes/${userId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export function listTasks(userId) {
  return request(`/api/tasks?user_id=${encodeURIComponent(userId)}`);
}

export function resetTask(userId, jobId) {
  return request("/api/tasks/reset", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, job_id: jobId }),
  });
}
