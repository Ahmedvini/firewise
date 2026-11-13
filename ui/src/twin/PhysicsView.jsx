// Physics twin: every model result with inputs (and their provenance), outputs with units and validation,
// assumptions, warnings and limitations; validation records; models that are NOT implemented.
import { useEffect, useState } from "react";
import { TwinStatusTag, ValidationTag } from "../components/Tags.jsx";
import { useTwin } from "./TwinContext.jsx";
import { twin } from "../services/api.js";
import { ErrorPanel } from "../components/States.jsx";

const STATUS_TONE = { completed: "green", unavailable: "amber", rejected: "red" };
const n = (v) => (v == null ? "—" : Number(Number(v).toPrecision(5)));

function Result({ r, card }) {
  return (
    <div className={`panel model-card ${r.status}`}>
      <div className="card-top">
        <h3>{r.model_name} <span className="muted small">v{r.model_version}</span></h3>
        <span><span className={`tag ${STATUS_TONE[r.status]}`}>{r.status}</span><ValidationTag status={r.validation_status} /></span>
      </div>
      <p className="muted small">Scope: {r.scope}</p>
      {r.reason && <p className="note small">{r.reason}</p>}
      {r.warnings.map((w) => <p key={w} className="note small">{w}</p>)}
      <div className="grid cols-2">
        <table className="dense"><thead><tr><th>Input</th><th>Value</th><th>Status</th></tr></thead>
          <tbody>{r.inputs.map((i) => <tr key={i.name}><td className="small">{i.name.replaceAll("_", " ")}</td><td className="tnum small">{n(i.value)} {i.unit}</td><td><TwinStatusTag status={i.status} source={i.source} />{i.source && <div className="muted small">{i.source}</div>}</td></tr>)}</tbody></table>
        {r.outputs.length > 0 && (
          <table className="dense"><thead><tr><th>Output</th><th>Value</th><th>Validation</th></tr></thead>
            <tbody>{r.outputs.map((o) => <tr key={o.name}><td className="small">{o.name.replaceAll("_", " ")}</td><td className="tnum small">{n(o.value)} {o.unit}</td><td><ValidationTag status={o.validation_status} /></td></tr>)}</tbody></table>
        )}
      </div>
      <details><summary className="small">Equations, assumptions, applicability, limitations</summary>
        {card && <ul className="small mono eqs">{card.equations.map((e) => <li key={e}>{e}</li>)}</ul>}
        <p className="small"><b>Assumptions.</b> {r.assumptions.join(" ")}</p>
        {card && <p className="small"><b>Boundary conditions.</b> {card.boundary_conditions.join(" ")} <b>Applicability.</b> {card.applicability}</p>}
        <p className="small"><b>Limitations.</b> {r.limitations.join(" ")}</p>
        {card && <p className="small muted"><b>References.</b> {card.references.join("; ")}</p>}
      </details>
    </div>
  );
}

