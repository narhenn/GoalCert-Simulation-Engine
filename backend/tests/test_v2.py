"""v2 tests: role lens purity, multi-actor scoring, task events, phase drills, decision gates."""
from __future__ import annotations

import copy

from app.engine.config import RunConfig, WorkflowConfig
from app.engine.enums import Difficulty, EventType, Side
from app.engine.environment import EnvironmentSpec
from app.engine.run import run
from app.engine.scenario import Scenario
from app.scenarios.loader import get_seed_scenario

SID = "operation_black_phoenix"


def _scn() -> Scenario:
    s = get_seed_scenario(SID)
    assert s is not None
    return s


def _env(default: bool = True) -> EnvironmentSpec:
    env = copy.deepcopy(_scn().recommended_topology)
    for c in env.controls:
        c.enabled = default
    return env


def test_focus_role_is_a_pure_lens():
    """Switching the focus role must not change the underlying timeline or scores."""
    s = _scn()
    env = _env(True)
    red_view = run(s, copy.deepcopy(env), RunConfig(difficulty=Difficulty.HARD, readiness=55, focus_role=Side.RED))
    blue_view = run(s, copy.deepcopy(env), RunConfig(difficulty=Difficulty.HARD, readiness=55, focus_role=Side.BLUE))
    assert [e.model_dump() for e in red_view.events] == [e.model_dump() for e in blue_view.events]
    assert red_view.scores == blue_view.scores
    assert red_view.focus_role == "red" and blue_view.focus_role == "blue"


def test_all_teams_score_and_emit_tasks():
    s = _scn()
    r = run(s, _env(True), RunConfig(difficulty=Difficulty.EXPERT, readiness=55, focus_role=Side.BLUE))
    # every team has a score entry; defenders actually score under a strong posture
    for role in ("red", "blue", "soc", "mgmt", "ot"):
        assert role in r.scores
    assert r.scores["soc"] > 0 and r.scores["blue"] > 0
    # task-status events drive the per-role sub-reports
    task_actors = {e.side.value for e in r.events if e.type == EventType.TASK}
    assert {"red", "soc", "blue"}.issubset(task_actors)
    # role_tasks snapshot has SOC steps marked done
    soc_done = [t for t in r.role_tasks["soc"] if t["status"] == "done"]
    assert len(soc_done) >= 2


def test_escalation_decision_and_notify_events():
    s = _scn()
    r = run(s, _env(True), RunConfig(difficulty=Difficulty.EXPERT, readiness=55))
    types = {e.type for e in r.events}
    assert EventType.ESCALATION in types          # SOC classified a P-level
    assert EventType.NOTIFY in types              # management notified
    assert EventType.DECISION in types            # isolate-DC decision gate fired
    # KPIs include the SOC/Blue clock metrics
    for k in ("mtta_s", "mttc_s", "escalation_accuracy", "hunt_success"):
        assert k in r.kpis


def test_phase_range_drill_runs_a_single_phase():
    s = _scn()
    # Phase 3 = Privilege Escalation drill
    r = run(s, _env(True), RunConfig(difficulty=Difficulty.HARD, readiness=60, phase_range=(3, 3)))
    phases = {e.phase for e in r.events if e.type == EventType.PHASE}
    assert phases == {"Privilege Escalation"}
    # priming gave the attacker a foothold so the drill is meaningful
    assert r.summary["succeeded"] >= 1


def test_per_team_scenarios_seeded():
    for sid in ("operation_black_phoenix_red", "operation_black_phoenix_soc",
                "operation_black_phoenix_blue"):
        assert get_seed_scenario(sid) is not None


# --------------------------------------------------------------------------- #
#  Workflow customization mechanically changes outcomes (the core requirement)
# --------------------------------------------------------------------------- #
def _wc(**teams) -> WorkflowConfig:
    return WorkflowConfig(enabled=teams)


def test_block_egress_task_stops_exfiltration():
    s = _scn()
    base = dict(difficulty=Difficulty.EXPERT, readiness=50)
    # controls off so only the Blue task decides; SOC off so containment doesn't interfere
    on = run(s, _env(False), RunConfig(**base, workflow_config=_wc(soc=[], blue=["blue.block_egress"], ot=[], mgmt=[])))
    off = run(s, _env(False), RunConfig(**base, workflow_config=_wc(soc=[], blue=[], ot=[], mgmt=[])))
    assert on.summary["exfiltrated"] is False     # egress blocked first
    assert off.summary["exfiltrated"] is True      # no egress control -> data leaves


def test_segmentation_task_protects_ot():
    s = _scn()
    base = dict(difficulty=Difficulty.EXPERT, readiness=50)
    seg = run(s, _env(False), RunConfig(**base, workflow_config=_wc(soc=[], blue=["blue.segmentation"], ot=[], mgmt=[])))
    noseg = run(s, _env(False), RunConfig(**base, workflow_config=_wc(soc=[], blue=[], ot=[], mgmt=[])))
    assert seg.summary["ot_impact"] is False       # IT/OT segmentation blocks the pivot
    assert noseg.summary["ot_impact"] is True


def test_red_evasion_slows_detection():
    s = _scn()
    base = dict(difficulty=Difficulty.HARD, readiness=60)
    core = ["red.recon", "red.access", "red.privesc", "red.persist", "red.lateral", "red.exfil", "red.impact"]
    evade = run(s, _env(True), RunConfig(**base))                                  # red defaults incl evasion
    plain = run(s, _env(True), RunConfig(**base, workflow_config=_wc(red=core)))   # evasion stripped
    assert evade.kpis["mttd_s"] > plain.kpis["mttd_s"]   # evasion increases dwell time


def test_eradication_task_prevents_persistence_reestablish():
    s = _scn()
    base = dict(difficulty=Difficulty.EXPERT, readiness=60)
    blue_no_erad = ["blue.identify", "blue.edr_contain", "blue.lessons"]
    blue_erad = blue_no_erad + ["blue.eradicate", "blue.krbtgt"]
    no_erad = run(s, _env(True), RunConfig(**base, workflow_config=_wc(blue=blue_no_erad)))
    erad = run(s, _env(True), RunConfig(**base, workflow_config=_wc(blue=blue_erad)))
    reestablished = lambda r: any("re-established" in e.message for e in r.events)  # noqa: E731
    assert reestablished(no_erad) is True       # persistence survives containment
    assert reestablished(erad) is False         # eradication defeats it


def test_workflow_config_filters_tasks_and_is_deterministic():
    s = _scn()
    env = _env(True)
    cfg = RunConfig(difficulty=Difficulty.HARD, readiness=55,
                    workflow_config=_wc(blue=["blue.identify", "blue.edr_contain", "blue.lessons"]))
    r1 = run(s, copy.deepcopy(env), cfg)
    r2 = run(s, copy.deepcopy(env), cfg.model_copy(deep=True))
    assert [e.model_dump() for e in r1.events] == [e.model_dump() for e in r2.events]
    blue_wf = next(w for w in r1.workflows if w["actor"] == "blue")
    assert {st["id"] for st in blue_wf["steps"]} == {"blue.identify", "blue.edr_contain", "blue.lessons"}
    assert {t["id"] for t in r1.role_tasks["blue"]} == {"blue.identify", "blue.edr_contain", "blue.lessons"}
