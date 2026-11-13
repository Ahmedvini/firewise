import { AlertTriangle } from "lucide-react";

export function Loading({ label = "Loading NASA evidence…", rows = 3 }) {
  return (
    <div className="panel" role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton" style={{ width: `${88 - i * 15}%` }} />)}
    </div>
  );
}

export function ErrorPanel({ error, onRetry }) {
  return (
    <div className="panel warn" role="alert">
      <span className="tag red"><AlertTriangle size={12} /> Data service unavailable</span>
      <p className="muted">{error?.message ?? "Unknown error."} {error?.code && <span className="mono small">({error.code})</span>}</p>
      {onRetry && <button className="btn" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="panel empty hatch">
      <strong>{title}</strong>
      {children && <p className="muted small">{children}</p>}
    </div>
  );
}
