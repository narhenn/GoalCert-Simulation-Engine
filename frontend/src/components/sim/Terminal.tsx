import { useEffect, useRef, useState } from "react";
import { fmtT } from "./shared";

/* The Kali terminal dock — real tool output (live-fire) + synthetic command lines for sim steps. */
export default function Terminal({ events, termUrl, height = 200 }: { events: any[]; termUrl?: string | null; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(true);
  useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [events.length, open]);

  const lines = events.filter((e) => e.kind === "action" || (e.data && (e.data.command || e.data.live_fire)));

  return (
    <div className="term">
      <div className="term-head" onClick={() => setOpen((o) => !o)}>
        <i className={`fa ${open ? "fa-chevron-down" : "fa-chevron-up"}`} />
        <i className="fa fa-terminal" /> kali@gc-attacker — terminal
        <span style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
          {termUrl && <a href={termUrl} target="_blank" rel="noreferrer" style={{ color: "#22d3ee" }}
            onClick={(e) => e.stopPropagation()}><i className="fa fa-up-right-from-square" /> real shell</a>}
          <span>{lines.length} cmds</span>
        </span>
      </div>
      {open && (
        <div className="term-body" ref={ref} style={{ height }}>
          <div style={{ color: "#64748b" }}>GoalCert Kali — run tools from the palette, or open the real shell to type freely.</div>
          {lines.map((e, i) => <Line key={i} e={e} />)}
        </div>
      )}
    </div>
  );
}

function Line({ e }: { e: any }) {
  const lf = e.data?.live_fire;
  const cmd = e.data?.command;
  return (
    <div className="term-line">
      <span style={{ color: "#475569" }}>[{fmtT(e.t)}] </span>
      {lf ? (
        <>
          <span className="term-cmd">$ {lf.command || `${lf.tool} (${lf.function})`}</span>
          {lf.status === "queued" && <span style={{ color: "#eab308" }}> · running {lf.tool}…</span>}
          {lf.output && <pre className="term-out">{lf.output}</pre>}
          {lf.detected && <div style={{ color: "#f59e0b" }}><i className="fa fa-eye" /> DETECTED — {lf.detection_evidence}</div>}
          {lf.status === "unavailable" && <div style={{ color: "#64748b" }}>{lf.output}</div>}
        </>
      ) : (
        <>
          {cmd
            ? <span className="term-cmd">$ {cmd}</span>
            : <span style={{ color: "#cbd5e1" }}>{e.title}</span>}
          {e.message && !cmd && <span style={{ color: "#64748b" }}> — {e.message}</span>}
        </>
      )}
    </div>
  );
}
