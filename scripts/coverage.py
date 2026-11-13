#!/usr/bin/env python3
"""Evidence-coverage grid (Research Gap Map) and scenario-window counts over derived/runs.csv.

Usage: python3 -I scripts/coverage.py derived/runs.csv derived/coverage
Writes <out>.csv (cells) and <out>_summary.json (headline numbers + scenario counts).

Rules (FINAL_DATA_CONTRACT.md):
  * only combustion/aerosol records (fuel_class != none) and non-duplicates are counted
  * O2 bands use AMBIENT O2 only (inverse-flame burner-stream and FLEX-2 envelopes are excluded)
  * a record falls in a band by the midpoint of its documented interval; undocumented -> "not documented"
  * pressure bands are defined in psia with edges at the scenario boundaries (8.2, 10.2 psia)
"""
import collections, csv, json, sys

PSIA_PER_ATM = 14.6959
O2_BANDS = [(None, 20.5, "<20.5%"), (20.5, 23, "20.5-23% (air)"), (23, 30, "23-30%"), (30, 36, "30-36%"), (36, None, ">36%")]
P_BANDS = [(None, 8.2, "<8.2 psia"), (8.2, 10.2, "8.2-10.2 psia"), (10.2, 13.7, "10.2-13.7 psia"),
           (13.7, 15.7, "13.7-15.7 psia (~1 atm)"), (15.7, None, ">15.7 psia")]
SCENARIOS = {  # ambient O2 window (%), pressure window (psia); see FINAL_DATA_CONTRACT §7
    "iss": ((20.0, 22.0), (14.2, 15.2)),
    "exploration_envelope": ((30.0, 36.0), (8.2, 10.2)),
    "moon_base_challenge": ((30.0, 100.0), (0.0, 10.2)),
    "fm2_point": ((32.0, 36.0), (7.2, 9.2)),
}


def mid(r, k, u):
    a, b = r[f"{k}_min_{u}"], r[f"{k}_max_{u}"]
    return None if a in ("", None) else (float(a) + float(b)) / 2


def band(v, bands):
    if v is None:
        return "not documented"
    for lo, hi, label in bands:
        if (lo is None or v >= lo) and (hi is None or v < hi) or (hi is not None and v == hi and label.startswith("8.2")):
            return label
    return bands[-1][2]


def ambient_o2(r):
    return mid(r, "o2", "pct") if r["o2_context"] == "ambient" else None


def p_psia(r):
    v = mid(r, "p", "atm")
    return None if v is None else v * PSIA_PER_ATM


def in_window(r, win):
    (olo, ohi), (plo, phi) = win
    o, p = ambient_o2(r), p_psia(r)
    return o is not None and p is not None and olo <= o <= ohi and plo <= p <= phi


def main():
    allrows = list(csv.DictReader(open(sys.argv[1])))
    rows = [r for r in allrows if r["fuel_class"] != "none" and not r["duplicate_of"]]
    out = sys.argv[2]
    cells, who = collections.Counter(), collections.defaultdict(collections.Counter)
    for r in rows:
        k = (r["gravity_regime"], r["fuel_class"], band(ambient_o2(r), O2_BANDS), band(p_psia(r), P_BANDS))
        cells[k] += 1
        who[k][r["acronym"]] += 1
    with open(out + ".csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["gravity_regime", "fuel_class", "o2_band_ambient", "p_band", "records", "investigations"])
        for k, n in sorted(cells.items()):
            w.writerow([*k, n, "; ".join(f"{a}:{c}" for a, c in who[k].most_common())])
    scen = {}
    for sid, win in SCENARIOS.items():
        sel = [r for r in rows if in_window(r, win)]
        scen[sid] = {"records": len(sel), "by_investigation": dict(collections.Counter(r["investigation"] for r in sel)),
                     "by_fuel_class": dict(collections.Counter(r["fuel_class"] for r in sel))}
    sol = [r for r in rows if r["fuel_class"] == "solid"]
    o2sol = [float(r["o2_max_pct"]) for r in sol if r["o2_max_pct"]]
    summary = {
        "records_counted": len(rows),
        "records_by_fuel_class": dict(collections.Counter(r["fuel_class"] for r in rows)),
        "records_by_gravity": dict(collections.Counter(r["gravity_regime"] for r in rows)),
        "ambient_o2_documented": sum(1 for r in rows if ambient_o2(r) is not None),
        "pressure_documented": sum(1 for r in rows if p_psia(r) is not None),
        "scenarios": scen,
        "solid_records": len(sol), "solid_with_pressure": sum(1 for r in sol if r["p_min_atm"]),
        "solid_with_o2": len(o2sol), "solid_o2_max_pct": max(o2sol) if o2sol else None,
        "partial_gravity_records": sum(1 for r in rows if r["gravity_regime"] == "partial_gravity"),
        "bands": {"o2_ambient_pct": [b[2] for b in O2_BANDS], "pressure_psia": [b[2] for b in P_BANDS]},
    }
    json.dump(summary, open(out + "_summary.json", "w"), indent=1)
    print(json.dumps({k: summary[k] for k in ("records_counted", "scenarios", "solid_records", "solid_with_pressure",
                                               "solid_o2_max_pct", "partial_gravity_records")}, indent=1))


if __name__ == "__main__":
    main()
