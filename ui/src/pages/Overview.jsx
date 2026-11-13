import { useMemo, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ScatterChart, Scatter, ReferenceArea, Legend, ZAxis, ResponsiveContainer,
} from "recharts";
import SampleBanner from "../components/SampleBanner.jsx";
import StatCard from "../components/StatCard.jsx";
import ChartCard, { tooltipStyle } from "../components/ChartCard.jsx";
import ExperimentCard from "../components/ExperimentCard.jsx";
import { EvidenceLink, useEvidence } from "../components/Evidence.jsx";
import { TierTag } from "../components/Tags.jsx";
import { Loading, ErrorPanel } from "../components/States.jsx";
import { useApi } from "../services/api.js";
import { FUEL_LABEL, SERIES_COLOR, STATUS_INFO } from "../data/constants.js";
import { num } from "../utils/format.js";

const FEATURED = ["PSI-159", "PSI-69", "PSI-99", "PSI-47"];
const axis = { stroke: "#A9B0C0", fontSize: 12 };

/** Marker shape encodes measurement status (secondary encoding; colour = fuel class). */
function StatusShape({ cx, cy, fill, payload }) {
  if (cx == null || cy == null) return null;
  const st = payload.status;
  const r = 4;
  const ring = { stroke: "#0f1522", strokeWidth: 1 };
  if (st === "measured") return <circle cx={cx} cy={cy} r={r} fill={fill} fillOpacity={0.85} {...ring} />;
  if (st === "derived") return <path d={`M${cx} ${cy - r - 1}L${cx + r + 1} ${cy}L${cx} ${cy + r + 1}L${cx - r - 1} ${cy}Z`} fill={fill} {...ring} />;
  if (st === "specified") return <rect x={cx - r} y={cy - r} width={2 * r} height={2 * r} fill="none" stroke={fill} strokeWidth={1.6} />;
  return <circle cx={cx} cy={cy} r={r} fill="none" stroke={fill} strokeWidth={1.6} />; // reported (approximate)
}

function PointTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="chart-tip">
      <strong>{p.inv} · test {p.label}</strong>
      <div>Chamber O₂ {num(p.x)}% <span className="muted">({STATUS_INFO[p.o2s]?.label})</span></div>
      <div>Pressure {num(p.y)} psia <span className="muted">({STATUS_INFO[p.ps]?.label})</span></div>
      <div className="muted small">{FUEL_LABEL[p.fc]} · click to open the source row</div>
    </div>
  );
}

export function O2PressureChart({ height = 380, windows = true, highlight }) {
  const { data, error, loading, reload } = useApi("/api/points");
  const { data: summary } = useApi("/api/summary");
  const { open } = useEvidence();
  const series = useMemo(() => {
    if (!data) return {};
    const out = {};
    for (const [rowKey, inv, fc, label, o2, p, o2s, ps] of data.points) {
      // status of the point = the weaker of the two statuses (measured > derived > reported > specified)
      const rank = { measured: 0, derived: 1, reported: 2, specified: 3 };
      const status = rank[o2s] >= rank[ps] ? o2s : ps;
      (out[fc] ||= []).push({ x: o2, y: p, rowKey, inv, label, fc, o2s, ps, status });
    }
    return out;
  }, [data]);
  if (loading) return <Loading rows={6} />;
  if (error) return <ErrorPanel error={error} onRetry={reload} />;
  const sc = summary?.scenario_counts ?? {};
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h3>Chamber O₂ vs pressure — every documented NASA record</h3>
          <p className="muted small">{data.n_points.toLocaleString()} of {data.n_records.toLocaleString()} records document both chamber O₂ and pressure; the rest are not plotted (not documented ≠ zero). Inverse-flame burner-stream O₂ is excluded. Shape = measurement status.</p>
        </div>
      </div>
      <div style={{ height }} role="img" aria-label={`Scatter of ${data.n_points} records: chamber oxygen percent versus pressure in psia, coloured by fuel class.`}>
        <ScatterChartWrapper series={series} windows={windows} sc={sc} highlight={highlight} onPoint={(p) => open(`row:${p.rowKey}`)} />
      </div>
      <div className="tags legend" style={{ marginTop: 8 }}>
        {["measured", "derived", "reported", "specified"].map((s) => (
          <span key={s} className="tag status"><svg width="12" height="12" aria-hidden><StatusShape cx={6} cy={6} fill="#c3c2b7" payload={{ status: s }} /></svg> {STATUS_INFO[s].label}</span>
        ))}
      </div>
    </div>
  );
}

