import { FUEL_LABEL } from "../data/constants.js";
import { rangeText } from "../utils/format.js";

// Compact list row for one PSI investigation: identity, fuel class, and the documented conditions.
export default function ExperimentCard({ experiment: e, selected = false, onSelect, showSummary = false }) {
  return (
    <div className={`inv-row ${selected ? "selected" : ""}`} role="button" tabIndex={0}
      onClick={() => onSelect(e.id)} onKeyDown={(ev) => (ev.key === "Enter" || ev.key === " ") && (ev.preventDefault(), onSelect(e.id))} aria-pressed={selected}>
      <div className="inv-row-top">
        <b>{e.acronym || e.id}</b>
        <span className="mono faint small">{e.id}</span>
      </div>
      <div className="muted small clamp2">{e.title}</div>
      <div className="inv-row-facts small">
        <span>{e.fuel_classes.map((f) => FUEL_LABEL[f] ?? f).join(", ") || "—"}</span>
        <span className="tnum">{e.n_records.toLocaleString()} records</span>
        {!showSummary && <>
          <span className={e.o2_ambient.min == null ? "missing" : "tnum"}>O₂ {rangeText(e.o2_ambient)}</span>
          <span className={e.pressure.min == null ? "missing" : "tnum"}>P {rangeText(e.pressure, true)}</span>
        </>}
      </div>
    </div>
  );
}
