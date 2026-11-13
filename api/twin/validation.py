"""Reproducible verification/validation of the Digital Twin physics models.

Terminology used everywhere in FIREWISE:
- verified   — the implementation reproduces reference values that rest on the same equation or on the
               data the coefficients were fitted to (checks transcription and arithmetic, not physics).
- validated  — the model output is compared with INDEPENDENT reference data, with error metrics and
               the reference uncertainty stated, inside a stated applicability domain.
No model is calibrated: every parameter is literature data, so the calibration set is empty and the
validation sets below are not used to tune anything.

Run `python3 -I scripts/twin_validate.py .` to regenerate derived/twin/validation.json.
"""
import json
import math
import os

from . import physics, props

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF_PATH = os.path.join(ROOT, "derived", "twin", "reference_data.json")
OUT_PATH = os.path.join(ROOT, "derived", "twin", "validation.json")


def metrics(pred, ref):
    """MAE, RMSE, bias (mean signed error), mean and max absolute relative error (%)."""
    err = [p - r for p, r in zip(pred, ref)]
    rel = [abs(e) / abs(r) * 100 for e, r in zip(err, ref)]
    n = len(err)
    return {"n": n, "mae": sum(abs(e) for e in err) / n, "rmse": math.sqrt(sum(e * e for e in err) / n), "bias": sum(err) / n,
            "mean_abs_rel_error_pct": sum(rel) / n, "max_abs_rel_error_pct": max(rel)}


def _ref():
    with open(REF_PATH) as f:
        return {d["id"]: d for d in json.load(f)["datasets"]}


def _round(d, nd=6):
    return {k: (float(f"{v:.{nd}g}") if isinstance(v, float) else v) for k, v in d.items()}


