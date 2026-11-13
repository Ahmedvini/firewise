// Research gaps: where NASA's PSI data document no relevant tests, and what they do establish.
// Gaps lead (readable, actionable); the heatmaps and the methodology are one click away.
import { PageHeader, Notice, Disclosure, CoverageBar } from "../components/ui.jsx";
import { EvidenceLink } from "../components/Evidence.jsx";
import { Loading, ErrorPanel } from "../components/States.jsx";
import { useApi } from "../services/api.js";
import { FUEL_LABEL } from "../data/constants.js";
import GapMap from "./GapMap.jsx";

const STATUS = {
  gap: { label: "No NASA data", tone: "red" },
  partial: { label: "Partial evidence", tone: "amber" },
  established: { label: "Established by NASA data", tone: "green" },
  possible: { label: "Possible implication", tone: "amber" },
};

function gapsFrom(s) {
  const m = (k) => s.metrics[k]?.value;
  const doc = s.documentation_by_fuel_class;
  const both = Object.values(doc).reduce((a, d) => a + d.both, 0);
  const records = Object.values(doc).reduce((a, d) => a + d.both + d.o2_only + d.p_only + d.neither, 0);
  return [
    { id: "exploration", status: "gap", title: "Exploration atmosphere: 30–36% O₂ at 8.2–10.2 psia",
      text: `No PSI record documents chamber O₂ and pressure inside this window. Under the challenge's looser Moon-base definition (≥30% O₂, ≤10.2 psia) there are ${s.scenario_counts.moon_base_challenge} records, all ACME CFI-G gas flames.`,
      n: s.scenario_counts.exploration_envelope, total: both, of: "records that document both chamber O₂ and pressure",
      missing: ["any fuel at enriched O₂ and reduced pressure", "solid cabin materials"], next: "Fly material and gas tests at the planned habitat atmosphere (FM2 plans 34% O₂ / 8.2 psia).",
      evidence: ["agg:scenario:exploration_envelope", "agg:scenario:moon_base_challenge", "fact:F18"] },
    { id: "solids", status: "gap", title: "Solid materials have no documented chamber pressure",
      text: `${m("solid_with_pressure")} of ${m("solid_records")} solid-material tests document chamber pressure, and their documented O₂ reaches at most ${m("solid_o2_max_pct")}%.`,
      n: m("solid_with_pressure"), total: m("solid_records"), of: "solid-material tests with documented pressure",
      missing: ["chamber pressure", `chamber O₂ above ${m("solid_o2_max_pct")}%`], next: "Recover pressure from raw data or reports where it exists; test solids at enriched, low-pressure conditions.",
      evidence: ["agg:solid_records", "agg:solid_with_pressure", "agg:solid_o2_max_pct"] },
    { id: "gravity", status: "gap", title: "No partial-gravity (lunar or Mars) combustion data",
      text: "Every PSI combustion record is microgravity. LUCI flew at simulated lunar gravity in 2025 and FM2 is planned; neither has data in PSI.",
      n: m("partial_gravity_records"), total: records, of: "records at lunar or Mars gravity",
      missing: ["0.16 g and 0.38 g behaviour of every fuel class"], next: "Add LUCI and FM2 results when NASA publishes them; until then, lunar or Martian behaviour cannot be inferred.",
      evidence: ["agg:partial_gravity_records", "fact:F17", "fact:X01", "fact:X02"] },
  ];
}

function findingsFrom(s) {
  const m = (k) => s.metrics[k]?.value;
  return [
    { status: "established", title: "Cool flames appear only in a narrow CFI-G condition set",
      text: "Seven CFI-G normal-flame tests are marked as cool flames, all with 30% butane at about 39% chamber O₂ and about 2 bar.", evidence: ["agg:cfig_cool_flame_yes", "fact:F02"] },
    { status: "possible", title: "Normal-gravity screening and microgravity burning can disagree",
      text: "In Saffire-II at 20 cm/s, silicone samples that burned completely in normal-gravity tests showed about zero burn length in microgravity, while SIBAL fabric samples burned 29 cm in microgravity.", evidence: ["fact:F06"] },
    { status: "possible", title: "Burning without airflow at elevated O₂",
      text: "The BRE solid emulator observed quasi-steady burning in microgravity without air flow, notably in elevated-oxygen atmospheres. Its chamber pressure is not documented in the PSI table.", evidence: ["fact:F08", "fact:F09"] },
    { status: "established", title: "Smoke-detection research built on a qualified instrument",
      text: "DAFT/DAFT-2 qualified a modified particle counter in microgravity to de-risk SAME; SAME-R re-flew after SAME's sample grids returned contaminated.", evidence: ["fact:F04", "fact:F05"] },
    { status: "established", title: "NASA source tables contain defects — flagged, not hidden",
      text: `${m("anomaly_flags")} anomalies (duplicated rows, spreadsheet artifacts, encoding loss) are flagged on the affected records; duplicates are kept out of every count.`, evidence: ["agg:anomaly_flags", "fact:F20"] },
    { status: "established", title: "Inverse-flame O₂ is not an atmosphere",
      text: "In ACME inverse flames the O₂ value is the burner oxidizer stream issued into a fuel ambient; values up to 85% are never compared with a cabin.", evidence: ["fact:F19"] },
  ];
}

