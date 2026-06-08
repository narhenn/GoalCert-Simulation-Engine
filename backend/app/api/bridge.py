"""Bridge API — VM integration status and health checks."""
from __future__ import annotations

from fastapi import APIRouter

from app.engine.bridge.atomic import TECHNIQUE_ATOMICS
from app.engine.bridge.caldera import TECHNIQUE_MITRE as CALDERA_TECHNIQUES
from app.engine.bridge.kali import TECHNIQUE_KALI
from app.engine.bridge.native import TECHNIQUE_NATIVE
from app.engine.bridge.sysmon import DETECTION_RULES, SysmonDetectionBridge
from app.engine.bridge.registry import get_bridges, vm_enabled

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


@router.get("/status")
def bridge_status() -> dict:
    """Check if VM integration is active and which bridges are registered."""
    exec_bridge, detect_bridge = get_bridges()
    return {
        "vm_enabled": vm_enabled(),
        "execution_bridge": type(exec_bridge).__name__ if exec_bridge else None,
        "detection_bridge": type(detect_bridge).__name__ if detect_bridge else None,
        "techniques_atomic": len(TECHNIQUE_ATOMICS),
        "techniques_caldera": len(CALDERA_TECHNIQUES),
        "techniques_kali": len(TECHNIQUE_KALI),
        "techniques_native": len(TECHNIQUE_NATIVE),
        "detection_rules": len(DETECTION_RULES),
    }


@router.get("/detections")
def detection_rules() -> list[dict]:
    """List all Sysmon detection rules (replaces Wazuh)."""
    return SysmonDetectionBridge.get_detection_coverage()


@router.get("/techniques")
def technique_mappings() -> list[dict]:
    """List all technique mappings across all bridges."""
    all_keys = set(TECHNIQUE_ATOMICS.keys()) | set(CALDERA_TECHNIQUES.keys()) | set(TECHNIQUE_KALI.keys()) | set(TECHNIQUE_NATIVE.keys())
    results = []
    for key in sorted(all_keys):
        atomic = TECHNIQUE_ATOMICS.get(key)
        caldera = CALDERA_TECHNIQUES.get(key)
        kali = TECHNIQUE_KALI.get(key)
        native = TECHNIQUE_NATIVE.get(key)
        results.append({
            "technique_key": key,
            "mitre_id": (atomic or {}).get("mitre", caldera or ""),
            "bridges": {
                "atomic": bool(atomic),
                "caldera": bool(caldera),
                "kali": bool(kali),
                "native": bool(native),
            },
            "tool": (native or kali or {}).get("tool"),
            "description": (kali or atomic or {}).get("description", ""),
        })
    return results
