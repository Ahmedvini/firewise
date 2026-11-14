// AI settings: bring your own API key for any supported AI provider (Anthropic Claude, OpenAI, Google Gemini,
// OpenRouter, Groq, Mistral, DeepSeek, xAI, Together AI). The key stays in this browser and is sent only with Copilot
// requests; the server calls only the provider's fixed API address, uses the key for that request, and never stores it.
import { useEffect, useState } from "react";
import { KeyRound, X, Check, AlertTriangle } from "lucide-react";
import { useApi, userLLM, checkKey } from "../services/api.js";

export function useUserLLM() {
  const [c, setC] = useState(() => userLLM.get());
  useEffect(() => {
    const on = () => setC(userLLM.get());
    window.addEventListener("firewise-key", on);
    window.addEventListener("storage", on);
    return () => { window.removeEventListener("firewise-key", on); window.removeEventListener("storage", on); };
  }, []);
  return c;
}

const providerLabel = (providers, id) => providers?.find((p) => p.id === id)?.label ?? id;

/** Status line: which language model the Copilot will use. */
export function CopilotModeLine() {
  const c = useUserLLM();
  const { data: h } = useApi("/api/health");
  const { data: pv } = useApi("/api/copilot/providers");
  if (!h) return null;
  if (c) return <>Language model: {providerLabel(pv?.providers, c.provider)}{c.model ? ` · ${c.model}` : ""} with your key ({userLLM.masked(c.key)}).</>;
  if (h.copilot_configured) return <>Language model: server key ({h.copilot_model}).</>;
  return <>No language-model key: answers are built deterministically from the database. Add your own key in AI settings.</>;
}

const ANTHROPIC_RE = /^sk-ant-[A-Za-z0-9_-]{20,200}$/;
const GENERIC_RE = /^[A-Za-z0-9_\-.:]{16,300}$/;

export default function ApiKeySettings() {
  const [open, setOpen] = useState(false);
  const current = useUserLLM();
  const { data: h } = useApi("/api/health");
  const { data: pv } = useApi("/api/copilot/providers");
  const providers = pv?.providers ?? [];
  const [provider, setProvider] = useState("anthropic");
  const [input, setInput] = useState("");
  const [remember, setRemember] = useState(false);
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("");
  const [state, setState] = useState({ busy: false, result: null, error: null, saved: false });

  useEffect(() => {
    if (!open) return undefined;
    setProvider(current?.provider ?? "anthropic"); setInput(""); setModels([]); setModel(current?.model ?? "");
    setRemember(userLLM.remembered()); setState({ busy: false, result: null, error: null, saved: false });
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const label = providerLabel(providers, provider);
  const hint = providers.find((p) => p.id === provider)?.key_hint ?? "";

  const check = async (e) => {
    e.preventDefault();
    const key = input.trim();
    if (!(provider === "anthropic" ? ANTHROPIC_RE : GENERIC_RE).test(key)) {
      setState({ busy: false, result: null, error: `That does not look like a ${label} API key.`, saved: false });
      return;
    }
    setState({ busy: true, result: null, error: null, saved: false });
    try {
      const r = await checkKey(provider, key);
      setModels(r.valid ? r.models : []);
      setModel(r.valid ? (r.model || r.models[0] || "") : "");
      setState({ busy: false, result: r, error: null, saved: false });
    } catch (err) {
      setState({ busy: false, result: null, error: err.message, saved: false });
    }
  };
  const save = () => {
    userLLM.set({ provider, key: input.trim(), model: model || null }, remember);
    setInput(""); setModels([]);
    setState((s) => ({ ...s, saved: true }));
  };

  return (
    <>
      <button className="btn" onClick={() => setOpen(true)} aria-haspopup="dialog">
        <KeyRound /> AI settings{current ? <span className="tag green">your key</span> : null}
      </button>
      {open && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="AI settings" onClick={() => setOpen(false)}>
          <aside className="modal" onClick={(e) => e.stopPropagation()}>
            <header className="modal-head">
              <div><span className="eyebrow">Copilot</span><h3>AI settings</h3></div>
              <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close"><X size={18} /></button>
            </header>
            <div className="modal-body key-settings">
              <p className="muted">Use a language model from any supported provider to write Copilot answers. Whatever the model, every answer is checked by the FIREWISE validator (citations must resolve; numbers must appear in the cited evidence). Without a key, answers are built deterministically from the database.</p>
              <dl className="key-status">
                <dt>In use</dt>
                <dd>{current ? <><b>{providerLabel(providers, current.provider)}</b>{current.model ? <> · <span className="mono">{current.model}</span></> : null} · your key <span className="mono">{userLLM.masked(current.key)}</span> · {userLLM.remembered() ? "remembered on this device" : "this browser session only"}</>
                  : h?.copilot_configured ? <>server key · <span className="mono">{h.copilot_model}</span></> : "no key (deterministic answers)"}</dd>
              </dl>

              <form onSubmit={check} className="key-form">
                <label htmlFor="ai-provider">AI provider</label>
                <select id="ai-provider" value={provider} onChange={(e) => { setProvider(e.target.value); setModels([]); setModel(""); setState({ busy: false, result: null, error: null, saved: false }); }}>
                  {providers.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                </select>
                <label htmlFor="ak">{label} API key</label>
                <input id="ak" type="password" autoComplete="off" spellCheck={false} placeholder={hint} value={input}
                  onChange={(e) => { setInput(e.target.value); setModels([]); setState({ busy: false, result: null, error: null, saved: false }); }} />
                <label className="check"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember on this device</label>
                <div className="btn-row">
                  <button className="btn" type="submit" disabled={state.busy || !input.trim()}>{state.busy ? "Checking…" : "Check key"}</button>
                  {current && <button className="btn danger" type="button" onClick={() => { userLLM.clear(); setState({ busy: false, result: null, error: null, saved: false }); }}>Remove my key</button>}
                </div>
                {state.result?.valid && (
                  <>
                    <label htmlFor="ai-model">Model ({models.length} available to this key)</label>
                    <select id="ai-model" value={model} onChange={(e) => setModel(e.target.value)}>
                      {models.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                    <div className="btn-row"><button className="btn primary" type="button" disabled={!model} onClick={save}>Save and use</button></div>
                  </>
                )}
              </form>
              {state.result && !state.saved && (
                <p className={`key-result ${state.result.valid ? "ok" : "bad"}`} role="status">
                  {state.result.valid ? <Check size={15} /> : <AlertTriangle size={15} />} {state.result.message}{state.result.valid ? " Choose a model, then save. Model listing does not confirm generation or billing access." : " Not saved."}
                </p>
              )}
              {state.saved && <p className="key-result ok" role="status"><Check size={15} /> Saved. The Copilot now uses {label}{model ? ` · ${model}` : ""}.</p>}
              {state.error && <p className="key-result bad" role="alert"><AlertTriangle size={15} /> {state.error}</p>}

              <h4>Where your key goes</h4>
              <ul className="limits small">
                <li>It is stored only in this browser: for this session, or on this device if you tick “remember”.</li>
                <li>It is sent over HTTPS to this FIREWISE server with Copilot questions only, in a request header — never in a URL.</li>
                <li>The server calls only {label}'s official API address, uses the key for that single request, and never stores, caches or logs it.</li>
                <li>Checking a key only lists the provider's models (no answer is generated). Copilot answers are billed to your account with that provider.</li>
                <li>Anyone with access to this browser profile could read a remembered key. Remove it when you are done on a shared computer.</li>
              </ul>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
