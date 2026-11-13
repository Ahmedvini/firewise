import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import EmbersBackground from "./components/EmbersBackground.jsx";
import Overview from "./pages/Overview.jsx";
import AIAssistant from "./pages/AIAssistant.jsx";
import Experiments from "./pages/Experiments.jsx";
import Compare from "./pages/Compare.jsx";
import Insights from "./pages/Insights.jsx";

export default function App() {
  // The current page and the experiment chosen from the Overview are kept here
  const [page, setPage] = useState("overview");
  const [selectedExperimentId, setSelectedExperimentId] = useState(null);

  const openExperiment = (id) => {
    setSelectedExperimentId(id);
    setPage("experiments");
  };

  const pages = {
    overview: <Overview onNavigate={setPage} onOpenExperiment={openExperiment} />,
    assistant: <AIAssistant />,
    experiments: <Experiments initialSelectedId={selectedExperimentId} />,
    compare: <Compare />,
    insights: <Insights />,
  };

  return (
    <>
      <div className="bg-glow" />
      <EmbersBackground />
      <div className="app-shell">
        <Sidebar activePage={page} onNavigate={setPage} />
        <main className="main-content" key={page}>
          {pages[page]}
        </main>
      </div>
    </>
  );
}
