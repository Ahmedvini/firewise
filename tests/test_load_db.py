"""Acceptance tests for scripts/load_db.py (KICKOFF_CHECKLIST.md §5, tests 1-12)."""
import csv, json, os, random, re, sqlite3, subprocess, sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "build", "firewise.sqlite")
P = lambda *a: os.path.join(ROOT, *a)


@pytest.fixture(scope="module")
def db():
    if not os.path.exists(DB):
        subprocess.run([sys.executable, "-I", P("scripts/load_db.py"), ROOT], check=True)
    con = sqlite3.connect(DB)
    yield con
    con.close()


@pytest.fixture(scope="module")
def claims():
    return json.load(open(P("derived/claims_check.json")))


def one(db, sql, *args):
    return db.execute(sql, args).fetchone()[0]


def agg(db, name):
    return json.loads(one(db, "SELECT value_json FROM aggregate WHERE name=?", name))


# 1 -------------------------------------------------------------------------------------------
def test_01_investigation_loading(db):
    assert one(db, "SELECT COUNT(*) FROM investigation") == 24
    assert one(db, "SELECT COUNT(DISTINCT investigation_id) FROM source_table") == 20
    manifest = {r["path"]: r for r in csv.DictReader(open(P("sources/sources.csv")))}
    assert one(db, "SELECT record_sha256 FROM investigation WHERE id='PSI-23'") == manifest["sources/psi_api/PSI-23.json"]["sha256"]
    assert one(db, "SELECT COUNT(*) FROM investigation_meta") == 24


# 2 -------------------------------------------------------------------------------------------
def test_02_run_loading(db):
    assert one(db, "SELECT COUNT(*) FROM run") == 2019
    assert one(db, "SELECT COUNT(*) FROM run WHERE row_granularity NOT IN ('flow_visualization','figure_reference')") == 2007
    assert one(db, "SELECT COUNT(*) FROM run WHERE row_granularity='flow_visualization'") == 4
    assert one(db, "SELECT COUNT(*) FROM run WHERE row_granularity='figure_reference'") == 8


# 3 -------------------------------------------------------------------------------------------
def test_03_stable_identifiers(db):
    keys = [k for (k,) in db.execute("SELECT row_key FROM run")]
    assert len(keys) == len(set(keys))
    pat = re.compile(r"^PSI-\d+:[a-z0-9-]+:r\d+(:o2=[\d.]+)?$")
    assert all(pat.match(k) for k in keys), [k for k in keys if not pat.match(k)][:3]
    assert one(db, "SELECT COUNT(*) FROM run WHERE row_key='PSI-159:cfi-g-inverse-flames:r' || source_row AND test_label='21265C3'") == 1


# 4 -------------------------------------------------------------------------------------------
def test_04_duplicates(db):
    dup = dict(db.execute("SELECT investigation_id, COUNT(*) FROM run WHERE duplicate_of IS NOT NULL GROUP BY investigation_id"))
    assert dup == {"PSI-39": 8, "PSI-22": 1, "PSI-107": 34}
    assert agg(db, "unique_individual_tests") == 1386
    # every duplicate points at an earlier, identical source record in the same table
    for key, orig in db.execute("SELECT row_key, duplicate_of FROM run WHERE duplicate_of IS NOT NULL"):
        a = db.execute("SELECT raw_json, source_table_id, source_row FROM run WHERE row_key=?", (key,)).fetchone()
        b = db.execute("SELECT raw_json, source_table_id, source_row FROM run WHERE row_key=?", (orig,)).fetchone()
        assert a[0] == b[0] and a[1] == b[1] and b[2] < a[2]


# 5 -------------------------------------------------------------------------------------------
def test_05_source_rows_preserved(db):
    rows = db.execute("SELECT r.raw_json, r.source_row, t.local_path FROM run r JOIN source_table t ON t.id=r.source_table_id").fetchall()
    random.seed(20261114)
    cache = {}
    for raw, srow, path in random.sample(rows, 40):
        if path not in cache:
            with open(P(path), encoding="utf-8-sig", errors="replace", newline="") as fh:
                cache[path] = list(csv.reader(fh))
        recs = cache[path]
        hdr = [h.strip() for h in recs[0]]
        assert dict(zip(hdr, recs[srow - 1])) == json.loads(raw)


# 6 -------------------------------------------------------------------------------------------
def test_06_status_preservation(db):
    src = list(csv.DictReader(open(P("derived/runs.csv"))))
    for col in ("o2_status", "p_status", "flow_status"):
        from collections import Counter
        assert dict(Counter(r[col] for r in src)) == dict(db.execute(f"SELECT {col}, COUNT(*) FROM run GROUP BY {col}").fetchall())
    for k in ("o2_min_pct", "p_min_atm", "flow_min_cm_s"):
        st = {"o2_min_pct": "o2_status", "p_min_atm": "p_status", "flow_min_cm_s": "flow_status"}[k]
        assert one(db, f"SELECT COUNT(*) FROM run WHERE ({k} IS NULL) != ({st}='missing')") == 0
    allowed = {"measured", "derived", "reported", "specified", "missing"}
    assert {s for (s,) in db.execute("SELECT DISTINCT status FROM observation")} <= allowed
    with pytest.raises(sqlite3.IntegrityError):  # the schema itself refuses a value without status
        tmp = sqlite3.connect(":memory:")
        tmp.executescript(open(P("scripts/load_db.py")).read().split('DDL = """')[1].split('"""')[0])
        tmp.execute("INSERT INTO investigation (id,title,psi_url,project_type,n_files_listed,listed_gb,total_gb,listing_complete,record_sha256) "
                    "VALUES ('PSI-1','t','u','p',0,0,0,1,'x')")
        tmp.execute("INSERT INTO source_table VALUES ('PSI-1:t','PSI-1','f','p','s','u',1)")
        tmp.execute("INSERT INTO run (row_key,investigation_id,source_table_id,source_row,row_granularity,fuel_class,gravity_regime,platform,"
                    "o2_min_pct,o2_max_pct,o2_status,p_status,flow_status,raw_json) VALUES ('k','PSI-1','PSI-1:t',2,'test','solid','microgravity','x',"
                    "21,21,'missing','missing','missing','{}')")


