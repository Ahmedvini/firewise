"""Digital Twin evidence engine: matches come from the actual database, with FIREWISE semantics."""
import copy
import json

import pytest

from api.db import connect
from api.twin import evidence as tev
from tests.test_twin_physics import scenario


@pytest.fixture(scope="module")
def con():
    with connect() as c:
        yield c


def _direct_count(con, o2, o2_tol, p_kpa, p_tol):
    n = 0
    for r in con.execute("SELECT * FROM run WHERE fuel_class != 'none' AND duplicate_of IS NULL AND o2_context = 'ambient' "
                         "AND o2_min_pct IS NOT NULL AND p_min_atm IS NOT NULL AND gravity_regime = 'microgravity'"):
        o = (r["o2_min_pct"] + (r["o2_max_pct"] if r["o2_max_pct"] is not None else r["o2_min_pct"])) / 2
        p = (r["p_min_atm"] + (r["p_max_atm"] if r["p_max_atm"] is not None else r["p_min_atm"])) / 2 * 101.325
        n += abs(o - o2) <= o2_tol and abs(p - p_kpa) <= p_tol
    return n


@pytest.mark.parametrize("o2,p", [(21.0, 101.325), (34.0, 56.54), (39.0, 202.65), (30.0, 70.33)])
def test_exact_matches_equal_direct_sql(con, o2, p):
    s = scenario()
    s["composition"]["o2_pct"]["value"] = o2
    s["pressure_kPa"]["value"] = p
    ev = tev.evaluate(con, s)
    assert ev["coverage"]["exact_matches"] == _direct_count(con, o2, 2.0, p, 6.89)
    assert ev["coverage"]["records_considered"] == con.execute("SELECT COUNT(*) FROM run WHERE fuel_class!='none' AND duplicate_of IS NULL").fetchone()[0]


def test_semantics_missing_burner_duplicates_flow(con):
    s = scenario()
    s["matching"] = {"use_pressure": True, "use_airflow": True}
    ev = tev.evaluate(con, s, nearest_limit=100)
    dup = {r[0] for r in con.execute("SELECT row_key FROM run WHERE duplicate_of IS NOT NULL")}
    rows = {r["row_key"]: r for r in con.execute("SELECT * FROM run")}
    for it in ev["exact"] + ev["nearest"]:
        r = rows[it["row_key"]]
        assert it["row_key"] not in dup                                         # duplicates never counted
        if "o2_pct" in it["variables_compared"]:
            assert r["o2_context"] == "ambient"                                  # burner-stream O2 never compared
        if "pressure_kPa" in it["variables_compared"]:
            assert r["p_min_atm"] is not None                                    # missing never compared
        else:
            assert r["p_min_atm"] is None and "pressure_kPa" in it["missing_variables"]
        if "airflow_m_s" in it["variables_compared"]:
            assert r["flow_context"] in tev.COMPARABLE_FLOW                      # inlet sampling flow excluded
        assert set(it["components"]) == set(it["variables_compared"])           # undocumented vars contribute no distance
    for it in ev["exact"]:
        assert len(it["variables_compared"]) == len(it["variables_enabled"])    # exact requires every enabled variable documented


def test_temperature_and_gravity_are_never_matched_falsely(con):
    s = scenario()
    s["matching"] = {"use_temperature": True}
    ev = tev.evaluate(con, s)
    assert ev["coverage"]["exact_matches"] == 0 and ev["coverage"]["documented"]["temperature_K"]["records"] == 0
    s = scenario(gravity="lunar")
    ev = tev.evaluate(con, s)
    assert ev["coverage"]["exact_matches"] == 0 and ev["coverage"]["gravity"]["records_at_requested"] == 0
    assert ev["nearest"] and all(not n["gravity_matches"] and n["gravity_regime"] == "microgravity" for n in ev["nearest"])


def test_material_filter_and_ranking(con):
    s = scenario()
    s["experiment"]["material"] = "PMMA"
    s["matching"] = {"use_material": True}
    ev = tev.evaluate(con, s, nearest_limit=50)
    assert ev["nearest"] and all("pmma" in (n["fuel_or_material"] or "").lower() and n["fuel_class"] == "solid" for n in ev["nearest"])
    keys = [(-len(n["variables_compared"]), n["distance"], n["row_key"]) for n in ev["nearest"]]
    assert keys == sorted(keys)                                                  # documented lexicographic ranking


def test_evidence_is_deterministic_and_traceable(con):
    a, b = tev.evaluate(con, scenario()), tev.evaluate(con, copy.deepcopy(scenario()))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    for it in a["nearest"]:
        assert it["evidence_id"].startswith("row:") and it["source"]["file_name"] and it["source"]["source_row"] >= 2
