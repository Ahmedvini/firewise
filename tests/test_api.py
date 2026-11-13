"""Backend, scientific and Copilot tests (P0_ACCEPTANCE_CRITERIA.md §2-§3)."""
import json
import os

import pytest
from fastapi.testclient import TestClient

from api import copilot
from api.main import app

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAIMS = json.load(open(os.path.join(ROOT, "derived", "claims_check.json")))
c = TestClient(app)


def get(path, status=200):
    r = c.get(path)
    assert r.status_code == status, (path, r.status_code, r.text[:300])
    return r.json()


# ------------------------------------------------------------------------------------------- endpoints & errors
def test_health_never_exposes_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-SECRET")
    d = get("/api/health")
    assert d["status"] == "ok" and d["copilot_configured"] is True and d["copilot_model"] == "claude-opus-5-5"
    assert "SECRET" not in json.dumps(d)


def test_summary_matches_independent_check():
    m = {k: v["value"] for k, v in get("/api/summary")["metrics"].items()}
    assert m["investigations"] == 24 and m["investigations_with_tables"] == 20
    assert m["condition_records"] == CLAIMS["combustion_aerosol_rows"] == 2007
    assert m["unique_individual_tests"] == CLAIMS["unique_individual_tests"] == 1386
    assert m["duplicate_records"] == 43 and m["partial_gravity_records"] == 0
    assert m["solid_records"] == 264 and m["solid_with_pressure"] == 0 and m["solid_o2_max_pct"] == 22.2


def test_investigations_list_filters_and_pagination():
    d = get("/api/investigations?limit=5&offset=0")
    assert d["total"] == 24 and len(d["items"]) == 5
    assert get("/api/investigations?fuel_class=solid")["total"] == 5
    ids = {i["id"] for i in get("/api/investigations?q=cool%20flame")["items"]}
    assert {"PSI-159", "PSI-39"} <= ids
    for card in get("/api/investigations?limit=500")["items"]:
        if card["o2_ambient"]["min"] is None:
            assert card["o2_ambient"]["status"] == "missing" and card["o2_ambient"]["status_label"] == "Not documented"


def test_investigation_detail_and_runs():
    d = get("/api/investigations/PSI-159")
    assert d["objective"]["evidence_id"] == "inv:PSI-159#objective" and d["has_burner_stream_o2"] is True
    runs = get("/api/investigations/PSI-39/runs?limit=500")
    assert runs["page"]["total"] == 79  # duplicates hidden by default
    assert get("/api/investigations/PSI-39/runs?include_duplicates=true&limit=1")["page"]["total"] == 87
    r = get("/api/investigations/PSI-69/runs?limit=1")["page"]["items"][0]
    assert r["provenance"]["evidence_id"].startswith("row:PSI-69:flex:r") and r["provenance"]["source_row"] >= 2
    assert {o["variable"] for o in r["observations"]} >= {"extinction_d_mm", "test_end"}


def test_errors_use_contract_envelope():
    for path, code in (("/api/investigations/PSI-999", 404), ("/api/compare?ids=PSI-26", 400), ("/api/runs?o2_min=50&o2_max=10", 400),
                       ("/api/evidence/nope:1", 404), ("/api/scenarios/nope/evidence", 404), ("/api/distributions?variable=bad", 422)):
        d = get(path, code)
        assert set(d) == {"error"} and {"code", "message"} <= set(d["error"])
    assert c.post("/api/ask", json={"question": "x"}).status_code == 422


def test_distributions_never_bin_missing():
    d = get("/api/distributions?variable=p_atm&group_by=fuel_class")
    solid = next(g for g in d["groups"] if g["key"] == "solid")
    assert solid["n_documented"] == 0 and solid["n_missing"] == 264 and sum(b["n"] for b in solid["histogram"]) == 0


def test_evidence_resolver_kinds():
    for eid, kind in (("agg:scenario:exploration_envelope", "aggregate"), ("fact:F18", "curated_fact"),
                      ("inv:PSI-47%23objective", "psi_record_field")):
        assert get(f"/api/evidence/{eid}")["kind"].startswith(kind)


# ------------------------------------------------------------------------------------------- scientific gates
def test_scenarios_semantics():
    ex = get("/api/scenarios/exploration_envelope/evidence")
    assert ex["totals"]["in_window"] == 0 and ex["gravity_evidence"]["matching_records"] == 0
    assert "not a fire-risk" in ex["label"] and "No weighted score" in ex["ranking_method"]
    mb = get("/api/scenarios/moon_base_challenge/evidence")
    assert mb["totals"]["in_window"] == 20 and mb["items"][0]["investigation_id"] == "PSI-159" and mb["items"][0]["in_window"]["n"] == 20
    assert all("none" in i["gravity_match"] for i in mb["items"])
    assert get("/api/scenarios/fm2_point/evidence")["totals"]["in_window"] == 10
    # missing pressure never matches: BRE has O2 in window but no pressure -> 0 in-window, counted as undocumented
    bre = next(i for i in ex["items"] if i["investigation_id"] == "PSI-20")
    assert bre["in_window"]["n"] == 0 and bre["undocumented"]["pressure_not_documented"] == 43


