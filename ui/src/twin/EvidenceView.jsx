// Evidence twin: exact matches, transparent nearest-record ranking and coverage, all from the database.
import SampleBanner from "../components/SampleBanner.jsx";
import { EvidenceLink } from "../components/Evidence.jsx";
import { useTwin } from "./TwinContext.jsx";
import { FUEL_LABEL } from "../data/constants.js";

const VAR_LABEL = { o2_pct: "O₂", pressure_kPa: "Pressure", airflow_m_s: "Airflow", temperature_K: "Temperature" };
const fmt = (v, nd = 4) => (v == null ? "—" : Number(v.toPrecision(nd)));

function Cell({ v, unit }) {
  if (v.value == null) return <span className="missing" title={v.note || "not documented"}>not documented{v.note ? "*" : ""}</span>;
  return <span>{fmt(v.value)} {unit} <span className="muted small">({v.status_label})</span></span>;
}

function RecordTable({ items, onImport, exact }) {
  if (!items.length) return <p className="muted">{exact ? "No NASA record matches every enabled variable at this gravity." : "No record documents any enabled variable."}</p>;
  return (
    <div className="table-wrap">
      <table className="dense">
        <thead><tr><th>#</th><th>NASA record</th><th>Material</th><th>O₂</th><th>Pressure</th><th>Airflow</th><th>Distance (per variable)</th><th>Source</th><th /></tr></thead>
        <tbody>
          {items.map((n, i) => (
            <tr key={n.row_key} className={n.gravity_matches ? "" : "dim"}>
              <td className="tnum muted">{i + 1}</td>
              <td><b>{n.acronym || n.investigation_id}</b> <span className="mono small">{n.test_label || "—"}</span><div className="muted small">{n.investigation_id} · {n.gravity_regime}</div></td>
              <td className="small">{FUEL_LABEL[n.fuel_class] ?? n.fuel_class}<div className="muted">{n.fuel_or_material || "—"}</div></td>
              <td><Cell v={n.values.o2_pct} unit="%" /></td>
              <td><Cell v={n.values.pressure_kPa} unit="kPa" /></td>
              <td><Cell v={n.values.airflow_m_s} unit="m/s" /></td>
              <td className="small"><b className="tnum">{n.distance.toFixed(3)}</b> over {n.variables_compared.length}/{n.variables_enabled.length}
                <div className="muted">{Object.entries(n.components).map(([k, c]) => `${VAR_LABEL[k]} ${c.toFixed(2)}`).join(" · ")}</div>
                {n.missing_variables.length > 0 && <div className="missing">not compared: {n.missing_variables.map((k) => VAR_LABEL[k]).join(", ")}</div>}</td>
              <td><EvidenceLink id={n.evidence_id} label={`row ${n.source.source_row}`} /></td>
              <td><button className="btn small-btn" onClick={() => onImport(n)} title="Copy this record's documented O₂, pressure and airflow into the scenario with NASA status and source">Use conditions</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function EvidenceView() {
  const t = useTwin();
  const d = t.evaluation.data;
  if (!d) return <div className="panel">Computing…</div>;
  const ev = d.evidence;
  const cov = ev.coverage;
  const tg = ev.targets;
  return (
    <div>
      <SampleBanner danger={cov.gravity.requested_regime !== "microgravity"}>{cov.gravity.statement}</SampleBanner>
      <div className="grid cols-4">
        <div className="panel stat-tile"><span className="eyebrow">Exact matches</span><strong>{cov.exact_matches}</strong><span className="muted small">{ev.variables_enabled.map((v) => VAR_LABEL[v]).join(" + ")} within tolerance, same gravity</span></div>
        <div className="panel stat-tile"><span className="eyebrow">Records considered</span><strong>{cov.records_considered.toLocaleString()}</strong><span className="muted small">non-duplicate combustion/aerosol records</span></div>
        <div className="panel stat-tile"><span className="eyebrow">At requested gravity</span><strong>{cov.gravity.records_at_requested}</strong><span className="muted small">{tg.gravity} → {cov.gravity.requested_regime}</span></div>
        <div className="panel stat-tile"><span className="eyebrow">Investigations matched</span><strong>{cov.investigations.length}</strong><span className="muted small">{cov.investigations.map((i) => `${i.acronym || i.investigation_id} (${i.records})`).join(", ") || "none"}</span></div>
      </div>
      <p className="muted small section-gap">Targets (experiment zone {tg.zone_id}): O₂ {tg.o2_pct}% ±{ev.tolerances.o2_pct} · pressure {tg.pressure_kPa} kPa ±{ev.tolerances.pressure_kPa}
        {ev.variables_enabled.includes("airflow_m_s") && ` · airflow ${tg.airflow_m_s ?? "not set"} m/s ±${ev.tolerances.airflow_m_s}`}
        {ev.use_material && ` · material ${tg.fuel_class ?? "any"}${tg.material ? ` “${tg.material}”` : ""}`}. {ev.method} <span className="tag amber">{ev.label}</span></p>

      <div className="panel section-gap"><h3>Exact matches ({ev.exact.length})</h3><RecordTable items={ev.exact} onImport={t.importRecord} exact /></div>
      <div className="panel section-gap"><h3>Nearest documented records</h3>
        <p className="muted small">Distance 1.0 = one tolerance away on one variable. Rows in grey are at a different gravity level. * = value present in the record but not a chamber value (e.g. burner-stream O₂) or not documented.</p>
        <RecordTable items={ev.nearest} onImport={t.importRecord} /></div>

      <div className="grid cols-3 section-gap">
        <div className="panel"><h3>Missing measurements</h3>
          <ul className="plain">{cov.missing_measurements.map((m) => (
            <li key={m.variable}><b>{m.label}</b>: documented by {m.records_documenting.toLocaleString()} of {cov.records_considered.toLocaleString()} records
              {!m.enabled && <span className="muted small"> (not compared)</span>}{m.note && <div className="muted small">{m.note}</div>}</li>))}</ul></div>
        <div className="panel"><h3>Available measurements ({cov.basis})</h3>
          {cov.available_measurements.length ? <ul className="plain">{cov.available_measurements.slice(0, 10).map((m) => (
            <li key={m.variable}><span className="mono small">{m.variable}</span> — {m.records} records {m.unit ? `(${m.unit})` : ""}<div className="muted small">{Object.entries(m.statuses).map(([k, v]) => `${k} ${v}`).join(", ")}</div></li>))}</ul>
            : <p className="muted">No observation columns for these records.</p>}</div>
        <div className="panel"><h3>Materials and outcomes</h3>
          <p className="small">{Object.entries(cov.materials.fuel_classes).map(([k, v]) => `${FUEL_LABEL[k] ?? k}: ${v}`).join(" · ") || "—"}</p>
          <ul className="plain">{cov.outcomes.slice(0, 5).map((o) => <li key={o.evidence_id} className="small"><EvidenceLink id={o.evidence_id} label={`${o.investigation_id} ${o.test_label || ""}`} /> {o.outcome_text}</li>)}</ul>
          <h4>Sources</h4>
          <ul className="plain">{cov.sources.map((s) => <li key={s.file_name} className="small mono">{s.investigation_id} · {s.file_name}</li>)}</ul></div>
      </div>
    </div>
  );
}
