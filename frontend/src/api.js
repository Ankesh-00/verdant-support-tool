// Thin API client. Token is kept in localStorage so an agent stays signed in
// across refreshes.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TOKEN_KEY = "verdant_agent_token";

export const auth = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request(path, { method = "GET", body, authed = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (authed) {
    const t = auth.get();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  // customer
  testCustomers: () => request("/api/customer/test-customers"),
  sendCustomerMessage: (payload) =>
    request("/api/customer/message", { method: "POST", body: payload }),
  customerConversation: (phone) =>
    request(`/api/customer/conversation?phone=${encodeURIComponent(phone)}`),

  // agent
  login: (username, password) =>
    request("/api/agent/login", { method: "POST", body: { username, password } }),
  conversations: () => request("/api/agent/conversations", { authed: true }),
  conversation: (id) => request(`/api/agent/conversations/${id}`, { authed: true }),
  approve: (id, draftId, text) =>
    request(`/api/agent/conversations/${id}/approve`, {
      method: "POST",
      authed: true,
      body: { draft_id: draftId, text },
    }),
};
