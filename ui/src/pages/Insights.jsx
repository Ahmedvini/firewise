import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import { EvidenceLink } from "../components/Evidence.jsx";
import { Loading, ErrorPanel } from "../components/States.jsx";
import { useApi } from "../services/api.js";

const STATUS_LABELS = {
  established: "Established finding (NASA data)",
  possible: "Possible implication (interpretation)",
  research: "More research needed (no data)",
};
const STATUS_TAG = { established: "green", possible: "amber", research: "red" };

// Editorial wording is limited to what the cited evidence supports; numbers are filled from the API.
function buildInsights(m, sc) {
  const v = (k) => m[k]?.value;
  return [
    { section: "Spacecraft and ISS", status: "established", title: "Cool flames appear only in a narrow CFI-G condition set",
      observation: "Seven CFI-G normal-flame tests are marked as cool flames, all with 30% butane at about 39% chamber O₂ and about 2 bar.",
      why: "Cool-flame chemistry matters for ignition and extinction behaviour of fuels in spacecraft.", evidence: ["agg:cfig_cool_flame_yes", "fact:F02"] },
    { section: "Spacecraft and ISS", status: "possible", title: "Normal-gravity screening and microgravity burning can disagree",
      observation: "In Saffire-II at 20 cm/s, silicone samples that burned completely in normal-gravity tests showed about zero burn length in microgravity, while SIBAL fabric samples burned 29 cm in microgravity.",
      why: "Material selection relies on normal-gravity tests; flight data show outcomes can differ by material and flow.", evidence: ["fact:F06"] },
    { section: "Spacecraft and ISS", status: "possible", title: "Burning without airflow at elevated O₂",
      observation: "The BRE solid emulator observed quasi-steady burning in microgravity without air flow, notably in elevated-oxygen atmospheres. Its chamber pressure is not documented in the PSI table.",
      why: "Stopping ventilation is a standard response to a fire; its effect at elevated O₂ is not confirmed for real materials.", evidence: ["fact:F08", "fact:F09"] },
    { section: "Spacecraft and ISS", status: "established", title: "Smoke-detection research built on a qualified instrument",
      observation: "DAFT/DAFT-2 qualified a modified particle counter in microgravity to de-risk SAME; SAME-R re-flew after SAME's sample grids returned contaminated.",
      why: "Detector response depends on smoke particle size, which can differ in microgravity.", evidence: ["fact:F04", "fact:F05"] },
    { section: "Lunar habitats", status: "research", title: "No test in the exploration atmosphere envelope",
      observation: `${sc.exploration_envelope ?? "…"} PSI records document chamber O₂ of 30–36% together with 8.2–10.2 psia. Under the challenge's Moon-base definition there are ${sc.moon_base_challenge ?? "…"} records, all gas flames.`,
      why: "Planned habitats may use oxygen-enriched, reduced-pressure air; the closest NASA evidence brackets but does not cover it.", evidence: ["agg:scenario:exploration_envelope", "agg:scenario:moon_base_challenge", "fact:F18"] },
    { section: "Lunar habitats", status: "research", title: "Solid materials lack pressure data",
      observation: `${v("solid_with_pressure")} of ${v("solid_records")} solid-material tests document chamber pressure; documented O₂ for solids reaches at most ${v("solid_o2_max_pct")}%.`,
      why: "Cabin materials are solids; their behaviour in enriched, low-pressure atmospheres is not documented in PSI.", evidence: ["agg:solid_with_pressure", "agg:solid_o2_max_pct"] },
    { section: "Lunar habitats", status: "research", title: "Partial-gravity behaviour is unconfirmed",
      observation: `${v("partial_gravity_records")} PSI records are at lunar gravity. LUCI (flown 2025) and FM2 (planned) are the first steps; their data are not in PSI.`,
      why: "Lunar fire safety cannot be inferred from microgravity data alone.", evidence: ["agg:partial_gravity_records", "fact:X01", "fact:X02"] },
    { section: "Mars habitats and rovers", status: "research", title: "Mars-gravity combustion is unconfirmed",
      observation: `${v("partial_gravity_records")} PSI records are at Mars gravity (0.38 g).`,
      why: "Habitat and rover designs need partial-gravity evidence.", evidence: ["agg:partial_gravity_records", "fact:F17"] },
    { section: "Using NASA data responsibly", status: "established", title: "NASA source tables contain defects — flagged, not hidden",
      observation: `${v("anomaly_flags")} anomalies were found in the PSI tables (duplicated rows, spreadsheet artifacts, encoding loss) and are flagged on the affected records.`,
      why: "Counts and comparisons are only as reliable as the source rows behind them.", evidence: ["agg:anomaly_flags", "fact:F20"] },
    { section: "Using NASA data responsibly", status: "established", title: "Inverse-flame O₂ is not an atmosphere",
      observation: "In ACME inverse flames the O₂ value is the burner oxidizer stream issued into a fuel ambient; values up to 85% are not chamber atmospheres.",
      why: "Mixing the two would invent evidence for oxygen-rich habitats.", evidence: ["fact:F19"] },
  ];
}

export default function Insights() {
  const { data, error, loading, reload } = useApi("/api/summary");
  const insights = data ? buildInsights(data.metrics, data.scenario_counts) : [];
  const sections = [...new Set(insights.map((i) => i.section))];
  return (
    <>
      <SampleBanner danger>
        PSI currently provides no partial-gravity combustion data. Lunar and Martian conclusions must not be read as experimentally confirmed.
      </SampleBanner>
      <Header eyebrow="Findings" title="Fire-safety findings, graded by evidence"
        description="What NASA's data establish, what they suggest, and where evidence is missing. These are not risk scores and do not predict real-world fire risk." />
      <div className="tags legend">
        {Object.entries(STATUS_LABELS).map(([key, label]) => <span key={key} className={`tag ${STATUS_TAG[key]}`}>{label}</span>)}
      </div>
      {loading && <Loading rows={6} />}
      {error && <ErrorPanel error={error} onRetry={reload} />}
      {sections.map((section) => (
        <section key={section}>
          <h3 className="section-title">{section}</h3>
          <div className="grid cols-3">
            {insights.filter((i) => i.section === section).map((i) => (
              <div className="panel" key={i.title}>
                <span className={`tag ${STATUS_TAG[i.status]}`}>{STATUS_LABELS[i.status]}</span>
                <h3>{i.title}</h3>
                <p className="muted">{i.observation}</p>
                <dl>
                  <dt>Why it matters</dt><dd>{i.why}</dd>
                  <dt>Evidence</dt><dd className="ev-row">{i.evidence.map((id) => <EvidenceLink key={id} id={id} />)}</dd>
                </dl>
              </div>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
