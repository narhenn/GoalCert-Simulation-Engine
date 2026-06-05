"""The deterministic, multi-actor simulation orchestrator (v2).

run(scenario, environment, config) -> RunResult

Every team acts. Red's technique playbook emits telemetry; controls turn telemetry into
alerts; the SOC triages/classifies/escalates; Blue contains (with decision gates) which
mutates the world and can truncate Red; Management and OT react to severity/phase. Each team
emits TASK status events so the operator can watch all teams side-by-side, and is scored
separately. The operator's `focus_role` is purely a lens — it does not change the timeline.

Pure: no wall-clock, no RNG. Identical inputs always produce an identical timeline.
"""
from __future__ import annotations

import heapq

from .catalog.spec import TechniqueSpec, get_technique
from .config import RunConfig
from .enums import CredScope, EventType, PLevel, SecurityState, Severity, Side
from .environment import EnvironmentSpec, build_world
from .events import SimEvent
from .kpis import compute_kpis
from .resolve import resolver as R
from .result import ObjectiveStatus, RunResult
from .scenario import Scenario, TargetSelector
from .workflows import get_workflow
from .world import AssetInstance, World

_KIND_PRIORITY = {"phase": 0, "attack": 1, "detection": 3,
                  "soc_triage": 4, "mgmt": 5, "blue_contain": 6, "ot_ops": 7}

# latency bases (seconds, pre difficulty/readiness scaling)
SOC_TRIAGE_BASE = 150.0
BLUE_CONTAIN_BASE = 300.0
DC_APPROVAL_BASE = 180.0
MGMT_NOTIFY_BASE = 200.0
OT_OPS_BASE = 240.0

RED_STAGE = {
    "Reconnaissance": "red.recon", "Initial Compromise": "red.access",
    "Privilege Escalation": "red.privesc", "Lateral Movement": "red.lateral",
    "Persistence": "red.persist", "Data Exfiltration": "red.exfil",
    "Ransomware": "red.impact", "OT Attack": "red.impact",
}
PERSISTENCE_TECHNIQUES = {"persistence_task", "cloud_persistence"}


def _select_target(world: World, sel: TargetSelector | None) -> AssetInstance | None:
    if sel is None:
        return None
    matches = world.by_role(sel.value) if sel.by == "role" else world.by_type(sel.value)
    return matches[0] if matches else None


def _asset_snapshot(world: World) -> list[dict]:
    return [{"id": a.id, "type": a.type_key, "name": a.name, "role": a.role, "zone": a.zone,
             "criticality": a.criticality, "security_state": a.security_state.value,
             "health": a.health.value} for a in world.all_assets()]


def _p_level(spec: TechniqueSpec, target: AssetInstance | None) -> PLevel:
    if spec.key in ("dcsync_domain_admin", "ransomware", "ot_plc_modify"):
        return PLevel.P0
    if spec.severity == Severity.CRITICAL:
        return PLevel.P0
    crit = target.criticality if target else 3
    if spec.severity == Severity.HIGH:
        return PLevel.P1 if crit >= 4 else PLevel.P2
    if spec.severity == Severity.MEDIUM:
        return PLevel.P2
    return PLevel.NONE


def _soc_assigns(correct: PLevel, config: RunConfig) -> tuple[PLevel, bool]:
    """Deterministic SOC classification — may under-classify under stress (escalation accuracy)."""
    if correct != PLevel.P0 and config.difficulty.rank >= 4 and config.readiness < 40 \
            and correct.value >= 2:
        lowered = {PLevel.P1: PLevel.P2, PLevel.P2: PLevel.NONE}.get(correct, correct)
        return lowered, False
    return correct, True


# objective milestone keyword maps
_RED_KW = {
    "foothold": ("access", "compromise", "foothold", "phish", "initial"),
    "privilege": ("privilege", "escalat", "credential", "admin"),
    "domain_admin": ("domain admin",), "persistence": ("persist",), "exfil": ("exfil",),
    "ransomware": ("ransom", "encrypt", "deploy"),
    "ot": ("ot", "plc", "process", "production", "physical", "scada"),
}
_BLUE_KW = {
    "detect": ("detect", "identif", "hunt", "evidence", "forensic", "preserve", "timeline", "scope"),
    "contain": ("contain", "isolat", "block"), "prevent": ("prevent",),
    "recover": ("recover", "restore", "continuity", "backup"),
    "notify": ("notif", "report", "regulat", "communicat", "escalat", "draft"),
}


