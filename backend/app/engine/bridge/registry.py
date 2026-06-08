"""Bridge registry — global singleton for the execution and detection bridges.

The engine calls get_bridges() to check if VM integration is active.
If no bridges are registered, the engine falls back to the model (zero impact).
Register bridges at startup via settings or environment variables.
"""
from __future__ import annotations

from .base import DetectionBridge, ExecutionBridge

_execution: ExecutionBridge | None = None
_detection: DetectionBridge | None = None


def register_bridges(
    execution: ExecutionBridge | None = None,
    detection: DetectionBridge | None = None,
) -> None:
    """Register the execution and/or detection bridges globally."""
    global _execution, _detection
    if execution is not None:
        _execution = execution
    if detection is not None:
        _detection = detection


def get_bridges() -> tuple[ExecutionBridge | None, DetectionBridge | None]:
    """Get the current bridges. Returns (None, None) if VM integration is off."""
    return _execution, _detection


def vm_enabled() -> bool:
    """True if at least the execution bridge is registered."""
    return _execution is not None
