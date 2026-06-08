"""Abstract bridge interfaces + data models for VM integration.

Two bridges:
- ExecutionBridge: runs a real attack on a real VM (e.g., Atomic Red Team via WinRM)
- DetectionBridge: queries a real SIEM for alerts (e.g., Wazuh API)

Both are optional. The engine calls them only when an asset has a VMBinding.
Concrete implementations live in separate files (atomic.py, wazuh.py).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from ..catalog.spec import TechniqueSpec
from ..world import AssetInstance


# ---------------------------------------------------------------------------
#  VM Binding — maps a modeled asset to a real VM
# ---------------------------------------------------------------------------
class VMBinding(BaseModel):
    """Optional config on an AssetSpec that maps it to a real VM."""
    host: str                                    # IP or hostname
    port: int = 5986                             # WinRM HTTPS default
    protocol: Literal["winrm", "ssh"] = "winrm"
    username: str = "Administrator"
    password: str = ""                           # or use credential_ref
    credential_ref: str = ""                     # key into a secrets store
    os: Literal["windows", "linux"] = "windows"
    atomic_path: str = ""                        # path to Invoke-AtomicRedTeam on the VM


# ---------------------------------------------------------------------------
#  Execution result
# ---------------------------------------------------------------------------
@dataclass
class ExecutionResult:
    """Result of executing a real attack on a VM."""
    success: bool
    technique_key: str = ""
    mitre_id: str = ""
    output: str = ""                             # stdout from the attack command
    artifacts: list[str] = field(default_factory=list)  # paths to logs, pcaps, screenshots
    duration_ms: int = 0                         # how long the attack took
    error: str | None = None


# ---------------------------------------------------------------------------
#  Detection result
# ---------------------------------------------------------------------------
@dataclass
class DetectionResult:
    """Result of querying a real SIEM/EDR for detection of an attack."""
    detected: bool
    alert_name: str | None = None                # e.g., "Wazuh rule 92652"
    alert_id: str | None = None                  # SIEM alert ID
    source: str | None = None                    # "wazuh", "elastic", "velociraptor"
    mitre_id: str | None = None                  # MITRE technique ID from the alert
    latency_s: float = 0.0                       # seconds from attack to alert
    severity: str | None = None                  # alert severity
    raw: dict | None = None                      # full alert JSON for the report


# ---------------------------------------------------------------------------
#  Abstract bridges
# ---------------------------------------------------------------------------
class ExecutionBridge(abc.ABC):
    """Run a real attack on a real VM."""

    @abc.abstractmethod
    async def execute(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> ExecutionResult:
        """Execute the technique on the target VM. Returns success/failure + output."""
        ...

    @abc.abstractmethod
    async def health_check(self, vm: VMBinding) -> bool:
        """Check if the VM is reachable and ready for attacks."""
        ...

    @abc.abstractmethod
    async def cleanup(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> bool:
        """Clean up artifacts left by the attack (optional, best-effort)."""
        ...


class DetectionBridge(abc.ABC):
    """Query a real SIEM/EDR for alerts after an attack."""

    @abc.abstractmethod
    async def query_detection(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        executed_at_epoch: float,
        window_s: float = 300.0,
    ) -> DetectionResult:
        """Check if the SIEM detected the attack within the time window."""
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Check if the SIEM is reachable."""
        ...
