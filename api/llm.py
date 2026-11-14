"""Bring-your-own-key language-model providers for the Copilot.

Security model:
- Every provider has a FIXED base URL from this table. Users choose a provider id, never a URL, so the server
  cannot be pointed at internal addresses (no SSRF).
- The user's key is used for one request only (see copilot.request_llm) and is never stored, cached, logged
  or returned. Keys are sent in headers, never in URLs.
- Whatever the provider, the answer must be the same JSON structure, and it then goes through the same FIREWISE
  validator (citations must resolve, numbers must appear in cited evidence, no risk/fire predictions).
"""
import json
import re

import httpx

PROVIDERS = {
    "anthropic": {"label": "Anthropic Claude", "kind": "anthropic", "base": None, "key_hint": "sk-ant-…"},
    "openai": {"label": "OpenAI", "kind": "openai", "base": "https://api.openai.com/v1", "key_hint": "sk-…"},
    "gemini": {"label": "Google Gemini", "kind": "gemini", "base": "https://generativelanguage.googleapis.com/v1beta", "key_hint": "AIza…"},
    "openrouter": {"label": "OpenRouter", "kind": "openai", "base": "https://openrouter.ai/api/v1", "key_hint": "sk-or-…"},
    "groq": {"label": "Groq", "kind": "openai", "base": "https://api.groq.com/openai/v1", "key_hint": "gsk_…"},
    "mistral": {"label": "Mistral AI", "kind": "openai", "base": "https://api.mistral.ai/v1", "key_hint": "…"},
    "deepseek": {"label": "DeepSeek", "kind": "openai", "base": "https://api.deepseek.com/v1", "key_hint": "sk-…"},
    "xai": {"label": "xAI Grok", "kind": "openai", "base": "https://api.x.ai/v1", "key_hint": "xai-…"},
    "together": {"label": "Together AI", "kind": "openai", "base": "https://api.together.xyz/v1", "key_hint": "…"},
}
KEY_RE = {"anthropic": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,200}")}
GENERIC_KEY_RE = re.compile(r"[A-Za-z0-9_\-.:]{16,300}")
MODEL_RE = re.compile(r"[A-Za-z0-9._:/\-]{1,120}")
GEMINI_MODEL_RE = re.compile(r"[A-Za-z0-9._\-]{1,120}")       # becomes part of a URL path: no slashes
NON_CHAT = re.compile(r"embed|tts|whisper|dall-e|moderation|transcri|audio|image|realtime|search|davinci|babbage|rerank|guard", re.I)
TIMEOUT = httpx.Timeout(45.0, connect=10.0)
GEMINI_MODEL_PREFERENCE = (
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
    "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash",
    "gemini-2.5-flash-lite", "gemini-2.5-pro",
)


class ChoiceError(ValueError):
    pass


def providers_public():
    return [{"id": k, "label": v["label"], "key_hint": v["key_hint"]} for k, v in PROVIDERS.items()]


def validate_choice(provider, key, model):
    """Return a normalised {provider, key, model} or raise ChoiceError (messages never contain the key)."""
    provider = (provider or "anthropic").strip().lower()
    if provider not in PROVIDERS:
        raise ChoiceError(f"Unknown AI provider; supported: {', '.join(PROVIDERS)}")
    key = (key or "").strip()
    if not (KEY_RE.get(provider) or GENERIC_KEY_RE).fullmatch(key):
        raise ChoiceError(f"The key does not look like a {PROVIDERS[provider]['label']} API key")
    model = (model or "").strip() or None
    if model is not None:
        rx = GEMINI_MODEL_RE if PROVIDERS[provider]["kind"] == "gemini" else MODEL_RE
        if not rx.fullmatch(model):
            raise ChoiceError("Invalid model id")
    return {"provider": provider, "key": key, "model": model}


# ------------------------------------------------------------------------------------------- key check / model list
def _headers(provider, key):
    if PROVIDERS[provider]["kind"] == "gemini":
        return {"x-goog-api-key": key}
    return {"Authorization": f"Bearer {key}"}


