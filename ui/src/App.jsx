import { Suspense, lazy, useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import { EvidenceProvider } from "./components/Evidence.jsx";
import Overview from "./pages/Overview.jsx";
import AIAssistant from "./pages/AIAssistant.jsx";
import Investigations from "./pages/Investigations.jsx";
import Scenarios from "./pages/Scenarios.jsx";
import ResearchGaps from "./pages/ResearchGaps.jsx";
import { TwinProvider } from "./twin/TwinContext.jsx";

const DigitalTwin = lazy(() => import("./twin/DigitalTwin.jsx")); // three.js loads only when the twin opens

// Routes. Old links keep working: #/compare → Investigations (compare), #/insights → Research gaps.
const PAGES = ["overview", "experiments", "compare", "scenarios", "twin", "gaps", "insights", "assistant"];
const NAV_OF = { compare: "experiments", insights: "gaps" };

function readHash() {
  const [, page, id] = window.location.hash.split("?")[0].split("/");
  return { page: PAGES.includes(page) ? page : "overview", id: id ? decodeURIComponent(id) : null };
}

export default function App() {
  const initial = readHash();
  const [page, setPage] = useState(initial.page);
  const [selectedExperimentId, setSelectedExperimentId] = useState(initial.page === "experiments" ? initial.id : null);
  const [twinTab, setTwinTab] = useState(initial.page === "twin" ? initial.id || "habitat" : "habitat");

  useEffect(() => {
    const onHash = () => {
      const h = readHash();
      setPage(h.page);
      if (h.page === "experiments" && h.id) setSelectedExperimentId(h.id);
      if (h.page === "twin") setTwinTab(h.id || "habitat");
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

  const investigations = (mode) => (
    <Investigations mode={mode} onMode={(m) => navigate(m === "compare" ? "compare" : "experiments")} selectedId={selectedExperimentId}
      onSelect={(id) => navigate("experiments", id)} onOpenExperiment={openExperiment} />
  );
  const pages = {
    overview: <Overview onNavigate={navigate} onOpenExperiment={openExperiment} />,
    experiments: investigations("browse"),
    compare: investigations("compare"),
    scenarios: <Scenarios onOpenExperiment={openExperiment} />,
    gaps: <ResearchGaps onOpenExperiment={openExperiment} onNavigate={navigate} />,
    insights: <ResearchGaps onOpenExperiment={openExperiment} onNavigate={navigate} />,
    assistant: <AIAssistant onOpenExperiment={openExperiment} />,
    twin: (
      <Suspense fallback={<div className="panel">Loading the Digital Twin…</div>}>
        <DigitalTwin tab={twinTab} onTab={(k) => { window.location.hash = `/twin/${k}`; }} onOpenExperiment={openExperiment} />
      </Suspense>
    ),
  };

  return (
    <EvidenceProvider>
      <TwinProvider>
        <a href="#main" className="skip-link" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
        <div className="app-shell">
          <Sidebar activePage={NAV_OF[page] ?? page} onNavigate={navigate} />
          <main className={`main-content ${page === "twin" ? "wide" : ""}`} key={page} id="main" tabIndex={-1}>
            {pages[page]}
          </main>
        </div>
      </TwinProvider>
    </EvidenceProvider>
  );
}
