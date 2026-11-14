import { EvidenceLink, registerInlineEvidence } from "./Evidence.jsx";
import { TierTag } from "./Tags.jsx";
import { Disclosure } from "./ui.jsx";
import { evidenceKind } from "../utils/format.js";

const MODE_LABEL = {
  llm_validated: "Language-model answer, validated against cited evidence",
  llm_web_search: "Web-searched model answer; not validated against NASA evidence",
  llm_unverified: "General model response, not validated against NASA evidence",
  deterministic: "Deterministic answer computed from the database",
  evidence_only: "Evidence list only (no validated prose)",
};
// Claim groups, in reading order. Every claim keeps its exact tier tag inside its group.
const GROUPS = [
  ["Documented evidence", ["measured", "reported", "literature"]],
  ["Calculations and model estimates", ["calculation", "model_prediction"]],
  ["Unknown or not documented", ["unknown"]],
  ["Interpretation", ["interpretation"]],
];

/** One Copilot answer: summary, grouped cited claims, limitations and gaps; sources and method on demand. */
export default function Answer({ r, onOpenExperiment, context }) {
  registerInlineEvidence(r.evidence);
  const status = r.status === "answered" ? null : r.status === "partial" ? "Partial answer" : "Insufficient evidence";
  return (
    <div className="msg system answer">
      {(status || r.cached || context?.twin_scenario) && (
        <div className="tags answer-tags">
          {status && <span className={`tag ${r.status === "partial" ? "amber" : "red"}`}>{status}</span>}
          {context?.twin_scenario && <span className="tag amber" title={`Selected zone ${context.selected_zone ?? "—"} · input hash ${context.input_hash}`}>Twin: {context.twin_scenario}</span>}
          {r.cached && <span className="tag blue" title="Same question and context answered before; served from the answer cache">Cached answer</span>}
        </div>
      )}
      {r.notice && <p className="note small">{r.notice}</p>}
      {r.answer_summary && <p className="summary">{r.answer_summary}</p>}
      {GROUPS.map(([title, tiers]) => {
        const claims = r.claims.filter((c) => tiers.includes(c.tier));
        if (!claims.length) return null;
        return (
          <div key={title} className="claim-group">
            <span className="eyebrow">{title}</span>
            <ul className="claims">
              {claims.map((c, i) => (
                <li key={i}>
                  <span className="claim-text">{c.text}</span>
                  <span className="claim-meta"><TierTag tier={c.tier} />{c.evidence_ids.map((id) => <EvidenceLink key={id} id={id} />)}</span>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
      {r.limitations.length > 0 && <div className="claim-group"><span className="eyebrow">Limitations</span><ul className="limits">{r.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul></div>}
      {r.gaps.length > 0 && <div className="claim-group"><span className="eyebrow">Evidence gaps</span><ul className="limits">{r.gaps.map((g, i) => <li key={i}>{g}</li>)}</ul></div>}
      <Disclosure plain title={`Sources and method (${r.evidence.length} evidence items)`}>
        <p className="small faint">{MODE_LABEL[r.mode]} · {r.latency_ms} ms{r.model ? ` · ${r.model.id}` : ""}</p>
        {r.related_investigations.length > 0 && onOpenExperiment && (
          <p className="small">Related investigations: {r.related_investigations.map((id, i) => <span key={id}>{i ? ", " : ""}<button className="linkish" onClick={() => onOpenExperiment(id)}>{id}</button></span>)}</p>
        )}
        <ul className="plain evidence-list">
          {r.evidence.map((e) => (
            <li key={e.evidence_id}>
              <EvidenceLink id={e.evidence_id} label={e.title} />
              <span className="faint small"> {evidenceKind(e.kind)}</span>
              <div className="muted small clamp2">{e.snippet}</div>
            </li>
          ))}
        </ul>
      </Disclosure>
    </div>
  );
}
