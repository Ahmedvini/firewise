import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import ChartCard, { tooltipStyle } from "../components/ChartCard.jsx";
import { EXPERIMENTS, COMPARE_PARAMETERS } from "../data/sampleData.js";

export default function Compare() {
  const [chosenIds, setChosenIds] = useState(["bass2", "saffire3", "acme"]);
  const [paramKey, setParamKey] = useState("oxygenPercent");

  const toggle = (id) =>
    setChosenIds(chosenIds.includes(id) ? chosenIds.filter((x) => x !== id) : [...chosenIds, id]);

  const chosen = EXPERIMENTS.filter((e) => chosenIds.includes(e.id));
  const param = COMPARE_PARAMETERS.find((p) => p.key === paramKey);
  const missing = chosen.filter((e) => e[paramKey] == null);
  const axis = { stroke: "#A9B0C0", fontSize: 12 };
  const show = (v) => (v == null ? <span className="muted">Not in dataset</span> : v);

  return (
    <>
      <SampleBanner />
      <Header title="Compare and analyze"
        description="Select two or more experiments. When a measurement is missing, the experiments are flagged as not directly comparable. Values are placeholders and imply no scientific conclusion." />

      <div className="chips">
        {EXPERIMENTS.map((e) => (
          <button key={e.id} className={chosenIds.includes(e.id) ? "on" : ""} onClick={() => toggle(e.id)}>{e.name}</button>
        ))}
      </div>

      {chosen.length < 2 ? (
        <div className="panel empty">Select at least two experiments to compare.</div>
      ) : (
        <>
          <div className="grid cols-2">
            <div>
              <select value={paramKey} onChange={(e) => setParamKey(e.target.value)} aria-label="Parameter" className="param-select">
                {COMPARE_PARAMETERS.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
              </select>
              <ChartCard title={param.label}>
                <BarChart data={chosen}>
                  <CartesianGrid stroke="rgba(169,176,192,.12)" vertical={false} />
                  <XAxis dataKey="name" {...axis} /><YAxis {...axis} />
                  <Tooltip {...tooltipStyle} />
                  <Bar dataKey={paramKey} name={param.label} fill="#FF7138" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ChartCard>
            </div>

            <div className="grid">
              {missing.length > 0 ? (
                <div className="panel warn">
                  <span className="tag red">Not directly comparable</span>
                  <p className="muted">{missing.map((e) => e.name).join(", ")} {missing.length > 1 ? "have" : "has"} no value for this parameter in the sample data.</p>
                </div>
              ) : (
                <div className="panel">
                  <span className="tag green">Values available</span>
                  <p className="muted">All selected experiments report this parameter. Differences in other conditions may still limit comparison.</p>
                </div>
              )}
              {chosen.map((e) => (
                <div className="panel" key={e.id}><h3>{e.name}</h3><span className="tag">{e.type}</span></div>
              ))}
            </div>
          </div>

          <div className="panel table-wrap">
            <table>
              <thead><tr><th>Parameter</th>{chosen.map((e) => <th key={e.id}>{e.name}</th>)}</tr></thead>
              <tbody>
                <tr><td>Program</td>{chosen.map((e) => <td key={e.id}>{e.program}</td>)}</tr>
                <tr><td>Fuel / material</td>{chosen.map((e) => <td key={e.id}>{e.fuel}</td>)}</tr>
                {COMPARE_PARAMETERS.map((p) => (
                  <tr key={p.key}><td>{p.label}</td>{chosen.map((e) => <td key={e.id}>{show(e[p.key])}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
