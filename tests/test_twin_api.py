"""Digital Twin API: persistence, workspace isolation, validation, comparison, simulations, reports, Copilot."""
import json
import re

import pytest
from fastapi.testclient import TestClient

from api import copilot
from api.main import app

c = TestClient(app)
WS = {"X-Workspace": "test-workspace-" + "a" * 32}
OTHER = {"X-Workspace": "other-workspace-" + "b" * 32}


@pytest.fixture(autouse=True)
def state_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FIREWISE_STATE_DB", str(tmp_path / "twin_state.sqlite"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def preset(i=1):
    return c.get("/api/twin/environments/fwh-1/presets").json()[i]["scenario"]


def test_environment_models_validation_endpoints():
    envs = c.get("/api/twin/environments").json()
    assert envs[0]["id"] == "fwh-1" and len(envs[0]["zones"]) == 5 and "not a model of any specific" in envs[0]["description"]
    models = {m["id"]: m for m in c.get("/api/twin/models").json()}
    for mid in ("ideal_gas", "gas_mixture", "bulk_airflow", "forced_convection_flat_plate", "wall_conduction"):
        m = models[mid]
        assert m["equations"] and m["inputs"] and m["outputs"] and m["assumptions"] and m["applicability"] and m["limitations"] and m["version"]
        assert all(v["unit"] for v in m["inputs"] + m["outputs"])
    assert models["flame_extinction"]["validation_status"] == "not_implemented"
    v = c.get("/api/twin/validation").json()
    assert {r["status"] for r in v["records"]} <= {"verified", "validated", "not_implemented"}
    assert c.get("/api/twin/models/nope").status_code == 404


def test_crud_duplicate_history_and_isolation():
    sc = preset()
    r = c.post("/api/twin/scenarios", json=sc, headers=WS)
    assert r.status_code == 201
    s = r.json()
    sid = s["id"]
    assert s["version"] == 1 and s["pressure_kPa"]["status"] == "user_defined"
    sc["pressure_kPa"] = {"value": 60.0, "status": "user_defined", "source": None}
    assert c.put(f"/api/twin/scenarios/{sid}", json=sc, headers=WS).json()["version"] == 2
    assert [h["pressure_kPa"] for h in c.get(f"/api/twin/scenarios/{sid}/history", headers=WS).json()] == [56.54, 60.0]
    d = c.post(f"/api/twin/scenarios/{sid}/duplicate", json={"name": "Copy"}, headers=WS).json()
    assert d["id"] != sid and d["name"] == "Copy" and d["pressure_kPa"]["value"] == 60.0
    assert {x["id"] for x in c.get("/api/twin/scenarios", headers=WS).json()} == {sid, d["id"]}
    # another workspace sees nothing and cannot read, change or delete
    assert c.get("/api/twin/scenarios", headers=OTHER).json() == []
    assert c.get(f"/api/twin/scenarios/{sid}", headers=OTHER).status_code == 404
    assert c.put(f"/api/twin/scenarios/{sid}", json=sc, headers=OTHER).status_code == 404
    assert c.delete(f"/api/twin/scenarios/{sid}", headers=OTHER).status_code == 404
    assert c.get("/api/twin/scenarios").status_code == 422                                   # header required
    assert c.get("/api/twin/scenarios", headers={"X-Workspace": "short"}).status_code == 400
    assert c.delete(f"/api/twin/scenarios/{d['id']}", headers=WS).status_code == 204
    assert c.get(f"/api/twin/scenarios/{d['id']}", headers=WS).status_code == 404


@pytest.mark.parametrize("path,value,code", [("pressure_kPa", {"value": 500.0}, 422), ("temperature_K", {"value": 10.0}, 422),
                                             ("pressure_kPa", {"value": None}, 422)])
def test_invalid_inputs_rejected(path, value, code):
    sc = preset()
    sc[path] = value
    r = c.post("/api/twin/scenarios", json=sc, headers=WS)
    assert r.status_code == code and r.json()["error"]["code"] == "validation_error"


def test_invalid_references_and_composition_rejected():
    sc = preset()
    sc["experiment"]["zone_id"] = "Z9"
    assert c.post("/api/twin/scenarios", json=sc, headers=WS).status_code == 400
    sc = preset()
    sc["composition"]["ar_pct"] = {"value": 5.0}
    sc["composition"]["co2_pct"] = {"value": 5.0}
    sc["composition"]["o2_pct"] = {"value": 95.0}
    assert c.post("/api/twin/evaluate", json={"scenario": sc}).status_code == 422


