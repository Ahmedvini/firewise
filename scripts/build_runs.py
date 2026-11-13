#!/usr/bin/env python3
"""Normalize PSI "Experimental table" CSVs into one condition-record table (FINAL_DATA_CONTRACT.md).

Usage: python3 -I scripts/build_runs.py <psi_files_dir> <out_prefix>
Writes <out_prefix>.csv / .json (one row per normalized record) and <out_prefix>_flags.csv (quality flags).

Contract highlights
  * row_key = {investigation}:{table_slug}:r{source_row}[:{split}]  (source_row = CSV record number, header = 1)
  * test_label = the investigation's own (non-unique) identifier; duplicate_of marks exact duplicate source rows
  * row_granularity says what one row represents (test, test_point, test_day, envelope, ...)
  * o2_context distinguishes chamber (ambient) O2 from inverse-flame burner-stream O2
  * statuses: measured | derived | reported | specified | missing   (never inferred; missing is never 0)
  * raw keeps the verbatim source row; every meaning-changing transformation emits a coded flag
"""
import csv, glob, json, os, re, sys

FIELDS = ["row_key", "test_label", "investigation", "acronym", "source_table_id", "source_file", "source_row",
          "row_granularity", "duplicate_of", "date", "fuel_or_material", "fuel_class", "fuel_class_detail",
          "geometry", "diluent", "gravity_regime", "platform",
          "o2_min_pct", "o2_max_pct", "o2_status", "o2_context",
          "p_min_atm", "p_max_atm", "p_status", "p_context",
          "flow_min_cm_s", "flow_max_cm_s", "flow_status", "flow_context",
          "outcome", "flags", "raw"]

PLATFORM = {**{a: "ISS-CIR" for a in ("PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159", "PSI-39", "PSI-68", "PSI-69")},
            **{a: "ISS-MSG" for a in ("PSI-25", "PSI-26", "PSI-101", "PSI-102", "PSI-106", "PSI-107")},
            "PSI-47": "ISS-cabin", "PSI-98": "Cygnus", "PSI-99": "Cygnus", "PSI-100": "Cygnus", "PSI-142": "ground-lab"}
GRANULARITY = {
    "PSI-10": "test", "PSI-159": "test", "PSI-39": "test", "PSI-69": "test", "PSI-25": "test", "PSI-26": "test",
    "PSI-101": "test", "PSI-98": "test", "PSI-99": "test", "PSI-100": "test",
    "PSI-20": "test_day_o2_level", "PSI-21": "test_day", "PSI-22": "test_day", "PSI-23": "test_day",
    "PSI-106": "test_date", "PSI-107": "test_point", "PSI-68": "condition_envelope", "PSI-47": "session",
    "PSI-102": "material_condition_set", "PSI-142": "figure_reference",
}


def num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def nums(s):
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(s or ""))]