function ScatterChartWrapper({ series, windows, sc, highlight, onPoint }) {
  const [hover, setHover] = useState(null);
  return (
    <ResponsiveScatter>
      <ScatterChart margin={{ top: 16, right: 24, bottom: 28, left: 8 }}>
        <CartesianGrid stroke="rgba(169,176,192,.12)" />
        <XAxis type="number" dataKey="x" name="Chamber O₂" unit="%" domain={[10, 45]} ticks={[10, 15, 20, 25, 30, 35, 40, 45]} {...axis}
          label={{ value: "Chamber (ambient) O₂, mole %", position: "insideBottom", offset: -16, fill: "#A9B0C0", fontSize: 12 }} />
        <YAxis type="number" dataKey="y" name="Pressure" unit=" psia" scale="log" domain={[5, 80]} allowDataOverflow={false}
          ticks={[5, 7.35, 8.2, 10.2, 14.7, 20, 30, 45, 75]} tickFormatter={(v) => `${v}`} {...axis}
          label={{ value: "Pressure, psia (log scale)", angle: -90, position: "insideLeft", fill: "#A9B0C0", fontSize: 12 }} />
        <ZAxis range={[60, 60]} />
        {windows && (
          <>
            <ReferenceArea x1={30} x2={45} y1={5} y2={10.2} fill="#FFB454" fillOpacity={0.05} stroke="rgba(255,180,84,.35)" strokeDasharray="3 3"
              label={{ value: `Moon base (challenge): ${sc.moon_base_challenge ?? "…"} records`, position: "insideBottomRight", fill: "#FFB454", fontSize: 11 }} />
            <ReferenceArea x1={30} x2={36} y1={8.2} y2={10.2} fill={highlight === "exploration" ? "rgba(255,113,56,.18)" : "rgba(255,113,56,.10)"} stroke="#FF7138" strokeWidth={1.5}
              label={{ value: `Exploration envelope: ${sc.exploration_envelope ?? "…"} records`, position: "top", fill: "#FF7138", fontSize: 11 }} />
            <ReferenceArea x1={20} x2={22} y1={14.2} y2={15.2} fill="rgba(169,176,192,.08)" stroke="rgba(169,176,192,.5)"
              label={{ value: `ISS cabin: ${sc.iss ?? "…"}`, position: "insideTopLeft", fill: "#A9B0C0", fontSize: 11, dy: -16 }} />
          </>
        )}
        <Tooltip content={<PointTooltip />} cursor={{ strokeDasharray: "3 3", stroke: "rgba(169,176,192,.4)" }} />
        <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12, color: "#A9B0C0" }} />
        {Object.entries(series).map(([fc, pts]) => (
          <Scatter key={fc} name={`${FUEL_LABEL[fc]} (${pts.length})`} data={pts} fill={SERIES_COLOR[fc]} shape={<StatusShape />}
            onClick={(p) => onPoint(p.payload ?? p)} onMouseEnter={(p) => setHover(p)} onMouseLeave={() => setHover(null)}
            isAnimationActive={false} cursor="pointer" fillOpacity={hover ? 0.85 : 1} />
        ))}
      </ScatterChart>
    </ResponsiveScatter>
  );
}

const ResponsiveScatter = ({ children }) => <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>;

