// Scientific scenario report (deterministic, server-generated). Rendered from Markdown; downloadable.
import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { useTwin } from "./TwinContext.jsx";
import { twin } from "../services/api.js";
import { ErrorPanel, Loading } from "../components/States.jsx";

// Minimal, safe Markdown renderer for the report's own constructs (headings, tables, lists, quotes, code, bold).
function inline(text) {
  const parts = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m, k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(m[0].startsWith("**") ? <b key={k++}>{m[0].slice(2, -2)}</b> : <code key={k++} className="mono">{m[0].slice(1, -1)}</code>);
    last = m.index + m[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

export function Markdown({ md }) {
  const lines = md.split("\n");
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (l.startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].startsWith("|")) rows.push(lines[i++]);
      i--;
      const cells = (r) => r.slice(1, -1).split("|").map((c) => c.trim());
      out.push(<div className="table-wrap" key={i}><table className="dense"><thead><tr>{cells(rows[0]).map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead>
        <tbody>{rows.slice(2).map((r, ri) => <tr key={ri}>{cells(r).map((c, j) => <td key={j} className="small">{inline(c)}</td>)}</tr>)}</tbody></table></div>);
    } else if (l.startsWith("### ")) out.push(<h4 key={i}>{inline(l.slice(4))}</h4>);
    else if (l.startsWith("## ")) out.push(<h3 key={i} className="section-title">{inline(l.slice(3))}</h3>);
    else if (l.startsWith("# ")) out.push(<h2 key={i}>{inline(l.slice(2))}</h2>);
    else if (l.startsWith("> ")) out.push(<p key={i} className="note">{inline(l.slice(2))}</p>);
    else if (/^\s*- /.test(l)) {
      const items = [];
      while (i < lines.length && /^\s*- /.test(lines[i])) items.push(lines[i++].replace(/^\s*- /, ""));
      i--;
      out.push(<ul key={i} className="limits">{items.map((x, j) => <li key={j}>{inline(x)}</li>)}</ul>);
    } else if (l.trim()) out.push(<p key={i}>{inline(l)}</p>);
  }
  return <div className="report-md">{out}</div>;
}

export default function ReportView() {
  const t = useTwin();
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const useSaved = t.savedId && !t.dirty;
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true }));
    const p = useSaved ? twin.report(t.savedId) : twin.reportUnsaved(t.scenario);
    p.then((data) => live && setState({ data, error: null, loading: false })).catch((error) => live && setState({ data: null, error, loading: false }));
    return () => { live = false; };
  }, [useSaved, t.savedId, t.savedVersion, t.scenario]);
  const download = (ext) => {
    const d = state.data;
    const blob = ext === "md" ? new Blob([d.markdown], { type: "text/markdown" }) : new Blob([JSON.stringify(d, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `firewise-twin-report-${(t.scenario.name || "scenario").replace(/[^A-Za-z0-9_-]+/g, "-").slice(0, 40)}.${ext}`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  if (state.loading && !state.data) return <Loading rows={8} />;
  if (state.error) return <ErrorPanel error={state.error} />;
  return (
    <div className="panel report">
      <div className="row-between">
        <span className="muted small">{useSaved ? `Report for saved scenario ${t.savedId} v${t.savedVersion}` : "Report for the current unsaved configuration"} · input hash <span className="mono">{state.data.input_hash}</span></span>
        <span className="btn-row">
          <button className="btn" onClick={() => download("md")}><Download size={14} /> Markdown</button>
          <button className="btn" onClick={() => download("json")}><Download size={14} /> JSON</button>
        </span>
      </div>
      <Markdown md={state.data.markdown} />
    </div>
  );
}
