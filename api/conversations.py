"""Copilot conversations (chat history, switching between chats) and the Copilot answer cache.

- Conversations and messages live in the FIREWISE user-state store (api/twin/state.py, migration 3),
  scoped to the client's workspace key (header X-Workspace; the server stores only its SHA-256).
- Answer cache: an identical question with an identical context returns the stored response.
  The key covers the normalised question, the twin scenario (physically relevant part) and selected
  zone, the scientific-database build fingerprint, the answer mode (deterministic or model id/effort)
  and the twin engine version — so a database rebuild or a model change never serves a stale answer.
  Fallback answers produced because the language model failed are never cached.
"""
import datetime
import hashlib
import json
import re
import time
import uuid
from typing import Any, Literal, Optional

from fastapi import APIRouter, Body, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import copilot
from .db import connect, db_available
from .twin import physics, state
from .twin.schemas import TwinAskContext

CACHE_MAX_ENTRIES = 5000
CACHE_MAX_AGE_DAYS = 30
MAX_MESSAGES = 400
WS_RE = re.compile(r"[A-Za-z0-9_-]{32,128}")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")


# ------------------------------------------------------------------------------------------- answer cache
def _fingerprint(con):
    m = dict(con.execute("SELECT key, value FROM meta").fetchall())
    return f"{m.get('schema_version')}:{m.get('inputs_sha256')}:{m.get('runs_csv_sha256')}"


def cache_key(con, question, scenario_id=None, twin=None, owner=None):
    """Twin answers quote user-written scenario text (name, description), so the key covers the WHOLE twin
    context and, when a workspace is known, the workspace too: a cached twin answer is never served to a
    different context or another workspace. General questions carry no user data and share the cache."""
    mode = f"llm:{copilot.MODEL_ID}:{copilot.EFFORT}" if copilot.llm_available() else "deterministic"
    q = re.sub(r"\s+", " ", question.strip().lower())
    ctx = None
    if twin:
        ctx = {"context": twin, "engine": physics.ENGINE_VERSION, "owner": owner}
    payload = json.dumps({"q": q, "scenario_id": scenario_id, "twin": ctx, "db": _fingerprint(con), "mode": mode}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def cacheable(resp):
    return resp["mode"] in ("llm_validated", "deterministic") and not (resp.get("notice") and "unavailable (" in resp["notice"])


def ask_cached(con, question, scenario_id=None, twin=None, owner=None):
    """copilot.ask with the answer cache. Returns the response with `cached` set."""
    t0 = time.time()
    key = cache_key(con, question, scenario_id, twin, owner)
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=CACHE_MAX_AGE_DAYS)).isoformat(timespec="seconds")
    with state.connect() as s:
        r = s.execute("SELECT response_json FROM copilot_answer_cache WHERE cache_key=? AND created_at >= ?", (key, cutoff)).fetchone()
        if r:
            s.execute("UPDATE copilot_answer_cache SET hits = hits + 1, last_hit_at = ? WHERE cache_key=?", (_now(), key))
            resp = json.loads(r[0])
            return {**resp, "cached": True, "latency_ms": int((time.time() - t0) * 1000)}
    resp = copilot.ask(con, question, scenario_id, twin=twin)
    resp = {**resp, "cached": False}
    if cacheable(resp):
        with state.connect() as s:
            s.execute("INSERT OR REPLACE INTO copilot_answer_cache (cache_key, response_json, created_at, last_hit_at, hits) VALUES (?,?,?,NULL,0)",
                      (key, json.dumps(resp, sort_keys=True), _now()))
            s.execute("DELETE FROM copilot_answer_cache WHERE cache_key IN (SELECT cache_key FROM copilot_answer_cache "
                      "ORDER BY COALESCE(last_hit_at, created_at) DESC LIMIT -1 OFFSET ?)", (CACHE_MAX_ENTRIES,))
    return resp


# ------------------------------------------------------------------------------------------- conversations
def _conv(r, n=None, last=None):
    return {"id": r["id"], "title": r["title"], "kind": r["kind"], "created_at": r["created_at"], "updated_at": r["updated_at"],
            "message_count": n if n is not None else 0, "last_question": last}


def list_conversations(s, owner, kind=None):
    q = ("SELECT c.*, (SELECT COUNT(*) FROM chat_message m WHERE m.conversation_id=c.id) AS n, "
         "(SELECT content FROM chat_message m WHERE m.conversation_id=c.id AND m.role='user' ORDER BY seq DESC LIMIT 1) AS last "
         "FROM chat_conversation c WHERE c.owner_hash=?" + (" AND c.kind=?" if kind else "") + " ORDER BY c.updated_at DESC, c.rowid DESC")
    return [_conv(r, r["n"], r["last"]) for r in s.execute(q, (owner, kind) if kind else (owner,))]


def get_conversation(s, owner, cid):
    r = s.execute("SELECT * FROM chat_conversation WHERE id=? AND owner_hash=?", (cid, owner)).fetchone()
    if not r:
        return None
    msgs = [{"seq": m["seq"], "role": m["role"], "content": m["content"], "response": json.loads(m["response_json"]) if m["response_json"] else None,
             "context": json.loads(m["context_json"]) if m["context_json"] else None, "cached": bool(m["cached"]), "created_at": m["created_at"]}
            for m in s.execute("SELECT * FROM chat_message WHERE conversation_id=? ORDER BY seq", (cid,))]
    return {**_conv(r, len(msgs), next((m["content"] for m in reversed(msgs) if m["role"] == "user"), None)), "messages": msgs}


