"""Deterministic query logic for every non-LLM endpoint (FINAL_API_CONTRACT.md §2-§3)."""
import collections
import json
import math
import re

from .db import PSIA_PER_ATM, RUN_SELECT, STATUS_LABEL, aggregate, attach_details, quantity

COMBUSTION = "fuel_class != 'none'"
NEAR_O2_PTS, NEAR_P_PSIA = 2.0, 1.0

SCENARIOS = {
    "exploration_envelope": dict(
        label="Exploration envelope (30–36% O₂, 8.2–10.2 psia)",
        description="FIREWISE definition spanning FM2's elevated-O₂ point (34% / 8.2 psia) and the challenge's ≤10.2 psi.",
        window=dict(o2_min_pct=30, o2_max_pct=36, p_min_psia=8.2, p_max_psia=10.2, gravity="partial_gravity_lunar", fuel_focus="solid"),
        source="fact:X02; fact:X03"),
    "moon_base_challenge": dict(
        label="Moon base, challenge definition (≥30% O₂, ≤10.2 psia, 0.16 g)",
        description="Atmosphere stated in the Space Apps 2026 'Flame in Freefall' challenge text.",
        window=dict(o2_min_pct=30, o2_max_pct=100, p_min_psia=0, p_max_psia=10.2, gravity="partial_gravity_lunar", fuel_focus="any"),
        source="fact:X03"),
    "fm2_point": dict(
        label="FM2 elevated-O₂ test point (34% ±2 pts, 8.2 ±1 psia)",
        description="Planned Flammability of Materials on the Moon atmosphere (NTRS 20240015307), with stated tolerances.",
        window=dict(o2_min_pct=32, o2_max_pct=36, p_min_psia=7.2, p_max_psia=9.2, gravity="partial_gravity_lunar", fuel_focus="solid"),
        source="fact:X02"),
    "iss": dict(
        label="ISS cabin (20–22% O₂, 14.2–15.2 psia, µg)",
        description="Nominal ISS cabin atmosphere window (FIREWISE default tolerance).",
        window=dict(o2_min_pct=20, o2_max_pct=22, p_min_psia=14.2, p_max_psia=15.2, gravity="microgravity", fuel_focus="any"),
        source="fact:X03"),
}
GRAVITY_REGIME = {"microgravity": "microgravity", "partial_gravity_lunar": "partial_gravity",
                  "partial_gravity_mars": "partial_gravity", "normal_gravity": "normal_gravity"}


# ------------------------------------------------------------------------------------------- helpers
def _mid(lo, hi):
    return None if lo is None else (lo + hi) / 2


def _range_quantity(rows, lo_key, hi_key, st_key, ctx_key, unit, context_filter=None):
    sel = [r for r in rows if r[lo_key] is not None and (context_filter is None or r[ctx_key] == context_filter)]
    if not sel:
        return quantity(None, None, unit, "missing", context_filter)
    st = collections.Counter(r[st_key] for r in sel)
    status = st.most_common(1)[0][0]
    q = quantity(min(r[lo_key] for r in sel), max(r[hi_key] for r in sel), unit, status,
                 context_filter or collections.Counter(r[ctx_key] for r in sel).most_common(1)[0][0])
    if len(st) > 1:
        q["status_label"] = "Mixed: " + ", ".join(f"{STATUS_LABEL[k].lower()} ({v})" for k, v in st.most_common())
    return q


def build_info(con):
    m = dict(con.execute("SELECT key, value FROM meta").fetchall())
    return {"schema_version": int(m["schema_version"]), "build_utc": m["build_utc"], "counts": json.loads(m["counts"]),
            "report_pages_indexed": int(m["report_pages_indexed"]), "claims_check_sha256": m["claims_check_sha256"]}


def cards(con, ids=None):
    meta = {r["investigation_id"]: r for r in con.execute("SELECT * FROM investigation_meta")}
    pubs = dict(con.execute("SELECT investigation_id, COUNT(*) FROM publication GROUP BY investigation_id").fetchall())
    anomalies = dict(con.execute("SELECT investigation_id, COUNT(*) FROM quality_flag WHERE severity='anomaly' GROUP BY investigation_id").fetchall())
    runs = collections.defaultdict(list)
    for r in con.execute("SELECT * FROM run"):
        runs[r["investigation_id"]].append(r)
    out = []
    q = "SELECT * FROM investigation ORDER BY CAST(substr(id, 5) AS INTEGER)"
    for inv in con.execute(q):
        if ids is not None and inv["id"] not in ids:
            continue
        rs = runs.get(inv["id"], [])
        comb = [r for r in rs if r["fuel_class"] != "none" and r["duplicate_of"] is None]
        m = meta.get(inv["id"])
        out.append({
            "id": inv["id"], "acronym": inv["acronym"], "title": inv["title"], "project_type": inv["project_type"],
            "platform": inv["platform"], "facility": m["facility"] if m else None, "insert_hw": m["insert_hw"] if m else None,
            "data_class": m["data_class"] if m else None,
            "fuel_classes": sorted({r["fuel_class"] for r in comb}),
            "n_records": len([r for r in rs if r["duplicate_of"] is None]),
            "n_unique_tests": len([r for r in comb if r["row_granularity"] == "test"]),
            "n_duplicates": len([r for r in rs if r["duplicate_of"] is not None]),
            "o2_ambient": _range_quantity(comb, "o2_min_pct", "o2_max_pct", "o2_status", "o2_context", "pct", "ambient"),
            "pressure": _range_quantity(comb, "p_min_atm", "p_max_atm", "p_status", "p_context", "atm"),
            "flow": _range_quantity(comb, "flow_min_cm_s", "flow_max_cm_s", "flow_status", "flow_context", "cm_s"),
            "has_burner_stream_o2": any(r["o2_context"] == "burner_stream" for r in comb),
            "n_publications": pubs.get(inv["id"], 0), "n_anomalies": anomalies.get(inv["id"], 0),
            "psi_url": inv["psi_url"], "doi_url": f"https://doi.org/{inv['doi']}" if inv["doi"] else None,
        })
    return out