def _objective_met(text: str, milestones: dict[str, bool], keywords: dict[str, tuple]) -> bool:
    low = text.lower()
    for milestone, kws in keywords.items():
        if any(kw in low for kw in kws) and milestones.get(milestone):
            return True
    return False


def run(scenario: Scenario, env: EnvironmentSpec, config: RunConfig) -> RunResult:
    world = build_world(env)
    events: list[SimEvent] = []
    duration_s = config.duration_min * 60
    nominal = max(1, scenario.nominal_duration_min)
    scale = config.duration_min / nominal
    seq = 0

    bindings = scenario.workflow_bindings or {}
    workflows = {actor: get_workflow(wid) for actor, wid in bindings.items()}
    task_status: dict[tuple[str, str], str] = {}
    for wf in workflows.values():
        for st in wf.steps:
            task_status[(wf.actor, st.id)] = "pending"

    def emit(t: int, etype: EventType, **kw) -> None:
        nonlocal seq
        events.append(SimEvent(seq=seq, t=t, type=etype, **kw))
        seq += 1

    def step_time(at_min: float) -> int:
        return max(0, round(at_min * 60 * scale))

    def set_task(t, actor, step_id, status, msg="", phase=None):
        if task_status.get((actor, step_id)) == status:
            return
        task_status[(actor, step_id)] = status
        label = ""
        wf = workflows.get(actor)
        if wf:
            for st in wf.steps:
                if st.id == step_id:
                    label = st.label
                    break
        emit(t, EventType.TASK, side=Side(actor), actor=actor, phase=phase, title=label or step_id,
             message=msg or label, data={"step_id": step_id, "status": status, "label": label})

    # ---- phase-range drill: filter playbook + prime preconditions ----------
    playbook = list(scenario.playbook)
    if config.phase_range:
        lo, hi = config.phase_range
        names = scenario.phases
        playbook = [s for s in playbook if s.phase in names and lo <= names.index(s.phase) + 1 <= hi]
        if lo >= 2:  # prime attacker so a mid-chain drill is meaningful
            eps = world.by_role("primary_endpoint") or world.by_type("endpoint")
            if eps:
                eps[0].security_state = SecurityState.COMPROMISED
                world.attacker.add_foothold(eps[0].id)
            world.attacker.flags["c2"] = True
            world.attacker.raise_creds(CredScope.USER if lo < 4 else CredScope.PRIVILEGED)

    # NB: focus_role is a lens only — it must NOT appear in the timeline (keeps it pure).
    emit(0, EventType.SYSTEM, actor="engine", title="Initialised",
         message=f"Scenario loaded: {scenario.name}")
    emit(0, EventType.SYSTEM, actor="white-cell", title="Briefing", message=scenario.description)

    heap: list[tuple] = []
    counter = 0

    def push(t, kind, payload):
        nonlocal counter
        heapq.heappush(heap, (t, _KIND_PRIORITY[kind], counter, payload))
        counter += 1

    for s in playbook:
        pidx = scenario.phases.index(s.phase) if s.phase in scenario.phases else 0
        push(step_time(s.at_min), "attack", {"kind": "attack", "step": s, "phase_idx": pidx})

    # ---- accumulators -------------------------------------------------------
    attempts = successes = blocked = detected = contained = 0
    dwells: list[int] = []
    mtta: list[int] = []
    mttc: list[int] = []
    first_detection_t: int | None = None
    esc_correct = esc_total = 0
    hunt_found = hunt_planted = 0
    scores = {"red": 0, "blue": 0, "soc": 0, "mgmt": 0, "ot": 0}
    soc_max_p = PLevel.NONE
    escalated: set[str] = set()
    mgmt_done: set[str] = set()
    evidence_ok = config.readiness >= 50
    current_phase_idx = -1

    def score_event(t):
        emit(t, EventType.SCORE, actor="scoring", title="score", data=dict(scores))

    def schedule_mgmt(t, level, phase):
        nonlocal soc_max_p
        if level.value > soc_max_p.value:
            soc_max_p = level
        if level.value >= PLevel.P1.value and "notify_ciso" not in mgmt_done:
            mgmt_done.add("notify_ciso")
            push(t + config.latency(MGMT_NOTIFY_BASE), "mgmt",
                 {"kind": "mgmt", "step": "mgmt.notify_ciso", "deadline_s": 1800, "start": t,
                  "phase": phase, "label": "CISO notified / war-room opened"})
        if level.value >= PLevel.P0.value and "declare_p0" not in mgmt_done:
            mgmt_done.add("declare_p0")
            push(t + config.latency(MGMT_NOTIFY_BASE), "mgmt",
                 {"kind": "mgmt", "step": "mgmt.declare_p0", "deadline_s": 1800, "start": t,
                  "phase": phase, "label": "P0 declared · BCP activated"})
            push(t + config.latency(MGMT_NOTIFY_BASE * 1.5), "mgmt",
                 {"kind": "mgmt", "step": "mgmt.comms", "deadline_s": 3600, "start": t,
                  "phase": phase, "label": "Comms & legal engaged (no ransom w/o Legal)"})

    # ---- main loop ----------------------------------------------------------
    while heap:
        t, _pr, _c, p = heapq.heappop(heap)
        if t > duration_s:
            continue
        kind = p["kind"]

        if kind == "attack":
            step = p["step"]
            spec = get_technique(step.technique)
            target = _select_target(world, step.target)
            phase = step.phase
            tname = target.name if target else "environment"
            red_stage = RED_STAGE.get(phase)

            if p["phase_idx"] > current_phase_idx:
                current_phase_idx = p["phase_idx"]
                emit(t, EventType.PHASE, actor="white-cell", phase=phase,
                     title=f"Phase: {phase}", message=f"Entering phase: {phase}")
                if red_stage:
                    set_task(t, "red", red_stage, "active", f"{phase} underway", phase)

            if step.is_inject:
                emit(t, EventType.INJECT, side=Side.RED, actor="white-cell", phase=phase,
                     severity=spec.severity, technique=spec.mitre, title="Inject",
                     message=step.label or spec.name,
                     asset_id=target.id if target else None, asset_label=tname if target else None)

            attempts += 1
            res = R.resolve(spec, world, target, config)

            if res.status == "blocked":
                blocked += 1
                scores["blue"] += spec.score.blue_contain
                if red_stage:
                    set_task(t, "red", red_stage, "blocked", f"{spec.name} blocked", phase)
                emit(t, EventType.BLOCK, side=Side.BLUE, actor=res.prevented_by or "control",
                     phase=phase, severity=Severity.MEDIUM, technique=spec.mitre,
                     title=f"Prevented: {spec.name}",
                     message=f"{spec.name} blocked by {res.prevented_by} ({tname})",
                     asset_id=target.id if target else None, asset_label=tname if target else None)
                score_event(t)

            elif res.status == "failed":
                if red_stage and task_status.get(("red", red_stage)) == "active":
                    set_task(t, "red", red_stage, "blocked", f"{spec.name} could not proceed", phase)
                emit(t, EventType.FAIL, side=Side.RED, actor="red-team", phase=phase,
                     severity=Severity.LOW, technique=spec.mitre, title=f"Attempt failed: {spec.name}",
                     message=f"Preconditions unmet ({res.reason}); cannot {spec.name} on {tname}",
                     asset_id=target.id if target else None, asset_label=tname if target else None)

            else:  # success
                successes += 1
                scores["red"] += spec.score.red_success
                affected = R.apply_effects(spec, world, target)
                if step.technique in PERSISTENCE_TECHNIQUES:
                    hunt_planted += 1
                if red_stage:
                    set_task(t, "red", red_stage, "done", f"{spec.name} succeeded", phase)
                emit(t, EventType.ATTACK, side=Side.RED, actor="red-team", phase=phase,
                     severity=spec.severity, technique=spec.mitre, title=spec.name,
                     message=(step.label or spec.name) + (f" → {tname}" if target else ""),
                     asset_id=target.id if target else None, asset_label=tname if target else None)
                for em in R.build_emits(spec, world, target):
                    emit(t, EventType.TELEMETRY, actor=em.channel, phase=phase, severity=em.severity,
                         channel=em.channel, technique=spec.mitre, title=spec.name, message=em.text,
                         asset_id=target.id if target else None, asset_label=tname if target else None)
                for aid in affected:
                    asset = world.get(aid)
                    if asset:
                        emit(t, EventType.STATE, actor="env", asset_id=aid, asset_label=asset.name,
                             title="State change",
                             message=f"{asset.name}: {asset.security_state.value} / {asset.health.value}",
                             data={"security_state": asset.security_state.value, "health": asset.health.value})
                det = R.compute_detection(spec, world, target, config, t)
                if det is not None:
                    dt, ctype, cid = det
                    push(dt, "detection", {"kind": "detection", "spec_key": spec.key, "success_t": t,
                                           "ctype": ctype, "cid": cid,
                                           "target_id": target.id if target else None, "phase": phase})
                if world.attacker.flags.get("in_ot") and "ot" in workflows:
                    push(t + config.latency(OT_OPS_BASE), "ot_ops",
                         {"kind": "ot_ops", "phase": phase, "target_id": target.id if target else None})
                score_event(t)

        elif kind == "detection":
            spec = get_technique(p["spec_key"])
            ctype, cid = p["ctype"], p["cid"]
            if ctype in world.attacker.disabled_control_types:
                continue
            ctrl = world.controls.get(cid)
            if ctrl is None or not ctrl.active:
                continue
            detected += 1
            dwell = t - p["success_t"]
            dwells.append(dwell)
            if first_detection_t is None:
                first_detection_t = t
            scores["soc"] += spec.score.blue_detect
            target = world.get(p["target_id"]) if p["target_id"] else None
            tlabel = target.name if target else None
            set_task(t, "soc", "soc.triage", "active", "Triaging incoming alert", p["phase"])
            emit(t, EventType.DETECTION, side=Side.SOC, actor=ctype.upper(), phase=p["phase"],
                 severity=spec.severity, technique=spec.mitre, title=f"Alert: {spec.name}",
                 message=f"{ctrl.name} detected {spec.name}" + (f" on {tlabel}" if tlabel else "")
                         + f" (dwell {dwell}s)",
                 asset_id=p["target_id"], asset_label=tlabel, data={"control": ctype, "dwell_s": dwell})
            if spec.key in PERSISTENCE_TECHNIQUES:
                hunt_found += 1
                set_task(t, "soc", "soc.hunt", "done", "Persistence mechanism hunted & found", p["phase"])
            push(t + config.latency(SOC_TRIAGE_BASE), "soc_triage",
                 {"kind": "soc_triage", "spec_key": spec.key, "detect_t": t,
                  "target_id": p["target_id"], "phase": p["phase"]})

        elif kind == "soc_triage":
            spec = get_technique(p["spec_key"])
            target = world.get(p["target_id"]) if p["target_id"] else None
            correct = _p_level(spec, target)
            assigned, ok = _soc_assigns(correct, config)
            esc_total += 1
            esc_correct += 1 if ok else 0
            mtta.append(t - p["detect_t"])
            scores["soc"] += 30 if ok else 10
            set_task(t, "soc", "soc.triage", "done", "Alert triaged (confirmed malicious)", p["phase"])
            set_task(t, "soc", "soc.classify", "done",
                     f"Classified {assigned.label}"
                     + ("" if ok else f" (under-classified; should be {correct.label})"), p["phase"])
            set_task(t, "soc", "soc.investigate", "done", "L2 investigation: scope widened", p["phase"])
            emit(t, EventType.ESCALATION, side=Side.SOC, actor="soc", phase=p["phase"],
                 severity=spec.severity, technique=spec.mitre, title=f"SOC: {assigned.label}",
                 message=f"{spec.name} classified {assigned.label}" + (f" on {target.name}" if target else ""),
                 data={"p_level": assigned.value, "p_label": assigned.label, "correct": ok})
            schedule_mgmt(t, assigned, p["phase"])
            if assigned.value >= PLevel.P2.value and target is not None and spec.containable \
                    and target.id not in escalated and target.security_state != SecurityState.CONTAINED:
                escalated.add(target.id)
                set_task(t, "soc", "soc.escalate", "done", f"Escalated {target.name} to IR", p["phase"])
                push(t + config.latency(BLUE_CONTAIN_BASE), "blue_contain",
                     {"kind": "blue_contain", "spec_key": p["spec_key"], "alert_t": p["detect_t"],
                      "target_id": target.id, "phase": p["phase"]})
            score_event(t)

        elif kind == "blue_contain":
            spec = get_technique(p["spec_key"])
            target = world.get(p["target_id"])
            if target is None or target.security_state == SecurityState.CONTAINED:
                continue
            is_dc = target.type_key == "domain_controller"
            if is_dc and not p.get("approved"):
                emit(t, EventType.DECISION, side=Side.BLUE, actor="ir-team", phase=p["phase"],
                     severity=Severity.MEDIUM, title="Decision gate: isolate DC?",
                     message=f"Isolating {target.name} (DC) requires CISO approval — holding for sign-off",
                     asset_id=target.id, asset_label=target.name, data={"gate": "isolate_dc"})
                scores["blue"] += 10
                p["approved"] = True
                push(t + config.latency(DC_APPROVAL_BASE), "blue_contain", p)
                continue
            set_task(t, "blue", "blue.identify", "done",
                     "Scoped incident; memory captured first" if evidence_ok
                     else "Scoped incident (no memory image)", p["phase"])
            target.security_state = SecurityState.CONTAINED
            if target.id in world.attacker.footholds:
                world.attacker.footholds.remove(target.id)
            contained += 1
            mttc.append(t - p["alert_t"])
            scores["blue"] += spec.score.blue_contain + (15 if evidence_ok else 0) + (10 if is_dc else 0)
            set_task(t, "blue", "blue.contain", "done", f"{target.name} isolated / contained", p["phase"])
            emit(t, EventType.RESPONSE, side=Side.BLUE, actor="ir-team", phase=p["phase"],
                 severity=Severity.MEDIUM, title=f"Contained: {target.name}",
                 message=f"{target.name} isolated; foothold revoked"
                         + (" (memory preserved)" if evidence_ok else "") + f" (MTTC {t - p['alert_t']}s)",
                 asset_id=target.id, asset_label=target.name,
                 data={"mttc_s": t - p["alert_t"], "evidence_integrity": evidence_ok})
            emit(t, EventType.STATE, actor="env", asset_id=target.id, asset_label=target.name,
                 title="State change", message=f"{target.name}: contained",
                 data={"security_state": target.security_state.value, "health": target.health.value})
            score_event(t)

        elif kind == "mgmt":
            step_id = p["step"]
            on_time = (t - p["start"]) <= p["deadline_s"]
            scores["mgmt"] += 40 if on_time else 15
            set_task(t, "mgmt", step_id, "done", p["label"] + ("" if on_time else " (late)"), p["phase"])
            emit(t, EventType.NOTIFY, side=Side.MGMT, actor="incident-commander", phase=p["phase"],
                 severity=Severity.HIGH, title=p["label"],
                 message=p["label"] + (f" — within {p['deadline_s'] // 60}m window" if on_time
                                       else " — DEADLINE MISSED"),
                 data={"on_time": on_time, "deadline_s": p["deadline_s"]})
            if step_id == "mgmt.declare_p0" and "regulatory" not in mgmt_done:
                mgmt_done.add("regulatory")
                push(t + config.latency(MGMT_NOTIFY_BASE), "mgmt",
                     {"kind": "mgmt", "step": "mgmt.regulatory", "deadline_s": 43200, "start": t,
                      "phase": p["phase"], "label": "Regulatory / critical-infra notification"})
            score_event(t)

        elif kind == "ot_ops":
            if "ot" not in workflows or task_status.get(("ot", "ot.manual")) == "done":
                continue
            for sid, msg in [("ot.validate", "OT alerts validated"),
                             ("ot.coordinate", "Coordinated with plant operators"),
                             ("ot.manual", "Switched to manual operations"),
                             ("ot.isolate", "OT segment isolated")]:
                set_task(t, "ot", sid, "done", msg, p["phase"])
            ot_impacted = world.attacker.flags.get("ot_impact")
            scores["ot"] += 30 if ot_impacted else 80
            emit(t, EventType.RESPONSE, side=Side.OT, actor="ot-ops", phase=p["phase"],
                 severity=Severity.HIGH, title="OT: manual operations",
                 message="Plant switched to manual; safety-critical systems protected"
                         + (" (impact already occurred)" if ot_impacted else ""),
                 data={"safety_preserved": not ot_impacted})
            score_event(t)

    # ---- finalise -----------------------------------------------------------
    a = world.attacker
    backups_enabled = world.active_global_control("backups") is not None
    final_assets = world.all_assets()

    if contained > 0:
        set_task(duration_s, "blue", "blue.eradicate", "done", "Persistence removed; krbtgt rotated ×2")
        set_task(duration_s, "blue", "blue.recover", "done" if backups_enabled else "blocked",
                 "Restored from offline backups" if backups_enabled
                 else "No tested backups — recovery impaired")
        set_task(duration_s, "blue", "blue.lessons", "done", "After-action report produced")
        scores["blue"] += 40 if backups_enabled else 0

    milestones = {
        "foothold": a.has_foothold() or any(x.security_state == SecurityState.COMPROMISED for x in final_assets),
        "privilege": a.cred_scope.rank >= 2, "domain_admin": a.cred_scope.rank >= 3,
        "persistence": bool(a.flags.get("persistence") or a.flags.get("cloud_persistence")),
        "exfil": bool(a.flags.get("exfiltrated")), "ransomware": bool(a.flags.get("ransomware")),
        "ot": bool(a.flags.get("ot_impact")), "detect": detected > 0, "contain": contained > 0,
        "prevent": blocked > 0, "recover": backups_enabled,
        "notify": bool(a.flags.get("ransomware") or a.flags.get("exfiltrated")),
    }
    objectives = {
        "red": [ObjectiveStatus(text=o, met=_objective_met(o, milestones, _RED_KW))
                for o in scenario.objectives.red],
        "blue": [ObjectiveStatus(text=o, met=_objective_met(o, milestones, _BLUE_KW))
                 for o in scenario.objectives.blue],
    }

    kpis = compute_kpis(attempts=attempts, successes=successes, detected=detected, contained=contained,
                        blocked=blocked, dwells=dwells, mttrs=mttc, first_detection_t=first_detection_t)
    kpis["mtta_s"] = round(sum(mtta) / len(mtta), 1) if mtta else 0.0
    kpis["mttc_s"] = round(sum(mttc) / len(mttc), 1) if mttc else 0.0
    kpis["escalation_accuracy"] = round(esc_correct / esc_total, 3) if esc_total else 1.0
    kpis["hunt_success"] = round(hunt_found / hunt_planted, 3) if hunt_planted else 0.0

    summary = {
        "attempts": attempts, "succeeded": successes, "blocked": blocked,
        "failed": attempts - successes - blocked, "detected": detected, "contained": contained,
        "escalations": esc_total, "max_p_level": soc_max_p.label, "assets_total": len(final_assets),
        "assets_compromised": sum(1 for x in final_assets if x.security_state == SecurityState.COMPROMISED),
        "assets_contained": sum(1 for x in final_assets if x.security_state == SecurityState.CONTAINED),
        "assets_down": sum(1 for x in final_assets if x.health.value == "down"),
        "attacker_max_creds": a.cred_scope.value, "exfiltrated": bool(a.flags.get("exfiltrated")),
        "ransomware": bool(a.flags.get("ransomware")), "ot_impact": bool(a.flags.get("ot_impact")),
        "backups_enabled": backups_enabled,
    }

    emit(duration_s, EventType.SYSTEM, actor="engine", title="Complete",
         message=f"Complete — Red {scores['red']} / Blue {scores['blue']} / SOC {scores['soc']} / "
                 f"Mgmt {scores['mgmt']} / OT {scores['ot']}")

    role_tasks: dict[str, list[dict]] = {}
    for actor, wf in workflows.items():
        role_tasks[actor] = [{"id": st.id, "label": st.label, "description": st.description,
                              "status": task_status.get((actor, st.id), "pending")} for st in wf.steps]

    return RunResult(
        scenario_id=scenario.id, duration_s=duration_s, focus_role=config.focus_role.value,
        events=events, scores=scores, kpis=kpis, summary=summary, objectives=objectives,
        environment=_asset_snapshot(build_world(env)), final_assets=_asset_snapshot(world),
        workflows=[{"actor": wf.actor, "id": wf.id, "name": wf.name, "description": wf.description,
                    "steps": [s.model_dump() for s in wf.steps]} for wf in workflows.values()],
        role_tasks=role_tasks,
    )
