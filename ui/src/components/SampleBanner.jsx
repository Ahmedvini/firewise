import { Info } from "lucide-react";

// Provenance / caution note shown at the top of pages. Pass children to override the message.
export default function SampleBanner({ children, danger = false }) {
  return (
    <div className={`banner ${danger ? "danger" : ""}`} role="note">
      <Info size={18} />
      <span>
        {children || "All values come from NASA PSI investigation records and experimental tables. Each value carries its status: measured, derived, reported, set-point or not documented — missing values are never treated as zero."}
      </span>
    </div>
  );
}
