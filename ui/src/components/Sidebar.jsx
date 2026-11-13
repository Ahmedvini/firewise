import { LayoutDashboard, Sparkles, FlaskConical, GitCompare, ShieldAlert } from "lucide-react";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "assistant", label: "AI Assistant", icon: Sparkles },
  { id: "experiments", label: "Experiments", icon: FlaskConical },
  { id: "compare", label: "Compare", icon: GitCompare },
  { id: "insights", label: "Safety", icon: ShieldAlert },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="brand">
        FLARE
        <small>Fire Intelligence for Space Exploration</small>
      </div>
      {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
        <button key={id} className={`nav-link ${activePage === id ? "active" : ""}`}
          onClick={() => onNavigate(id)} aria-current={activePage === id ? "page" : undefined}>
          <Icon size={18} />
          <span>{label}</span>
        </button>
      ))}
      <p className="sidebar-about">
        A research interface for NASA microgravity combustion data. Frontend prototype: no dataset or AI backend is connected yet.
      </p>
    </nav>
  );
}
