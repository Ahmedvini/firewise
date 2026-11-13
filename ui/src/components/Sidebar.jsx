import { LayoutDashboard, Sparkles, FlaskConical, GitCompare, ShieldAlert, Crosshair, Grid3x3, Box } from "lucide-react";
import { useApi } from "../services/api.js";

const NAV_ITEMS = [
  { id: "overview", label: "Mission Control", short: "Home", icon: LayoutDashboard },
  { id: "experiments", label: "Investigations", short: "Explore", icon: FlaskConical },
  { id: "scenarios", label: "Scenario Explorer", short: "Scenarios", icon: Crosshair },
  { id: "twin", label: "Digital Twin", short: "Twin", icon: Box },
  { id: "compare", label: "Compare", short: "Compare", icon: GitCompare },
  { id: "gaps", label: "Research Gap Map", short: "Gaps", icon: Grid3x3 },
  { id: "insights", label: "Findings", short: "Findings", icon: ShieldAlert },
  { id: "assistant", label: "AI Copilot", short: "Copilot", icon: Sparkles },
];

export default function Sidebar({ activePage, onNavigate }) {
  const { data: health, error } = useApi("/api/health");
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="brand">
        FIREWISE
        <small>Fire-safety evidence for space exploration</small>
      </div>
      {NAV_ITEMS.map(({ id, label, short, icon: Icon }) => (
        <button key={id} className={`nav-link ${activePage === id ? "active" : ""}`}
          onClick={() => onNavigate(id)} aria-current={activePage === id ? "page" : undefined}>
          <Icon size={18} />
          <span className="nav-long">{label}</span><span className="nav-short">{short}</span>
        </button>
      ))}
      <div className="sidebar-about">
        <div className="status-line">
          <span className={`dot ${error ? "bad" : health ? "ok" : ""}`} aria-hidden />
          {error ? "Data service offline" : health ? "NASA evidence database online" : "Connecting…"}
        </div>
        {health?.build && <div className="small">Build {health.build.build_utc.slice(0, 10)} · {health.build.report_pages_indexed.toLocaleString()} NASA report pages indexed</div>}
        {health && <div className="small">Copilot: {health.copilot_configured ? `${health.copilot_model} + validator` : "deterministic mode (no language model configured)"}</div>}
        <div className="small">Data: NASA Physical Sciences Informatics (PSI). Not an official NASA product.</div>
      </div>
    </nav>
  );
}
