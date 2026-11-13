export default function StatCard({ value, label }) {
  const isText = typeof value === "string";
  return (
    <div className="panel stat-card">
      <strong className={isText ? "small" : ""}>{value}</strong>
      <span>{label}</span>
    </div>
  );
}