def create_conversation(s, owner, title=None, kind="general"):
    cid = "chat_" + uuid.uuid4().hex[:12]
    now = _now()
    s.execute("INSERT INTO chat_conversation VALUES (?,?,?,?,?,?)", (cid, owner, (title or "New chat")[:80], kind, now, now))
    return get_conversation(s, owner, cid)


def append_exchange(s, owner, cid, question, resp, context):
    conv = s.execute("SELECT * FROM chat_conversation WHERE id=? AND owner_hash=?", (cid, owner)).fetchone()
    n = s.execute("SELECT COALESCE(MAX(seq), 0) FROM chat_message WHERE conversation_id=?", (cid,)).fetchone()[0]
    now = _now()
    ctx = json.dumps(context, sort_keys=True) if context else None
    s.execute("INSERT INTO chat_message VALUES (?,?,?,?,?,?,?,?)", (cid, n + 1, "user", question, None, ctx, 0, now))
    s.execute("INSERT INTO chat_message VALUES (?,?,?,?,?,?,?,?)",
              (cid, n + 2, "assistant", resp.get("answer_summary") or "", json.dumps(resp, sort_keys=True), ctx, int(bool(resp.get("cached"))), now))
    title = conv["title"]
    if n == 0 and title == "New chat":
        title = (question[:77] + "…") if len(question) > 78 else question
    s.execute("UPDATE chat_conversation SET updated_at=?, title=? WHERE id=?", (now, title, cid))


# ------------------------------------------------------------------------------------------- HTTP
router = APIRouter(prefix="/api/conversations", tags=["copilot-conversations"])
WS_HEADER = Header(..., alias="X-Workspace", description="Random workspace key generated by the client; conversations are visible only to it.")


def _owner(key):
    if not WS_RE.fullmatch(key or ""):
        raise HTTPException(400, "X-Workspace must be 32–128 characters of A-Z, a-z, 0-9, _ or -")
    return state.owner_hash(key)


class ConversationIn(BaseModel):
    title: Optional[str] = Field(default=None, max_length=80)
    kind: Literal["general", "twin"] = "general"


class ConversationPatch(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class MessageIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    twin: Optional[TwinAskContext] = None


@router.get("", response_model=list[dict[str, Any]])
def conversations(kind: Optional[Literal["general", "twin"]] = None, ws: str = WS_HEADER):
    owner = _owner(ws)
    with state.connect() as s:
        return list_conversations(s, owner, kind)


@router.post("", response_model=dict[str, Any], status_code=201)
def new_conversation(body: ConversationIn = Body(default_factory=ConversationIn), ws: str = WS_HEADER):
    owner = _owner(ws)
    with state.connect() as s:
        return create_conversation(s, owner, body.title, body.kind)


@router.get("/{cid}", response_model=dict[str, Any])
def conversation(cid: str, ws: str = WS_HEADER):
    owner = _owner(ws)
    with state.connect() as s:
        c = get_conversation(s, owner, cid)
    if not c:
        raise HTTPException(404, f"Unknown conversation {cid}")
    return c


@router.patch("/{cid}", response_model=dict[str, Any])
def rename_conversation(cid: str, body: ConversationPatch, ws: str = WS_HEADER):
    owner = _owner(ws)
    with state.connect() as s:
        if s.execute("UPDATE chat_conversation SET title=?, updated_at=? WHERE id=? AND owner_hash=?", (body.title.strip(), _now(), cid, owner)).rowcount == 0:
            raise HTTPException(404, f"Unknown conversation {cid}")
        return get_conversation(s, owner, cid)


@router.delete("/{cid}", status_code=204)
def delete_conversation(cid: str, ws: str = WS_HEADER):
    owner = _owner(ws)
    with state.connect() as s:
        if s.execute("DELETE FROM chat_conversation WHERE id=? AND owner_hash=?", (cid, owner)).rowcount == 0:
            raise HTTPException(404, f"Unknown conversation {cid}")
    return Response(status_code=204)


@router.post("/{cid}/messages", response_model=dict[str, Any])
def send_message(cid: str, body: MessageIn, ws: str = WS_HEADER):
    """Ask the Copilot inside a conversation: the exchange is stored, the answer cache is used."""
    owner = _owner(ws)
    with state.connect() as s:
        c = s.execute("SELECT (SELECT COUNT(*) FROM chat_message WHERE conversation_id=c.id) FROM chat_conversation c WHERE id=? AND owner_hash=?",
                      (cid, owner)).fetchone()
    if c is None:
        raise HTTPException(404, f"Unknown conversation {cid}")
    if c[0] >= MAX_MESSAGES:
        raise HTTPException(400, f"Conversation is full ({MAX_MESSAGES} messages); start a new chat")
    if not db_available():
        raise HTTPException(503, "Database not built. Run scripts/load_db.py")
    twin = body.twin.model_dump() if body.twin else None
    with connect() as con:
        try:
            resp = ask_cached(con, body.question.strip(), None, twin, owner)
        except copilot.TwinContextError as e:
            raise HTTPException(400, str(e))
    context = None
    if twin:
        context = {"twin_scenario": twin["scenario"]["name"], "selected_zone": twin.get("selected_zone"),
                   "input_hash": hashlib.sha256(json.dumps(physics.scenario_core(twin["scenario"]), sort_keys=True, default=str).encode()).hexdigest()[:16]}
    with state.connect() as s:
        append_exchange(s, owner, cid, body.question.strip(), resp, context)
        conv = get_conversation(s, owner, cid)
    return {"conversation": {k: v for k, v in conv.items() if k != "messages"}, "messages": conv["messages"][-2:], "response": resp}
