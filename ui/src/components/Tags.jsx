import { STATUS_INFO, TIER_INFO, TWIN_STATUS, VALIDATION_INFO } from "../data/constants.js";
import { contextLabel, rangeText } from "../utils/format.js";

/** Measurement status: glyph + text (never colour alone). */
export function StatusTag({ status, label }) {
  const s = STATUS_INFO[status] ?? STATUS_INFO.missing;
  return (
    <span className={`tag status ${s.tone} ${status === "missing" ? "dashed" : ""}`} title={s.desc}>
      <span aria-hidden className="glyph">{s.glyph}</span>{label ?? s.label}
    </span>
  );
}

export function TierTag({ tier }) {
  const t = TIER_INFO[tier] ?? { label: tier, glyph: "•", tone: "", desc: "" };
  return (
    <span className={`tag status ${t.tone}`} title={t.desc}>
      <span aria-hidden className="glyph">{t.glyph}</span>{t.label}
    </span>
  );
}

/** A documented range with its status and physical context; "Not documented" is visually distinct from any value. */
export function Quantity({ q, psia = false, compact = false }) {
  const missing = !q || q.min === null || q.min === undefined;
  return (
    <span className="qty">
      <span className={missing ? "qty-value missing" : "qty-value"}>
        {rangeText(q)}
        {psia && !missing && q.psia && <span className="muted small"> ({rangeText(q, true)})</span>}
      </span>
      {!compact && !missing && (
        <span className="qty-meta">
          <StatusTag status={q?.status ?? "missing"} label={q?.status_label?.startsWith("Mixed") ? q.status_label : undefined} />
          {!missing && q.context && <span className="muted small">{contextLabel(q.context)}</span>}
        </span>
      )}
    </span>
  );
}

export function StatusLegend() {
  return (
    <div className="tags legend">
      {Object.entries(STATUS_INFO).map(([k]) => <StatusTag key={k} status={k} />)}
    </div>
  );
}

/** Digital Twin value status (user-defined vs NASA vs model output vs not documented). */
export function TwinStatusTag({ status, source }) {
  const t = TWIN_STATUS[status] ?? { label: status, glyph: "•", tone: "", desc: "" };
  return (
    <span className={`tag status ${t.tone}`} title={`${t.desc}${source ? ` Source: ${source}` : ""}`}>
      <span aria-hidden className="glyph">{t.glyph}</span>{t.label}
    </span>
  );
}

export function ValidationTag({ status }) {
  const v = VALIDATION_INFO[status] ?? { label: status, tone: "", desc: "" };
  return <span className={`tag ${v.tone}`} title={v.desc}>{v.label}</span>;
}