# ------------------------------------------------------------------------------------------- summary
def summary(con):
    a = lambda n: aggregate(con, n)
    metric = lambda n, desc: {"value": a(n), "description": desc, "evidence_id": f"agg:{n}"}
    metrics = {
        "investigations": metric("investigations_total", "NASA PSI combustion-science investigation records"),
        "investigations_with_tables": metric("investigations_with_tables", "investigations with a PSI experimental table"),
        "condition_records": metric("condition_records", "combustion/aerosol condition records (tests, test points, test days, envelopes)"),
        "unique_individual_tests": metric("unique_individual_tests", "individual tests, exact duplicates excluded"),
        "duplicate_records": metric("duplicate_records", "exact duplicate source rows (marked, not deleted)"),
        "partial_gravity_records": metric("partial_gravity_records", "records at partial gravity"),
        "solid_records": metric("solid_records", "solid-material tests"),
        "solid_with_pressure": metric("solid_with_pressure", "solid tests documenting chamber pressure"),
        "solid_o2_max_pct": metric("solid_o2_max_pct", "highest documented O₂ in a solid test (%)"),
        "anomaly_flags": metric("anomaly_flags", "defects found in NASA source tables (flagged, not hidden)"),
        "report_pages_indexed": {"value": build_info(con)["report_pages_indexed"], "description": "NASA report pages searchable by the Copilot", "evidence_id": "meta:report_pages_indexed"},
    }
    base = f"WHERE {COMBUSTION} AND duplicate_of IS NULL"
    return {
        "metrics": metrics,
        "by_fuel_class": dict(con.execute(f"SELECT fuel_class, COUNT(*) FROM run {base} GROUP BY fuel_class ORDER BY 2 DESC").fetchall()),
        "by_granularity": dict(con.execute(f"SELECT row_granularity, COUNT(*) FROM run {base} GROUP BY 1 ORDER BY 2 DESC").fetchall()),
        "by_data_class": dict(con.execute("SELECT data_class, COUNT(*) FROM investigation_meta GROUP BY 1 ORDER BY 1").fetchall()),
        "by_platform": dict(con.execute(f"SELECT platform, COUNT(*) FROM run {base} GROUP BY 1 ORDER BY 2 DESC").fetchall()),
        "flags_by_severity": dict(con.execute("SELECT severity, COUNT(*) FROM quality_flag GROUP BY 1").fetchall()),
        "documentation_by_fuel_class": {
            r["fuel_class"]: {"both": r["both"], "o2_only": r["o2_only"], "p_only": r["p_only"], "neither": r["neither"]}
            for r in con.execute(f"""SELECT fuel_class,
                SUM(COALESCE(o2_context,'')='ambient' AND p_min_atm IS NOT NULL) both,
                SUM(COALESCE(o2_context,'')='ambient' AND p_min_atm IS NULL) o2_only,
                SUM(COALESCE(o2_context,'')!='ambient' AND p_min_atm IS NOT NULL) p_only,
                SUM(COALESCE(o2_context,'')!='ambient' AND p_min_atm IS NULL) neither
                FROM run {base} GROUP BY fuel_class ORDER BY COUNT(*) DESC""")},
        "scenario_counts": {sid: a(f"scenario:{sid}")["records"] for sid in SCENARIOS},
        "key_findings": key_findings(con),
        "limitations": [
            "PSI experimental tables are summaries: a value that is 'not documented' may still exist in raw data or papers; it is never treated as zero.",
            "In inverse flames (ACME Flame Design, CFI-G) the O₂ value is the burner oxidizer stream, not the chamber atmosphere; habitat matching uses chamber (ambient) O₂ only.",
            "SPICE rows are condition points within 151 ignitions; BRE, CLD, E-FIELD and s-Flame rows are test-day summaries; FLEX-2 rows are design envelopes.",
            "All PSI flight evidence is microgravity; 1 g appears only as Saffire-II paired observations; there is no partial-gravity record.",
            "Literature facts (LUCI, FM2, published results) are cited by URL and were not archived locally.",
            "Evidence relevance is not fire risk: FIREWISE does not predict flammability or fire behaviour.",
        ],
        "build": build_info(con),
    }


