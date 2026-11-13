"""Digital Twin state store: user scenarios, their version history and simulation runs.

Why a separate file: build/firewise.sqlite is the deterministic, read-only scientific database that
scripts/load_db.py rebuilds from NASA sources (and replaces atomically). User scenarios are mutable
state; storing them there would either be wiped on every rebuild or break build reproducibility.
This store holds NO scientific records — only user configuration and computed-run metadata.

Location: $FIREWISE_STATE_DB (default state/twin_state.sqlite). Migrations are versioned and applied
idempotently on first use (table schema_migrations).
"""
import datetime
import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_lock = threading.Lock()

MIGRATIONS = [
    (1, "create scenario, version history and simulation-run tables", """
CREATE TABLE twin_scenario (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', environment_id TEXT NOT NULL,
  version INTEGER NOT NULL CHECK (version >= 1), body_json TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, duplicated_from TEXT);
CREATE TABLE twin_scenario_version (
  scenario_id TEXT NOT NULL REFERENCES twin_scenario(id) ON DELETE CASCADE, version INTEGER NOT NULL,
  body_json TEXT NOT NULL, created_at TEXT NOT NULL, note TEXT, PRIMARY KEY (scenario_id, version));
CREATE TABLE twin_simulation_run (
  run_id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL REFERENCES twin_scenario(id) ON DELETE CASCADE,
  scenario_version INTEGER NOT NULL, status TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed')),
  engine_version TEXT NOT NULL, input_hash TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT,
  summary_json TEXT NOT NULL DEFAULT '{}', result_json TEXT, error TEXT);
CREATE INDEX twin_run_by_scenario ON twin_simulation_run (scenario_id, created_at);
"""),
]


def state_path():
    return os.environ.get("FIREWISE_STATE_DB", os.path.join(ROOT, "state", "twin_state.sqlite"))


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    path = state_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        migrate(con)
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def migrate(con):
    with _lock:
        con.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, description TEXT NOT NULL, applied_at TEXT NOT NULL)")
        done = {r[0] for r in con.execute("SELECT version FROM schema_migrations")}
        for ver, desc, sql in MIGRATIONS:
            if ver not in done:
                con.executescript(sql)
                con.execute("INSERT INTO schema_migrations VALUES (?,?,?)", (ver, desc, _now()))
        con.commit()


def applied_migrations(con):
    return [dict(r) for r in con.execute("SELECT * FROM schema_migrations ORDER BY version")]


def _row(r):
    body = json.loads(r["body_json"])
    return {**body, "id": r["id"], "version": r["version"], "created_at": r["created_at"], "updated_at": r["updated_at"]}


def create(con, body, note="created", duplicated_from=None):
    sid = "sc_" + uuid.uuid4().hex[:12]
    now = _now()
    js = json.dumps(body, sort_keys=True)
    con.execute("INSERT INTO twin_scenario VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, body["name"], body.get("description", ""), body["habitat"]["environment_id"], 1, js, now, now, duplicated_from))
    con.execute("INSERT INTO twin_scenario_version VALUES (?,?,?,?,?)", (sid, 1, js, now, note))
    return get(con, sid)


def get(con, sid):
    r = con.execute("SELECT * FROM twin_scenario WHERE id=?", (sid,)).fetchone()
    return r and _row(r)


def update(con, sid, body, note="updated"):
    cur = get(con, sid)
    if not cur:
        return None
    ver = cur["version"] + 1
    now = _now()
    js = json.dumps(body, sort_keys=True)
    con.execute("UPDATE twin_scenario SET name=?, description=?, environment_id=?, version=?, body_json=?, updated_at=? WHERE id=?",
                (body["name"], body.get("description", ""), body["habitat"]["environment_id"], ver, js, now, sid))
    con.execute("INSERT INTO twin_scenario_version VALUES (?,?,?,?,?)", (sid, ver, js, now, note))
    return get(con, sid)


def delete(con, sid):
    return con.execute("DELETE FROM twin_scenario WHERE id=?", (sid,)).rowcount > 0


def duplicate(con, sid, name=None):
    cur = get(con, sid)
    if not cur:
        return None
    body = {k: v for k, v in cur.items() if k not in ("id", "version", "created_at", "updated_at")}
    body["name"] = (name or f"{cur['name']} (copy)")[:80]
    return create(con, body, note=f"duplicated from {sid} v{cur['version']}", duplicated_from=sid)


def list_all(con):
    out = []
    for r in con.execute("SELECT * FROM twin_scenario ORDER BY updated_at DESC, id"):
        b = json.loads(r["body_json"])
        out.append({"id": r["id"], "name": r["name"], "description": r["description"], "version": r["version"], "updated_at": r["updated_at"],
                    "environment_id": r["environment_id"], "o2_pct": b["composition"]["o2_pct"].get("value"),
                    "pressure_kPa": b["pressure_kPa"].get("value"), "gravity": b["gravity"]})
    return out


def history(con, sid):
    out = []
    for r in con.execute("SELECT * FROM twin_scenario_version WHERE scenario_id=? ORDER BY version", (sid,)):
        b = json.loads(r["body_json"])
        out.append({"version": r["version"], "created_at": r["created_at"], "note": r["note"],
                    "o2_pct": b["composition"]["o2_pct"].get("value"), "pressure_kPa": b["pressure_kPa"].get("value"),
                    "temperature_K": b["temperature_K"].get("value"), "ventilation_m3_h": b["ventilation"]["volumetric_flow_m3_h"].get("value"),
                    "scenario": b})
    return out


def record_run(con, sid, version, engine_version, input_hash, summary, result, status="completed", error=None):
    rid = "run_" + uuid.uuid4().hex[:12]
    now = _now()
    con.execute("INSERT INTO twin_simulation_run VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rid, sid, version, status, engine_version, input_hash, now, now if status in ("completed", "failed") else None,
                 json.dumps(summary, sort_keys=True), json.dumps(result, sort_keys=True) if result is not None else None, error))
    return get_run(con, rid)


def get_run(con, rid, with_result=True):
    r = con.execute("SELECT * FROM twin_simulation_run WHERE run_id=?", (rid,)).fetchone()
    if not r:
        return None
    return {"run_id": r["run_id"], "scenario_id": r["scenario_id"], "scenario_version": r["scenario_version"], "status": r["status"],
            "engine_version": r["engine_version"], "input_hash": r["input_hash"], "created_at": r["created_at"], "completed_at": r["completed_at"],
            "summary": json.loads(r["summary_json"]), "result": json.loads(r["result_json"]) if (with_result and r["result_json"]) else None,
            "error": r["error"]}


def list_runs(con, sid):
    return [get_run(con, r[0], with_result=False) for r in
            con.execute("SELECT run_id FROM twin_simulation_run WHERE scenario_id=? ORDER BY created_at DESC, run_id", (sid,))]