def test_inverse_flame_o2_never_used_as_atmosphere():
    r = c.post("/api/scenarios/custom/evidence", json={"o2_min_pct": 45, "o2_max_pct": 100, "p_min_psia": 0, "p_max_psia": 100})
    items = {i["investigation_id"]: i["in_window"]["n"] for i in r.json()["items"]}
    assert items.get("PSI-159", 0) == 0  # CFI-G normal-flame chamber O2 never exceeds ~40%; 50-85% values are burner stream


def test_compare_flags_incompatibility_and_relations():
    d = get("/api/compare?ids=PSI-47,PSI-102")
    assert d["incompatibilities"] and "dust" in d["incompatibilities"][0]["reason"].lower()
    assert any(r["type"] == "qualified_instrument_for" and r["src"] == "PSI-47" for r in d["relations"])
    d2 = get("/api/compare?ids=PSI-26,PSI-100")
    o2 = next(f for f in d2["features"] if f["name"].startswith("Chamber (ambient)"))
    assert o2["comparable"] is False and o2["similarity"] is None  # undocumented is not a value
    assert "never scientific equivalence" in d2["label"]


def test_gap_map():
    g = get("/api/gaps")
    assert sum(x["records"] for x in g["cells"]) == 2007 - 43
    assert not [x for x in g["cells"] if x["gravity_regime"] == "partial_gravity"]
    assert not [x for x in g["cells"] if x["o2_band"] == "30-36%" and x["p_band"] == "8.2-10.2 psia"]
    assert not [x for x in g["cells"] if x["fuel_class"] == "solid" and x["p_band"] != "not documented"]
    assert {o["id"] for o in g["literature_overlays"]} == {"LUCI", "FM2-34", "FM2-21"}


# ------------------------------------------------------------------------------------------- Copilot
def ask(q):
    r = c.post("/api/ask", json={"question": q})
    assert r.status_code == 200
    return r.json()


def test_copilot_works_without_llm(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    r = ask("Under what conditions did CFI-G produce cool flames?")
    assert r["mode"] == "deterministic" and r["status"] == "answered" and "not configured" in r["notice"]
    ev = {e["evidence_id"] for e in r["evidence"]}
    for cl in r["claims"]:
        assert cl["evidence_ids"] and set(cl["evidence_ids"]) <= ev


def test_copilot_api_failure_falls_back(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    def boom(*a, **k):
        import anthropic
        raise anthropic.APIConnectionError(request=None)
    monkeypatch.setattr(copilot, "call_llm", boom)
    r = ask("What evidence is there for partial-gravity combustion?")
    assert r["mode"] == "deterministic" and "unavailable" in r["notice"] and r["claims"]


def test_copilot_validator_rejects_fabrication(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    fake = copilot.LLMAnswer(answer_summary="PSI has 0 partial-gravity records.", sufficient_evidence=True, limitations=[], gaps=[],
                             related_investigations=["PSI-999"], claims=[
        copilot.LLMClaim(text="PSI holds 0 partial-gravity records.", tier="measured", evidence_ids=["agg:partial_gravity_records"]),
        copilot.LLMClaim(text="Lunar fires would spread 37% faster than on ISS.", tier="interpretation", evidence_ids=["fact:F06"]),
        copilot.LLMClaim(text="There were 4123 lunar tests.", tier="measured", evidence_ids=["agg:partial_gravity_records"]),
        copilot.LLMClaim(text="Made-up citation.", tier="measured", evidence_ids=["fact:NOPE"]),
    ])
    monkeypatch.setattr(copilot, "call_llm", lambda q, p: fake)
    r = ask("What evidence is there for partial-gravity combustion?")
    assert r["mode"] == "llm_validated" and r["status"] == "partial"
    assert [cl["text"] for cl in r["claims"]] == ["PSI holds 0 partial-gravity records."]
    assert "PSI-999" not in r["related_investigations"]
    assert any("removed by the validator" in l for l in r["limitations"])


def test_copilot_refuses_risk_and_unsupported():
    r = ask("What is the fire risk on ISS?")
    assert r["status"] == "insufficient_evidence" and "does not assess fire safety" in r["notice"]
    assert ask("xyzzy plugh frobnicate")["status"] == "insufficient_evidence"


def test_validation_set_recall_and_traps(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    V = [json.loads(l) for l in open(os.path.join(ROOT, "derived", "validation.jsonl"))]
    hits = n = 0
    for v in V:
        r = ask(v["question"])
        text = " ".join([r["answer_summary"] or ""] + [cl["text"] for cl in r["claims"]]).lower()
        assert not [b for b in v["must_not_contain"] if b.lower() in text], v["id"]
        if v["must_cite_any"]:
            n += 1
            hits += any(e in [x["evidence_id"] for x in r["evidence"][:5]] for e in v["must_cite_any"])
    assert hits / n >= 0.8, f"recall@5 {hits}/{n}"
