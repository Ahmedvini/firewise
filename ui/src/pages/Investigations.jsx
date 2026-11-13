// Investigations: browse the 24 NASA PSI combustion investigations, or compare 2–4 of them.
import { List, GitCompare } from "lucide-react";
import { PageHeader, Tabs } from "../components/ui.jsx";
import Experiments from "./Experiments.jsx";
import Compare from "./Compare.jsx";

export default function Investigations({ mode = "browse", onMode, selectedId, onSelect, onOpenExperiment }) {
  return (
    <>
      <PageHeader title="Investigations"
        description="NASA's 24 combustion investigations in the Physical Sciences Informatics (PSI) repository: what each tested, under which documented conditions, and where every value comes from." />
      <Tabs label="Investigations mode" value={mode} onChange={onMode} items={[["browse", "Browse", List], ["compare", "Compare", GitCompare]]} />
      {mode === "compare" ? <Compare onOpenExperiment={onOpenExperiment} /> : <Experiments initialSelectedId={selectedId} onSelect={onSelect} />}
    </>
  );
}
