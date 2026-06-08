"""VM bridge — optional real-infrastructure execution and detection.

When an asset has a VM binding, the engine delegates attack execution to a real VM
and detection verification to a real SIEM, instead of using the modeled resolution.
If no VM binding exists, the engine falls back to the existing deterministic model.
"""
from .base import DetectionBridge, DetectionResult, ExecutionBridge, ExecutionResult, VMBinding
from .registry import get_bridges, register_bridges
from .caldera import CalderaConfig, CalderaExecutionBridge
from .kali import KaliExecutionBridge
from .native import NativeExecutionBridge
from .sysmon import SysmonDetectionBridge

__all__ = [
    "ExecutionBridge", "ExecutionResult",
    "DetectionBridge", "DetectionResult",
    "VMBinding",
    "get_bridges", "register_bridges",
    "CalderaExecutionBridge", "CalderaConfig",
    "KaliExecutionBridge",
    "NativeExecutionBridge",
    "SysmonDetectionBridge",
]
