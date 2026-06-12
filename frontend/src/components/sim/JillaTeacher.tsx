/**
 * JillaTeacher — the orchestrator that replaces JillaChat.
 *
 * NOT a sidebar chat. Instead:
 * - Floating teaching cards that appear next to relevant workspace elements
 * - Spotlight overlay that dims everything except what to look at
 * - Topology annotations
 * - A small FAB button (bottom-right) to summon Jilla
 * - Proactive teaching at phase transitions
 * - Chat input for free-form questions (slides up from FAB)
 */
import { useCallback, useEffect, useRef, useState } from "react";
import JillaSpotlight from "./JillaSpotlight";
import TeachingCard, { AttackFlowDiagram } from "./TeachingCard";
import { TEAM_META } from "./shared";

interface Props {
  sim: any;
  myRole: string;
  scenarioId: string;
}

interface FloatingCard {
  id: number;
  type: "concept" | "action" | "result" | "flow";
  title: string;
  body: string;
  code?: string;
  diagram?: React.ReactNode;
  position: { top: number; right: number };
}

// Phase-specific teaching content for W1
const PHASE_TEACHINGS: Record<string, { title: string; body: string; type: "concept" | "action" | "result" }> = {
  "Host Discovery": {
    type: "concept",
    title: "🤔 Phase 1: Reconnaissance",
    body: "Before an attacker can strike, they need to know what's out there.\n\n**Question:** What's the first thing you'd do if you landed on a network you've never seen before? Look at your tool palette — which tool maps a network?",
  },
  "SMB Enumeration": {
    type: "action",
    title: "🤔 Phase 2: Finding Targets",
    body: "You found hosts. But not all are vulnerable.\n\n**Question:** WannaCry exploits a specific protocol. Look at the amber hosts on the map — what do they all have in common? What's the protocol from 2006 that has a critical remote code execution flaw?",
  },
  "Exploit": {
    type: "action",
    title: "⚡ Phase 3: The Exploit",
    body: "You found vulnerable targets. Now comes the critical moment.\n\n**Question:** The exploit is named **EternalBlue**. It was discovered by which intelligence agency and leaked by which group? Watch the target node when you fire — what happens to the SOC's IDS?",
  },
  "Payload": {
    type: "concept",
    title: "🤔 Phase 4: Payload",
    body: "The exploit gave you a shell — but that's temporary.\n\n**Question:** What's the difference between having a shell and having the worm resident on the host? Why does the node change from orange to red?",
  },
  "Persistence": {
    type: "concept",
    title: "🤔 Phase 5: Persistence",
    body: "If an IT admin simply reboots this host, what happens to your foothold?\n\n**Question:** What could you install that would make the worm start automatically at boot? Look for the ⚓ icon — what does it mean for the defender?",
  },
  "C2": {
    type: "concept",
    title: "🤔 Phase 6: The Kill Switch",
    body: "WannaCry has a fascinating secret that stopped the entire global outbreak.\n\n**Question:** Why would a malware author hardcode a domain check that stops the worm if it resolves? Was it a bug, a sandbox check, or an intentional kill switch? What could Blue do with this knowledge?",
  },
  "Lateral Movement": {
    type: "action",
    title: "⚡ Phase 7: Propagation",
    body: "This is what makes it a **WORM** instead of regular malware.\n\n**Watch the map** as you press this. The R-value is the reproduction rate — if it's 3.0, each infected host infects 3 others. **Question:** What's the most effective single action Blue could take to cap the blast radius?",
  },
  "Disable Recovery": {
    type: "action",
    title: "⚡ Phase 8: Point of No Return",
    body: "Before encrypting, smart ransomware cuts the safety net.\n\n**Question:** What are **shadow copies** and why does the attacker delete them? If you were Blue, what would you protect RIGHT NOW before it's too late?",
  },
  "Impact": {
    type: "result",
    title: "💀 Phase 9: Impact",
    body: "The hospital goes dark. Files are encrypted. Ransom notes appear.\n\n**Reflect:** At which earlier phase could this have been stopped with the least effort? Switch to **Victim Desktop** to see the human impact. Switch to **Blue** to see what recovery looks like.",
  },
};

