/**
 * JillaTeacher v6 — Jilla is a PERSON, not a system.
 *
 * One conversational panel where Jilla talks to you like a mentor
 * sitting next to you. She tells the story, reacts when you act,
 * explains concepts, and asks questions — all in one conversation.
 *
 * Messages appear automatically (event-driven). Student CAN type
 * back but doesn't have to. Jilla is the storyteller.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import PhaseCinematic from "./PhaseCinematic";
import IncidentTicker from "./IncidentTicker";

interface Props {
  sim: any;
  myRole: string;
  scenarioId: string;
  sessionId?: string;
}

interface JillaMessage {
  id: number;
  type: "story" | "react" | "teach" | "question" | "user" | "system";
  text: string;
  timestamp: number;
}

/** Jilla's animated face avatar — eyes blink, expression reacts to state */
function JillaFace({ size = 40, state = "idle" }: { size?: number; state?: "idle" | "thinking" | "speaking" }) {
  const s = size;
  const eyeW = Math.round(s * 0.15);
  const eyeH = Math.round(s * 0.2);
  const eyeTop = Math.round(s * 0.34);
  const eyeGap = Math.round(s * 0.22);
  const mouthW = Math.round(s * 0.25);
  const mouthBottom = Math.round(s * 0.2);

  return (
    <div className={`jilla-face-avatar jilla-face-${state}`}
      style={{ width: s, height: s, minWidth: s }}>
      {/* Left eye */}
      <div className="jilla-eye jilla-eye-l"
        style={{ width: eyeW, height: eyeH, top: eyeTop, left: `calc(50% - ${eyeGap}px)` }} />
      {/* Right eye */}
      <div className="jilla-eye jilla-eye-r"
        style={{ width: eyeW, height: eyeH, top: eyeTop, left: `calc(50% + ${eyeGap - eyeW}px)` }} />
      {/* Mouth / expression */}
      <div className="jilla-mouth"
        style={{ width: mouthW, bottom: mouthBottom, left: `calc(50% - ${mouthW / 2}px)` }} />
    </div>
  );
}

