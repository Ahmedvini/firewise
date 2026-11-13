"""Write docs/DATA_CITATIONS.md from the database (same content as /api/citations and the website's
'Data sources & DOIs' page). Usage: python3 -I scripts/export_citations.py <repo-root>"""
import os
import sqlite3
import sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, ROOT)
from api import services  # noqa: E402

con = sqlite3.connect(f"file:{os.path.join(ROOT, 'build', 'firewise.sqlite')}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
d = services.citations(con)
L = ["# FIREWISE — Data sources and DOIs", "",
     f"Generated from the FIREWISE database by `scripts/export_citations.py`. The same list is served at `/api/citations` and on the website's **Data sources & DOIs** page.",
     "", d["how_to_cite"], "",
     f"- NASA PSI investigation datasets: **{d['counts']['datasets']}** (dataset DOIs: {d['counts']['dataset_dois']})",
     f"- Publication DOIs listed in the PSI records: **{d['counts']['publication_dois']}**", "",
     "## NASA PSI investigation datasets", "", "| Investigation | Title | Dataset DOI | Licence |", "|---|---|---|---|"]
for x in d["datasets"]:
    L.append(f"| {x['investigation_id']} {x['acronym'] or ''} | {x['title']} | [{x['doi']}]({x['doi_url']}) | {x['license'] or 'not stated'} |")
L += ["", "## Method references (FIREWISE physics models)", ""]
for m in d["method_references"]:
    L.append(f"- **{m['use']}** — {m['citation']} " + (f"DOI: [{m['doi']}]({m['doi_url']})" if m["doi"] else "(no DOI; cited by title)"))
L += ["", "## Publications listed in the PSI records (by investigation)", ""]
for x in d["datasets"]:
    if not x["publications"]:
        continue
    L += [f"### {x['investigation_id']} {x['acronym'] or ''}", ""]
    for p in x["publications"]:
        L.append(f"- {p['title']}. {p['authors']}. DOI: [{p['doi']}]({p['doi_url']})")
    L.append("")
open(os.path.join(ROOT, "docs", "DATA_CITATIONS.md"), "w").write("\n".join(L) + "\n")
print(f"wrote docs/DATA_CITATIONS.md: {d['counts']}")