def key_findings(con):
    a = lambda n: aggregate(con, n)
    mb = a("scenario:moon_base_challenge")
    return [
        {"id": "K1", "title": "No documented test in the exploration envelope",
         "statement": f"{a('scenario:exploration_envelope')['records']} PSI records document chamber O₂ of 30–36% together with 8.2–10.2 psia.",
         "evidence_ids": ["agg:scenario:exploration_envelope", "fact:F18"], "tier": "measured"},
        {"id": "K2", "title": "Moon-base atmosphere: gas flames only",
         "statement": f"Under the challenge's Moon-base definition (≥30% O₂, ≤10.2 psia) there are {mb['records']} records, all from "
                      f"{', '.join(mb['by_investigation'])} (gas flames, pressure reported as approximate).",
         "evidence_ids": ["agg:scenario:moon_base_challenge", "fact:F18"], "tier": "measured"},
        {"id": "K3", "title": "Solid materials lack pressure data",
         "statement": f"{a('solid_with_pressure')} of {a('solid_records')} solid-material tests document chamber pressure; "
                      f"{a('solid_with_o2')} document O₂, at most {a('solid_o2_max_pct')}%.",
         "evidence_ids": ["agg:solid_records", "agg:solid_with_pressure", "agg:solid_o2_max_pct"], "tier": "measured"},
        {"id": "K4", "title": "Zero partial-gravity evidence in PSI",
         "statement": f"{a('partial_gravity_records')} PSI records are at lunar or Martian gravity. LUCI (flown 2025) and FM2 (planned) are outside PSI.",
         "evidence_ids": ["agg:partial_gravity_records", "fact:F17", "fact:X01", "fact:X02"], "tier": "measured"},
        {"id": "K5", "title": "Cool flames in exactly seven CFI-G tests",
         "statement": f"{a('cfig_cool_flame_yes')} CFI-G normal-flame tests are marked cool flame = yes, all '30% butane' at X_O₂ ≈ 0.39 and ≈2 bar "
                      f"({a('cfig_cool_flame_not_recorded')} rows leave the field blank).",
         "evidence_ids": ["agg:cfig_cool_flame_yes", "fact:F02"], "tier": "measured"},
        {"id": "K6", "title": "DAFT qualified the instrument for SAME",
         "statement": "DAFT/DAFT-2 tested a modified TSI P-Trak against a DustTrak with Arizona Road Dust to de-risk SAME's smoke measurements.",
         "evidence_ids": ["inv:PSI-47#objective", "fact:F04"], "tier": "reported"},
    ]


# ------------------------------------------------------------------------------------------- investigations
def list_investigations(con, q=None, fuel_class=None, platform=None, data_class=None, o2_min=None, o2_max=None,
                        p_min_atm=None, p_max_atm=None, limit=50, offset=0, sort="id"):
    items = cards(con)
    if q:
        hits = {r[0] for r in con.execute("SELECT DISTINCT investigation_id FROM passage WHERE passage MATCH ? AND investigation_id IS NOT NULL",
                                          (fts_query(q, "and"),))}
        ql = q.lower()
        items = [c for c in items if c["id"] in hits or ql in (c["acronym"] or "").lower() or ql in c["title"].lower() or ql == c["id"].lower()]
    if fuel_class:
        items = [c for c in items if set(fuel_class) & set(c["fuel_classes"])]
    if platform:
        items = [c for c in items if any(p.lower() in (c["facility"] or c["platform"] or "").lower() for p in platform)]
    if data_class:
        items = [c for c in items if c["data_class"] in data_class]

    def overlaps(qty, lo, hi):
        if lo is None and hi is None:
            return True
        if qty["min"] is None:
            return False
        return (hi is None or qty["min"] <= hi) and (lo is None or qty["max"] >= lo)
    items = [c for c in items if overlaps(c["o2_ambient"], o2_min, o2_max) and overlaps(c["pressure"], p_min_atm, p_max_atm)]
    key = {"id": lambda c: int(c["id"][4:]), "acronym": lambda c: (c["acronym"] or "~").lower(), "n_records": lambda c: -c["n_records"]}[sort]
    items.sort(key=key)
    return {"items": items[offset:offset + limit], "total": len(items), "limit": limit, "offset": offset}


def investigation_detail(con, inv_id):
    inv = con.execute("SELECT * FROM investigation WHERE id=?", (inv_id,)).fetchone()
    if inv is None:
        return None
    card = cards(con, {inv_id})[0]
    folders = dict(con.execute("SELECT folder, COUNT(*) FROM data_file WHERE investigation_id=? GROUP BY folder ORDER BY 2 DESC", (inv_id,)).fetchall())
    dl = con.execute("SELECT COUNT(*) FROM data_file WHERE investigation_id=? AND downloaded=1", (inv_id,)).fetchone()[0]
    rels = [{"src": r["src"], "dst": r["dst"], "type": r["type"], "status": r["status"], "note": r["note"], "evidence_id": r["evidence_id"]}
            for r in con.execute("SELECT * FROM relation WHERE src=? OR dst=? ORDER BY id", (inv_id, inv_id))]
    facts = [{"id": f["id"], "value": f["value"], "tier": f["tier"], "source": f["source"], "confidence": f["confidence"],
              "caveat": f["caveat"], "evidence_id": f"fact:{f['id']}"}
             for f in con.execute("SELECT c.* FROM claim c JOIN claim_investigation ci ON ci.claim_id=c.id WHERE ci.investigation_id=? ORDER BY c.id", (inv_id,))]
    tf = lambda k: {"value": inv[k], "evidence_id": f"inv:{inv_id}#{k}"}
    return {**card, "hardware": inv["hardware"], "sub_research_area": inv["sub_research_area"], "start_date": inv["start_date"],
            "end_date": inv["end_date"], "doi": inv["doi"], "license": inv["license"],
            "objective": tf("objective"), "hypothesis": tf("hypothesis"), "approach": tf("approach"), "research_impacts": tf("research_impacts"),
            "publications": [dict(title=p["title"], authors=p["authors"], doi=p["doi"], status=p["status"])
                             for p in con.execute("SELECT * FROM publication WHERE investigation_id=? ORDER BY id", (inv_id,))],
            "data_products": {"n_files_listed": inv["n_files_listed"], "listed_gb": inv["listed_gb"], "total_gb": inv["total_gb"],
                              "listing_complete": bool(inv["listing_complete"]), "folders": folders, "downloaded_files": dl},
            "flags_by_code": dict(con.execute("SELECT code, COUNT(*) FROM quality_flag WHERE investigation_id=? GROUP BY code ORDER BY 2 DESC", (inv_id,)).fetchall()),
            "granularity": dict(con.execute("SELECT row_granularity, COUNT(*) FROM run WHERE investigation_id=? GROUP BY 1", (inv_id,)).fetchall()),
            "relations": rels, "curated_facts": facts,
            "source_tables": [dict(r) for r in con.execute("SELECT id, file_name, sha256, source_url, n_source_records FROM source_table WHERE investigation_id=? ORDER BY id", (inv_id,))]}


