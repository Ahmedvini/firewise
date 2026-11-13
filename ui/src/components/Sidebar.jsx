import { LayoutDashboard, Sparkles, FlaskConical, Crosshair, Box, SearchX } from "lucide-react";
import { useApi } from "../services/api.js";
import { CopilotModeLine } from "./ApiKeySettings.jsx";

// Six task-based destinations. Secondary actions (compare, findings, scenarios, reports) live inside their pages.
const NAV_ITEMS = [
  { id: "overview", label: "Overview", short: "Overview", icon: LayoutDashboard },
  { id: "experiments", label: "Investigations", short: "Explore", icon: FlaskConical },
  { id: "scenarios", label: "Scenario Explorer", short: "Scenarios", icon: Crosshair },
  { id: "twin", label: "Digital Twin", short: "Twin", icon: Box },
  { id: "gaps", label: "Research Gaps", short: "Gaps", icon: SearchX },
  { id: "assistant", label: "Copilot", short: "Copilot", icon: Sparkles },
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
          <Icon aria-hidden />
          <span className="nav-long">{label}</span><span className="nav-short">{short}</span>
        </button>
      ))}
      <div className="sidebar-about">
        <div className="status-line">
          <span className={`dot ${error ? "bad" : health ? "ok" : ""}`} aria-hidden />
          {error ? "Data service offline" : health ? "NASA evidence database online" : "Connecting…"}
        </div>
        {health && <div className="small"><CopilotModeLine /></div>}
        <div className="small">Every value comes from NASA PSI records and keeps its status (measured, derived, reported, set-point, not documented). Missing values are never zero. Not an official NASA product.</div>
      </div>
    </nav>
  );
}
