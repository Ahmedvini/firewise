// ============================================================
// FIREWISE API CLIENT — the only place that talks to the backend.
// Production: the FastAPI server serves this build, so API_BASE_URL is "" (same origin).
// Development: `npm run dev` proxies /api to http://127.0.0.1:8000 (see vite.config.js).
// A separate host can be set with VITE_API_BASE_URL (that host must allow CORS for this origin).
// ============================================================
import { useCallback, useEffect, useState } from "react";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details || {};
  }
}

/** Human-readable validation messages from a 422 error envelope. */
export const errorLines = (e) => (e?.details?.errors || []).map((x) => x.msg.replace(/^Value error, /, ""));

async function request(path, options = {}) {
  // One automatic retry on a network-level failure — a dropped/changed connection or a truncated body.
  // HTTP errors (4xx/5xx) are not retried. A response that cannot be read is NEVER treated as empty success.
  for (let attempt = 0; ; attempt++) {
    let response, text;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
      });
      text = await response.text();
    } catch (error) {
      if (error.name === "AbortError") throw error;
      if (attempt === 0) { await new Promise((r) => setTimeout(r, 400)); continue; }
      throw new ApiError(0, "network_error", "The FIREWISE data service is unreachable. Check your connection, then retry.");
    }
    if (response.status === 204) return null;
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch { body = undefined; }
    if (!response.ok) {
      throw new ApiError(response.status, body?.error?.code ?? "error", body?.error?.message ?? `The server responded with status ${response.status}.`, body?.error?.details);
    }
    if (body === undefined || body === null) {
      if (attempt === 0) { await new Promise((r) => setTimeout(r, 400)); continue; }
      throw new ApiError(0, "bad_response", "The server response could not be read. Check your connection, then retry.");
    }
    return body;
  }
}

export const apiGet = (path, signal) => request(path, { signal });

// ------------------------------------------------------------ workspace key
// Scenarios and conversations belong to a random workspace key generated in this browser (header X-Workspace).
// It is capability-key isolation, not a login: anyone holding the key sees the same workspace.
let memoryKey = null;
export function workspaceKey() {
  try {
    let k = window.localStorage.getItem("firewise.workspace");
    if (!k || !/^[A-Za-z0-9_-]{32,128}$/.test(k)) {
      k = `ws-${crypto.randomUUID()}`;
      window.localStorage.setItem("firewise.workspace", k);
    }
    return k;
  } catch {
    memoryKey ||= `ws-${crypto.randomUUID()}`; // storage blocked: key lives for this page session only
    return memoryKey;
  }
}
const ws = (options = {}) => ({ ...options, headers: { "X-Workspace": workspaceKey(), ...(options.headers || {}) } });
const json = (method, body) => ({ method, body: JSON.stringify(body) });

// ------------------------------------------------------------ "Bring your own" Anthropic key
// Stored only in this browser: sessionStorage by default (cleared when the tab closes), localStorage if the user
// chooses "remember on this device". Sent only with Copilot requests, as the X-Anthropic-Key header (never in a URL).
const KEY_NAME = "firewise.anthropic_key";
export const userKey = {
  get() {
    try { return window.sessionStorage.getItem(KEY_NAME) || window.localStorage.getItem(KEY_NAME) || null; } catch { return null; }
  },
  remembered() {
    try { return !!window.localStorage.getItem(KEY_NAME); } catch { return false; }
  },
  set(key, remember) {
    try {
      window.sessionStorage.removeItem(KEY_NAME); window.localStorage.removeItem(KEY_NAME);
      (remember ? window.localStorage : window.sessionStorage).setItem(KEY_NAME, key);
    } catch { /* storage blocked */ }
    window.dispatchEvent(new Event("firewise-key"));
  },
  clear() {
    try { window.sessionStorage.removeItem(KEY_NAME); window.localStorage.removeItem(KEY_NAME); } catch { /* storage blocked */ }
    window.dispatchEvent(new Event("firewise-key"));
  },
  masked(k = userKey.get()) { return k ? `${k.slice(0, 7)}…${k.slice(-4)}` : null; },
};
const withKey = (options = {}) => {
  const k = userKey.get();
  return k ? { ...options, headers: { ...(options.headers || {}), "X-Anthropic-Key": k } } : options;
};
export const checkKey = (key) => request("/api/copilot/key/check", { method: "POST", headers: { "X-Anthropic-Key": key } });