VARY_COLS = ["fuel_or_material", "diluent", "geometry", "o2", "pressure", "flow", "row_granularity", "fuel_class", "platform"]


def investigation_runs(con, inv_id, granularity=None, include_duplicates=False, limit=100, offset=0):
    where, args = ["r.investigation_id=?"], [inv_id]
    if not include_duplicates:
        where.append("r.duplicate_of IS NULL")
    if granularity:
        where.append(f"r.row_granularity IN ({','.join('?' * len(granularity))})"); args += granularity
    allrows = con.execute(f"{RUN_SELECT} WHERE {' AND '.join(where)} ORDER BY r.source_table_id, r.source_row, r.row_key", args).fetchall()
    qcols = {"o2": ("o2_min_pct", "o2_max_pct", "o2_status"), "pressure": ("p_min_atm", "p_max_atm", "p_status"),
             "flow": ("flow_min_cm_s", "flow_max_cm_s", "flow_status")}
    sig = lambda r, c: json.dumps([r[k] for k in qcols[c]]) if c in qcols else r[c]
    varying, constant = [], {}
    for c in VARY_COLS:
        vals = {sig(r, c) for r in allrows}
        if len(vals) > 1:
            varying.append(c)
        else:
            constant[c] = None if not vals else (None if next(iter(vals)) is None else str(next(iter(vals))))
    page = attach_details(con, allrows[offset:offset + limit])
    return {"varying_columns": varying, "constant_columns": constant,
            "page": {"items": page, "total": len(allrows), "limit": limit, "offset": offset}}


