import { useEffect, useMemo, useState } from "react";
import { ArrowRight, FlaskConical, Crosshair, Box, Sparkles } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ScatterChart, Scatter, ReferenceArea, Legend, ZAxis, ResponsiveContainer,
} from "recharts";
import { tooltipStyle } from "../components/ChartCard.jsx";
import { PageHeader, Metrics, Disclosure } from "../components/ui.jsx";
import { EvidenceLink, useEvidence } from "../components/Evidence.jsx";
import { TierTag } from "../components/Tags.jsx";
import { Loading, ErrorPanel } from "../components/States.jsx";
import { useApi, twin, chats } from "../services/api.js";
import { FUEL_LABEL, SERIES_COLOR, STATUS_INFO } from "../data/constants.js";
import { num } from "../utils/format.js";

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
      <div className="muted small">Source: {p.rowKey.split(":")[1]} table, row {p.rowKey.split(":")[2]?.slice(1)}</div>
      <div className="muted small">{FUEL_LABEL[p.fc]} · click to open the verbatim NASA row</div>
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

function relTime(iso) {
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 3600) return `${Math.max(1, Math.floor(d / 60))} min ago`;
  if (d < 86400) return `${Math.floor(d / 3600)} h ago`;
  return new Date(iso).toLocaleDateString();
}

/** Recent activity in this browser's workspace (saved twin scenarios and Copilot conversations). */
function RecentActivity({ onNavigate }) {
  const [state, setState] = useState({ scenarios: null, chats: null });
  useEffect(() => {
    twin.list().then((x) => setState((s) => ({ ...s, scenarios: x }))).catch(() => setState((s) => ({ ...s, scenarios: [] })));
    chats.list().then((x) => setState((s) => ({ ...s, chats: x }))).catch(() => setState((s) => ({ ...s, chats: [] })));
  }, []);
  const items = [
    ...(state.scenarios ?? []).map((x) => ({ kind: "Twin scenario", title: x.name, when: x.updated_at, detail: `${x.o2_pct}% O₂ · ${x.pressure_kPa} kPa · ${x.gravity}`, go: () => onNavigate("twin", "scenarios") })),
    ...(state.chats ?? []).filter((c) => c.message_count).map((c) => ({ kind: "Copilot", title: c.title, when: c.updated_at, detail: `${c.message_count / 2 | 0} question${c.message_count === 2 ? "" : "s"}`, go: () => onNavigate("assistant") })),
  ].sort((a, b) => b.when.localeCompare(a.when)).slice(0, 5);
  if (state.scenarios === null || state.chats === null) return <p className="faint small">Loading…</p>;
  if (!items.length) return <p className="muted small">Nothing yet. Saved Digital Twin scenarios and Copilot conversations from this browser appear here.</p>;
  return (
    <ul className="plain activity">
      {items.map((x, i) => (
        <li key={i}><button className="activity-row" onClick={x.go}>
          <span className="tag">{x.kind}</span><span className="activity-title">{x.title}</span>
          <span className="faint small">{x.detail} · {relTime(x.when)}</span>
        </button></li>
      ))}
    </ul>
  );
}

const TASKS = [
  { page: "experiments", icon: FlaskConical, title: "Explore investigations", text: "Browse NASA's 24 combustion investigations, their test records and sources." },
  { page: "scenarios", icon: Crosshair, title: "Check a habitat atmosphere", text: "See which NASA tests document a given O₂ and pressure." },
  { page: "twin", icon: Box, title: "Configure the Digital Twin", text: "Set up a habitat in 3D, match it to evidence and run physics models." },
  { page: "assistant", icon: Sparkles, title: "Ask the Copilot", text: "Get cited answers that separate evidence, calculations and unknowns." },
];

export default function Overview({ onNavigate }) {
  const { data: summary, error, loading, reload } = useApi("/api/summary");
  const m = (k) => summary?.metrics[k];
  return (
    <>
      <PageHeader eyebrow="FIREWISE" title="Fire-safety evidence for space exploration"
        description="NASA's microgravity combustion investigations, organised so you can see what was tested, under which documented conditions, and where the evidence stops." />
      {loading && <Loading rows={3} />}
      {error && <ErrorPanel error={error} onRetry={reload} />}
      {summary && (
        <Metrics items={[
          { value: m("investigations").value, label: "NASA combustion investigations", evidence: m("investigations").evidence_id },
          { value: m("unique_individual_tests").value, label: "individual tests (duplicates excluded)", evidence: m("unique_individual_tests").evidence_id,
            tip: `${m("condition_records").value.toLocaleString()} condition records in 22 NASA tables, some summarising several tests.` },
          { value: summary.scenario_counts.exploration_envelope, label: "tests in the 30–36% O₂ / 8.2–10.2 psia habitat window", evidence: "agg:scenario:exploration_envelope", alert: true },
          { value: m("partial_gravity_records").value, label: "partial-gravity (Moon/Mars) records", evidence: m("partial_gravity_records").evidence_id, alert: true },
        ]} />
      )}

      <h3 className="section-title">Start here</h3>
      <div className="task-grid">
        {TASKS.map(({ page, icon: Icon, title, text }) => (
          <button key={page} className="task" onClick={() => onNavigate(page)}>
            <Icon size={18} aria-hidden /><span><b>{title}</b><span className="muted small">{text}</span></span>
            <ArrowRight size={16} className="task-arrow" aria-hidden />
          </button>
        ))}
      </div>

      <div className="overview-cols">
        <section>
          <div className="section-head"><h3>Key findings</h3><button className="btn ghost sm" onClick={() => onNavigate("gaps")}>All research gaps <ArrowRight size={14} /></button></div>
          {summary && (
            <ul className="plain findings-compact">
              {summary.key_findings.slice(0, 4).map((k) => (
                <li key={k.id}>
                  <div className="row-between"><b>{k.title}</b><TierTag tier={k.tier} /></div>
                  <p className="muted small">{k.statement}</p>
                  <div className="ev-row">{k.evidence_ids.slice(0, 2).map((id) => <EvidenceLink key={id} id={id} />)}</div>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section>
          <div className="section-head"><h3>Recent activity</h3></div>
          <RecentActivity onNavigate={onNavigate} />
        </section>
      </div>

      <Disclosure title="Where the evidence sits: chamber O₂ vs pressure for every documented record" hint="interactive chart">
        <O2PressureChart height={380} />
      </Disclosure>
      {summary && (
        <Disclosure title="Limitations of the data">
          <ul className="limits">{summary.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
        </Disclosure>
      )}
    </>
  );
}
