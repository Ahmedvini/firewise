"""Read-only access to build/firewise.sqlite plus shared value formatting (FINAL_API_CONTRACT.md §1)."""
import json
import os
import sqlite3
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("FIREWISE_DB", os.path.join(ROOT, "build", "firewise.sqlite"))
PSIA_PER_ATM = 14.6959

STATUS_LABEL = {
    "measured": "Measured",
    "derived": "Derived",
    "reported": "Reported (approx.)",
    "specified": "Set-point / specified",
    "missing": "Not documented",
}


@contextmanager
def connect():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def db_available() -> bool:
    return os.path.exists(DB_PATH)


def quantity(lo, hi, unit, status, context):
    q = {"min": lo, "max": hi, "unit": unit, "status": status, "status_label": STATUS_LABEL[status], "context": context, "psia": None}
    if unit == "atm" and lo is not None:
        q["psia"] = {"min": round(lo * PSIA_PER_ATM, 2), "max": round(hi * PSIA_PER_ATM, 2)}
    return q


def run_dict(row, flags=None, observations=None):
    """Canonical Run representation: one representation per variable, provenance always attached."""
    return {
        "row_key": row["row_key"],
        "investigation_id": row["investigation_id"],
        "test_label": row["test_label"],
        "row_granularity": row["row_granularity"],
        "duplicate_of": row["duplicate_of"],
        "date_text": row["date_text"],
        "fuel_or_material": row["fuel_or_material"],
        "fuel_class": row["fuel_class"],
        "fuel_class_detail": row["fuel_class_detail"],
        "geometry": row["geometry"],
        "diluent": row["diluent"],
        "gravity_regime": row["gravity_regime"],
        "platform": row["platform"],
        "o2": quantity(row["o2_min_pct"], row["o2_max_pct"], "pct", row["o2_status"], row["o2_context"]),
        "pressure": quantity(row["p_min_atm"], row["p_max_atm"], "atm", row["p_status"], row["p_context"]),
        "flow": quantity(row["flow_min_cm_s"], row["flow_max_cm_s"], "cm_s", row["flow_status"], row["flow_context"]),
        "outcome_text": row["outcome_text"],
        "observations": observations or [],
        "flags": flags or [],
        "provenance": {
            "row_key": row["row_key"],
            "source_table_id": row["source_table_id"],
            "source_file": row["file_name"],
            "source_row": row["source_row"],
            "source_sha256": row["sha256"],
            "source_url": row["source_url"],
            "psi_url": f"https://psi.nasa.gov/physci/repo/data/investigations/{row['investigation_id']}",
            "evidence_id": f"row:{row['row_key']}",
        },
    }


RUN_SELECT = """SELECT r.*, t.file_name, t.sha256, t.source_url FROM run r JOIN source_table t ON t.id = r.source_table_id"""


def attach_details(con, rows):
    """Bulk-load observations and flags for a list of run rows."""
    keys = [r["row_key"] for r in rows]
    obs, fl = {}, {}
    for i in range(0, len(keys), 500):
        chunk = keys[i:i + 500]
        q = ",".join("?" * len(chunk))
        for o in con.execute(f"SELECT * FROM observation WHERE row_key IN ({q}) ORDER BY variable, gravity_regime", chunk):
            obs.setdefault(o["row_key"], []).append({
                "variable": o["variable"], "value_num": o["value_num"], "value_text": o["value_text"], "unit": o["unit"],
                "status": o["status"], "status_label": STATUS_LABEL[o["status"]], "gravity_regime": o["gravity_regime"],
                "source_column": o["source_column"], "evidence_id": f"obs:{o['row_key']}#{o['variable']}"})
        for f in con.execute(f"SELECT * FROM quality_flag WHERE row_key IN ({q}) ORDER BY id", chunk):
            fl.setdefault(f["row_key"], []).append({"severity": f["severity"], "code": f["code"], "message": f["message"]})
    return [run_dict(r, fl.get(r["row_key"]), obs.get(r["row_key"])) for r in rows]


def aggregate(con, name):
    row = con.execute("SELECT value_json FROM aggregate WHERE name=?", (name,)).fetchone()
    return None if row is None else json.loads(row[0])
