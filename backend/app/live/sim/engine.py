"""ScenarioSim — the dynamic, tick-based cyber-range engine behind the immersive workspaces.

Rides on a LiveSession (multi-user + WS + manager ticker + live-fire). It owns a `Topology`, per-team
state, an alert queue, and worm flags; teams act through `run_tool`; the worm spreads on `tick`;
auto-driven seats are **telegraphed** (announce intent + countdown so a human can pre-empt); the
outcome **emerges** from how fast the worm spreads vs. how fast SOC detects and Blue contains.

Real Red tools queue a live-fire job (real nmap/NetExec/… against the Docker lab) and ALSO apply their
topology effect; simulated tools only apply the effect + print synthetic terminal output. Nothing
dangerous (worm spread, encryption, shadow deletion) ever touches the lab.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import topology as T
from . import tools as TL

if TYPE_CHECKING:
    from ..session import LiveSession

AUTO_EVERY = 3                  # ticks between an auto seat's actions = the telegraph/reaction window
ROLES = ("soc", "blue", "red")  # defenders telegraph/act before Red each cycle


@dataclass
class TeamState:
    score: int = 0
    done: set[str] = field(default_factory=set)     # tool ids ever used (unlock + once gating)


class ScenarioSim:
    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id
        _builders = {"scn-wannacry-w1": T.build_w1, "scn-r5-phishing": T.build_r5, "scn-c5-edr": T.build_c5}
        self.topo: T.Topology = _builders.get(scenario_id, T.build_w1)()
        self.tools: dict[str, TL.Tool] = TL.by_id(scenario_id)
        self.teams = {"red": TeamState(), "blue": TeamState(), "soc": TeamState()}
        self.events: list[dict] = []
        self.seq = 0
        self.started_at = time.time()
        self.tick_n = 0
        self.alerts: list[dict] = []
        self.alert_seq = 0
        self.incident_declared: set[str] = set()
        # worm flags
        self.propagating = False
        self.kill_switch: str | None = None           # None | "armed" | "tripped"
        self.segmented = False
        self.smbv1_patched = False
        self.backups_safe = True
        self.r_value = 2.4
        # the unnamed remainder of the 250-host fleet — tracked as aggregates so the worm can reach
        # real scale (Degraded/Catastrophic) without drawing 250 nodes
        self.extra_infected = 0
        self.extra_impacted = 0
        self.extra_dormant = 0
        self.pending_intents: dict[str, dict] = {}     # role -> {tool_id, params, label, ticks_left}
        # Auto-driven seats act ONLY when the host enables this. Off by default so a learner can read,
        # explore tools and act at their own pace — nothing happens on a clock until they make it happen.
        self.auto_enabled = False
        self.finished = False
        self.outcome: str | None = None
        self.report: dict | None = None
        self.session: "LiveSession | None" = None      # set on attach
        self._emit("g_phase", "system", "Operation Tripwire — you are the worm",
                   "Patient zero FIN-WS-014 is infected. Discover the network, spread before the "
                   "defenders stop you. Switch tabs to watch SOC and Blue react.", sev="high")

    # ---- time / events -------------------------------------------------------
    def _t(self) -> int:
        return int(time.time() - self.started_at)

    def _emit(self, kind: str, role: str, title: str, message: str, *, sev: str = "info",
              data: dict | None = None, notify: bool = False) -> dict:
        ev = {"seq": self.seq, "t": self._t(), "kind": kind, "role": role, "title": title,
              "message": message, "severity": sev, "data": data or {}, "notify": notify}
        self.seq += 1
        self.events.append(ev)
        return ev

    def _alert(self, label: str, host: T.Host | None, sev: str, mitre: str = "") -> None:
        a = {"id": f"al{self.alert_seq}", "t": self._t(), "label": label, "mitre": mitre,
             "severity": sev, "host_id": host.id if host else None,
             "host_name": host.name if host else None, "status": "new"}
        self.alert_seq += 1
        self.alerts.append(a)
        self._emit("alert", "soc", f"ALERT: {label}",
                   (f"on {host.name} " if host else "") + "— awaiting SOC triage",
                   sev=sev, data={"alert_id": a["id"]}, notify=True)

    # ---- host filters --------------------------------------------------------
    def _hosts_for(self, flt: str) -> list[T.Host]:
        hs = self.topo.hosts.values()
        if flt == "exploitable":
            return [h for h in hs if h.vulnerable and h.revealed and h.state in ("healthy", "vulnerable")]
        if flt == "exploited":
            return [h for h in hs if h.state == "exploited"]
        if flt == "vulnerable":
            return [h for h in hs if h.vulnerable and h.state in ("healthy", "vulnerable")]
        if flt == "containable":
            return [h for h in hs if h.state in T.LIVE_INFECTED or h.state == "exploited"]
        if flt == "impacted":
            return [h for h in hs if h.state == "impacted"]
        return list(hs)

    # ---- availability / unlocks ---------------------------------------------
    def _available(self, tool: TL.Tool) -> tuple[bool, str]:
        ts = self.teams[tool.team]
        if tool.once and tool.id in ts.done:
            return False, "already done"
        for req in tool.unlocks_after:
            if req not in ts.done:
                return False, f"requires {self.tools[req].name if req in self.tools else req}"
        # target availability for host-targeted tools
        for f in tool.schema:
            if f.type in ("host", "hosts") and not self._hosts_for(f.filter):
                return False, f"no {f.filter} host yet"
            if f.type == "alert":
                pool = [a for a in self.alerts if a["status"] == ("new" if f.filter == "new" else "triaged")]
                if not pool:
                    return False, f"no {f.filter} alert"
        if tool.effect == "sinkhole" and self.kill_switch != "armed":
            return False, "no kill-switch callback observed yet"
        if tool.effect == "restore" and not self.backups_safe:
            return False, "backups were not preserved"
        return True, ""

    def unlocked(self, team: str) -> list[dict]:
        out = []
        for t in self.tools.values():
            if t.team != team:
                continue
            ok, reason = self._available(t)
            out.append(t.public(ok, reason))
        return out

    # ====================================================================== #
    #  run_tool — the single entry point for every team action
    # ====================================================================== #
    def run_tool(self, team: str, tool_id: str, params: dict | None = None,
                 by_auto: bool = False) -> tuple[bool, str]:
        if self.finished:
            return False, "scenario complete"
        tool = self.tools.get(tool_id)
        if tool is None or tool.team != team:
            return False, "unknown tool for this team"
        ok, reason = self._available(tool)
        if not ok:
            return False, reason
        params = params or {}
        msg = self._apply(tool, params)
        self.teams[team].done.add(tool.id)
        self.teams[team].score += 12 if team == "red" else 15
        # real tools also fire the real command against the lab (streamed back by the manager)
        if tool.kind == "real" and tool.fire_action and self.session is not None:
            from app.lab import live_fire as lf
            ev = self._emit("action", "red", tool.name, f"{tool.fire_action}: real tool",
                            sev="medium", data={"tool_id": tool.id, "kind": "real",
                                                "live_fire": lf.queued_view(tool.fire_action)}, notify=True)
            self.session.pending_fire.append({"seq": ev["seq"], "action_id": tool.fire_action,
                                              "target_id": None})
        else:
            self._emit("action" if team == "red" else "response", team, tool.name,
                       (tool.command_hint + "  ·  " if tool.command_hint else "") + (msg or tool.outcome),
                       sev="high" if team != "red" else "medium",
                       data={"tool_id": tool.id, "kind": tool.kind,
                             "command": tool.command_hint, "mitigates": tool.mitigates}, notify=True)
        self._check_finish()
        return True, ""

    def _apply(self, tool: TL.Tool, params: dict) -> str:
        eff = tool.effect
        topo = self.topo
        # ---- RED ----
        if eff == "reveal_hosts":
            rng = params.get("range", "subnet")
            for h in topo.hosts.values():
                if rng == "all" or h.vlan == "fin":
                    h.revealed = True
            self._emit("g_telemetry", "soc", "Port-445 scan", "Horizontal TCP/445 fan-out from one source "
                       "(LOW signal — easy to miss)", sev="low", data={"telemetry": "scan"})
            return f"{sum(1 for h in topo.hosts.values() if h.revealed)} hosts discovered"
        if eff == "mark_vulnerable":
            n = 0
            for h in topo.hosts.values():
                h.revealed = True
                if h.vulnerable and h.state == "healthy":
                    h.state = "vulnerable"
                    n += 1
            self._emit("g_telemetry", "soc", "SMBv1 negotiation", "Legacy SMBv1 dialect to many hosts "
                       "(LOW–MEDIUM)", sev="low", data={"telemetry": "smb_negotiation"})
            return f"{n} SMBv1-vulnerable hosts identified"
        if eff == "exploit":
            h = topo.hosts.get(params.get("host", ""))
            if h is None or h not in self._hosts_for("exploitable"):
                return "select a valid vulnerable host"
            h.state = "exploited"
            self._alert("Exploit signature (SMBv1)", h, "high", "T1210")
            return f"{h.name} exploited"
        if eff == "infect":
            h = topo.hosts.get(params.get("host", ""))
            if h is None or h.state != "exploited":
                return "select an exploited host"
            h.state = "infected"
            self._alert("Suspicious payload write", h, "medium", "T1059.003")
            return f"{h.name} infected"
        if eff == "persist":
            for h in topo.hosts.values():
                if h.state in T.LIVE_INFECTED:
                    h.flags.add("persistent")
            self._alert("New service / autorun", None, "medium", "T1543")
            return "persistence established on infected hosts"
        if eff == "killswitch_check":
            self.kill_switch = "armed"
            self._alert("Outbound to newly-seen domain", None, "medium", "T1071.001")
            return "kill-switch domain unreachable — worm proceeds"
        if eff == "start_propagation":
            self.propagating = True
            self._emit("g_telemetry", "soc", "Multi-source scanning", "Same scan/exploit pattern now from "
                       "MANY internal hosts (HIGH — it's spreading)", sev="high", data={"telemetry": "spread"})
            return "worm propagation started"
        if eff == "disable_recovery":
            for h in topo.hosts.values():
                if h.state in T.LIVE_INFECTED:
                    h.flags.add("recovery_disabled")
            self._alert("Shadow-copy deletion", None, "high", "T1490")
            return "local recovery disabled on infected hosts"
        if eff == "encrypt":
            n = 0
            for h in topo.hosts.values():
                if h.state in T.LIVE_INFECTED:
                    h.state = "impacted"
                    h.flags.add("encrypted")
                    n += 1
            self.extra_impacted += self.extra_infected
            n += self.extra_infected
            self.extra_infected = 0
            self.propagating = False           # detonation ends the spread phase
            self._alert("Mass file rename (.locked)", None, "critical", "T1486")
            return f"{n} hosts encrypted"
        # ---- BLUE ----
        if eff == "isolate":
            h = topo.hosts.get(params.get("host", ""))
            if h is None or h not in self._hosts_for("containable"):
                return "select a compromised host"
            h.state = "contained"
            h.flags.discard("persistent")
            bonus = " (on a SOC-escalated incident)" if h.id in self.incident_declared else ""
            self.teams["blue"].score += 10 if h.id in self.incident_declared else 5
            return f"{h.name} isolated{bonus}"
        if eff == "patch_hosts":
            ids = [x for x in params.get("hosts", "").split(",") if x]
            n = 0
            for hid in ids:
                h = topo.hosts.get(hid)
                if h and h.vulnerable:
                    h.vulnerable = False
                    if h.state == "vulnerable":
                        h.state = "healthy"
                    n += 1
            return f"SMBv1 disabled on {n} host(s)"
        if eff == "segment":
            a, b = (params.get("edge", "fin|srv").split("|") + ["fin", "srv"])[:2]
            topo.cut_edge(a, b)
            self.segmented = True
            self._recompute_r()
            return f"severed {a.upper()} ↔ {b.upper()} on TCP/445"
        if eff == "sinkhole":
            if self.kill_switch != "armed":
                return "no kill-switch callback to sinkhole"
            self.kill_switch = "tripped"
            for h in topo.hosts.values():
                if h.state in T.LIVE_INFECTED:
                    h.state = "dormant"
            self.extra_dormant += self.extra_infected
            self.extra_infected = 0
            self.propagating = False
            self.r_value = 0.0
            return "kill-switch tripped — infected hosts went dormant fleet-wide"
        if eff == "patch_all":
            for h in topo.hosts.values():
                if h.vulnerable:
                    h.vulnerable = False
                    if h.state == "vulnerable":
                        h.state = "healthy"
            self.smbv1_patched = True
            self.r_value = 0.0
            return "SMBv1 patched fleet-wide — the vector is gone"
        if eff == "restore":
            h = topo.hosts.get(params.get("host", ""))
            if h is None or h.state != "impacted":
                return "select an impacted host"
            h.state = "recovered"
            h.flags.discard("encrypted")
            return f"{h.name} restored from clean backup"
        # ---- SOC ----
        if eff == "view":
            return f"inspected telemetry via {tool.name}"
        if eff == "hunt":
            n = 0
            for h in topo.hosts.values():
                if h.state in T.LIVE_INFECTED and not any(al["host_id"] == h.id for al in self.alerts):
                    self._alert(f"Hunt: undetected foothold", h, "high")
                    n += 1
            return f"surfaced {n} undetected foothold(s)"
        if eff == "triage":
            a = next((x for x in self.alerts if x["id"] == params.get("alert") and x["status"] == "new"), None)
            if a is None:
                return "select a new alert"
            a["status"] = "triaged"
            return f"triaged {a['label']}"
        if eff == "escalate":
            a = next((x for x in self.alerts if x["id"] == params.get("alert") and x["status"] == "triaged"), None)
            if a is None:
                return "select a triaged alert"
            a["status"] = "escalated"
            if a["host_id"]:
                self.incident_declared.add(a["host_id"])
            self.teams["soc"].score += 10
            return f"escalated — incident declared" + (f" on {a['host_name']}" if a["host_name"] else "")
        return ""

    def _recompute_r(self) -> None:
        r = 2.4
        if self.segmented:
            r *= 0.4
        if self.smbv1_patched or self.kill_switch == "tripped":
            r = 0.0
        self.r_value = round(r, 2)

    # ====================================================================== #
    #  tick — worm propagation + telegraphed auto + outcome
    # ====================================================================== #
    def tick(self) -> bool:
        if self.finished:
            return False
        self.tick_n += 1
        changed = self._propagate()
        changed = self._auto_step() or changed
        if self._check_finish():
            changed = True
        return changed

    def _propagate(self) -> bool:
        if not self.propagating or self.smbv1_patched or self.kill_switch == "tripped" or self.r_value <= 0:
            return False
        sources = [h for h in self.topo.hosts.values() if h.state in T.LIVE_INFECTED]
        named_live = len(sources)
        if named_live == 0 and self.extra_infected == 0:
            return False
        for h in sources:
            if h.state == "infected":
                h.state = "propagating"
        changed = False
        # spread among the named, drawn hosts (reachability + vulnerability gated)
        pool, seen = [], set()
        for s in sources:
            for t in self.topo.spread_targets(s):
                if t.id not in seen:
                    seen.add(t.id)
                    pool.append(t)
        if pool:
            n = min(len(pool), max(1, round(self.r_value * 0.5 * max(1, named_live))), 5)
            for t in pool[:n]:
                t.state = "infected"
            changed = True
        # spread into the unnamed remainder of the fleet (the other ~226 hosts) — geometric in R
        total_live = named_live + self.extra_infected
        remaining = self.topo.extra_hosts - self.extra_infected - self.extra_impacted - self.extra_dormant
        if remaining > 0 and total_live > 0:
            grow = min(remaining, max(1, round(self.r_value * 0.4 * total_live)), 30)
            self.extra_infected += grow
            changed = True
        if changed:
            self._emit("g_telemetry", "soc", "Worm spread",
                       f"{self.infected_total()} hosts infected (R≈{self.r_value})",
                       sev="high", data={"telemetry": "spread"}, notify=True)
            if not any(al["label"].startswith("Lateral") for al in self.alerts[-4:]):
                self._alert("Lateral movement (multi-source)", None, "high", "T1021.002")
        return changed

    # ---- telegraphed auto-drivers -------------------------------------------
    def _is_auto(self, role: str) -> bool:
        if self.session is None:
            return True
        return self.session.is_auto(role)

    def _auto_step(self) -> bool:
        if not self.auto_enabled:               # learner-paced: no seat acts on a timer
            if self.pending_intents:
                self.pending_intents.clear()
            return False
        changed = False
        for role in ROLES:
            if not self._is_auto(role):
                self.pending_intents.pop(role, None)
                continue
            intent = self.pending_intents.get(role)
            if intent is None:
                intent = self._plan(role)
                if intent is not None:
                    intent["ticks_left"] = AUTO_EVERY
                    self.pending_intents[role] = intent
                    self._emit("g_intent", role, f"{role.upper()} will {intent['label']}",
                               f"in ~{AUTO_EVERY * 3}s — act first to change the outcome",
                               sev="medium", data={"role": role, "eta_ticks": AUTO_EVERY})
                continue
            intent["ticks_left"] -= 1
            if intent["ticks_left"] <= 0:
                ok, _ = self.run_tool(role, intent["tool_id"], intent.get("params"), by_auto=True)
                self.pending_intents.pop(role, None)
                changed = changed or ok
        return changed

    def _plan(self, role: str) -> dict | None:
        """Pick an auto seat's next intended tool + a human-readable label (no execution yet)."""
        def avail(tid: str) -> bool:
            t = self.tools.get(tid)
            return t is not None and self._available(t)[0]

        if role == "red":
            for tid in ("nmap", "netexec"):
                if avail(tid):
                    return {"tool_id": tid, "label": self.tools[tid].name}
            if avail("eternalblue"):
                h = (self._hosts_for("exploitable") or [None])[0]
                if h:
                    return {"tool_id": "eternalblue", "params": {"host": h.id}, "label": f"exploit {h.name}"}
            if avail("payload"):
                h = (self._hosts_for("exploited") or [None])[0]
                if h:
                    return {"tool_id": "payload", "params": {"host": h.id}, "label": f"infect {h.name}"}
            for tid in ("propagate", "persistence", "dns_killswitch", "shadow_delete", "ransomware"):
                if avail(tid):
                    return {"tool_id": tid, "label": self.tools[tid].name}
            return None
        if role == "soc":
            new = next((a for a in self.alerts if a["status"] == "new"), None)
            if new and avail("soc_triage"):
                return {"tool_id": "soc_triage", "params": {"alert": new["id"]}, "label": f"triage '{new['label']}'"}
            tri = next((a for a in self.alerts if a["status"] == "triaged"), None)
            if tri and avail("soc_escalate"):
                return {"tool_id": "soc_escalate", "params": {"alert": tri["id"]}, "label": "escalate an incident"}
            for tid in ("threat_hunt", "splunk", "sysmon"):
                if avail(tid):
                    return {"tool_id": tid, "label": self.tools[tid].name}
            return None
        if role == "blue":
            if self.propagating and not self.segmented and avail("segment"):
                return {"tool_id": "segment", "params": {"edge": "fin|srv"}, "label": "segment Finance ↔ Server"}
            if self.kill_switch == "armed" and avail("sinkhole"):
                return {"tool_id": "sinkhole", "label": "sinkhole the kill-switch domain"}
            cont = self._hosts_for("containable")
            if cont and avail("edr_quarantine"):
                pick = next((h for h in cont if h.id in self.incident_declared), cont[0])
                return {"tool_id": "edr_quarantine", "params": {"host": pick.id}, "label": f"isolate {pick.name}"}
            if avail("wsus"):
                return {"tool_id": "wsus", "label": "patch SMBv1 fleet-wide"}
            imp = self._hosts_for("impacted")
            if imp and avail("restore"):
                return {"tool_id": "restore", "params": {"host": imp[0].id}, "label": f"restore {imp[0].name}"}
            return None
        return None

    # ---- outcome -------------------------------------------------------------
    def infected_total(self) -> int:
        return self.topo.infected_count() + self.extra_infected

    def impacted_total(self) -> int:
        return self.topo.impacted_count() + self.extra_impacted

    def outcome_band(self) -> str:
        total = self.topo.total_hosts()
        hit = self.infected_total() + self.impacted_total()
        ratio = hit / total if total else 0.0
        if ratio < 0.10 and self.backups_safe:
            return "Contained"
        if ratio < 0.45:
            return "Degraded"
        return "Catastrophic"

    def financial_loss(self) -> int:
        return int(self.impacted_total() * (85.0 + 750.0))

    def _live_threats(self) -> int:
        return sum(1 for h in self.topo.hosts.values()
                   if h.state in T.LIVE_INFECTED or h.state == "exploited")

    def _check_finish(self) -> bool:
        if self.finished:
            return False
        ransomed = "ransomware" in self.teams["red"].done
        # Blue win: no live threats (named or unnamed) + vector neutralised
        evicted = (self._live_threats() == 0 and self.extra_infected == 0
                   and (self.smbv1_patched or self.kill_switch == "tripped"))
        # Red end: impact detonated and the spread phase is over
        spent = ransomed and not self.propagating
        # No idle/timeout finish — the run ends only on real eviction, ransomware impact, or a manual
        # Conclude. A beginner can take as long as they like before acting.
        if evicted or spent:
            self._finish()
            return True
        return False

    def set_auto_enabled(self, on: bool) -> None:
        self.auto_enabled = bool(on)
        if not on:
            self.pending_intents.clear()

    def conclude(self) -> None:
        if not self.finished:
            self._finish()

    def _finish(self) -> None:
        self.finished = True
        self.outcome = self.outcome_band()
        self.report = self._build_report()
        self._emit("g_result", "system", f"Scenario complete — {self.outcome}",
                   f"{self.infected_total()} infected, {self.impacted_total()} impacted, "
                   f"est. loss ${self.financial_loss():,}.", sev="critical",
                   data={"outcome": self.outcome}, notify=True)
        # Save the AAR (Reports & AAR) — reuse the guided persistence (compatible report shape).
        if self.session is not None:
            try:
                self.session.report = self.report
                self.session.status = "completed"
                self.session.match_result = "guided"
                from ..guided_runtime import _persist_guided_report
                _persist_guided_report(self.session)
            except Exception:  # noqa: BLE001 — persistence must never break conclusion
                pass

    # ---- AAR -----------------------------------------------------------------
    def _build_report(self) -> dict:
        band = self.outcome or self.outcome_band()
        result = {"Contained": "blue", "Degraded": "draw", "Catastrophic": "red"}.get(band, "draw")
        counts = self.topo.counts()
        teams = {}
        for role in ("red", "soc", "blue"):
            tl = [{"t": e["t"], "label": e["title"]} for e in self.events
                  if e["role"] == role and e["kind"] in ("action", "response", "soc")]
            teams[role] = {"score": self.teams[role].score, "timeline": tl,
                           "kpis": {"actions": len(tl)}}
        teams["soc"]["kpis"]["alerts"] = len(self.alerts)
        teams["soc"]["kpis"]["escalated"] = sum(1 for a in self.alerts if a["status"] == "escalated")
        recs = []
        if band != "Contained":
            recs.append("Act earlier — segment / patch / isolate before propagation outruns you.")
        if not self.smbv1_patched:
            recs.append("Disable SMBv1 fleet-wide; it is the worm's entire vector.")
        if band == "Contained":
            recs.append("Strong run — early detection + containment held the blast radius down.")
        return {
            "session_id": self.session.id if self.session else "", "guided": True,
            "scenario": {"id": self.scenario_id, "name": "Operation Tripwire",
                         "subtitle": "WannaCry-Style SMB Worm"},
            "result": result, "outcome_band": band,
            "verdict": {"Contained": "Contained — minimal impact.", "Degraded": "Degraded — partial impact.",
                        "Catastrophic": "Catastrophic — fleet-wide encryption."}.get(band, "Concluded."),
            "duration_s": self._t(), "teams": teams,
            "outcome": {"outcome_band": band, "infected": self.infected_total(),
                        "impacted": self.impacted_total(), "total_hosts": self.topo.total_hosts(),
                        "financial_loss": self.financial_loss(), **counts},
            "recommendations": recs[:6],
            "note": "Immersive cyber-range AAR — saved to Reports & AAR.",
        }

    # ---- snapshot ------------------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "scenario_id": self.scenario_id, "tick": self.tick_n, "finished": self.finished,
            "outcome": self.outcome, "auto_enabled": self.auto_enabled, "topology": self.topo.public(),
            "worm": {"r_value": self.r_value, "propagating": self.propagating,
                     "kill_switch": self.kill_switch, "segmented": self.segmented,
                     "smbv1_patched": self.smbv1_patched, "backups_safe": self.backups_safe,
                     "infected": self.infected_total(), "impacted": self.impacted_total(),
                     "extra_infected": self.extra_infected, "extra_impacted": self.extra_impacted,
                     "financial_loss": self.financial_loss(), "outcome_band": self.outcome_band()},
            "teams": {r: {"score": self.teams[r].score, "tools": self.unlocked(r)} for r in ("red", "soc", "blue")},
            "alerts": list(self.alerts),
            "incident_declared": sorted(self.incident_declared),
            "pending_intents": {r: {"label": i["label"], "ticks_left": i.get("ticks_left", 0)}
                                for r, i in self.pending_intents.items()},
            "events": self.events,
            "report": self.report,
        }
