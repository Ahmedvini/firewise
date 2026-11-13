// 2D engineering dashboard over the SAME shared state as the 3D view.
// Provenance is part of every series name: user-defined inputs (orange), NASA records (blue), model outputs (green).
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, LineChart, Line, ScatterChart, Scatter, ZAxis, Legend, Cell, LabelList } from "recharts";
import ChartCard, { tooltipStyle } from "../components/ChartCard.jsx";
import { TwinStatusTag, ValidationTag } from "../components/Tags.jsx";
import { useTwin, val } from "./TwinContext.jsx";
import { twin } from "../services/api.js";

export const SERIES = { user: "#d95926", nasa: "#3987e5", model: "#199e70" };
const axis = { stroke: "#A9B0C0", fontSize: 12 };
const grid = <CartesianGrid stroke="rgba(169,176,192,.12)" />;
const out = (ph, mid, scope, name) => ph?.results.find((r) => r.model_id === mid && r.scope === scope && r.status === "completed")?.outputs.find((o) => o.name === name)?.value ?? null;

function ZoneBars({ title, data, unit, color, refLine, refLabel, provenance }) {
  return (
    <ChartCard title={title}>
      <BarChart data={data} margin={{ top: 18, right: 16, left: 4, bottom: 4 }}>
        {grid}
        <XAxis dataKey="zone" {...axis} />
        <YAxis {...axis} unit={unit} width={64} domain={[0, "auto"]} />
        <Tooltip {...tooltipStyle} formatter={(v, n, item) => [v == null ? "Not set" : `${v} ${unit}`, `${provenance} (${item.payload.status})`]} />
        <Bar dataKey="value" name={provenance} fill={color} radius={[4, 4, 0, 0]} isAnimationActive={false} minPointSize={2}>
          {data.map((d) => <Cell key={d.zone} fill={d.value == null ? "transparent" : color} stroke={d.selected ? "#FFB454" : "none"} strokeWidth={2} />)}
          <LabelList dataKey="value" position="top" fill="#A9B0C0" fontSize={11} formatter={(v) => (v == null ? "not set" : v)} />
        </Bar>
        {refLine != null && <ReferenceLine y={refLine} stroke={SERIES.model} strokeDasharray="5 4" label={{ value: refLabel, fill: SERIES.model, fontSize: 11, position: "insideTopRight" }} />}
      </BarChart>
    </ChartCard>
  );
}

