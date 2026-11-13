import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import EmbersBackground from "./components/EmbersBackground.jsx";
import { EvidenceProvider } from "./components/Evidence.jsx";
import Overview from "./pages/Overview.jsx";
import AIAssistant from "./pages/AIAssistant.jsx";
import Experiments from "./pages/Experiments.jsx";
import Compare from "./pages/Compare.jsx";
import Insights from "./pages/Insights.jsx";
import Scenarios from "./pages/Scenarios.jsx";
import GapMap from "./pages/GapMap.jsx";

const PAGES = ["overview", "experiments", "scenarios", "compare", "gaps", "insights", "assistant"];

// Pages are linkable via the hash: #/compare, #/experiments/PSI-69
function readHash() {
  const [, page, id] = window.location.hash.split("?")[0].split("/");
  return { page: PAGES.includes(page) ? page : "overview", id: id ? decodeURIComponent(id) : null };
}

export default function App() {
  const initial = readHash();
  const [page, setPage] = useState(initial.page);
  const [selectedExperimentId, setSelectedExperimentId] = useState(initial.id);

  useEffect(() => {
    const onHash = () => {
      const h = readHash();
      setPage(h.page);
      if (h.id) setSelectedExperimentId(h.id);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = (p, id = null) => {
    window.location.hash = id ? `/${p}/${encodeURIComponent(id)}` : `/${p}`;
    window.scrollTo({ top: 0 });
  };
  const openExperiment = (id) => {
    setSelectedExperimentId(id);
    navigate("experiments", id);
  };

  const pages = {
    overview: <Overview onNavigate={navigate} onOpenExperiment={openExperiment} />,
    experiments: <Experiments initialSelectedId={selectedExperimentId} onSelect={(id) => navigate("experiments", id)} />,
    scenarios: <Scenarios onOpenExperiment={openExperiment} />,
    compare: <Compare onOpenExperiment={openExperiment} />,
    gaps: <GapMap onOpenExperiment={openExperiment} />,
    insights: <Insights onNavigate={navigate} />,
    assistant: <AIAssistant onOpenExperiment={openExperiment} />,
  };

  return (
    <EvidenceProvider>
      <a href="#main" className="skip-link" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <div className="bg-glow" />
      <EmbersBackground />
      <div className="app-shell">
        <Sidebar activePage={page} onNavigate={navigate} />
        <main className="main-content" key={page} id="main" tabIndex={-1}>
          {pages[page]}
        </main>
      </div>
    </EvidenceProvider>
  );
}
