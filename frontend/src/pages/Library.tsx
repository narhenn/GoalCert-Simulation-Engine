import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ScenarioSummary } from "../api/types";

const FILTERS = [
  { key: "all", label: "All" }, { key: "red", label: "Red Team" }, { key: "blue", label: "Blue Team" },
  { key: "purple", label: "Purple" }, { key: "soc", label: "SOC" }, { key: "ics", label: "ICS/OT" },
  { key: "cloud", label: "Cloud" }, { key: "edu", label: "Educational" },
];

// Educational simulation scenarios (interactive, SOC-console based)
const EDU_SCENARIOS = [
  {
    id: "scn-wannacry-w1", name: "Operation Tripwire",
    subtitle: "WannaCry Ransomware Worm",
    description: "A ransomware worm sweeps through a 250-host hospital network. Identify each attack stage, choose defensive responses, contain the outbreak.",
    icon: "fa-virus", color: "#C8413E", gradient: "linear-gradient(135deg, #C8413E, #E07A3E)",
    stages: 11, duration: 35, mitre: ["T1046", "T1210", "T1486", "T1490", "T1021.002"],
    difficulty: ["Guided", "Standard", "Pressure"],
    setting: "Mercy Regional Health Network", role: "SOC Analyst (Tier 2)",
  },
  {
    id: "scn-r5-phish2enc", name: "R5 — Phishing to Encrypt",
    subtitle: "Ransomware Campaign",
    description: "A targeted phishing email leads to macro execution, credential theft, lateral movement, and enterprise-wide ransomware. 4 roles: Red, Victim, SOC, Blue.",
    icon: "fa-envelope-open-text", color: "#E07A3E", gradient: "linear-gradient(135deg, #E07A3E, #C8413E)",
    stages: 10, duration: 45, mitre: ["T1566.001", "T1204.002", "T1053.005", "T1003.001", "T1486"],
    difficulty: ["Guided", "Standard", "Pressure"],
    setting: "MediumCorp Financial Services", role: "SOC Analyst / Incident Responder",
  },
  {
    id: "scn-c5-edr-outage", name: "C5 — EDR Outage Exploitation",
    subtitle: "Attacking During Blindness",
    description: "Your EDR vendor pushes a bad update. 80% of endpoint visibility goes dark. An attacker piggybacks on the outage — password spray, lateral movement, double extortion.",
    icon: "fa-eye-slash", color: "#5B7FB0", gradient: "linear-gradient(135deg, #5B7FB0, #c084fc)",
    stages: 13, duration: 50, mitre: ["T1110.003", "T1133", "T1003.001", "T1048.003", "T1486"],
    difficulty: ["Standard", "Pressure"],
    setting: "GlobalTech Corp — 500 hosts", role: "Incident Responder (degraded visibility)",
  },
];

export default function Library() {
  const nav = useNavigate();
  const [filter, setFilter] = useState("all");
  const { data, isLoading } = useQuery<ScenarioSummary[]>({ queryKey: ["scenarios"], queryFn: api.scenarios });

  const scenarios = (data ?? []).filter((s) => filter === "all" || s.type === filter || s.industry === filter);

  return (
    <>
      <div className="section-header">
        <h1>Scenario Library</h1>
        <p>Pre-built and custom scenarios — each runs on the model-driven engine</p>
      </div>

      <div className="scenario-filters">
        {FILTERS.map((f) => (
          <button key={f.key} className={"filter-chip" + (filter === f.key ? " active" : "")} onClick={() => setFilter(f.key)}>
            {f.label}
          </button>
        ))}
      </div>

      {/* Educational Simulations */}
      {(filter === "all" || filter === "edu") && (
        <>
          <div style={{ marginTop: 24, marginBottom: 12 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700 }}><i className="fa fa-graduation-cap" style={{ marginRight: 8, color: "var(--gc-accent)" }} />Educational Simulations</h2>
            <p style={{ fontSize: 12, color: "var(--gc-muted)" }}>Interactive, scenario-driven learning modules with real SOC console experience</p>
          </div>
          <div className="scenario-grid">
            {EDU_SCENARIOS.map((s) => (
              <div key={s.id} className="scenario-card" style={{ cursor: "pointer", position: "relative" }}
                onClick={() => nav(`/sim-edu/${s.id}`)}>
                <div style={{ width: 44, height: 44, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", background: s.gradient, marginBottom: 10 }}>
                  <i className={`fa ${s.icon}`} style={{ color: "#fff", fontSize: 18 }} />
                </div>
                <div className="scenario-name">{s.name}</div>
                <div style={{ fontSize: 11, color: s.color, fontWeight: 600, marginBottom: 6 }}>{s.subtitle}</div>
                <div className="scenario-desc">{s.description}</div>
                <div style={{ fontSize: 11, color: "var(--gc-muted)", margin: "8px 0 4px" }}>
                  <i className="fa fa-hospital" /> {s.setting} · <i className="fa fa-user-shield" /> {s.role}
                </div>
                <div className="scenario-meta">
                  <div className="meta-item"><i className="fa fa-layer-group" /> {s.stages} stages</div>
                  <div className="meta-item"><i className="fa fa-clock" /> {s.duration}m</div>
                  <div className="meta-item"><i className="fa fa-shield-alt" /> {s.mitre.length} techniques</div>
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 8 }}>
                  {s.difficulty.map(d => (
                    <span key={d} style={{ fontSize: 9, padding: "2px 6px", borderRadius: 3, background: "var(--gc-surface)", color: "var(--gc-muted)", fontWeight: 600 }}>{d}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Engine Simulations */}
      {filter !== "edu" && (
        <div style={{ marginTop: 24, marginBottom: 12 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700 }}><i className="fa fa-cogs" style={{ marginRight: 8, color: "var(--gc-accent)" }} />Engine Simulations</h2>
          <p style={{ fontSize: 12, color: "var(--gc-muted)" }}>Model-driven, deterministic simulations with full AAR reporting</p>
        </div>
      )}
      {isLoading && <div className="center-empty"><span className="spinner" /> Loading…</div>}
      {filter !== "edu" && <div className="scenario-grid">
        {scenarios.map((s) => (
          <div key={s.id} className="scenario-card" onClick={() => nav(`/launch/${s.id}`)}>
            <div className={`scenario-badge ${s.badge}`}>{s.label}</div>
            <div className="scenario-name">{s.name}</div>
            <div className="scenario-desc">{s.description}</div>
            <div className="scenario-meta">
              <div className="meta-item"><i className="fa fa-clock" /> {s.nominal_duration_min}m</div>
              <div className="meta-item"><i className="fa fa-layer-group" /> {s.phases.length} phases</div>
              <div className="meta-item"><i className="fa fa-bolt" /> {s.step_count} steps</div>
              <div className="meta-item"><i className="fa fa-industry" /> {s.industry}</div>
            </div>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <button className="btn btn-ghost" style={{ fontSize: 10, padding: "4px 10px" }}
                onClick={(e) => { e.stopPropagation(); nav(`/builder?clone=${s.id}`); }}>
                <i className="fa fa-copy" /> Clone
              </button>
            </div>
          </div>
        ))}
      </div>}
    </>
  );
}
