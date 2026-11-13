"""Twin-aware Copilot context: evidence-pack items describing the active Digital Twin scenario and
deterministic, source-grounded answers for twin questions.

Pack items (ephemeral, rebuilt per question from the scenario the UI sends):
  twin:scenario        the user's configuration (user-defined values, NOT measurements)
  twin:evidence        deterministic SQL evidence evaluation (exact matches, nearest records)
  twin:coverage        documented / not documented variables, available measurements
  twin:calc:<model>:<scope>   physics outputs with units, statuses and model versions
  twin:unavailable     models not computed and why
  twin:planned         models that are NOT implemented
  twin:o2 / twin:sensitivity  intent-specific computed items
Persistent items: row:<key> (NASA rows), model:<id> (model cards), twinval:<id> (validation records).

Claim tiers: measured (NASA records/SQL counts), calculation (exact physical-law arithmetic),
model_prediction (correlation-based estimates), unknown (not documented / not computable),
interpretation (hedged reasoning), reported, literature.
"""
import copy
import re

from . import evidence as tev
from . import physics, service

TWIN_INTENTS = [
    ("twin_reliability", r"\b(reliab\w*|validat\w*|accura\w*|trust\w*|uncertain\w*)\b"),
    ("twin_limits", r"\bprevent\w*\b|\bwhy (can'?t|cannot|can not)\b|\bpredict\w*\b.*\b(flame|fire|ignition|spread|burn\w*)\b|\bflame behaviou?r\b"),
    ("twin_models", r"\b(physical|physics) models?\b|\bwhich models?\b|\bmodels? (can|could) be applied\b|\bapply\b.*\bmodels?\b"),
    ("twin_missing", r"\bmissing\b|\bnot documented\b|\bwhich variables\b|\black\w*\b"),
    ("twin_pressure", r"\bpressure\b.*\b(modif\w*|chang\w*|increas\w*|decreas\w*|lower\w*|rais\w*|reduc\w*)\b|\b(modif\w*|chang\w*|increas\w*|decreas\w*|lower\w*|rais\w*|reduc\w*)\b.*\bpressure\b"),
    ("twin_material_flow", r"\bmaterials?\b.*\b(airflow|air ?flow|flow)\b|\b(airflow|air ?flow|flow)\b.*\bmaterials?\b"),
    ("twin_nearest", r"\b(closest|nearest|similar|comparable|match\w*)\b"),
    ("twin_o2", r"\b(oxygen|o2|o₂)\b"),
]

TRANSPORT = {"viscosity", "thermal_conductivity", "prandtl"}


def _item(pack, eid):
    return next(i for i in pack.items if i["evidence_id"] == eid)


def twin_route(q):
    ql = q.lower()
    for name, pat in TWIN_INTENTS:
        if re.search(pat, ql):
            return name
    return "twin_general"


def g(x, nd=4):
    return "not documented" if x is None else (f"{x:.{nd}g}" if isinstance(x, float) else str(x))


def _v(tv):
    return None if tv is None else tv.get("value")


def _st(tv):
    return "not set" if tv is None or tv.get("value") is None else tv.get("status", "user_defined").replace("_", "-")


def _nearest_text(items, k=5):
    out = []
    for i, n in enumerate(items[:k], 1):
        o, p = n["values"]["o2_pct"], n["values"]["pressure_kPa"]
        f = n["values"]["airflow_m_s"]
        out.append(f"{i}) {n['acronym'] or n['investigation_id']} ({n['investigation_id']}) test {n['test_label'] or '—'} [{n['row_key']}], "
                   f"{n['fuel_class']} '{n['fuel_or_material'] or '—'}': chamber O2 {g(o['value'])}% ({o['status_label']}), "
                   f"pressure {g(p['value'])} kPa ({p['status_label']}), airflow {g(f['value'])} m/s ({f['status_label']}), "
                   f"gravity {n['gravity_regime']}; distance {g(n['distance'], 3)} over {len(n['variables_compared'])} of {len(n['variables_enabled'])} variables")
    return "; ".join(out)


