#!/usr/bin/env python3
"""Independently recompute every quantitative FIREWISE claim from derived/runs.csv + raw PSI tables.

Usage: python3 -I scripts/verify_claims.py <NasaSA root>  ->  writes derived/claims_check.json, prints it.
This is deliberately a SECOND implementation (separate from coverage.py / the API) so tests can cross-check them.
Read-only with respect to Data/ and sources/.
"""
import collections, csv, glob, json, os, re, sys

ROOT = os.path.abspath(sys.argv[1])
P = lambda *a: os.path.join(ROOT, *a)
runs = list(csv.DictReader(open(P("derived/runs.csv"))))
flags = list(csv.DictReader(open(P("derived/runs_flags.csv"))))
f = lambda v: float(v) if v not in ("", None) else None
PS = 14.6959
out = {}


def mid(r, k, u):
    a, b = f(r[f"{k}_min_{u}"]), f(r[f"{k}_max_{u}"])
    return None if a is None else (a + b) / 2


# ---------------------------------------------------------------- 1. counts, identity, provenance
keys = [r["row_key"] for r in runs]
out["rows_total"] = len(runs)
out["row_keys_unique"] = len(keys) == len(set(keys))
out["rows_by_granularity"] = dict(collections.Counter(r["row_granularity"] for r in runs))
comb = [r for r in runs if r["row_granularity"] not in ("flow_visualization", "figure_reference")]
out["combustion_aerosol_rows"] = len(comb)
out["investigations_with_tables"] = len({r["investigation"] for r in runs})
out["flight_investigations_in_combustion_rows"] = len({r["investigation"] for r in comb})
out["duplicate_rows"] = dict(collections.Counter(r["investigation"] for r in runs if r["duplicate_of"]))
out["duplicate_rows_total"] = sum(out["duplicate_rows"].values())
out["individual_test_rows"] = sum(1 for r in runs if r["row_granularity"] == "test")
out["unique_individual_tests"] = sum(1 for r in runs if r["row_granularity"] == "test" and not r["duplicate_of"])
out["rows_missing_provenance"] = sum(1 for r in runs if not (r["source_file"] and r["source_row"] and r["raw"]))
out["flags_total"] = len(flags)
out["flags_by_severity"] = dict(collections.Counter(fl["severity"] for fl in flags))
out["rows_with_anomaly"] = len({fl["row_key"] for fl in flags if fl["severity"] == "anomaly"})
keyset = set(keys)
out["orphan_flags"] = sum(1 for fl in flags if fl["row_key"] not in keyset)
out["status_vocab"] = {k: dict(collections.Counter(r[k] for r in runs)) for k in ("o2_status", "p_status", "flow_status")}
out["status_value_mismatch"] = sum(1 for r in runs for k, u in (("o2", "pct"), ("p", "atm"), ("flow", "cm_s"))
                                   if bool(r[f"{k}_min_{u}"]) != (r[f"{k}_status"] != "missing"))
sp = [json.loads(r["raw"]) for r in runs if r["investigation"] == "PSI-107"]
out["spice_rows"], out["spice_distinct_ignitions"] = len(sp), len({(x["GMT date"], x["GMT ignition"]) for x in sp})


# ---------------------------------------------------------------- 2. ambient-O2 envelopes (inverse decided from raw table name)
def raw_inverse(r):
    return r["investigation"] in ("PSI-10", "PSI-159") and "Inverse" in r["source_file"]


amb = [r for r in comb if not raw_inverse(r) and r["investigation"] != "PSI-68" and not r["duplicate_of"]]
out["inverse_flame_rows"] = sum(1 for r in comb if raw_inverse(r))
out["inverse_rows_with_burner_stream_context"] = sum(1 for r in comb if raw_inverse(r) and r["o2_context"] == "burner_stream")
ENV = {
    "A_exploration_envelope_O2_30_36_P_8.2_10.2psia": lambda o, p: 30 <= o <= 36 and 8.2 <= p <= 10.2,
    "B_moon_base_challenge_O2_ge30_P_le10.2psia": lambda o, p: o >= 30 and p <= 10.2,
    "C_fm2_point_O2_32_36_P_7.2_9.2psia": lambda o, p: 32 <= o <= 36 and 7.2 <= p <= 9.2,
    "D_bracket_O2_30_36_P_7_11psia": lambda o, p: 30 <= o <= 36 and 7.0 <= p <= 11.0,
    "E_iss_O2_20_22_P_14.2_15.2psia": lambda o, p: 20 <= o <= 22 and 14.2 <= p <= 15.2,
}
for name, pred in ENV.items():
    sel = [r for r in amb if mid(r, "o2", "pct") is not None and mid(r, "p", "atm") is not None
           and pred(mid(r, "o2", "pct"), mid(r, "p", "atm") * PS)]
    out[f"ambient_{name}"] = {
        "n": len(sel), "by_investigation": dict(collections.Counter(r["investigation"] for r in sel)),
        "by_status": dict(collections.Counter(f"O2 {r['o2_status']} / P {r['p_status']}" for r in sel)),
        "p_psia_range": [round(min(mid(r, "p", "atm") for r in sel) * PS, 2), round(max(mid(r, "p", "atm") for r in sel) * PS, 2)] if sel else None,
    }
