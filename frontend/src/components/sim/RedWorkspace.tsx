import { useState } from "react";
import TopologyMap from "./TopologyMap";
import Terminal from "./Terminal";
import ToolWorkspace from "./ToolWorkspace";

/* RED — "I am patient zero, watching the infection spread." Mission rail + live topology + tool
   palette (Kali tools) + the terminal dock. */
export default function RedWorkspace({ sim, canPlay, runTool, events, termUrl }:
  { sim: any; canPlay: boolean; runTool: (id: string, p?: Record<string, string>) => void; events: any[]; termUrl?: string | null }) {
  const [tool, setTool] = useState<any>(null);
  const red = sim.teams.red;
  const worm = sim.worm;

  const objectives = [
    { label: "Discover the network", met: sim.topology.hosts.some((h: any) => h.revealed && !h.patient_zero) },
    { label: "Identify SMBv1 targets", met: sim.topology.hosts.some((h: any) => h.state === "vulnerable") },
    { label: "Gain a second foothold", met: sim.topology.hosts.some((h: any) => ["exploited", "infected"].includes(h.state) && !h.patient_zero) },
    { label: "Unleash propagation", met: worm.propagating || worm.infected > 5 },
    { label: "Encrypt for impact", met: worm.impacted > 0 },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div style={{ display: "flex", gap: 12, flex: 1, minHeight: 0, padding: 12 }}>
        {/* left rail */}
        <div style={{ width: 270, display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", flexShrink: 0 }}>
          <div className="ws-card">
            <h3>Incident operator console</h3>
            <div style={{ fontSize: 12, lineHeight: 1.7 }}>
              <div>Patient zero: <b style={{ color: "#fde047" }}>FIN-WS-014</b></div>
              <div>State: <b style={{ color: "#ef4444" }}>Infected</b></div>
              <div style={{ color: "#8aa0c2", marginTop: 6 }}>Mission: maximize spread before the defenders stop you.</div>
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
            <div style={{ display: "grid", gap: 7 }}>
              {red.tools.map((t: any) => (
                <button key={t.id} className="tool-btn" disabled={!canPlay || !t.available}
                  onClick={() => setTool(t)} title={t.available ? t.summary : t.reason}>
                  <span className="t-name">
                    <i className={`fa ${t.kind === "real" ? "fa-terminal" : "fa-bolt"}`} style={{ marginRight: 6, color: t.kind === "real" ? "#22d3ee" : "#ef4444" }} />
                    {t.name} {t.kind === "real" && <span style={{ fontSize: 8, color: "#22d3ee" }}>REAL</span>}
                  </span>
                  <span className="t-sum">{t.available ? t.summary : `🔒 ${t.reason}`}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
        {/* center: topology */}
        <div style={{ flex: 1, minWidth: 0 }}><TopologyMap sim={sim} /></div>
      </div>
      <Terminal events={events} termUrl={termUrl} />
      {tool && <ToolWorkspace tool={tool} sim={sim} onRun={runTool} onClose={() => setTool(null)} />}
    </div>
  );
}