export default function PhysicsView() {
  const t = useTwin();
  const d = t.evaluation.data;
  const [cards, setCards] = useState({});
  const [val, setVal] = useState(null);
  const [runs, setRuns] = useState([]);
  const [runErr, setRunErr] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    twin.models().then((ms) => setCards(Object.fromEntries(ms.map((m) => [m.id, m])))).catch(() => {});
    twin.validation().then(setVal).catch(() => {});
  }, []);
  useEffect(() => { if (t.savedId) twin.runs(t.savedId).then(setRuns).catch(() => setRuns([])); else setRuns([]); }, [t.savedId, t.savedVersion]);
  if (!d) return <div className="panel">Computing…</div>;
  const ph = d.physics;
  const sel = t.selectedZone;
  const shown = ph.results.filter((r) => r.scope === `zone:${sel}` || r.scope === "habitat" || r.scope.startsWith("experiment") || (r.model_id === "wall_conduction"));
  const record = async () => {
    setBusy(true); setRunErr(null);
    try { await twin.simulate(t.savedId); setRuns(await twin.runs(t.savedId)); } catch (e) { setRunErr(e); } finally { setBusy(false); }
  };
  return (
    <div>
      <div className="panel">
        <p>{ph.notice}</p>
        <p className="muted small">Engine <span className="mono">{ph.engine_version}</span> · input hash <span className="mono">{ph.input_hash}</span> · showing zone {sel} (select another zone in the panel or the 3D view), the habitat and the experiment.</p>
        <div className="row-between">
          <span className="small">{t.savedId ? (t.dirty ? "Unsaved changes: save first to record a run of this exact configuration." : `Saved scenario v${t.savedVersion}.`) : "Save the scenario to record simulation runs."}</span>
          <button className="btn primary" disabled={!t.savedId || t.dirty || busy} onClick={record}>{busy ? "Running…" : "Run & record simulation"}</button>
        </div>
        {runErr && <ErrorPanel error={runErr} onRetry={record} />}
        {runs.length > 0 && (
          <table className="dense"><thead><tr><th>Run</th><th>Status</th><th>Version</th><th>Models completed / unavailable / rejected</th><th>Input hash</th><th>Completed</th></tr></thead>
            <tbody>{runs.map((r) => <tr key={r.run_id}><td className="mono small">{r.run_id}</td><td><span className={`tag ${r.status === "completed" ? "green" : "red"}`}>{r.status}</span></td><td>v{r.scenario_version}</td>
              <td className="small">{r.summary.completed} / {r.summary.unavailable} / {r.summary.rejected}</td><td className="mono small">{r.input_hash}</td><td className="small">{r.completed_at?.replace("T", " ").slice(0, 19)}</td></tr>)}</tbody></table>
        )}
      </div>
      <div className="grid section-gap">{shown.map((r) => <Result key={`${r.model_id}-${r.scope}`} r={r} card={cards[r.model_id]} />)}</div>

      <div className="panel section-gap">
        <h3>Model validation records</h3>
        <p className="muted small">{val?.nasa_psi_validation} Calibration set: none — no parameter is fitted. “Verified” = implementation reproduces reference values that rest on the same equation; “validated” = compared with independent reference data within its stated uncertainty.</p>
        {val && (
          <div className="table-wrap"><table className="dense">
            <thead><tr><th>Model / output</th><th>Kind</th><th>Status</th><th>Reference</th><th>Domain</th><th>n</th><th>MAE</th><th>RMSE</th><th>Bias</th><th>Max |rel. error|</th></tr></thead>
            <tbody>{val.records.filter((r) => r.status !== "not_implemented").map((r, i) => (
              <tr key={i}><td className="small"><b>{r.model_id}</b><div className="muted">{r.output}</div></td><td className="small">{r.kind}</td><td><ValidationTag status={r.status} /></td>
                <td className="small" title={r.independence || ""}>{r.reference || "—"}<div className="muted">{r.uncertainty || ""}</div></td><td className="small">{r.domain}</td>
                {r.metrics ? <><td className="tnum small">{r.metrics.n}</td><td className="tnum small">{n(r.metrics.mae)} {r.unit}</td><td className="tnum small">{n(r.metrics.rmse)}</td><td className="tnum small">{n(r.metrics.bias)}</td><td className="tnum small">{r.metrics.max_abs_rel_error_pct.toFixed(3)}%</td></>
                  : <td colSpan={5} className="muted small">{r.conclusion}</td>}
              </tr>))}</tbody>
          </table></div>
        )}
      </div>

      <div className="panel section-gap">
        <h3>Not implemented — no output is produced</h3>
        <ul className="plain">{ph.planned_models.map((m) => <li key={m.id}><b>{m.name}</b> <ValidationTag status="not_implemented" /><div className="muted small">{m.validation_summary}</div></li>)}</ul>
      </div>
    </div>
  );
}
