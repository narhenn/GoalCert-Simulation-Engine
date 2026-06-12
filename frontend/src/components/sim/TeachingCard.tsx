/**
 * TeachingCard — visual teaching content that replaces chat bubbles.
 *
 * 4 variants: concept (explain), action (do this), result (what happened), flow (attack chain).
 * Supports mini diagrams, code blocks, step counters, and action buttons.
 */

interface TeachingCardProps {
  type: "concept" | "action" | "result" | "flow";
  title: string;
  body: string;
  step?: { current: number; total: number };
  code?: string;
  diagram?: React.ReactNode;
  status?: "waiting" | "done" | "error";
  statusText?: string;
  onNext?: () => void;
  onDismiss?: () => void;
  onDeepen?: () => void;
  deepenLabel?: string;
  style?: React.CSSProperties;
}

const TYPE_STYLES: Record<string, { icon: string; accent: string; label: string }> = {
  concept: { icon: "fa-lightbulb", accent: "var(--gc-primary)", label: "LEARN" },
  action: { icon: "fa-hand-pointer", accent: "#ea580c", label: "YOUR TURN" },
  result: { icon: "fa-chart-bar", accent: "#16a34a", label: "RESULT" },
  flow: { icon: "fa-route", accent: "#0284c7", label: "ATTACK FLOW" },
};

export default function TeachingCard({
  type, title, body, step, code, diagram, status, statusText,
  onNext, onDismiss, onDeepen, deepenLabel, style,
}: TeachingCardProps) {
  const t = TYPE_STYLES[type] || TYPE_STYLES.concept;

  return (
    <div style={{
      width: 380, maxWidth: "90vw", background: "#fff", borderRadius: 16,
      borderLeft: `4px solid ${t.accent}`, boxShadow: "0 12px 40px rgba(0,0,0,0.18)",
      overflow: "hidden", color: "var(--gc-text)", zIndex: 9500,
      animation: "cardAppear 0.3s ease", ...style,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
        borderBottom: "1px solid var(--gc-border)" }}>
        <i className={`fa ${t.icon}`} style={{ color: t.accent, fontSize: 13 }} />
        <span style={{ fontSize: 10, fontWeight: 700, color: t.accent, letterSpacing: 1 }}>{t.label}</span>
        {step && (
          <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--gc-muted)",
            background: "var(--gc-soft)", padding: "2px 8px", borderRadius: 10 }}>
            {step.current}/{step.total}
          </span>
        )}
        {onDismiss && (
          <button onClick={onDismiss} style={{ marginLeft: step ? 4 : "auto", background: "none",
            border: "none", color: "var(--gc-muted)", cursor: "pointer", fontSize: 13, padding: 2 }}>
            <i className="fa fa-times" />
          </button>
        )}
      </div>

      {/* Body */}
      <div style={{ padding: "12px 14px" }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6, color: "var(--gc-text)" }}>{title}</div>

        {diagram && <div style={{ margin: "10px 0" }}>{diagram}</div>}

        <div style={{ fontSize: 12.5, color: "var(--gc-text2)", lineHeight: 1.7 }}>
          {body.split(/(\*\*[^*]+\*\*|`[^`]+`)/).map((part, i) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return <strong key={i} style={{ color: "var(--gc-text)" }}>{part.slice(2, -2)}</strong>;
            }
            if (part.startsWith("`") && part.endsWith("`")) {
              return <code key={i} style={{ background: "var(--gc-soft)", padding: "1px 5px",
                borderRadius: 4, fontFamily: "var(--mono)", fontSize: 11.5, color: t.accent }}>
                {part.slice(1, -1)}
              </code>;
            }
            return <span key={i}>{part}</span>;
          })}
        </div>

        {code && (
          <div style={{ margin: "10px 0", background: "#0b1220", borderRadius: 8, padding: "8px 12px",
            fontFamily: "var(--mono)", fontSize: 11.5, color: "#34d399", userSelect: "text",
            cursor: "text", position: "relative" }}>
            <span style={{ color: "#ef4444" }}>$</span> {code}
            <button onClick={() => navigator.clipboard.writeText(code)}
              style={{ position: "absolute", top: 6, right: 6, background: "rgba(255,255,255,0.1)",
                border: "none", color: "#94a3b8", cursor: "pointer", borderRadius: 4, padding: "2px 6px",
                fontSize: 10 }}>
              <i className="fa fa-copy" />
            </button>
          </div>
        )}

        {status && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, fontSize: 11,
            color: status === "done" ? "#16a34a" : status === "error" ? "#ef4444" : "var(--gc-muted)" }}>
            {status === "waiting" && <span className="spinner" style={{ width: 10, height: 10 }} />}
            {status === "done" && <i className="fa fa-check-circle" />}
            {status === "error" && <i className="fa fa-times-circle" />}
            {statusText || (status === "waiting" ? "Waiting for you..." : status === "done" ? "Done!" : "Error")}
          </div>
        )}
      </div>

      {/* Footer */}
      {(onNext || onDeepen) && (
        <div style={{ display: "flex", gap: 6, padding: "8px 14px",
          borderTop: "1px solid var(--gc-border)", justifyContent: "flex-end" }}>
          {onDeepen && (
            <button onClick={onDeepen} style={{ fontSize: 11, padding: "5px 12px", borderRadius: 8,
              background: "var(--gc-soft)", border: "1px solid var(--gc-border)",
              color: "var(--gc-primary)", cursor: "pointer", fontWeight: 500 }}>
              {deepenLabel || "Tell me more"}
            </button>
          )}
          {onNext && (
            <button onClick={onNext} style={{ fontSize: 11, padding: "5px 14px", borderRadius: 8,
              background: t.accent, border: "none", color: "#fff", cursor: "pointer", fontWeight: 600 }}>
              Next →
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* Mini diagram components for use inside TeachingCard */

export function MiniTopology({ hosts }: { hosts: { id: string; name: string; state: string }[] }) {
  const stateColors: Record<string, string> = {
    healthy: "#16a34a", vulnerable: "#ca8a04", exploited: "#ea580c",
    infected: "#dc2626", impacted: "#111", contained: "#3b82f6",
  };
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", padding: "6px 0" }}>
      {hosts.map(h => (
        <div key={h.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
          <div style={{ width: 28, height: 28, borderRadius: 7, background: stateColors[h.state] || "#94a3b8",
            display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 11 }}>
            <i className="fa fa-desktop" />
          </div>
          <span style={{ fontSize: 8, color: "var(--gc-muted)", maxWidth: 40, overflow: "hidden",
            textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.name}</span>
        </div>
      ))}
    </div>
  );
}

export function AttackFlowDiagram({ steps }: { steps: { icon: string; label: string; sublabel: string }[] }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "8px 0", overflowX: "auto" }}>
      {steps.map((s, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: "var(--gc-soft)",
              border: "2px solid var(--gc-primary)", display: "flex", alignItems: "center",
              justifyContent: "center", fontSize: 14, color: "var(--gc-primary)",
              animation: `cardAppear 0.4s ease ${i * 0.2}s both` }}>
              <i className={`fa ${s.icon}`} />
            </div>
            <span style={{ fontSize: 8, color: "var(--gc-text)", fontWeight: 600 }}>{s.label}</span>
            <span style={{ fontSize: 7, color: "var(--gc-muted)" }}>{s.sublabel}</span>
          </div>
          {i < steps.length - 1 && (
            <div style={{ width: 20, height: 2, background: "var(--gc-primary)", opacity: 0.4,
              animation: `cardAppear 0.3s ease ${i * 0.2 + 0.1}s both` }} />
          )}
        </div>
      ))}
    </div>
  );
}
