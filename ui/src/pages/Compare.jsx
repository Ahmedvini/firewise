import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LabelList } from "recharts";
import { Disclosure } from "../components/ui.jsx";
import ChartCard, { tooltipStyle } from "../components/ChartCard.jsx";
import { EvidenceLink } from "../components/Evidence.jsx";
import { Quantity, TierTag } from "../components/Tags.jsx";
import { Loading, ErrorPanel, Empty } from "../components/States.jsx";
import { useApi } from "../services/api.js";
import { COMPARE_PRESETS, FUEL_LABEL } from "../data/constants.js";
import { num } from "../utils/format.js";

const PARAMS = [
  { key: "Chamber (ambient) O₂", label: "Chamber O₂ (%)", noun: "chamber O₂", unit: "%", pick: (q) => [q.min, q.max] },
  { key: "Chamber pressure", label: "Pressure (psia)", noun: "chamber pressure", unit: " psia", pick: (q) => (q.psia ? [q.psia.min, q.psia.max] : [null, null]) },
  { key: "Airflow", label: "Airflow (cm/s)", noun: "airflow", unit: " cm/s", pick: (q) => [q.min, q.max] },
];
const axis = { stroke: "#A9B0C0", fontSize: 12 };

function Value({ v }) {
  if (v && typeof v === "object" && "unit" in v) return <Quantity q={v} psia={v.unit === "atm"} />;
  if (Array.isArray(v)) return v.length ? <span className="small">{v.map((x) => FUEL_LABEL[x] ?? x).join(", ")}</span> : <span className="missing">Not documented</span>;
  if (v == null || v === "") return <span className="missing">Not documented</span>;
  return <span>{String(v)}</span>;
}