def search_runs(con, investigation_id=None, fuel_class=None, o2_context="ambient", o2_min=None, o2_max=None, p_min_atm=None,
                p_max_atm=None, documented_only=False, include_duplicates=False, granularity=None, limit=100, offset=0):
    where, args = [f"r.{COMBUSTION}"], []
    if investigation_id:
        where.append(f"r.investigation_id IN ({','.join('?' * len(investigation_id))})"); args += investigation_id
    if fuel_class:
        where.append(f"r.fuel_class IN ({','.join('?' * len(fuel_class))})"); args += fuel_class
    if granularity:
        where.append(f"r.row_granularity IN ({','.join('?' * len(granularity))})"); args += granularity
    if not include_duplicates:
        where.append("r.duplicate_of IS NULL")
    if o2_min is not None or o2_max is not None or documented_only:
        where.append("r.o2_context = ?"); args.append(o2_context)
    if o2_min is not None:
        where.append("(r.o2_min_pct + r.o2_max_pct) / 2 >= ?"); args.append(o2_min)
    if o2_max is not None:
        where.append("(r.o2_min_pct + r.o2_max_pct) / 2 <= ?"); args.append(o2_max)
    if p_min_atm is not None or p_max_atm is not None or documented_only:
        where.append("r.p_min_atm IS NOT NULL")
    if p_min_atm is not None:
        where.append("(r.p_min_atm + r.p_max_atm) / 2 >= ?"); args.append(p_min_atm)
    if p_max_atm is not None:
        where.append("(r.p_min_atm + r.p_max_atm) / 2 <= ?"); args.append(p_max_atm)
    w = " AND ".join(where)
    total = con.execute(f"SELECT COUNT(*) FROM run r WHERE {w}", args).fetchone()[0]
    rows = con.execute(f"{RUN_SELECT} WHERE {w} ORDER BY r.investigation_id, r.row_key LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
    return {"items": attach_details(con, rows), "total": total, "limit": limit, "offset": offset}


# ------------------------------------------------------------------------------------------- scatter points
def points(con):
    """Compact chamber-O2 x pressure points for every non-duplicate record documenting BOTH (ambient O2 only)."""
    rows = con.execute(f"""SELECT row_key, investigation_id, fuel_class, test_label, (o2_min_pct+o2_max_pct)/2 o2, (p_min_atm+p_max_atm)/2 p,
                               o2_status, p_status FROM run WHERE {COMBUSTION} AND duplicate_of IS NULL AND o2_context='ambient'
                               AND p_min_atm IS NOT NULL ORDER BY row_key""").fetchall()
    total = con.execute(f"SELECT COUNT(*) FROM run WHERE {COMBUSTION} AND duplicate_of IS NULL").fetchone()[0]
    return {"fields": ["row_key", "investigation_id", "fuel_class", "test_label", "o2_pct", "p_psia", "o2_status", "p_status"],
            "points": [[r["row_key"], r["investigation_id"], r["fuel_class"], r["test_label"], round(r["o2"], 3),
                        round(r["p"] * PSIA_PER_ATM, 3), r["o2_status"], r["p_status"]] for r in rows],
            "n_points": len(rows), "n_records": total,
            "note": "Records lacking either documented chamber O2 or pressure are not plotted (counted in n_records)."}


# ------------------------------------------------------------------------------------------- distributions
VAR = {"o2_pct": ("o2_min_pct", "o2_max_pct", "o2_status", "pct"), "p_atm": ("p_min_atm", "p_max_atm", "p_status", "atm"),
       "flow_cm_s": ("flow_min_cm_s", "flow_max_cm_s", "flow_status", "cm_s")}


def distributions(con, variable, group_by="fuel_class", o2_context="ambient", bins=20):
    lo_k, hi_k, st_k, unit = VAR[variable]
    gcol = {"fuel_class": "fuel_class", "investigation": "investigation_id", "status": st_k}[group_by]
    rows = con.execute(f"SELECT {gcol} AS g, {lo_k} AS lo, {hi_k} AS hi, {st_k} AS st, o2_context FROM run "
                       f"WHERE {COMBUSTION} AND duplicate_of IS NULL").fetchall()
    groups = collections.defaultdict(list)
    for r in rows:
        if variable == "o2_pct" and r["lo"] is not None and r["o2_context"] != o2_context:
            continue  # burner-stream / envelope O2 never mixed into an ambient distribution
        groups[r["g"]].append(r)
    mids = [(r["lo"] + r["hi"]) / 2 for rs in groups.values() for r in rs if r["lo"] is not None]
    if not mids:
        return {"variable": variable, "unit": unit, "o2_context": o2_context if variable == "o2_pct" else None, "groups": []}
    lo, hi = min(mids), max(mids)
    width = (hi - lo) / bins if hi > lo else 1.0
    out = []
    for g, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        doc = [(r["lo"] + r["hi"]) / 2 for r in rs if r["lo"] is not None]
        hist = [0] * bins
        for v in doc:
            hist[min(bins - 1, int((v - lo) / width)) if hi > lo else 0] += 1
        out.append({"key": g, "n_documented": len(doc), "n_missing": len(rs) - len(doc),
                    "status_counts": dict(collections.Counter(r["st"] for r in rs)),
                    "histogram": [{"lo": round(lo + i * width, 4), "hi": round(lo + (i + 1) * width, 4), "n": n} for i, n in enumerate(hist)]})
    return {"variable": variable, "unit": unit, "o2_context": o2_context if variable == "o2_pct" else None, "groups": out}


# ------------------------------------------------------------------------------------------- scenarios
def scenario_list(con):
    out = []
    for sid, s in SCENARIOS.items():
        g = GRAVITY_REGIME.get(s["window"]["gravity"])
        n = con.execute(f"SELECT COUNT(*) FROM run WHERE {COMBUSTION} AND duplicate_of IS NULL AND gravity_regime=?", (g,)).fetchone()[0] if g else 0
        out.append({"id": sid, **s, "gravity_evidence_records": n})
    return out


def scenario_evidence(con, window, scenario_id="custom", label=None, description=None, source=None):
    w = window
    rows = con.execute(f"SELECT * FROM run WHERE {COMBUSTION} AND duplicate_of IS NULL").fetchall()
    inv = {r["id"]: r for r in con.execute("SELECT id, acronym FROM investigation")}
    by = collections.defaultdict(list)
    for r in rows:
        by[r["investigation_id"]].append(r)
    greg = GRAVITY_REGIME.get(w["gravity"])
    grav_n = sum(1 for r in rows if greg and r["gravity_regime"] == greg)
    items = []
    for acc, rs in by.items():
        inn, near, und = [], [], collections.Counter()
        for r in rs:
            o = _mid(r["o2_min_pct"], r["o2_max_pct"]) if r["o2_context"] == "ambient" else None
            p = _mid(r["p_min_atm"], r["p_max_atm"])
            p = None if p is None else p * PSIA_PER_ATM
            if o is None:
                und["o2_not_documented_as_ambient"] += 1
            if p is None:
                und["pressure_not_documented"] += 1
            if o is None or p is None:
                continue
            if w["o2_min_pct"] <= o <= w["o2_max_pct"] and w["p_min_psia"] <= p <= w["p_max_psia"]:
                inn.append(r)
            elif (w["o2_min_pct"] - NEAR_O2_PTS <= o <= w["o2_max_pct"] + NEAR_O2_PTS and
                  w["p_min_psia"] - NEAR_P_PSIA <= p <= w["p_max_psia"] + NEAR_P_PSIA):
                near.append(r)
        classes = sorted({r["fuel_class"] for r in rs})
        match = w["fuel_focus"] == "any" or w["fuel_focus"] in classes
        cw = lambda sel, eid=None: {"n": len(sel), "o2_status": dict(collections.Counter(r["o2_status"] for r in sel)),
                                    "p_status": dict(collections.Counter(r["p_status"] for r in sel)), "evidence_id": eid}
        if w["gravity"] in ("partial_gravity_lunar", "partial_gravity_mars"):
            gm = "none — PSI has 0 partial-gravity records; these are microgravity results"
        elif w["gravity"] == "microgravity":
            gm = "microgravity (matches)"
        elif w["gravity"] == "normal_gravity":
            gm = "none — PSI flight records are microgravity"
        else:
            gm = "not constrained"
        items.append({"investigation_id": acc, "acronym": inv[acc]["acronym"],
                      "in_window": cw(inn, f"query:scenario:{scenario_id}:{acc}"), "near_window": cw(near),
                      "undocumented": dict(und), "records_considered": len(rs), "material_class": classes, "material_match": match,
                      "gravity_match": gm, "sample_row_keys": [r["row_key"] for r in (inn or near)[:5]]})
    items.sort(key=lambda i: (-i["in_window"]["n"], -i["near_window"]["n"], not i["material_match"], int(i["investigation_id"][4:])))
    if greg == "partial_gravity":
        statement = "PSI contains no partial-gravity combustion records. Everything below is microgravity evidence and must not be read as lunar or Martian behaviour."
    elif greg == "microgravity":
        statement = f"{grav_n} microgravity records are available."
    elif greg == "normal_gravity":
        statement = "PSI flight records are microgravity; 1 g appears only as Saffire-II paired observations."
    else:
        statement = "Gravity not constrained."
    return {
        "scenario": {"id": scenario_id, "label": label or "Custom window", "description": description or "User-defined window",
                     "window": w, "source": source or "user input", "gravity_evidence_records": grav_n},
        "gravity_evidence": {"requested": w["gravity"], "matching_records": grav_n, "statement": statement},
        "ranking_method": "Lexicographic: (1) records in window, (2) records within tolerance of the window, (3) material class matches focus, (4) PSI id. No weighted score.",
        "near_window_tolerance": f"±{NEAR_O2_PTS:g} percentage points O₂, ±{NEAR_P_PSIA:g} psia",
        "label": "Evidence relevance — not a fire-risk score or flammability prediction",
        "totals": {"in_window": sum(i["in_window"]["n"] for i in items), "near_window": sum(i["near_window"]["n"] for i in items),
                   "records_considered": len(rows)},
        "items": items,
    }


# ------------------------------------------------------------------------------------------- compare
def _interval_sim(a, b):
    if a["min"] is None or b["min"] is None:
        return None
    lo, hi = max(a["min"], b["min"]), min(a["max"], b["max"])
    inter = max(0.0, hi - lo)
    union = max(a["max"], b["max"]) - min(a["min"], b["min"])
    if union == 0:
        return 1.0 if inter == 0 and a["min"] == b["min"] else 0.0
    return round(inter / union, 3)


def _jaccard(a, b):
    a, b = set(a), set(b)
    if not a or not b:
        return None
    return round(len(a & b) / len(a | b), 3)


INCOMPATIBLE = [
    ({"dust_aerosol"}, {"smoke_source_nonflaming"}, "Mineral dust vs pyrolysis smoke: different aerosols. The link is instrument qualification, not shared science."),
    ({"solid_emulating_gas_burner"}, {"solid"}, "Gas burner emulating a solid vs real solid samples: compare conditions, not burning or spread rates."),
    ({"liquid_droplet"}, {"solid"}, "Droplet vs solid-sheet combustion: different geometries and physics; compare conditions only."),
    ({"smoke_source_nonflaming"}, {"gaseous", "solid", "liquid_droplet", "solid_emulating_gas_burner"}, "Non-flaming smoke generation vs flames."),
    ({"dust_aerosol"}, {"gaseous", "solid", "liquid_droplet", "solid_emulating_gas_burner"}, "Dust aerosol instrument test vs combustion."),
]


def compare(con, ids):
    cs = cards(con, set(ids))
    cs.sort(key=lambda c: ids.index(c["id"]))
    rows = collections.defaultdict(list)
    q = ",".join("?" * len(ids))
    for r in con.execute(f"SELECT * FROM run WHERE investigation_id IN ({q}) AND {COMBUSTION} AND duplicate_of IS NULL", ids):
        rows[r["investigation_id"]].append(r)
    obsvars = collections.defaultdict(set)
    for acc, var in con.execute(f"SELECT r.investigation_id, o.variable FROM observation o JOIN run r USING(row_key) WHERE r.investigation_id IN ({q})", ids):
        obsvars[acc].add(var)
    by = {c["id"]: c for c in cs}
    burner = {c["id"]: _range_quantity(rows[c["id"]], "o2_min_pct", "o2_max_pct", "o2_status", "o2_context", "pct", "burner_stream") for c in cs}
    feats = []

    def add(name, kind, values, sims, note=None):
        vals = [s for s in sims if s is not None]
        feats.append({"name": name, "kind": kind, "values": values, "comparable": len(vals) == len(sims) and len(sims) > 0,
                      "similarity": round(sum(vals) / len(vals), 3) if vals and len(vals) == len(sims) else None, "note": note})

    pairs = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]]
    cat = lambda f: [None if by[a][f] is None or by[b][f] is None else float(by[a][f] == by[b][f]) for a, b in pairs]
    add("Facility", "categorical", {i: by[i]["facility"] for i in ids}, cat("facility"))
    add("Hardware insert / apparatus", "categorical", {i: by[i]["insert_hw"] for i in ids}, cat("insert_hw"))
    fc = {i: sorted({r["fuel_class"] for r in rows[i]}) for i in ids}
    add("Fuel class", "set", fc, [_jaccard(fc[a], fc[b]) for a, b in pairs])
    fuels = {i: sorted({(r["fuel_or_material"] or "").strip() for r in rows[i] if r["fuel_or_material"]})[:25] for i in ids}
    add("Fuels / materials", "set", fuels, [_jaccard(fuels[a], fuels[b]) for a, b in pairs])
    dil = {i: sorted({r["diluent"] for r in rows[i] if r["diluent"]}) for i in ids}
    add("Diluent", "set", dil, [_jaccard(dil[a], dil[b]) for a, b in pairs])
    add("Chamber (ambient) O₂", "interval", {i: by[i]["o2_ambient"] for i in ids},
        [_interval_sim(by[a]["o2_ambient"], by[b]["o2_ambient"]) for a, b in pairs],
        "Overlap of documented ranges; 'Not documented' is never treated as a value.")
    if any(burner[i]["min"] is not None for i in ids):
        add("Burner-stream O₂ (inverse flames)", "interval", burner, [_interval_sim(burner[a], burner[b]) for a, b in pairs],
            "Oxidizer stream issued from the burner — not an atmosphere; never compared with ambient O₂.")
    add("Chamber pressure", "interval", {i: by[i]["pressure"] for i in ids},
        [_interval_sim(by[a]["pressure"], by[b]["pressure"]) for a, b in pairs])
    flow_ctx = {i: sorted({r["flow_context"] for r in rows[i] if r["flow_context"]}) for i in ids}
    add("Airflow", "interval", {i: {**by[i]["flow"], "contexts": flow_ctx[i]} for i in ids},
        [_interval_sim(by[a]["flow"], by[b]["flow"]) if set(flow_ctx[a]) & set(flow_ctx[b]) else None for a, b in pairs],
        "Compared only when the flow type matches (e.g. duct flow vs coflow vs inlet are not comparable).")
    gr = {i: sorted({r["gravity_regime"] for r in rows[i]}) for i in ids}
    add("Gravity", "set", gr, [_jaccard(gr[a], gr[b]) for a, b in pairs], "All PSI flight records are microgravity.")
    gran = {i: sorted({r["row_granularity"] for r in rows[i]}) for i in ids}
    add("Record type", "set", gran, [_jaccard(gran[a], gran[b]) for a, b in pairs],
        "Tests vs test-day summaries vs envelopes: counts are not directly comparable across record types.")
    add("Measured outcomes available", "set", {i: sorted(obsvars[i]) for i in ids},
        [_jaccard(obsvars[a], obsvars[b]) for a, b in pairs])
    add("Records (non-duplicate)", "count", {i: by[i]["n_records"] for i in ids}, [], "Context only; not a similarity dimension.")
    add("Data class", "categorical", {i: by[i]["data_class"] for i in ids}, cat("data_class"))
    comparable = [f for f in feats if f["comparable"]]
    dims = [f for f in feats if f["kind"] != "count"]
    incompat = []
    for a, b in pairs:
        A, B = set(fc[a]), set(fc[b])
        for x, y, reason in INCOMPATIBLE:
            if (A & x and B & y and not (A & y)) or (B & x and A & y and not (B & y)):
                incompat.append({"a": a, "b": b, "reason": reason}); break
    rels = [{"src": r["src"], "dst": r["dst"], "type": r["type"], "status": r["status"], "note": r["note"], "evidence_id": r["evidence_id"]}
            for r in con.execute("SELECT * FROM relation ORDER BY id") if (r["src"] in ids and r["dst"] in ids)]
    shared_hw = collections.defaultdict(list)
    for r in con.execute("SELECT * FROM relation WHERE type IN ('uses_insert','uses_facility')"):
        if r["src"] in ids:
            shared_hw[r["dst"]].append(r["src"])
    for hw, members in shared_hw.items():
        if len(members) > 1:
            rels.append({"src": " + ".join(members), "dst": hw, "type": "shared_hardware", "status": "verified",
                         "note": f"{', '.join(members)} all used {hw}", "evidence_id": f"inv:{members[0]}#hardware"})
    sims = [f["similarity"] for f in comparable if f["similarity"] is not None]
    return {"investigations": cs, "features": feats, "compared_on": f"{len(comparable)}/{len(dims)}",
            "mean_similarity_on_comparable": round(sum(sims) / len(sims), 3) if sims else None,
            "incompatibilities": incompat, "relations": rels,
            "label": "Condition similarity on comparable dimensions only — never scientific equivalence"}