export default function JillaTeacher({ sim, myRole, scenarioId }: Props) {
  const [showFab, setShowFab] = useState(true);
  const [floatingCard, setFloatingCard] = useState<FloatingCard | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatResponse, setChatResponse] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [spotlightActive, setSpotlightActive] = useState(false);
  const [spotlightStep, setSpotlightStep] = useState(0);
  const lastPhaseRef = useRef("");
  const seqRef = useRef(0);
  const meta = TEAM_META[myRole] || TEAM_META.red;

  // Show teaching card on phase transition
  useEffect(() => {
    const phase = sim?.guide?.phase;
    if (!phase || phase === lastPhaseRef.current) return;
    lastPhaseRef.current = phase;

    const teaching = PHASE_TEACHINGS[phase];
    if (teaching) {
      seqRef.current++;
      setFloatingCard({
        id: seqRef.current,
        type: teaching.type,
        title: teaching.title,
        body: teaching.body,
        position: { top: 80, right: 20 },
      });
      // Auto-dismiss after 15s
      const timer = setTimeout(() => setFloatingCard(prev => prev?.id === seqRef.current ? null : prev), 15000);
      return () => clearTimeout(timer);
    }
  }, [sim?.guide?.phase]);

  // Show result card after tool execution
  useEffect(() => {
    const events = sim?.events || [];
    const last = events[events.length - 1];
    if (!last || !last.notify || !last.data?.consequence) return;

    seqRef.current++;
    const id = seqRef.current;
    setFloatingCard({
      id,
      type: "result",
      title: `${last.title}`,
      body: last.data.consequence + (last.data.teaching_note ? `\n\n**Learn:** ${last.data.teaching_note}` : ""),
      code: last.data.command || undefined,
      position: { top: 80, right: 20 },
    });
    setTimeout(() => setFloatingCard(prev => prev?.id === id ? null : prev), 12000);
  }, [sim?.events?.length]);

  // Chat with Jilla
  const sendChat = useCallback(async (msg: string) => {
    if (!msg.trim() || chatLoading) return;
    setChatInput("");
    setChatLoading(true);
    setChatResponse("");

    try {
      const resp = await fetch("/api/jilla/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg.trim(), role: myRole, scenario_id: scenarioId,
          sim_state: sim || {}, history: [],
        }),
      });
      const data = await resp.json();
      setChatResponse(data.message);
    } catch {
      setChatResponse("Sorry, couldn't process that. Try again?");
    } finally {
      setChatLoading(false);
    }
  }, [chatLoading, myRole, scenarioId, sim]);

  // Spotlight walkthrough
  const spotlightSteps = [
    { target: ".topo", type: "concept" as const, title: "This is your network",
      body: "Each node is a host. Colors show their security state:\n🟢 Healthy  🟡 Vulnerable  🟠 Exploited  🔴 Infected  ⬛ Impacted  🔵 Contained" },
    { target: ".ws-card:has(h3)", type: "action" as const, title: "Your tools are here",
      body: "Click a tool to read its briefing and stage its command. Tools unlock as you progress through the kill chain." },
    { target: ".term", type: "concept" as const, title: "The terminal",
      body: "This is a real Kali terminal. Stage a tool above, then type its command here to execute it. Everything you run is real." },
  ];

  return (
    <>
      {/* Floating teaching card */}
      {floatingCard && (
        <div style={{ position: "fixed", top: floatingCard.position.top, right: floatingCard.position.right,
          zIndex: 9200, animation: "cardAppear 0.35s ease" }}>
          <TeachingCard
            type={floatingCard.type}
            title={floatingCard.title}
            body={floatingCard.body}
            code={floatingCard.code}
            diagram={floatingCard.diagram}
            onDismiss={() => setFloatingCard(null)}
            onDeepen={() => {
              setChatOpen(true);
              sendChat(`Tell me more about ${floatingCard.title}`);
              setFloatingCard(null);
            }}
            deepenLabel="Go deeper"
          />
        </div>
      )}

      {/* Spotlight overlay */}
      {spotlightActive && (
        <JillaSpotlight
          steps={spotlightSteps}
          currentStep={spotlightStep}
          total={spotlightSteps.length}
          onNext={() => {
            if (spotlightStep < spotlightSteps.length - 1) {
              setSpotlightStep(prev => prev + 1);
            } else {
              setSpotlightActive(false);
              setSpotlightStep(0);
            }
          }}
          onDismiss={() => { setSpotlightActive(false); setSpotlightStep(0); }}
        />
      )}

      {/* Chat popup (slides up from FAB) */}
      {chatOpen && (
        <div style={{ position: "fixed", bottom: 76, right: 20, zIndex: 9100, width: 360,
          background: "#fff", borderRadius: 16, boxShadow: "0 12px 40px rgba(0,0,0,0.2)",
          border: "1px solid var(--gc-border)", overflow: "hidden",
          animation: "cardAppear 0.25s ease" }}>
          <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--gc-border)",
            display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 18 }}>🤖</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700 }}>Ask Jilla</div>
              <div style={{ fontSize: 10, color: "var(--gc-muted)" }}>AI Instructor · sees your sim state</div>
            </div>
            <button onClick={() => setChatOpen(false)} style={{ marginLeft: "auto", background: "none",
              border: "none", color: "var(--gc-muted)", cursor: "pointer" }}>
              <i className="fa fa-times" />
            </button>
          </div>

          {chatResponse && (
            <div style={{ padding: "12px 14px", maxHeight: 200, overflowY: "auto", fontSize: 12.5,
              lineHeight: 1.7, color: "var(--gc-text2)" }}>
              {chatResponse.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) => {
                if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
                if (part.startsWith("`") && part.endsWith("`")) return <code key={i} style={{ background: "var(--gc-soft)", padding: "1px 4px", borderRadius: 3, fontFamily: "var(--mono)", fontSize: 11 }}>{part.slice(1, -1)}</code>;
                return <span key={i}>{part}</span>;
              })}
            </div>
          )}

          {/* Quick actions */}
          <div style={{ padding: "6px 14px", display: "flex", gap: 4, flexWrap: "wrap" }}>
            {["What should I do?", "Explain current phase", "I'm stuck"].map(q => (
              <button key={q} onClick={() => sendChat(q)} disabled={chatLoading}
                style={{ fontSize: 10, padding: "4px 10px", borderRadius: 16, background: "var(--gc-soft)",
                  border: "1px solid var(--gc-border)", color: "var(--gc-primary)", cursor: "pointer" }}>
                {q}
              </button>
            ))}
          </div>

          <form onSubmit={e => { e.preventDefault(); sendChat(chatInput); }}
            style={{ display: "flex", gap: 6, padding: "8px 14px", borderTop: "1px solid var(--gc-border)" }}>
            <input value={chatInput} onChange={e => setChatInput(e.target.value)} disabled={chatLoading}
              placeholder="Ask anything..."
              style={{ flex: 1, padding: "8px 12px", borderRadius: 20, border: "1px solid var(--gc-border)",
                fontSize: 12, background: "var(--gc-soft)", color: "var(--gc-text)", outline: "none" }} />
            <button type="submit" disabled={chatLoading || !chatInput.trim()}
              style={{ width: 32, height: 32, borderRadius: "50%", border: "none",
                background: chatInput.trim() ? "var(--gc-primary)" : "var(--gc-soft)",
                color: chatInput.trim() ? "#fff" : "var(--gc-muted)", cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12 }}>
              <i className="fa fa-paper-plane" />
            </button>
          </form>
        </div>
      )}

      {/* FAB — Jilla presence button */}
      {showFab && (
        <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 9000,
          display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>

          {/* Tour button */}
          {!spotlightActive && sim?.guide?.progress?.done === 0 && (
            <button onClick={() => setSpotlightActive(true)}
              style={{ padding: "6px 14px", borderRadius: 20, background: "#fff",
                border: "1px solid var(--gc-border)", boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                fontSize: 11, fontWeight: 600, color: "var(--gc-primary)", cursor: "pointer",
                animation: "cardAppear 0.3s ease", display: "flex", alignItems: "center", gap: 6 }}>
              <i className="fa fa-map" /> Take the tour
            </button>
          )}

          {/* Main FAB */}
          <button onClick={() => setChatOpen(prev => !prev)}
            style={{ width: 52, height: 52, borderRadius: "50%", border: "none",
              background: chatOpen ? "var(--gc-text)" : "var(--gc-primary)",
              color: "#fff", cursor: "pointer", fontSize: 22,
              boxShadow: "0 6px 20px rgba(73,2,162,0.35)",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s",
              animation: !chatOpen && !floatingCard ? "fabPulse 3s ease infinite" : "none",
            }}>
            {chatOpen ? <i className="fa fa-times" style={{ fontSize: 16 }} /> : "🤖"}
          </button>
        </div>
      )}
    </>
  );
}
