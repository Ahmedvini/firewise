import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, Legend } from "recharts";
import SampleBanner from "../components/SampleBanner.jsx";
import StatCard from "../components/StatCard.jsx";
import ChartCard, { CHART_COLORS, tooltipStyle } from "../components/ChartCard.jsx";
import ExperimentCard from "../components/ExperimentCard.jsx";
import { EXPERIMENTS, DOCUMENT_COUNT, FEATURED_EXPERIMENT_IDS } from "../data/sampleData.js";
import { countBy } from "../utils/countBy.js";

export default function Overview({ onNavigate, onOpenExperiment }) {
  const [microgravity, setMicrogravity] = useState(false);

  const byProgram = countBy(EXPERIMENTS, "program");
  const byYear = countBy(EXPERIMENTS, "year");
  const byCategory = countBy(EXPERIMENTS, "category");
  const featured = EXPERIMENTS.filter((e) => FEATURED_EXPERIMENT_IDS.includes(e.id));
  const axis = { stroke: "#A9B0C0", fontSize: 12 };

  return (
    <>
      <SampleBanner />

      <section className="hero">
        <div>
          <h1 className="hero-title">FLARE</h1>
          <p className="hero-sub">Understanding combustion in microgravity. Turning NASA research into intelligent fire safety insights.</p>
          <p className="lede">
            FLARE is a research interface for exploring NASA microgravity combustion experiments, comparing their
            conditions, and connecting findings to fire safety questions for spacecraft and future habitats.
          </p>
          <button className="btn primary" onClick={() => onNavigate("experiments")}>Explore Research</button>{" "}
          <button className="btn" onClick={() => onNavigate("assistant")}>Ask the AI Assistant</button>
        </div>

        <div className="panel stage" aria-label="Flame shape on Earth versus in microgravity">
          <div className={`flame ${microgravity ? "round" : ""}`} />
          <div className="stage-controls">
            <div className="segmented">
              <button className={!microgravity ? "on" : ""} onClick={() => setMicrogravity(false)}>Earth gravity</button>
              <button className={microgravity ? "on" : ""} onClick={() => setMicrogravity(true)}>Microgravity</button>
            </div>
            <small className="muted">Conceptual illustration, not experimental data</small>
          </div>
        </div>
      </section>

      <h2>Dataset at a glance <span className="tag amber">Sample data</span></h2>
      <div className="grid cols-4 section-gap">
        <StatCard value={EXPERIMENTS.length} label="Total experiments" />
        <StatCard value={byProgram.length} label="Research missions" />
        <StatCard value={byCategory.length} label="Combustion categories" />
        <StatCard value={DOCUMENT_COUNT ?? "Not connected"} label="Research documents" />
      </div>

      <h2>Research overview</h2>
      <div className="grid cols-3 section-gap">
        <ChartCard title="By research program">
          <BarChart data={byProgram}>
            <CartesianGrid stroke="rgba(169,176,192,.12)" vertical={false} />
            <XAxis dataKey="name" {...axis} /><YAxis allowDecimals={false} {...axis} />
            <Tooltip {...tooltipStyle} /><Bar dataKey="value" name="Experiments" fill="#FF7138" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ChartCard>
        <ChartCard title="By year">
          <BarChart data={byYear}>
            <CartesianGrid stroke="rgba(169,176,192,.12)" vertical={false} />
            <XAxis dataKey="name" {...axis} /><YAxis allowDecimals={false} {...axis} />
            <Tooltip {...tooltipStyle} /><Bar dataKey="value" name="Experiments" fill="#FFB454" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ChartCard>
        <ChartCard title="By category">
          <PieChart>
            <Pie data={byCategory} dataKey="value" nameKey="name" innerRadius="50%" outerRadius="75%" stroke="#090D16">
              {byCategory.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Pie>
            <Tooltip {...tooltipStyle} /><Legend wrapperStyle={{ fontSize: 12, color: "#A9B0C0" }} />
          </PieChart>
        </ChartCard>
      </div>

      <h2>Featured research <span className="tag amber">Sample data</span></h2>
      <div className="grid cols-4 section-gap">
        {featured.map((e) => (
          <ExperimentCard key={e.id} experiment={e} showSummary onSelect={onOpenExperiment} />
        ))}
      </div>
    </>
  );
}