export default function JillaTeacher({ sim, myRole, scenarioId, sessionId = "" }: Props) {
  const [messages, setMessages] = useState<JillaMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [inputFocused, setInputFocused] = useState(false);
  const [unread, setUnread] = useState(0);

  // Phase cinematic
  const [cinematicPhase, setCinematicPhase] = useState<{ phase: string; prevPhase?: string } | null>(null);

  // Refs
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevSimRef = useRef<any>(null);
  const lastEventTick = useRef(0);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const introDone = useRef(false);
  const seqRef = useRef(0);

  // ---- Add message ----
  const addJillaMsg = useCallback((type: JillaMessage["type"], text: string) => {
    seqRef.current++;
    const msg: JillaMessage = { id: seqRef.current, type, text, timestamp: Date.now() };
    setMessages(prev => [...prev, msg]);
    if (!panelOpen) setUnread(prev => prev + 1);
  }, [panelOpen]);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // ---- Fire event to backend ----
  const fireEvent = useCallback(async (eventType: string, eventData: Record<string, any> = {}) => {
    lastEventTick.current = sim?.tick || 0;
    setLoading(true);
    try {
      const resp = await fetch("/api/jilla/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: eventType, session_id: sessionId,
          role: myRole, scenario_id: scenarioId,
          sim_state: sim || {}, event_data: eventData,
        }),
      });
      const data = await resp.json();
      if (data.narration) {
        addJillaMsg("story", data.narration);
      }
      if (data.card && data.card.title && data.card.body) {
        // Teach the concept as a message, not a floating card
        addJillaMsg("teach", `**${data.card.title}**\n${data.card.body}`);
      }
    } catch { /* silent */ }
    setLoading(false);
  }, [sim, myRole, scenarioId, sessionId, addJillaMsg]);

  // ---- Intro ----
  useEffect(() => {
    if (introDone.current || !myRole) return;
    introDone.current = true;
    fetch(`/api/jilla/intro?role=${myRole}&scenario_id=${scenarioId}`)
      .then(r => r.json())
      .then(data => {
        if (data.narration) addJillaMsg("story", data.narration);
        if (data.card?.body) {
          setTimeout(() => addJillaMsg("teach", data.card.body), 2000);
        }
      })
      .catch(() => addJillaMsg("story", "Hey, I'm Jilla. I'll be guiding you through this scenario. Let's begin."));
  }, [myRole, scenarioId, addJillaMsg]);

  // ---- Event detection ----
  useEffect(() => {
    const prev = prevSimRef.current;
    prevSimRef.current = sim;
    if (!sim || !prev) return;
    if (sim.tick - lastEventTick.current < 3) return;

    const curPhase = sim.guide?.phase;
    const prevPhase = prev.guide?.phase;
    if (curPhase && curPhase !== prevPhase) {
      setCinematicPhase({ phase: curPhase, prevPhase });
      fireEvent("phase_changed", { phase: curPhase, prev_phase: prevPhase });
      return;
    }

    const curEvents = sim.events || [];
    const prevEvents = prev.events || [];
    if (curEvents.length > prevEvents.length) {
      const newEvts = curEvents.slice(prevEvents.length);
      const toolEvt = newEvts.find((e: any) => e.kind === "action" || e.kind === "response");
      if (toolEvt) {
        fireEvent("tool_used", {
          tool_id: toolEvt.data?.tool_id || "", tool_name: toolEvt.title || "",
          role: toolEvt.role || myRole,
        });
        return;
      }
    }

    const curInfected = sim.worm?.infected || 0;
    const prevInfected = prev.worm?.infected || 0;
    if (curInfected > prevInfected && curInfected - prevInfected >= 2) {
      fireEvent("host_infected", { count: curInfected, delta: curInfected - prevInfected });
      return;
    }

    const curAlerts = sim.alerts?.length || 0;
    const prevAlerts = prev.alerts?.length || 0;
    if (curAlerts > prevAlerts) {
      const newAlert = sim.alerts[sim.alerts.length - 1];
      fireEvent("alert_generated", { alert: newAlert?.label, severity: newAlert?.severity });
      return;
    }

    if (sim.worm?.segmented && !prev.worm?.segmented) {
      fireEvent("tool_used", { tool_id: "segment", tool_name: "Network Segmentation", role: "blue" });
      return;
    }
    if (sim.worm?.kill_switch === "sinkholed" && prev.worm?.kill_switch !== "sinkholed") {
      fireEvent("tool_used", { tool_id: "sinkhole", tool_name: "Kill Switch Sinkhole", role: "blue" });
      return;
    }
    if (sim.finished && !prev.finished) {
      fireEvent("phase_changed", { phase: "Debrief", prev_phase: sim.guide?.phase });
    }
  }, [sim?.tick, fireEvent, myRole]);

  // ---- Idle detection ----
  useEffect(() => {
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => {
      fireEvent("idle_too_long", { idle_seconds: 45 });
    }, 45000);
    return () => { if (idleTimer.current) clearTimeout(idleTimer.current); };
  }, [sim?.guide?.progress?.done, fireEvent]);

  // ---- Student sends a message ----
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg = text.trim();
    setInput("");
    addJillaMsg("user", userMsg);
    setLoading(true);
    try {
      const history = messages.slice(-8).map(m => ({
        role: m.type === "user" ? "user" : "assistant",
        content: m.text,
      }));
      const resp = await fetch("/api/jilla/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg, role: myRole, scenario_id: scenarioId,
          sim_state: sim || {}, history,
        }),
      });
      const data = await resp.json();
      addJillaMsg("react", data.message);
    } catch {
      addJillaMsg("react", "Sorry, I couldn't process that. Try again?");
    }
    setLoading(false);
  }, [loading, messages, myRole, scenarioId, sim, addJillaMsg]);

  // ---- Keyboard shortcut ----
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "j" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tag = (e.target as HTMLElement).tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        setPanelOpen(prev => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // ---- Render markdown ----
  const renderMd = (text: string) =>
    text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**"))
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      if (part.startsWith("`") && part.endsWith("`"))
        return <code key={i} className="jilla-inline-code">{part.slice(1, -1)}</code>;
      return <span key={i}>{part}</span>;
    });

  // Message style by type
  const msgStyle = (type: string) => {
    switch (type) {
      case "story": return "jilla-msg-story";
      case "react": return "jilla-msg-react";
      case "teach": return "jilla-msg-teach";
      case "question": return "jilla-msg-question";
      case "user": return "jilla-msg-user";
      case "system": return "jilla-msg-system";
      default: return "";
    }
  };

  return (
    <>
      {/* News Ticker */}
      <IncidentTicker sim={sim} scenarioId={scenarioId} />

      {/* Phase Cinematic */}
      {cinematicPhase && (
        <PhaseCinematic
          phase={cinematicPhase.phase}
          prevPhase={cinematicPhase.prevPhase}
          role={myRole}
          onDismiss={() => setCinematicPhase(null)}
        />
      )}

      {/* ---- Jilla Panel (the main experience) ---- */}
      {panelOpen ? (
        <div className="jilla-convo-panel">
          {/* Header */}
          <div className="jilla-convo-header">
            <JillaFace size={38} state={loading ? "thinking" : "idle"} />
            <div className="jilla-convo-info">
              <div className="jilla-convo-name">Jilla</div>
              <div className="jilla-convo-status">
                {loading ? "thinking..." : `guiding you as ${myRole.toUpperCase()}`}
              </div>
            </div>
            <button className="jilla-convo-minimize" onClick={() => setPanelOpen(false)}
              title="Minimize (press J to reopen)">
              <i className="fa fa-chevron-right" />
            </button>
          </div>

          {/* Messages */}
          <div className="jilla-convo-messages" ref={scrollRef}>
            {messages.map(msg => (
              <div key={msg.id} className={`jilla-convo-msg ${msgStyle(msg.type)}`}>
                {msg.type !== "user" && msg.type !== "system" && (
                  <JillaFace size={28} state={loading ? "thinking" : "speaking"} />
                )}
                <div className={`jilla-convo-bubble ${msg.type === "user" ? "user-bubble" : "jilla-bubble"}`}>
                  {renderMd(msg.text)}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {loading && (
              <div className="jilla-convo-msg jilla-msg-react">
                <JillaFace size={28} state={loading ? "thinking" : "speaking"} />
                <div className="jilla-convo-typing">
                  <span className="jilla-dot" />
                  <span className="jilla-dot" style={{ animationDelay: "0.15s" }} />
                  <span className="jilla-dot" style={{ animationDelay: "0.3s" }} />
                </div>
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="jilla-convo-actions">
            {["What should I do?", "Tell me more", "Why does this matter?"].map(q => (
              <button key={q} className="jilla-convo-chip" onClick={() => sendMessage(q)} disabled={loading}>
                {q}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className={`jilla-convo-input-area${inputFocused ? " focused" : ""}`}>
            <form onSubmit={e => { e.preventDefault(); sendMessage(input); }} className="jilla-convo-form">
              <input value={input} onChange={e => setInput(e.target.value)} disabled={loading}
                placeholder="Ask Jilla anything..."
                className="jilla-convo-input"
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)} />
              <button type="submit" disabled={loading || !input.trim()}
                className={`jilla-convo-send${input.trim() ? " active" : ""}`}>
                <i className="fa fa-arrow-up" />
              </button>
            </form>
          </div>
        </div>
      ) : (
        /* Collapsed: small floating button with unread badge */
        <button className="jilla-fab" onClick={() => { setPanelOpen(true); setUnread(0); }}
          style={{ position: "fixed", bottom: 20, right: 20, zIndex: 9000 }}>
          <JillaFace size={30} state="idle" />
          {unread > 0 && <span className="jilla-fab-badge">{unread}</span>}
        </button>
      )}
    </>
  );
}