def build(con, pack, ctx, intent, question):
    """Add twin items to the pack. Returns the evaluation (evidence + physics) used to build them."""
    sc = ctx["scenario"]
    ev = service.evaluate(con, sc, nearest_limit=20)
    env = service.environment(con, sc["habitat"]["environment_id"])
    e, ph, t = ev["evidence"], ev["physics"], ev["evidence"]["targets"]
    zname = {z["id"]: z["name"] for z in env["zones"]}
    sel = ctx.get("selected_zone")
    st = physics.zone_state(sc, t["zone_id"])
    exp = sc["experiment"]
    txt = (f"Scenario '{sc['name']}' (configuration entered by the user; values are not measurements unless their status says so). "
           f"Experiment zone {t['zone_id']} ({zname.get(t['zone_id'])}). Chamber O2 in that zone {g(t['o2_pct'])}% ({_st(st['o2_pct'])}); "
           f"pressure {g(t['pressure_kPa'])} kPa = {g(t['pressure_kPa'] / 6.894757 if t['pressure_kPa'] else None)} psia ({_st(sc['pressure_kPa'])}); "
           f"temperature {g(t['temperature_K'])} K ({_st(st['temperature_K'])}); airflow at the experiment {g(t['airflow_m_s'])} m/s ({_st(st['airflow_m_s'])}); "
           f"gravity {sc['gravity']}; material class {exp.get('fuel_class') or 'not set'}{'; material ' + t['material'] if t['material'] else ''}; "
           f"ventilation {g(_v(sc['ventilation']['volumetric_flow_m3_h']))} m3/h ({_st(sc['ventilation']['volumetric_flow_m3_h'])}).")
    if sel and sel in zname:
        zs = physics.zone_state(sc, sel)
        txt += f" Selected zone {sel} ({zname[sel]}): O2 {g(_v(zs['o2_pct']))}%, temperature {g(_v(zs['temperature_K']))} K, airflow {g(_v(zs['airflow_m_s']))} m/s."
    pack.add("twin:scenario", "twin_scenario (user configuration)", f"Digital Twin scenario — {sc['name']}", txt)
    cov = e["coverage"]
    inv = ", ".join(f"{i['investigation_id']} {i['records']}" for i in cov["investigations"]) or "none"
    pack.add("twin:evidence", "twin_evidence (computed by SQL for this scenario)", "Evidence evaluation for the scenario",
             f"Records considered (non-duplicate combustion/aerosol): {cov['records_considered']}. Variables compared: {', '.join(e['variables_enabled'])}; "
             f"tolerances O2 ±{g(e['tolerances']['o2_pct'])} points, pressure ±{g(e['tolerances']['pressure_kPa'])} kPa, airflow ±{g(e['tolerances']['airflow_m_s'])} m/s. "
             f"Exact matches (all compared variables within tolerance and same gravity): {cov['exact_matches']} (by investigation: {inv}). "
             f"Records at the requested gravity ({cov['gravity']['requested_regime']}): {cov['gravity']['records_at_requested']}. {cov['gravity']['statement']} "
             f"Nearest documented records (closest conditions, not equivalent experiments): {_nearest_text(e['nearest'])}.")
    docs = cov["documented"]
    meas = ", ".join(f"{m['variable']} ({m['records']})" for m in cov["available_measurements"][:8]) or "none"
    pack.add("twin:coverage", "twin_evidence (computed by SQL for this scenario)", "Documentation coverage",
             f"Of {cov['records_considered']} records: chamber O2 documented by {docs['o2_pct']['records']} and not documented by {docs['o2_pct']['not_documented']}; "
             f"chamber pressure documented by {docs['pressure_kPa']['records']} and not documented by {docs['pressure_kPa']['not_documented']}; "
             f"ambient airflow (comparable flow types) documented by {docs['airflow_m_s']['records']}; chamber gas temperature documented by "
             f"{docs['temperature_K']['records']} (no PSI table documents it). Measurements available among the {cov['basis']}: {meas}.")
    for i in e["nearest"][:5]:
        pack.ev(i["evidence_id"])
    unavailable = []
    for r in ph["results"]:
        if r["scope"] not in (f"zone:{t['zone_id']}", "habitat") and not r["scope"].startswith("experiment"):
            continue
        if r["status"] != "completed":
            unavailable.append(f"{r['model_name']} ({r['scope']}): {r['status']} — {r['reason']}")
            continue
        outs = "; ".join(f"{o['name']} = {g(o['value'])} {o['unit']} [{o['validation_status']}]" for o in r["outputs"])
        ins = "; ".join(f"{i['name']} = {g(i['value'])} {i['unit']} ({i['status'].replace('_', '-')})" for i in r["inputs"])
        pack.add(f"twin:calc:{r['model_id']}:{r['scope']}", "twin_calculation (deterministic physics model output)",
                 f"{r['model_name']} v{r['model_version']} — {r['scope']}",
                 f"{r['model_name']} version {r['model_version']} (validation status {r['validation_status']}) for {r['scope']}: {outs}. "
                 f"Inputs: {ins}. {' '.join(r['warnings'])}")
    pack.add("twin:unavailable", "twin_calculation (deterministic physics model output)", "Models not computed",
             ("Models not computed for this scenario: " + "; ".join(unavailable)) if unavailable else "All implemented models were computed for this scenario.")
    pack.add("twin:planned", "twin_model_registry", "Models not implemented",
             "Not implemented in FIREWISE (no output is produced): " + "; ".join(f"{m['name']}" for m in ph["planned_models"])
             + ". FIREWISE implements no combustion, ignition, extinction or flame-spread model and does not predict fire behaviour.")
    for mid in physics.REGISTRY:
        pack.ev(f"model:{mid}")
    if intent == "twin_reliability":
        for mid in physics.REGISTRY:
            pack.ev(f"twinval:{mid}")
    if intent == "twin_o2":
        o2_only = copy.deepcopy(sc)
        o2_only["matching"] = {**o2_only.get("matching", {}), "use_pressure": False, "use_airflow": False, "use_temperature": False, "use_material": False}
        o2_only["gravity"] = "microgravity"
        e2 = tev.evaluate(con, o2_only, nearest_limit=5)
        stat = {}
        for i in e2["exact"]:
            s = i["values"]["o2_pct"]["status_label"]
            stat[s] = stat.get(s, 0) + 1
        inv2 = ", ".join(f"{i['investigation_id']} {i['records']}" for i in e2["coverage"]["investigations"]) or "none"
        pack.add("twin:o2", "twin_evidence (computed by SQL for this scenario)", "Evidence at the scenario O2 (O2 only)",
                 f"Records documenting chamber (ambient) O2 within ±{g(e2['tolerances']['o2_pct'])} points of {g(t['o2_pct'])}% (pressure, airflow and gravity "
                 f"not constrained; burner-stream O2 excluded): {e2['coverage']['exact_matches']} (by investigation: {inv2}). "
                 f"O2 status of those records: {', '.join(f'{k} {v}' for k, v in sorted(stat.items())) or 'none'}.",
                 value={"n": e2["coverage"]["exact_matches"], "rows": [i["evidence_id"] for i in e2["exact"][:3]]})
        for i in e2["exact"][:3]:
            pack.ev(i["evidence_id"])
    if intent == "twin_pressure":
        rows = []
        p0 = t["pressure_kPa"]
        for f in (0.8, 1.0, 1.2):
            p = round(p0 * f, 2)
            if not 10.0 <= p <= 200.0:
                continue
            s2 = copy.deepcopy(sc)
            s2["pressure_kPa"] = {"value": p, "status": "user_defined", "source": "sensitivity"}
            ph2 = physics.run_scenario(env, s2)
            e3 = tev.evaluate(con, s2, nearest_limit=1)
            dens = service._out(ph2, "ideal_gas", f"zone:{t['zone_id']}", "density")
            po2 = service._out(ph2, "gas_mixture", f"zone:{t['zone_id']}", "o2_partial_pressure")
            h = service._out(ph2, "forced_convection_flat_plate", "experiment", "heat_transfer_coefficient")
            rows.append(f"at {g(p)} kPa: density {g(dens)} kg/m3, O2 partial pressure {g(po2)} kPa"
                        + (f", convective coefficient {g(h)} W/(m2·K)" if h is not None else "")
                        + f", exact NASA matches {e3['coverage']['exact_matches']}, nearest distance "
                        + (g(e3["nearest"][0]["distance"], 3) if e3["nearest"] else "none"))
        pack.add("twin:sensitivity", "twin_calculation (deterministic physics model output)", "Pressure sensitivity (all else unchanged)",
                 "Pressure sensitivity, other inputs unchanged (Models A/B/D1 and SQL evidence counts): " + "; ".join(rows) + ".")
    if intent == "twin_material_flow":
        s2 = copy.deepcopy(sc)
        s2["matching"] = {**s2.get("matching", {}), "use_material": True, "use_airflow": True}
        e4 = tev.evaluate(con, s2, nearest_limit=5)
        pack.add("twin:material_flow", "twin_evidence (computed by SQL for this scenario)", "Material and airflow matching",
                 f"With the material filter (class {t['fuel_class'] or 'any'}{', text ' + t['material'] if t['material'] else ''}) and airflow "
                 f"{g(t['airflow_m_s'])} m/s ±{g(e4['tolerances']['airflow_m_s'])} enabled: exact matches {e4['coverage']['exact_matches']}; "
                 f"records of that material that document comparable ambient airflow: {sum(1 for n in e4['nearest'] if 'airflow_m_s' in n['variables_compared'])} "
                 f"among the nearest {len(e4['nearest'])}. Nearest: {_nearest_text(e4['nearest'], 3)}.",
                 value={"n": e4["coverage"]["exact_matches"], "nearest": e4["nearest"][:3]})
        for i in e4["nearest"][:3]:
            pack.ev(i["evidence_id"])
    return ev