def list_models(choice):
    """No-cost model listing that doubles as a key check. Returns (valid, generic message, [model ids])."""
    p = PROVIDERS[choice["provider"]]
    try:
        with httpx.Client(timeout=httpx.Timeout(15.0, connect=10.0)) as c:
            if p["kind"] == "gemini":
                r = c.get(f"{p['base']}/models", params={"pageSize": 200}, headers=_headers(choice["provider"], choice["key"]))
            else:
                r = c.get(f"{p['base']}/models", headers=_headers(choice["provider"], choice["key"]))
    except httpx.HTTPError:
        return False, "The key could not be checked right now; try again later.", []
    if r.status_code in (401, 403):
        return False, "Key not accepted.", []
    if r.status_code >= 400:
        return False, "The key could not be checked right now; try again later.", []
    try:
        d = r.json()
    except ValueError:
        return False, "The key could not be checked right now; try again later.", []
    if p["kind"] == "gemini":
        ids = [m["name"].removeprefix("models/") for m in d.get("models", []) if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    else:
        ids = [m.get("id") for m in d.get("data", []) if m.get("id")]
    ids = {i for i in ids if not NON_CHAT.search(i)}
    if choice["provider"] == "gemini":
        preferred = [i for i in GEMINI_MODEL_PREFERENCE if i in ids]
        ids = preferred + sorted(ids.difference(preferred))
    else:
        ids = sorted(ids)
    ids = ids[:300]
    return True, "Key accepted.", ids


# ------------------------------------------------------------------------------------------- generation
JSON_INSTRUCTIONS = """

Respond with ONLY one JSON object (no prose, no code fences) with exactly these fields:
{"answer_summary": string (at most two sentences, no number that is not in the evidence pack),
 "claims": [{"text": string, "tier": one of "measured" | "reported" | "literature" | "interpretation" | "calculation" | "model_prediction" | "unknown",
             "evidence_ids": [evidence_id strings copied exactly from the evidence pack]}],
 "limitations": [string], "gaps": [string], "related_investigations": [string, e.g. "PSI-159"], "sufficient_evidence": boolean}"""


def _parse_json(text):
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    if not t.startswith("{"):
        i, j = t.find("{"), t.rfind("}")
        t = t[i:j + 1] if i >= 0 and j > i else t
    return json.loads(t)


def generate(choice, system, user_message):
    """Call a non-Anthropic provider and return the parsed JSON answer (dict). Raises on any failure."""
    p = PROVIDERS[choice["provider"]]
    if not choice.get("model"):
        raise ChoiceError("Choose a model for this provider in AI settings")
    sys_text = system + JSON_INSTRUCTIONS
    with httpx.Client(timeout=TIMEOUT) as c:
        if p["kind"] == "gemini":
            body = {"systemInstruction": {"parts": [{"text": sys_text}]},
                    "contents": [{"role": "user", "parts": [{"text": user_message}]}],
                    "generationConfig": {"responseMimeType": "application/json"}}
            r = c.post(f"{p['base']}/models/{choice['model']}:generateContent", json=body, headers=_headers(choice["provider"], choice["key"]))
            r.raise_for_status()
            parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            return _parse_json("".join(x.get("text", "") for x in parts))
        body = {"model": choice["model"], "messages": [{"role": "system", "content": sys_text}, {"role": "user", "content": user_message}],
                "response_format": {"type": "json_object"}}
        r = c.post(f"{p['base']}/chat/completions", json=body, headers=_headers(choice["provider"], choice["key"]))
        if r.status_code == 400:                       # some models/providers reject response_format: retry once without it
            body.pop("response_format")
            r = c.post(f"{p['base']}/chat/completions", json=body, headers=_headers(choice["provider"], choice["key"]))
        r.raise_for_status()
        msg = (r.json().get("choices") or [{}])[0].get("message", {})
        return _parse_json(msg.get("content") or "")
