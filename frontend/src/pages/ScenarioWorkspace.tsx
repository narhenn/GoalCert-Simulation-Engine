import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useLiveSocket } from "../hooks/useLiveSocket";
import RedWorkspace from "../components/sim/RedWorkspace";
import SocWorkspace from "../components/sim/SocWorkspace";
import BlueWorkspace from "../components/sim/BlueWorkspace";
import VictimDesktop from "../components/sim/VictimDesktop";
import AarReport from "../components/AarReport";
import GuidePanel from "../components/sim/GuidePanel";
import ResultOverlayModal from "../components/sim/ResultOverlay";
import { TEAM_META } from "../components/sim/shared";
import "../components/sim/sim.css";

type Sess = { session_id: string; player_id: string; role: string | null };

export default function ScenarioWorkspace() {
  const { scenarioId = "" } = useParams();
  const nav = useNavigate();
  const key = `gc_guided_${scenarioId}`;
  const [sess, setSess] = useState<Sess | null>(() => {
    try { const r = localStorage.getItem(key); return r ? JSON.parse(r) : null; } catch { return null; }
  });
  const [meta, setMeta] = useState<any>(null);
  const [lab, setLab] = useState<any>(null);
  const [tab, setTab] = useState<string>("red");

  useEffect(() => { api.guidedScenario(scenarioId).then(setMeta).catch(() => {}); }, [scenarioId]);
  useEffect(() => { api.labStatus().then(setLab).catch(() => {}); }, []);

  const live = useLiveSocket(sess?.session_id ?? null, sess?.player_id ?? null);
  const claimed = useRef(false);
  useEffect(() => {
    if (live.state.connected && sess?.role && !claimed.current) { claimed.current = true; live.claimRole(sess.role); }
  }, [live.state.connected, sess, live]);

  // A stored session can be stale (backend restarted, or an old session id) → "session not found".
  // Recover by clearing it and returning to the landing screen so a fresh session is created.
  useEffect(() => {
    const e = live.state.error || "";
    if (e.includes("session not found") || e.includes("re-join") || e.includes("unknown player")) {
      localStorage.removeItem(key);
      claimed.current = false;
      setSess(null);
      live.clearError();
    }
  }, [live.state.error]);  // eslint-disable-line react-hooks/exhaustive-deps

  // default the active tab to your seat once chosen
  useEffect(() => { if (sess?.role) setTab(sess.role); }, [sess?.role]);

  // Guide: surface the latest tool result (with a teaching consequence) as an overlay.
  // These hooks MUST stay above the early returns below, or the hook order changes between
  // renders once the snapshot arrives (React: "Rendered more hooks than during the previous render").
  const [lastResult, setLastResult] = useState<any>(null);
  const seenGuide = useRef(-1);
  const simEvents: any[] = (live.state.snapshot as any)?.sim?.events ?? [];
  useEffect(() => {
    const fresh = simEvents.filter((e: any) => e.seq > seenGuide.current && e.notify && e.data?.consequence);
    if (fresh.length) {
      seenGuide.current = Math.max(seenGuide.current, ...simEvents.map((e: any) => e.seq));
      const last = fresh[fresh.length - 1];
      setLastResult({
        tool_name: last.title, tool_id: last.data?.tool_id || "", team: last.role,
        consequence: last.data?.consequence || "", next_hint: last.data?.next_hint || "",
        teaching_note: last.data?.teaching_note || "", command: last.data?.command || "",
        outcome: last.message,
      });
    }
  }, [simEvents]);  // eslint-disable-line react-hooks/exhaustive-deps

  function launch(name: string, role: string) {
    api.createGuidedSession({ host_name: name || "operator", scenario_id: scenarioId }).then((r) => {
      const s = { session_id: r.session_id, player_id: r.player_id, role };
      localStorage.setItem(key, JSON.stringify(s)); claimed.current = false; setSess(s);
    });
  }
  function pickRole(role: string) {
    if (!sess) return;
    const s = { ...sess, role }; localStorage.setItem(key, JSON.stringify(s)); claimed.current = false; setSess(s);
  }
  function quit() { localStorage.removeItem(key); setSess(null); claimed.current = false; nav("/live"); }

  if (!sess) return <Landing meta={meta} onLaunch={launch} onBack={() => nav("/live")} />;
  if (!sess.role) return <RolePick meta={meta} connected={live.state.connected} onPick={pickRole} onBack={quit} />;

  const snap: any = live.state.snapshot;
  const sim = snap?.sim;
  if (!sim) {
    return <div style={{ padding: 40, color: "#94a3b8" }}>
      <i className="fa fa-circle-notch fa-spin" /> Spinning up the range…
      {live.state.error && <div style={{ color: "#ef4444", marginTop: 8 }}>{live.state.error}</div>}
    </div>;
  }

  const myRole = sess.role;
  const canPlay = (t: string) => t === myRole;
  const events = sim.events || [];
  const termUrl = lab?.terminal_url;

  return (
    <div className="ws-root">
      <ResultOverlayModal result={lastResult} onClose={() => setLastResult(null)} />
      {/* top bar */}
      <div className="ws-topbar">
        <button className="btn" onClick={quit}><i className="fa fa-arrow-left" /></button>
        <b>{meta?.name ?? "Operation Tripwire"}</b>
        <div style={{ display: "flex", gap: 4 }}>
          {["red", "soc", "blue", "victim"].map((t) => {
            const m = TEAM_META[t];
            return (
              <button key={t} className={"ws-tab" + (tab === t ? " active" : "")} style={{ color: tab === t ? m.color : undefined }}
                onClick={() => setTab(t)}>
                <i className={`fa ${m.icon}`} /> {m.label}
                {t === myRole && <span className="seat" style={{ color: m.color }}>YOU</span>}
              </button>
            );
          })}
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 12, alignItems: "center", fontSize: 12 }}>
          <span style={{ color: "#8aa0c2" }}>tick {sim.tick}</span>
          <OutcomeBadge band={sim.worm.outcome_band} finished={sim.finished} outcome={sim.outcome} />
          {termUrl
            ? <a className="btn" href={termUrl} target="_blank" rel="noreferrer" style={{ color: "#22d3ee" }}><i className="fa fa-terminal" /> Kali</a>
            : <span style={{ color: "#64748b", fontSize: 11 }}><i className="fa fa-terminal" /> Kali offline</span>}
          <button className={"btn" + (sim.auto_enabled ? " btn-primary" : "")} title="When ON, empty seats auto-play (telegraphed). OFF = learn at your own pace."
            onClick={() => live.setSimAuto(!sim.auto_enabled)}>
            <i className={`fa ${sim.auto_enabled ? "fa-robot" : "fa-user"}`} /> Auto-defense {sim.auto_enabled ? "ON" : "OFF"}
          </button>
          {!sim.finished && <button className="btn" onClick={live.conclude}><i className="fa fa-flag-checkered" /> Conclude</button>}
        </div>
      </div>

      {/* telegraph reaction-window banners (auto seats other than yours) */}
      {Object.entries(sim.pending_intents || {}).filter(([r]) => r !== myRole).map(([r, i]: any) => (
        <div key={r} className="intent-banner">
          <i className="fa fa-bolt" /> {TEAM_META[r]?.label} will <b>{i.label}</b> in ~{Math.max(0, i.ticks_left) * 3}s — act first to change the outcome.
        </div>
      ))}

      <div className="ws-body" style={{ display: "flex" }}>
        <GuidePanel sim={sim} myRole={myRole} scenarioId={scenarioId} />
        <div style={{ flex: 1, minWidth: 0, overflow: "auto" }}>
          {tab === "red" && <RedWorkspace sim={sim} canPlay={canPlay("red")} runTool={live.runTool} events={events} termUrl={termUrl} error={live.state.error} />}
          {tab === "soc" && <SocWorkspace sim={sim} canPlay={canPlay("soc")} runTool={live.runTool} events={events} />}
          {tab === "blue" && <BlueWorkspace sim={sim} canPlay={canPlay("blue")} runTool={live.runTool} events={events} error={live.state.error} />}
          {tab === "victim" && <VictimDesktop sim={sim} />}
        </div>
      </div>

      {sim.finished && <FinishOverlay sim={sim} report={snap.report} onQuit={quit} />}
    </div>
  );
}

