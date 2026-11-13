// Scenario management: save, load, duplicate, delete, compare (2–4), version history.
import { useCallback, useEffect, useState } from "react";
import { useTwin } from "./TwinContext.jsx";
import { twin } from "../services/api.js";
import { ErrorPanel } from "../components/States.jsx";
import { TwinStatusTag } from "../components/Tags.jsx";

const fmt = (v) => (v == null ? "—" : typeof v === "number" ? Number(v.toPrecision(5)) : String(v));

export default function ScenariosView() {
  const t = useTwin();
  const [list, setList] = useState(null);
  const [picked, setPicked] = useState([]);
  const [cmp, setCmp] = useState(null);
  const [hist, setHist] = useState([]);
  const [err, setErr] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const refresh = useCallback(() => twin.list().then(setList).catch((e) => { setErr(e); setList([]); }), []);
  useEffect(() => { refresh(); }, [refresh, t.savedId, t.savedVersion]);
  useEffect(() => { if (t.savedId) twin.history(t.savedId).then(setHist).catch(() => setHist([])); else setHist([]); }, [t.savedId, t.savedVersion]);
  const act = (fn) => async (...a) => { setErr(null); try { await fn(...a); await refresh(); } catch (e) { setErr(e); } };
  const save = act((asNew) => t.save(asNew));
  const dup = act(async (id) => { const d = await twin.duplicate(id); await t.load(d.id); });
  const del = act(async (id) => { setConfirm(null); await twin.remove(id); setPicked((p) => p.filter((x) => x !== id)); if (id === t.savedId) t.detach(); });
  const compare = act(async () => setCmp(await twin.compare(picked)));
  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length >= 4 ? p : [...p, id]));
  return (
    <div>
      <div className="panel">
        <div className="row-between">
          <div>
            <h3>{t.scenario.name}</h3>
            <span className="muted small">{t.savedId ? `Saved as ${t.savedId}, version ${t.savedVersion}${t.dirty ? " · unsaved changes" : ""}` : "Not saved yet"}</span>
          </div>
          <div className="btn-row">
            <button className="btn primary" disabled={t.saving || (t.savedId && !t.dirty)} onClick={() => save(false)}>{t.savedId ? "Save new version" : "Save scenario"}</button>
            <button className="btn" disabled={t.saving} onClick={() => save(true)}>Save as new scenario</button>
            <button className="btn" onClick={t.newScenario}>New scenario</button>
          </div>
        </div>
        {err && <ErrorPanel error={err} onRetry={refresh} />}
      </div>

      <div className="panel section-gap table-wrap">
        <div className="row-between"><h3>Saved scenarios</h3>
          <button className="btn" disabled={picked.length < 2} onClick={compare}>Compare selected ({picked.length}/4)</button></div>
        {list === null && <p className="muted">Loading…</p>}
        {list?.length === 0 && <p className="muted">No saved scenarios in this workspace yet.</p>}
        {list?.length > 0 && (
          <table className="dense">
            <thead><tr><th>Compare</th><th>Name</th><th>O₂</th><th>Pressure</th><th>Gravity</th><th>Version</th><th>Updated</th><th>Actions</th></tr></thead>
            <tbody>{list.map((s) => (
              <tr key={s.id} className={s.id === t.savedId ? "current" : ""}>
                <td><input type="checkbox" aria-label={`Select ${s.name} for comparison`} checked={picked.includes(s.id)} onChange={() => toggle(s.id)} style={{ width: "auto" }} /></td>
                <td><b>{s.name}</b><div className="mono muted small">{s.id}</div></td>
                <td className="tnum">{fmt(s.o2_pct)}%</td><td className="tnum">{fmt(s.pressure_kPa)} kPa</td><td>{s.gravity}</td><td>v{s.version}</td>
                <td className="small">{s.updated_at.replace("T", " ").slice(0, 16)}</td>
                <td className="btn-row">
                  <button className="btn small-btn" onClick={act(() => t.load(s.id))}>Load</button>
                  <button className="btn small-btn" onClick={() => dup(s.id)}>Duplicate</button>
                  {confirm === s.id
                    ? <><button className="btn small-btn danger" onClick={() => del(s.id)}>Confirm delete</button><button className="btn small-btn" onClick={() => setConfirm(null)}>Keep</button></>
                    : <button className="btn small-btn" onClick={() => setConfirm(s.id)}>Delete</button>}
                </td>
              </tr>))}</tbody>
          </table>
        )}
      </div>

      {cmp && (
        <div className="panel section-gap table-wrap">
          <h3>Scenario comparison</h3>
          <p className="muted small">{cmp.note} Rows that differ are highlighted.</p>
          <table className="dense">
            <thead><tr><th>Group</th><th>Quantity</th>{cmp.scenarios.map((s) => <th key={s.id}>{s.name}<div className="muted small">v{s.version}</div></th>)}<th>Unit</th></tr></thead>
            <tbody>{cmp.rows.map((r) => (
              <tr key={r.label} className={r.differs ? "differs" : ""}>
                <td className="small muted">{r.group}</td><td>{r.label}</td>
                {r.values.map((v, i) => <td key={i} className="tnum">{v == null ? <span className="missing">not documented</span> : fmt(v)}{r.statuses[i] && r.group !== "evidence" && <div><TwinStatusTag status={r.statuses[i]} /></div>}</td>)}
                <td className="small">{r.unit || ""}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}

      {hist.length > 0 && (
        <div className="panel section-gap table-wrap">
          <h3>Version history — {t.scenario.name}</h3>
          <table className="dense"><thead><tr><th>Version</th><th>Saved</th><th>Note</th><th>O₂</th><th>Pressure</th><th>Temperature</th><th>Ventilation</th><th /></tr></thead>
            <tbody>{hist.slice().reverse().map((h) => (
              <tr key={h.version}><td>v{h.version}</td><td className="small">{h.created_at.replace("T", " ").slice(0, 16)}</td><td className="small">{h.note}</td>
                <td className="tnum">{fmt(h.o2_pct)}%</td><td className="tnum">{fmt(h.pressure_kPa)} kPa</td><td className="tnum">{h.temperature_K == null ? "—" : `${(h.temperature_K - 273.15).toFixed(1)} °C`}</td>
                <td className="tnum">{fmt(h.ventilation_m3_h)} m³/h</td>
                <td><button className="btn small-btn" onClick={() => t.loadVersion(h.scenario, h.version)}>Restore</button></td></tr>))}</tbody></table>
        </div>
      )}
    </div>
  );
}
