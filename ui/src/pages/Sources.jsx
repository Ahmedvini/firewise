// Data sources & DOIs: every DOI FIREWISE relies on — the 24 NASA PSI investigation datasets, their publications,
// and the references behind the physics models. All NASA DOIs come from the PSI records themselves.
import { useMemo, useState } from "react";
import { Copy, Check, Download, ExternalLink } from "lucide-react";
import { PageHeader, Metrics, Disclosure } from "../components/ui.jsx";
import { Loading, ErrorPanel, Empty } from "../components/States.jsx";
import { useApi } from "../services/api.js";

function CopyDoi({ doi }) {
  const [done, setDone] = useState(false);
  return (
    <button className="icon-btn" title={`Copy DOI ${doi}`} aria-label={`Copy DOI ${doi}`}
      onClick={() => { navigator.clipboard?.writeText(`https://doi.org/${doi}`).then(() => { setDone(true); setTimeout(() => setDone(false), 1500); }).catch(() => {}); }}>
      {done ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

const Doi = ({ doi }) => (
  <span className="doi">
    <a href={`https://doi.org/${doi}`} target="_blank" rel="noreferrer" className="mono">doi:{doi}</a><CopyDoi doi={doi} />
  </span>
);

function csv(data) {
  const rows = [["type", "investigation_id", "acronym", "title", "doi", "doi_url"]];
  for (const d of data.datasets) {
    rows.push(["dataset", d.investigation_id, d.acronym ?? "", d.title, d.doi ?? "", d.doi_url ?? ""]);
    for (const p of d.publications) rows.push(["publication", d.investigation_id, d.acronym ?? "", p.title, p.doi, p.doi_url]);
  }
  for (const m of data.method_references) rows.push(["method_reference", "", "", m.citation, m.doi ?? "", m.doi_url ?? ""]);
  return rows.map((r) => r.map((x) => `"${String(x).replaceAll('"', '""')}"`).join(",")).join("\n");
}

export default function Sources({ onOpenExperiment }) {
  const { data, error, loading, reload } = useApi("/api/citations");
  const [q, setQ] = useState("");
  const items = useMemo(() => {
    if (!data) return [];
    const t = q.trim().toLowerCase();
    return data.datasets.filter((d) => !t || `${d.investigation_id} ${d.acronym} ${d.title} ${d.doi}`.toLowerCase().includes(t)
      || d.publications.some((p) => `${p.title} ${p.authors} ${p.doi}`.toLowerCase().includes(t)));
  }, [data, q]);
  const download = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv(data)], { type: "text/csv" }));
    a.download = "firewise-dois.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  return (
    <>
      <PageHeader title="Data sources & DOIs"
        description="Every NASA dataset and publication behind FIREWISE, with its DOI. Cite the dataset DOI of each investigation you use."
        note={data?.how_to_cite}
        actions={data && <button className="btn" onClick={download}><Download /> Download all DOIs (CSV)</button>} />
      {loading && <Loading rows={6} />}
      {error && <ErrorPanel error={error} onRetry={reload} />}
      {data && (
        <>
          <Metrics items={[
            { value: data.counts.datasets, label: "NASA PSI investigation datasets" },
            { value: data.counts.dataset_dois, label: "dataset DOIs (NASA PSI)" },
            { value: data.counts.publication_dois, label: "publication DOIs listed by PSI" },
            { value: data.method_references.filter((m) => m.doi).length, label: "method-reference DOIs" },
          ]} />
          <div className="section-head"><h3>NASA PSI investigation datasets</h3>
            <input type="search" className="doi-search" placeholder="Filter by investigation, title, author or DOI" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Filter sources" /></div>
          {items.length === 0 && <Empty title="No source matches this filter.">Clear the filter to see all 24 investigations.</Empty>}
          <div className="panel table-wrap">
            <table>
              <thead><tr><th>Investigation</th><th>Dataset DOI</th><th>Licence</th><th>Publications</th></tr></thead>
              <tbody>
                {items.map((d) => (
                  <tr key={d.investigation_id}>
                    <td><button className="linkish" onClick={() => onOpenExperiment(d.investigation_id)}>{d.acronym || d.investigation_id}</button>
                      <div className="mono faint small">{d.investigation_id}</div><div className="muted small clamp2">{d.title}</div></td>
                    <td>{d.doi ? <Doi doi={d.doi} /> : <span className="missing">no DOI in the PSI record</span>}
                      <div><a className="small" href={d.psi_url} target="_blank" rel="noreferrer">PSI record <ExternalLink size={11} /></a></div></td>
                    <td className="small">{d.license ?? <span className="missing">not stated</span>}</td>
                    <td className="small">
                      {d.publications.length ? (
                        <Disclosure plain title={`${d.publications.length} publication DOI${d.publications.length === 1 ? "" : "s"}`}>
                          <ul className="plain pub-dois">
                            {d.publications.map((p) => (
                              <li key={p.doi}><span>{p.title}</span><span className="faint">{p.authors}</span><Doi doi={p.doi} /></li>
                            ))}
                          </ul>
                        </Disclosure>
                      ) : <span className="missing">none listed</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3 className="section-title">Method references (physics models)</h3>
          <ul className="plain panel method-refs">
            {data.method_references.map((m) => (
              <li key={m.citation}><b className="small">{m.use}</b><div className="small">{m.citation}</div>
                {m.doi ? <Doi doi={m.doi} /> : <span className="faint small">no DOI — cited by title</span>}</li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