export default function ResearchGaps({ onOpenExperiment, onNavigate }) {
  const { data: s, error, loading, reload } = useApi("/api/summary");
  const { data: g } = useApi("/api/gaps");
  return (
    <>
      <PageHeader title="Research gaps"
        description="Where NASA's combustion data document no tests relevant to future habitats — and what they do establish."
        actions={<button className="btn" onClick={() => onNavigate("twin")}>Test a habitat in the Digital Twin</button>} />
      <Notice>A gap means no documented PSI test. It is a gap in evidence — not a statement that a condition is safe or unsafe.</Notice>
      {loading && <Loading rows={6} />}
      {error && <ErrorPanel error={error} onRetry={reload} />}
      {s && (
        <>
          <h3 className="section-title">Key evidence gaps</h3>
          <div className="gap-list">
            {gapsFrom(s).map((x) => (
              <article key={x.id} className="gap-item">
                <div className="gap-main">
                  <span className={`tag ${STATUS[x.status].tone}`}>{STATUS[x.status].label}</span>
                  <h3>{x.title}</h3>
                  <p className="muted">{x.text}</p>
                  <div className="gap-facts small">
                    <div><span className="faint">Missing</span> {x.missing.join(" · ")}</div>
                    <div><span className="faint">What would close it</span> {x.next}</div>
                  </div>
                  <div className="ev-row">{x.evidence.map((id) => <EvidenceLink key={id} id={id} />)}</div>
                </div>
                <div className="gap-cov">
                  <span className="faint small">Coverage</span>
                  <CoverageBar n={x.n} total={x.total} />
                  <span className="faint small">{x.of}</span>
                </div>
              </article>
            ))}
          </div>

          <h3 className="section-title">How completely each fuel class is documented</h3>
          <div className="panel table-wrap">
            <table>
              <thead><tr><th>Fuel class</th><th>Chamber O₂ and pressure</th><th>O₂ only</th><th>Pressure only</th><th>Neither</th></tr></thead>
              <tbody>
                {Object.entries(s.documentation_by_fuel_class).map(([fc, d]) => {
                  const t = d.both + d.o2_only + d.p_only + d.neither;
                  return (
                    <tr key={fc}><td>{FUEL_LABEL[fc] ?? fc}</td><td><CoverageBar n={d.both} total={t} /></td>
                      <td className="tnum">{d.o2_only}</td><td className="tnum">{d.p_only}</td><td className="tnum">{d.neither}</td></tr>
                  );
                })}
              </tbody>
            </table>
            <p className="faint small">Non-duplicate records; chamber (ambient) O₂ only. “Not documented” may exist in raw data or papers — it is never treated as zero.</p>
          </div>

          <h3 className="section-title">What NASA data do establish</h3>
          <ul className="finding-list">
            {findingsFrom(s).map((f) => (
              <li key={f.title}>
                <span className={`tag ${STATUS[f.status].tone}`}>{STATUS[f.status].label}</span>
                <div><b>{f.title}</b><p className="muted small">{f.text}</p><div className="ev-row">{f.evidence.map((id) => <EvidenceLink key={id} id={id} />)}</div></div>
              </li>
            ))}
          </ul>

          <Disclosure title="Coverage map by fuel class, pressure and O₂" hint="heatmaps for each gravity level">
            <GapMap onOpenExperiment={onOpenExperiment} />
          </Disclosure>
          <Disclosure title="Methodology, definitions and limitations">
            {g && <dl>{Object.entries(g.definitions).map(([k, v]) => <div key={k}><dt>{k.replaceAll("_", " ")}</dt><dd>{v}</dd></div>)}</dl>}
            <h4>Limitations</h4>
            <ul className="limits">{s.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
          </Disclosure>
        </>
      )}
    </>
  );
}
