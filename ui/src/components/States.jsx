import { AlertTriangle, Inbox } from "lucide-react";

export function Loading({ label = "Loading NASA evidence…", rows = 3 }) {
  return (
    <div className="panel" role="status" aria-live="polite">
      <span className="small faint">{label}</span>
      {Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton" style={{ width: `${88 - i * 15}%` }} />)}
    </div>
  );
}

/** Error with what happened and how to recover. */
export function ErrorPanel({ error, onRetry }) {
  const offline = error?.status === 0 || error?.code === "network_error";
  return (
    <div className="panel warn state" role="alert">
      <span className="state-title"><AlertTriangle size={15} aria-hidden /> {offline ? "The FIREWISE data service is unreachable" : "Something went wrong"}</span>
      <span className="muted small">{error?.message ?? "Unknown error."} {error?.code && !offline && <span className="mono">({error.code})</span>}</span>
      <span className="faint small">{offline ? "Check that the backend is running, then retry." : "Retry; if it persists, reload the page."}</span>
      {onRetry && <button className="btn sm" onClick={onRetry}>Retry</button>}
    </div>
  );
}

/** Empty state: say what is (not) there and what the user can do next. */
export function Empty({ title, children }) {
  return (
    <div className="panel empty state center">
      <Inbox size={20} className="faint" aria-hidden />
      <span className="state-title">{title}</span>
      {children && <span className="muted small">{children}</span>}
    </div>
  );
}
