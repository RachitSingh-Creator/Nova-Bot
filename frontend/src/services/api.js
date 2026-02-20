import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("nova_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const setTokens = (access, refresh) => {
  localStorage.setItem("nova_access_token", access);
  localStorage.setItem("nova_refresh_token", refresh);
};

export const clearTokens = () => {
  localStorage.removeItem("nova_access_token");
  localStorage.removeItem("nova_refresh_token");
};

export const getAccessToken = () => localStorage.getItem("nova_access_token");

export async function login(payload) {
  const { data } = await api.post("/auth/login", payload);
  return data;
}

export async function signup(payload) {
  const { data } = await api.post("/auth/signup", payload);
  return data;
}

export async function fetchMe() {
  const { data } = await api.get("/users/me");
  return data;
}

export async function fetchUsage() {
  const { data } = await api.get("/users/usage/summary");
  return data;
}

export async function createChat(payload) {
  const { data } = await api.post("/chat/new", payload);
  return data;
}

export async function listChats() {
  const { data } = await api.get("/chat/list");
  return data;
}

export async function renameChat(chatId, title) {
  const { data } = await api.patch(`/chat/${chatId}`, { title });
  return data;
}

export async function deleteChat(chatId) {
  const { data } = await api.delete(`/chat/${chatId}`);
  return data;
}

export async function fetchHistory(chatId) {
  const { data } = await api.get(`/chat/history/${chatId}`);
  return data;
}

export async function sendChat(payload) {
  const { data } = await api.post("/chat/send", payload);
  return data;
}

export function streamChat(payload, onToken, onDone, onError, abortSignal) {
  const token = getAccessToken();
  return fetch(`${API_BASE}/chat/send/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
    signal: abortSignal,
  }).then(async (response) => {
    if (!response.ok || !response.body) {
      throw new Error(`Streaming failed (${response.status})`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      for (const evt of events) {
        if (!evt.startsWith("data:")) continue;
        const raw = evt.slice(5).trim();
        if (!raw) continue;
        const parsed = JSON.parse(raw);
        if (parsed.type === "token") onToken(parsed.value);
        if (parsed.type === "done") onDone();
        if (parsed.type === "error") onError(parsed.value);
      }
    }
  });
}