/* ---------- landing / role pick ---------- */
function Landing({ meta, onLaunch, onBack }: { meta: any; onLaunch: (n: string, r: string) => void; onBack: () => void }) {
  const [name, setName] = useState(localStorage.getItem("gc_live_name") || "");
  const [role, setRole] = useState("red");
  return (
    <div style={{ maxWidth: 720, margin: "48px auto", padding: 24, color: "#e2e8f0" }}>
      <button className="btn" onClick={onBack} style={{ marginBottom: 16 }}><i className="fa fa-arrow-left" /> Live</button>
      <div style={{ border: "1px solid #334155", borderRadius: 12, padding: 20, background: "#0a1120", marginBottom: 18 }}>
        <div style={{ fontSize: 11, letterSpacing: 1, color: "#f59e0b" }}>W1 INCIDENT OPERATOR CONSOLE</div>
        <h1 style={{ margin: "6px 0" }}>{meta?.name ?? "Operation Tripwire"}</h1>
        <div style={{ color: "#8aa0c2", fontSize: 13, lineHeight: 1.7 }}>
          Patient Zero: <b style={{ color: "#fde047" }}>FIN-WS-014</b> · State: <b style={{ color: "#ef4444" }}>Infected</b><br />
          {meta?.summary}
        </div>
      </div>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Pick your seat <span style={{ color: "#8aa0c2", fontWeight: 400 }}>— take your time; the other seats stay idle until you turn on Auto-defense (top bar) or teammates join</span></div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        {["red", "blue", "soc"].map((k) => {
          const m = TEAM_META[k];
          return (
            <div key={k} onClick={() => setRole(k)} style={{ cursor: "pointer", border: `2px solid ${role === k ? m.color : "#33415544"}`,
              borderRadius: 12, padding: 14, background: role === k ? `${m.color}14` : "transparent" }}>
              <div style={{ color: m.color, fontWeight: 700 }}><i className={`fa ${m.icon}`} /> {m.label}</div>
              <div style={{ fontSize: 12, color: "#8aa0c2", marginTop: 4 }}>{m.blurb}</div>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
        <input className="form-input" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} style={{ flex: 1 }} />
        <button className="btn btn-primary" onClick={() => onLaunch(name, role)}><i className="fa fa-play" /> Enter the range</button>
      </div>
    </div>
  );
}

function RolePick({ meta, connected, onPick, onBack }: { meta: any; connected: boolean; onPick: (r: string) => void; onBack: () => void }) {
  return (
    <div style={{ maxWidth: 640, margin: "60px auto", padding: 24, textAlign: "center", color: "#e2e8f0" }}>
      <h1>Join: {meta?.name ?? "Scenario"}</h1>
      <div style={{ color: "#8aa0c2", marginBottom: 18 }}>Pick a free seat — <span style={{ color: connected ? "#22c55e" : "#f59e0b" }}>{connected ? "connected" : "connecting…"}</span></div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        {["red", "blue", "soc"].map((k) => {
          const m = TEAM_META[k];
          return (
            <div key={k} onClick={() => onPick(k)} style={{ cursor: "pointer", border: `2px solid ${m.color}55`, borderRadius: 12, padding: 16 }}>
              <div style={{ color: m.color, fontWeight: 700 }}><i className={`fa ${m.icon}`} /> {m.label}</div>
              <div style={{ fontSize: 12, color: "#8aa0c2", marginTop: 4 }}>{m.blurb}</div>
            </div>
          );
        })}
      </div>
      <button className="btn" onClick={onBack} style={{ marginTop: 18 }}><i className="fa fa-arrow-left" /> Leave</button>
    </div>
  );
}

function OutcomeBadge({ band, finished, outcome }: { band: string; finished: boolean; outcome: string | null }) {
  const text = finished ? outcome : band;
  const c = text === "Contained" ? "#22c55e" : text === "Degraded" ? "#f59e0b" : "#ef4444";
  return <span style={{ color: c, fontWeight: 700, border: `1px solid ${c}66`, borderRadius: 6, padding: "1px 8px" }}>{text}</span>;
}

/* ---------- finish overlay ---------- */
function FinishOverlay({ sim, report, onQuit }: { sim: any; report: any; onQuit: () => void }) {
  const [showReport, setShowReport] = useState(false);
  const c = sim.outcome === "Contained" ? "#22c55e" : sim.outcome === "Degraded" ? "#f59e0b" : "#ef4444";

  if (showReport && report) {
    return (
      <div style={{ position: "fixed", inset: 0, zIndex: 80, background: "#070b14", overflowY: "auto" }}>
        <AarReport report={report} onClose={() => setShowReport(false)} />
        <div className="no-print" style={{ textAlign: "center", paddingBottom: 28 }}>
          <button className="btn btn-primary" onClick={onQuit}><i className="fa fa-rotate-right" /> Back to scenarios</button>
        </div>
      </div>
    );
  }
  return (
    <div style={{ position: "fixed", inset: 0, background: "#000a", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="ws-card" style={{ width: 460, textAlign: "center", borderColor: c }}>
        <div style={{ fontSize: 12, color: "#8aa0c2" }}>Scenario complete</div>
        <div style={{ fontSize: 30, fontWeight: 800, color: c, margin: "6px 0" }}>{sim.outcome}</div>
        <div style={{ fontSize: 13, color: "#cbd5e1", marginBottom: 12 }}>
          {sim.worm.infected} infected · {sim.worm.impacted} impacted · ${(sim.worm.financial_loss / 1000).toFixed(0)}k loss
        </div>
        {report && <div style={{ display: "flex", justifyContent: "center", gap: 20, fontSize: 13, color: "#8aa0c2", marginBottom: 14 }}>
          {Object.entries(report.teams || {}).map(([r, t]: any) => <span key={r}>{r.toUpperCase()} {t.score}</span>)}
        </div>}
        <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
          {report && <button className="btn btn-primary" onClick={() => setShowReport(true)}><i className="fa fa-file-lines" /> View full report</button>}
          <button className="btn" onClick={onQuit}><i className="fa fa-rotate-right" /> Back to scenarios</button>
        </div>
        {report && <div style={{ fontSize: 11, color: "#8aa0c2", marginTop: 8 }}><i className="fa fa-floppy-disk" /> Saved to Reports &amp; AAR (open it there to view or print as PDF).</div>}
      </div>
    </div>
  );
}
