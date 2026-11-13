import { useState } from "react";
import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import ExperimentCard from "../components/ExperimentCard.jsx";
import { EXPERIMENTS } from "../data/sampleData.js";

const unique = (key) => [...new Set(EXPERIMENTS.map((e) => e[key]))].sort();
const EMPTY_FILTERS = { search: "", program: "", year: "", type: "", fuel: "" };

// One dropdown filter (defined outside the page so it is not re-created on every render)
function FilterSelect({ field, label, value, onChange }) {
  return (
    <select value={value} onChange={onChange} aria-label={label}>
      <option value="">{label}</option>
      {unique(field).map((v) => <option key={v} value={v}>{v}</option>)}
    </select>
  );
}

export default function Experiments({ initialSelectedId }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [sortBy, setSortBy] = useState("name");
  const [selectedId, setSelectedId] = useState(initialSelectedId);

  const setFilter = (key) => (e) => setFilters({ ...filters, [key]: e.target.value });
  const search = filters.search.toLowerCase();

  const results = EXPERIMENTS
    .filter((e) =>
      (!search || `${e.name} ${e.program} ${e.type} ${e.fuel}`.toLowerCase().includes(search)) &&
      (!filters.program || e.program === filters.program) &&
      (!filters.year || String(e.year) === filters.year) &&
      (!filters.type || e.type === filters.type) &&
      (!filters.fuel || e.fuel === filters.fuel))
    .sort((a, b) => String(a[sortBy]).localeCompare(String(b[sortBy]), undefined, { numeric: true }));

  const selected = EXPERIMENTS.find((e) => e.id === selectedId);

  return (
    <>
      <SampleBanner />
      <Header title="Explore experiments" description="Search and filter the experiment index. Select a card to see its details." />

      <div className="filters">
        <input value={filters.search} onChange={setFilter("search")} placeholder="Search experiments" aria-label="Search experiments" />
        <FilterSelect field="program" label="Program" value={filters.program} onChange={setFilter("program")} />
        <FilterSelect field="year" label="Year" value={filters.year} onChange={setFilter("year")} />
        <FilterSelect field="type" label="Type" value={filters.type} onChange={setFilter("type")} />
        <FilterSelect field="fuel" label="Fuel / material" value={filters.fuel} onChange={setFilter("fuel")} />
      </div>
      <div className="sort-row">
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label="Sort by">
          <option value="name">Sort: name</option>
          <option value="year">Sort: year</option>
          <option value="program">Sort: program</option>
        </select>
        <button className="btn" onClick={() => setFilters(EMPTY_FILTERS)}>Clear filters</button>
      </div>

      <div className="split">
        <div className="grid">
          {results.length === 0 ? (
            <div className="panel empty">No experiments match these filters. Clear a filter or change the search text.</div>
          ) : results.map((e) => (
            <ExperimentCard key={e.id} experiment={e} selected={e.id === selectedId} onSelect={setSelectedId} />
          ))}
        </div>

        {selected ? (
          <div className="panel detail">
            <h2>{selected.name} <span className="tag amber">Sample data</span></h2>
            <dl>
              <dt>Research program</dt><dd>{selected.program}, {selected.year}</dd>
              <dt>Objective</dt><dd>{selected.objective}</dd>
              <dt>Combustion conditions</dt><dd>{selected.conditions}</dd>
              <dt>Fuel / material</dt><dd>{selected.fuel}</dd>
              <dt>Important observations</dt><dd>{selected.observations}</dd>
              <dt>Source documents</dt>
              <dd className="muted">{selected.sources.length ? selected.sources.join(", ") : "None linked. Documents will be listed when the dataset is connected."}</dd>
            </dl>
          </div>
        ) : (
          <div className="panel empty">Select an experiment to see its details.</div>
        )}
      </div>
    </>
  );
}
