// AI settings: let a user add their own Anthropic API key for the Copilot ("bring your own key").
// The key stays in this browser and is sent only with Copilot requests; the server uses it for that request
// and never stores or logs it. A server-wide key (ANTHROPIC_API_KEY) is used when the user has none.
import { useEffect, useState } from "react";
import { KeyRound, X, Check, AlertTriangle } from "lucide-react";
import { useApi, userKey, checkKey } from "../services/api.js";

export function useUserKey() {
  const [k, setK] = useState(() => userKey.get());
  useEffect(() => {
    const on = () => setK(userKey.get());
    window.addEventListener("firewise-key", on);
    window.addEventListener("storage", on);
    return () => { window.removeEventListener("firewise-key", on); window.removeEventListener("storage", on); };
  }, []);
  return k;
}

/** Status line: which language model source the Copilot will use. */
export function CopilotModeLine() {
  const k = useUserKey();
  const { data: h } = useApi("/api/health");
  if (!h) return null;
  if (k) return <>Language model: your API key ({userKey.masked(k)}).</>;
  if (h.copilot_configured) return <>Language model: server key.</>;
  return <>No language model key: answers are built deterministically from the database. Add your own key in AI settings.</>;
}

export default function ApiKeySettings() {
  const [open, setOpen] = useState(false);
  const k = useUserKey();
  const { data: h } = useApi("/api/health");
  const [input, setInput] = useState("");
  const [remember, setRemember] = useState(false);
  const [state, setState] = useState({ busy: false, result: null, error: null });

  useEffect(() => {
    if (!open) return undefined;
    setInput(""); setRemember(userKey.remembered()); setState({ busy: false, result: null, error: null });
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const save = async (e) => {
    e.preventDefault();
    const key = input.trim();
    if (!/^sk-ant-[A-Za-z0-9_-]{20,200}$/.test(key)) {
      setState({ busy: false, result: null, error: "That does not look like an Anthropic API key (it starts with sk-ant-)." });
      return;
    }
    setState({ busy: true, result: null, error: null });
    try {
      const r = await checkKey(key);
      if (r.valid) { userKey.set(key, remember); setInput(""); }
      setState({ busy: false, result: r, error: null });
    } catch (err) {
      setState({ busy: false, result: null, error: err.message });
    }
  };

  return (
    <>
      <button className="btn" onClick={() => setOpen(true)} aria-haspopup="dialog">
        <KeyRound /> AI settings{k ? <span className="tag green">your key</span> : null}
      </button>
      {open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="AI settings" onClick={() => setOpen(false)}>
          <aside className="modal" onClick={(e) => e.stopPropagation()}>
            <header className="modal-head">
              <div><span className="eyebrow">Copilot</span><h3>AI settings</h3></div>
              <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close"><X size={18} /></button>
            </header>
            <div className="modal-body key-settings">
              <p className="muted">The Copilot can use a Claude language model to write answers. Every answer is still checked by the FIREWISE validator (citations must resolve; numbers must appear in the cited evidence). Without a key, answers are built deterministically from the database.</p>
              <dl className="key-status">
                <dt>Server key</dt><dd>{h ? (h.copilot_configured ? "configured by the server operator" : "not configured") : "…"}</dd>
                <dt>Your key</dt><dd>{k ? <><span className="mono">{userKey.masked(k)}</span> · {userKey.remembered() ? "remembered on this device" : "this browser session only"}</> : "not set"}</dd>
                <dt>Model</dt><dd className="mono">{h?.copilot_model ?? "…"}</dd>
              </dl>

              <form onSubmit={save} className="key-form">
                <label htmlFor="ak">{k ? "Replace your Anthropic API key" : "Your Anthropic API key"}</label>
                <input id="ak" type="password" autoComplete="off" spellCheck={false} placeholder="sk-ant-…" value={input} onChange={(e) => setInput(e.target.value)} />
                <label className="check"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember on this device</label>
                <div className="btn-row">
                  <button className="btn primary" type="submit" disabled={state.busy || !input.trim()}>{state.busy ? "Checking…" : "Check and save"}</button>
                  {k && <button className="btn danger" type="button" onClick={() => { userKey.clear(); setState({ busy: false, result: null, error: null }); }}>Remove my key</button>}
                </div>
              </form>
              {state.result && (
                <p className={`key-result ${state.result.valid ? "ok" : "bad"}`} role="status">
                  {state.result.valid ? <Check size={15} /> : <AlertTriangle size={15} />} {state.result.message}{state.result.valid ? " Saved." : " Not saved."}
                </p>
              )}
              {state.error && <p className="key-result bad" role="alert"><AlertTriangle size={15} /> {state.error}</p>}

              <h4>Where your key goes</h4>
              <ul className="limits small">
                <li>It is stored only in this browser: for this session, or on this device if you tick “remember”.</li>
                <li>It is sent over HTTPS to this FIREWISE server with Copilot questions only, in a request header — never in a URL.</li>
                <li>The server uses it for that single request to call Anthropic and never stores, caches or logs it.</li>
                <li>Checking a key uses Anthropic's free Models API. Copilot answers are billed to your Anthropic account.</li>
                <li>Anyone with access to this browser profile could read a remembered key. Remove it when you are done on a shared computer.</li>
              </ul>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