out["o2_30_36_pressure_undocumented"] = dict(collections.Counter(
    r["acronym"] for r in amb if mid(r, "o2", "pct") is not None and 30 <= mid(r, "o2", "pct") <= 36 and not r["p_min_atm"]))

# ---------------------------------------------------------------- 3. solids, gravity
sol = [r for r in comb if r["fuel_class"] == "solid"]
o2s = [f(r["o2_max_pct"]) for r in sol if r["o2_max_pct"]]
out.update(solid_rows=len(sol), solid_with_pressure=sum(1 for r in sol if r["p_min_atm"]), solid_with_o2=len(o2s),
           solid_o2_max_pct=max(o2s) if o2s else None,
           solid_by_investigation=dict(collections.Counter(r["acronym"] for r in sol)))
out["partial_gravity_rows"] = sum(1 for r in comb if r["gravity_regime"] == "partial_gravity")
out["gravity_regimes"] = dict(collections.Counter(r["gravity_regime"] for r in comb))

# ---------------------------------------------------------------- 4. CFI-G
cfg = [r for r in runs if r["investigation"] == "PSI-159"]
cool = [r for r in cfg if (json.loads(r["raw"]).get("Cool flame?") or "").strip().lower().startswith("yes")]
out["cfig_rows"] = len(cfg)
out["cfig_cool_yes"] = [{"test": r["test_label"], "fuel": json.loads(r["raw"]).get("Fuel"),
                         "xo2_before": json.loads(r["raw"]).get(" XO2 before test"),
                         "p_bar_raw": json.loads(r["raw"]).get("approx p (bar)"),
                         "label": json.loads(r["raw"]).get("Cool flame?")} for r in cool]
normal = [json.loads(r["raw"]) for r in cfg if "Normal" in r["source_file"]]
out["cfig_normal_rows"] = len(normal)
out["cfig_cool_no"] = sum(1 for x in normal if re.match(r"no\b", (x.get("Cool flame?") or "").strip().lower()))
out["cfig_cool_blank"] = sum(1 for x in normal if not (x.get("Cool flame?") or "").strip())
raw_tables = " ".join(open(p, errors="replace").read() for p in glob.glob(P("sources/psi_files/PSI-159/Experimental table/*.csv")))
out["cfig_tables_mention_pentane"] = bool(re.search(r"pentan", raw_tables, re.I))
out["cfig_objective_mentions_pentane"] = "pentane" in (json.load(open(P("sources/psi_api/PSI-159.json"))).get("objective") or "").lower()
out["local_tests"] = [{"test": r["test_label"], "row_key": r["row_key"], "o2_pct": r["o2_min_pct"], "o2_context": r["o2_context"],
                       "p_bar_raw": json.loads(r["raw"]).get("approx p (bar)"), "outcome": r["outcome"]}
                      for r in cfg if r["test_label"] in ("21265C3", "21265H1")]

# ---------------------------------------------------------------- 5. lineage, misc
flex_nums = [int(r["test_label"].split("/")[0]) for r in runs if r["investigation"] == "PSI-69"]
cfi_nums = [int(json.loads(r["raw"])["Flex Number"]) for r in runs if r["investigation"] == "PSI-39"]
out["flex_test_number_range"], out["cfi_flex_number_range"] = [min(flex_nums), max(flex_nums)], [min(cfi_nums), max(cfi_nums)]
out["cfi_rows"], out["cfi_unique"] = len(cfi_nums), sum(1 for r in runs if r["investigation"] == "PSI-39" and not r["duplicate_of"])
rec47 = json.load(open(P("sources/psi_api/PSI-47.json")))
out["daft_objective_says_mitigate_SAME_risk"] = "mitigate the risk for the Smoke Aerosol Measurement Experiment" in (rec47.get("objective") or "")
out["saffire_flowvis_rows"] = sum(1 for r in runs if r["row_granularity"] == "flow_visualization")
fl = [r for r in runs if r["investigation"] == "PSI-69" and r["fuel_or_material"] == "Methanol" and r["diluent"] == "N2"
      and r["o2_min_pct"] and f(r["o2_min_pct"]) <= 15]
out["flex_methanol_n2_le15_tests"] = len(fl)
out["flex_methanol_n2_le15_extinction"] = sum(1 for r in fl if "end=Extinction" in r["outcome"])

json.dump(out, open(P("derived/claims_check.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
