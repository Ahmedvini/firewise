import { Info } from "lucide-react";

// Note shown at the top of pages. Pass children to override the message.
export default function SampleBanner({ children, danger = false }) {
  return (
    <div className={`banner ${danger ? "danger" : ""}`} role="note">
      <Info size={18} />
      <span>
        {children || "Prototype: all experiments, values and summaries are placeholders. No NASA dataset or AI backend is connected."}
      </span>
    </div>
  );
}