# ------------------------------------------------------------------------------------------- gaps
def gaps(con):
    cells = []
    for c in con.execute("SELECT * FROM coverage_cell ORDER BY gravity_regime, fuel_class, o2_band, p_band"):
        invs = {}
        for part in (c["investigations"] or "").split(";"):
            if part:
                k, v = part.split(":"); invs[k] = int(v)
        cells.append({"gravity_regime": c["gravity_regime"], "fuel_class": c["fuel_class"], "o2_band": c["o2_band"],
                      "p_band": c["p_band"], "records": c["records"], "investigations": invs})
    fuel_classes = [r[0] for r in con.execute(f"SELECT fuel_class FROM run WHERE {COMBUSTION} GROUP BY 1 ORDER BY COUNT(*) DESC")]
    return {
        "dims": {"gravity_regime": ["microgravity", "partial_gravity", "normal_gravity"], "fuel_class": fuel_classes,
                 "o2_band": ["<20.5%", "20.5-23% (air)", "23-30%", "30-36%", ">36%", "not documented"],
                 "p_band": ["<8.2 psia", "8.2-10.2 psia", "10.2-13.7 psia", "13.7-15.7 psia (~1 atm)", ">15.7 psia", "not documented"]},
        "cells": cells,
        "literature_overlays": [
            {"id": "LUCI", "label": "LUCI — flown 2025 (New Shepard, lunar g > 25 s); data not in PSI", "gravity_regime": "partial_gravity",
             "fuel_class": "solid", "o2_band": "not documented", "p_band": "not documented", "status": "literature (flown)", "evidence_id": "fact:X01"},
            {"id": "FM2-34", "label": "FM2 — planned 34% O₂ / 8.2 psia on CLPS (not yet flown)", "gravity_regime": "partial_gravity",
             "fuel_class": "solid", "o2_band": "30-36%", "p_band": "8.2-10.2 psia", "status": "literature (planned)", "evidence_id": "fact:X02"},
            {"id": "FM2-21", "label": "FM2 — planned 21% O₂ / 14.7 psia on CLPS (not yet flown)", "gravity_regime": "partial_gravity",
             "fuel_class": "solid", "o2_band": "20.5-23% (air)", "p_band": "13.7-15.7 psia (~1 atm)", "status": "literature (planned)", "evidence_id": "fact:X02"},
        ],
        "definitions": {
            "records": "Non-duplicate combustion/aerosol records from PSI experimental tables.",
            "o2_band": "Chamber (ambient) O₂ only, by midpoint of the documented range. Burner-stream O₂ of inverse flames is excluded.",
            "p_band": "Chamber pressure by midpoint, in psia; band edges at the scenario boundaries 8.2 and 10.2 psia.",
            "not documented": "The PSI table does not document the value. It may exist in raw data or papers; it is not zero.",
            "zero cell": "No documented PSI record. This is a gap in evidence, not a statement that the condition is safe or unsafe.",
            "normal_gravity": "1 g appears only as Saffire-II paired observations (not as separate records).",
        },
        "headline": key_findings(con)[:4],
    }


