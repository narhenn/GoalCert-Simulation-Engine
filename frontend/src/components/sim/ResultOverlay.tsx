/**
 * ResultOverlay — modal that appears after each tool execution.
 * Shows: what was done, what happened, consequence, what to do next.
 * Replaces the toast notifications with a proper teaching moment.
 */
import { useEffect, useState } from "react";
import { TEAM_META } from "./shared";

interface ResultData {
  tool_name: string;
  tool_id: string;
  team: string;
  consequence: string;
  next_hint: string;
  teaching_note: string;
  command?: string;
  outcome?: string;
}

interface Props {
  result: ResultData | null;
  onClose: () => void;
  onGoToNext?: (toolId: string) => void;
}

export default function ResultOverlay({ result, onClose, onGoToNext }: Props) {
  const [progress, setProgress] = useState(100);

  // Auto-dismiss after 12 seconds with progress bar
  useEffect(() => {
    if (!result) return;
    setProgress(100);
    const start = Date.now();
    const duration = 12000;
    const tick = setInterval(() => {
      const elapsed = Date.now() - start;
      const pct = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(pct);
      if (pct <= 0) { clearInterval(tick); onClose(); }
    }, 50);
    return () => clearInterval(tick);
  }, [result]);  // eslint-disable-line react-hooks/exhaustive-deps — onClose is stable

  if (!result) return null;

  const meta = TEAM_META[result.team] || TEAM_META.red;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ width: 520, maxWidth: "92vw", background: "#0d1320", borderRadius: 12,
        border: `1px solid ${meta.color}30`, overflow: "hidden" }}>

        {/* Progress bar */}
        <div style={{ height: 3, background: "rgba(255,255,255,0.04)" }}>
          <div style={{ height: "100%", width: `${progress}%`, background: meta.color, transition: "width 0.05s linear" }} />
        </div>

        {/* Header */}
        <div style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 10,
          borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <i className={`fa ${meta.icon}`} style={{ color: meta.color, fontSize: 16 }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--gc-text)" }}>{result.tool_name}</div>
            <div style={{ fontSize: 10, color: meta.color, fontWeight: 600, letterSpacing: 1 }}>{result.team.toUpperCase()} TEAM</div>
          </div>
          <button onClick={onClose} style={{ marginLeft: "auto", background: "none", border: "none",
            color: "var(--gc-muted)", cursor: "pointer", fontSize: 16, padding: 4 }}>
            <i className="fa fa-times" />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: "14px 18px", display: "flex", flexDirection: "column", gap: 12 }}>

          {/* What happened */}
          {result.consequence && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--gc-accent)", letterSpacing: 1, marginBottom: 4 }}>
                WHAT HAPPENED
              </div>
              <div style={{ fontSize: 13, color: "var(--gc-text)", lineHeight: 1.6 }}>{result.consequence}</div>
            </div>
          )}

          {/* Command (if available) */}
          {result.command && (
            <div style={{ background: "#080c14", borderRadius: 6, padding: "8px 12px", fontFamily: "var(--mono)",
              fontSize: 11.5, color: "#9ecbff", userSelect: "text", cursor: "text" }}>
              <span style={{ color: "#ef4444" }}>$</span> {result.command}
            </div>
          )}

          {/* Teaching note */}
          {result.teaching_note && (
            <div style={{ background: "rgba(224,164,88,0.06)", borderRadius: 8, padding: "10px 14px",
              borderLeft: "3px solid var(--gc-accent)" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--gc-accent)", letterSpacing: 1, marginBottom: 3 }}>
                <i className="fa fa-graduation-cap" style={{ marginRight: 4 }} /> LEARN
              </div>
              <div style={{ fontSize: 12, color: "var(--gc-body)", lineHeight: 1.6 }}>{result.teaching_note}</div>
            </div>
          )}

          {/* What to do next */}
          {result.next_hint && (
            <div style={{ background: "rgba(34,211,238,0.06)", borderRadius: 8, padding: "10px 14px",
              borderLeft: "3px solid #22d3ee" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#22d3ee", letterSpacing: 1, marginBottom: 3 }}>
                <i className="fa fa-arrow-right" style={{ marginRight: 4 }} /> NEXT STEP
              </div>
              <div style={{ fontSize: 12, color: "var(--gc-body)", lineHeight: 1.6 }}>{result.next_hint}</div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: "10px 18px", borderTop: "1px solid rgba(255,255,255,0.06)",
          display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onClose} className="btn btn-ghost" style={{ fontSize: 12 }}>
            Dismiss
          </button>
          <button onClick={() => { onClose(); }} className="btn btn-primary" style={{ fontSize: 12, background: meta.color }}>
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
