"""Tests for the VM integration bridge layer.

Verifies: imports, models, registry, technique mappings, backward compatibility,
VM binding propagation, and engine integration (vm_results in summary).
"""
from __future__ import annotations

import copy

from app.engine.bridge.base import (
    DetectionBridge, DetectionResult, ExecutionBridge, ExecutionResult, VMBinding,
)
from app.engine.bridge.atomic import AtomicExecutionBridge, TECHNIQUE_ATOMICS
from app.engine.bridge.registry import get_bridges, register_bridges, vm_enabled
from app.engine.bridge.wazuh import WazuhDetectionBridge
from app.engine.catalog.spec import all_techniques
from app.engine.config import RunConfig
from app.engine.enums import Difficulty
from app.engine.environment import AssetSpec, EnvironmentSpec, VMBindingSpec, build_world
from app.engine.run import run
from app.scenarios.loader import get_seed_scenario


SID = "operation_black_phoenix"


def _scn():
    return get_seed_scenario(SID)


def test_bridge_imports():
    """All bridge modules import cleanly."""
    from app.engine.bridge import (
        ExecutionBridge, DetectionBridge, VMBinding,
        ExecutionResult, DetectionResult, get_bridges, register_bridges,
    )
    assert ExecutionBridge is not None


def test_vm_binding_model():
    """VMBinding and VMBindingSpec are valid Pydantic models."""
    vm = VMBinding(host="10.0.0.5", username="admin", password="pass")
    assert vm.host == "10.0.0.5"
    assert vm.protocol == "winrm"
    assert vm.port == 5986

    spec = VMBindingSpec(host="10.0.0.5")
    assert spec.os == "windows"


def test_execution_result_dataclass():
    r = ExecutionResult(success=True, technique_key="credential_dump", mitre_id="T1003.001",
                        output="LSASS dumped", duration_ms=1200)
    assert r.success
    assert r.duration_ms == 1200


def test_detection_result_dataclass():
    r = DetectionResult(detected=True, alert_name="Wazuh rule 92652", source="wazuh",
                        latency_s=47.3, severity="12")
    assert r.detected
    assert r.latency_s == 47.3


def test_registry_starts_empty():
    """With no bridges registered, vm_enabled() is False."""
    # Reset by importing fresh (registry is module-level global)
    import app.engine.bridge.registry as reg
    reg._execution = None
    reg._detection = None
    assert not reg.vm_enabled()
    ex, det = reg.get_bridges()
    assert ex is None and det is None


def test_registry_register_and_get():
    import app.engine.bridge.registry as reg
    exec_bridge = AtomicExecutionBridge()
    detect_bridge = WazuhDetectionBridge()
    reg.register_bridges(execution=exec_bridge, detection=detect_bridge)
    assert reg.vm_enabled()
    ex, det = reg.get_bridges()
    assert isinstance(ex, AtomicExecutionBridge)
    assert isinstance(det, WazuhDetectionBridge)
    # Clean up
    reg._execution = None
    reg._detection = None


def test_technique_mappings_cover_all_engine_techniques():
    """Every engine technique has an entry in TECHNIQUE_ATOMICS."""
    engine_keys = {t.key for t in all_techniques()}
    mapped_keys = set(TECHNIQUE_ATOMICS.keys())
    # All engine techniques should be mapped (even if command is None for ICS)
    assert engine_keys.issubset(mapped_keys), f"Unmapped: {engine_keys - mapped_keys}"


def test_technique_mappings_have_valid_structure():
    """Every mapping has required fields."""
    for key, info in TECHNIQUE_ATOMICS.items():
        assert "mitre" in info, f"{key} missing mitre"
        assert "command" in info, f"{key} missing command"
        assert "needs_admin" in info, f"{key} missing needs_admin"
        assert "description" in info, f"{key} missing description"
        assert "test" in info, f"{key} missing test"
        assert "cleanup" in info, f"{key} missing cleanup"


def test_ics_techniques_have_no_atomic():
    """OT/ICS techniques (T0866, T0836) should have command=None (no atomic test)."""
    assert TECHNIQUE_ATOMICS["ot_pivot"]["command"] is None
    assert TECHNIQUE_ATOMICS["ot_plc_modify"]["command"] is None


def test_asset_spec_with_vm_binding():
    """AssetSpec accepts an optional VM binding."""
    a = AssetSpec(id="ws-1", type="endpoint",
                  vm=VMBindingSpec(host="192.168.1.50", username="admin", password="P@ss"))
    assert a.vm is not None
    assert a.vm.host == "192.168.1.50"


def test_asset_spec_without_vm_binding():
    """AssetSpec without VM is backward compatible."""
    a = AssetSpec(id="ws-1", type="endpoint")
    assert a.vm is None


def test_vm_binding_propagates_to_asset_instance():
    """VM binding in AssetSpec ends up in AssetInstance.props['vm']."""
    a = AssetSpec(id="ws-1", type="endpoint",
                  vm=VMBindingSpec(host="10.0.0.5", username="admin"))
    env = EnvironmentSpec(assets=[a], controls=[])
    world = build_world(env)
    asset = world.all_assets()[0]
    assert "vm" in asset.props
    assert asset.props["vm"]["host"] == "10.0.0.5"


def test_no_vm_binding_no_vm_in_props():
    """Assets without VM binding don't have 'vm' in props."""
    a = AssetSpec(id="ws-1", type="endpoint")
    env = EnvironmentSpec(assets=[a], controls=[])
    world = build_world(env)
    asset = world.all_assets()[0]
    assert "vm" not in asset.props


def test_existing_scenario_runs_unchanged():
    """Existing precomputed scenarios work exactly as before with no VM bridges."""
    import app.engine.bridge.registry as reg
    reg._execution = None
    reg._detection = None

    s = _scn()
    env = copy.deepcopy(s.recommended_topology)
    r = run(s, env, RunConfig(difficulty=Difficulty.HARD, readiness=60))
    assert r.summary["succeeded"] >= 1
    assert r.scores["red"] > 0
    # No VM results when bridges aren't registered
    assert r.summary.get("vm_enabled") is False
    assert r.summary.get("vm_results") == []


def test_vm_results_populated_when_bridge_registered():
    """When execution bridge is registered and assets have VM bindings, vm_results is populated."""
    import app.engine.bridge.registry as reg
    reg._execution = AtomicExecutionBridge()
    reg._detection = None

    s = _scn()
    env = copy.deepcopy(s.recommended_topology)
    # Add VM binding to the first endpoint
    for a in env.assets:
        if a.type == "endpoint" and a.vm is None:
            a.vm = VMBindingSpec(host="10.0.0.99", username="test")
            break

    r = run(s, env, RunConfig(difficulty=Difficulty.HARD, readiness=60))
    vm_results = r.summary.get("vm_results", [])
    # At least some attacks should have targeted the VM-bound endpoint
    assert len(vm_results) >= 1, "Expected VM results for the bound endpoint"
    for vr in vm_results:
        assert vr["mode"] == "real_vm"
        assert vr["vm_host"] == "10.0.0.99"
        assert "technique" in vr
        assert "mitre" in vr

    # Clean up
    reg._execution = None
    reg._detection = None
