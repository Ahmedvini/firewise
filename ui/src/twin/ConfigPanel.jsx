// Environmental configuration. Every input edits the shared twin state; every value shows its status.
import { useEffect, useState } from "react";
import { useTwin, val, RANGES } from "./TwinContext.jsx";
import { TwinStatusTag } from "../components/Tags.jsx";
import { Disclosure } from "../components/ui.jsx";

const C2K = 273.15;
const FUEL = [["", "Not set"], ["solid", "Solid material"], ["gaseous", "Gaseous flame"], ["liquid_droplet", "Liquid droplet"],
  ["smoke_source_nonflaming", "Smoke source (non-flaming)"], ["solid_emulating_gas_burner", "Solid-emulating gas burner"]];
const GRAVITY = [["microgravity", "Microgravity (spacecraft)"], ["lunar", "Lunar (0.16 g)"], ["mars", "Mars (0.38 g)"], ["earth", "Earth (1 g)"]];

/** Numeric input bound to a TwinValue. Out-of-range input is shown and NOT committed. `toUi`/`fromUi` convert display units. */
export function NumField({ id, label, unit, tv, range, onCommit, step = "any", toUi = (x) => x, fromUi = (x) => x, optional = false, hint, readout }) {
  const shown = val(tv) == null ? "" : String(Number(toUi(val(tv)).toFixed(4)));
  const [text, setText] = useState(shown);
  const [err, setErr] = useState(null);
  useEffect(() => { setText(shown); setErr(null); }, [shown]);
  const commit = (raw) => {
    if (raw.trim() === "") {
      if (optional) { setErr(null); onCommit(null); } else setErr("A value is required.");
      return;
    }
    const v = fromUi(Number(raw));
    if (!Number.isFinite(v)) { setErr("Not a number."); return; }
    if (range && (v < range[0] || v > range[1])) {
      setErr(`Allowed ${toUi(range[0]).toFixed(range[0] < 1 ? 3 : 1)}–${toUi(range[1]).toFixed(1)} ${unit}.`);
      return;
    }
    setErr(null);
    onCommit(v);
  };
  return (
    <label className="field" htmlFor={id}>
      <span className="field-head">
        <span>{label}</span>
        {(val(tv) != null || !optional) ? <TwinStatusTag status={val(tv) == null ? "not_documented" : tv.status} source={tv?.source} /> : <span className="muted small">not set</span>}
      </span>
      <span className="field-input">
        <input id={id} type="number" step={step} value={text} placeholder={optional ? "not set" : ""} aria-invalid={!!err}
          onChange={(e) => { setText(e.target.value); if (e.target.value !== "" && Number.isFinite(Number(e.target.value))) commit(e.target.value); }}
          onBlur={(e) => commit(e.target.value)} />
        <span className="unit">{unit}</span>
      </span>
      {readout && <span className="muted small">{readout}</span>}
      {hint && !err && <span className="muted small">{hint}</span>}
      {err && <span className="field-err" role="alert">{err}</span>}
    </label>
  );
}

