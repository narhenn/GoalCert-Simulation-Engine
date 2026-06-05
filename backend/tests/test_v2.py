"""v2 tests: role lens purity, multi-actor scoring, task events, phase drills, decision gates."""
from __future__ import annotations

import copy

from app.engine.config import RunConfig
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
