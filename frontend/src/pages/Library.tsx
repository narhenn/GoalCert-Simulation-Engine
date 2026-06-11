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
    description: "A ransomware worm sweeps through a 250-host hospital network. Red drives the worm, Blue contains and patches, SOC detects and escalates — all teams functional, real interplay.",
    icon: "fa-virus", color: "#C8413E", gradient: "linear-gradient(135deg, #C8413E, #E07A3E)",
    stages: 9, duration: 35, mitre: ["T1046", "T1210", "T1486", "T1490", "T1021.002"],
    difficulty: ["Standard", "Pressure"],
    setting: "Mercy Regional Health Network", role: "Red · Blue · SOC",
  },
  {
    id: "scn-r5-phishing", name: "R5 — Phishing to Encrypt",
    subtitle: "Human-Operated Ransomware",
    description: "A targeted phishing email leads to macro execution, credential theft, lateral movement, and enterprise-wide ransomware. Red attacks, Blue defends, SOC monitors — all live.",
    icon: "fa-envelope-open-text", color: "#E07A3E", gradient: "linear-gradient(135deg, #E07A3E, #C8413E)",
    stages: 9, duration: 45, mitre: ["T1566.001", "T1204.002", "T1053.005", "T1003.001", "T1486"],
    difficulty: ["Standard", "Pressure"],
    setting: "MediumCorp Financial Services", role: "Red · Blue · SOC",
  },
  {
    id: "scn-c5-edr", name: "C5 — EDR Outage Exploitation",
    subtitle: "Attacking During Blindness",
    description: "Your EDR vendor pushes a bad update and endpoint visibility goes dark. An attacker piggybacks — password spray, lateral movement, double extortion. Defend with compensating controls.",
    icon: "fa-eye-slash", color: "#5B7FB0", gradient: "linear-gradient(135deg, #5B7FB0, #c084fc)",
    stages: 9, duration: 50, mitre: ["T1110.003", "T1133", "T1003.001", "T1048.003", "T1486"],
    difficulty: ["Standard", "Pressure"],
    setting: "GlobalTech Corp — 500 hosts", role: "Red · Blue · SOC",
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
        <p>Practice arena — full scenarios with <b>all teams functional</b>. Pick a role; the others play live against you.</p>
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
            <h2 style={{ fontSize: 16, fontWeight: 700 }}><i className="fa fa-dumbbell" style={{ marginRight: 8, color: "var(--gc-orange)" }} />Practice Arena — All Teams Live</h2>
            <p style={{ fontSize: 12.5, color: "var(--gc-muted)" }}>Pick a role and play it against the others for real. Same mission goals and per-phase guidance as the live teaching scenarios — but here the opposing teams actually respond.</p>
          </div>
          <div className="scenario-grid">
            {EDU_SCENARIOS.map((s) => (
              <div key={s.id} className="scenario-card" style={{ cursor: "pointer", position: "relative" }}
                onClick={() => nav(`/play/${s.id}?mode=practice`)}>
                <span style={{ position: "absolute", top: 14, right: 14, fontSize: 9, fontWeight: 700, letterSpacing: .5,
                  padding: "3px 8px", borderRadius: 20, background: "rgba(234,88,12,.12)", color: "var(--gc-orange)" }}>
                  <i className="fa fa-dumbbell" /> PRACTICE
                </span>
                <div style={{ width: 46, height: 46, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", background: s.gradient, marginBottom: 12 }}>
                  <i className={`fa ${s.icon}`} style={{ color: "#fff", fontSize: 19 }} />
                </div>
                <div className="scenario-name">{s.name}</div>
                <div style={{ fontSize: 11.5, color: s.color, fontWeight: 600, marginBottom: 7 }}>{s.subtitle}</div>
                <div className="scenario-desc">{s.description}</div>
                <div style={{ fontSize: 11.5, color: "var(--gc-muted)", margin: "8px 0 4px" }}>
                  <i className="fa fa-location-dot" /> {s.setting} · <i className="fa fa-users" /> {s.role}
                </div>
                <div className="scenario-meta">
                  <div className="meta-item"><i className="fa fa-layer-group" /> {s.stages} phases</div>
                  <div className="meta-item"><i className="fa fa-clock" /> {s.duration}m</div>
                  <div className="meta-item"><i className="fa fa-shield-halved" /> {s.mitre.length} techniques</div>
                </div>
                <button className="btn btn-primary" style={{ marginTop: 12, width: "100%", justifyContent: "center" }}>
                  <i className="fa fa-play" /> Enter practice
                </button>
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
