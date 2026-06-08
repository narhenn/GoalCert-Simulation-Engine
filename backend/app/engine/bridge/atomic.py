"""Atomic Red Team execution bridge — runs real attacks on real VMs.

Uses pywinrm (Windows) or paramiko (Linux) to execute Invoke-AtomicTest
commands on target VMs. Each engine technique key maps to one or more
Atomic Red Team test GUIDs.

Requirements on target VM:
- Windows: PowerShell 5.1+, Invoke-AtomicRedTeam installed, WinRM enabled
- Linux: SSH access, atomic-operator or bash atomics

Install on target: IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/
invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing);
Install-AtomicRedTeam -getAtomics
"""
from __future__ import annotations

import asyncio
import time

from ..catalog.spec import TechniqueSpec
from ..world import AssetInstance
from .base import ExecutionBridge, ExecutionResult, VMBinding


# ---------------------------------------------------------------------------
#  Engine technique key -> Atomic Red Team test mapping
# ---------------------------------------------------------------------------
TECHNIQUE_ATOMICS: dict[str, dict] = {
    "recon_osint": {
        "mitre": "T1595",
        "test": "T1595.002",
        "command": "Invoke-AtomicTest T1595.002 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1595.002 -Cleanup",
        "needs_admin": False,
        "description": "Active scanning / port scan simulation",
    },
    "phishing": {
        "mitre": "T1566.001",
        "test": "T1566.001-1",
        "command": "Invoke-AtomicTest T1566.001 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1566.001 -TestNumbers 1 -Cleanup",
        "needs_admin": False,
        "description": "Download phishing attachment simulation",
    },
    "c2_beacon": {
        "mitre": "T1071.001",
        "test": "T1071.001-1",
        "command": "Invoke-AtomicTest T1071.001 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1071.001 -TestNumbers 1 -Cleanup",
        "needs_admin": False,
        "description": "HTTP C2 beacon simulation",
    },
    "credential_dump": {
        "mitre": "T1003.001",
        "test": "T1003.001-2",
        "command": "Invoke-AtomicTest T1003.001 -TestNumbers 2 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1003.001 -TestNumbers 2 -Cleanup",
        "needs_admin": True,
        "description": "LSASS dump via comsvcs.dll MiniDump",
    },
    "kerberoasting": {
        "mitre": "T1558.003",
        "test": "T1558.003-1",
        "command": "Invoke-AtomicTest T1558.003 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1558.003 -TestNumbers 1 -Cleanup",
        "needs_admin": False,
        "description": "Kerberoasting via Rubeus",
    },
    "dcsync_domain_admin": {
        "mitre": "T1003.006",
        "test": "T1003.006-1",
        "command": "Invoke-AtomicTest T1003.006 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1003.006 -TestNumbers 1 -Cleanup",
        "needs_admin": True,
        "description": "DCSync via Mimikatz",
    },
    "lateral_movement": {
        "mitre": "T1021.002",
        "test": "T1021.002-1",
        "command": "Invoke-AtomicTest T1021.002 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1021.002 -TestNumbers 1 -Cleanup",
        "needs_admin": True,
        "description": "Lateral movement via SMB/Admin shares",
    },
    "persistence_task": {
        "mitre": "T1053.005",
        "test": "T1053.005-1",
        "command": "Invoke-AtomicTest T1053.005 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1053.005 -TestNumbers 1 -Cleanup",
        "needs_admin": True,
        "description": "Scheduled task persistence",
    },
    "cloud_persistence": {
        "mitre": "T1136.003",
        "test": "T1136.003-1",
        "command": "Invoke-AtomicTest T1136.003 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1136.003 -TestNumbers 1 -Cleanup",
        "needs_admin": False,
        "description": "Cloud account persistence",
    },
    "collection_staging": {
        "mitre": "T1074.001",
        "test": "T1074.001-1",
        "command": "Invoke-AtomicTest T1074.001 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1074.001 -TestNumbers 1 -Cleanup",
        "needs_admin": False,
        "description": "Data staging to local directory",
    },
    "exfiltration": {
        "mitre": "T1567.002",
        "test": "T1567.002-1",
        "command": "Invoke-AtomicTest T1567.002 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1567.002 -TestNumbers 1 -Cleanup",
        "needs_admin": False,
        "description": "Exfiltration to cloud storage simulation",
    },
    "disable_security_tools": {
        "mitre": "T1562.001",
        "test": "T1562.001-1",
        "command": "Invoke-AtomicTest T1562.001 -TestNumbers 1 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1562.001 -TestNumbers 1 -Cleanup",
        "needs_admin": True,
        "description": "Disable security tools / tamper protection",
    },
    "ransomware": {
        "mitre": "T1486",
        "test": "T1486-2",
        # Test #2: 7z encryption of test files (SAFE — only encrypts canary files)
        "command": "Invoke-AtomicTest T1486 -TestNumbers 2 -Confirm:$false",
        "cleanup": "Invoke-AtomicTest T1486 -TestNumbers 2 -Cleanup",
        "needs_admin": False,
        "description": "Ransomware simulation (7z encrypt canary files — SAFE)",
    },
    "ot_pivot": {
        "mitre": "T0866",
        "test": None,  # No Atomic Red Team test for ICS techniques
        "command": None,
        "cleanup": None,
        "needs_admin": True,
        "description": "IT/OT pivot — no atomic test available, uses model",
    },
    "ot_plc_modify": {
        "mitre": "T0836",
        "test": None,
        "command": None,
        "cleanup": None,
        "needs_admin": True,
        "description": "PLC modification — no atomic test available, uses model",
    },
}