def test_compare_simulations_report():
    a = c.post("/api/twin/scenarios", json=preset(0), headers=WS).json()
    b = c.post("/api/twin/scenarios", json=preset(1), headers=WS).json()
    cmp = c.post("/api/twin/compare", json={"ids": [a["id"], b["id"]]}, headers=WS).json()
    diff = {r["label"] for r in cmp["rows"] if r["differs"]}
    assert "Pressure" in diff and "Gravity" in diff
    assert c.post("/api/twin/compare", json={"ids": [a["id"], b["id"]]}, headers=OTHER).status_code == 404
    run = c.post(f"/api/twin/scenarios/{b['id']}/simulations", headers=WS)
    assert run.status_code == 201 and run.json()["status"] == "completed" and run.json()["result"]["results"]
    rid = run.json()["run_id"]
    assert c.get(f"/api/twin/simulations/{rid}", headers=WS).json()["input_hash"] == run.json()["input_hash"]
    assert c.get(f"/api/twin/simulations/{rid}", headers=OTHER).status_code == 404
    assert [x["run_id"] for x in c.get(f"/api/twin/scenarios/{b['id']}/simulations", headers=WS).json()] == [rid]
    rep = c.get(f"/api/twin/scenarios/{b['id']}/report", headers=WS).json()
    assert "not a fire-risk assessment" in rep["markdown"] and "## 3. Physics calculations" in rep["markdown"]
    assert rep["input_hash"] == run.json()["input_hash"]
    cov = c.get(f"/api/twin/scenarios/{b['id']}/coverage", headers=WS).json()
    assert cov["coverage"]["documented"]["temperature_K"]["records"] == 0


def test_evaluate_unsaved_state_is_consistent():
    sc = preset(1)
    d1 = c.post("/api/twin/evaluate", json={"scenario": sc}).json()
    d2 = c.post("/api/twin/evaluate", json={"scenario": sc}).json()
    assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)
    assert {z["zone_id"] for z in d1["zone_conditions"]} == {"Z1", "Z2", "Z3", "Z4", "Z5"}
    assert d1["evidence"]["coverage"]["exact_matches"] == 0                      # lunar gravity: no PSI records
    assert c.get("/api/evidence/model:gas_mixture").json()["kind"] == "physics_model_card"
    assert "MAE" in c.get("/api/evidence/twinval:gas_mixture").json()["text"]


TWIN_QUESTIONS = ["Which NASA experiments are closest to this environment?", "What evidence exists at this oxygen concentration?",
                  "What changes when cabin pressure is modified?", "Are there experiments with similar material and airflow?",
                  "Which variables are missing from the NASA records?", "What physical models can be applied here?",
                  "What prevents us from predicting flame behavior?", "How reliable is the selected model?"]


@pytest.mark.parametrize("q", TWIN_QUESTIONS)
def test_copilot_twin_questions_without_llm(q):
    sc = preset(1)
    sc["experiment"]["material"] = "PMMA"
    r = c.post("/api/ask", json={"question": q, "twin": {"scenario": sc, "selected_zone": "Z3"}})
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "deterministic" and d["status"] == "answered" and d["claims"]
    ev = {e["evidence_id"]: e for e in d["evidence"]}
    for cl in d["claims"]:
        assert cl["evidence_ids"] and all(i in ev for i in cl["evidence_ids"])
        assert cl["tier"] in ("measured", "reported", "literature", "interpretation", "calculation", "model_prediction", "unknown")
        if cl["tier"] in ("calculation", "model_prediction"):
            assert any(i.startswith(("twin:calc:", "twin:sensitivity", "model:", "twinval:")) for i in cl["evidence_ids"])
    assert not any(re.search(r"\b(is safe|unsafe|fire risk)\b", cl["text"], re.I) for cl in d["claims"])


def test_copilot_twin_material_citations_are_the_filtered_records():
    sc = preset(1)
    sc["experiment"]["material"] = "PMMA"
    d = c.post("/api/ask", json={"question": "Are there experiments with similar material and airflow?", "twin": {"scenario": sc}}).json()
    rows = [i for cl in d["claims"] for i in cl["evidence_ids"] if i.startswith("row:")]
    ev = {e["evidence_id"]: e for e in d["evidence"]}
    assert rows and all("pmma" in ev[i]["snippet"].lower() for i in rows)


def test_copilot_twin_validator_rejects_fabricated_calculation(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    fake = copilot.LLMAnswer(answer_summary="The scenario was evaluated.", sufficient_evidence=True, limitations=[], gaps=[], related_investigations=[], claims=[
        copilot.LLMClaim(text="The gas density in zone Z3 is 0.9123 kg/m3.", tier="calculation", evidence_ids=["twin:scenario"]),
        copilot.LLMClaim(text="Flame spread would be predicted to slow at this pressure.", tier="model_prediction", evidence_ids=["model:ideal_gas"]),
        copilot.LLMClaim(text="Exact matches: 0 NASA records.", tier="measured", evidence_ids=["twin:evidence"]),
    ])
    monkeypatch.setattr(copilot, "call_llm", lambda q, p: fake)
    d = c.post("/api/ask", json={"question": "Which NASA experiments are closest to this environment?", "twin": {"scenario": preset(1)}}).json()
    assert d["mode"] == "llm_validated" and d["status"] == "partial"
    texts = [cl["text"] for cl in d["claims"]]
    assert texts == ["Exact matches: 0 NASA records."]
    assert "removed by the validator" in " ".join(d["limitations"])


def test_copilot_twin_falls_back_when_api_fails(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-SECRET")

    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(copilot, "call_llm", boom)
    r = c.post("/api/ask", json={"question": "What physical models can be applied here?", "twin": {"scenario": preset(0)}})
    d = r.json()
    assert d["mode"] == "deterministic" and "unavailable" in d["notice"] and d["claims"] and "SECRET" not in r.text
