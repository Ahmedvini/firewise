"""Digital Twin service layer: environments, presets, the shared evaluation (evidence + physics),
scenario comparison and the scientific report. Everything here is deterministic."""
import json

from . import evidence as tev
from . import physics

PSIA_PER_KPA = 1 / 6.894757


class TwinError(ValueError):
    pass


def environments(con):
    return [json.loads(r["body_json"]) for r in con.execute("SELECT body_json FROM twin_environment ORDER BY id")]


def environment(con, env_id):
    r = con.execute("SELECT body_json FROM twin_environment WHERE id=?", (env_id,)).fetchone()
    return r and json.loads(r["body_json"])


def check_refs(env, sc):
    """Zone and slot references must exist in the environment (Pydantic cannot know the environment)."""
    if env is None:
        raise TwinError(f"habitat.environment_id '{sc['habitat']['environment_id']}' does not exist")
    zones = {z["id"] for z in env["zones"]}
    errs = [f"zones: unknown zone_id '{z['zone_id']}'" for z in sc.get("zones", []) if z["zone_id"] not in zones]
    exp = sc["experiment"]
    if exp["zone_id"] not in zones:
        errs.append(f"experiment.zone_id '{exp['zone_id']}' does not exist")
    if exp.get("slot_id"):
        slot = next((s for s in env["experiment_slots"] if s["id"] == exp["slot_id"]), None)
        if not slot:
            errs.append(f"experiment.slot_id '{exp['slot_id']}' does not exist")
        elif slot["zone_id"] != exp["zone_id"]:
            errs.append(f"experiment.slot_id '{exp['slot_id']}' is in zone {slot['zone_id']}, not {exp['zone_id']}")
    if errs:
        raise TwinError("; ".join(errs))


def _tv(value, note, status="user_defined"):
    return {"value": value, "status": status, "source": note}


def presets(env):
    """Starting configurations. Every value is user-defined; notes say where the numbers come from."""
    zones = [{"zone_id": z["id"], "temperature_K": _tv(295.15, "preset example (22 °C)"), "airflow_m_s": _tv(0.1, "preset example"), "o2_pct": None}
             for z in env["zones"]]
    g = env["geometry"]
    base = {
        "description": "", "habitat": {"environment_id": env["id"], "diameter_m": _tv(g["default_diameter_m"], "template default"),
                                       "length_m": _tv(g["default_length_m"], "template default")},
        "temperature_K": _tv(295.15, "preset example (22 °C)"), "gravity": "microgravity",
        "ventilation": {"volumetric_flow_m3_h": _tv(400.0, "preset example"), "direction": "+x"},
        "zones": zones,
        "experiment": {"zone_id": "Z3", "slot_id": "rack-chamber", "fuel_class": "solid", "material": None,
                       "characteristic_length_m": _tv(0.1, "preset example: 10 cm sample"), "surface_temperature_K": None},
        "wall": None, "matching": {"o2_tolerance_pts": 2.0, "pressure_tolerance_kPa": 6.89, "airflow_tolerance_m_s": 0.05,
                                   "use_pressure": True, "use_airflow": False, "use_material": False, "use_temperature": False},
    }
    mk = lambda pid, name, desc, o2, p, grav, note_o2, note_p: {"id": pid, "scenario": {**json.loads(json.dumps(base)), "name": name, "description": desc,
        "composition": {"o2_pct": _tv(o2, note_o2), "ar_pct": None, "co2_pct": None, "balance": "N2"},
        "pressure_kPa": _tv(p, note_p), "gravity": grav}}
    return [
        mk("sea_level_air", "Sea-level cabin air", "21% O₂ at 101.3 kPa (14.7 psia), microgravity: the ISS-like baseline used in the Scenario Explorer.",
           21.0, 101.325, "microgravity", "ISS-like cabin (challenge text)", "14.7 psia"),
        mk("exploration_atmosphere", "Exploration atmosphere", "34% O₂ at 56.5 kPa (8.2 psia) at lunar gravity: the FM2 elevated-O₂ test point (fact X02).",
           34.0, 56.54, "lunar", "FM2 planned test point (X02)", "8.2 psia (X02)"),
        mk("moon_base_challenge", "Moon base (challenge definition)", "30% O₂ at 70.3 kPa (10.2 psia) at lunar gravity: the challenge's Moon-base bound.",
           30.0, 70.33, "lunar", "challenge Moon-base definition (≥30% O₂)", "challenge Moon-base definition (≤10.2 psia)"),
    ]