export default function Overview({ onNavigate, onOpenExperiment }) {
  const [microgravity, setMicrogravity] = useState(false);
  const { data: s, error, loading, reload } = useApi("/api/summary");
  const { data: invs } = useApi("/api/investigations?limit=500");

  const m = s?.metrics ?? {};
  const byFuel = s ? Object.entries(s.by_fuel_class).map(([k, v]) => ({ name: FUEL_LABEL[k] ?? k, value: v })) : [];
  const doc = s
    ? Object.entries(s.documentation_by_fuel_class).map(([k, v]) => ({ name: FUEL_LABEL[k] ?? k, ...v }))
    : [];
  const featured = (invs?.items ?? []).filter((e) => FEATURED.includes(e.id)).sort((a, b) => FEATURED.indexOf(a.id) - FEATURED.indexOf(b.id));

  return (
    <>
      <SampleBanner />

      <section className="hero">
        <div>
          <h1 className="hero-title">FIREWISE</h1>
          <p className="hero-sub">Understanding combustion in microgravity. Turning NASA research into evidence for fire-safety decisions.</p>
          <p className="lede">
            FIREWISE organizes NASA&apos;s Physical Sciences Informatics combustion investigations into documented test
            conditions, comparisons and research gaps for spacecraft and future lunar habitats. Every value links to
            its NASA source and keeps its status — measured, set-point, reported or not documented.
          </p>
          <button className="btn primary" onClick={() => onNavigate("scenarios")}>Explore habitat scenarios</button>{" "}
          <button className="btn" onClick={() => onNavigate("assistant")}>Ask the Copilot</button>
        </div>

        <div className="panel stage" aria-label="Flame shape on Earth versus in microgravity">
          <div className={`flame ${microgravity ? "round" : ""}`} />
          <div className="stage-controls">
            <div className="segmented">
              <button className={!microgravity ? "on" : ""} onClick={() => setMicrogravity(false)}>Earth gravity</button>
              <button className={microgravity ? "on" : ""} onClick={() => setMicrogravity(true)}>Microgravity</button>
            </div>
            <small className="muted">Conceptual illustration, not experimental data</small>
          </div>
        </div>
      </section>

      {loading && <Loading rows={4} />}
      {error && <ErrorPanel error={error} onRetry={reload} />}
      {s && (
        <>
          <h2>The evidence base at a glance</h2>
          <div className="grid cols-3 section-gap">
            <StatCard value={m.investigations.value} label="NASA PSI combustion investigations" evidence={m.investigations.evidence_id} />
            <StatCard value={m.condition_records.value} label="Normalized condition records from 22 NASA experimental tables" evidence={m.condition_records.evidence_id} />
            <StatCard value={m.unique_individual_tests.value} label="Unique individual tests (duplicates excluded)" evidence={m.unique_individual_tests.evidence_id} />
            <StatCard value={m.partial_gravity_records.value} label="Partial-gravity (lunar / Mars) records" evidence={m.partial_gravity_records.evidence_id} highlight />
            <StatCard value={m.anomaly_flags.value} label="Defects found in NASA source tables — flagged, not hidden" evidence={m.anomaly_flags.evidence_id} />
            <StatCard value={m.report_pages_indexed.value} label="NASA report pages searchable by the Copilot" />
          </div>

          <h2>Key findings</h2>
          <p className="lede">Each finding is computed from the database and links to the records behind it.</p>
          <div className="grid cols-3 section-gap">
            {s.key_findings.map((k) => (
              <div className="panel finding" key={k.id}>
                <TierTag tier={k.tier} />
                <h3>{k.title}</h3>
                <p className="muted">{k.statement}</p>
                <div className="ev-row">{k.evidence_ids.map((id) => <EvidenceLink key={id} id={id} />)}</div>
              </div>
            ))}
          </div>

          <h2>Where the evidence sits</h2>
          <div className="section-gap"><O2PressureChart /></div>

          <div className="grid cols-2 section-gap">
            <ChartCard title="Records by fuel class">
              <BarChart data={byFuel} layout="vertical" margin={{ left: 40, right: 24 }}>
                <CartesianGrid stroke="rgba(169,176,192,.12)" horizontal={false} />
                <XAxis type="number" allowDecimals={false} {...axis} />
                <YAxis type="category" dataKey="name" width={170} {...axis} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="value" name="Records" fill="#3987e5" radius={[0, 4, 4, 0]} isAnimationActive={false} />
              </BarChart>
            </ChartCard>
            <ChartCard title="What each fuel class documents (chamber O₂ / pressure)">
              <BarChart data={doc} layout="vertical" margin={{ left: 40, right: 24 }} stackOffset="expand">
                <defs>
                  <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                    <rect width="6" height="6" fill="#1b2232" /><line x1="0" y1="0" x2="0" y2="6" stroke="#5b6475" strokeWidth="2" />
                  </pattern>
                </defs>
                <CartesianGrid stroke="rgba(169,176,192,.12)" horizontal={false} />
                <XAxis type="number" tickFormatter={(v) => `${Math.round(v * 100)}%`} {...axis} />
                <YAxis type="category" dataKey="name" width={170} {...axis} />
                <Tooltip {...tooltipStyle} formatter={(v, name) => [v.toLocaleString(), name]} />
                <Legend wrapperStyle={{ fontSize: 12, color: "#A9B0C0" }} />
                <Bar dataKey="both" stackId="d" name="O₂ and pressure" fill="#86b6ef" isAnimationActive={false} />
                <Bar dataKey="o2_only" stackId="d" name="O₂ only" fill="#3987e5" isAnimationActive={false} />
                <Bar dataKey="p_only" stackId="d" name="Pressure only" fill="#1c5cab" isAnimationActive={false} />
                <Bar dataKey="neither" stackId="d" name="Neither documented" fill="url(#hatch)" isAnimationActive={false} />
              </BarChart>
            </ChartCard>
          </div>

          <h2>Featured investigations</h2>
          <div className="grid cols-4 section-gap">
            {featured.map((e) => <ExperimentCard key={e.id} experiment={e} showSummary onSelect={onOpenExperiment} />)}
          </div>

          <h2>Read this before drawing conclusions</h2>
          <div className="panel section-gap">
            <ul className="limits">{s.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
          </div>
        </>
      )}
    </>
  );
}
