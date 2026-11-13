import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import SampleBanner from "../components/SampleBanner.jsx";
import Header from "../components/Header.jsx";
import { SUGGESTED_QUESTIONS } from "../data/sampleData.js";
import { askQuestion } from "../services/api.js";

// Sections the real answer will fill once the backend is connected
const ANSWER_SECTIONS = ["Answer", "Key findings", "Supporting NASA experiments", "Source documents and citations", "Related questions"];

export default function AIAssistant() {
  const [messages, setMessages] = useState([{ role: "system", kind: "welcome" }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages, loading]);

  const send = async () => {
    const question = input.trim();
    if (!question || loading) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    try {
      const result = await askQuestion(question);
      setMessages((m) => [...m, { role: "system", kind: result.status === "ok" ? "answer" : "not_connected", question, result }]);
    } catch (error) {
      setMessages((m) => [...m, { role: "system", kind: "error", text: error.message }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <SampleBanner />
      <Header sample={false} title="AI Research Assistant"
        description="Ask questions about microgravity combustion research. Answers will be grounded in retrieved NASA documents once the RAG backend is connected." />

      <div className="panel chat" aria-live="polite">
        {messages.map((msg, i) => <Message key={i} msg={msg} />)}
        {loading && <div className="msg system">Waiting for the backend…</div>}
        <div ref={endRef} />
      </div>

      <div className="chips">
        {SUGGESTED_QUESTIONS.map((q) => <button key={q} onClick={() => setInput(q)}>{q}</button>)}
      </div>

      <div className="ask-row">
        <textarea rows={2} value={input} placeholder="Ask a question about NASA combustion research" aria-label="Your question"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
        <button className="btn primary" onClick={send} disabled={loading || !input.trim()}>
          <Send size={16} /> Send
        </button>
      </div>
    </>
  );
}

// Renders one chat message (user question, placeholder card, real answer or error)
function Message({ msg }) {
  if (msg.role === "user") return <div className="msg user">{msg.text}</div>;

  if (msg.kind === "welcome") {
    return <div className="msg system"><b>Welcome.</b> You can ask about flame behavior, specific experiments, or fire safety. The assistant is not connected yet, so questions are not answered at this stage.</div>;
  }
  if (msg.kind === "error") {
    return <div className="msg system">The request failed: {msg.text} Check that the backend is running, then try again.</div>;
  }
  if (msg.kind === "answer") {
    const { answer, key_findings = [], sources = [], related_experiments = [] } = msg.result;
    return (
      <div className="msg system">
        <p>{answer}</p>
        {key_findings.length > 0 && <><h4>Key findings</h4><ul>{key_findings.map((f, i) => <li key={i}>{f}</li>)}</ul></>}
        {related_experiments.length > 0 && <><h4>Supporting experiments</h4><p>{related_experiments.join(", ")}</p></>}
        {sources.length > 0 && (
          <><h4>Sources</h4><ul>{sources.map((s, i) => (
            <li key={i}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a> {s.experiment && `– ${s.experiment}`} {s.year && `(${s.year})`}</li>
          ))}</ul></>
        )}
      </div>
    );
  }
  // not_connected: show where the real answer will appear
  return (
    <div className="msg system">
      <b>Assistant not connected.</b> This is where the answer to “{msg.question}” will appear after the RAG backend is implemented. No answer or citation is generated in this prototype.
      <div className="slots">{ANSWER_SECTIONS.map((s) => <div key={s} className="slot">{s}: waiting for backend</div>)}</div>
    </div>
  );
}