def answer(con, intent, pack, ctx, ev, question):
    """Deterministic claims for twin intents. Every number appears in a cited pack item."""
    C = lambda text, tier, ids: {"text": text, "tier": tier, "evidence_ids": [i for i in ids if i in pack.ids]}
    e, ph, t = ev["evidence"], ev["physics"], ev["evidence"]["targets"]
    cov = e["coverage"]
    near = e["nearest"]
    zone = t["zone_id"]
    calc = lambda mid, scope=None: f"twin:calc:{mid}:{scope or 'zone:' + zone}"
    out = lambda mid, name, scope=None: service._out(ph, mid, scope or f"zone:{zone}", name)
    lim = ["Scenario values are user-defined unless their status says otherwise; they are not measurements.",
           "Evidence counts use documented NASA values only; undocumented variables never match."]
    gaps = []
    gravity_claim = None
    if cov["gravity"]["requested_regime"] != "microgravity":
        gravity_claim = C(f"PSI holds {cov['gravity']['records_at_requested']} records at the requested gravity ({cov['gravity']['requested_regime']}); "
                          "every nearest record is microgravity evidence.", "measured", ["twin:evidence"])
        gaps.append("Combustion data at the requested gravity level.")
    if intent == "twin_nearest" or intent == "twin_general":
        claims = [C(f"{cov['exact_matches']} of {cov['records_considered']} NASA records match the scenario on {', '.join(e['variables_enabled'])} within tolerance at the same gravity.",
                    "measured", ["twin:evidence"])]
        for n in near[:3]:
            o, p = n["values"]["o2_pct"], n["values"]["pressure_kPa"]
            claims.append(C(f"{n['acronym'] or n['investigation_id']} test {n['test_label'] or '—'} documents chamber O2 {g(o['value'])}% ({o['status_label']}) "
                            f"and pressure {g(p['value'])} kPa ({p['status_label']}), distance {g(n['distance'], 3)} tolerance units.",
                            "measured", [n["evidence_id"], "twin:evidence"]))
        if gravity_claim:
            claims.append(gravity_claim)
        claims.append(C("Nearest means closest documented conditions; it does not make those tests equivalent to this scenario.", "interpretation", ["twin:evidence"]))
        summary = (f"{cov['exact_matches']} NASA records match this scenario; the closest documented record is "
                   f"{near[0]['acronym'] or near[0]['investigation_id']} test {near[0]['test_label'] or '—'}." if near else
                   f"{cov['exact_matches']} NASA records match this scenario and none documents a comparable variable.")
        if intent == "twin_general":
            d = out("ideal_gas", "density")
            po2 = out("gas_mixture", "o2_partial_pressure")
            if d is not None:
                claims.append(C(f"Ideal-gas density in zone {zone} is {g(d)} kg/m³ and O2 partial pressure is {g(po2)} kPa (calculated from the configured values).",
                                "calculation", [calc("ideal_gas"), calc("gas_mixture")]))
        return summary, claims, lim, gaps
    if intent == "twin_o2":
        val = _item(pack, "twin:o2")["value"]
        n_o2 = val["n"]
        claims = [C(f"{n_o2} NASA records document chamber O2 within ±{g(e['tolerances']['o2_pct'])} points of {g(t['o2_pct'])}%, regardless of pressure and gravity.",
                    "measured", ["twin:o2"] + val["rows"]),
                  C(f"With pressure also compared, {cov['exact_matches']} records match.", "measured", ["twin:evidence"]),
                  C("Burner-stream O2 of inverse flames is excluded because it is not a chamber atmosphere.", "reported", ["fact:F19", "twin:o2"])]
        if gravity_claim:
            claims.append(gravity_claim)
        return f"{n_o2} NASA records document chamber O2 near {g(t['o2_pct'])}%.", claims, lim, gaps
    if intent == "twin_pressure":
        claims = [C("At fixed temperature and composition, density, molar concentration and O2 partial pressure are proportional to pressure (ideal gas and Dalton's law).",
                    "calculation", ["model:ideal_gas", "model:gas_mixture", "twin:sensitivity"]),
                  C(_item(pack, "twin:sensitivity")["text"].replace("Pressure sensitivity, other inputs unchanged (Models A/B/D1 and SQL evidence counts): ", "Computed for this scenario: "),
                    "calculation", ["twin:sensitivity"]),
                  C("Viscosity and conductivity are pressure-independent in Model B (dilute-gas assumption), so kinematic viscosity rises as pressure falls.",
                    "model_prediction", ["model:gas_mixture"]),
                  C(f"The NASA evidence count at the configured pressure is {cov['exact_matches']} exact matches.", "measured", ["twin:evidence"])]
        return "Lowering cabin pressure lowers gas density and O2 partial pressure in proportion; the NASA evidence count changes with the pressure window.", claims, lim, gaps
    if intent == "twin_material_flow":
        val = _item(pack, "twin:material_flow")["value"]
        n = val["n"]
        claims = [C(f"With material and airflow both compared, {n} NASA records match exactly.", "measured", ["twin:material_flow"]),
                  C("Airflow is compared only for ambient flow types (forced duct, quiescent, coflow, imposed envelope); smoke-sampling inlet flows are excluded.",
                    "interpretation", ["twin:material_flow", "twin:coverage"]),
                  C(f"Only {cov['documented']['airflow_m_s']['records']} of {cov['records_considered']} records document a comparable ambient airflow.",
                    "measured", ["twin:coverage"])]
        for nr in val["nearest"][:2]:
            f, o = nr["values"]["airflow_m_s"], nr["values"]["o2_pct"]
            claims.append(C(f"Closest documented record of this material: {nr['acronym'] or nr['investigation_id']} test {nr['test_label'] or '—'} "
                            f"('{nr['fuel_or_material'] or '—'}'), airflow {g(f['value'])} m/s ({f['status_label']}), chamber O2 {g(o['value'])}% ({o['status_label']}).",
                            "measured", [nr["evidence_id"], "twin:material_flow"]))
        return f"{n} NASA records match both the material and the airflow of this scenario.", claims, lim, gaps
    if intent == "twin_missing":
        d = cov["documented"]
        N = cov["records_considered"]
        claims = [C(f"Chamber gas temperature is documented by {d['temperature_K']['records']} of {N} NASA records.", "unknown", ["twin:coverage"]),
                  C(f"Chamber pressure is not documented by {d['pressure_kPa']['not_documented']} of {N} records and chamber O2 by {d['o2_pct']['not_documented']}.",
                    "unknown", ["twin:coverage"]),
                  C(f"Comparable ambient airflow is documented by only {d['airflow_m_s']['records']} of {N} records.", "unknown", ["twin:coverage"])]
        un = [r for r in ph["results"] if r["status"] != "completed" and (r["scope"] in (f"zone:{zone}", "habitat") or r["scope"].startswith("experiment"))]
        if un:
            claims.append(C("Some physics models were not computed because scenario inputs are missing or out of range (see the models-not-computed list).",
                            "unknown", ["twin:unavailable"]))
        if gravity_claim:
            claims.append(gravity_claim)
        gaps += ["Chamber gas temperature in NASA records.", "Chamber pressure for solid-material tests."]
        return "Temperature is never documented in the NASA tables, and pressure and airflow are often missing.", claims, lim, gaps
    if intent == "twin_models":
        done = sorted({(r["model_id"], r["model_name"], r["model_version"], r["validation_status"]) for r in ph["results"] if r["status"] == "completed"})
        claims = [C(f"{name} v{ver} was computed for this scenario (validation status: {vs}).", "calculation",
                    [f"model:{mid}"] + [i for i in pack.order() if i.startswith(f"twin:calc:{mid}:")][:1]) for mid, name, ver, vs in done]
        claims.append(C("Models that need missing inputs are listed as not computed instead of being filled with assumed values.", "unknown", ["twin:unavailable"]))
        claims.append(C("No combustion, ignition, extinction or flame-spread model is implemented.", "unknown", ["twin:planned"]))
        return f"{len(done)} physics models apply to this scenario; none of them is a combustion model.", claims, lim, gaps
    if intent == "twin_limits":
        claims = [C("No combustion, ignition, extinction or flame-spread model is implemented, so FIREWISE produces no flame-behaviour output.", "unknown", ["twin:planned"]),
                  C(f"{cov['exact_matches']} NASA records match this scenario's conditions, so there is no direct experimental anchor at these conditions.",
                    "measured", ["twin:evidence"]),
                  C(f"Chamber gas temperature is documented by {cov['documented']['temperature_K']['records']} NASA records.", "unknown", ["twin:coverage"])]
        if gravity_claim:
            claims.append(gravity_claim)
        if t["fuel_class"] == "solid":
            claims.append(C("PSI documents chamber pressure for 0 of its solid-material tests.", "measured", ["agg:solid_with_pressure"]))
        claims.append(C("Predicting flame behaviour would need a validated combustion model and experiments at these conditions; neither is available here.",
                        "interpretation", ["twin:planned", "twin:evidence"]))
        gaps += ["A validated combustion model for the scenario's material.", "Experiments at the scenario's O2, pressure and gravity."]
        return "No validated combustion model and no matching experiments exist for this scenario, so flame behaviour cannot be predicted.", claims, lim, gaps
    if intent == "twin_reliability":
        ql = question.lower()
        names = {"ideal_gas": ("ideal gas", "model a"), "gas_mixture": ("mixture", "model b", "viscosity", "conductivity", "heat capacity"),
                 "bulk_airflow": ("airflow", "model c", "ventilation", "reynolds"), "forced_convection_flat_plate": ("convection", "model d1", "heat transfer coefficient"),
                 "wall_conduction": ("conduction", "wall", "model d2")}
        sel = [m for m, keys in names.items() if any(k in ql for k in keys)] or list(physics.REGISTRY)
        claims = []
        from ..services import validation_text  # noqa: F401  (text already in the pack via twinval:)
        for mid in sel:
            card = physics.REGISTRY[mid]
            claims.append(C(f"{card.name} has validation status '{card.validation_status}': {card.validation_summary}", "calculation",
                            [f"model:{mid}", f"twinval:{mid}"]))
        if "gas_mixture" in sel and t["o2_pct"] and t["o2_pct"] > 23:
            claims.append(C("The transport-property validation used air composition; this O2-enriched scenario is outside the validated composition range.",
                            "unknown", ["model:gas_mixture", "twin:scenario"]))
        claims.append(C("No model is validated against NASA PSI measurements, and none predicts combustion.", "unknown", ["twin:planned"]))
        return "The implemented models are verified or validated against reference data, not against NASA combustion measurements.", claims, lim, gaps
    return None, [], lim, gaps
