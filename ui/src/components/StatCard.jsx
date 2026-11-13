import { EvidenceLink } from "./Evidence.jsx";

export default function StatCard({ value, label, evidence, highlight = false }) {
  const isText = typeof value === "string";
  return (
    <div className={`panel stat-card ${highlight ? "highlight" : ""}`}>
      <strong className={isText ? "small" : ""}>{typeof value === "number" ? value.toLocaleString("en-US") : value}</strong>
      <span>{label}</span>
      {evidence && <div className="stat-ev"><EvidenceLink id={evidence} label="source" /></div>}
    </div>
  );
}
