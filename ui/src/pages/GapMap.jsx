import { useMemo, useState } from "react";
import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import { Loading, ErrorPanel } from "../components/States.jsx";
import { EvidenceLink } from "../components/Evidence.jsx";
import { TierTag } from "../components/Tags.jsx";
import { useApi } from "../services/api.js";
import { FUEL_LABEL } from "../data/constants.js";

// Sequential single-hue ramp (dataviz reference blue, dark mode: brighter = more records).
const RAMP = ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#cde2fb"];
const GRAVITY_TABS = [
  ["microgravity", "Microgravity (all PSI flight data)"],
  ["partial_gravity", "Partial gravity (Moon / Mars)"],
  ["normal_gravity", "Normal gravity (1 g)"],
];

// "8.2-10.2 psia" -> "0.56–0.69 atm"; "<8.2 psia" -> "<0.56 atm" (1 atm = 14.696 psia)
function psiaToAtm(band) {
  const a = (v) => (parseFloat(v) / 14.696).toFixed(2);
  const m = band.match(/^([<>]?)([\d.]+)(?:-([\d.]+))?/);
  if (!m) return "";
  return m[3] ? `${a(m[2])}–${a(m[3])} atm` : `${m[1]}${a(m[2])} atm`;
}

function cellColor(n, max) {
  if (!n) return null;
  const t = Math.log(n + 1) / Math.log(max + 1);
  return RAMP[Math.min(RAMP.length - 1, Math.floor(t * RAMP.length))];
}

export default function GapMap({ onOpenExperiment }) {
  const { data, error, loading, reload } = useApi("/api/gaps");
  const [gravity, setGravity] = useState("microgravity");
  const [picked, setPicked] = useState(null);

  const idx = useMemo(() => {
    const m = new Map();
    data?.cells.forEach((c) => m.set(`${c.gravity_regime}|${c.fuel_class}|${c.o2_band}|${c.p_band}`, c));
    return m;
  }, [data]);
  if (loading) return <Loading rows={8} />;
  if (error) return <ErrorPanel error={error} onRetry={reload} />;
  if (!data) return null;

  const max = Math.max(1, ...data.cells.map((c) => c.records));
  const o2 = data.dims.o2_band;
  // High pressure at the top; "not documented" kept as the last row/column, visually separated.
  const pBands = [...data.dims.p_band.filter((b) => b !== "not documented").reverse(), "not documented"];
  const overlays = data.literature_overlays.filter((o) => o.gravity_regime === gravity);
  const totalAt = data.cells.filter((c) => c.gravity_regime === gravity).reduce((a, c) => a + c.records, 0);

  return (
    <>
      <SampleBanner danger>
        A zero cell means NASA&apos;s PSI tables document no test there. It is a gap in evidence — not a statement that the condition is safe or unsafe.
      </SampleBanner>
      <Header eyebrow="Research Gap Map" title="Where NASA has — and has not — tested"
        description="Each panel is one fuel class. Rows are chamber pressure, columns chamber (ambient) O₂; the last row and column hold records where that value is not documented. Cell shade = number of records (log scale). Hatched = none. The outlined cell is the 30–36% O₂ / 8.2–10.2 psia exploration envelope." />

      <div className="grid cols-4 section-gap">
        {data.headline.map((k) => (
          <div className="panel finding" key={k.id}><TierTag tier={k.tier} /><h3>{k.title}</h3><p className="muted small">{k.statement}</p>
            <div className="ev-row">{k.evidence_ids.slice(0, 2).map((id) => <EvidenceLink key={id} id={id} />)}</div></div>
        ))}
      </div>

      <div className="segmented gravity-tabs" role="tablist">
        {GRAVITY_TABS.map(([g, l]) => (
          <button key={g} role="tab" aria-selected={gravity === g} className={gravity === g ? "on" : ""} onClick={() => { setGravity(g); setPicked(null); }}>{l}</button>
        ))}
      </div>
      <p className="muted small">{totalAt.toLocaleString()} documented records at this gravity level.{gravity === "normal_gravity" && ` ${data.definitions.normal_gravity}`}</p>

      <div className="gap-grid">
        {data.dims.fuel_class.map((fc) => (
          <div className="panel gap-panel" key={fc}>
            <h3>{FUEL_LABEL[fc] ?? fc}</h3>
            <div className="heat" style={{ gridTemplateColumns: `78px repeat(${o2.length}, minmax(0, 1fr))` }} role="grid" aria-label={`${FUEL_LABEL[fc]} records by pressure and oxygen`}>
              <div />
              {o2.map((b) => <div key={b} className={`heat-col ${b === "not documented" ? "nd" : ""}`}>{b === "not documented" ? "O₂ n/d" : b.replace(" (air)", "")}</div>)}
              {pBands.map((pb) => (
                <div key={pb} className="heat-row" role="row" style={{ display: "contents" }}>
                  <div className={`heat-rowlabel ${pb === "not documented" ? "nd" : ""}`}>{pb === "not documented" ? "P not documented" : <>{pb.replace(" (~1 atm)", "")}<span className="atm">{psiaToAtm(pb)}</span></>}</div>
                  {o2.map((ob) => {
                    const c = idx.get(`${gravity}|${fc}|${ob}|${pb}`);
                    const n = c?.records ?? 0;
                    const color = cellColor(n, max);
                    const env = ob === "30-36%" && pb === "8.2-10.2 psia";
                    const lit = overlays.filter((o) => o.fuel_class === fc && o.o2_band === ob && o.p_band === pb);
                    return (
                      <button key={ob} role="gridcell" className={`heat-cell ${n ? "" : "hatch"} ${env ? "env" : ""} ${lit.length ? "lit" : ""} ${ob === "not documented" || pb === "not documented" ? "nd" : ""}`}
                        style={color ? { background: color, color: RAMP.indexOf(color) >= 4 ? "#0b1220" : "#F5F7FA" } : undefined}
                        title={`${FUEL_LABEL[fc]} · O₂ ${ob} · ${pb}${pb === "not documented" ? "" : ` (${psiaToAtm(pb)})`}: ${n} records${lit.length ? ` · ${lit.map((o) => o.label).join("; ")}` : ""}`}
                        onClick={() => setPicked({ fc, ob, pb, c, lit })}>
                        {n ? n : lit.length ? "lit" : "0"}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="legend-row small muted section-gap">
        <span>Fewer</span>{RAMP.map((c) => <span key={c} className="sw" style={{ background: c }} />)}<span>More records</span>
        <span className="sw hatch" /> none documented <span className="sw env-sw" /> exploration envelope <span className="sw lit-sw" /> literature only (outside PSI)
      </div>

      {picked && (
        <div className="panel section-gap">
          <h3>{FUEL_LABEL[picked.fc]} · chamber O₂ {picked.ob} · {picked.pb}</h3>
          {picked.c ? (
            <p>{picked.c.records} documented records from{" "}
              {Object.entries(picked.c.investigations).map(([inv, n], i) => (
                <span key={inv}>{i ? ", " : ""}<button className="linkish" onClick={() => onOpenExperiment(inv)}>{inv}</button> ({n})</span>
              ))}.
            </p>
          ) : <p className="muted">No PSI record documents this combination.</p>}
          {picked.lit.map((o) => <p key={o.id}><span className="tag amber">{o.status}</span> {o.label} <EvidenceLink id={o.evidence_id} /></p>)}
        </div>
      )}

      <div className="panel section-gap">
        <h3>Definitions</h3>
        <dl>{Object.entries(data.definitions).map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      </div>
    </>
  );
}
