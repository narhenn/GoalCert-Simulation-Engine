import { useEffect, useRef, useState } from "react";
import { STATE_COLOR, STATE_LABEL, HOST_ICON, fmtUSD, SimHost } from "./shared";

/* Structured VLAN map — named host nodes coloured by state, R-value gauge, infection counter,
   strike-flash on state change + a scan ring on freshly-discovered hosts. Shared by every team view. */
export default function TopologyMap({ sim, onPick, compact }: { sim: any; onPick?: (h: SimHost) => void; compact?: boolean }) {
  const topo = sim.topology;
  const worm = sim.worm;
  const hosts: SimHost[] = topo.hosts;
  const prev = useRef<Record<string, string>>({});
  const [flash, setFlash] = useState<Record<string, number>>({});

  useEffect(() => {
    const changed: Record<string, number> = {};
    for (const h of hosts) {
      if (prev.current[h.id] && prev.current[h.id] !== h.state) changed[h.id] = Date.now();
      prev.current[h.id] = h.state;
    }
    if (Object.keys(changed).length) {
      setFlash((f) => ({ ...f, ...changed }));
      const t = setTimeout(() => setFlash((f) => {
        const n = { ...f }; for (const k of Object.keys(changed)) delete n[k]; return n;
      }), 800);
      return () => clearTimeout(t);
    }
  }, [hosts]);

  const band = worm.outcome_band;
  const bandColor = band === "Contained" ? "#22c55e" : band === "Degraded" ? "#f59e0b" : "#ef4444";

  return (
    <div className="ws-card" style={{ height: "100%", display: "flex", flexDirection: "column", minHeight: 0 }}>
      {/* worm control bar */}
      <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
        <Stat label="R-value" value={worm.r_value} color={worm.r_value > 1 ? "#f59e0b" : "#22c55e"} />
        <Stat label="Infected" value={worm.infected} color="#ef4444" />
        <Stat label="Impacted" value={worm.impacted} color="#fca5a5" />
        <Stat label={`of ${topo.total_hosts}`} value={`${Math.round(((worm.infected + worm.impacted) / topo.total_hosts) * 100)}%`} />
        <Stat label="Est. loss" value={fmtUSD(worm.financial_loss)} color="#f59e0b" />
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center", fontSize: 11 }}>
          {worm.propagating && <span style={{ color: "#ef4444" }}><i className="fa fa-radiation" /> SPREADING</span>}
          {worm.segmented && <span style={{ color: "#3b82f6" }}><i className="fa fa-network-wired" /> segmented</span>}
          {worm.kill_switch === "tripped" && <span style={{ color: "#94a3b8" }}><i className="fa fa-power-off" /> kill-switch</span>}
          {worm.smbv1_patched && <span style={{ color: "#22c55e" }}><i className="fa fa-shield" /> patched</span>}
          <span style={{ color: bandColor, fontWeight: 700, border: `1px solid ${bandColor}66`, borderRadius: 6, padding: "1px 8px" }}>{band}</span>
        </div>
      </div>

      <div className="topo" style={{ gridTemplateColumns: `repeat(${topo.vlans.length}, 1fr)`, flex: 1, minHeight: 0, overflowY: "auto" }}>
        {topo.vlans.map((v: any) => {
          const vh = hosts.filter((h) => h.vlan === v.id);
          return (
            <div key={v.id} className="topo-vlan">
              <h4>{v.name} · {vh.length}</h4>
              <div className="topo-grid">
                {vh.map((h) => {
                  const cls = "node" + (h.patient_zero ? " pz" : "")
                    + (flash[h.id] ? " strike" : "")
                    + (["infected", "propagating", "encrypting"].includes(h.state) ? " spreading" : "");
                  return (
                    <div key={h.id} className={cls} title={`${h.name} — ${STATE_LABEL[h.state]}${h.vulnerable ? " · SMBv1" : ""}`}
                      onClick={() => onPick?.(h)}>
                      <div className="dot" style={{ background: STATE_COLOR[h.state] || "#334155" }}>
                        {!h.revealed && h.state === "healthy" ? <i className="fa fa-question" style={{ opacity: .5 }} />
                          : <i className={`fa ${HOST_ICON[h.role] || "fa-desktop"}`} />}
                        {worm.propagating && h.state === "propagating" && <span className="scan-ring" />}
                        {h.flags.includes("persistent") && <i className="fa fa-anchor anchor" />}
                      </div>
                      {!compact && <div className="nm">{h.name}</div>}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* unnamed fleet + legend */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8, fontSize: 10.5, color: "#8aa0c2", flexWrap: "wrap", gap: 8 }}>
        <span>+ {topo.extra_hosts} more hosts in the fleet ({worm.extra_infected || 0} infected · {worm.extra_impacted || 0} impacted)</span>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {["healthy", "vulnerable", "exploited", "infected", "impacted", "contained", "dormant"].map((s) => (
            <span key={s} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 9, height: 9, borderRadius: 2, background: STATE_COLOR[s], display: "inline-block" }} />{STATE_LABEL[s]}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: any; color?: string }) {
  return (
    <div className="gauge" style={{ textAlign: "center" }}>
      <div style={{ fontSize: 18, fontWeight: 800, color: color || "#e2e8f0", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 9, color: "#8aa0c2", textTransform: "uppercase", letterSpacing: .5 }}>{label}</div>
    </div>
  );
}
