import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import Header from "../components/Header.jsx";
import SampleBanner from "../components/SampleBanner.jsx";
import { EvidenceLink } from "../components/Evidence.jsx";
import { TierTag } from "../components/Tags.jsx";
import { SUGGESTED_QUESTIONS } from "../data/constants.js";
import { askQuestion, useApi } from "../services/api.js";
import { evidenceKind } from "../utils/format.js";

const MODE_LABEL = {
  llm_validated: "Language-model answer, validated against cited evidence",
  deterministic: "Deterministic answer computed from the database",
  evidence_only: "Evidence list only (no validated prose)",
};

export default function AIAssistant({ onOpenExperiment }) {
  const [messages, setMessages] = useState([{ role: "system", kind: "welcome" }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);
  const { data: health } = useApi("/api/health");

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages, loading]);

  // Deep link: #/assistant?q=... asks the question on load (shareable demo answers)
  useEffect(() => {
    const q = new URLSearchParams(window.location.hash.split("?")[1] || "").get("q");
    if (q) send(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = async (text) => {
    const question = (text ?? input).trim();
    if (question.length < 3 || loading) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const result = await askQuestion(question);
      setMessages((m) => [...m, { role: "system", kind: "answer", question, result }]);
    } catch (error) {
      setMessages((m) => [...m, { role: "system", kind: "error", text: error.message }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <SampleBanner>
        Every statement cites NASA evidence and is checked by a validator before it is shown: citations must resolve and every number must appear in the cited source.
        {health && !health.copilot_configured && " No language model is configured on this server, so answers are built deterministically from the database."}
      </SampleBanner>
      <Header eyebrow="AI Copilot" title="Ask about NASA combustion evidence"
        description="Answers separate measured evidence, reported text, literature and interpretation. FIREWISE does not predict fire risk or partial-gravity behaviour." />

      <div className="panel chat" aria-live="polite">
        {messages.map((msg, i) => <Message key={i} msg={msg} onOpenExperiment={onOpenExperiment} />)}
        {loading && <div className="msg system">Retrieving NASA evidence and validating the answer…</div>}
        <div ref={endRef} />
      </div>

      <div className="chips">
        {SUGGESTED_QUESTIONS.map((q) => <button key={q} onClick={() => send(q)} disabled={loading}>{q}</button>)}
      </div>

      <div className="ask-row">
        <textarea rows={2} value={input} placeholder="Ask a question about NASA combustion research" aria-label="Your question" maxLength={1000}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
        <button className="btn primary" onClick={() => send()} disabled={loading || input.trim().length < 3}>
          <Send size={16} /> Send
        </button>
      </div>
    </>
  );
}

function Message({ msg, onOpenExperiment }) {
  if (msg.role === "user") return <div className="msg user">{msg.text}</div>;
  if (msg.kind === "welcome") {
    return <div className="msg system"><b>Welcome.</b> Ask about specific investigations, test conditions, habitat atmospheres or evidence gaps. Try one of the questions below.</div>;
  }
  if (msg.kind === "error") {
    return <div className="msg system">The request failed: {msg.text} The other pages keep working without the Copilot.</div>;
  }
  const r = msg.result;
  return (
    <div className="msg system answer">
      <div className="tags">
        <span className={`tag ${r.status === "answered" ? "green" : r.status === "partial" ? "amber" : "red"}`}>
          {r.status === "answered" ? "Answered" : r.status === "partial" ? "Partial answer" : "Insufficient evidence"}
        </span>
        <span className="tag">{MODE_LABEL[r.mode]}</span>
        <span className="tag mono">{r.latency_ms} ms</span>
      </div>
      {r.notice && <p className="note small">{r.notice}</p>}
      {r.answer_summary && <p className="summary">{r.answer_summary}</p>}
      {r.claims.length > 0 && (
        <ul className="claims">
          {r.claims.map((c, i) => (
            <li key={i}>
              <TierTag tier={c.tier} />
              <span>{c.text}</span>
              <span className="ev-row">{c.evidence_ids.map((id) => <EvidenceLink key={id} id={id} />)}</span>
            </li>
          ))}
        </ul>
      )}
      {r.limitations.length > 0 && <><h4>Limitations</h4><ul>{r.limitations.map((l, i) => <li key={i} className="muted">{l}</li>)}</ul></>}
      {r.gaps.length > 0 && <><h4>Evidence gaps</h4><ul>{r.gaps.map((g, i) => <li key={i} className="muted">{g}</li>)}</ul></>}
      {r.related_investigations.length > 0 && (
        <><h4>Related investigations</h4>
          <p>{r.related_investigations.map((id, i) => <span key={id}>{i ? ", " : ""}<button className="linkish" onClick={() => onOpenExperiment(id)}>{id}</button></span>)}</p></>
      )}
      {r.evidence.length > 0 && (
        <details className="evidence-list">
          <summary>Evidence consulted ({r.evidence.length})</summary>
          <ul>
            {r.evidence.map((e) => (
              <li key={e.evidence_id}>
                <EvidenceLink id={e.evidence_id} label={e.title} />
                <span className="muted small"> {evidenceKind(e.kind)}</span>
                <div className="muted small clamp2">{e.snippet}</div>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
