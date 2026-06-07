import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { LiveMission, LiveSessionSummary, ScenarioSummary } from "../api/types";

export function storePlayer(sessionId: string, playerId: string) {
  localStorage.setItem(`gc_live_${sessionId}`, playerId);
}
export function loadPlayer(sessionId: string): string | null {
  return localStorage.getItem(`gc_live_${sessionId}`);
}
export function myName(): string {
  return localStorage.getItem("gc_live_name") || "";
}

export default function LiveSessions() {
  const nav = useNavigate();
  const [name, setName] = useState(myName());
  const [busy, setBusy] = useState(false);

  const { data: sessions } = useQuery<LiveSessionSummary[]>({
    queryKey: ["live-sessions"], queryFn: api.liveSessions, refetchInterval: 3000,
  });
  const { data: missions } = useQuery<LiveMission[]>({ queryKey: ["live-missions"], queryFn: api.liveMissions });
  const { data: scenarios } = useQuery<ScenarioSummary[]>({ queryKey: ["scenarios"], queryFn: api.scenarios });

  const goLive = async (body: { mission_id?: string; scenario_id?: string }) => {
    if (!name.trim()) { alert("Enter your operator name first."); return; }
    setBusy(true);
    try {
      localStorage.setItem("gc_live_name", name.trim());
      const r = await api.createLiveSession({ host_name: name.trim(), ...body });
      storePlayer(r.session_id, r.player_id);
      nav(`/live/${r.session_id}`);
    } finally { setBusy(false); }
  };

  const join = async (s: LiveSessionSummary) => {
    const who = name.trim() || window.prompt("Your operator name:")?.trim();
    if (!who) return;
    setName(who); localStorage.setItem("gc_live_name", who);
    const existing = loadPlayer(s.id);
    if (existing) { nav(`/live/${s.id}`); return; }
    const r = await api.joinLiveSession(s.id, { name: who });
    storePlayer(s.id, r.player_id);
    nav(`/live/${s.id}`);
  };

  return (
    <>
      <div className="section-header">
        <h1>Live Multiplayer</h1>
        <p>Pick a <b>mission</b> to go live — teammates then join and choose roles (Red / Blue / SOC, or auto-pilot). Each mission is a dedicated, self-contained engagement.</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: "1 1 240px" }}>
            <div className="builder-label">Your operator name</div>
            <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Operator-1" />
          </div>
          <div className="muted" style={{ fontSize: 12, flex: "2 1 300px" }}>
            Choose a dedicated mission below, or launch a pre-built scenario. The host sets the adversary
            profile and automation in the lobby.
          </div>
        </div>
      </div>

      {/* DEDICATED MISSIONS */}
      <div className="card-title" style={{ marginBottom: 12 }}><i className="fa fa-bullseye" /> Dedicated missions</div>
      <div className="scenario-grid" style={{ marginBottom: 24 }}>
        {(missions ?? []).map((m) => (
          <div key={m.id} className="scenario-card" onClick={() => !busy && goLive({ mission_id: m.id })}>
            <div className="scenario-badge badge-red">{m.klass}</div>
            <div className="scenario-name">{m.name}</div>
            <div className="scenario-desc">{m.tagline}</div>
            <div className="scenario-meta">
              <div className="meta-item"><i className="fa fa-gauge-high" /> {m.headline_metric}</div>
              <div className="meta-item"><i className="fa fa-clock" /> {m.cadence}</div>
            </div>
            <div style={{ marginTop: 10 }}>
              <button className="btn btn-danger" style={{ fontSize: 12 }} disabled={busy}
                onClick={(e) => { e.stopPropagation(); goLive({ mission_id: m.id }); }}>
                <i className="fa fa-satellite-dish" /> Go Live
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* PRE-BUILT SCENARIOS (e.g. Black Phoenix) */}
      <div className="card-title" style={{ marginBottom: 12 }}><i className="fa fa-database" /> Pre-built scenarios</div>
      <div className="scenario-grid" style={{ marginBottom: 24 }}>
        {(scenarios ?? []).map((s) => (
          <div key={s.id} className="scenario-card" onClick={() => !busy && goLive({ scenario_id: s.id })}>
            <div className={`scenario-badge ${s.badge}`}>{s.label}</div>
            <div className="scenario-name">{s.name}</div>
            <div className="scenario-desc">{s.description}</div>
            <div className="scenario-meta">
              <div className="meta-item"><i className="fa fa-layer-group" /> {s.phases.length} phases</div>
              <div className="meta-item"><i className="fa fa-industry" /> {s.industry}</div>
            </div>
            <div style={{ marginTop: 10 }}>
              <button className="btn btn-ghost" style={{ fontSize: 12 }} disabled={busy}
                onClick={(e) => { e.stopPropagation(); goLive({ scenario_id: s.id }); }}>
                <i className="fa fa-satellite-dish" /> Go Live (pick mission in lobby)
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* OPEN SESSIONS */}
      <div className="card-title" style={{ marginBottom: 12 }}><i className="fa fa-broadcast-tower" /> Open sessions</div>
      {(sessions ?? []).length === 0 && (
        <div className="center-empty" style={{ fontSize: 14 }}>No live sessions right now. Launch one above.</div>
      )}
      <div className="scenario-grid">
        {(sessions ?? []).map((s) => (
          <div key={s.id} className="scenario-card" onClick={() => join(s)}>
            <div className={`scenario-badge ${s.status === "active" ? "badge-red" : "badge-purple"}`}>
              {s.status === "active" ? "● LIVE" : "LOBBY"}
            </div>
            <div className="scenario-name">{s.scenario_name}</div>
            <div className="scenario-desc">Session {s.id}</div>
            <div className="scenario-meta">
              <div className="meta-item"><i className="fa fa-users" /> {s.player_count} player(s)</div>
              {Object.entries(s.roles).map(([r, n]) => (
                <div key={r} className="meta-item"><i className="fa fa-user-tag" /> {r} ×{n}</div>
              ))}
            </div>
            <div style={{ marginTop: 10 }}>
              <button className="btn btn-success" style={{ fontSize: 12 }} onClick={(e) => { e.stopPropagation(); join(s); }}>
                <i className="fa fa-right-to-bracket" /> Join
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
