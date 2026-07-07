import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

const MODELS = [
  { id: "claude-opus-4-8", label: "Claude Opus 4.8 (most capable)" },
  { id: "claude-sonnet-5", label: "Claude Sonnet 5 (balanced)" },
  { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (fastest)" },
];

export default function StudioSettings() {
  const qc = useQueryClient();
  const { data: settings } = useQuery({ queryKey: ["studio-settings"], queryFn: api.studioSettings });
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["studio-settings"] });
    setSaved(true); setTimeout(() => setSaved(false), 2500);
  };

  const save = async () => {
    setBusy(true);
    try {
      await api.studioSaveSettings({
        api_key: key.trim() || undefined,
        model: model || settings?.model,
      });
      setKey(""); invalidate();
    } catch (e) { alert("Save failed: " + e); }
    finally { setBusy(false); }
  };

  const clear = async () => {
    if (!confirm("Remove the stored Anthropic key? The Studio will fall back to local stub mode.")) return;
    setBusy(true);
    try { await api.studioClearKey(); invalidate(); }
    catch (e) { alert(e); }
    finally { setBusy(false); }
  };

  const agent = settings?.ai_mode === "agent";

  return (
    <>
      <div className="section-header">
        <h1>Scenario Studio — AI Settings</h1>
        <p>The Studio runs fully in a local deterministic mode with no key. Add your <b>Anthropic API key</b> to power authoring, in-context simulation, analysis and the training coach with Claude. The key is stored on this server and used for the Studio's own endpoints.</p>
      </div>

      <div style={{ maxWidth: 640 }}>
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <span style={{ width: 12, height: 12, borderRadius: "50%", background: agent ? "#22c55e" : "#94a3b8" }} />
            <div style={{ fontWeight: 700, fontSize: 15 }}>{agent ? "Claude connected" : "Local stub mode"}</div>
          </div>
          <div className="muted" style={{ fontSize: 13 }}>
            {agent
              ? <>Using <b>{settings?.model}</b> · key <code>{settings?.masked_key}</code> · source: {settings?.source}</>
              : "No key set — the Studio uses deterministic offline generators. Everything still works; add a key for richer, sector-specific reasoning."}
          </div>
        </div>

        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}><i className="fa fa-key" /> Anthropic API key</div>

          <div className="builder-label">API key</div>
          <input className="form-input" type="password" value={key} onChange={(e) => setKey(e.target.value)}
            placeholder={settings?.has_key ? "•••••••• (a key is already stored — paste to replace)" : "sk-ant-…"}
            style={{ marginBottom: 12, fontFamily: "var(--mono)" }} />

          <div className="builder-label">Model</div>
          <select className="form-select" value={model || settings?.model || MODELS[0].id} onChange={(e) => setModel(e.target.value)} style={{ marginBottom: 16 }}>
            {MODELS.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn btn-primary" disabled={busy || (!key.trim() && !model)} onClick={save}>
              {busy ? <><span className="spinner" /> Saving…</> : <><i className="fa fa-floppy-disk" /> Save</>}
            </button>
            {settings?.has_key && <button className="btn btn-ghost" disabled={busy} onClick={clear} style={{ color: "var(--gc-red)" }}><i className="fa fa-trash" /> Remove key</button>}
            {saved && <span style={{ color: "#22c55e", fontSize: 13 }}><i className="fa fa-check" /> Saved</span>}
          </div>

          <div className="muted" style={{ fontSize: 11.5, marginTop: 14, lineHeight: 1.6 }}>
            <i className="fa fa-shield-halved" /> The key is stored server-side and never returned to the browser in full (only a masked preview). Get a key at <span style={{ fontFamily: "var(--mono)" }}>console.anthropic.com</span>. You can also set <code>ANTHROPIC_API_KEY</code> as an environment variable instead.
          </div>
        </div>
      </div>
    </>
  );
}
