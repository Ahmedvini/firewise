// Card used in the Overview and in the Experiments list.
export default function ExperimentCard({ experiment, selected = false, onSelect, showSummary = false }) {
  return (
    <div className={`panel clickable ${selected ? "selected" : ""}`} role="button" tabIndex={0}
      onClick={() => onSelect(experiment.id)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(experiment.id)}>
      <h3>{experiment.name}</h3>
      <div className="tags">
        <span className="tag">{experiment.program}</span>
        <span className="tag">{experiment.year}</span>
        {!showSummary && <span className="tag">{experiment.type}</span>}
      </div>
      {showSummary && (
        <p className="muted">{experiment.type}. Placeholder summary until the NASA dataset is connected.</p>
      )}
    </div>
  );
}