def zone_conditions(env, sc):
    out = []
    for z in env["zones"]:
        st = physics.zone_state(sc, z["id"])
        out.append({"zone_id": z["id"], "name": z["name"], "o2_pct": st["o2_pct"], "o2_scope": st["o2_scope"],
                    "temperature_K": st["temperature_K"], "temperature_scope": st["temperature_scope"],
                    "airflow_m_s": st["airflow_m_s"] or {"value": None, "status": "not_documented", "source": "not set"},
                    "pressure_kPa": sc["pressure_kPa"]})
    return out


def evaluate(con, sc, nearest_limit=20):
    env = environment(con, sc["habitat"]["environment_id"])
    check_refs(env, sc)
    ev = tev.evaluate(con, sc, nearest_limit)
    ph = physics.run_scenario(env, sc)
    return {"environment_id": env["id"], "zone_conditions": zone_conditions(env, sc), "evidence": ev, "physics": ph,
            "status_legend": STATUS_LEGEND}


STATUS_LEGEND = {"user_defined": "Configured by the user in this scenario", "measured": "Measured in a NASA PSI test (copied with its source)",
                 "derived": "Derived by NASA or the FIREWISE pipeline from measured values", "reported": "Reported as approximate in NASA text/tables",
                 "specified": "NASA set-point", "simulated": "Computed by a FIREWISE physics model (see model id and version)",
                 "not_documented": "Not documented / not set — never treated as zero"}


def _out(ph, model_id, scope_prefix, name):
    for r in ph["results"]:
        if r["model_id"] == model_id and r["scope"].startswith(scope_prefix) and r["status"] == "completed":
            for o in r["outputs"]:
                if o["name"] == name:
                    return o["value"]
    return None


KEY_OUTPUTS = [("gas_mixture", "zone:", "o2_partial_pressure", "kPa"), ("ideal_gas", "zone:", "density", "kg/m³"),
               ("gas_mixture", "zone:", "viscosity", "µPa·s"), ("bulk_airflow", "habitat", "bulk_velocity", "cm/s"),
               ("bulk_airflow", "habitat", "air_changes_per_hour", "1/h"), ("forced_convection_flat_plate", "experiment", "heat_transfer_coefficient", "W/(m²·K)")]


def compare(con, scenarios):
    """Side-by-side comparison of 2–4 saved scenarios: configuration, evidence counts, key physics outputs."""
    evals = [evaluate(con, s, nearest_limit=5) for s in scenarios]
    v = lambda tv: None if tv is None else tv.get("value")
    rows = []

    def add(group, label, unit, vals, statuses=None):
        uniq = {round(x, 6) if isinstance(x, float) else x for x in vals}
        rows.append({"group": group, "label": label, "unit": unit, "values": vals, "statuses": statuses or [None] * len(vals), "differs": len(uniq) > 1})

    add("configuration", "Chamber O₂ (experiment zone)", "%", [e["evidence"]["targets"]["o2_pct"] for e in evals])
    add("configuration", "Pressure", "kPa", [v(s["pressure_kPa"]) for s in scenarios], [s["pressure_kPa"]["status"] for s in scenarios])
    add("configuration", "Temperature (experiment zone)", "K", [e["evidence"]["targets"]["temperature_K"] for e in evals])
    add("configuration", "Airflow at experiment", "m/s", [e["evidence"]["targets"]["airflow_m_s"] for e in evals])
    add("configuration", "Gravity", None, [s["gravity"] for s in scenarios])
    add("configuration", "Material class", None, [s["experiment"].get("fuel_class") for s in scenarios])
    add("configuration", "Ventilation", "m³/h", [v(s["ventilation"]["volumetric_flow_m3_h"]) for s in scenarios])
    add("evidence", "Exact NASA matches", "records", [e["evidence"]["coverage"]["exact_matches"] for e in evals])
    add("evidence", "Nearest record distance", "tolerances", [e["evidence"]["nearest"][0]["distance"] if e["evidence"]["nearest"] else None for e in evals])
    add("evidence", "Records at requested gravity", "records", [e["evidence"]["coverage"]["gravity"]["records_at_requested"] for e in evals])
    for mid, scope, name, unit in KEY_OUTPUTS:
        exp_zone = [s["experiment"]["zone_id"] for s in scenarios]
        vals = [_out(e["physics"], mid, f"zone:{z}" if scope == "zone:" else scope, name) for e, z in zip(evals, exp_zone)]
        add("physics", f"{physics.REGISTRY[mid].name.split(' — ')[1]}: {name.replace('_', ' ')}", unit, vals, ["simulated" if x is not None else "not_documented" for x in vals])
    return {"scenarios": [{"id": s.get("id"), "name": s["name"], "version": s.get("version")} for s in scenarios], "rows": rows,
            "note": "Physics rows are model outputs for each scenario's experiment zone; evidence rows are deterministic counts over NASA PSI records. Differences are not risk rankings."}


