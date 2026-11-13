"""Evidence twin: match a Digital Twin scenario against NASA PSI records in the scientific database.

Semantics (same rules as the rest of FIREWISE):
- Only non-duplicate combustion/aerosol records are considered (duplicate_of IS NULL, fuel_class != 'none').
- Chamber O₂ is the ambient O₂ only; burner-stream O₂ (inverse flames) is never compared with a cabin.
- A variable that a record does not document never matches and never contributes a distance.
- Airflow is compared only for ambient flow types (forced duct, quiescent, coflow, imposed envelope);
  smoke-sampling inlet velocities are not airflow over a sample.
- No PSI table documents chamber gas temperature: temperature is reported as missing evidence.
- "Nearest" is a transparent normalised distance over the variables both sides document. It means
  "closest documented conditions", never "scientifically equivalent experiment".
"""
import collections
import math

from ..db import RUN_SELECT, STATUS_LABEL
from . import physics

KPA_PER_ATM = 101.325
KPA_PER_PSIA = 6.894757
COMPARABLE_FLOW = {"forced_duct": "forced flow over the sample (duct)", "quiescent": "quiescent (no imposed flow)",
                   "coflow": "coflow around the flame", "envelope": "imposed flow envelope"}
GRAVITY_TO_REGIME = {"microgravity": "microgravity", "lunar": "partial_gravity", "mars": "partial_gravity", "earth": "normal_gravity"}
VARIABLES = ("o2_pct", "pressure_kPa", "airflow_m_s", "temperature_K")
METHOD = ("Exact match: every enabled variable is documented by the record and its documented midpoint lies within the tolerance of the "
          "scenario value; gravity must match; material filter applied when enabled. Nearest: records ranked lexicographically by "
          "(1) number of enabled variables both sides document, descending, then (2) distance D = √Σ((x − target)/tolerance)² over "
          "those variables, ascending, then (3) row key. Undocumented variables are excluded from D, never set to zero.")


def _mid(lo, hi):
    if lo is None:
        return None
    return lo if hi is None or hi == lo else (lo + hi) / 2


def record_values(r):
    o2 = _mid(r["o2_min_pct"], r["o2_max_pct"]) if r["o2_context"] == "ambient" else None
    p = _mid(r["p_min_atm"], r["p_max_atm"])
    flow = _mid(r["flow_min_cm_s"], r["flow_max_cm_s"]) if r["flow_context"] in COMPARABLE_FLOW else None
    return {"o2_pct": {"value": o2, "status": r["o2_status"] if o2 is not None else "missing",
                       "context": r["o2_context"], "note": "burner-stream O₂ (not a chamber atmosphere)" if r["o2_context"] == "burner_stream" else None},
            "pressure_kPa": {"value": None if p is None else p * KPA_PER_ATM, "status": r["p_status"] if p is not None else "missing", "context": r["p_context"], "note": None},
            "airflow_m_s": {"value": None if flow is None else flow / 100.0, "status": r["flow_status"] if flow is not None else "missing",
                            "context": r["flow_context"], "note": None if r["flow_context"] in COMPARABLE_FLOW or r["flow_context"] is None
                            else f"{r['flow_context']} flow (not compared with cabin airflow)"},
            "temperature_K": {"value": None, "status": "missing", "context": None, "note": "chamber gas temperature not documented in PSI tables"}}


def targets(scenario):
    exp = scenario["experiment"]
    st = physics.zone_state(scenario, exp["zone_id"])
    val = lambda tv: None if tv is None else tv.get("value")
    return {"zone_id": exp["zone_id"], "o2_pct": val(st["o2_pct"]), "pressure_kPa": val(scenario["pressure_kPa"]),
            "airflow_m_s": val(st["airflow_m_s"]), "temperature_K": val(st["temperature_K"]),
            "gravity": scenario["gravity"], "gravity_regime": GRAVITY_TO_REGIME[scenario["gravity"]],
            "fuel_class": exp.get("fuel_class"), "material": (exp.get("material") or "").strip() or None}


def enabled_vars(scenario):
    m = scenario.get("matching") or {}
    out = ["o2_pct"]
    if m.get("use_pressure", True):
        out.append("pressure_kPa")
    if m.get("use_airflow"):
        out.append("airflow_m_s")
    if m.get("use_temperature"):
        out.append("temperature_K")
    return out


def tolerances(scenario):
    m = scenario.get("matching") or {}
    return {"o2_pct": m.get("o2_tolerance_pts", 2.0), "pressure_kPa": m.get("pressure_tolerance_kPa", 6.89),
            "airflow_m_s": m.get("airflow_tolerance_m_s", 0.05), "temperature_K": 5.0}


def material_match(r, t):
    ok = True
    if t["fuel_class"]:
        ok = r["fuel_class"] == t["fuel_class"]
    if ok and t["material"]:
        hay = f"{r['fuel_or_material'] or ''} {r['fuel_class_detail'] or ''} {r['geometry'] or ''}".lower()
        ok = all(tok in hay for tok in t["material"].lower().split())
    return ok


def _records(con):
    return con.execute(f"{RUN_SELECT} WHERE r.fuel_class != 'none' AND r.duplicate_of IS NULL ORDER BY r.row_key").fetchall()


def _acronyms(con):
    return {r["id"]: r["acronym"] for r in con.execute("SELECT id, acronym FROM investigation")}


