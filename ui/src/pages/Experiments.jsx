import { useEffect, useMemo, useState } from "react";
import { ExternalLink } from "lucide-react";
import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import ExperimentCard from "../components/ExperimentCard.jsx";
import { EvidenceLink, useEvidence } from "../components/Evidence.jsx";
import { Quantity, StatusTag, TierTag, StatusLegend } from "../components/Tags.jsx";
import { Loading, ErrorPanel, Empty } from "../components/States.jsx";
import { useApi } from "../services/api.js";
import { FUEL_LABEL, GRANULARITY_LABEL } from "../data/constants.js";
import { rangeText, num } from "../utils/format.js";

const EMPTY_FILTERS = { search: "", fuel: "", facility: "", dataClass: "" };

function useDebounced(value, ms = 300) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

export default function Experiments({ initialSelectedId, onSelect }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [sortBy, setSortBy] = useState("id");
  const q = useDebounced(filters.search.trim());
  const params = new URLSearchParams({ limit: "500", sort: sortBy });
  if (q) params.set("q", q);
  if (filters.fuel) params.set("fuel_class", filters.fuel);
  if (filters.facility) params.set("platform", filters.facility);
  if (filters.dataClass) params.set("data_class", filters.dataClass);
  const { data, error, loading, reload } = useApi(`/api/investigations?${params}`);
  const { data: all } = useApi("/api/investigations?limit=500");
  const selectedId = initialSelectedId;
  const setFilter = (key) => (e) => setFilters({ ...filters, [key]: e.target.value });

  const options = useMemo(() => {
    const items = all?.items ?? [];
    return {
      fuel: [...new Set(items.flatMap((i) => i.fuel_classes))].sort(),
      facility: [...new Set(items.map((i) => i.facility).filter(Boolean))].sort(),
      dataClass: [...new Set(items.map((i) => i.data_class).filter(Boolean))].sort(),
    };
  }, [all]);

  return (
    <>
      <SampleBanner />
      <Header eyebrow="Investigation Explorer" title="NASA combustion investigations"
        description="Search the 24 PSI combustion investigations. Select one to see its verbatim objectives, documented test conditions with their measurement status, every test record and its NASA source." />

      <div className="filters">
        <input value={filters.search} onChange={setFilter("search")} placeholder="Search records and reports (e.g. cool flame, smoke, PMMA)" aria-label="Search investigations" />
        <select value={filters.fuel} onChange={setFilter("fuel")} aria-label="Fuel class">
          <option value="">Fuel class</option>{options.fuel.map((v) => <option key={v} value={v}>{FUEL_LABEL[v] ?? v}</option>)}
        </select>
        <select value={filters.facility} onChange={setFilter("facility")} aria-label="Facility">
          <option value="">Facility</option>{options.facility.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={filters.dataClass} onChange={setFilter("dataClass")} aria-label="PSI data class">
          <option value="">Data class</option>{options.dataClass.map((v) => <option key={v} value={v}>Class {v}</option>)}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label="Sort by">
          <option value="id">Sort: PSI id</option><option value="acronym">Sort: name</option><option value="n_records">Sort: most records</option>
        </select>
      </div>
      <div className="sort-row">
        <span className="muted small">{data ? `${data.total} of 24 investigations` : ""}</span>
        <button className="btn" onClick={() => setFilters(EMPTY_FILTERS)}>Clear filters</button>
      </div>

      <div className="split wide-detail">
        <div className="grid list-col">
          {loading && <Loading rows={5} />}
          {error && <ErrorPanel error={error} onRetry={reload} />}
          {data && data.items.length === 0 && <Empty title="No investigation matches these filters.">Clear a filter or change the search words.</Empty>}
          {data?.items.map((e) => <ExperimentCard key={e.id} experiment={e} selected={e.id === selectedId} onSelect={onSelect} />)}
        </div>
        {selectedId ? <Detail id={selectedId} /> : <div className="panel empty">Select an investigation to see its records and sources.</div>}
      </div>
    </>
  );
}

function Detail({ id }) {
  const [tab, setTab] = useState("overview");
  const { data: d, error, loading, reload } = useApi(`/api/investigations/${encodeURIComponent(id)}`);
  useEffect(() => setTab("overview"), [id]);
  if (loading) return <Loading rows={8} />;
  if (error) return <ErrorPanel error={error} onRetry={reload} />;
  if (!d) return null;
  return (
    <div className="panel detail">
      <div className="card-top">
        <h2>{d.acronym || d.id}</h2>
        <span className="mono muted small">{d.id}</span>
      </div>
      <p className="muted">{d.title}</p>
      <div className="tags">
        <a className="tag link" href={d.psi_url} target="_blank" rel="noreferrer">PSI record <ExternalLink size={11} /></a>
        {d.doi_url && <a className="tag link" href={d.doi_url} target="_blank" rel="noreferrer">DOI {d.doi} <ExternalLink size={11} /></a>}
        {d.facility && <span className="tag">{d.facility}{d.insert_hw ? ` · ${d.insert_hw}` : ""}</span>}
        <span className="tag">{d.project_type}</span>
      </div>

      <div className="tabs" role="tablist">
        {[["overview", "Overview"], ["records", `Test records (${d.n_records.toLocaleString()})`], ["sources", `Publications (${d.publications.length})`], ["data", "Data & quality"]].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      {tab === "overview" && (
        <>
          <div className="cond-grid">
            <div><span className="eyebrow">Chamber O₂</span><Quantity q={d.o2_ambient} /></div>
            <div><span className="eyebrow">Pressure</span><Quantity q={d.pressure} psia /></div>
            <div><span className="eyebrow">Airflow</span><Quantity q={d.flow} /></div>
          </div>
          {d.has_burner_stream_o2 && <p className="note small">Includes inverse flames whose O₂ value is the burner oxidizer stream — not shown as chamber O₂ and never compared with habitat atmospheres.</p>}
          <dl>
            {[["Objective", d.objective], ["Hypothesis", d.hypothesis], ["Approach", d.approach], ["Research impacts", d.research_impacts]].map(([label, f]) => f.value && (
              <div key={label}><dt>{label} <EvidenceLink id={f.evidence_id} label="PSI text" /></dt><dd className="clamp-text">{f.value}</dd></div>
            ))}
            <dt>Fuel classes</dt><dd>{d.fuel_classes.map((f) => FUEL_LABEL[f] ?? f).join(", ") || "—"}</dd>
            <dt>Record types</dt><dd>{Object.entries(d.granularity).map(([g, n]) => `${GRANULARITY_LABEL[g] ?? g}: ${n}`).join(" · ")}</dd>
            <dt>Dates (PSI record)</dt><dd>{d.start_date || "—"} → {d.end_date || "—"}</dd>
          </dl>
          {d.curated_facts.length > 0 && (
            <>
              <h4>Verified facts</h4>
              {d.curated_facts.map((f) => (
                <div className="fact" key={f.id}>
                  <TierTag tier={f.tier} /> <EvidenceLink id={f.evidence_id} />
                  <p>{f.value}</p>
                  {f.caveat && <p className="muted small">Caveat: {f.caveat}</p>}
                </div>
              ))}
            </>
          )}
          {d.relations.length > 0 && (
            <>
              <h4>Relationships</h4>
              <ul className="plain">
                {d.relations.map((r, i) => (
                  <li key={i}><span className="mono small">{r.src}</span> → <b>{r.type.replaceAll("_", " ")}</b> → <span className="mono small">{r.dst}</span>{" "}
                    <span className={`tag ${r.status === "verified" ? "green" : "amber"}`}>{r.status}</span> <span className="muted small">{r.note}</span></li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
      {tab === "records" && <Records id={d.id} />}
      {tab === "sources" && (
        d.publications.length ? (
          <ul className="plain pubs">
            {d.publications.map((p, i) => (
              <li key={i}>
                <span>{p.title}</span>
                <span className="muted small">{p.authors}</span>
                {p.doi && <a className="small" href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer">doi:{p.doi}</a>}
              </li>
            ))}
          </ul>
        ) : <Empty title="No publications listed in the PSI record." />
      )}
      {tab === "data" && (
        <dl>
          <dt>Files listed by PSI</dt><dd>{d.data_products.n_files_listed.toLocaleString()} files, {num(d.data_products.listed_gb)} GB {d.data_products.listing_complete ? "" : <span className="tag amber">record claims {num(d.data_products.total_gb)} GB but lists fewer files</span>}</dd>
          <dt>Downloaded for FIREWISE</dt><dd>{d.data_products.downloaded_files.toLocaleString()} files (≤500 MB, documents and telemetry; no video)</dd>
          <dt>Folders</dt><dd>{Object.entries(d.data_products.folders).map(([k, v]) => `${k} (${v})`).join(" · ") || "—"}</dd>
          <dt>Source tables</dt><dd>{d.source_tables.map((t) => <div key={t.id} className="mono small">{t.file_name} · {t.n_source_records} rows · sha256 {String(t.sha256).slice(0, 12)}…</div>)}</dd>
          <dt>Quality flags</dt>
          <dd>{Object.keys(d.flags_by_code).length ? Object.entries(d.flags_by_code).map(([k, v]) => <span className="tag" key={k}>{k.replaceAll("_", " ")}: {v}</span>) : "None"}</dd>
        </dl>
      )}
    </div>
  );
}

const COL_LABEL = { fuel_or_material: "Fuel / material", diluent: "Diluent", geometry: "Geometry", o2: "O₂", pressure: "Pressure", flow: "Airflow", row_granularity: "Record type", fuel_class: "Fuel class", platform: "Platform" };

function Records({ id }) {
  const [offset, setOffset] = useState(0);
  const [dups, setDups] = useState(false);
  const { open } = useEvidence();
  const limit = 50;
  const { data, error, loading, reload } = useApi(`/api/investigations/${encodeURIComponent(id)}/runs?limit=${limit}&offset=${offset}&include_duplicates=${dups}`);
  useEffect(() => setOffset(0), [id, dups]);
  if (loading && !data) return <Loading rows={6} />;
  if (error) return <ErrorPanel error={error} onRetry={reload} />;
  if (!data || data.page.total === 0) return <Empty title="No experimental table in PSI for this investigation.">Ground or modeling studies have no test records; see Publications.</Empty>;
  const vary = data.varying_columns;
  const cols = ["fuel_or_material", "o2", "pressure", "flow", "diluent", "geometry"].filter((c) => vary.includes(c) || ["o2", "pressure"].includes(c));
  return (
    <>
      <p className="muted small">
        Columns that change between tests are shown; constant values:{" "}
        {Object.entries(data.constant_columns).filter(([, v]) => v && !v.startsWith("[")).map(([k, v]) => `${COL_LABEL[k] ?? k} = ${v}`).join(" · ") || "none"}.
      </p>
      <div className="row-between">
        <label className="small"><input type="checkbox" checked={dups} onChange={(e) => setDups(e.target.checked)} style={{ width: "auto", marginRight: 6 }} />Show duplicate source rows</label>
        <span className="muted small">{data.page.total.toLocaleString()} rows</span>
      </div>
      <StatusLegend />
      <div className="table-wrap">
        <table className="dense">
          <thead><tr><th>Test</th>{cols.map((c) => <th key={c}>{COL_LABEL[c]}</th>)}<th>Outcome (as reported)</th><th>Source</th></tr></thead>
          <tbody>
            {data.page.items.map((r) => (
              <tr key={r.row_key} className={r.duplicate_of ? "dup" : ""}>
                <td className="mono small">{r.test_label ?? "—"}<div className="muted small">{GRANULARITY_LABEL[r.row_granularity]}</div>{r.duplicate_of && <span className="tag amber">duplicate</span>}</td>
                {cols.map((c) => (
                  <td key={c}>
                    {["o2", "pressure", "flow"].includes(c) ? (
                      <span className={r[c].min == null ? "missing" : ""}>
                        {rangeText(r[c], c === "pressure")}<br /><StatusTag status={r[c].status} />
                        {c === "o2" && r.o2.context === "burner_stream" && <div className="muted small">burner stream</div>}
                      </span>
                    ) : (r[c] ?? <span className="missing">—</span>)}
                  </td>
                ))}
                <td className="small">{r.outcome_text ?? "—"}{r.flags.filter((f) => f.severity === "anomaly").map((f, i) => <div key={i} className="flag">⚠ {f.message}</div>)}</td>
                <td><button className="ev-link" onClick={() => open(r.provenance.evidence_id)} title="Open the verbatim NASA row">row {r.provenance.source_row}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row-between">
        <button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button>
        <span className="muted small">{offset + 1}–{Math.min(offset + limit, data.page.total)} of {data.page.total}</span>
        <button className="btn" disabled={offset + limit >= data.page.total} onClick={() => setOffset(offset + limit)}>Next</button>
      </div>
    </>
  );
}
