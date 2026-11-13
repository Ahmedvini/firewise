"""Bring-your-own-key for every supported provider: fixed endpoints (no SSRF), keys only in headers, model listing,
answer parsing, the same FIREWISE validator, and no cache sharing across providers. The network is mocked."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from api import copilot, llm
from api.main import app

c = TestClient(app)
WS = {"X-Workspace": "llm-workspace-" + "p" * 32}
ANSWER = {"answer_summary": "PSI has 0 partial-gravity records.", "sufficient_evidence": True, "limitations": [], "gaps": [],
          "related_investigations": [], "claims": [{"text": "PSI holds 0 partial-gravity records.", "tier": "measured",
                                                    "evidence_ids": ["agg:partial_gravity_records"]}]}


@pytest.fixture
def net(monkeypatch):
    """Route every httpx call made by api/llm.py to a recorder; returns the list of recorded requests."""
    seen = []
    real = httpx.Client

    def handler(request):
        seen.append(request)
        u = str(request.url)
        if u.endswith("/models") or "/models?" in u:
            if "googleapis" in u:
                return httpx.Response(200, json={"models": [{"name": "models/gemini-x-pro", "supportedGenerationMethods": ["generateContent"]},
                                                            {"name": "models/text-embedding-9", "supportedGenerationMethods": ["embedContent"]}]})
            return httpx.Response(200, json={"data": [{"id": "gpt-x"}, {"id": "text-embedding-3"}, {"id": "whisper-1"}]})
        if "googleapis" in u:
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(ANSWER)}]}}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "```json\n" + json.dumps(ANSWER) + "\n```"}}]})
    monkeypatch.setattr(llm.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return seen


def test_provider_list_and_validation():
    ps = {p["id"] for p in c.get("/api/copilot/providers").json()["providers"]}
    assert {"anthropic", "openai", "gemini", "openrouter", "groq", "mistral", "deepseek", "xai", "together"} <= ps
    for h, code in (({"X-LLM-Provider": "evil", "X-LLM-Key": "k" * 30}, 400),
                    ({"X-LLM-Provider": "openai", "X-LLM-Key": "short"}, 400),
                    ({"X-LLM-Provider": "gemini", "X-LLM-Key": "AIza" + "a" * 35, "X-LLM-Model": "../../admin"}, 400),
                    ({"X-LLM-Provider": "anthropic", "X-LLM-Key": "not-an-anthropic-key-0000000"}, 400)):
        r = c.post("/api/ask", json={"question": "Is there partial-gravity data?"}, headers=h)
        assert r.status_code == code and h["X-LLM-Key"] not in r.text


@pytest.mark.parametrize("provider,base", [(k, v["base"]) for k, v in llm.PROVIDERS.items() if v["kind"] == "openai"])
def test_openai_compatible_providers_use_fixed_endpoints(net, provider, base):
    key = f"{provider}-secret-" + "z" * 30
    r = c.post("/api/ask", json={"question": "Is there partial-gravity combustion data in PSI?"},
               headers={"X-LLM-Provider": provider, "X-LLM-Key": key, "X-LLM-Model": "vendor/model-1"})
    d = r.json()
    assert r.status_code == 200 and d["mode"] == "llm_validated" and d["model"]["provider"] == provider and d["model"]["id"] == "vendor/model-1"
    assert d["claims"][0]["text"] == "PSI holds 0 partial-gravity records."                       # validated claim kept
    req = net[-1]
    assert str(req.url) == f"{base}/chat/completions" and req.headers["authorization"] == f"Bearer {key}"
    assert key not in str(req.url) and key not in r.text
    assert json.loads(req.content)["model"] == "vendor/model-1"


def test_gemini_uses_header_key_and_fixed_endpoint(net):
    key = "AIza" + "g" * 35
    r = c.post("/api/ask", json={"question": "Is there partial-gravity combustion data in PSI?"},
               headers={"X-LLM-Provider": "gemini", "X-LLM-Key": key, "X-LLM-Model": "gemini-x-pro"})
    assert r.json()["mode"] == "llm_validated" and r.json()["model"]["provider"] == "gemini"
    req = net[-1]
    assert str(req.url) == "https://generativelanguage.googleapis.com/v1beta/models/gemini-x-pro:generateContent"
    assert req.headers["x-goog-api-key"] == key and key not in str(req.url) and key not in r.text


def test_key_check_lists_chat_models_per_provider(net):
    r = c.post("/api/copilot/key/check", headers={**WS, "X-LLM-Provider": "openai", "X-LLM-Key": "sk-" + "o" * 40}).json()
    assert r["valid"] and r["models"] == ["gpt-x"] and r["model"] == "gpt-x"                    # embeddings/whisper filtered out
    r = c.post("/api/copilot/key/check", headers={**WS, "X-LLM-Provider": "gemini", "X-LLM-Key": "AIza" + "h" * 35}).json()
    assert r["valid"] and r["models"] == ["gemini-x-pro"]
    assert all(str(q.url).startswith(("https://api.openai.com/v1/", "https://generativelanguage.googleapis.com/v1beta/")) for q in net)


def test_rejected_key_and_bad_output_fall_back_safely(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    real = httpx.Client
    monkeypatch.setattr(llm.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(lambda rq: httpx.Response(401, json={"error": "bad key"})), **kw))
    assert llm.list_models({"provider": "openai", "key": "sk-" + "x" * 40, "model": None})[:2] == (False, "Key not accepted.")
    r = c.post("/api/ask", json={"question": "Is there partial-gravity combustion data in PSI?"},
               headers={"X-LLM-Provider": "openai", "X-LLM-Key": "sk-" + "x" * 40, "X-LLM-Model": "gpt-x"}).json()
    assert r["mode"] == "deterministic" and r["notice"].startswith("Your API key could not be used") and r["claims"]
    # non-JSON model output is rejected, never shown
    monkeypatch.setattr(llm.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(
        lambda rq: httpx.Response(200, json={"choices": [{"message": {"content": "I think it is risky."}}]})), **kw))
    r = c.post("/api/ask", json={"question": "Is there partial-gravity combustion data in PSI?"},
               headers={"X-LLM-Provider": "groq", "X-LLM-Key": "gsk_" + "y" * 40, "X-LLM-Model": "llama-x"}).json()
    assert r["mode"] == "deterministic" and "risky" not in json.dumps(r)


def test_cache_is_not_shared_across_providers_or_models(net):
    q = {"question": "What evidence is there for partial-gravity combustion?"}
    a = c.post("/api/ask", json=q, headers={"X-LLM-Provider": "openai", "X-LLM-Key": "sk-" + "a" * 40, "X-LLM-Model": "gpt-x"}).json()
    b = c.post("/api/ask", json=q, headers={"X-LLM-Provider": "mistral", "X-LLM-Key": "m" * 40, "X-LLM-Model": "mistral-x"}).json()
    a2 = c.post("/api/ask", json=q, headers={"X-LLM-Provider": "openai", "X-LLM-Key": "sk-" + "b" * 40, "X-LLM-Model": "gpt-x"}).json()
    d = c.post("/api/ask", json=q).json()
    assert a["cached"] is False and b["cached"] is False and a2["cached"] is True and d["cached"] is False
    assert d["mode"] == "deterministic"
