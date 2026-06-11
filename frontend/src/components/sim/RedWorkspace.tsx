import { useState } from "react";
import TopologyMap from "./TopologyMap";
import Terminal, { StagedCmd } from "./Terminal";
import ToolWorkspace from "./ToolWorkspace";
import { toolCommand } from "./shared";

/* RED — "I am patient zero, watching the infection spread." Mission rail + live topology + tool
   palette (Kali tools) + the interactive terminal dock. Clicking a tool STAGES its real command;
   the operator then types it in the terminal to fire it — a hands-on-keyboard "real hack" loop. */
export default function RedWorkspace({ sim, canPlay, runTool, events, termUrl, error }:
  { sim: any; canPlay: boolean; runTool: (id: string, p?: Record<string, string>) => void;
    events: any[]; termUrl?: string | null; error?: string | null }) {
  const [tool, setTool] = useState<any>(null);
  const [pending, setPending] = useState<StagedCmd | null>(null);
  const red = sim.teams.red;
  const worm = sim.worm;
  const pz = sim.topology.hosts.find((h: any) => h.patient_zero);

  const hostName = (id?: string) => sim.topology.hosts.find((h: any) => h.id === id)?.name;
  const stage = (toolId: string, params: Record<string, string>, command: string, label: string) => {
    const hid = params.host || (params.hosts || "").split(",")[0];
    setPending({ toolId, params, command, label, targetLabel: hostName(hid) });
  };
  const onToolClick = (t: any) => {
    if (!canPlay || !t.available) return;
    if (t.schema && t.schema.length) setTool(t);                  // pick targets first, then stage
    else stage(t.id, {}, toolCommand(t), t.name);                 // no params → stage right away
  };
  const execute = (toolId: string, params: Record<string, string>) => { runTool(toolId, params); setPending(null); };

  const objectives = [
    { label: "Establish a foothold", met: sim.topology.hosts.some((h: any) => ["exploited", "infected", "propagating"].includes(h.state)) },
    { label: "Discover the network", met: sim.topology.hosts.some((h: any) => h.revealed && !h.patient_zero) },
    { label: "Move laterally / spread", met: worm.propagating || worm.infected > 1 },
    { label: "Disable recovery", met: !worm.backups_safe || sim.topology.hosts.some((h: any) => (h.flags || []).includes("recovery_disabled")) },
    { label: "Encrypt for impact", met: worm.impacted > 0 },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div style={{ display: "flex", gap: 12, flex: 1, minHeight: 0, padding: 12 }}>
        {/* left rail */}
        <div style={{ width: 270, display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", flexShrink: 0 }}>
          <div className="ws-card">
            <h3>Attacker console</h3>
            <div style={{ fontSize: 12, lineHeight: 1.7 }}>
              <div>Patient zero: <b style={{ color: "#fde047" }}>{pz?.name ?? "—"}</b></div>
              <div>State: <b style={{ color: "#ef4444" }}>{pz ? pz.state.charAt(0).toUpperCase() + pz.state.slice(1) : "—"}</b></div>
              <div style={{ color: "#8aa0c2", marginTop: 6 }}>Mission: progress the kill chain and detonate before the defenders stop you.</div>
            </div>
          </div>
          <div className="ws-card">
            <h3>Objectives</h3>
            {objectives.map((o) => (
              <div key={o.label} style={{ display: "flex", gap: 8, fontSize: 12.5, marginBottom: 6 }}>
                <i className={`fa ${o.met ? "fa-circle-check" : "fa-circle"}`} style={{ color: o.met ? "#22c55e" : "#475569" }} />
                <span style={{ color: o.met ? "#e2e8f0" : "#8aa0c2" }}>{o.label}</span>
              </div>
            ))}
            <div style={{ marginTop: 8, fontSize: 12, color: "#8aa0c2" }}>Red score: <b style={{ color: "#ef4444" }}>{red.score}</b></div>
          </div>
          <div className="ws-card">
            <h3>Kali tools</h3>
            {!canPlay && <div style={{ fontSize: 11, color: "#8aa0c2", marginBottom: 8 }}><i className="fa fa-eye" /> spectating — claim Red to act</div>}
            {canPlay && <div style={{ fontSize: 10.5, color: "#8aa0c2", marginBottom: 8 }}><i className="fa fa-keyboard" /> click a tool to stage its command, then type it in the terminal below.</div>}
            <div style={{ display: "grid", gap: 7 }}>
              {red.tools.map((t: any) => {
                const staged = pending?.toolId === t.id;
                return (
                  <button key={t.id} className="tool-btn" disabled={!canPlay || !t.available}
                    style={staged ? { borderColor: "#22d3ee", boxShadow: "0 0 0 1px #22d3ee55" } : undefined}
                    onClick={() => onToolClick(t)} title={t.available ? t.summary : t.reason}>
                    <span className="t-name">
                      <i className={`fa ${t.kind === "real" ? "fa-terminal" : "fa-bolt"}`} style={{ marginRight: 6, color: t.kind === "real" ? "#22d3ee" : "#ef4444" }} />
                      {t.name} {t.kind === "real" && <span style={{ fontSize: 8, color: "#22d3ee" }}>REAL</span>}
                      {staged && <span style={{ fontSize: 8, color: "#22d3ee", marginLeft: 4 }}>STAGED ↓</span>}
                    </span>
                    <span className="t-sum">{t.available ? t.summary : `🔒 ${t.reason}`}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        {/* center: topology */}
        <div style={{ flex: 1, minWidth: 0 }}><TopologyMap sim={sim} /></div>
      </div>
      <Terminal events={events} termUrl={termUrl} pending={pending} canPlay={canPlay} onExecute={execute} error={error} />
      {tool && <ToolWorkspace tool={tool} sim={sim} mode="stage" onRun={runTool}
        onStage={(id, p, cmd) => { stage(id, p, cmd, tool.name); setTool(null); }} onClose={() => setTool(null)} />}
    </div>
  );
}
