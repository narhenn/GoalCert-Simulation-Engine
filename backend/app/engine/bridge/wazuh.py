"""Wazuh detection bridge — queries the Wazuh SIEM for real alerts.

After the engine executes a real attack on a VM, this bridge queries the
Wazuh Indexer API (OpenSearch on port 9200) to check if the SIEM detected
the attack within a configurable time window.

Requirements:
- Wazuh Manager + Indexer running (Docker Compose recommended)
- Wazuh Agent on target VMs with Sysmon forwarding enabled
- Default index pattern: wazuh-alerts-*
"""
from __future__ import annotations

import asyncio
import time

from ..catalog.spec import TechniqueSpec
from ..world import AssetInstance
from .base import DetectionBridge, DetectionResult


class WazuhDetectionBridge(DetectionBridge):
    """Query Wazuh Indexer (OpenSearch) for alerts matching a technique."""

    def __init__(
        self,
        indexer_url: str = "https://localhost:9200",
        username: str = "admin",
        password: str = "admin",
        index_pattern: str = "wazuh-alerts-*",
        verify_ssl: bool = False,
        pipeline_delay_s: float = 60.0,
    ):
        self.indexer_url = indexer_url.rstrip("/")
        self.username = username
        self.password = password
        self.index_pattern = index_pattern
        self.verify_ssl = verify_ssl
        self.pipeline_delay_s = pipeline_delay_s

    async def query_detection(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        executed_at_epoch: float,
        window_s: float = 300.0,
    ) -> DetectionResult:
        # Wait for log pipeline latency (Sysmon -> Wazuh Agent -> Indexer)
        await asyncio.sleep(self.pipeline_delay_s)

        mitre_id = spec.mitre.split("/")[0].strip()  # "T1003.001" from "T1003.001/..."
        agent_name = target.name

        query = {
            "size": 5,
            "sort": [{"@timestamp": {"order": "asc"}}],
            "query": {
                "bool": {
                    "must": [
                        {"range": {
                            "@timestamp": {
                                "gte": int(executed_at_epoch * 1000),
                                "lte": int((executed_at_epoch + window_s) * 1000),
                                "format": "epoch_millis",
                            }
                        }},
                    ],
                    "should": [
                        {"term": {"rule.mitre.id": mitre_id}},
                        {"match": {"rule.mitre.technique": spec.name}},
                    ],
                    "minimum_should_match": 1,
                    "filter": [
                        {"term": {"agent.name": agent_name}},
                    ],
                }
            }
        }

        result = await self._search(query)
        hits = result.get("hits", {}).get("hits", [])

        if hits:
            alert = hits[0]["_source"]
            alert_ts = alert.get("@timestamp", "")
            # Compute detection latency
            try:
                import datetime
                if isinstance(alert_ts, str):
                    dt = datetime.datetime.fromisoformat(alert_ts.replace("Z", "+00:00"))
                    latency = dt.timestamp() - executed_at_epoch
                else:
                    latency = 0.0
            except Exception:
                latency = 0.0

            rule = alert.get("rule", {})
            return DetectionResult(
                detected=True,
                alert_name=rule.get("description", "Wazuh alert"),
                alert_id=rule.get("id"),
                source="wazuh",
                mitre_id=mitre_id,
                latency_s=max(0.0, latency),
                severity=str(rule.get("level", "")),
                raw=alert,
            )

        return DetectionResult(detected=False, source="wazuh", mitre_id=mitre_id)

    async def health_check(self) -> bool:
        try:
            result = await self._get("/_cluster/health")
            return result.get("status") in ("green", "yellow")
        except Exception:
            return False

    async def _search(self, query: dict) -> dict:
        return await self._request("POST", f"/{self.index_pattern}/_search", json=query)

    async def _get(self, path: str) -> dict:
        return await self._request("GET", path)

    async def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        """Make an HTTP request to the Wazuh Indexer."""
        try:
            import httpx
        except ImportError:
            # Fallback to requests (synchronous, wrapped in thread)
            import requests as req  # type: ignore[import-untyped]

            def _do():
                resp = req.request(
                    method, f"{self.indexer_url}{path}",
                    json=json, auth=(self.username, self.password),
                    verify=self.verify_ssl, timeout=30,
                )
                resp.raise_for_status()
                return resp.json()

            return await asyncio.to_thread(_do)

        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            resp = await client.request(
                method, f"{self.indexer_url}{path}",
                json=json, auth=(self.username, self.password),
            )
            resp.raise_for_status()
            return resp.json()