export default function ConfigPanel({ zoneOpen = false }) {
  const t = useTwin();
  const sc = t.scenario;
  if (!sc || !t.env) return <div className="panel">Loading habitat…</div>;
  const zone = t.env.zones.find((z) => z.id === t.selectedZone) ?? t.env.zones[0];
  const zc = (sc.zones || []).find((z) => z.zone_id === zone.id) || {};
  const p = val(sc.pressure_kPa);
  const exp = sc.experiment;
  const slots = t.env.experiment_slots;
  const m = sc.matching || {};
  const setM = (k, v) => t.set(["matching", k], v);
  const wall = sc.wall || {};
  return (
    <div className="config">
      <section className="cfg-sec">
        <label className="field" htmlFor="sc-preset"><span className="field-head"><span>Start from a preset</span></span>
          <select id="sc-preset" value="" onChange={(e) => e.target.value && t.loadPreset(e.target.value)}>
            <option value="">Choose a preset…</option>
            {t.presets.map((pr) => <option key={pr.id} value={pr.id}>{pr.scenario.name}</option>)}
          </select></label>
        <label className="field" htmlFor="sc-name"><span className="field-head"><span>Scenario name</span></span>
          <input id="sc-name" value={sc.name} maxLength={80} onChange={(e) => t.set(["name"], e.target.value || "Untitled")} /></label>
      </section>

      <section className="cfg-sec">
        <h4>Cabin atmosphere</h4>
        <NumField id="o2" label="Oxygen" unit="%" tv={sc.composition.o2_pct} range={RANGES.o2_pct} step="0.1" onCommit={(v) => t.setValue(["composition", "o2_pct"], v)} />
        <NumField id="p" label="Pressure" unit="kPa" tv={sc.pressure_kPa} range={RANGES.pressure_kPa} step="0.1" onCommit={(v) => t.setValue(["pressure_kPa"], v)}
          readout={p != null ? `= ${(p / 6.894757).toFixed(2)} psia = ${(p / 101.325).toFixed(3)} atm` : null} />
        <NumField id="T" label="Temperature" unit="°C" tv={sc.temperature_K} range={RANGES.temperature_K} step="0.5"
          toUi={(k) => k - C2K} fromUi={(c) => c + C2K} onCommit={(v) => t.setValue(["temperature_K"], v)} />
        <label className="field" htmlFor="grav"><span className="field-head"><span>Gravity</span><TwinStatusTag status="user_defined" /></span>
          <select id="grav" value={sc.gravity} onChange={(e) => t.set(["gravity"], e.target.value)}>
            {GRAVITY.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select></label>
      </section>

      <section className="cfg-sec">
        <h4>Experiment</h4>
        <label className="field" htmlFor="slot"><span className="field-head"><span>Location</span></span>
          <select id="slot" value={exp.slot_id || ""} onChange={(e) => {
            const s = slots.find((x) => x.id === e.target.value);
            t.set(["experiment"], { ...exp, slot_id: s?.id ?? null, zone_id: s?.zone_id ?? exp.zone_id });
            if (s) t.ui({ selectedZone: s.zone_id });
          }}>
            {slots.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.zone_id})</option>)}
          </select></label>
        <label className="field" htmlFor="fc"><span className="field-head"><span>Material class</span></span>
          <select id="fc" value={exp.fuel_class || ""} onChange={(e) => t.set(["experiment", "fuel_class"], e.target.value || null)}>
            {FUEL.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select></label>
      </section>

      <span className="eyebrow adv-title">Advanced</span>
      <Disclosure plain title={`Zone ${zone.id} conditions`} hint={zone.name} open={zoneOpen}>
        <div className="zone-pick" role="group" aria-label="Select zone">
          {t.env.zones.map((z) => <button key={z.id} className={z.id === zone.id ? "on" : ""} onClick={() => t.ui({ selectedZone: z.id })} aria-pressed={z.id === zone.id}>{z.id}</button>)}
        </div>
        <NumField id="zT" label="Zone temperature" unit="°C" tv={zc.temperature_K} range={RANGES.temperature_K} optional step="0.5"
          toUi={(k) => k - C2K} fromUi={(c) => c + C2K} onCommit={(v) => t.setZone(zone.id, "temperature_K", v)} hint="Blank = habitat temperature." />
        <NumField id="zU" label="Local airflow" unit="m/s" tv={zc.airflow_m_s} range={RANGES.airflow_m_s} optional step="0.01"
          onCommit={(v) => t.setZone(zone.id, "airflow_m_s", v)} hint="User-defined local speed (not computed)." />
        <NumField id="zO" label="Zone O₂ override" unit="%" tv={zc.o2_pct} range={RANGES.o2_pct} optional step="0.1"
          onCommit={(v) => t.setZone(zone.id, "o2_pct", v)} hint="Blank = habitat O₂." />
      </Disclosure>

      <Disclosure plain title="Sample and heat transfer" hint="Models D1, D2">
        <label className="field" htmlFor="mat"><span className="field-head"><span>Material text (optional)</span></span>
          <input id="mat" value={exp.material || ""} maxLength={60} placeholder="e.g. PMMA, SIBAL, heptane"
            onChange={(e) => t.set(["experiment", "material"], e.target.value || null)} /></label>
        <NumField id="Ls" label="Sample length (flow direction)" unit="m" tv={exp.characteristic_length_m} range={RANGES.characteristic_length_m} optional step="0.01"
          onCommit={(v) => t.setValue(["experiment", "characteristic_length_m"], v)} />
        <NumField id="Ts" label="Sample surface temperature" unit="°C" tv={exp.surface_temperature_K} range={RANGES.surface_temperature_K} optional step="1"
          toUi={(k) => k - C2K} fromUi={(c) => c + C2K} onCommit={(v) => t.setValue(["experiment", "surface_temperature_K"], v)}
          hint="Needed for Model D1 (inert surface heat exchange); never assumed." />
        <p className="faint small">Wall conduction (D2) needs all four wall values; wall properties are never assumed.</p>
        <label className="field" htmlFor="wl"><span className="field-head"><span>Wall material label</span></span>
          <input id="wl" value={wall.material_label || ""} maxLength={60} onChange={(e) => t.set(["wall"], { ...wall, material_label: e.target.value || null })} /></label>
        {[["thickness_m", "Wall thickness", "m", "0.001"], ["conductivity_W_mK", "Wall thermal conductivity", "W/(m·K)", "0.01"]].map(([k, l, u, st]) => (
          <NumField key={k} id={`w-${k}`} label={l} unit={u} tv={wall[k]} range={RANGES[k]} optional step={st}
            onCommit={(v) => t.set(["wall"], { ...wall, [k]: v == null ? null : { value: v, status: "user_defined", source: null } })} />
        ))}
        {[["inner_temperature_K", "Wall inner temperature"], ["outer_temperature_K", "Wall outer temperature"]].map(([k, l]) => (
          <NumField key={k} id={`w-${k}`} label={l} unit="°C" tv={wall[k]} range={RANGES[k]} optional step="1" toUi={(x) => x - C2K} fromUi={(x) => x + C2K}
            onCommit={(v) => t.set(["wall"], { ...wall, [k]: v == null ? null : { value: v, status: "user_defined", source: null } })} />
        ))}
      </Disclosure>

      <Disclosure plain title="Habitat and ventilation" hint="geometry, Model C">
        <NumField id="D" label="Interior diameter" unit="m" tv={sc.habitat.diameter_m} range={RANGES.diameter_m} step="0.1" onCommit={(v) => t.setValue(["habitat", "diameter_m"], v)} />
        <NumField id="L" label="Interior length" unit="m" tv={sc.habitat.length_m} range={RANGES.length_m} step="0.1" onCommit={(v) => t.setValue(["habitat", "length_m"], v)} />
        <NumField id="Q" label="Ventilation flow" unit="m³/h" tv={sc.ventilation.volumetric_flow_m3_h} range={RANGES.ventilation} step="10"
          onCommit={(v) => t.setValue(["ventilation", "volumetric_flow_m3_h"], v)} />
        <label className="field" htmlFor="dir"><span className="field-head"><span>Flow direction</span></span>
          <select id="dir" value={sc.ventilation.direction} onChange={(e) => t.set(["ventilation", "direction"], e.target.value)}>
            <option value="+x">Forward → aft</option><option value="-x">Aft → forward</option>
          </select></label>
      </Disclosure>

      <Disclosure plain title="Trace gases" hint="Ar, CO₂">
        <NumField id="ar" label="Argon" unit="%" tv={sc.composition.ar_pct} range={RANGES.ar_pct} optional step="0.01" onCommit={(v) => t.setValue(["composition", "ar_pct"], v)} hint="Blank = not included (dry O₂/N₂ mixture)." />
        <NumField id="co2" label="Carbon dioxide" unit="%" tv={sc.composition.co2_pct} range={RANGES.co2_pct} optional step="0.01" onCommit={(v) => t.setValue(["composition", "co2_pct"], v)} />
      </Disclosure>

      <Disclosure plain title="Evidence matching" hint="what counts as a NASA match">
        <label className="check"><input type="checkbox" checked={m.use_pressure !== false} onChange={(e) => setM("use_pressure", e.target.checked)} /> Compare pressure</label>
        <label className="check"><input type="checkbox" checked={!!m.use_airflow} onChange={(e) => setM("use_airflow", e.target.checked)} /> Compare local airflow</label>
        <label className="check"><input type="checkbox" checked={!!m.use_material} onChange={(e) => setM("use_material", e.target.checked)} /> Filter by material</label>
        <label className="check"><input type="checkbox" checked={!!m.use_temperature} onChange={(e) => setM("use_temperature", e.target.checked)} /> Compare temperature <span className="faint small">(no PSI table documents it)</span></label>
        <div className="tol">
          <label>O₂ ± <input type="number" min="0.1" max="20" step="0.5" value={m.o2_tolerance_pts ?? 2} onChange={(e) => setM("o2_tolerance_pts", Math.min(20, Math.max(0.1, +e.target.value || 2)))} /> pts</label>
          <label>P ± <input type="number" min="0.5" max="50" step="0.5" value={m.pressure_tolerance_kPa ?? 6.89} onChange={(e) => setM("pressure_tolerance_kPa", Math.min(50, Math.max(0.5, +e.target.value || 6.89)))} /> kPa</label>
          <label>Airflow ± <input type="number" min="0.005" max="1" step="0.01" value={m.airflow_tolerance_m_s ?? 0.05} onChange={(e) => setM("airflow_tolerance_m_s", Math.min(1, Math.max(0.005, +e.target.value || 0.05)))} /> m/s</label>
        </div>
      </Disclosure>
    </div>
  );
}