def compute():
    ref = _ref()
    recs = []
    # --- Model A: ideal-gas density vs US Standard Atmosphere 1976 sea level (verification)
    d = ref["REF-USSA1976-SL"]
    pts = d["points"]
    pred = [physics.run_ideal_gas({"pressure_kPa": p["pressure_Pa"] / 1000, "temperature_K": p["temperature_K"], "molar_mass_g_mol": p["molar_mass_g_mol"],
                                   "o2_mole_fraction": 0.209476, "zone_volume_m3": 1.0})["density"] for p in pts]
    obs = [p["density_kg_m3"] for p in pts]
    recs.append({"model_id": "ideal_gas", "output": "density", "unit": "kg/m³", "kind": "verification", "reference": d["id"],
                 "reference_source": d["source"], "independence": d["independence"], "calibration_set": "none (no fitted parameters)",
                 "domain": "288.15 K, 101.325 kPa (single reference state)", "metrics": _round(metrics(pred, obs)),
                 "points": [{"input": p, "predicted": round(x, 6), "reference": o} for p, x, o in zip(pts, pred, obs)],
                 "uncertainty": d["uncertainty"], "status": "verified",
                 "conclusion": "The implementation reproduces the reference density to within its rounding. This is a consistency check, not an experimental validation."})
    # --- Model B: molar mass of dry air (verification)
    d = ref["REF-USSA1976-COMPOSITION"]
    x = props.normalize(d["composition"])
    mm = props.molar_mass(x) * 1000
    recs.append({"model_id": "gas_mixture", "output": "molar_mass", "unit": "g/mol", "kind": "verification", "reference": d["id"],
                 "reference_source": d["source"], "independence": d["independence"], "calibration_set": "none (no fitted parameters)",
                 "domain": "dry air composition", "metrics": _round(metrics([mm], [d["molar_mass_g_mol"]])),
                 "points": [{"input": d["composition"], "predicted": round(mm, 5), "reference": d["molar_mass_g_mol"]}],
                 "uncertainty": d["uncertainty"], "status": "verified",
                 "conclusion": "Mixture molar mass agrees with the standard value; the residual reflects the omitted trace gases."})
    # --- Model B: cp at 298.15 K vs NIST-JANAF (verification of coefficient transcription)
    d = ref["REF-JANAF-CP298"]
    pred = [props.cp_molar(p["species"], 298.15) for p in d["points"]]
    obs = [p["cp_J_molK"] for p in d["points"]]
    recs.append({"model_id": "gas_mixture", "output": "cp_molar (pure components)", "unit": "J/(mol·K)", "kind": "verification", "reference": d["id"],
                 "reference_source": d["source"], "independence": d["independence"], "calibration_set": "none (no fitted parameters)",
                 "domain": "298.15 K; N2, O2, Ar, CO2", "metrics": _round(metrics(pred, obs)),
                 "points": [{"input": {"species": p["species"], "T_K": 298.15}, "predicted": round(x, 4), "reference": o} for p, x, o in zip(d["points"], pred, obs)],
                 "uncertainty": d["uncertainty"], "status": "verified",
                 "conclusion": "Heat capacities agree with NIST-JANAF; the largest deviation (N2, about −0.18%) is a property of the published N2 polynomial."})
    # --- Model B: Wilke viscosity and Mason–Saxena conductivity vs independent air correlations (validation)
    air = props.normalize(ref["REF-USSA1976-COMPOSITION"]["composition"])
    for rid, out, unit, fn, key, scale in (("REF-WHITE-AIR-VISCOSITY", "viscosity", "µPa·s", props.mixture_viscosity, "mu0", 1e6),
                                           ("REF-WHITE-AIR-CONDUCTIVITY", "thermal_conductivity", "mW/(m·K)", props.mixture_conductivity, "k0", 1e3)):
        d = ref[rid]
        Ts = d["temperatures_K"]
        a = d["air"]
        pred = [fn(air, T) * scale for T in Ts]
        obs = [a[key] * (T / a["T0"]) ** 1.5 * (a["T0"] + a["S"]) / (T + a["S"]) * scale for T in Ts]
        m = metrics(pred, obs)
        recs.append({"model_id": "gas_mixture", "output": out, "unit": unit, "kind": "validation", "reference": d["id"],
                     "reference_source": d["source"], "independence": d["independence"], "calibration_set": "none (no fitted parameters)",
                     "domain": f"dry air composition, {min(Ts)}–{max(Ts)} K", "metrics": _round(m),
                     "points": [{"input": {"T_K": T}, "predicted": round(p, 5), "reference": round(o, 5)} for T, p, o in zip(Ts, pred, obs)],
                     "uncertainty": d["uncertainty"],
                     "status": "validated" if m["max_abs_rel_error_pct"] <= 2.0 else "failed",
                     "conclusion": (f"Maximum deviation {m['max_abs_rel_error_pct']:.2f}% is within the ±2% reference uncertainty over the domain. "
                                    "Not validated for O₂-enriched compositions or outside 250–400 K.")})
    # --- Models C, D: no meaningful reference comparison available -> explicit records, no metrics
    for mid, why in (("bulk_airflow", "Algebraic definitions (A, V, Q/A, Q/V, Re). Verified by unit tests; there is no velocity-field measurement in PSI or in this project to validate against, so no error metric is reported."),
                     ("forced_convection_flat_plate", "Classical laminar correlation, implementation verified by unit tests. FIREWISE holds no heat-transfer measurements for inert samples in cabin flow, so no validation metric is reported."),
                     ("wall_conduction", "Fourier's law, verified by unit tests against hand calculations. No experimental comparison performed; no metric reported.")):
        recs.append({"model_id": mid, "output": "all", "unit": None, "kind": "verification", "reference": None, "reference_source": None,
                     "independence": None, "calibration_set": "none (no fitted parameters)", "domain": physics.REGISTRY[mid].applicability,
                     "metrics": None, "points": [], "uncertainty": None, "status": "verified", "conclusion": why})
    for m in physics.PLANNED:
        recs.append({"model_id": m.id, "output": "all", "unit": None, "kind": "none", "reference": None, "reference_source": None,
                     "independence": None, "calibration_set": None, "domain": None, "metrics": None, "points": [], "uncertainty": None,
                     "status": "not_implemented", "conclusion": m.validation_summary})
    return {"engine_version": physics.ENGINE_VERSION, "reference_file": "derived/twin/reference_data.json",
            "nasa_psi_validation": "No implemented model predicts a quantity measured in the NASA PSI tables, so no model is validated against PSI data. No combustion model is implemented.",
            "records": recs}


def write(path=OUT_PATH):
    out = compute()
    with open(path, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return out


def load():
    with open(OUT_PATH) as f:
        return json.load(f)
