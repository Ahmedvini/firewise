import { ResponsiveContainer } from "recharts";

// Colors and tooltip style shared by all charts
export const CHART_COLORS = ["#FF7138", "#FFB454", "#d9985f", "#c4552a", "#8a93a8"];
export const tooltipStyle = {
  contentStyle: { background: "#111827", border: "1px solid rgba(169,176,192,.25)", borderRadius: 8, color: "#F5F7FA" },
  cursor: { fill: "rgba(255,113,56,.08)" },
};

// A titled card that holds a responsive chart (pass the chart as children).
export default function ChartCard({ title, children }) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <div className="chart-box">
        <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer>
      </div>
    </div>
  );
}