# ------------------------------------------------------------------------------------------- evidence
def evidence(con, eid):
    if eid.startswith("inv:"):
        m = re.fullmatch(r"inv:(PSI-\d+)#(\w+)", eid)
        if not m:
            return None
        acc, field = m.groups()
        cols = {"objective", "hypothesis", "approach", "research_impacts", "hardware", "title"}
        if field not in cols:
            return None
        r = con.execute(f"SELECT {field} AS v, title, psi_url FROM investigation WHERE id=?", (acc,)).fetchone()
        return r and {"evidence_id": eid, "kind": "psi_record_field", "title": f"{acc} {r['title']} — {field}", "text": r["v"], "url": r["psi_url"]}
    if eid.startswith("row:"):
        r = con.execute(f"{RUN_SELECT} WHERE r.row_key=?", (eid[4:],)).fetchone()
        if not r:
            return None
        d = attach_details(con, [r])[0]
        return {"evidence_id": eid, "kind": "psi_table_row", "title": f"{r['investigation_id']} {r['file_name']} row {r['source_row']}",
                "text": r["raw_json"], "url": r["source_url"], "data": d}
    if eid.startswith("obs:"):
        key, _, var = eid[4:].partition("#")
        o = con.execute("SELECT * FROM observation WHERE row_key=? AND variable=?", (key, var)).fetchone()
        return o and {"evidence_id": eid, "kind": "observation", "title": f"{var} — {key}",
                      "text": f"{var} = {o['value_num'] if o['value_num'] is not None else o['value_text']} {o['unit'] or ''} ({STATUS_LABEL[o['status']]}; column '{o['source_column']}')",
                      "url": None, "data": dict(o)}
    if eid.startswith("fact:"):
        f = con.execute("SELECT * FROM claim WHERE id=?", (eid[5:],)).fetchone()
        return f and {"evidence_id": eid, "kind": f"curated_fact ({f['tier']})", "title": f"{f['id']} {f['field']}", "text": f["value"],
                      "url": next(iter(re.findall(r"https?://\S+", f["source"] or "")), None), "data": dict(f)}
    if eid.startswith("agg:"):
        a = con.execute("SELECT * FROM aggregate WHERE name=?", (eid[4:],)).fetchone()
        return a and {"evidence_id": eid, "kind": "aggregate", "title": a["name"], "text": f"{a['description']}: {a['value_json']}",
                      "url": None, "data": {"definition": a["definition"], "value": json.loads(a["value_json"])}}
    if eid.startswith("pdf:"):
        p = con.execute("SELECT * FROM document_page WHERE evidence_id=?", (eid,)).fetchone()
        return p and {"evidence_id": eid, "kind": "nasa_report_page", "title": f"{p['investigation_id']} {p['file_name']} p.{p['page']}",
                      "text": p["text"], "url": f"https://psi.nasa.gov/physci/repo/data/investigations/{p['investigation_id']}",
                      "data": {"sha256": p["sha256"], "local_path": p["local_path"], "page": p["page"]}}
    if eid.startswith("group:"):
        p = con.execute("SELECT * FROM passage WHERE evidence_id=?", (eid,)).fetchone()
        return p and {"evidence_id": eid, "kind": "run_group_summary", "title": p["title"], "text": p["text"], "url": None}
    return None


def fts_query(text, mode="or"):
    """Turn free text into a safe FTS5 query of quoted word tokens (no operators from user input).
    mode='and' (Explorer search: all words) or 'or' (Copilot retrieval: recall)."""
    toks = [t for t in re.findall(r"[A-Za-z0-9]{2,}", text.lower()) if t not in STOP]
    return (" AND " if mode == "and" else " OR ").join(f'"{t}"' for t in toks[:24]) or '""'


STOP = set("the a an of in on at to for and or is are was were be by with from what which how do does did can could "
           "there their this that these those about any all into as it its than then them they we you i me my our".split())