class AtomicExecutionBridge(ExecutionBridge):
    """Execute Atomic Red Team tests on VMs via WinRM or SSH."""

    async def execute(
        self, spec: TechniqueSpec, target: AssetInstance, vm: VMBinding,
    ) -> ExecutionResult:
        mapping = TECHNIQUE_ATOMICS.get(spec.key)
        if mapping is None or mapping.get("command") is None:
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=spec.mitre,
                error=f"no_atomic_mapping:{spec.key}",
            )

        command = mapping["command"]
        start = time.time()

        if vm.protocol == "winrm":
            result = await self._run_winrm(vm, command)
        else:
            result = await self._run_ssh(vm, command)

        elapsed = int((time.time() - start) * 1000)
        return ExecutionResult(
            success=result["success"],
            technique_key=spec.key,
            mitre_id=spec.mitre,
            output=result["output"],
            duration_ms=elapsed,
            error=result.get("error"),
        )

    async def health_check(self, vm: VMBinding) -> bool:
        if vm.protocol == "winrm":
            result = await self._run_winrm(vm, "hostname")
        else:
            result = await self._run_ssh(vm, "hostname")
        return result["success"]

    async def cleanup(
        self, spec: TechniqueSpec, target: AssetInstance, vm: VMBinding,
    ) -> bool:
        mapping = TECHNIQUE_ATOMICS.get(spec.key)
        if mapping is None or mapping.get("cleanup") is None:
            return True
        if vm.protocol == "winrm":
            result = await self._run_winrm(vm, mapping["cleanup"])
        else:
            result = await self._run_ssh(vm, mapping["cleanup"])
        return result["success"]

    # --- transport implementations ---

    async def _run_winrm(self, vm: VMBinding, command: str) -> dict:
        """Execute a PowerShell command on a Windows VM via WinRM."""
        try:
            import winrm  # type: ignore[import-untyped]
        except ImportError:
            return {"success": False, "output": "", "error": "pywinrm not installed (pip install pywinrm)"}

        def _do():
            try:
                url = f"https://{vm.host}:{vm.port}/wsman"
                session = winrm.Session(
                    url,
                    auth=(vm.username, vm.password),
                    transport="ntlm",
                    server_cert_validation="ignore",
                )
                result = session.run_ps(command)
                return {
                    "success": result.status_code == 0,
                    "output": result.std_out.decode("utf-8", errors="replace"),
                    "error": result.std_err.decode("utf-8", errors="replace") if result.status_code != 0 else None,
                }
            except Exception as e:
                return {"success": False, "output": "", "error": str(e)}

        return await asyncio.to_thread(_do)

    async def _run_ssh(self, vm: VMBinding, command: str) -> dict:
        """Execute a command on a Linux VM via SSH."""
        try:
            import paramiko  # type: ignore[import-untyped]
        except ImportError:
            return {"success": False, "output": "", "error": "paramiko not installed (pip install paramiko)"}

        def _do():
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(
                    vm.host, port=vm.port if vm.port != 5986 else 22,
                    username=vm.username, password=vm.password,
                    timeout=30,
                )
                _, stdout, stderr = client.exec_command(command, timeout=120)
                exit_code = stdout.channel.recv_exit_status()
                output = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
                client.close()
                return {
                    "success": exit_code == 0,
                    "output": output,
                    "error": err if exit_code != 0 else None,
                }
            except Exception as e:
                return {"success": False, "output": "", "error": str(e)}

        return await asyncio.to_thread(_do)