// ------------------------------------------------------------ Digital Twin
export const twin = {
  environments: () => request("/api/twin/environments"),
  presets: (envId) => request(`/api/twin/environments/${encodeURIComponent(envId)}/presets`),
  models: () => request("/api/twin/models"),
  validation: () => request("/api/twin/validation"),
  evaluate: (scenario, signal) => request("/api/twin/evaluate", { ...json("POST", { scenario, nearest_limit: 25 }), signal }),
  list: () => request("/api/twin/scenarios", ws()),
  get: (id) => request(`/api/twin/scenarios/${id}`, ws()),
  create: (scenario) => request("/api/twin/scenarios", ws(json("POST", scenario))),
  update: (id, scenario, note) => request(`/api/twin/scenarios/${id}${note ? `?note=${encodeURIComponent(note)}` : ""}`, ws(json("PUT", scenario))),
  remove: (id) => request(`/api/twin/scenarios/${id}`, ws({ method: "DELETE" })),
  duplicate: (id, name) => request(`/api/twin/scenarios/${id}/duplicate`, ws(json("POST", { name }))),
  history: (id) => request(`/api/twin/scenarios/${id}/history`, ws()),
  compare: (ids) => request("/api/twin/compare", ws(json("POST", { ids }))),
  simulate: (id) => request(`/api/twin/scenarios/${id}/simulations`, ws({ method: "POST" })),
  runs: (id) => request(`/api/twin/scenarios/${id}/simulations`, ws()),
  run: (runId) => request(`/api/twin/simulations/${runId}`, ws()),
  report: (id) => request(`/api/twin/scenarios/${id}/report`, ws()),
  reportUnsaved: (scenario) => request("/api/twin/report", json("POST", scenario)),
};

// ------------------------------------------------------------ Copilot conversations (saved history, switching chats)
export const chats = {
  list: (kind) => request(`/api/conversations${kind ? `?kind=${kind}` : ""}`, ws()),
  create: (kind = "general", title) => request("/api/conversations", ws(json("POST", { kind, title: title ?? null }))),
  get: (id) => request(`/api/conversations/${id}`, ws()),
  rename: (id, title) => request(`/api/conversations/${id}`, ws(json("PATCH", { title }))),
  remove: (id) => request(`/api/conversations/${id}`, ws({ method: "DELETE" })),
  send: (id, question, twinContext) => request(`/api/conversations/${id}/messages`, withKey(ws(json("POST", { question, twin: twinContext ?? null })))),
};

/** POST /api/ask — evidence-grounded Copilot. Returns the AskResponse contract (docs/FINAL_API_CONTRACT.md §4). */
export const askQuestion = (question, scenarioId) =>
  request("/api/ask", withKey({ method: "POST", body: JSON.stringify({ question, scenario_id: scenarioId ?? null }) }));

export const scenarioCustom = (window) =>
  request("/api/scenarios/custom/evidence", { method: "POST", body: JSON.stringify(window) });

const cache = new Map();

/** React hook: GET a path; refetches when it changes; `null` path stays idle. Results are cached per session. */
export function useApi(path) {
  const [state, setState] = useState({ data: path && cache.get(path), error: null, loading: !!path && !cache.has(path) });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!path) {
      setState({ data: null, error: null, loading: false });
      return undefined;
    }
    if (cache.has(path) && tick === 0) {
      setState({ data: cache.get(path), error: null, loading: false });
      return undefined;
    }
    const controller = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    apiGet(path, controller.signal)
      .then((data) => {
        if (data != null) cache.set(path, data); // never cache an empty result
        setState({ data, error: null, loading: false });
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setState({ data: null, error, loading: false });
      });
    return () => controller.abort();
  }, [path, tick]);

  const reload = useCallback(() => {
    cache.delete(path);
    setTick((t) => t + 1);
  }, [path]);
  return { ...state, reload };
}
