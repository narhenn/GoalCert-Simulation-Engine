/**
 * JillaChat — AI cybersecurity tutor chat panel.
 *
 * Replaces the static GuidePanel with an interactive AI assistant that:
 * - Proactively teaches at phase transitions
 * - Responds to student questions with contextual awareness
 * - Progressive hints (4 levels)
 * - Highlights nodes/tools when referenced
 * - Quick-action suggestion buttons
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { TEAM_META } from "./shared";

interface Message {
  id: number;
  role: "jilla" | "user";
  content: string;
  suggestions?: string[];
  highlight_host?: string | null;
  highlight_tool?: string | null;
  timestamp: number;
}

interface Props {
  sim: any;
  myRole: string;
  scenarioId: string;
  onHighlightNode?: (hostId: string | null) => void;
  onHighlightTool?: (toolId: string | null) => void;
}

const JILLA_AVATAR = "🤖";

export default function JillaChat({ sim, myRole, scenarioId, onHighlightNode, onHighlightTool }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [hintLevel, setHintLevel] = useState(1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastPhaseRef = useRef("");
  const seqRef = useRef(0);
  const initDone = useRef(false);

  const meta = TEAM_META[myRole] || TEAM_META.red;

  const addMessage = useCallback((msg: Omit<Message, "id" | "timestamp">) => {
    seqRef.current++;
    setMessages(prev => [...prev, { ...msg, id: seqRef.current, timestamp: Date.now() }]);
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Intro message on first load
  useEffect(() => {
    if (initDone.current) return;
    initDone.current = true;
    fetch(`/api/jilla/intro?role=${myRole}&scenario_id=${scenarioId}`)
      .then(r => r.json())
      .then(data => {
        addMessage({ role: "jilla", content: data.message, suggestions: data.suggestions });
      })
      .catch(() => {
        addMessage({
          role: "jilla",
          content: `Hey! I'm **Jilla**, your cyber range instructor.\n\nI can see the simulation state and help you learn. Ask me anything!`,
          suggestions: ["What should I do first?", "Explain this scenario", "Just nudge me"],
        });
      });
  }, [myRole, scenarioId, addMessage]);

  // Proactive phase transition messages
  useEffect(() => {
    const phase = sim?.guide?.phase;
    if (!phase || phase === lastPhaseRef.current) return;
    lastPhaseRef.current = phase;
    setHintLevel(1); // Reset hint level on new phase

    // Don't spam on the first phase (intro already covers it)
    if (messages.length < 2) return;

    const guide = sim.guide;
    const nextTool = guide?.next_tools?.[myRole];
    const phaseMsg = `**Phase transition → ${phase}**\n\nYou're now in the **${phase}** phase.${nextTool ? `\n\nNext suggested tool: **${nextTool.name}**` : ""}`;

    addMessage({
      role: "jilla",
      content: phaseMsg,
      suggestions: ["What should I do?", "Explain this phase", "I'm stuck"],
      highlight_tool: nextTool?.id || null,
    });
  }, [sim?.guide?.phase, myRole, messages.length, addMessage, sim?.guide]);

  // Send message to Jilla API
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg = text.trim();
    setInput("");
    addMessage({ role: "user", content: userMsg });
    setLoading(true);

    try {
      const history = messages.slice(-6).map(m => ({
        role: m.role === "jilla" ? "assistant" : "user",
        content: m.content,
      }));

      const resp = await fetch("/api/jilla/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          role: myRole,
          scenario_id: scenarioId,
          sim_state: sim || {},
          history,
        }),
      });
      const data = await resp.json();

      addMessage({
        role: "jilla",
        content: data.message,
        suggestions: data.suggestions,
        highlight_host: data.highlight_host,
        highlight_tool: data.highlight_tool,
      });

      if (data.highlight_host) onHighlightNode?.(data.highlight_host);
      if (data.highlight_tool) onHighlightTool?.(data.highlight_tool);
    } catch {
      addMessage({ role: "jilla", content: "Sorry, I couldn't process that. Try again?" });
    } finally {
      setLoading(false);
    }
  }, [loading, messages, myRole, scenarioId, sim, addMessage, onHighlightNode, onHighlightTool]);

  // Get progressive hint
  const getHint = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch("/api/jilla/hint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: myRole,
          scenario_id: scenarioId,
          sim_state: sim || {},
          hint_level: hintLevel,
        }),
      });
      const data = await resp.json();
      addMessage({
        role: "jilla",
        content: data.message,
        suggestions: data.suggestions,
      });
      setHintLevel(prev => Math.min(prev + 1, 4));
    } catch {
      addMessage({ role: "jilla", content: "Hmm, couldn't generate a hint. Try asking me directly!" });
    } finally {
      setLoading(false);
    }
  }, [myRole, scenarioId, sim, hintLevel, addMessage]);

  // Handle suggestion click
  const handleSuggestion = (text: string) => {
    if (text.toLowerCase().includes("hint") || text.toLowerCase().includes("stuck")) {
      getHint();
    } else {
      sendMessage(text);
    }
  };

  // Collapsed state
  if (collapsed) {
    return (
      <div style={{ width: 44, background: "#fff", borderRight: "1px solid var(--gc-border)",
        display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 14, cursor: "pointer",
        gap: 8, flexShrink: 0 }}
        onClick={() => setCollapsed(false)}>
        <div style={{ fontSize: 20 }}>{JILLA_AVATAR}</div>
        <div style={{ writingMode: "vertical-rl", fontSize: 10, color: "var(--gc-primary)", fontWeight: 700,
          letterSpacing: 1 }}>JILLA</div>
        {messages.length > 0 && (
          <div style={{ width: 18, height: 18, borderRadius: "50%", background: "var(--gc-primary)",
            color: "#fff", fontSize: 9, fontWeight: 700, display: "flex", alignItems: "center",
            justifyContent: "center" }}>
            {messages.filter(m => m.role === "jilla").length}
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ width: 320, background: "#fff", borderRight: "1px solid var(--gc-border)",
      display: "flex", flexDirection: "column", flexShrink: 0 }}>

      {/* Header */}
      <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--gc-border)",
        display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 20 }}>{JILLA_AVATAR}</span>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--gc-text)" }}>Jilla</div>
          <div style={{ fontSize: 10, color: "var(--gc-muted)" }}>AI Instructor · {myRole.toUpperCase()} perspective</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          <button onClick={getHint} disabled={loading}
            style={{ background: "var(--gc-soft)", border: "1px solid var(--gc-border)", borderRadius: 6,
              padding: "4px 8px", fontSize: 10, fontWeight: 600, color: "var(--gc-primary)", cursor: "pointer" }}
            title="Get a progressive hint">
            💡 Hint
          </button>
          <button onClick={() => setCollapsed(true)}
            style={{ background: "none", border: "none", color: "var(--gc-muted)", cursor: "pointer", fontSize: 12 }}>
            <i className="fa fa-chevron-left" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: "10px 12px",
        display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
        {messages.map(msg => (
          <div key={msg.id} style={{ display: "flex", flexDirection: "column",
            alignItems: msg.role === "user" ? "flex-end" : "flex-start", gap: 4 }}>

            {/* Avatar + bubble */}
            <div style={{ display: "flex", gap: 6, alignItems: msg.role === "user" ? "flex-end" : "flex-start",
              flexDirection: msg.role === "user" ? "row-reverse" : "row", maxWidth: "92%" }}>
              {msg.role === "jilla" && (
                <div style={{ width: 24, height: 24, borderRadius: "50%", background: "var(--gc-soft)",
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, flexShrink: 0 }}>
                  {JILLA_AVATAR}
                </div>
              )}
              <div style={{
                background: msg.role === "user" ? "var(--gc-primary)" : "var(--gc-soft)",
                color: msg.role === "user" ? "#fff" : "var(--gc-text)",
                borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                padding: "8px 12px", fontSize: 12.5, lineHeight: 1.6,
                whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}>
                {/* Simple markdown: bold and code */}
                {msg.content.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) => {
                  if (part.startsWith("**") && part.endsWith("**")) {
                    return <strong key={i}>{part.slice(2, -2)}</strong>;
                  }
                  if (part.startsWith("`") && part.endsWith("`")) {
                    return <code key={i} style={{ background: msg.role === "user" ? "rgba(255,255,255,0.2)" : "rgba(73,2,162,0.08)",
                      padding: "1px 4px", borderRadius: 3, fontFamily: "var(--mono)", fontSize: 11.5 }}>
                      {part.slice(1, -1)}
                    </code>;
                  }
                  return <span key={i}>{part}</span>;
                })}
              </div>
            </div>

            {/* Suggestion buttons */}
            {msg.role === "jilla" && msg.suggestions && msg.suggestions.length > 0 && (
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap", paddingLeft: 30, marginTop: 2 }}>
                {msg.suggestions.map((s, i) => (
                  <button key={i} onClick={() => handleSuggestion(s)} disabled={loading}
                    style={{ fontSize: 10.5, padding: "4px 10px", borderRadius: 20,
                      background: "var(--gc-soft)", border: "1px solid var(--gc-border)",
                      color: "var(--gc-primary)", cursor: "pointer", fontWeight: 500,
                      transition: "all 0.15s", whiteSpace: "nowrap" }}
                    onMouseEnter={e => { (e.target as HTMLElement).style.background = "var(--gc-primary)"; (e.target as HTMLElement).style.color = "#fff"; }}
                    onMouseLeave={e => { (e.target as HTMLElement).style.background = "var(--gc-soft)"; (e.target as HTMLElement).style.color = "var(--gc-primary)"; }}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div style={{ display: "flex", gap: 6, alignItems: "center", paddingLeft: 30 }}>
            <div style={{ width: 24, height: 24, borderRadius: "50%", background: "var(--gc-soft)",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>
              {JILLA_AVATAR}
            </div>
            <div style={{ background: "var(--gc-soft)", borderRadius: 14, padding: "8px 14px" }}>
              <span className="spinner" style={{ width: 12, height: 12 }} />
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ padding: "8px 12px", borderTop: "1px solid var(--gc-border)", flexShrink: 0 }}>
        <form onSubmit={e => { e.preventDefault(); sendMessage(input); }}
          style={{ display: "flex", gap: 6 }}>
          <input value={input} onChange={e => setInput(e.target.value)} disabled={loading}
            placeholder="Ask Jilla anything..."
            style={{ flex: 1, padding: "8px 12px", borderRadius: 20, border: "1px solid var(--gc-border)",
              fontSize: 12.5, background: "var(--gc-soft)", color: "var(--gc-text)", outline: "none" }}
            onFocus={e => (e.target.style.borderColor = "var(--gc-primary)")}
            onBlur={e => (e.target.style.borderColor = "var(--gc-border)")} />
          <button type="submit" disabled={loading || !input.trim()}
            style={{ width: 34, height: 34, borderRadius: "50%", border: "none",
              background: input.trim() ? "var(--gc-primary)" : "var(--gc-soft)",
              color: input.trim() ? "#fff" : "var(--gc-muted)", cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13,
              transition: "all 0.15s" }}>
            <i className="fa fa-paper-plane" />
          </button>
        </form>
      </div>
    </div>
  );
}
