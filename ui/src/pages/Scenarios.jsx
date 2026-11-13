import { useEffect, useState } from "react";
import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import StatCard from "../components/StatCard.jsx";
import { Loading, ErrorPanel } from "../components/States.jsx";
import { StatusTag } from "../components/Tags.jsx";
import { EvidenceLink } from "../components/Evidence.jsx";
import { useApi, scenarioCustom } from "../services/api.js";
import { FUEL_LABEL } from "../data/constants.js";
import { O2PressureChart } from "./Overview.jsx";

const GRAVITY = [
  ["microgravity", "Microgravity (spacecraft)"],
  ["partial_gravity_lunar", "Lunar gravity (0.16 g)"],
  ["partial_gravity_mars", "Mars gravity (0.38 g)"],
  ["any", "Not constrained"],
];
const FOCUS = [["any", "Any material"], ["solid", "Solid materials"], ["gaseous", "Gaseous flames"], ["liquid_droplet", "Liquid droplets"]];

function Counts({ c }) {
  return (
    <span className="counts">
      <strong className="tnum">{c.n.toLocaleString()}</strong>
      {c.n > 0 && (
        <span className="tags">
          {Object.entries(c.o2_status).map(([s, n]) => <span key={`o${s}`} className="small muted">O₂ <StatusTag status={s} label={`${n}`} /></span>)}
          {Object.entries(c.p_status).map(([s, n]) => <span key={`p${s}`} className="small muted">P <StatusTag status={s} label={`${n}`} /></span>)}
        </span>
      )}
    </span>
  );
}

