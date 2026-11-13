import { useCallback, useEffect, useRef, useState } from "react";
import { MessageSquarePlus, Pencil, Trash2, Send, Check, X } from "lucide-react";
import Answer from "./Answer.jsx";
import { chats } from "../services/api.js";
import { ErrorPanel } from "./States.jsx";

const ACTIVE_KEY = (kind) => `firewise.chat.active.${kind}`;
const readActive = (kind) => { try { return window.localStorage.getItem(ACTIVE_KEY(kind)); } catch { return null; } };
const writeActive = (kind, id) => { try { id ? window.localStorage.setItem(ACTIVE_KEY(kind), id) : window.localStorage.removeItem(ACTIVE_KEY(kind)); } catch { /* storage blocked */ } };

function relTime(iso) {
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 60) return "just now";
  if (d < 3600) return `${Math.floor(d / 60)} min ago`;
  if (d < 86400) return `${Math.floor(d / 3600)} h ago`;
  return new Date(iso).toLocaleDateString();
}

/**
 * Saved Copilot conversations: list, switch, new, rename, delete; messages persist on the server.
 * kind: "general" (Copilot page) or "twin" (Digital Twin panel). getContext() returns the twin context or null.
 */
export default function ChatPanel({ kind = "general", getContext, suggestions = [], onOpenExperiment, compact = false, intro }) {
  const [list, setList] = useState(null);
  const [activeId, setActiveId] = useState(() => readActive(kind));
  const [conv, setConv] = useState(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [renaming, setRenaming] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const endRef = useRef(null);

  const refreshList = useCallback(async () => {
    try {
      const l = await chats.list(kind);
      setList(l);
      return l;
    } catch (e) {
      setError(e);
      setList([]);
      return [];
    }
  }, [kind]);

  useEffect(() => { refreshList(); }, [refreshList]);

  useEffect(() => {
    writeActive(kind, activeId);
    if (!activeId) { setConv(null); return; }
    let live = true;
    chats.get(activeId).then((c) => live && setConv(c)).catch((e) => {
      if (!live) return;
      if (e.status === 404) { setActiveId(null); return; }
      setError(e);
    });
    return () => { live = false; };
  }, [activeId, kind]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [conv?.messages?.length, busy]);

  const newChat = async () => {
    setError(null);
    try {
      const c = await chats.create(kind);
      setActiveId(c.id);
      setConv(c);
      refreshList();
    } catch (e) { setError(e); }
  };

  const send = async (text) => {
    const question = (text ?? input).trim();
    if (question.length < 3 || busy) return;
    setBusy(true);
    setError(null);
    setInput("");
    try {
      let id = activeId;
      if (!id) {
        const c = await chats.create(kind);
        id = c.id;
        setActiveId(id);
        setConv(c);
      }
      setConv((c) => c && { ...c, messages: [...(c.messages || []), { seq: -1, role: "user", content: question, pending: true }] });
      const out = await chats.send(id, question, getContext ? getContext() : null);
      setConv((c) => ({ ...out.conversation, messages: [...(c?.messages || []).filter((m) => !m.pending), ...out.messages] }));
      refreshList();
    } catch (e) {
      setError(e);
      setConv((c) => c && { ...c, messages: (c.messages || []).filter((m) => !m.pending) });
      setInput(question);
    } finally {
      setBusy(false);
    }
  };

  const rename = async (id, title) => {
    const t = title.trim();
    setRenaming(null);
    if (!t) return;
    try {
      const c = await chats.rename(id, t);
      if (id === activeId) setConv((old) => ({ ...old, title: c.title }));
      refreshList();
    } catch (e) { setError(e); }
  };

  const remove = async (id) => {
    setConfirmDelete(null);
    try {
      await chats.remove(id);
      if (id === activeId) setActiveId(null);
      refreshList();
    } catch (e) { setError(e); }
  };

  const messages = conv?.messages || [];
  return (
    <div className={`chat-shell ${compact ? "compact" : ""}`}>
      <aside className="chat-list" aria-label="Conversations">
        <button className="btn new-chat" onClick={newChat}><MessageSquarePlus size={16} /> New chat</button>
        {list === null && <p className="muted small">Loading conversations…</p>}
        {list?.length === 0 && <p className="muted small">No saved conversations yet. Your questions and answers are saved here.</p>}
        <ul>
          {list?.map((c) => (
            <li key={c.id} className={c.id === activeId ? "on" : ""}>
              {renaming === c.id ? (
                <form className="rename" onSubmit={(e) => { e.preventDefault(); rename(c.id, e.target.elements.t.value); }}>
                  <input name="t" defaultValue={c.title} maxLength={80} autoFocus aria-label="Conversation title" />
                  <button className="icon-btn" type="submit" aria-label="Save title"><Check size={14} /></button>
                  <button className="icon-btn" type="button" onClick={() => setRenaming(null)} aria-label="Cancel rename"><X size={14} /></button>
                </form>
              ) : confirmDelete === c.id ? (
                <div className="confirm">
                  <span className="small">Delete “{c.title}”?</span>
                  <button className="btn sm danger" onClick={() => remove(c.id)}>Delete</button>
                  <button className="btn sm" onClick={() => setConfirmDelete(null)}>Keep</button>
                </div>
              ) : (
                <>
                  <button className="chat-item" onClick={() => setActiveId(c.id)} aria-current={c.id === activeId ? "true" : undefined}>
                    <span className="chat-title">{c.title}</span>
                    <span className="muted small">{c.message_count / 2 | 0} question{c.message_count === 2 ? "" : "s"} · {relTime(c.updated_at)}</span>
                  </button>
                  <span className="chat-actions">
                    <button className="icon-btn" onClick={() => setRenaming(c.id)} aria-label={`Rename ${c.title}`}><Pencil size={13} /></button>
                    <button className="icon-btn" onClick={() => setConfirmDelete(c.id)} aria-label={`Delete ${c.title}`}><Trash2 size={13} /></button>
                  </span>
                </>
              )}
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat-main">
        <div className="chat" aria-live="polite">
          {conv && <div className="chat-head"><h3>{conv.title}</h3><span className="muted small">Saved conversation · {messages.length / 2 | 0} exchange{(messages.length / 2 | 0) === 1 ? "" : "s"}</span></div>}
          {messages.length === 0 && (
            <div className="msg system">{intro ?? <><b>Welcome.</b> Ask about NASA investigations, test conditions, habitat atmospheres or evidence gaps.</>}</div>
          )}
          {messages.map((m) => m.role === "user"
            ? <div key={`${m.seq}-u`} className={`msg user ${m.pending ? "pending" : ""}`}>{m.content}</div>
            : m.response ? <Answer key={`${m.seq}-a`} r={{ ...m.response, cached: m.cached }} context={m.context} onOpenExperiment={onOpenExperiment} /> : null)}
          {busy && <div className="msg system">Retrieving NASA evidence and validating the answer…</div>}
          <div ref={endRef} />
        </div>
        {error && <ErrorPanel error={error} onRetry={() => { setError(null); refreshList(); }} />}
        {suggestions.length > 0 && messages.length === 0 && !busy && (
          <div className="chips suggestions">
            <span className="faint small">Try:</span>
            {suggestions.map((q) => <button key={q} onClick={() => send(q)} disabled={busy}>{q}</button>)}
          </div>
        )}
        <div className="ask-row">
          <textarea rows={2} value={input} placeholder="Ask a question about NASA combustion research" aria-label="Your question" maxLength={1000}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
          <button className="btn primary" onClick={() => send()} disabled={busy || input.trim().length < 3}><Send size={16} /> Send</button>
        </div>
      </section>
    </div>
  );
}
