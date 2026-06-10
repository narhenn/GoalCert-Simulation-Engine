import { useMemo, useState } from "react";
import { hostsForFilter, SimHost } from "./shared";

/* Generic tool workspace — renders a tool's schema as a form, previews the command, and RUNs it.
   Real tools stream output to the terminal; sim/act tools mutate the topology. */
export default function ToolWorkspace({ tool, sim, onRun, onClose }:
  { tool: any; sim: any; onRun: (toolId: string, params: Record<string, string>) => void; onClose: () => void }) {
  const hosts: SimHost[] = sim.topology.hosts;
  const alerts: any[] = sim.alerts || [];
  const [params, setParams] = useState<Record<string, string>>(() => {
    const p: Record<string, string> = {};
    for (const f of tool.schema || []) if (f.default) p[f.key] = f.default;
    return p;
  });
  const set = (k: string, v: string) => setParams((p) => ({ ...p, [k]: v }));

  const cmdPreview = useMemo(() => {
    if (tool.kind === "real" && tool.fire_action) return `[real] ${tool.name} → live-fire`;
    return tool.command_hint || "";
  }, [tool]);

  const run = () => { onRun(tool.id, params); onClose(); };
  const accent = tool.team === "red" ? "#ef4444" : tool.team === "blue" ? "#3b82f6" : "#a855f7";

  return (
    <div style={{ position: "fixed", inset: 0, background: "#0008", zIndex: 70, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={onClose}>
      <div className="ws-card" style={{ width: 480, maxWidth: "92vw", borderColor: accent }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ color: accent, fontWeight: 700, fontSize: 15 }}>{tool.name}</span>
          {tool.kind === "real" && <span style={{ fontSize: 9, color: "#22d3ee", border: "1px solid #22d3ee66", borderRadius: 4, padding: "0 5px" }}>REAL TOOL</span>}
          <span style={{ marginLeft: "auto", fontSize: 10, color: "#8aa0c2" }}>{tool.stage}</span>
          <button className="btn" style={{ padding: "1px 7px" }} onClick={onClose}><i className="fa fa-xmark" /></button>
        </div>
        <div style={{ fontSize: 12, color: "#cbd5e1", lineHeight: 1.5, display: "grid", gap: 3, marginBottom: 12 }}>
          <div><b style={{ color: "#93a4bd" }}>Does:</b> {tool.does}</div>
          <div><b style={{ color: "#93a4bd" }}>How:</b> {tool.how}</div>
          <div><b style={{ color: "#93a4bd" }}>Outcome:</b> {tool.outcome}</div>
        </div>

        {(tool.schema || []).map((f: any) => (
          <div key={f.key} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11, color: "#93a4bd", marginBottom: 4 }}>{f.label}</div>
            {f.type === "select" && (
              <select className="form-select" value={params[f.key] ?? ""} onChange={(e) => set(f.key, e.target.value)} style={{ width: "100%" }}>
                {f.options.map((o: [string, string]) => <option key={o[0]} value={o[0]}>{o[1]}</option>)}
              </select>
            )}
            {f.type === "host" && (
              <select className="form-select" value={params[f.key] ?? ""} onChange={(e) => set(f.key, e.target.value)} style={{ width: "100%" }}>
                <option value="">select host…</option>
                {hostsForFilter(hosts, f.filter).map((h) => <option key={h.id} value={h.id}>{h.name} ({h.vlan})</option>)}
              </select>
            )}
            {f.type === "hosts" && (
              <div style={{ display: "grid", gap: 4, maxHeight: 160, overflowY: "auto", border: "1px solid #1e293b", borderRadius: 6, padding: 6 }}>
                {hostsForFilter(hosts, f.filter).map((h) => {
                  const sel = (params[f.key] || "").split(",").filter(Boolean);
                  const on = sel.includes(h.id);
                  return (
                    <label key={h.id} style={{ fontSize: 12, display: "flex", gap: 6, alignItems: "center" }}>
                      <input type="checkbox" checked={on} onChange={() => {
                        const next = on ? sel.filter((x) => x !== h.id) : [...sel, h.id];
                        set(f.key, next.join(","));
                      }} /> {h.name} <span style={{ color: "#64748b" }}>({h.vlan})</span>
                    </label>
                  );
                })}
                <button className="btn btn-ghost" style={{ fontSize: 10 }}
                  onClick={() => set(f.key, hostsForFilter(hosts, f.filter).map((h) => h.id).join(","))}>select all</button>
              </div>
            )}
            {f.type === "alert" && (
              <select className="form-select" value={params[f.key] ?? ""} onChange={(e) => set(f.key, e.target.value)} style={{ width: "100%" }}>
                <option value="">select alert…</option>
                {alerts.filter((a) => a.status === (f.filter === "new" ? "new" : "triaged"))
                  .map((a) => <option key={a.id} value={a.id}>{a.label}{a.host_name ? ` · ${a.host_name}` : ""}</option>)}
              </select>
            )}
            {f.type === "text" && (
              <input className="form-input" value={params[f.key] ?? ""} onChange={(e) => set(f.key, e.target.value)} style={{ width: "100%" }} />
            )}
          </div>
        ))}

        {cmdPreview && (
          <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 11.5, color: "#22d3ee", background: "#05080f",
            border: "1px solid #1e293b", borderRadius: 6, padding: "6px 8px", marginBottom: 12 }}>$ {cmdPreview}</div>
        )}
        <button className="btn btn-primary" style={{ width: "100%", background: accent, borderColor: accent }} onClick={run}>
          <i className={`fa ${tool.kind === "real" ? "fa-terminal" : tool.team === "blue" ? "fa-shield" : "fa-bolt"}`} /> RUN — {tool.name}
        </button>
      </div>
    </div>
  );
}