# 7 -------------------------------------------------------------------------------------------
def test_07_flags(db):
    n_csv = sum(1 for _ in csv.DictReader(open(P("derived/runs_flags.csv"))))
    assert one(db, "SELECT COUNT(*) FROM quality_flag") == n_csv
    assert one(db, "SELECT COUNT(*) FROM quality_flag WHERE row_key NOT IN (SELECT row_key FROM run)") == 0
    assert agg(db, "anomaly_flags") == 111
    assert one(db, "SELECT COUNT(*) FROM quality_flag WHERE code='exact_duplicate'") == 43


# 8 -------------------------------------------------------------------------------------------
def test_08_missing_values(db):
    assert one(db, "SELECT COUNT(*) FROM run WHERE investigation_id='PSI-20' AND (p_status!='missing' OR p_min_atm IS NOT NULL)") == 0
    assert agg(db, "cfig_cool_flame_not_recorded") == 171
    assert agg(db, "cfig_cool_flame_yes") == 7
    assert one(db, "SELECT COUNT(*) FROM run WHERE p_min_atm = 0 OR o2_min_pct = 0") == 0
    assert one(db, "SELECT p_status FROM run WHERE investigation_id='PSI-69' AND test_label LIKE '114 /%'") == "missing"
    # flow is never assumed: only BRE (record text says quiescent) has a 0 cm/s flow
    assert {a for (a,) in db.execute("SELECT DISTINCT investigation_id FROM run WHERE flow_min_cm_s = 0 AND flow_context='quiescent'")} == {"PSI-20"}


# 9 -------------------------------------------------------------------------------------------
def test_09_o2_context(db):
    assert one(db, "SELECT COUNT(*) FROM run WHERE o2_context='burner_stream'") == 274
    assert one(db, "SELECT COUNT(*) FROM run WHERE source_table_id LIKE '%inverse%' AND o2_context!='burner_stream'") == 0


# 10 ------------------------------------------------------------------------------------------
def test_10_coverage_reproducible(db, claims):
    assert agg(db, "scenario:exploration_envelope")["records"] == 0 == claims["ambient_A_exploration_envelope_O2_30_36_P_8.2_10.2psia"]["n"]
    assert agg(db, "scenario:moon_base_challenge") == {"records": 20, "by_investigation": {"PSI-159": 20}}
    assert agg(db, "scenario:fm2_point")["records"] == 10
    assert agg(db, "scenario:iss")["records"] == claims["ambient_E_iss_O2_20_22_P_14.2_15.2psia"]["n"]
    assert agg(db, "solid_records") == 264 and agg(db, "solid_with_pressure") == 0
    assert agg(db, "solid_with_o2") == 140 and agg(db, "solid_o2_max_pct") == 22.2
    assert agg(db, "partial_gravity_records") == 0
    assert one(db, "SELECT COALESCE(SUM(records),0) FROM coverage_cell WHERE o2_band='30-36%' AND p_band='8.2-10.2 psia'") == 0
    assert one(db, "SELECT COALESCE(SUM(records),0) FROM coverage_cell WHERE gravity_regime='partial_gravity'") == 0


# 11 & 12 -------------------------------------------------------------------------------------
def _snapshot_mtimes():
    out = {}
    for d in ("Data", "sources/psi_api"):
        for root, _, files in os.walk(P(d)):
            for f in files:
                p = os.path.join(root, f)
                out[p] = os.stat(p).st_mtime_ns
    return out


def _dump(path):
    con = sqlite3.connect(path)
    lines = [l for l in con.iterdump() if "'build_utc'" not in l]
    con.close()
    return "\n".join(lines)


def test_11_and_12_no_mutation_and_determinism(tmp_path):
    before = _snapshot_mtimes()
    outs = []
    for i in range(2):
        out = tmp_path / f"b{i}.sqlite"
        subprocess.run([sys.executable, "-I", P("scripts/load_db.py"), ROOT, "--out", os.path.relpath(out, ROOT), "--no-pdfs"],
                       check=True, capture_output=True)
        outs.append(_dump(out))
    assert _snapshot_mtimes() == before
    chk = subprocess.run([sys.executable, "-I", P("scripts/checksum_data.py"), P("Data"), P("derived/data_sha256.txt"), "--verify"],
                         capture_output=True, text=True)
    assert chk.returncode == 0 and chk.stdout.startswith("OK")
    assert outs[0] == outs[1]
