import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import { INSIGHTS, STATUS_LABELS } from "../data/sampleData.js";

const STATUS_TAG = { established: "green", possible: "amber", research: "red" };
const SECTIONS = [...new Set(INSIGHTS.map((i) => i.section))];

export default function Insights() {
  return (
    <>
      <SampleBanner />
      <SampleBanner danger>
        PSI currently provides no partial-gravity combustion data. Lunar and Martian partial-gravity conclusions must not be read as experimentally confirmed.
      </SampleBanner>
      <Header title="Fire safety insights"
        description="Potential fire safety considerations drawn from research. These are not risk scores and do not predict real-world fire risk." />

      <div className="tags legend">
        {Object.entries(STATUS_LABELS).map(([key, label]) => <span key={key} className={`tag ${STATUS_TAG[key]}`}>{label}</span>)}
      </div>

      {SECTIONS.map((section) => (
        <section key={section}>
          <h3 className="section-title">{section}</h3>
          <div className="grid cols-3">
            {INSIGHTS.filter((i) => i.section === section).map((i) => (
              <div className="panel" key={i.id}>
                <span className={`tag ${STATUS_TAG[i.status]}`}>{STATUS_LABELS[i.status]}</span>
                <h3>{i.title}</h3>
                <p className="muted">{i.observation}</p>
                <dl>
                  <dt>Why it matters</dt><dd>{i.whyItMatters}</dd>
                  <dt>Related experiments</dt><dd>{i.related.length ? i.related.join(", ") : "None available"}</dd>
                  <dt>Evidence</dt><dd className="muted">Source placeholder: no documents linked yet.</dd>
                </dl>
              </div>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
