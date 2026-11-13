import { FUEL_LABEL } from "../data/constants.js";
import { rangeText } from "../utils/format.js";

// Card for one PSI investigation (Overview and Investigations list).
export default function ExperimentCard({ experiment: e, selected = false, onSelect, showSummary = false }) {
  return (
    <div className={`panel clickable ${selected ? "selected" : ""}`} role="button" tabIndex={0}
      onClick={() => onSelect(e.id)} onKeyDown={(ev) => ev.key === "Enter" && onSelect(e.id)} aria-pressed={selected}>
      <div className="card-top"><h3>{e.acronym || e.id}</h3><span className="mono muted small">{e.id}</span></div>
      <p className="muted small clamp2">{e.title}</p>
      <div className="tags">
        {e.facility && <span className="tag">{e.facility}</span>}
        {e.fuel_classes.slice(0, 2).map((f) => <span className="tag" key={f}>{FUEL_LABEL[f] ?? f}</span>)}
        <span className={`tag ${e.data_class === "A" ? "green" : e.data_class === "C" ? "amber" : ""}`} title="PSI data class: A raw/telemetry · B analyzed · C summary table only · D metadata only">Data class {e.data_class ?? "—"}</span>
      </div>
      {showSummary ? (
        <p className="muted small">{e.n_records.toLocaleString()} records · O₂ {rangeText(e.o2_ambient)} · P {rangeText(e.pressure, true)}</p>
      ) : (
        <dl className="mini">
          <div><dt>Records</dt><dd>{e.n_records.toLocaleString()}{e.n_duplicates ? <span className="muted small"> (+{e.n_duplicates} duplicates)</span> : null}</dd></div>
          <div><dt>Chamber O₂</dt><dd className={e.o2_ambient.min == null ? "missing" : ""}>{rangeText(e.o2_ambient)}</dd></div>
          <div><dt>Pressure</dt><dd className={e.pressure.min == null ? "missing" : ""}>{rangeText(e.pressure, true)}</dd></div>
        </dl>
      )}
    </div>
  );
}
