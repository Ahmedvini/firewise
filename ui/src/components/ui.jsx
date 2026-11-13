// FIREWISE design-system primitives. Pages compose these instead of ad-hoc markup.
import { Info, AlertTriangle, HelpCircle } from "lucide-react";
import { EvidenceLink } from "./Evidence.jsx";

/** Page title, one-sentence description, optional provenance note and actions. */
export function PageHeader({ title, description, eyebrow, note, actions }) {
  return (
    <header className="page-header">
      <div className="ph-text">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h2>{title}</h2>
        {description && <p className="lede">{description}</p>}
        {note && <p className="ph-note"><Info size={14} aria-hidden /> <span>{note}</span></p>}
      </div>
      {actions && <div className="ph-actions">{actions}</div>}
    </header>
  );
}

/** Callout. tone: "warn" (default) | "danger" | "info". Use only for information the reader must not miss. */
export function Notice({ tone = "warn", children }) {
  const Icon = tone === "danger" ? AlertTriangle : Info;
  return (
    <div className={`banner ${tone === "warn" ? "" : tone}`} role="note">
      <Icon size={16} aria-hidden />
      <span>{children}</span>
    </div>
  );
}

/** A row of key numbers. items: [{value, label, evidence?, alert?, foot?}] */
export function Metrics({ items }) {
  return (
    <div className="metrics">
      {items.map((m) => (
        <div key={m.label} className={`metric ${m.alert ? "alert" : ""}`}>
          <span className={`m-value ${typeof m.value === "string" ? "text" : ""}`}>{typeof m.value === "number" ? m.value.toLocaleString("en-US") : m.value}</span>
          <span className="m-label">{m.label}{m.tip && <InfoTip text={m.tip} />}</span>
          {(m.evidence || m.foot) && <span className="m-foot">{m.evidence && <EvidenceLink id={m.evidence} label="source" />}{m.foot}</span>}
        </div>
      ))}
    </div>
  );
}

/** Progressive disclosure: an expandable section with a one-line hint of what is inside. */
export function Disclosure({ title, hint, children, open = false, plain = false, id }) {
  return (
    <details className={`disclosure ${plain ? "plain" : ""}`} open={open} id={id}>
      <summary><span>{title}</span>{hint && <span className="d-hint">{hint}</span>}</summary>
      <div className="d-body">{children}</div>
    </details>
  );
}

/** Underlined tab bar. items: [[key, label, Icon?]]; `after` renders right-aligned extra items. */
export function Tabs({ items, value, onChange, label, after }) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {items.map(([k, l, Icon]) => (
        <button key={k} role="tab" aria-selected={value === k} className={value === k ? "on" : ""} onClick={() => onChange(k)}>
          {Icon && <Icon size={15} aria-hidden />}{l}
        </button>
      ))}
      {after && <><span className="tabs-spacer" />{after}</>}
    </div>
  );
}

/** Small ⓘ that explains a technical term on hover/focus. */
export function InfoTip({ text }) {
  return (
    <span className="infotip" tabIndex={0} aria-label={text}>
      <HelpCircle size={13} aria-hidden />
      <span className="tip" role="tooltip">{text}</span>
    </span>
  );
}

/** Thin bar showing how many records document something (n of total). Zero is drawn hatched, never as a value. */
export function CoverageBar({ n, total, label }) {
  const pct = total ? (100 * n) / total : 0;
  return (
    <span className="cov" title={label ?? `${n.toLocaleString()} of ${total.toLocaleString()}`}>
      <span className={`coverage-bar ${n === 0 ? "zero" : ""}`} aria-hidden><span style={{ width: `${pct}%` }} /></span>
      <span className="small tnum">{n.toLocaleString()} / {total.toLocaleString()}</span>
    </span>
  );
}