export default function Scenarios({ onOpenExperiment }) {
  const { data: presets, error: pErr, loading: pLoading, reload: pReload } = useApi("/api/scenarios");
  const [sid, setSid] = useState("exploration_envelope");
  const [custom, setCustom] = useState(null);
  const [form, setForm] = useState({ o2_min_pct: 30, o2_max_pct: 36, p_min_psia: 8.2, p_max_psia: 10.2, gravity: "partial_gravity_lunar", fuel_focus: "any" });
  const [customState, setCustomState] = useState({ loading: false, error: null });
  const preset = useApi(sid !== "custom" ? `/api/scenarios/${sid}/evidence` : null);
  const ev = sid === "custom" ? custom : preset.data;

  useEffect(() => {
    if (sid !== "custom" && presets) {
      const p = presets.find((x) => x.id === sid);
      if (p) setForm({ ...p.window });
    }
  }, [sid, presets]);

  const runCustom = async (e) => {
    e?.preventDefault();
    const w = { ...form, o2_min_pct: +form.o2_min_pct, o2_max_pct: +form.o2_max_pct, p_min_psia: +form.p_min_psia, p_max_psia: +form.p_max_psia };
    if (w.o2_min_pct > w.o2_max_pct || w.p_min_psia > w.p_max_psia) {
      setCustomState({ loading: false, error: { message: "Each minimum must be less than or equal to its maximum." } });
      return;
    }
    setSid("custom");
    setCustomState({ loading: true, error: null });
    try {
      setCustom(await scenarioCustom(w));
      setCustomState({ loading: false, error: null });
    } catch (err) {
      setCustomState({ loading: false, error: err });
    }
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const loading = sid === "custom" ? customState.loading : preset.loading;
  const error = sid === "custom" ? customState.error : preset.error;
  const maxIn = ev ? Math.max(1, ...ev.items.map((i) => i.in_window.n + i.near_window.n)) : 1;

  return (
    <>
      <SampleBanner />
      <Header eyebrow="Scenario Explorer" title="Which NASA tests document a habitat atmosphere?"
        description="Pick a habitat atmosphere. Investigations are ranked by how many tests document chamber O₂ and pressure inside the window — then within tolerance — then by material. No weighted score, no fire-risk prediction; missing pressure never counts as a match." />

      {pLoading && <Loading rows={2} />}
      {pErr && <ErrorPanel error={pErr} onRetry={pReload} />}
      <div className="chips">
        {presets?.map((p) => <button key={p.id} className={sid === p.id ? "on" : ""} onClick={() => setSid(p.id)}>{p.label}</button>)}
        <button className={sid === "custom" ? "on" : ""} onClick={() => runCustom()}>Custom window</button>
      </div>

      <form className="panel scenario-form" onSubmit={runCustom}>
        <label>Chamber O₂ min (%)<input type="number" step="0.1" min="0" max="100" value={form.o2_min_pct} onChange={set("o2_min_pct")} /></label>
        <label>O₂ max (%)<input type="number" step="0.1" min="0" max="100" value={form.o2_max_pct} onChange={set("o2_max_pct")} /></label>
        <label>Pressure min (psia)<input type="number" step="0.1" min="0" max="100" value={form.p_min_psia} onChange={set("p_min_psia")} /></label>
        <label>Pressure max (psia)<input type="number" step="0.1" min="0" max="100" value={form.p_max_psia} onChange={set("p_max_psia")} /></label>
        <label>Gravity<select value={form.gravity} onChange={set("gravity")}>{GRAVITY.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label>Material focus<select value={form.fuel_focus} onChange={set("fuel_focus")}>{FOCUS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <button className="btn primary" type="submit">Find evidence</button>
      </form>

      {loading && <Loading rows={6} />}
      {error && <ErrorPanel error={error} onRetry={sid === "custom" ? runCustom : preset.reload} />}
      {ev && !loading && (
        <>
          {ev.gravity_evidence.matching_records === 0 && ev.gravity_evidence.requested !== "any" ? (
            <SampleBanner danger>{ev.gravity_evidence.statement}</SampleBanner>
          ) : (
            <SampleBanner>{ev.gravity_evidence.statement}</SampleBanner>
          )}
          <div className="grid cols-4 section-gap">
            <StatCard value={ev.totals.in_window} label="Tests documenting chamber O₂ and pressure inside the window" highlight={ev.totals.in_window === 0}
              evidence={sid !== "custom" ? `agg:scenario:${sid}` : undefined} />
            <StatCard value={ev.totals.near_window} label={`Tests within tolerance (${ev.near_window_tolerance})`} />
            <StatCard value={ev.gravity_evidence.matching_records} label="Records at the requested gravity" />
            <StatCard value={ev.totals.records_considered} label="Records considered (duplicates excluded)" />
          </div>
          <p className="muted small">{ev.scenario.description} · {ev.ranking_method} <span className="tag amber">{ev.label}</span></p>

          <div className="panel table-wrap section-gap">
            <table>
              <thead><tr><th>#</th><th>Investigation</th><th>In window</th><th>Near window</th><th>Not documented</th><th>Material</th><th>Gravity</th></tr></thead>
              <tbody>
                {ev.items.map((it, i) => (
                  <tr key={it.investigation_id} className={it.in_window.n + it.near_window.n === 0 ? "dim" : ""}>
                    <td className="tnum muted">{i + 1}</td>
                    <td>
                      <button className="linkish" onClick={() => onOpenExperiment(it.investigation_id)}>{it.acronym || it.investigation_id}</button>
                      <div className="mono muted small">{it.investigation_id}</div>
                      <div className="bar-track" aria-hidden>
                        <span className="bar-in" style={{ width: `${(100 * it.in_window.n) / maxIn}%` }} />
                        <span className="bar-near" style={{ width: `${(100 * it.near_window.n) / maxIn}%` }} />
                      </div>
                    </td>
                    <td><Counts c={it.in_window} /></td>
                    <td><Counts c={it.near_window} /></td>
                    <td className="small muted">{it.undocumented.o2_not_documented_as_ambient ?? 0} without chamber O₂<br />{it.undocumented.pressure_not_documented ?? 0} without pressure</td>
                    <td className="small">{it.material_class.map((c) => FUEL_LABEL[c] ?? c).join(", ")}{it.material_match ? "" : <div className="muted">not the focus material</div>}</td>
                    <td className="small muted" title={it.gravity_match}>{it.gravity_match.startsWith("none") ? "None — microgravity data only" : it.gravity_match}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="legend-row small muted"><span className="sw bar-in" /> in window <span className="sw bar-near" /> within tolerance · out of {ev.totals.records_considered.toLocaleString()} records</div>
          </div>
          {sid !== "custom" && <EvidenceLink id={`agg:scenario:${sid}`} label="How this count is computed" />}
          <div className="section-gap" style={{ marginTop: 16 }}><O2PressureChart height={360} highlight={sid === "exploration_envelope" ? "exploration" : undefined} /></div>
        </>
      )}
    </>
  );
}
