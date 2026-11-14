import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { FileText, X, ExternalLink } from "lucide-react";
import { apiGet } from "../services/api.js";
import { evidenceKind } from "../utils/format.js";

const EvidenceContext = createContext({ open: () => {} });

// Per-answer evidence (twin calculations and external search sources) has no server endpoint; register it here.
const inline = new Map();
export function registerInlineEvidence(items = []) {
  items.forEach((i) => inline.set(i.evidence_id, i));
}
export const useEvidence = () => useContext(EvidenceContext);

/** Provides a single modal that resolves any evidence id (row:, inv:, fact:, agg:, pdf:, obs:, group:). */
export function EvidenceProvider({ children }) {
  const [id, setId] = useState(null);
  const [state, setState] = useState({ data: null, error: null });
  const open = useCallback((evidenceId) => setId(evidenceId), []);

  useEffect(() => {
    if (!id) return;
    if (inline.has(id)) {
      const i = inline.get(id);
      setState({ data: { evidence_id: id, kind: i.kind, title: i.title, text: i.snippet, url: i.url }, error: null });
      return;
    }
    setState({ data: null, error: null });
    apiGet(`/api/evidence/${encodeURIComponent(id)}`)
      .then((data) => setState({ data, error: null }))
      .catch((e) => setState({ data: null, error: e.status === 404 ? "This item was computed for a single answer and is shown in the answer's evidence list." : e.message }));
  }, [id]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && setId(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const ev = state.data;
  let raw = null;
  if (ev?.kind === "psi_table_row") {
    try { raw = JSON.parse(ev.text); } catch { raw = null; }
  }
  const prov = ev?.data?.provenance;

  return (
    <EvidenceContext.Provider value={{ open }}>
      {children}
      {id && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="Source evidence" onClick={() => setId(null)}>
          <aside className="modal" onClick={(e) => e.stopPropagation()}>
            <header className="modal-head">
              <div>
                <span className="eyebrow">{ev ? evidenceKind(ev.kind) : "Source evidence"}</span>
                <h3>{ev?.title ?? id}</h3>
                <code className="mono muted">{id}</code>
              </div>
              <button className="icon-btn" onClick={() => setId(null)} aria-label="Close"><X size={18} /></button>
            </header>
            <div className="modal-body">
              {state.error && <p className="muted">{state.error}</p>}
              {!ev && !state.error && <p className="muted">Loading source…</p>}
              {ev?.data?.dataset_doi_url && (
                <p className="small">Dataset DOI: <a href={ev.data.dataset_doi_url} target="_blank" rel="noreferrer" className="mono">doi:{ev.data.dataset_doi}</a></p>
              )}
              {raw && (
                <>
                  <p className="muted small">Verbatim record from the NASA PSI experimental table. Blank cells are shown as “—”.</p>
                  <table className="kv">
                    <tbody>
                      {Object.entries(raw).map(([k, v]) => (
                        <tr key={k}><th>{k || "(unnamed column)"}</th><td className={String(v).trim() ? "mono" : "mono muted"}>{String(v).trim() || "—"}</td></tr>
                      ))}
                    </tbody>
                  </table>
                  {prov && (
                    <p className="muted small" style={{ marginTop: 12 }}>
                      File <span className="mono">{prov.source_file}</span>, row {prov.source_row} · SHA-256 <span className="mono">{String(prov.source_sha256).slice(0, 16)}…</span>
                    </p>
                  )}
                </>
              )}
              {ev && !raw && <p className="prewrap">{ev.text}</p>}
              {ev?.url && <a className="ext-link" href={ev.url} target="_blank" rel="noreferrer">Open original source <ExternalLink size={14} /></a>}
            </div>
          </aside>
        </div>
      )}
    </EvidenceContext.Provider>
  );
}

/** Small button that opens one evidence item. */
export function EvidenceLink({ id, label }) {
  const { open } = useEvidence();
  return (
    <button type="button" className="ev-link" onClick={() => open(id)} title={`Open source: ${id}`}>
      <FileText size={12} /> <span>{label ?? id}</span>
    </button>
  );
}