def report(con, sc, ev=None):
    """Structured scientific report (JSON sections + Markdown) for a scenario. Deterministic for a given scenario."""
    ev = ev or evaluate(con, sc)
    env = environment(con, sc["habitat"]["environment_id"])
    e, ph = ev["evidence"], ev["physics"]
    t = e["targets"]
    fmt = lambda x, nd=4: "not documented" if x is None else (f"{x:.{nd}g}" if isinstance(x, float) else str(x))
    v = lambda tv: None if tv is None else tv.get("value")
    lines = [f"# FIREWISE Digital Twin report — {sc['name']}", ""]
    if sc.get("id"):
        lines.append(f"Scenario `{sc['id']}` version {sc.get('version')} · environment `{env['id']}` ({env['name']}) · engine `{ph['engine_version']}` · input hash `{ph['input_hash']}`")
    else:
        lines.append(f"Unsaved scenario · environment `{env['id']}` · engine `{ph['engine_version']}` · input hash `{ph['input_hash']}`")
    lines += ["", "> Evidence relevance and physics calculations only. This is not a fire-risk assessment and contains no prediction of fire behaviour.", "",
              "## 1. Configuration", "", "| Variable | Value | Unit | Status | Source / note |", "|---|---|---|---|---|"]
    cfg = [("Habitat diameter", sc["habitat"]["diameter_m"], "m"), ("Habitat length", sc["habitat"]["length_m"], "m"),
           ("Pressure", sc["pressure_kPa"], "kPa"), ("Habitat temperature", sc["temperature_K"], "K"),
           ("O₂ (habitat)", sc["composition"]["o2_pct"], "mole %"), ("Ar", sc["composition"].get("ar_pct"), "mole %"),
           ("CO₂", sc["composition"].get("co2_pct"), "mole %"), ("Ventilation", sc["ventilation"]["volumetric_flow_m3_h"], "m³/h"),
           ("Sample length", sc["experiment"].get("characteristic_length_m"), "m"), ("Sample surface temperature", sc["experiment"].get("surface_temperature_K"), "K")]
    for label, tv, unit in cfg:
        lines.append(f"| {label} | {fmt(v(tv))} | {unit} | {(tv or {}).get('status', 'not_documented') if v(tv) is not None else 'not_documented'} | {(tv or {}).get('source') or ''} |")
    lines += [f"| Gravity | {sc['gravity']} | — | user_defined | |",
              f"| Experiment | zone {t['zone_id']}, {sc['experiment'].get('fuel_class') or 'class not set'}{', ' + t['material'] if t['material'] else ''} | — | user_defined | |", "",
              "### Zone conditions", "", "| Zone | O₂ % | Temperature K | Airflow m/s |", "|---|---|---|---|"]
    for z in ev["zone_conditions"]:
        lines.append(f"| {z['zone_id']} {z['name']} | {fmt(v(z['o2_pct']))} ({z['o2_scope']}) | {fmt(v(z['temperature_K']))} ({z['temperature_scope']}) | {fmt(v(z['airflow_m_s']))} |")
    cov = e["coverage"]
    lines += ["", "## 2. NASA evidence", "", f"Method: {e['method']}", "",
              f"- Records considered (non-duplicate combustion/aerosol): **{cov['records_considered']}**",
              f"- Exact matches (variables: {', '.join(e['variables_enabled'])}; gravity {t['gravity']}): **{cov['exact_matches']}**",
              f"- Gravity: {cov['gravity']['statement']}"]
    for inv in cov["investigations"]:
        lines.append(f"  - {inv['investigation_id']} {inv['acronym'] or ''}: {inv['records']} records")
    lines += ["", "### Nearest documented records (closest conditions, not equivalent experiments)", "",
              "| # | Record | Material | O₂ % (status) | Pressure kPa (status) | Compared | Distance | Source |", "|---|---|---|---|---|---|---|---|"]
    for i, n in enumerate(e["nearest"][:10], 1):
        o, p = n["values"]["o2_pct"], n["values"]["pressure_kPa"]
        lines.append(f"| {i} | {n['investigation_id']} {n['acronym'] or ''} test {n['test_label'] or '—'} | {n['fuel_or_material'] or '—'} | "
                     f"{fmt(o['value'])} ({o['status_label']}) | {fmt(p['value'])} ({p['status_label']}) | {len(n['variables_compared'])}/{len(n['variables_enabled'])} | "
                     f"{n['distance']:.3g} | `{n['evidence_id']}` {n['source']['file_name']} row {n['source']['source_row']} |")
    lines += ["", "### Coverage and missing evidence", ""]
    for m in cov["missing_measurements"]:
        lines.append(f"- {m['label']}: documented by {m['records_documenting']} of {cov['records_considered']} records" + (f" — {m['note']}" if m["note"] else ""))
    lines += ["", "## 3. Physics calculations", "", ph["notice"], ""]
    for r in ph["results"]:
        card = physics.REGISTRY[r["model_id"]]
        lines.append(f"### {r['model_name']} v{r['model_version']} — {r['scope']} — {r['status']} (validation: {r['validation_status']})")
        if r["status"] != "completed":
            lines += ["", f"Not computed: {r['reason']}", ""]
            continue
        lines += ["", "| Output | Value | Unit | Validation |", "|---|---|---|---|"]
        for o in r["outputs"]:
            lines.append(f"| {o['name']} | {fmt(o['value'])} | {o['unit']} | {o['validation_status']} |")
        lines += ["", "Equations: " + "; ".join(card.equations), "", "Assumptions: " + " ".join(r["assumptions"]), ""]
        for w in r["warnings"]:
            lines.append(f"Warning: {w}")
        lines.append("")
    lines += ["### Not implemented (no output produced)", ""] + [f"- {m['name']}: {m['validation_summary']}" for m in ph["planned_models"]]
    lines += ["", "## 4. Limitations", "",
              "- Values marked user_defined are scenario inputs, not measurements. Monitoring points are virtual and not connected to telemetry.",
              "- Evidence counts use documented midpoints of NASA ranges; undocumented variables never match.",
              "- No PSI table documents chamber gas temperature; temperature cannot be matched to NASA evidence.",
              "- PSI contains no partial-gravity combustion records.",
              "- No combustion, ignition, extinction or flame-spread model is implemented; FIREWISE does not predict fire behaviour.", ""]
    sections = {"configuration": cfg and [{"label": l, "value": v(tv), "unit": u, "status": (tv or {}).get("status") if v(tv) is not None else "not_documented",
                                           "source": (tv or {}).get("source")} for l, tv, u in cfg],
                "zone_conditions": ev["zone_conditions"], "evidence": {"targets": t, "coverage": cov, "nearest": e["nearest"][:10], "method": e["method"]},
                "physics": ph}
    return {"title": f"FIREWISE Digital Twin report — {sc['name']}", "scenario_id": sc.get("id"), "scenario_version": sc.get("version"),
            "input_hash": ph["input_hash"], "engine_version": ph["engine_version"], "sections": sections, "markdown": "\n".join(lines)}