def _item(r, vals, acr, comps, compared, enabled, t, dist):
    return {"row_key": r["row_key"], "evidence_id": f"row:{r['row_key']}", "investigation_id": r["investigation_id"],
            "acronym": acr.get(r["investigation_id"]), "test_label": r["test_label"], "row_granularity": r["row_granularity"],
            "fuel_class": r["fuel_class"], "fuel_or_material": r["fuel_or_material"], "gravity_regime": r["gravity_regime"],
            "gravity_matches": r["gravity_regime"] == t["gravity_regime"], "material_match": material_match(r, t),
            "values": {k: {**vals[k], "status_label": STATUS_LABEL.get(vals[k]["status"], vals[k]["status"])} for k in VARIABLES},
            "components": comps, "variables_compared": compared, "variables_enabled": enabled,
            "missing_variables": [v for v in enabled if v not in compared], "distance": dist,
            "outcome_text": r["outcome_text"], "source": {"file_name": r["file_name"], "source_row": r["source_row"], "source_url": r["source_url"]}}


def evaluate(con, scenario, nearest_limit=20):
    t = targets(scenario)
    en = enabled_vars(scenario)
    tol = tolerances(scenario)
    use_mat = (scenario.get("matching") or {}).get("use_material", False)
    acr = _acronyms(con)
    rows = _records(con)
    exact, scored = [], []
    doc_counts = collections.Counter()
    for r in rows:
        vals = record_values(r)
        for v in VARIABLES:
            if vals[v]["value"] is not None:
                doc_counts[v] += 1
        if use_mat and not material_match(r, t):
            continue
        comps, compared = {}, []
        for v in en:
            x, tg = vals[v]["value"], t[v]
            if x is None or tg is None:
                continue
            comps[v] = round(abs(x - tg) / tol[v], 4)
            compared.append(v)
        if not compared:
            continue
        dist = round(math.sqrt(sum(c * c for c in comps.values())), 4)
        it = _item(r, vals, acr, comps, compared, en, t, dist)
        scored.append(it)
        if len(compared) == len(en) and all(c <= 1.0 for c in comps.values()) and it["gravity_matches"]:
            exact.append(it)
    scored.sort(key=lambda i: (-len(i["variables_compared"]), i["distance"], i["row_key"]))
    nearest = scored[:nearest_limit]
    basis = exact or nearest
    keys = [i["row_key"] for i in basis]
    obs = collections.defaultdict(lambda: {"n": 0, "statuses": collections.Counter(), "unit": None})
    if keys:
        q = ",".join("?" * len(keys))
        for o in con.execute(f"SELECT variable, unit, status FROM observation WHERE row_key IN ({q})", keys):
            d = obs[o["variable"]]
            d["n"] += 1
            d["statuses"][o["status"]] += 1
            d["unit"] = o["unit"]
    grav = collections.Counter(r["gravity_regime"] for r in rows)
    by_inv = collections.Counter(i["investigation_id"] for i in exact)
    cov = {
        "records_considered": len(rows),
        "exact_matches": len(exact),
        "investigations": [{"investigation_id": k, "acronym": acr.get(k), "records": n} for k, n in sorted(by_inv.items(), key=lambda x: (-x[1], x[0]))],
        "basis": "exact matches" if exact else "nearest documented records",
        "documented": {v: {"records": doc_counts[v], "not_documented": len(rows) - doc_counts[v]} for v in VARIABLES},
        "available_measurements": [{"variable": k, "records": d["n"], "unit": d["unit"], "statuses": dict(d["statuses"])}
                                   for k, d in sorted(obs.items(), key=lambda x: (-x[1]["n"], x[0]))],
        "missing_measurements": _missing(t, en, doc_counts, len(rows)),
        "gravity": {"requested": t["gravity"], "requested_regime": t["gravity_regime"], "records_by_regime": dict(grav),
                    "records_at_requested": grav.get(t["gravity_regime"], 0),
                    "statement": _gravity_statement(t, grav)},
        "materials": {"fuel_classes": dict(collections.Counter(i["fuel_class"] for i in basis)),
                      "top_materials": [{"material": m, "records": n} for m, n in collections.Counter(i["fuel_or_material"] for i in basis).most_common(8)]},
        "outcomes": [{"evidence_id": i["evidence_id"], "investigation_id": i["investigation_id"], "test_label": i["test_label"], "outcome_text": i["outcome_text"]}
                     for i in basis if i["outcome_text"]][:8],
        "sources": sorted({(i["investigation_id"], i["source"]["file_name"], i["source"]["source_url"]) for i in basis}),
    }
    cov["sources"] = [{"investigation_id": a, "file_name": b, "source_url": c} for a, b, c in cov["sources"]]
    return {"targets": t, "variables_enabled": en, "tolerances": tol, "use_material": use_mat, "method": METHOD,
            "label": "Evidence relevance only — not a fire-risk score, not a prediction, and nearest ≠ scientifically equivalent.",
            "exact": exact, "nearest": nearest, "coverage": cov}


def _missing(t, en, doc, n):
    out = []
    names = {"o2_pct": "chamber (ambient) O₂", "pressure_kPa": "chamber pressure", "airflow_m_s": "ambient airflow over the sample",
             "temperature_K": "chamber gas temperature"}
    for v in VARIABLES:
        out.append({"variable": v, "label": names[v], "enabled": v in en, "scenario_value_set": t[v] is not None,
                    "records_documenting": doc[v], "records_not_documenting": n - doc[v],
                    "note": ("No PSI table documents chamber gas temperature; temperature can only be compared once such data exist."
                             if v == "temperature_K" else None)})
    return out


def _gravity_statement(t, grav):
    if t["gravity_regime"] == "microgravity":
        return f"{grav.get('microgravity', 0)} microgravity records are available."
    if t["gravity_regime"] == "partial_gravity":
        return "PSI contains no partial-gravity combustion records. Exact matches require matching gravity, so there are none; nearest records are microgravity evidence and must not be read as lunar or Martian behaviour."
    return "PSI flight records are microgravity; 1 g appears only as Saffire-II paired observations, not as separate records. Exact matches at Earth gravity: none."