def table_slug(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = stem.split("Experimental table_", 1)[-1]
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")


def read(path):
    """Return header and [(source_row, row_dict)] where source_row is the CSV record number (header = 1).
    Blank records are skipped but numbering is preserved, so provenance points at the true source record."""
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        recs = list(csv.reader(f))
    hdr = [h.strip() for h in recs[0]]
    return hdr, [(n + 2, dict(zip(hdr, r))) for n, r in enumerate(recs[1:]) if any(c.strip() for c in r)]


def base(acc, acr, path, recno, raw, **kw):
    r = {k: "" for k in FIELDS}
    r.update(investigation=acc, acronym=acr, source_file=os.path.basename(path), source_row=recno,
             source_table_id=f"{acc}:{table_slug(path)}", row_key=f"{acc}:{table_slug(path)}:r{recno}",
             raw=json.dumps(raw, ensure_ascii=False), gravity_regime="microgravity", platform=PLATFORM.get(acc, ""),
             row_granularity=GRANULARITY.get(acc, "test"), o2_status="missing", p_status="missing", flow_status="missing")
    r["_flags"] = []
    r.update(kw)
    return r


SEVERITY = {  # anomaly = defect in the NASA source table; limitation = value not documented; note = interpretation aid
    "pct_format_artifact": "anomaly", "autoincrement_artifact": "anomaly", "exact_duplicate": "anomaly",
    "encoding_loss": "anomaly", "zero_as_missing": "anomaly", "malformed_date": "anomaly", "missing_decimal": "anomaly",
    "merged_cell_inherited": "anomaly", "test_label_reused": "anomaly", "negative_flow": "anomaly",
    "header_interpretation": "anomaly",
    "conditions_not_in_table": "limitation", "pressure_not_identified": "limitation", "flow_uncalibrated": "limitation",
    "burner_stream_o2": "note", "approximate_value": "note", "day_split_by_o2": "note", "multiple_o2_levels": "note",
    "envelope_row": "note", "not_a_burn": "note", "not_a_test": "note", "ramped_test": "note",
    "flow_from_record_text": "note", "continuation_row_merged": "note",
}


def flag(r, code, msg):
    assert code in SEVERITY, f"unclassified flag code {code}"
    r["_flags"].append((code, msg))


def setrange(r, key, vals, status, context=None):
    vals = [v for v in vals if v is not None]
    if vals:
        suffix = {"o2": "_pct", "p": "_atm", "flow": "_cm_s"}[key]
        r[f"{key}_min{suffix}"] = min(vals)
        r[f"{key}_max{suffix}"] = max(vals)
        r[f"{key}_status"] = status
        if context:
            r[f"{key}_context"] = context


# ---------------------------------------------------------------- per-investigation normalizers
def bre(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        r = base("PSI-20", "ACME BRE", path, recno, x, test_label=f"{x['Year']}-{x['Month']}-{x['Date']}",
                 date=f"{x['Year']}-{x['Month']}-{x['Date']}", fuel_or_material=x["Fuel Bottle"].strip(),
                 fuel_class="solid_emulating_gas_burner", fuel_class_detail="porous flat burner emulating a burning solid",
                 geometry=f"flat porous burner {x['Burner Size (mm)']} mm", diluent="N2",
                 outcome=f"flames ignited that day (all listed O2 levels): {x['Flames Ignited']}")
        o2, artifacts = [], []
        for tok in str(x["Oxygen Conc (percent)"]).split(";"):
            t = tok.strip()
            if re.fullmatch(r"\d{3,4}%", t):  # spreadsheet percent-format artifact, e.g. 3400% == 34 %
                v = float(t[:-1]) / 100
                o2.append(v); artifacts.append((t, v))
            elif num(t) is not None:
                o2.append(num(t))
        for v in (o2 or [None]):
            rr = dict(r); rr["_flags"] = list(r["_flags"])
            for t, av in artifacts:
                if v == av:
                    flag(rr, "pct_format_artifact", f"O2 '{t}' read as {av:g}% (spreadsheet percent-format artifact)")
            flag(rr, "pressure_not_identified", "chamber pressure varied between tests but is not identified in the PSI table")
            setrange(rr, "flow", [0.0], "specified", "quiescent")
            flag(rr, "flow_from_record_text", "flow 0 cm/s: 'quiescent microgravity ambient' per PSI-20 objective")
            if v is not None:
                rr["row_key"] = f"{r['row_key']}:o2={v:g}"
                setrange(rr, "o2", [v], "specified", "ambient")
                if len(o2) > 1:
                    flag(rr, "day_split_by_o2", f"test day listed {len(o2)} O2 levels; ignition count is for the whole day")
            out.append(rr)
    return out


def _fix_autoincrement(r, fuel):
    for pat, good in ((r"(\d+%) CH(\d+)", "CH4"), (r"(\d+%) C2H(\d+)", "C2H4")):
        m = re.fullmatch(pat, fuel)
        if m and m.group(2) != "4":  # CH5..CH14 / C2H5.. are not bottled fuels: auto-increment artifact
            flag(r, "autoincrement_artifact", f"fuel '{fuel}' read as '{m.group(1)} {good}' (spreadsheet auto-increment artifact)")
            return f"{m.group(1)} {good}"
    return fuel


def cld(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        r = base("PSI-21", "ACME CLD Flame", path, recno, x, test_label=x["Test Day"].strip(), date=f"YYDDD {x['Test Day']}",
                 fuel_class="gaseous", fuel_class_detail="coflow laminar diffusion flame", geometry="coflow burner",
                 diluent="N2", outcome=f"flames ignited: {x['Flames ignited']}; fuel conc range {x['Fuel conc. Range']}")
        r["fuel_or_material"] = _fix_autoincrement(r, x["Fuel Bottle"].strip())
        flag(r, "conditions_not_in_table", "coflow O2, pressure and flow not in PSI table")
        out.append(r)
    return out


def efield(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        if not x.get("Test Day", "").strip():  # continuation record = extra fuel concentration for the previous day
            if out:
                out[-1]["outcome"] += f"; also fuel conc {x.get('Fuel Conc','').strip()} (source row {recno})"
                flag(out[-1], "continuation_row_merged", f"continuation source row {recno} merged into this test day")
            continue
        r = base("PSI-22", "ACME E-FIELD Flames", path, recno, x, test_label=x["Test Day"].strip(),
                 date=f"{x['Year']}-{x['Month']}-{x['Date']}", fuel_or_material=x["Fuel Bottle"].strip(),
                 fuel_class="gaseous", fuel_class_detail="laminar jet/coflow flame in electric field",
                 geometry=x["Test Type"].strip(), diluent="N2",
                 outcome=f"mesh polarity {x['Mesh Polarity']}; fuel conc {x['Fuel Conc']}; flames ignited {x['Flames Ignited']}")
        flag(r, "conditions_not_in_table", "O2, pressure and flow not in PSI table")
        out.append(r)
    return out


def flame_design(path):
    hdr, rows = read(path); out = []
    inverse = "Inverse" in os.path.basename(path)
    for recno, x in rows:
        r = base("PSI-10", "ACME Flame Design", path, recno, x, test_label=x["Test"].strip(), date=f"test day index {x['Day']}",
                 fuel_or_material=("C2H4 ambient (inverse flame)" if inverse else x.get("Fuel", "")),
                 fuel_class="gaseous", fuel_class_detail=("inverse" if inverse else "normal") + " spherical diffusion flame",
                 geometry="porous spherical burner", diluent="N2",
                 outcome=f"{'inverse' if inverse else 'normal'} flame; Tad {x.get('Tad (K)','')} K; mean Zst {x.get('mean Zst','')}")
        if inverse:  # O2/N2 issued from the burner into a C2H4/N2 ambient
            r["o2_context"] = "burner_stream"
            v = num(x.get("XO2"))
            setrange(r, "o2", [v * 100 if v is not None else None], "specified", "burner_stream")
            flag(r, "burner_stream_o2", "inverse flame: XO2 is the burner oxidizer stream, not the chamber atmosphere")
        else:
            vals = [num(x.get("XO2 (init)")), num(x.get("XO2 (final)"))]
            setrange(r, "o2", [v * 100 for v in vals if v is not None], "measured", "ambient")
        setrange(r, "p", [num(x.get("pinit (atm)")), num(x.get("pfinal (atm)"))], "measured", "chamber")
        if any(str(v).strip().upper() == "RAMPED" for v in x.values()):
            flag(r, "ramped_test", "flow/composition RAMPED during test: per-test mass flows not single-valued")
        out.append(r)
    return out


def bass2(path):
    hdr, rows = read(path); out = []
    o2i = next(h for h in hdr if h.startswith("Calibrated  initial O2") or h.startswith("Calibrated initial O2"))
    for recno, x in rows:
        mat = re.sub(r"\s+", " ", x["Fuel Sample Material"]).strip()
        r = base("PSI-25", "BASS-II", path, recno, x, test_label=x["Test #"].strip(), date=x["Date"],
                 fuel_or_material=mat, fuel_class="solid", geometry=mat,
                 outcome=f"O2 final {x.get('Calibrated final O2 % by vol','')}%; CO final {x.get('Final CO (ppm)','')} ppm")
        setrange(r, "o2", [num(x[o2i])], "measured", "ambient")  # initial O2 = condition; final O2 is an outcome
        r["flow_context"] = "fan_setting_uncalibrated"
        flag(r, "flow_uncalibrated", "flow given only as fan/air display settings (not cm/s)")
        out.append(r)
    return out


def bass(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        r = base("PSI-26", "BASS", path, recno, x, test_label=f"{x.get('As Run Test #','').strip()}/{x.get('Test #','').strip()}",
                 date=x["Date"], fuel_or_material=x.get("Fuel Sample Material", "").strip(), fuel_class="solid",
                 geometry=x.get("Fuel Sample Material", "").strip())
        if "`" in x["Date"]:
            flag(r, "malformed_date", f"malformed date '{x['Date']}'")
        flag(r, "conditions_not_in_table", "O2, pressure and flow not in PSI table")
        out.append(r)
    return out


def daft(path):
    hdr, rows = read(path)
    return [base("PSI-47", "DAFT / DAFT-2", path, recno, x, test_label=x["Session Name"], date=x["Actual Day"],
                 fuel_or_material=x["Sample Material"], fuel_class="dust_aerosol",
                 fuel_class_detail="Arizona Road Dust aerosol (non-combustion instrument test)",
                 geometry=x["Hardware Description"], outcome=f"sampled: {x['Sampled Location']}") for recno, x in rows]


def flex2(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        fuel = x["Sample (Fuel Type)"].strip()
        r = base("PSI-68", "FLEX-2", path, recno, x, test_label=fuel,
                 fuel_or_material=fuel, fuel_class="liquid_droplet",
                 geometry=f"free droplet, d0 {x['Initial Droplet Diameter (mm)']} mm",
                 diluent=x["Ambient Gas Mixture"].strip(), outcome="condition envelope per fuel (not per test)")
        setrange(r, "o2", [v * 100 for v in nums(x["Oxygen Mole Fraction"])], "specified", "envelope")
        setrange(r, "p", nums(x["Ambient Pressure (atm)"]), "specified", "envelope")
        setrange(r, "flow", nums(x["Flow Velocity (cm/s)"]), "specified", "envelope")
        flag(r, "envelope_row", "envelope row: conditions are ranges across a test series, not a single test")
        out.append(r)
    return out


def flex(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        dil = [g for g, k in (("N2", "N initial ambient composition; mole fraction"),
                              ("CO2", "CO initial ambient composition; mole fraction"),
                              ("He", "He initial ambient composition; mole fraction")) if (num(x.get(k)) or 0) > 0]
        r = base("PSI-69", "FLEX", path, recno, x, test_label=f"{x['FLEX Test #'].strip()} / {x['FLEX Identifier'].strip()}",
                 date=x["Test Date"], fuel_or_material=x["Fuel"], fuel_class="liquid_droplet",
                 geometry=f"free droplet, d0 {x['Droplet initial diameter; mm']} mm", diluent="+".join(dil),
                 outcome=(f"end={x['Test end']}; extinction d {x['Visible flame extinction diameter; mm']} mm; "
                          f"burning rate {x['Burning rate; mm']}; burn time {x['Burn time; s']} s"))
        if "�" in x.get("Droplet initial diameter; mm", ""):
            flag(r, "encoding_loss", "initial droplet diameter unreadable (encoding loss in PSI CSV)")
        o2 = num(x.get("O initial ambient composition; mole fraction"))
        setrange(r, "o2", [o2 * 100 if o2 is not None else None], "measured", "ambient")
        p = num(x.get("Ambient pressure; mmHg"))
        if p == 0:
            flag(r, "zero_as_missing", "ambient pressure recorded as 0 mmHg - treated as not documented")
            p = None
        setrange(r, "p", [p / 760.0 if p is not None else None], "measured", "chamber")
        if r is not None and recno == rows[0][0]:
            flag(r, "header_interpretation", "header 'CO initial ambient composition' read as CO2 (subscript lost); "
                 "'Burning rate; mm' unit unverified (likely mm^2/s) - see NASA/TP-2015-216046")
        out.append(r)
    return out


def saffire(path, acc, acr):
    hdr, rows = read(path); out = []
    hmap = {h.strip().lower(): h for h in hdr}

    def g(x, *keys):
        for k in keys:
            for hk, h in hmap.items():
                if hk.startswith(k):
                    return x.get(h, "")
        return ""
    last_material = ""
    for recno, x in rows:
        sid = g(x, "sample number").strip()
        if sid.lower().startswith("note"):  # footnote records stay in the source file; they are not runs
            continue
        material = g(x, "material").strip()
        if re.fullmatch(r"F\d+C\d+/F\d+C\d+", sid):  # pre-test flow visualization, not a burn
            r = base(acc, acr, path, recno, x, test_label=sid, fuel_or_material="(none: flow visualization)",
                     fuel_class="none", fuel_class_detail="pre-test flow visualization", row_granularity="flow_visualization",
                     outcome=material)
            flag(r, "not_a_burn", "pre-test flow-visualization camera record, not a burn")
            out.append(r)
            continue
        inherited = not material and bool(last_material)
        material = material or last_material
        last_material = material
        thick = g(x, "sample thickness", "samle thickness")
        r = base(acc, acr, path, recno, x, test_label=sid, fuel_or_material=material, fuel_class="solid",
                 geometry=f"sheet {thick} x {g(x, 'sample length')} x {g(x, 'sample width')}",
                 outcome=f"flow direction {g(x, 'flow direction', 'direction')}; burn time {g(x, 'burn time')}")
        if inherited:
            flag(r, "merged_cell_inherited", f"material blank in table; inherited '{material}' from previous row (merged cell)")
        if re.match(r"^0\d", thick.strip()):
            flag(r, "missing_decimal", f"thickness '{thick.strip()}' likely means 0.{thick.strip()[1:]} (missing decimal point)")
        setrange(r, "flow", nums(g(x, "air flow")), "specified", "forced_duct")
        o2 = nums(g(x, "percent o2"))
        if o2:  # Saffire-II Note 1: O2 'derived from measured CO2 production and referenced to initial O2 reported by ISS'
            setrange(r, "o2", o2, "derived" if acc == "PSI-99" else "reported", "ambient")
        else:
            flag(r, "conditions_not_in_table", "O2 not in PSI table")
        if any("?-g" in h for h in hdr):
            flag(r, "encoding_loss", "header '?-g' read as 'µ-g' (encoding loss in PSI CSV)")
            ug = [h for h in hdr if h.startswith("?-g")]
            og = [h for h in hdr if h.startswith("1-g")]
            r["outcome"] += "; µg: " + ", ".join(f"{h[4:]}={x.get(h,'')}" for h in ug) + \
                            "; 1g: " + ", ".join(f"{h[4:]}={x.get(h,'')}" for h in og)
        out.append(r)
    return out


def same_r(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        r = base("PSI-101", "SAME-R", path, recno, x, test_label=x["SAME Test #"].strip(), date=x["Date"],
                 fuel_or_material=x["Sample Type"].strip(), fuel_class="smoke_source_nonflaming",
                 geometry="SAME sample carousel (heated sample)",
                 outcome=f"Rt/R0 {x.get('Rt/R0','')}; duration {x.get('Duration (sec)','')} s; net aging {x.get('Net aging time (sec)','')} s")
        setrange(r, "flow", [num(x.get("Inlet velocity (cm/s)"))], "specified", "inlet")
        out.append(r)
    return out


def same(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        r = base("PSI-102", "SAME", path, recno, x, test_label=x["Sample #"].strip(),
                 fuel_or_material=x[[h for h in hdr if h.startswith("Sample Material")][0]].strip(),
                 fuel_class="smoke_source_nonflaming", geometry="SAME sample carousel",
                 outcome=f"weight loss {x.get('Weight loss rate (mg/min)','')} mg/min; aging {x.get('Aging Duration (minutes)','')} min")
        setrange(r, "flow", [num(x.get("Air Flow (cm/s)"))], "specified", "inlet")
        out.append(r)
    return out


def slice_(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        r = base("PSI-106", "SLICE", path, recno, x, test_label=x["Test Date"].strip(), date=x["Test Date"],
                 fuel_or_material=x["Fuel Type"], fuel_class="gaseous", fuel_class_detail="coflow jet, lifted flames",
                 geometry="exchangeable burner tubes in fan-driven flow duct")
        flag(r, "conditions_not_in_table", "only date and fuel reported; O2, pressure and flow not in PSI table")
        out.append(r)
    return out


def spice(path):
    hdr, rows = read(path); out = []
    for recno, x in rows:
        r = base("PSI-107", "SPICE", path, recno, x, test_label=f"GMT{x['GMT date'].strip()} {x['GMT ignition'].strip()}",
                 date=f"GMT day {x['GMT date']}", fuel_or_material=x["Fuel"], fuel_class="gaseous",
                 fuel_class_detail="coflow jet (smoke point)", geometry=f"nozzle {x['Nozzle (mm)']} mm",
                 outcome=f"fuel rate {x['Fuel Rate (sccm)']} sccm ({x['Fuel Rate (mg/s)']} mg/s)")
        setrange(r, "flow", [num(x["Air Rate (cm/s)"])], "specified", "coflow")
        if (num(x["Air Rate (cm/s)"]) or 0) < 0:
            flag(r, "negative_flow", f"negative air rate {x['Air Rate (cm/s)']} cm/s kept as reported (likely zero-flow sensor offset)")
        out.append(r)
    return out


def cfi(path):
    hdr, rows = read(path); out = []
    H = {h.strip(): h for h in hdr}
    for recno, x in rows:
        fuel = x[H["Fuel"]].strip()
        dil = [g for g in ("Nitrogen", "Helium") if (num(x.get(H.get(g, g))) or 0) > 0]
        r = base("PSI-39", "CFI", path, recno, x, test_label=x["Flex Number"].strip(), date=x["Test Date"],
                 fuel_or_material={"C12H26": "n-dodecane (C12H26)"}.get(fuel, fuel), fuel_class="liquid_droplet",
                 geometry="droplet " + ("on support fiber" if x[H["Fiber"]].strip().lower() == "yes" else "free-deployed"),
                 diluent="+".join({"Nitrogen": "N2", "Helium": "He"}[g] for g in dil),
                 outcome=f"CIR test id {x[H['CIR']].strip()}; PSI column 'Flex Number' = {x['Flex Number'].strip()}")
        o2 = num(x.get(H["Oxygen"]))
        setrange(r, "o2", [o2 * 100 if o2 is not None else None], "specified", "ambient")
        setrange(r, "p", nums(x[H["Pressure"]]), "specified", "chamber")
        out.append(r)
    return out


def cfig(path):
    """CFI-G normal / inverse flame tables (explicit column mapping, verified against headers)."""
    hdr, rows = read(path); out = []
    H = {re.sub(r"\s+", " ", h).strip().lower(): h for h in hdr}

    def g(x, key):
        return x.get(H.get(key, ""), "").strip()
    inverse = "Inverse" in os.path.basename(path)
    BAR = 1 / 1.01325
    for recno, x in rows:
        test = re.sub(r"\s+", "", g(x, "test"))
        if not test:
            continue
        end_raw = g(x, "self-ext or flow term") or g(x, "self -ext or flow term")
        end = {"SE": "self-extinguished", "FT": "flow terminated"}.get(end_raw, end_raw)
        outcome = (f"{'inverse' if inverse else 'normal'} flame; hot ignition={g(x,'hot ignition')}; "
                   f"burn time {g(x,'burn time (sec)')} s; end={end}; Tad {g(x,'tad (k)')} K; Zst {g(x,'zst')}")
        if not inverse:
            outcome = f"cool flame={g(x, 'cool flame?') or 'not recorded'}; " + outcome
        if g(x, "comments"):
            outcome += f"; comment: {g(x, 'comments')}"
        r = base("PSI-159", "ACME CFI-G", path, recno, x, test_label=test, date=f"YYDDD {test[:5]}",
                 fuel_or_material=g(x, "fuel"), fuel_class="gaseous",
                 fuel_class_detail=("inverse" if inverse else "normal") + " spherical diffusion flame (cool-flame study)",
                 geometry="porous spherical burner", diluent="N2", outcome=outcome)
        p = num(g(x, "approx p (bar)"))
        setrange(r, "p", [p * BAR if p is not None else None], "reported", "chamber")
        if p is not None:
            flag(r, "approximate_value", "pressure from 'approx p (bar)' converted bar->atm; status reported (approximate)")
        if inverse:
            r["o2_context"] = "burner_stream"
            v = num(g(x, "xo2"))
            setrange(r, "o2", [v * 100 if v is not None else None], "specified", "burner_stream")
            flag(r, "burner_stream_o2", "inverse flame: XO2 is the burner oxidizer stream, not the chamber atmosphere")
            r["outcome"] += f"; ambient fuel X {g(x,'xf before test')}->{g(x,'xf after test')}"
        else:
            vals = [num(g(x, "xo2 before test")), num(g(x, "xo2 after test"))]
            setrange(r, "o2", [v * 100 for v in vals if v is not None], "measured", "ambient")
        out.append(r)
    return out


def sflame(path):
    """ACME s-Flame test-day table; atmosphere '~21% O2 with N2' (approximate; ~1 atm per table note)."""
    hdr, rows = read(path); out = []
    H = {h.strip().rstrip("*"): h for h in hdr}
    for recno, x in rows:
        day = x[H["Test Day"]].strip()
        if not day:
            continue
        atm, fuel = x[H["Atmosphere"]].strip(), x[H["Fuel Bottle"]].strip()
        r = base("PSI-23", "ACME s-Flame", path, recno, x, test_label=day, date=f"{x['Year']}-{x['Month']}-{x['Date']}",
                 fuel_or_material=re.sub(r"with N\d+", "with N2", fuel), fuel_class="gaseous",
                 fuel_class_detail="spherical diffusion flame", geometry="porous spherical burner",
                 diluent="He" if "He" in atm else "N2",
                 outcome=f"flames ignited that day: {x[H['Flames Ignited']]}; {x['Test Type'].strip()}")
        for txt, label in ((atm, "atmosphere"), (fuel, "fuel bottle")):
            for m in re.finditer(r"with N(\d+)", txt):
                if m.group(1) != "2":
                    flag(r, "autoincrement_artifact", f"{label} 'with N{m.group(1)}' read as 'with N2' (spreadsheet auto-increment artifact)")
        o2 = [float(v) for v in re.findall(r"~(\d+(?:\.\d+)?)%", atm)]
        setrange(r, "o2", o2, "reported", "ambient")
        setrange(r, "p", [1.0], "reported", "chamber")
        flag(r, "approximate_value", "O2 and pressure approximate ('~'); table note: ~1 atm, pressure rises and O2 drops with vitiation")
        if len(o2) > 1:
            flag(r, "multiple_o2_levels", "test day ran at more than one O2 level (" + ", ".join(f"{v:g}%" for v in o2) + ")")
        out.append(r)
    return out


def figure_refs(path, acc):
    hdr, rows = read(path)
    out = []
    for recno, x in rows:
        r = base(acc, "", path, recno, x, test_label=x.get("Data ID", "").strip(), fuel_class="none",
                 fuel_class_detail="reference to a figure in a publication (not a test)", gravity_regime="normal_gravity",
                 outcome="; ".join(f"{k}={v}" for k, v in x.items())[:300])
        flag(r, "not_a_test", "data-summary row pointing to a publication figure; not an experimental test")
        out.append(r)
    return out


DISPATCH = {
    "PSI-20": bre, "PSI-21": cld, "PSI-22": efield, "PSI-10": flame_design, "PSI-25": bass2, "PSI-26": bass,
    "PSI-47": daft, "PSI-68": flex2, "PSI-69": flex, "PSI-101": same_r, "PSI-102": same, "PSI-106": slice_,
    "PSI-107": spice, "PSI-39": cfi, "PSI-159": cfig, "PSI-23": sflame,
    "PSI-98": lambda p: saffire(p, "PSI-98", "Saffire-I"), "PSI-99": lambda p: saffire(p, "PSI-99", "Saffire-II"),
    "PSI-100": lambda p: saffire(p, "PSI-100", "Saffire-III"), "PSI-142": lambda p: figure_refs(p, "PSI-142"),
}


def mark_duplicates(rows):
    """duplicate_of = row_key of the first identical source record in the same table (BRE split rows share a source
    record by design and are not duplicates). Also flag test labels reused for non-identical rows."""
    first = {}
    for r in rows:
        key = (r["source_table_id"], r["raw"])
        if key in first and first[key]["source_row"] != r["source_row"]:
            r["duplicate_of"] = first[key]["row_key"]
            flag(r, "exact_duplicate", f"exact duplicate of source row {first[key]['source_row']} ({first[key]['row_key']})")
        else:
            first.setdefault(key, r)
    by_label = {}
    for r in rows:
        if r["duplicate_of"] or not r["test_label"] or r["row_granularity"] not in ("test",):
            continue
        k = (r["investigation"], r["test_label"])
        if k in by_label and by_label[k]["source_row"] != r["source_row"]:
            flag(r, "test_label_reused", f"test label '{r['test_label']}' also used by non-identical row {by_label[k]['row_key']}")
        by_label.setdefault(k, r)


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    for path in sorted(glob.glob(os.path.join(root, "PSI-*", "Experimental table", "*.csv"))):
        acc = os.path.basename(os.path.dirname(os.path.dirname(path)))
        fn = DISPATCH.get(acc)
        if fn is None:
            raise SystemExit(f"no normalizer for {acc} ({os.path.basename(path)}): refusing to guess")
        got = fn(path)
        rows.extend(got)
        print(f"  {acc:8s} {len(got):4d} rows  <- {os.path.basename(path)}")
    rows.sort(key=lambda r: (int(r["investigation"][4:]), r["source_table_id"], int(r["source_row"]), r["row_key"]))
    mark_duplicates(rows)
    keys = [r["row_key"] for r in rows]
    assert len(keys) == len(set(keys)), "row_key not unique"
    flags_out = []
    for r in rows:
        r["flags"] = " | ".join(m for _, m in r["_flags"])
        for code, msg in r["_flags"]:
            flags_out.append({"row_key": r["row_key"], "investigation": r["investigation"], "source_table_id": r["source_table_id"],
                              "source_row": r["source_row"], "severity": SEVERITY[code], "code": code, "message": msg})
        del r["_flags"]
    with open(out + ".csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    with open(out + ".json", "w") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    with open(out + "_flags.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["row_key", "investigation", "source_table_id", "source_row", "severity", "code", "message"])
        w.writeheader(); w.writerows(flags_out)
    sev = {k: sum(1 for f in flags_out if f["severity"] == k) for k in ("anomaly", "limitation", "note")}
    print(f"{len(rows)} rows, {len(flags_out)} flags {sev}, {sum(1 for r in rows if r['duplicate_of'])} duplicates "
          f"-> {out}.csv/.json, {out}_flags.csv")


if __name__ == "__main__":
    main()