export default function Compare({ onOpenExperiment }) {
  const [chosenIds, setChosenIds] = useState(COMPARE_PRESETS[0].ids);
  const [paramKey, setParamKey] = useState(PARAMS[0].key);
  const { data: list } = useApi("/api/investigations?limit=500");
  const ready = chosenIds.length >= 2 && chosenIds.length <= 4;
  const { data, error, loading, reload } = useApi(ready ? `/api/compare?ids=${chosenIds.join(",")}` : null);

  const toggle = (id) =>
    setChosenIds(chosenIds.includes(id) ? chosenIds.filter((x) => x !== id) : chosenIds.length >= 4 ? chosenIds : [...chosenIds, id]);
  const param = PARAMS.find((p) => p.key === paramKey);
  const feature = data?.features.find((f) => f.name === paramKey);
  const chartData = data && feature
    ? data.investigations.map((inv) => {
        const [lo, hi] = param.pick(feature.values[inv.id] ?? {});
        return { name: inv.acronym || inv.id, range: lo == null ? null : [lo, hi === lo ? lo + (paramKey.includes("O₂") ? 0.15 : 0.08) : hi], lo, hi };
      })
    : [];
  const missing = chartData.filter((d) => d.range == null);

  return (
    <>
      <p className="muted small compare-intro">Pick a preset or choose 2–4 investigations. Documented ranges are compared dimension by dimension; anything not documented is excluded — never treated as zero. Similarity means condition overlap, not scientific equivalence.</p>

      <div className="chips">
        {COMPARE_PRESETS.map((p) => (
          <button key={p.label} className={p.ids.join() === chosenIds.join() ? "on" : ""} onClick={() => setChosenIds(p.ids)}>{p.label}</button>
        ))}
      </div>
      <Disclosure title={`Choose investigations`} hint={`${chosenIds.length} selected · up to 4`}>
        <div className="chips">
          {(list?.items ?? []).map((e) => (
            <button key={e.id} className={chosenIds.includes(e.id) ? "on" : ""} onClick={() => toggle(e.id)} title={e.title}>{e.acronym || e.id}</button>
          ))}
        </div>
      </Disclosure>

      {!ready && <div className="panel empty">Select between two and four investigations to compare.</div>}
      {ready && loading && <Loading rows={6} />}
      {ready && error && <ErrorPanel error={error} onRetry={reload} />}
      {ready && data && (
        <>
          <div className="grid cols-2" style={{ marginTop: 16 }}>
            <div>
              <select value={paramKey} onChange={(e) => setParamKey(e.target.value)} aria-label="Parameter" className="param-select">
                {PARAMS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
              </select>
              {missing.length === chartData.length ? (
                <div className="panel"><Empty title={`No selected investigation documents ${param.noun}.`}>Choose another parameter or preset; missing values are not plotted as zero.</Empty></div>
              ) : (
              <ChartCard title={`${param.label} — documented range`}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 40 }}>
                  <CartesianGrid stroke="rgba(169,176,192,.12)" horizontal={false} />
                  <XAxis type="number" domain={["auto", "auto"]} {...axis} />
                  <YAxis type="category" dataKey="name" width={120} {...axis} />
                  <Tooltip {...tooltipStyle} formatter={(_, __, item) => {
                    const p = item.payload;
                    return [p.lo == null ? "Not documented" : p.lo === p.hi ? `${num(p.lo)}${param.unit}` : `${num(p.lo)}–${num(p.hi)}${param.unit}`, param.label];
                  }} />
                  <Bar dataKey="range" fill="#3987e5" radius={4} isAnimationActive={false} minPointSize={3}>
                    <LabelList dataKey="lo" position="right" formatter={(v) => (v == null ? "Not documented" : "")} fill="#A9B0C0" fontSize={11} />
                  </Bar>
                </BarChart>
              </ChartCard>
              )}
            </div>

            <div className="grid">
              {missing.length > 0 ? (
                <div className="panel warn">
                  <span className="tag red">Not directly comparable on this parameter</span>
                  <p className="muted">{missing.map((d) => d.name).join(", ")} {missing.length > 1 ? "do" : "does"} not document {param.noun} in the PSI tables.</p>
                </div>
              ) : (
                <div className="panel">
                  <span className="tag green">Documented for all selected</span>
                  <p className="muted">Ranges overlap {feature?.similarity == null ? "—" : `${Math.round(feature.similarity * 100)}%`} (interval overlap ÷ union). Other conditions may still limit comparison.</p>
                </div>
              )}
              {data.incompatibilities.map((x, i) => (
                <div className="panel warn" key={i}><span className="tag red">Incompatible: {x.a} vs {x.b}</span><p className="muted">{x.reason}</p></div>
              ))}
              {data.relations.map((r, i) => (
                <div className="panel" key={i}>
                  <span className={`tag ${r.status === "verified" ? "green" : "amber"}`}>{r.status} relationship</span>
                  <p className="muted"><b>{r.src}</b> {r.type.replaceAll("_", " ")} <b>{r.dst}</b>. {r.note}</p>
                  <EvidenceLink id={r.evidence_id} />
                </div>
              ))}
              <div className="panel">
                <span className="tag">Compared on {data.compared_on} dimensions</span>
                <p className="muted small">{data.label}. Mean similarity on comparable dimensions: {data.mean_similarity_on_comparable == null ? "—" : data.mean_similarity_on_comparable.toFixed(2)}.</p>
              </div>
            </div>
          </div>

          <div className="panel table-wrap">
            <table>
              <thead>
                <tr><th>Dimension</th>{data.investigations.map((e) => (
                  <th key={e.id}><button className="linkish" onClick={() => onOpenExperiment(e.id)}>{e.acronym || e.id}</button><div className="mono muted small">{e.id}</div></th>
                ))}<th>Similarity</th></tr>
              </thead>
              <tbody>
                {data.features.map((f) => (
                  <tr key={f.name}>
                    <td>{f.name}{f.note && <div className="muted small">{f.note}</div>}</td>
                    {data.investigations.map((e) => <td key={e.id}><Value v={f.values[e.id]} /></td>)}
                    <td>{f.kind === "count" ? <span className="muted small">context</span> : f.comparable ? <span className="tnum">{f.similarity.toFixed(2)}</span> : <span className="tag">not comparable</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {ready && data && (
        <div className="panel section-gap">
          <h3>Reported in NASA record text</h3>
          <p className="muted small">Facts curated from PSI record text and publications. They are labelled by evidence tier and are not part of the table-based similarity above.</p>
          <div className="facts-grid">
            {data.investigations.map((e) => <RecordFacts key={e.id} id={e.id} name={e.acronym || e.id} />)}
          </div>
        </div>
      )}
      {ready && data && data.investigations.length < chosenIds.length && <Empty title="Some selected ids were not found." />}
    </>
  );
}

function RecordFacts({ id, name }) {
  const { data } = useApi(`/api/investigations/${encodeURIComponent(id)}`);
  if (!data) return <div><b>{name}</b><Loading rows={2} /></div>;
  return (
    <div>
      <b>{name}</b>
      {data.curated_facts.length === 0 && <p className="muted small">No curated facts.</p>}
      {data.curated_facts.map((f) => (
        <div className="fact small" key={f.id}><TierTag tier={f.tier} /> <EvidenceLink id={f.evidence_id} /><p>{f.value}</p></div>
      ))}
    </div>
  );
}
