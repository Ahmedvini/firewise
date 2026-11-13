import { EvidenceLink, registerInlineEvidence } from "./Evidence.jsx";
import { TierTag } from "./Tags.jsx";
import { evidenceKind } from "../utils/format.js";

const MODE_LABEL = {
  llm_validated: "Language-model answer, validated against cited evidence",
  deterministic: "Deterministic answer computed from the database",
  evidence_only: "Evidence list only (no validated prose)",
};

/** Renders one Copilot AskResponse: status, tiers, cited claims, limitations, gaps, evidence. */
export default function Answer({ r, onOpenExperiment, context }) {
  registerInlineEvidence(r.evidence);
  return (
    <div className="msg system answer">
      <div className="tags">
        <span className={`tag ${r.status === "answered" ? "green" : r.status === "partial" ? "amber" : "red"}`}>
          {r.status === "answered" ? "Answered" : r.status === "partial" ? "Partial answer" : "Insufficient evidence"}
        </span>
        <span className="tag">{MODE_LABEL[r.mode]}</span>
        {r.cached && <span className="tag blue" title="Identical question and context answered before; served from the answer cache">Cached answer</span>}
        {context?.twin_scenario && <span className="tag amber" title={`Selected zone ${context.selected_zone ?? "—"} · input hash ${context.input_hash}`}>Twin: {context.twin_scenario}</span>}
        <span className="tag mono">{r.latency_ms} ms</span>
      </div>
      {r.notice && <p className="note small">{r.notice}</p>}
      {r.answer_summary && <p className="summary">{r.answer_summary}</p>}
      {r.claims.length > 0 && (
        <ul className="claims">
          {r.claims.map((c, i) => (
            <li key={i}>
              <TierTag tier={c.tier} />
              <span>{c.text}</span>
              <span className="ev-row">{c.evidence_ids.map((id) => <EvidenceLink key={id} id={id} />)}</span>
            </li>
          ))}
        </ul>
      )}
      {r.limitations.length > 0 && <><h4>Limitations</h4><ul>{r.limitations.map((l, i) => <li key={i} className="muted">{l}</li>)}</ul></>}
      {r.gaps.length > 0 && <><h4>Evidence gaps</h4><ul>{r.gaps.map((g, i) => <li key={i} className="muted">{g}</li>)}</ul></>}
      {r.related_investigations.length > 0 && onOpenExperiment && (
        <><h4>Related investigations</h4>
          <p>{r.related_investigations.map((id, i) => <span key={id}>{i ? ", " : ""}<button className="linkish" onClick={() => onOpenExperiment(id)}>{id}</button></span>)}</p></>
      )}
      {r.evidence.length > 0 && (
        <details className="evidence-list">
          <summary>Evidence consulted ({r.evidence.length})</summary>
          <ul>
            {r.evidence.map((e) => (
              <li key={e.evidence_id}>
                <EvidenceLink id={e.evidence_id} label={e.title} />
                <span className="muted small"> {evidenceKind(e.kind)}</span>
                <div className="muted small clamp2">{e.snippet}</div>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
