"""MITRE Caldera execution bridge — orchestrates attacks via Caldera REST API.

Instead of running individual commands via WinRM, this bridge:
1. Finds Caldera abilities matching the engine technique
2. Creates a single-ability adversary profile
3. Launches a Caldera operation targeting agents on the asset's host
4. Polls until complete
5. Returns the result

Requirements:
- Caldera server running (Docker or standalone)
- Sandcat agent deployed on target VM and connected to Caldera
- `requests` Python package
"""
from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass

try:  # optional dep — the Caldera bridge is only used when an operator wires it up
    import requests
except ImportError:  # pragma: no cover - keeps the whole app importable without it
    requests = None  # type: ignore[assignment]

from ..catalog.spec import TechniqueSpec
from ..world import AssetInstance
from .base import DetectionBridge, ExecutionBridge, ExecutionResult, VMBinding

# Caldera technique_id mapping — engine key → MITRE ATT&CK ID
# (Caldera uses ATT&CK IDs to tag abilities)
TECHNIQUE_MITRE: dict[str, str] = {
    "phishing": "T1566.001",
    "exploit_public": "T1190",
    "lsass_dump": "T1003.001",
    "kerberoast": "T1558.003",
    "dcsync": "T1003.006",
    "lateral_wmi": "T1047",
    "lateral_psexec": "T1569.002",
    "lateral_rdp": "T1021.001",
    "persist_task": "T1053.005",
    "persist_reg": "T1547.001",
    "exfil_http": "T1048.003",
    "ransomware": "T1486",
    "defense_evasion": "T1562.001",
    "discovery_ad": "T1087.002",
}


@dataclass
class CalderaConfig:
    """Connection config for a Caldera server."""
    base_url: str = "http://localhost:8888"
    api_key: str = "ADMIN123"
    agent_group: str = "red"
    poll_interval_s: float = 3.0
    timeout_s: float = 300.0


class CalderaExecutionBridge(ExecutionBridge):
    """Execute attacks via MITRE Caldera's REST API."""

    def __init__(self, config: CalderaConfig | None = None):
        self.config = config or CalderaConfig()
        self._headers = {
            "KEY": self.config.api_key,
            "Content-Type": "application/json",
        }
        self._base = self.config.base_url.rstrip("/")

    def _api(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self._base}/api/v2{path}"
        resp = requests.request(method, url, headers=self._headers, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    # --- ExecutionBridge interface ---

    def _execute_sync(self, spec: TechniqueSpec, vm: VMBinding) -> ExecutionResult:
        """Synchronous execution — called via asyncio.to_thread from execute()."""
        if requests is None:
            return ExecutionResult(
                success=False, technique_key=spec.key,
                error="Caldera bridge requires the 'requests' package (pip install requests)",
            )
        mitre_id = TECHNIQUE_MITRE.get(spec.key, spec.mitre)
        if not mitre_id:
            return ExecutionResult(
                success=False, technique_key=spec.key,
                error=f"No MITRE ID mapping for technique {spec.key}",
            )

        try:
            # 1. Find abilities for this technique
            abilities = self._find_abilities(mitre_id, platform="windows")
            if not abilities:
                return ExecutionResult(
                    success=False, technique_key=spec.key, mitre_id=mitre_id,
                    error=f"No Caldera abilities found for {mitre_id}",
                )

            # 2. Check for alive agents
            agents = self._get_agents()
            if not agents:
                return ExecutionResult(
                    success=False, technique_key=spec.key, mitre_id=mitre_id,
                    error="No alive Caldera agents",
                )

            # 3. Create adversary with first matching ability
            ability_id = abilities[0]["ability_id"]
            adversary = self._create_adversary(
                name=f"GC-{spec.key}-{int(time.time())}",
                ability_ids=[ability_id],
            )

            # 4. Launch operation
            operation = self._create_operation(
                name=f"GC-{spec.key}",
                adversary_id=adversary["adversary_id"],
            )
            op_id = operation["id"]

            # 5. Poll until finished
            start = time.time()
            while time.time() - start < self.config.timeout_s:
                status = self._api("GET", f"/operations/{op_id}").json()
                if status.get("state") == "finished":
                    break
                time.sleep(self.config.poll_interval_s)
            else:
                return ExecutionResult(
                    success=False, technique_key=spec.key, mitre_id=mitre_id,
                    error=f"Operation {op_id} timed out after {self.config.timeout_s}s",
                )

            # 6. Collect results
            links = self._api("GET", f"/operations/{op_id}/links").json()
            duration_ms = int((time.time() - start) * 1000)

            success = any(link.get("status") == -3 for link in links)  # -3 = collected
            output_parts = []
            for link in links:
                if link.get("status") == -3:
                    try:
                        raw = self._api(
                            "GET",
                            f"/operations/{op_id}/links/{link['id']}/result",
                        ).json()
                        decoded = base64.b64decode(
                            raw.get("result", "")
                        ).decode("utf-8", errors="replace")
                        output_parts.append(decoded)
                    except Exception:
                        output_parts.append("[could not decode output]")

            return ExecutionResult(
                success=success,
                technique_key=spec.key,
                mitre_id=mitre_id,
                output="\n".join(output_parts)[:2000],
                duration_ms=duration_ms,
            )

        except requests.RequestException as exc:
            return ExecutionResult(
                success=False, technique_key=spec.key, mitre_id=mitre_id,
                error=f"Caldera API error: {exc}",
            )

    async def execute(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> ExecutionResult:
        """Async wrapper — runs blocking Caldera calls in a thread."""
        return await asyncio.to_thread(self._execute_sync, spec, vm)

    async def health_check(self, vm: VMBinding) -> bool:
        if requests is None:
            return False
        try:
            resp = requests.get(
                f"{self._base}/api/v2/health",
                headers=self._headers, timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def cleanup(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        vm: VMBinding,
    ) -> bool:
        # Caldera handles cleanup via ability cleanup commands
        return True

    # --- Caldera API helpers ---

    def _find_abilities(self, technique_id: str, platform: str = "windows") -> list[dict]:
        all_abilities = self._api("GET", "/abilities").json()
        matched = []
        for a in all_abilities:
            if a.get("technique_id") != technique_id:
                continue
            executors = a.get("executors", [])
            for ex in executors:
                if ex.get("platform") == platform or platform in ex.get("platform", ""):
                    matched.append(a)
                    break
        return matched

    def _get_agents(self) -> list[dict]:
        agents = self._api("GET", "/agents").json()
        return [a for a in agents if a.get("group") == self.config.agent_group]

    def _create_adversary(self, name: str, ability_ids: list[str]) -> dict:
        return self._api("POST", "/adversaries", json={
            "name": name,
            "description": f"Auto-generated by GoalCert",
            "atomic_ordering": ability_ids,
        }).json()

    def _create_operation(self, name: str, adversary_id: str) -> dict:
        return self._api("POST", "/operations", json={
            "name": name,
            "adversary": {"adversary_id": adversary_id},
            "planner": {"id": "aaa7c857-37a0-4c4a-85f7-4e9f7f30e31a"},
            "source": {"id": "ed32b9c3-9593-4c33-b0db-e2007315096b"},
            "group": self.config.agent_group,
            "auto_close": True,
            "obfuscator": "plain-text",
            "jitter": "2/8",
        }).json()

    def get_operation_report(self, operation_id: str) -> dict:
        """Get full Caldera operation report (for GoalCert AAR integration)."""
        return self._api("POST", f"/operations/{operation_id}/report", json={
            "enable_agent_output": True,
        }).json()
