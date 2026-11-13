import { useEffect, useState } from "react";
import { PageHeader } from "../components/ui.jsx";
import ChatPanel from "../components/ChatPanel.jsx";
import { SUGGESTED_QUESTIONS } from "../data/constants.js";
import { useApi, chats } from "../services/api.js";

export default function AIAssistant({ onOpenExperiment }) {
  const { data: health } = useApi("/api/health");
  const [deepLink, setDeepLink] = useState(null);

  // Deep link: #/assistant?q=... opens a new saved conversation with that question
  useEffect(() => {
    const q = new URLSearchParams(window.location.hash.split("?")[1] || "").get("q");
    if (!q) return;
    chats.create("general").then((c) => chats.send(c.id, q).then(() => {
      try { window.localStorage.setItem("firewise.chat.active.general", c.id); } catch { /* storage blocked */ }
      setDeepLink(c.id);
    })).catch(() => setDeepLink("error"));
  }, []);

  const waiting = new URLSearchParams(window.location.hash.split("?")[1] || "").get("q") && !deepLink;
  return (
    <>
      <PageHeader title="Copilot" description="Ask a scientific question about NASA's combustion evidence. Answers cite their sources and separate documented evidence, calculations, unknowns and interpretation."
        note={`${health && !health.copilot_configured ? "No language model is configured on this server, so answers are built deterministically from the database. " : ""}Every claim is checked before it is shown: citations must resolve and every number must appear in the cited source. FIREWISE does not predict fire risk or partial-gravity behaviour. Conversations are saved in this browser's workspace.`} />
      {waiting ? <div className="panel">Opening your question…</div> : (
        <ChatPanel key={deepLink || "chat"} kind="general" suggestions={SUGGESTED_QUESTIONS} onOpenExperiment={onOpenExperiment}
          intro={<><b>Welcome.</b> Ask about specific investigations, test conditions, habitat atmospheres or evidence gaps. Your conversations are saved — switch between them on the left.</>} />
      )}
    </>
  );
}
