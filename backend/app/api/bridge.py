"""Bridge API — VM integration status and health checks."""
from __future__ import annotations

from fastapi import APIRouter

from app.engine.bridge.atomic import TECHNIQUE_ATOMICS
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
    }


@router.get("/techniques")
def technique_mappings() -> list[dict]:
    """List all technique-to-Atomic Red Team mappings."""
    return [
        {
            "technique_key": key,
            "mitre_id": info["mitre"],
            "atomic_test": info["test"],
            "has_command": info["command"] is not None,
            "needs_admin": info["needs_admin"],
            "description": info["description"],
        }
        for key, info in TECHNIQUE_ATOMICS.items()
    ]
