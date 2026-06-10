import { useState } from "react";
import TopologyMap from "./TopologyMap";
import ToolWorkspace from "./ToolWorkspace";
import { fmtUSD, STATE_COLOR, STATE_LABEL } from "./shared";

/* BLUE — "I act." Network health dashboard + action center (containment/eradication/recovery) +
   live business impact. Blue acts; SOC detects. */
export default function BlueWorkspace({ sim, canPlay, runTool }:
  { sim: any; canPlay: boolean; runTool: (id: string, p?: Record<string, string>) => void }) {
  const [tool, setTool] = useState<any>(null);
  const blue = sim.teams.blue;
  const worm = sim.worm;
  const counts = sim.topology.counts;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0, padding: 12, gap: 12 }}>
      {/* health dashboard */}
      <div className="ws-card">
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center" }}>
          {["healthy", "vulnerable", "infected", "impacted", "contained", "dormant", "recovered"].map((s) => (
            <div key={s} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 17, fontWeight: 800, color: STATE_COLOR[s] }}>
                {counts[s] || 0}{s === "infected" ? `+${worm.extra_infected || 0}` : s === "impacted" ? `+${worm.extra_impacted || 0}` : ""}
              </div>
              <div style={{ fontSize: 9, color: "#8aa0c2", textTransform: "uppercase" }}>{STATE_LABEL[s]}</div>
            </div>
          ))}
          <div style={{ marginLeft: "auto", textAlign: "center" }}>
            <div style={{ fontSize: 17, fontWeight: 800, color: worm.r_value > 1 ? "#f59e0b" : "#22c55e" }}>R {worm.r_value}</div>
            <div style={{ fontSize: 9, color: "#8aa0c2" }}>reproduction</div>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, flex: 1, minHeight: 0 }}>
        {/* action center + business impact */}
        <div style={{ width: 280, display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", flexShrink: 0 }}>
          <div className="ws-card">
            <h3>Action center · score {blue.score}</h3>
            {!canPlay && <div style={{ fontSize: 11, color: "#8aa0c2", marginBottom: 8 }}><i className="fa fa-eye" /> spectating — claim Blue to act</div>}
            <div style={{ display: "grid", gap: 7 }}>
              {blue.tools.map((t: any) => (
                <button key={t.id} className="tool-btn" disabled={!canPlay || !t.available} onClick={() => setTool(t)}
                  title={t.available ? t.summary : t.reason}>
                  <span className="t-name"><i className="fa fa-shield-halved" style={{ marginRight: 6, color: "#3b82f6" }} />{t.name}</span>
                  <span className="t-sum">{t.available ? t.summary : `🔒 ${t.reason}`}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="ws-card">
            <h3>Business impact</h3>
            <div style={{ fontSize: 26, fontWeight: 800, color: "#f59e0b" }}>{fmtUSD(worm.financial_loss)}</div>
            <div style={{ fontSize: 11, color: "#8aa0c2", marginBottom: 8 }}>estimated loss</div>
            <div style={{ fontSize: 12, color: "#cbd5e1" }}>{worm.impacted} hosts impacted · backups {worm.backups_safe ? "safe" : "lost"}</div>
            <div style={{ fontSize: 12, marginTop: 4, color: worm.outcome_band === "Contained" ? "#22c55e" : worm.outcome_band === "Degraded" ? "#f59e0b" : "#ef4444" }}>
              Trajectory: <b>{worm.outcome_band}</b>
            </div>
          </div>
        </div>
        {/* topology (read-only, so Blue sees the spread) */}
        <div style={{ flex: 1, minWidth: 0 }}><TopologyMap sim={sim} /></div>
      </div>
      {tool && <ToolWorkspace tool={tool} sim={sim} onRun={runTool} onClose={() => setTool(null)} />}
    </div>
  );
}
