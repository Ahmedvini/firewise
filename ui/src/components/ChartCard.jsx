import { ResponsiveContainer } from "recharts";

export const CHART_COLORS = ["#3987e5", "#d95926", "#199e70", "#8a93a8"];
export const tooltipStyle = {
  contentStyle: { background: "#1c2433", border: "1px solid rgba(148,163,184,.28)", borderRadius: 6, color: "#e8edf5", fontSize: 13 },
  cursor: { fill: "rgba(148,163,184,.06)" },
};

// A titled panel holding a responsive chart (pass the chart as children). `height` in px.
export default function ChartCard({ title, children, height = 260, subtitle }) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      {subtitle && <p className="small muted" style={{ margin: "4px 0 0" }}>{subtitle}</p>}
      <div className="chart-box" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
    </div>
  );
}
