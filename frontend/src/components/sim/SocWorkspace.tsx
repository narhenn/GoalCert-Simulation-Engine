import { useState } from "react";
import { SEV_COLOR, fmtT } from "./shared";

/* SOC — "I am an analyst." Alert feed (triage→escalate) + investigation lenses over the telemetry
   funnel (Zeek/Suricata/Splunk/Sysmon/Threat-Hunt) + a SIEM timeline. */
const LENS: Record<string, { tele: string[]; label: string }> = {
  zeek: { tele: ["scan", "spread"], label: "Zeek — network flow" },
  suricata: { tele: ["exploit_signature"], label: "Suricata — IDS" },
  splunk: { tele: ["scan", "smb_negotiation", "spread"], label: "Splunk — SIEM search" },
  sysmon: { tele: ["service_create", "shadow_delete", "mass_rename", "file_write"], label: "Sysmon — host telemetry" },
};

export default function SocWorkspace({ sim, canPlay, runTool, events }:
  { sim: any; canPlay: boolean; runTool: (id: string, p?: Record<string, string>) => void; events: any[] }) {
  const [lens, setLens] = useState("splunk");
  const soc = sim.teams.soc;
  const alerts: any[] = sim.alerts || [];
  const telemetry = events.filter((e) => e.kind === "g_telemetry" || e.kind === "alert");

  const act = (toolId: string, params?: Record<string, string>) => canPlay && runTool(toolId, params);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 12, height: "100%", padding: 12, minHeight: 0 }}>
      {/* alert feed */}
      <div className="ws-card" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
        <h3>Alert feed · SOC score {soc.score}</h3>
        {!canPlay && <div style={{ fontSize: 11, color: "#8aa0c2", marginBottom: 6 }}><i className="fa fa-eye" /> spectating</div>}
        <div style={{ flex: 1, overflowY: "auto", display: "grid", gap: 8 }}>
          {alerts.length === 0 && <div style={{ fontSize: 12, color: "#8aa0c2" }}>No alerts yet. The funnel starts quiet…</div>}
          {alerts.slice().reverse().map((a) => (
            <div key={a.id} style={{ border: "1px solid #1e293b", borderLeft: `3px solid ${SEV_COLOR[a.severity]}`, borderRadius: 6, padding: 8 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600 }}>{a.label}</div>
              <div style={{ fontSize: 10.5, color: "#8aa0c2" }}>
                {fmtT(a.t)} · {a.severity.toUpperCase()}{a.host_name ? ` · ${a.host_name}` : ""}{a.mitre ? ` · ${a.mitre}` : ""}
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                {a.status === "new" && <button className="btn" style={{ fontSize: 10, padding: "2px 8px" }} disabled={!canPlay}
                  onClick={() => act("soc_triage", { alert: a.id })}>Triage</button>}
                {a.status === "triaged" && <button className="btn btn-primary" style={{ fontSize: 10, padding: "2px 8px" }} disabled={!canPlay}
                  onClick={() => act("soc_escalate", { alert: a.id })}>Escalate to IR</button>}
                {a.status === "escalated" && <span style={{ fontSize: 10, color: "#22c55e" }}><i className="fa fa-flag" /> escalated</span>}
                {a.status !== "escalated" && <span style={{ fontSize: 10, color: "#8aa0c2", alignSelf: "center" }}>{a.status}</span>}
              </div>
            </div>
          ))}
        </div>
        <button className="btn btn-ghost" style={{ marginTop: 8, fontSize: 11 }} disabled={!canPlay}
          onClick={() => act("threat_hunt")}><i className="fa fa-crosshairs" /> Threat hunt (reveal hidden footholds)</button>
      </div>

      {/* investigation lenses + timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
        <div className="ws-card" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}>
            {Object.entries(LENS).map(([k, v]) => (
              <button key={k} className={"btn" + (lens === k ? " btn-primary" : "")} style={{ fontSize: 11 }}
                onClick={() => { setLens(k); act(k); }}>{v.label.split(" — ")[0]}</button>
            ))}
          </div>
          <div style={{ fontSize: 11, color: "#93a4bd", marginBottom: 6 }}>{LENS[lens].label}</div>
          <div style={{ flex: 1, overflowY: "auto", fontFamily: "ui-monospace, monospace", fontSize: 11.5 }}>
            {telemetry.filter((e) => e.kind === "alert" || LENS[lens].tele.includes(e.data?.telemetry))
              .slice().reverse().map((e, i) => (
                <div key={i} style={{ marginBottom: 3 }}>
                  <span style={{ color: "#475569" }}>[{fmtT(e.t)}] </span>
                  <span style={{ color: SEV_COLOR[e.severity] }}>{e.title}</span>
                  <span style={{ color: "#94a3b8" }}> — {e.message}</span>
                </div>
              ))}
          </div>
        </div>
        <div className="ws-card" style={{ maxHeight: 160, overflowY: "auto" }}>
          <h3>SIEM timeline</h3>
          {events.filter((e) => ["alert", "action", "response", "g_result"].includes(e.kind)).slice(-12).map((e, i) => (
            <div key={i} style={{ fontSize: 11.5, marginBottom: 3, color: "#cbd5e1" }}>
              <span style={{ color: "#475569" }}>{fmtT(e.t)}</span> · {e.title}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
