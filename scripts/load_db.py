#!/usr/bin/env python3
"""Build the canonical FIREWISE database (FINAL_DATA_CONTRACT.md, schema_version 1).

Usage: python3 -I scripts/load_db.py <NasaSA root> [--out build/firewise.sqlite] [--no-pdfs]
Exit 0 = valid database written. Any validation failure aborts with a non-zero exit and a message naming the rule.
Inputs are read-only. The output file is rebuilt from scratch (atomic replace) on every run.
"""
import csv, datetime, glob, hashlib, importlib.util, json, os, re, sqlite3, subprocess, sys

SCHEMA_VERSION = 1
ROOT = os.path.abspath(sys.argv[1])
OUT = os.path.join(ROOT, sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else os.path.join(ROOT, "build", "firewise.sqlite")
WITH_PDFS = "--no-pdfs" not in sys.argv
P = lambda *a: os.path.join(ROOT, *a)


class BuildError(Exception):
    pass


def fail(rule, detail):
    raise BuildError(f"[{rule}] {detail}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, P("scripts", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DDL = """
PRAGMA foreign_keys = ON;
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE investigation (
  id TEXT PRIMARY KEY CHECK (id GLOB 'PSI-[0-9]*'), acronym TEXT, title TEXT NOT NULL, doi TEXT, psi_url TEXT NOT NULL,
  license TEXT, project_type TEXT NOT NULL, platform TEXT, hardware TEXT, sub_research_area TEXT,
  start_date TEXT, end_date TEXT, objective TEXT, hypothesis TEXT, approach TEXT, research_impacts TEXT,
  n_files_listed INTEGER NOT NULL, listed_gb REAL NOT NULL, total_gb REAL NOT NULL,
  listing_complete INTEGER NOT NULL CHECK (listing_complete IN (0,1)), record_sha256 TEXT NOT NULL);
CREATE TABLE investigation_meta (
  investigation_id TEXT PRIMARY KEY REFERENCES investigation(id),
  data_class TEXT NOT NULL CHECK (data_class IN ('A','B','C','D','E')), facility TEXT, insert_hw TEXT,
  primary_fuel_class TEXT, source TEXT NOT NULL);
CREATE TABLE source_table (
  id TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigation(id), file_name TEXT NOT NULL,
  local_path TEXT NOT NULL, sha256 TEXT NOT NULL, source_url TEXT NOT NULL, n_source_records INTEGER NOT NULL);
CREATE TABLE run (
  row_key TEXT PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigation(id),
  source_table_id TEXT NOT NULL REFERENCES source_table(id), source_row INTEGER NOT NULL CHECK (source_row >= 2),
  test_label TEXT, row_granularity TEXT NOT NULL CHECK (row_granularity IN ('test','test_point','test_day',
    'test_day_o2_level','test_date','condition_envelope','session','material_condition_set','flow_visualization','figure_reference')),
  duplicate_of TEXT REFERENCES run(row_key), date_text TEXT, fuel_or_material TEXT,
  fuel_class TEXT NOT NULL CHECK (fuel_class IN ('gaseous','solid_emulating_gas_burner','liquid_droplet','solid',
    'smoke_source_nonflaming','dust_aerosol','none')), fuel_class_detail TEXT, geometry TEXT, diluent TEXT,
  gravity_regime TEXT NOT NULL CHECK (gravity_regime IN ('microgravity','normal_gravity','partial_gravity')),
  platform TEXT NOT NULL,
  o2_min_pct REAL, o2_max_pct REAL, o2_status TEXT NOT NULL, o2_context TEXT,
  p_min_atm REAL, p_max_atm REAL, p_status TEXT NOT NULL, p_context TEXT,
  flow_min_cm_s REAL, flow_max_cm_s REAL, flow_status TEXT NOT NULL, flow_context TEXT,
  outcome_text TEXT, raw_json TEXT NOT NULL,
  CHECK (o2_status IN ('measured','derived','reported','specified','missing')),
  CHECK (p_status IN ('measured','derived','reported','specified','missing')),
  CHECK (flow_status IN ('measured','derived','reported','specified','missing')),
  CHECK ((o2_min_pct IS NULL) = (o2_status = 'missing')),
  CHECK ((p_min_atm IS NULL) = (p_status = 'missing')),
  CHECK ((flow_min_cm_s IS NULL) = (flow_status = 'missing')),
  CHECK (o2_min_pct IS NULL OR (o2_min_pct >= 0 AND o2_max_pct <= 100 AND o2_min_pct <= o2_max_pct)),
  CHECK (p_min_atm IS NULL OR (p_min_atm > 0 AND p_min_atm <= p_max_atm)),
  CHECK (o2_context IS NULL OR o2_context IN ('ambient','burner_stream','envelope')));
CREATE INDEX run_inv ON run(investigation_id);
CREATE INDEX run_o2 ON run(o2_context, o2_min_pct, o2_max_pct);
CREATE INDEX run_p ON run(p_min_atm, p_max_atm);
CREATE TABLE observation (
  row_key TEXT NOT NULL REFERENCES run(row_key), variable TEXT NOT NULL, value_num REAL, value_text TEXT, unit TEXT,
  status TEXT NOT NULL CHECK (status IN ('measured','derived','reported','specified','missing')),
  gravity_regime TEXT NOT NULL, source_column TEXT NOT NULL, PRIMARY KEY (row_key, variable, gravity_regime));
CREATE TABLE quality_flag (
  id INTEGER PRIMARY KEY, row_key TEXT NOT NULL REFERENCES run(row_key), investigation_id TEXT NOT NULL REFERENCES investigation(id),
  severity TEXT NOT NULL CHECK (severity IN ('anomaly','limitation','note')), code TEXT NOT NULL, message TEXT NOT NULL);
CREATE INDEX flag_row ON quality_flag(row_key);
CREATE TABLE publication (id INTEGER PRIMARY KEY, investigation_id TEXT NOT NULL REFERENCES investigation(id),
  title TEXT NOT NULL, authors TEXT, doi TEXT, status TEXT);
CREATE TABLE data_file (investigation_id TEXT NOT NULL REFERENCES investigation(id), folder TEXT, file_name TEXT NOT NULL,
  bytes INTEGER, ext TEXT, downloaded INTEGER NOT NULL DEFAULT 0, local_path TEXT, sha256 TEXT,
  PRIMARY KEY (investigation_id, file_name));
CREATE TABLE relation (id INTEGER PRIMARY KEY, src TEXT NOT NULL, dst TEXT NOT NULL, type TEXT NOT NULL,
  evidence_id TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('verified','inferred')), note TEXT);
CREATE TABLE claim (id TEXT PRIMARY KEY, field TEXT, value TEXT NOT NULL, status TEXT, tier TEXT NOT NULL,
  source TEXT NOT NULL, confidence TEXT, caveat TEXT);
CREATE TABLE claim_investigation (claim_id TEXT REFERENCES claim(id), investigation_id TEXT, PRIMARY KEY (claim_id, investigation_id));
CREATE TABLE aggregate (name TEXT PRIMARY KEY, description TEXT NOT NULL, definition TEXT NOT NULL, value_json TEXT NOT NULL);
CREATE TABLE coverage_cell (gravity_regime TEXT, fuel_class TEXT, o2_band TEXT, p_band TEXT, records INTEGER NOT NULL,
  investigations TEXT, PRIMARY KEY (gravity_regime, fuel_class, o2_band, p_band));
CREATE TABLE document_page (evidence_id TEXT PRIMARY KEY, investigation_id TEXT REFERENCES investigation(id),
  file_name TEXT NOT NULL, local_path TEXT NOT NULL, sha256 TEXT NOT NULL, page INTEGER NOT NULL, text TEXT NOT NULL);
CREATE VIRTUAL TABLE passage USING fts5(evidence_id UNINDEXED, investigation_id UNINDEXED, kind UNINDEXED, title, text,
  tokenize = 'porter unicode61');
"""

# --------------------------------------------------------------------------- observation extraction (P0 map)
def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def obs_for(run):
    """Return [(variable, value_num, value_text, unit, status, gravity_regime, source_column)] from the raw row."""
    acc, x, out = run["investigation"], json.loads(run["raw"]), []

    def add(var, col, unit, status, g="microgravity", text_ok=True, keep_blank=None):
        if col not in x:
            return
        v = (x.get(col) or "").strip()
        if not v or v.lower() in ("n/a", "na", "-", "none"):
            if keep_blank:
                out.append((var, None, keep_blank, unit, "missing", g, col))
            return
        n = _num(v)
        if n is None and "�" in v:
            return
        out.append((var, n, None if n is not None else (v if text_ok else None), unit, status, g, col))

    if acc == "PSI-69":
        add("droplet_d0_mm", "Droplet initial diameter; mm", "mm", "measured")
        add("extinction_d_mm", "Visible flame extinction diameter; mm", "mm", "measured")
        add("burning_rate", "Burning rate; mm", "as in PSI header ('mm'; unit unverified)", "measured")
        add("burn_time_s", "Burn time; s", "s", "measured")
        add("test_end", "Test end", None, "measured")
    elif acc == "PSI-159":
        if "Cool flame?" in x:
            add("cool_flame", "Cool flame?", None, "measured", keep_blank="not_recorded")
        add("hot_ignition", "Hot ignition", None, "measured")
        add("burn_time_s", "burn time (sec)", "s", "measured")
        add("end_mode", "Self-ext or flow term", None, "measured")
        add("end_mode", "Self -ext or flow term", None, "measured")
        add("tad_K", "Tad (K)", "K", "derived")
        add("zst", "Zst", "-", "derived")
        add("peak_burner_T_C", "Peak burner T (C )", "C", "measured")
        add("peak_burner_T_C", "Peak burner Temp (C)", "C", "measured")
    elif acc == "PSI-10":
        add("tad_K", "Tad (K)", "K", "derived")
        add("zst", "mean Zst", "-", "derived")
    elif acc in ("PSI-98", "PSI-99", "PSI-100"):
        for col in x:
            c = col.strip().lower()
            if c.startswith("burn time"):
                add("burn_time", col, None, "reported")
            elif c.startswith("flow direction") or c == "direction":
                add("flow_direction", col, None, "specified")
            elif c.startswith("?-g burn length"):
                add("burn_length", col, None, "reported", "microgravity")
            elif c.startswith("?-g spread"):
                add("spread", col, None, "reported", "microgravity")
            elif c.startswith("1-g burn length"):
                add("burn_length", col, None, "reported", "normal_gravity")
            elif c.startswith("1-g spread"):
                add("spread", col, None, "reported", "normal_gravity")
    elif acc == "PSI-25":
        add("o2_final_pct", "Calibrated final O2 % by vol", "%", "measured")
        add("co2_initial_pct", "Initial CO2 % by vol", "%", "measured")
        add("co2_final_pct", "Final CO2 % by vol", "%", "measured")
        add("co_initial_ppm", "Initial CO (ppm)", "ppm", "measured")
        add("co_final_ppm", "Final CO (ppm)", "ppm", "measured")
    elif acc == "PSI-102":
        add("weight_loss_mg_min", "Weight loss rate (mg/min)", "mg/min", "measured")
        add("aging_min", "Aging Duration (minutes)", "min", "specified")
    elif acc == "PSI-101":
        add("rt_r0", "Rt/R0", "- (meaning unverified)", "reported")
        add("duration_s", "Duration (sec)", "s", "specified")
        add("net_aging_s", "Net aging time (sec)", "s", "reported")
    elif acc == "PSI-107":
        add("fuel_rate_sccm", "Fuel Rate (sccm)", "sccm", "specified")
        add("fuel_rate_mg_s", "Fuel Rate (mg/s)", "mg/s", "specified")
        add("nozzle_mm", "Nozzle (mm)", "mm", "specified")
    if acc in ("PSI-20", "PSI-21", "PSI-22", "PSI-23"):
        for col in ("Flames Ignited", "Flames ignited", "Flames Ignited*"):
            add("flames_ignited_that_day", col, "count", "reported")
    # de-duplicate by (variable, gravity) keeping first non-missing
    seen, final = set(), []
    for o in out:
        k = (o[0], o[5])
        if k not in seen:
            seen.add(k); final.append(o)
    return final


RELATIONS = [  # (src, dst, type, evidence_id, status, note)
    ("PSI-47", "PSI-102", "qualified_instrument_for", "inv:PSI-47#objective", "verified",
     "DAFT/DAFT-2 tested a modified TSI P-Trak (vs DustTrak control) to mitigate risk for SAME"),
    ("PSI-101", "PSI-102", "reflight_of", "inv:PSI-101#objective", "verified", "SAME-R re-flew SAME after TEM grid contamination"),
    ("PSI-39", "PSI-69", "shares_test_number_series", "fact:F11", "inferred",
     "CFI test IDs are a 'Flex Number' series (1206-1387); FLEX tests 1-274; intervening numbers undocumented"),
    ("PSI-25", "PSI-26", "follow_on_of", "inv:PSI-25#objective", "verified", "BASS-II continues BASS objectives"),
    ("PSI-99", "PSI-98", "follow_on_of", "inv:PSI-99#objective", "verified", "Saffire series"),
    ("PSI-100", "PSI-99", "follow_on_of", "inv:PSI-100#objective", "verified", "Saffire series"),
] + [(a, "ACME", "uses_insert", f"inv:{a}#hardware", "verified", "ACME insert in the Combustion Integrated Rack")
     for a in ("PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159")] + \
    [(a, "MDCA", "uses_insert", f"inv:{a}#hardware", "verified", "Multi-user Droplet Combustion Apparatus in the CIR")
     for a in ("PSI-39", "PSI-68", "PSI-69")] + \
    [(a, "MSG", "uses_facility", f"inv:{a}#hardware", "verified", "Microgravity Science Glovebox")
     for a in ("PSI-25", "PSI-26", "PSI-107")]


def pdf_pages(path):
    try:
        info = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=60).stdout
        n = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    except Exception:
        return []
    pages = []
    for i in range(1, min(n, 400) + 1):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), path, "-"],
                           capture_output=True, text=True, timeout=60).stdout
        t = re.sub(r"[ \t]+", " ", t).strip()
        if len(t) > 40:
            pages.append((i, t))
    return pages


def main():
    cov = load_module("coverage")
    claims = json.load(open(P("derived/claims_check.json")))
    runs = list(csv.DictReader(open(P("derived/runs.csv"))))
    flags = list(csv.DictReader(open(P("derived/runs_flags.csv"))))
    manifest = {}
    for m in csv.DictReader(open(P("sources/sources.csv"))):
        manifest[m["path"]] = m  # later rows win (re-fetch)
    meta_rows = json.load(open(P("derived/investigation_meta.json")))
    facts = json.load(open(P("derived/curated_facts.json")))
    psi_files = list(csv.DictReader(open(P("derived/psi_files.csv"))))
    summ = {r["accession"]: r for r in csv.DictReader(open(P("derived/psi_summary.csv")))}

    # Rule 7: original data untouched
    chk = subprocess.run([sys.executable, "-I", P("scripts/checksum_data.py"), P("Data"), P("derived/data_sha256.txt"), "--verify"],
                         capture_output=True, text=True)
    if chk.returncode != 0:
        fail("R7-originals", chk.stdout + chk.stderr)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.executescript(DDL)
    inputs = {}
    with db:
        # ---------------------------------------------------------------- investigations
        recs = sorted(glob.glob(P("sources/psi_api/PSI-*.json")), key=lambda p: int(re.findall(r"\d+", os.path.basename(p))[0]))
        for path in recs:
            d = json.load(open(path))
            acc = d["accession"]
            s = summ.get(acc, {})
            clean = lambda k: re.sub(r"\s+", " ", str(d.get(k) or "")).strip() or None
            rel = os.path.relpath(path, ROOT)
            rec_sha = sha256(path)
            if rel in manifest and manifest[rel]["sha256"] != rec_sha:
                fail("R1-provenance", f"{rel} sha256 differs from sources.csv")
            inputs[rel] = rec_sha
            db.execute("INSERT INTO investigation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                acc, clean("investigationAcronym"), clean("title"), clean("doi"),
                f"https://psi.nasa.gov/physci/repo/data/investigations/{acc}", clean("licenseIdentifier"),
                clean("projectType") or "unknown", clean("flightProgram"), clean("experimentHardware"), clean("subResearchArea"),
                clean("investigationStartDate"), clean("investigationEndDate"), clean("objective"), clean("hypothesis"),
                clean("approach"), clean("researchImpacts"), int(s.get("n_files_listed") or 0), float(s.get("listed_GB") or 0),
                float(s.get("totalFileSize_GB") or 0), 1 if s.get("listing_complete") == "True" else 0, rec_sha))
            for p in d.get("publications") or []:
                db.execute("INSERT INTO publication (investigation_id,title,authors,doi,status) VALUES (?,?,?,?,?)",
                           (acc, re.sub(r"\s+", " ", p.get("title") or "").strip() or "(untitled)", (p.get("authorList") or "").strip(),
                            (p.get("doi") or "").strip() or None, (p.get("status") or {}).get("annotationValue")))
        for m in meta_rows:
            db.execute("INSERT INTO investigation_meta VALUES (?,?,?,?,?,?)",
                       (m["investigation_id"], m["data_class"], m["facility"], m["insert_hw"], m["primary_fuel_class"], m["source"]))
        downloaded = {}
        for path, m in manifest.items():
            if path.startswith("sources/psi_files/"):
                downloaded[(path.split("/")[2], os.path.basename(path))] = m
        for f in sorted(psi_files, key=lambda r: (int(r["accession"][4:]), r["file_name"])):
            m = downloaded.get((f["accession"], f["file_name"]))
            db.execute("INSERT OR IGNORE INTO data_file VALUES (?,?,?,?,?,?,?,?)",
                       (f["accession"], f["folder"], f["file_name"], int(f["bytes"]), f["ext"], 1 if m else 0,
                        m["path"] if m else None, m["sha256"] if m else None))

        # ---------------------------------------------------------------- source tables
        tables = {}
        for r in runs:
            tables.setdefault(r["source_table_id"], (r["investigation"], r["source_file"]))
        for tid, (acc, fname) in sorted(tables.items()):
            rel = f"sources/psi_files/{acc}/Experimental table/{fname}"
            m = manifest.get(rel)
            if m is None:
                fail("R1-provenance", f"{rel} not in sources/sources.csv")
            actual = sha256(P(rel))
            if actual != m["sha256"]:
                fail("R1-provenance", f"{rel} sha256 {actual[:12]} != manifest {m['sha256'][:12]}")
            inputs[rel] = actual
            with open(P(rel), encoding="utf-8-sig", errors="replace", newline="") as fh:
                n_rec = sum(1 for _ in csv.reader(fh))
            db.execute("INSERT INTO source_table VALUES (?,?,?,?,?,?,?)", (tid, acc, fname, rel, actual, m["url"], n_rec))

        # ---------------------------------------------------------------- runs (sorted, duplicates point backwards)
        fnum = lambda v: float(v) if v not in ("", None) else None
        nn = lambda v: v if v not in ("", None) else None
        for r in sorted(runs, key=lambda r: (r["duplicate_of"] != "", r["row_key"])):
            db.execute("INSERT INTO run VALUES (" + ",".join("?" * 29) + ")", (
                r["row_key"], r["investigation"], r["source_table_id"], int(r["source_row"]), nn(r["test_label"]),
                r["row_granularity"], nn(r["duplicate_of"]), nn(r["date"]), nn(r["fuel_or_material"]), r["fuel_class"],
                nn(r["fuel_class_detail"]), nn(r["geometry"]), nn(r["diluent"]), r["gravity_regime"], r["platform"],
                fnum(r["o2_min_pct"]), fnum(r["o2_max_pct"]), r["o2_status"], nn(r["o2_context"]),
                fnum(r["p_min_atm"]), fnum(r["p_max_atm"]), r["p_status"], nn(r["p_context"]),
                fnum(r["flow_min_cm_s"]), fnum(r["flow_max_cm_s"]), r["flow_status"], nn(r["flow_context"]),
                nn(r["outcome"]), r["raw"]))
            for (var, vnum, vtext, unit, status, g, col) in obs_for(r):
                db.execute("INSERT OR IGNORE INTO observation VALUES (?,?,?,?,?,?,?,?)", (r["row_key"], var, vnum, vtext, unit, status, g, col))
        for i, fl in enumerate(sorted(flags, key=lambda f: (f["row_key"], f["code"], f["message"]))):
            db.execute("INSERT INTO quality_flag VALUES (?,?,?,?,?,?)",
                       (i + 1, fl["row_key"], fl["investigation"], fl["severity"], fl["code"], fl["message"]))

        # ---------------------------------------------------------------- relations, claims
        for i, (s_, d_, t, ev, st, note) in enumerate(RELATIONS):
            db.execute("INSERT INTO relation VALUES (?,?,?,?,?,?,?)", (i + 1, s_, d_, t, ev, st, note))
        tier_map = {"Lit": "literature"}
        for fct in sorted(facts, key=lambda x: x["id"]):
            tag = fct.get("tag", "")
            tier = "literature" if tag.strip() == "Lit" else ("interpretation" if "Inf" in tag else
                                                               ("measured" if fct.get("status") == "measured" else "reported"))
            db.execute("INSERT INTO claim VALUES (?,?,?,?,?,?,?,?)", (fct["id"], fct.get("field"), fct["value"], fct.get("status"),
                       tier, fct.get("source", ""), fct.get("confidence"), fct.get("caveat")))
            for inv in fct.get("investigations", []):
                db.execute("INSERT INTO claim_investigation VALUES (?,?)", (fct["id"], inv))

        # ---------------------------------------------------------------- aggregates (SQL-defined, server-computed)
        base_where = "fuel_class != 'none' AND duplicate_of IS NULL"
        aggs = {
            "investigations_total": ("PSI combustion investigation records", "SELECT COUNT(*) FROM investigation"),
            "investigations_with_tables": ("investigations with a PSI experimental table", "SELECT COUNT(DISTINCT investigation_id) FROM run"),
            "condition_records": ("combustion/aerosol condition records (all granularities, incl. duplicates)",
                                  "SELECT COUNT(*) FROM run WHERE row_granularity NOT IN ('flow_visualization','figure_reference')"),
            "unique_individual_tests": ("individual tests, exact duplicates excluded",
                                        "SELECT COUNT(*) FROM run WHERE row_granularity='test' AND duplicate_of IS NULL"),
            "duplicate_records": ("exact duplicate source records (marked, not deleted)", "SELECT COUNT(*) FROM run WHERE duplicate_of IS NOT NULL"),
            "partial_gravity_records": ("records in partial gravity", "SELECT COUNT(*) FROM run WHERE gravity_regime='partial_gravity'"),
            "solid_records": ("solid-material tests", f"SELECT COUNT(*) FROM run WHERE {base_where} AND fuel_class='solid'"),
            "solid_with_pressure": ("solid tests documenting chamber pressure", f"SELECT COUNT(*) FROM run WHERE {base_where} AND fuel_class='solid' AND p_min_atm IS NOT NULL"),
            "solid_with_o2": ("solid tests documenting O2", f"SELECT COUNT(*) FROM run WHERE {base_where} AND fuel_class='solid' AND o2_min_pct IS NOT NULL"),
            "solid_o2_max_pct": ("maximum documented O2 for solid tests (%)", f"SELECT MAX(o2_max_pct) FROM run WHERE {base_where} AND fuel_class='solid'"),
            "anomaly_flags": ("source-data anomaly flags", "SELECT COUNT(*) FROM quality_flag WHERE severity='anomaly'"),
            "rows_with_anomaly": ("records with at least one anomaly", "SELECT COUNT(DISTINCT row_key) FROM quality_flag WHERE severity='anomaly'"),
            "cfig_cool_flame_yes": ("CFI-G normal-flame tests marked cool flame = yes",
                                    "SELECT COUNT(*) FROM observation o JOIN run r USING(row_key) WHERE r.investigation_id='PSI-159' AND o.variable='cool_flame' AND lower(o.value_text) LIKE 'yes%'"),
            "cfig_cool_flame_not_recorded": ("CFI-G normal-flame tests with cool-flame field blank (not recorded)",
                                             "SELECT COUNT(*) FROM observation o JOIN run r USING(row_key) WHERE r.investigation_id='PSI-159' AND o.variable='cool_flame' AND o.value_text='not_recorded'"),
            "inverse_flame_records": ("inverse-flame records whose O2 is the burner stream", "SELECT COUNT(*) FROM run WHERE o2_context='burner_stream'"),
        }
        for name, (desc, sql) in sorted(aggs.items()):
            val = db.execute(sql).fetchone()[0]
            db.execute("INSERT INTO aggregate VALUES (?,?,?,?)", (name, desc, sql, json.dumps(val)))
        for sid, ((olo, ohi), (plo, phi)) in cov.SCENARIOS.items():
            sel = [r for r in runs if r["fuel_class"] != "none" and not r["duplicate_of"] and cov.in_window(r, ((olo, ohi), (plo, phi)))]
            val = {"records": len(sel), "by_investigation": {k: sum(1 for r in sel if r["investigation"] == k) for k in sorted({r["investigation"] for r in sel})}}
            db.execute("INSERT INTO aggregate VALUES (?,?,?,?)", (f"scenario:{sid}",
                       f"records with documented ambient O2 in {olo}-{ohi}% AND pressure in {plo}-{phi} psia (midpoints)",
                       "coverage.in_window over non-duplicate combustion records; ambient O2 only", json.dumps(val)))

        # ---------------------------------------------------------------- coverage cells
        cells = {}
        for r in runs:
            if r["fuel_class"] == "none" or r["duplicate_of"]:
                continue
            k = (r["gravity_regime"], r["fuel_class"], cov.band(cov.ambient_o2(r), cov.O2_BANDS), cov.band(cov.p_psia(r), cov.P_BANDS))
            cells.setdefault(k, []).append(r["investigation"])
        for k in sorted(cells):
            invs = cells[k]
            db.execute("INSERT INTO coverage_cell VALUES (?,?,?,?,?,?)",
                       (*k, len(invs), ";".join(f"{a}:{invs.count(a)}" for a in sorted(set(invs), key=lambda a: int(a[4:])))))

        # ---------------------------------------------------------------- full-text passages
        for (acc, title, obj, hyp, appr, imp) in db.execute(
                "SELECT id, title, objective, hypothesis, approach, research_impacts FROM investigation ORDER BY id").fetchall():
            for field, txt in (("objective", obj), ("hypothesis", hyp), ("approach", appr), ("research_impacts", imp)):
                if txt:
                    db.execute("INSERT INTO passage VALUES (?,?,?,?,?)", (f"inv:{acc}#{field}", acc, "record_text", f"{acc} {title} — {field}", txt))
        for fct in sorted(facts, key=lambda x: x["id"]):
            db.execute("INSERT INTO passage VALUES (?,?,?,?,?)", (f"fact:{fct['id']}", (fct.get("investigations") or [None])[0],
                       "curated_fact", fct.get("field", ""), fct["value"]))
        groups = db.execute("""SELECT investigation_id, fuel_class, COALESCE(fuel_or_material,''), COALESCE(diluent,''), COUNT(*),
              MIN(o2_min_pct), MAX(o2_max_pct), GROUP_CONCAT(DISTINCT o2_status), GROUP_CONCAT(DISTINCT o2_context),
              MIN(p_min_atm), MAX(p_max_atm), GROUP_CONCAT(DISTINCT p_status), MIN(row_key)
              FROM run WHERE duplicate_of IS NULL AND fuel_class != 'none'
              GROUP BY investigation_id, fuel_class, COALESCE(fuel_or_material,''), COALESCE(diluent,'')
              ORDER BY investigation_id, MIN(row_key)""").fetchall()
        for (acc, fc, fuel, dil, n, o2lo, o2hi, o2st, o2ctx, plo, phi, pst, first) in groups:
            o2 = f"O2 {o2lo:g}-{o2hi:g}% ({o2st}; {o2ctx})" if o2lo is not None else "O2 not documented"
            pr = f"pressure {plo:.3g}-{phi:.3g} atm ({pst})" if plo is not None else "pressure not documented"
            txt = f"{acc}: {n} records of {fuel or fc}{(' with ' + dil) if dil else ''} ({fc}); {o2}; {pr}."
            gid = hashlib.sha1(f"{acc}|{fc}|{fuel}|{dil}".encode()).hexdigest()[:10]
            db.execute("INSERT INTO passage VALUES (?,?,?,?,?)", (f"group:{acc}:{gid}", acc, "run_group", f"{acc} {fuel}", txt))
        for (name, desc, val) in db.execute("SELECT name, description, value_json FROM aggregate ORDER BY name").fetchall():
            db.execute("INSERT INTO passage VALUES (?,?,?,?,?)", (f"agg:{name}", None, "aggregate", name, f"{desc}: {val}"))
        n_pages = 0
        if WITH_PDFS:
            pdfs = sorted(p for p in glob.glob(P("sources/psi_files/PSI-*/*/*.pdf"))
                          if os.path.basename(os.path.dirname(p)) in ("Reports", "Science Documents"))
            for pdf in pdfs:
                rel = os.path.relpath(pdf, ROOT)
                m = manifest.get(rel)
                if m is None or int(m["bytes"]) != os.path.getsize(pdf):
                    continue  # incomplete or unmanifested download: never index
                acc = rel.split("/")[2]
                h = m["sha256"]
                inputs[rel] = h
                for page, text in pdf_pages(pdf):
                    eid = f"pdf:{h[:12]}#p{page}"
                    db.execute("INSERT OR IGNORE INTO document_page VALUES (?,?,?,?,?,?,?)", (eid, acc, os.path.basename(pdf), rel, h, page, text))
                    db.execute("INSERT INTO passage VALUES (?,?,?,?,?)", (eid, acc, "report_page", f"{os.path.basename(pdf)} p.{page}", text[:20000]))
                    n_pages += 1

        # ---------------------------------------------------------------- validation (contract §8)
        q = lambda sql: db.execute(sql).fetchone()[0]
        fk = db.execute("PRAGMA foreign_key_check").fetchall()
        if fk:
            fail("R4-integrity", f"{len(fk)} foreign key violations, first: {fk[0]}")
        if q("SELECT COUNT(*) FROM quality_flag WHERE row_key NOT IN (SELECT row_key FROM run)"):
            fail("R4-orphan-flags", "quality flags reference unknown records")
        if q("SELECT COUNT(*) FROM run WHERE investigation_id IN ('PSI-10','PSI-159') AND source_table_id LIKE '%inverse%' AND (o2_context IS NULL OR o2_context != 'burner_stream')"):
            fail("R5-o2-context", "inverse-flame records without burner_stream context")
        expect = {
            "condition_records": claims["combustion_aerosol_rows"], "unique_individual_tests": claims["unique_individual_tests"],
            "duplicate_records": claims["duplicate_rows_total"], "solid_records": claims["solid_rows"],
            "solid_with_pressure": claims["solid_with_pressure"], "partial_gravity_records": claims["partial_gravity_rows"],
            "inverse_flame_records": claims["inverse_flame_rows"],
        }
        for name, want in expect.items():
            got = json.loads(q(f"SELECT value_json FROM aggregate WHERE name='{name}'"))
            if got != want:
                fail("R6-reproduce-claims", f"{name}: db {got} != claims_check {want}")
        for sid, key in (("exploration_envelope", "ambient_A_exploration_envelope_O2_30_36_P_8.2_10.2psia"),
                         ("moon_base_challenge", "ambient_B_moon_base_challenge_O2_ge30_P_le10.2psia"),
                         ("fm2_point", "ambient_C_fm2_point_O2_32_36_P_7.2_9.2psia"), ("iss", "ambient_E_iss_O2_20_22_P_14.2_15.2psia")):
            got = json.loads(q(f"SELECT value_json FROM aggregate WHERE name='scenario:{sid}'"))["records"]
            if got != claims[key]["n"]:
                fail("R6-reproduce-claims", f"scenario {sid}: db {got} != independent check {claims[key]['n']}")

        counts = {t: q(f"SELECT COUNT(*) FROM {t}") for t in ("investigation", "source_table", "run", "observation", "quality_flag",
                                                             "publication", "data_file", "relation", "claim", "aggregate", "coverage_cell", "passage")}
        meta = {"schema_version": str(SCHEMA_VERSION), "build_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "counts": json.dumps(counts, sort_keys=True), "report_pages_indexed": str(n_pages),
                "claims_check_sha256": sha256(P("derived/claims_check.json")),
                "inputs_sha256": hashlib.sha256(json.dumps(sorted(inputs.items())).encode()).hexdigest(),
                "runs_csv_sha256": sha256(P("derived/runs.csv"))}
        for k, v in sorted(meta.items()):
            db.execute("INSERT INTO meta VALUES (?,?)", (k, v))
    db.execute("VACUUM")
    db.close()
    os.replace(tmp, OUT)
    print(f"OK {os.path.relpath(OUT, ROOT)}: {json.dumps(counts)}; report pages indexed: {n_pages}")


if __name__ == "__main__":
    try:
        main()
    except BuildError as e:
        print(f"BUILD FAILED {e}", file=sys.stderr)
        sys.exit(2)
