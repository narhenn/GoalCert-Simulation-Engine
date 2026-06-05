"""Layer 6 — Roles & Workflows.

Each team's procedure is *data*: an ordered list of steps the engine drives and reports on.
Red's actual actions come from the technique catalog (its workflow here is the kill-chain view
used for the live sub-report); SOC/Blue/Mgmt/OT steps are driven reactively by the engine
(alert -> triage -> escalation -> containment -> notification), each emitting TASK status so the
operator can watch every team's progress side-by-side.

The `kind` field is the stable handle the engine keys its reactive logic on; `label`/`description`
are what the UI shows. This is the action-space + guardrails a future AIDriver would consume.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .enums import Side


class RoleInfo(BaseModel):
    role: str
    name: str
    mission: str
    description: str


class WorkflowStep(BaseModel):
    id: str
    kind: str                 # engine handle (triage, escalate, contain, notify, manual_ops, ...)
    label: str
    description: str = ""
    phase_hint: str = ""      # which phase it typically activates in
    scored: bool = True


class Workflow(BaseModel):
    actor: str
    id: str
    name: str
    description: str
    steps: list[WorkflowStep] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Role descriptions
# --------------------------------------------------------------------------- #
ROLES: dict[str, RoleInfo] = {
    Side.RED.value: RoleInfo(
        role="red", name="Red Team (Adversary)",
        mission="Compromise, escalate, exfiltrate and impact — adapting TTPs when blocked.",
        description="Drives the APT→ransomware→OT kill-chain. Each phase applies MITRE techniques "
                    "to the environment; blocked steps branch to alternative TTPs."),
    Side.SOC.value: RoleInfo(
        role="soc", name="Security Operations Centre",
        mission="Detect fast, triage accurately, classify severity, escalate correctly.",
        description="Consumes control alerts, runs tiered triage, assigns a P-level via the severity "
                    "decision tree, escalates per the matrix, and hunts for persistence."),
    Side.BLUE.value: RoleInfo(
        role="blue", name="Blue Team (Incident Response)",
        mission="Contain, eradicate and recover — preserving evidence and following decision gates.",
        description="Runs the NIST 800-61 lifecycle: identify, contain (memory-first, don't-isolate-DC "
                    "without approval), eradicate persistence, recover safely."),
    Side.MGMT.value: RoleInfo(
        role="mgmt", name="Management / Incident Command",
        mission="Make executive decisions and meet notification & regulatory deadlines.",
        description="Triggered by P-level: notifies CISO/exec, opens the war-room, declares P0, "
                    "activates BCP, and meets regulatory clocks."),
    Side.OT.value: RoleInfo(
        role="ot", name="OT / Operations",
        mission="Protect safety-critical processes; switch to manual; preserve safety.",
        description="Validates OT alerts, coordinates with plant operators, switches to manual "
                    "operations, and isolates the OT segment to protect safety interlocks."),
}


# --------------------------------------------------------------------------- #
#  Workflow definitions (the reusable catalog)
# --------------------------------------------------------------------------- #
def _s(id, kind, label, desc="", phase="", scored=True) -> WorkflowStep:
    return WorkflowStep(id=id, kind=kind, label=label, description=desc, phase_hint=phase, scored=scored)


_WORKFLOWS: dict[str, Workflow] = {}


def _register(wf: Workflow) -> Workflow:
    _WORKFLOWS[wf.id] = wf
    return wf


_register(Workflow(
    actor="red", id="apt_ransomware_killchain", name="APT → Ransomware → OT kill-chain",
    description="Seven-stage adversary kill-chain; each stage applies one or more techniques.",
    steps=[
        _s("red.recon", "recon", "Reconnaissance", "OSINT, identity & service mapping", "Reconnaissance"),
        _s("red.access", "initial_access", "Initial Access", "Phishing → execution → C2 beacon", "Initial Compromise"),
        _s("red.privesc", "priv_esc", "Privilege Escalation", "LSASS, Kerberoast, DCSync → Domain Admin", "Privilege Escalation"),
        _s("red.lateral", "lateral", "Lateral Movement", "RDP/SMB pivot toward sensitive zones", "Lateral Movement"),
        _s("red.persist", "persistence", "Persistence", "Scheduled tasks, services, cloud accounts", "Persistence"),
        _s("red.exfil", "exfil", "Collection & Exfiltration", "Stage, archive, exfil to cloud/DNS", "Data Exfiltration"),
        _s("red.impact", "impact", "Impact & OT", "Ransomware, log clearing, PLC manipulation", "Ransomware"),
    ],
))

_register(Workflow(
    actor="soc", id="tiered_triage_escalation", name="Tiered triage & escalation",
    description="Alert lifecycle: triage → confirm → severity decision gate → escalate → hunt.",
    steps=[
        _s("soc.triage", "triage", "Triage alert", "L1 triage; filter false positives", ""),
        _s("soc.classify", "classify", "Classify severity (P-level)", "Severity decision gate by host/impact", ""),
        _s("soc.escalate", "escalate", "Escalate per matrix", "Hand off to IR / notify SOC lead", ""),
        _s("soc.investigate", "investigate", "L2 investigation", "Pull logs, build process tree, widen scope", ""),
        _s("soc.hunt", "hunt", "Threat hunt", "Hunt persistence & compromised accounts", "Persistence"),
    ],
))

_register(Workflow(
    actor="blue", id="nist_ir_response", name="NIST 800-61 incident response",
    description="Identify → Contain → Eradicate → Recover, with decision gates.",
    steps=[
        _s("blue.identify", "identify", "Identify & scope", "Confirm, scope, capture memory first", ""),
        _s("blue.contain", "contain", "Contain", "Isolate hosts, reset creds, block egress (decision-gated)", ""),
        _s("blue.eradicate", "eradicate", "Eradicate", "Remove persistence, rotate krbtgt ×2, reimage", "Persistence"),
        _s("blue.recover", "recover", "Recover", "Verify clean, restore priority systems", "Ransomware"),
        _s("blue.lessons", "lessons", "Lessons learned", "Produce AAR", "OT Attack"),
    ],
))

_register(Workflow(
    actor="mgmt", id="exec_escalation_regulatory", name="Executive escalation & regulatory",
    description="Decisions and notifications gated on P-level, with modeled deadlines.",
    steps=[
        _s("mgmt.notify_ciso", "notify_ciso", "Notify CISO / open war-room", "On P1 within 30 min", ""),
        _s("mgmt.declare_p0", "declare_p0", "Declare P0 / activate BCP", "On domain breach / ransomware", "Ransomware"),
        _s("mgmt.regulatory", "regulatory", "Regulatory notification", "Breach / critical-infra reporting clocks", "Data Exfiltration"),
        _s("mgmt.comms", "comms", "Public & customer comms", "Coordinated communications (no ransom w/o Legal)", "Ransomware"),
    ],
))

_register(Workflow(
    actor="ot", id="ot_safety_ops", name="OT safety operations",
    description="Protect safety-critical processes when the attack reaches OT.",
    steps=[
        _s("ot.validate", "validate", "Validate OT alerts", "Confirm setpoint deviations are real", "OT Attack"),
        _s("ot.coordinate", "coordinate", "Coordinate with plant operators", "", "OT Attack"),
        _s("ot.manual", "manual_ops", "Switch to manual operations", "Take control off the compromised path", "OT Attack"),
        _s("ot.isolate", "isolate_ot", "Isolate OT segment", "Protect safety interlocks", "OT Attack"),
    ],
))


def get_workflow(workflow_id: str) -> Workflow:
    if workflow_id not in _WORKFLOWS:
        raise KeyError(f"Unknown workflow: {workflow_id}")
    return _WORKFLOWS[workflow_id]


def all_workflows() -> list[Workflow]:
    return [_WORKFLOWS[k] for k in sorted(_WORKFLOWS)]


def workflows_by_actor(actor: str) -> list[Workflow]:
    return [w for w in all_workflows() if w.actor == actor]


def role_catalog() -> list[dict]:
    return [ROLES[r].model_dump() for r in ("red", "soc", "blue", "mgmt", "ot")]


def workflow_catalog() -> list[dict]:
    return [w.model_dump() for w in all_workflows()]


# default bindings used when a scenario doesn't specify them
DEFAULT_BINDINGS: dict[str, str] = {
    "red": "apt_ransomware_killchain",
    "soc": "tiered_triage_escalation",
    "blue": "nist_ir_response",
    "mgmt": "exec_escalation_regulatory",
    "ot": "ot_safety_ops",
}
