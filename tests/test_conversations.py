"""Copilot conversations (history, switching, rename, delete, isolation) and the answer cache."""
from fastapi.testclient import TestClient

from api import copilot
from api.main import app

c = TestClient(app)
WS = {"X-Workspace": "conv-workspace-" + "c" * 32}
OTHER = {"X-Workspace": "conv-workspace-" + "d" * 32}


def test_conversation_lifecycle_and_switching(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    a = c.post("/api/conversations", json={}, headers=WS).json()
    b = c.post("/api/conversations", json={"title": "Habitat questions"}, headers=WS).json()
    assert a["title"] == "New chat" and b["title"] == "Habitat questions"
    r = c.post(f"/api/conversations/{a['id']}/messages", json={"question": "Under what conditions did CFI-G produce cool flames?"}, headers=WS).json()
    assert r["response"]["claims"] and r["conversation"]["title"].startswith("Under what conditions") and r["conversation"]["message_count"] == 2
    c.post(f"/api/conversations/{b['id']}/messages", json={"question": "What evidence is there for partial-gravity combustion?"}, headers=WS)
    c.post(f"/api/conversations/{b['id']}/messages", json={"question": "What instrumentation was shared between SAME and DAFT?"}, headers=WS)
    lst = c.get("/api/conversations", headers=WS).json()
    assert [x["id"] for x in lst] == [b["id"], a["id"]] and lst[0]["message_count"] == 4     # most recent first
    full = c.get(f"/api/conversations/{a['id']}", headers=WS).json()                      # switch back: history intact
    assert [m["role"] for m in full["messages"]] == ["user", "assistant"] and full["messages"][1]["response"]["claims"]
    assert c.patch(f"/api/conversations/{b['id']}", json={"title": "Renamed"}, headers=WS).json()["title"] == "Renamed"
    assert c.get("/api/conversations", headers=OTHER).json() == []                         # isolation
    assert c.get(f"/api/conversations/{a['id']}", headers=OTHER).status_code == 404
    assert c.delete(f"/api/conversations/{a['id']}", headers=OTHER).status_code == 404
    assert c.delete(f"/api/conversations/{a['id']}", headers=WS).status_code == 204
    assert c.get(f"/api/conversations/{a['id']}", headers=WS).status_code == 404
    assert c.get("/api/conversations").status_code == 422


def test_answer_cache_hits_and_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    q = {"question": "What evidence is there for partial-gravity combustion?"}
    first, second = c.post("/api/ask", json=q).json(), c.post("/api/ask", json=q).json()
    assert first["cached"] is False and second["cached"] is True
    assert {k: v for k, v in first.items() if k not in ("cached", "latency_ms")} == {k: v for k, v in second.items() if k not in ("cached", "latency_ms")}
    assert c.post("/api/ask", json={"question": q["question"].upper() + "  "}).json()["cached"] is True   # normalised question
    preset = c.get("/api/twin/environments/fwh-1/presets").json()
    t0 = c.post("/api/ask", json={"question": "Which NASA experiments are closest to this environment?", "twin": {"scenario": preset[0]["scenario"]}}).json()
    t1 = c.post("/api/ask", json={"question": "Which NASA experiments are closest to this environment?", "twin": {"scenario": preset[1]["scenario"]}}).json()
    assert t0["cached"] is False and t1["cached"] is False and t0["claims"] != t1["claims"]     # different scenario -> different key


def test_failed_llm_fallback_is_not_cached(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(copilot, "call_llm", boom)
    q = {"question": "What evidence is there for partial-gravity combustion?"}
    assert c.post("/api/ask", json=q).json()["cached"] is False
    assert c.post("/api/ask", json=q).json()["cached"] is False


def test_twin_cache_never_crosses_names_or_workspaces(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sc = c.get("/api/twin/environments/fwh-1/presets").json()[1]["scenario"]
    q = "Which NASA experiments are closest to this environment?"
    first = c.post("/api/ask", json={"question": q, "twin": {"scenario": {**sc, "name": "Private habitat alpha"}}}).json()
    other = c.post("/api/ask", json={"question": q, "twin": {"scenario": {**sc, "name": "Another name"}}}).json()
    assert first["cached"] is False and other["cached"] is False
    assert "Private habitat alpha" not in str(other)
    a = c.post("/api/conversations", json={"kind": "twin"}, headers=WS).json()
    b = c.post("/api/conversations", json={"kind": "twin"}, headers=OTHER).json()
    r1 = c.post(f"/api/conversations/{a['id']}/messages", json={"question": q, "twin": {"scenario": sc}}, headers=WS).json()
    r2 = c.post(f"/api/conversations/{b['id']}/messages", json={"question": q, "twin": {"scenario": sc}}, headers=OTHER).json()
    assert r1["response"]["cached"] is False and r2["response"]["cached"] is False     # workspace-scoped twin cache


def test_user_api_key_is_request_scoped_and_never_exposed(monkeypatch):
    """Bring-your-own-key: used for the request only; never stored, cached into other modes, echoed or logged."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    key = "sk-ant-test-" + "X" * 40
    seen = []

    def fake(question, pack):
        seen.append(copilot._REQUEST_KEY.get())
        return copilot.LLMAnswer(answer_summary="PSI has 0 partial-gravity records.", sufficient_evidence=True, limitations=[], gaps=[],
                                 related_investigations=[], claims=[copilot.LLMClaim(text="PSI holds 0 partial-gravity records.", tier="measured",
                                                                                     evidence_ids=["agg:partial_gravity_records"])])
    monkeypatch.setattr(copilot, "call_llm", fake)
    q = {"question": "Is there partial-gravity combustion data in PSI?"}
    r = c.post("/api/ask", json=q, headers={"X-Anthropic-Key": key})
    assert r.status_code == 200 and r.json()["mode"] == "llm_validated" and r.json()["model"]["key"] == "user"
    assert seen == [key] and copilot._REQUEST_KEY.get() is None                      # scoped to that request
    assert key not in r.text
    r2 = c.post("/api/ask", json=q)                                                     # no key, no server key -> deterministic
    assert r2.json()["mode"] == "deterministic" and key not in r2.text
    conv = c.post("/api/conversations", json={}, headers=WS).json()
    m = c.post(f"/api/conversations/{conv['id']}/messages", json=q, headers={**WS, "X-Anthropic-Key": key})
    assert m.status_code == 200 and key not in m.text
    assert key not in c.get(f"/api/conversations/{conv['id']}", headers=WS).text      # not stored with the history
    import sqlite3, os
    db = os.environ["FIREWISE_STATE_DB"]
    dump = "\n".join(sqlite3.connect(db).iterdump())
    assert key not in dump                                                              # not in the state store / cache
    bad = c.post("/api/ask", json=q, headers={"X-Anthropic-Key": "not-a-key"})
    assert bad.status_code == 400 and "not-a-key" not in bad.text
    h = c.get("/api/health").json()
    assert h["copilot_configured"] is False and h["user_keys_accepted"] is True


def test_key_check_endpoint(monkeypatch):
    monkeypatch.setattr(copilot, "check_key", lambda k: (True, "Key accepted; model claude-opus-5-5 is available."))
    r = c.post("/api/copilot/key/check", headers={"X-Anthropic-Key": "sk-ant-test-" + "Y" * 40})
    assert r.status_code == 200 and r.json()["valid"] is True and "Y" * 10 not in r.text
    assert c.post("/api/copilot/key/check").status_code == 400
