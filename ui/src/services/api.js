// ============================================================
// FIREWISE API CLIENT — the only place that talks to the backend.
// Production: the FastAPI server serves this build, so API_BASE_URL is "" (same origin).
// Development: `npm run dev` proxies /api to http://127.0.0.1:8000 (see vite.config.js).
// A separate host can be set with VITE_API_BASE_URL (that host must allow CORS for this origin).
// ============================================================
import { useCallback, useEffect, useState } from "react";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers },
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "The FIREWISE data service is unreachable. Is the backend running?");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, body?.error?.code ?? "error", body?.error?.message ?? `The server responded with status ${response.status}.`);
  }
  return body;
}

export const apiGet = (path, signal) => request(path, { signal });

/** POST /api/ask — evidence-grounded Copilot. Returns the AskResponse contract (docs/FINAL_API_CONTRACT.md §4). */
export const askQuestion = (question, scenarioId) =>
  request("/api/ask", { method: "POST", body: JSON.stringify({ question, scenario_id: scenarioId ?? null }) });

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
        cache.set(path, data);
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