export default function EngineeringView() {
  const t = useTwin();
  const d = t.evaluation.data;
  const [history, setHistory] = useState([]);
  useEffect(() => {
    if (!t.savedId) { setHistory([]); return; }
    twin.history(t.savedId).then(setHistory).catch(() => setHistory([]));
  }, [t.savedId, t.savedVersion]);
  if (!d) return <div className="panel">{t.evaluation.error ? "Evaluation failed — see the message above." : "Computing…"}</div>;
  const zc = d.zone_conditions;
  const ph = d.physics;
  const sel = t.selectedZone;
  const o2 = zc.map((z) => ({ zone: z.zone_id, value: val(z.o2_pct), status: z.o2_pct?.status?.replace("_", "-") ?? "not set", selected: z.zone_id === sel }));
  const temp = zc.map((z) => ({ zone: z.zone_id, value: val(z.temperature_K) == null ? null : +(val(z.temperature_K) - 273.15).toFixed(2), status: z.temperature_K?.status?.replace("_", "-") ?? "not set", selected: z.zone_id === sel }));
  const flow = zc.map((z) => ({ zone: z.zone_id, value: val(z.airflow_m_s), status: val(z.airflow_m_s) == null ? "not set" : z.airflow_m_s.status.replace("_", "-"), selected: z.zone_id === sel }));
  const po2 = zc.map((z) => ({ zone: z.zone_id, value: out(ph, "gas_mixture", `zone:${z.zone_id}`, "o2_partial_pressure") == null ? null : +out(ph, "gas_mixture", `zone:${z.zone_id}`, "o2_partial_pressure").toFixed(2), status: "computed, Model B", selected: z.zone_id === sel }));
  const bulk = out(ph, "bulk_airflow", "habitat", "bulk_velocity");
  const p = val(t.scenario.pressure_kPa);
  const ev = d.evidence;
  const N = ev.coverage.records_considered;
  const cov = Object.entries(ev.coverage.documented).map(([k, v]) => ({ variable: { o2_pct: "Chamber O₂", pressure_kPa: "Pressure", airflow_m_s: "Ambient airflow", temperature_K: "Gas temperature" }[k],
    documented: v.records, missing: v.not_documented }));
  // experimental (NASA nearest) vs scenario (user-defined) on O2 × pressure
  const nasaPts = ev.nearest.filter((n) => n.values.o2_pct.value != null && n.values.pressure_kPa.value != null)
    .map((n) => ({ x: +n.values.o2_pct.value.toFixed(2), y: +n.values.pressure_kPa.value.toFixed(2), label: `${n.acronym || n.investigation_id} ${n.test_label || ""}`, status: `${n.values.o2_pct.status_label} / ${n.values.pressure_kPa.status_label}` }));
  const scPt = [{ x: ev.targets.o2_pct, y: ev.targets.pressure_kPa, label: t.scenario.name, status: "user-defined" }];
  // O2 partial pressure: scenario (computed by Model B from user inputs) vs NASA nearest (derived from documented O2 × P)
  const ppo2 = [{ name: "Scenario", value: out(ph, "gas_mixture", `zone:${ev.targets.zone_id}`, "o2_partial_pressure"), kind: "model" },
    ...nasaPts.slice(0, 6).map((n) => ({ name: n.label.slice(0, 18), value: +(n.x / 100 * n.y).toFixed(2), kind: "nasa" }))];
  const hist = history.map((h) => ({ v: `v${h.version}`, o2: h.o2_pct, p: h.pressure_kPa, T: h.temperature_K == null ? null : +(h.temperature_K - 273.15).toFixed(2) }));
  const session = t.timeline.map((x, i) => ({ i: i + 1, o2: x.o2, p: x.pressure, exact: x.exact }));
  const assumptions = [...new Set(ph.results.filter((r) => r.status === "completed").flatMap((r) => r.assumptions))];
  return (
    <div className="eng">
      <p className="small muted eng-key"><span className="sw" style={{ background: SERIES.user }} /> user-defined <span className="sw" style={{ background: SERIES.model }} /> computed by a model <span className="sw" style={{ background: SERIES.nasa }} /> NASA records · pressure {p?.toFixed(2)} kPa ({(p / 6.894757).toFixed(2)} psia) · bulk velocity {bulk == null ? "not computed" : `${bulk.toFixed(2)} cm/s (Model C)`}</p>
      <div className="grid cols-2 section-gap">
        <ZoneBars title="Oxygen by zone (user-defined)" data={o2} unit="%" color={SERIES.user} provenance="User-defined O₂" />
        <ZoneBars title="O₂ partial pressure by zone (computed, Model B)" data={po2} unit=" kPa" color={SERIES.model} provenance="Computed p(O₂)"
          refLine={21.22} refLabel="sea-level air 21.2 kPa (reference)" />
        <ZoneBars title="Temperature by zone (user-defined)" data={temp} unit=" °C" color={SERIES.user} provenance="User-defined temperature" />
        <ZoneBars title="Local airflow by zone (user-defined) vs bulk velocity (computed)" data={flow} unit=" m/s" color={SERIES.user}
          provenance="User-defined local airflow" refLine={bulk == null ? null : +(bulk / 100).toFixed(4)} refLabel={bulk == null ? "" : `Model C bulk ${(bulk / 100).toFixed(4)} m/s`} />
      </div>

      <div className="grid cols-2 section-gap">
        <ChartCard title="Experimental vs scenario: chamber O₂ × pressure">
          <ScatterChart margin={{ top: 10, right: 16, left: 4, bottom: 10 }}>
            {grid}
            <XAxis type="number" dataKey="x" name="O₂" unit="%" {...axis} domain={["auto", "auto"]} />
            <YAxis type="number" dataKey="y" name="Pressure" unit=" kPa" {...axis} width={70} domain={["auto", "auto"]} />
            <ZAxis range={[70, 70]} />
            <Tooltip {...tooltipStyle} formatter={(v, n) => [v, n]} labelFormatter={() => ""}
              content={({ active, payload }) => active && payload?.length ? <div className="chart-tip"><strong>{payload[0].payload.label}</strong><div>{payload[0].payload.x}% · {payload[0].payload.y} kPa</div><div className="muted">{payload[0].payload.status}</div></div> : null} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Scatter name="Nearest NASA records (documented)" data={nasaPts} fill={SERIES.nasa} isAnimationActive={false} />
            <Scatter name="Scenario (user-defined)" data={scPt} fill={SERIES.user} shape="star" isAnimationActive={false} />
          </ScatterChart>
        </ChartCard>
        <ChartCard title="O₂ partial pressure: scenario (computed) vs nearest NASA records (derived)">
          <BarChart data={ppo2} layout="vertical" margin={{ left: 30, right: 30 }}>
            {grid}
            <XAxis type="number" unit=" kPa" {...axis} />
            <YAxis type="category" dataKey="name" width={130} {...axis} />
            <Tooltip {...tooltipStyle} formatter={(v, n, item) => [`${v} kPa`, item.payload.kind === "model" ? "Computed by Model B from user-defined inputs" : "Derived from NASA documented O₂ × pressure"]} />
            <Bar dataKey="value" radius={4} isAnimationActive={false}>
              {ppo2.map((r, i) => <Cell key={i} fill={r.kind === "model" ? SERIES.model : SERIES.nasa} />)}
            </Bar>
          </BarChart>
        </ChartCard>
      </div>

      <div className="grid cols-2 section-gap">
        <ChartCard title={`Evidence coverage across ${N.toLocaleString()} NASA records`}>
          <BarChart data={cov} layout="vertical" margin={{ left: 30, right: 30 }}>
            {grid}
            <XAxis type="number" {...axis} />
            <YAxis type="category" dataKey="variable" width={120} {...axis} />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="documented" name="Documented" stackId="a" fill={SERIES.nasa} isAnimationActive={false} />
            <Bar dataKey="missing" name="Not documented (never zero)" stackId="a" fill="#3a4357" isAnimationActive={false} />
          </BarChart>
        </ChartCard>
        <div className="grid">
          {hist.length > 1 ? (
            <div className="grid cols-2">
              <ChartCard title="Saved versions: O₂ (%)"><LineChart data={hist}>{grid}<XAxis dataKey="v" {...axis} /><YAxis {...axis} width={44} domain={["auto", "auto"]} /><Tooltip {...tooltipStyle} /><Line dataKey="o2" stroke={SERIES.user} strokeWidth={2} dot isAnimationActive={false} name="O₂ (user-defined)" /></LineChart></ChartCard>
              <ChartCard title="Saved versions: pressure (kPa)"><LineChart data={hist}>{grid}<XAxis dataKey="v" {...axis} /><YAxis {...axis} width={44} domain={["auto", "auto"]} /><Tooltip {...tooltipStyle} /><Line dataKey="p" stroke={SERIES.user} strokeWidth={2} dot isAnimationActive={false} name="Pressure (user-defined)" /></LineChart></ChartCard>
            </div>
          ) : (
            <div className="panel"><h3>Scenario parameter history</h3><p className="muted small">{t.savedId ? "Only one saved version so far. Save again after changes to build the history." : "Save the scenario to record a version history."}</p></div>
          )}
          {session.length > 1 && (
            <ChartCard title="This session: exact NASA matches after each change">
              <LineChart data={session}>{grid}<XAxis dataKey="i" {...axis} /><YAxis {...axis} width={40} allowDecimals={false} /><Tooltip {...tooltipStyle} formatter={(v, n, item) => [v, `exact matches (O₂ ${item.payload.o2}%, ${item.payload.p} kPa)`]} /><Line dataKey="exact" stroke={SERIES.nasa} strokeWidth={2} dot isAnimationActive={false} name="Exact NASA matches" /></LineChart>
            </ChartCard>
          )}
        </div>
      </div>

      <div className="grid cols-2 section-gap">
        <div className="panel table-wrap">
          <h3>Simulation outputs — zone {sel}</h3>
          <table className="dense">
            <thead><tr><th>Model</th><th>Output</th><th>Value</th><th>Unit</th><th>Validation</th></tr></thead>
            <tbody>
              {ph.results.filter((r) => (r.scope === `zone:${sel}` || r.scope === "habitat" || r.scope.startsWith("experiment")) && r.status === "completed")
                .flatMap((r) => r.outputs.map((o) => (
                  <tr key={`${r.model_id}-${r.scope}-${o.name}`}><td className="small">{r.model_name.split(" — ")[0]} <span className="muted">({r.scope})</span></td>
                    <td>{o.name.replaceAll("_", " ")}</td><td className="tnum">{Number(o.value.toPrecision(5))}</td><td className="small">{o.unit}</td><td><ValidationTag status={o.validation_status} /></td></tr>
                )))}
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h3>Model assumptions in force</h3>
          <ul className="limits">{assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
          <p className="muted small">Uncertainty: Model B transport properties agree with independent air data within ±2% (250–400 K, air composition); other outputs are exact given their inputs and assumptions. See the Physics view for validation records.</p>
        </div>
      </div>
    </div>
  );
}
