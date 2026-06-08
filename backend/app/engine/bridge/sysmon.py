"""Sysmon detection bridge — reads Windows Event Logs directly, no SIEM needed.

Replaces Wazuh (4GB RAM) with a ~30MB Python service that:
1. Queries Sysmon events from the Windows Event Log via subprocess (wevtutil)
2. Matches events against MITRE ATT&CK technique patterns
3. Returns detection results to the engine

Works on Windows only (where Sysmon runs). On non-Windows, returns
"not available" gracefully so existing tests don't break.

Requirements:
- Sysmon installed and running on Windows
- No Docker, no SIEM, no external services
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from ..catalog.spec import TechniqueSpec
from ..world import AssetInstance
from .base import DetectionBridge, DetectionResult

IS_WINDOWS = sys.platform == "win32"

# Sysmon Event ID reference:
# 1  = Process Creation
# 3  = Network Connection
# 7  = Image Loaded
# 8  = CreateRemoteThread
# 10 = ProcessAccess
# 11 = FileCreate
# 12 = RegistryEvent (Object create/delete)
# 13 = RegistryEvent (Value Set)
# 15 = FileCreateStreamHash
# 22 = DNSEvent
# 23 = FileDelete

# MITRE technique → Sysmon detection rule
# Each rule: event_id to look for + field patterns to match
DETECTION_RULES: dict[str, dict] = {
    "T1003.001": {
        "name": "LSASS Memory Access",
        "event_ids": [10],
        "match": lambda e: "lsass.exe" in e.get("TargetImage", "").lower(),
        "severity": "critical",
    },
    "T1558.003": {
        "name": "Kerberoasting — TGS Request",
        "event_ids": [1],
        "match": lambda e: (
            "rubeus" in e.get("CommandLine", "").lower()
            or "getuserspns" in e.get("CommandLine", "").lower()
            or "invoke-kerberoast" in e.get("CommandLine", "").lower()
        ),
        "severity": "high",
    },
    "T1003.006": {
        "name": "DCSync — DRSUAPI Replication",
        "event_ids": [1, 3],
        "match": lambda e: (
            "secretsdump" in e.get("CommandLine", "").lower()
            or "dcsync" in e.get("CommandLine", "").lower()
            or "drsuapi" in e.get("Image", "").lower()
        ),
        "severity": "critical",
    },
    "T1047": {
        "name": "WMI Remote Execution",
        "event_ids": [1],
        "match": lambda e: (
            "wmiexec" in e.get("CommandLine", "").lower()
            or ("wmiprvse.exe" in e.get("ParentImage", "").lower()
                and e.get("Image", "").lower().endswith("cmd.exe"))
        ),
        "severity": "high",
    },
    "T1569.002": {
        "name": "PsExec Service Execution",
        "event_ids": [1],
        "match": lambda e: (
            "psexec" in e.get("CommandLine", "").lower()
            or "psexesvc" in e.get("Image", "").lower()
        ),
        "severity": "high",
    },
    "T1053.005": {
        "name": "Scheduled Task Created",
        "event_ids": [1],
        "match": lambda e: (
            "schtasks" in e.get("Image", "").lower()
            and "/create" in e.get("CommandLine", "").lower()
        ),
        "severity": "medium",
    },
    "T1547.001": {
        "name": "Registry Run Key Modified",
        "event_ids": [13],
        "match": lambda e: "currentversion\\run" in e.get("TargetObject", "").lower(),
        "severity": "high",
    },
    "T1566.001": {
        "name": "Suspicious Office Macro Execution",
        "event_ids": [1],
        "match": lambda e: (
            e.get("ParentImage", "").lower().endswith(("winword.exe", "excel.exe", "powerpnt.exe"))
            and e.get("Image", "").lower().endswith(("cmd.exe", "powershell.exe", "wscript.exe", "mshta.exe"))
        ),
        "severity": "high",
    },
    "T1562.001": {
        "name": "Security Tool Disabled",
        "event_ids": [1, 13],
        "match": lambda e: (
            "disable" in e.get("CommandLine", "").lower()
            and ("defender" in e.get("CommandLine", "").lower()
                 or "tamperprotection" in e.get("TargetObject", "").lower())
        ),
        "severity": "critical",
    },
    "T1087.002": {
        "name": "AD User Enumeration",
        "event_ids": [1],
        "match": lambda e: (
            ("net.exe" in e.get("Image", "").lower() and "user" in e.get("CommandLine", "").lower()
             and "/domain" in e.get("CommandLine", "").lower())
            or "nxc" in e.get("Image", "").lower()
            or "crackmapexec" in e.get("Image", "").lower()
        ),
        "severity": "medium",
    },
    "T1048.003": {
        "name": "Data Exfiltration over HTTP",
        "event_ids": [3],
        "match": lambda e: (
            e.get("DestinationPort", "") in ("80", "443", "8080")
            and e.get("Initiated", "").lower() == "true"
        ),
        "severity": "medium",
    },
    "T1486": {
        "name": "File Encryption (Ransomware Indicator)",
        "event_ids": [11, 23],
        "match": lambda e: (
            e.get("TargetFilename", "").endswith((".enc", ".locked", ".encrypted", ".crypto"))
        ),
        "severity": "critical",
    },
    "T1021.001": {
        "name": "RDP Connection",
        "event_ids": [3],
        "match": lambda e: e.get("DestinationPort", "") == "3389",
        "severity": "low",
    },
    "T1190": {
        "name": "Exploit Public-Facing Application",
        "event_ids": [1, 3],
        "match": lambda e: (
            "msfconsole" in e.get("CommandLine", "").lower()
            or "metasploit" in e.get("CommandLine", "").lower()
        ),
        "severity": "critical",
    },
}


def _query_sysmon_events(seconds_back: int = 300, max_events: int = 500) -> list[dict]:
    """Query recent Sysmon events from Windows Event Log via wevtutil."""
    if not IS_WINDOWS:
        return []

    # Build XPath query for events in the time window
    # wevtutil uses milliseconds for TimeCreated timediff
    ms = seconds_back * 1000
    xpath = f"*[System[TimeCreated[timediff(@SystemTime) <= {ms}]]]"

    try:
        result = subprocess.run(
            ["wevtutil", "qe", "Microsoft-Windows-Sysmon/Operational",
             "/q:" + xpath, f"/c:{max_events}", "/f:xml", "/rd:true"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return []

        # Parse XML events
        events = []
        raw = "<Events>" + result.stdout + "</Events>"
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            # wevtutil output may have encoding issues, try wrapping differently
            return []

        ns = {
            "e": "http://schemas.microsoft.com/win/2004/08/events/event",
            "s": "http://schemas.microsoft.com/win/2004/08/events/event",
        }

        for event_el in root:
            ev = {}
            # System data
            sys_el = event_el.find("e:System", ns)
            if sys_el is not None:
                eid_el = sys_el.find("e:EventID", ns)
                ev["EventID"] = int(eid_el.text) if eid_el is not None and eid_el.text else 0
                time_el = sys_el.find("e:TimeCreated", ns)
                ev["TimeCreated"] = time_el.get("SystemTime", "") if time_el is not None else ""

            # EventData
            data_el = event_el.find("e:EventData", ns)
            if data_el is not None:
                for d in data_el:
                    name = d.get("Name", "")
                    if name:
                        ev[name] = d.text or ""

            if ev.get("EventID"):
                events.append(ev)

        return events

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


class SysmonDetectionBridge(DetectionBridge):
    """Query local Sysmon event logs for attack detection. No SIEM needed."""

    def __init__(self, lookback_s: float = 300.0):
        self.lookback_s = lookback_s

    async def query_detection(
        self,
        spec: TechniqueSpec,
        target: AssetInstance,
        executed_at_epoch: float,
        window_s: float = 300.0,
    ) -> DetectionResult:
        mitre_id = spec.mitre
        rule = DETECTION_RULES.get(mitre_id)

        if not IS_WINDOWS:
            return DetectionResult(
                detected=False,
                source="sysmon-local",
                mitre_id=mitre_id,
                alert_name="Sysmon not available (not Windows)",
            )

        if not rule:
            return DetectionResult(
                detected=False,
                source="sysmon-local",
                mitre_id=mitre_id,
                alert_name=f"No detection rule for {mitre_id}",
            )

        # Query Sysmon events
        seconds_back = int(max(window_s, self.lookback_s))
        events = _query_sysmon_events(seconds_back=seconds_back)

        # Filter by event ID and match function
        matched = []
        for ev in events:
            if ev.get("EventID") in rule["event_ids"]:
                try:
                    if rule["match"](ev):
                        matched.append(ev)
                except Exception:
                    continue

        if not matched:
            return DetectionResult(
                detected=False,
                source="sysmon-local",
                mitre_id=mitre_id,
                alert_name=rule["name"],
                severity=rule["severity"],
            )

        # Calculate detection latency
        first_match = matched[0]
        latency_s = 0.0
        if executed_at_epoch and first_match.get("TimeCreated"):
            try:
                from datetime import datetime, timezone
                tc = first_match["TimeCreated"].replace("Z", "+00:00")
                detected_time = datetime.fromisoformat(tc).timestamp()
                latency_s = max(0, detected_time - executed_at_epoch)
            except Exception:
                latency_s = 0.0

        return DetectionResult(
            detected=True,
            alert_name=rule["name"],
            alert_id=f"sysmon-{first_match.get('EventID', 0)}-{mitre_id}",
            source="sysmon-local",
            mitre_id=mitre_id,
            latency_s=round(latency_s, 1),
            severity=rule["severity"],
            raw={"matched_events": len(matched), "first_event": first_match},
        )

    async def health_check(self) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            result = subprocess.run(
                ["wevtutil", "gl", "Microsoft-Windows-Sysmon/Operational"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def get_detection_coverage() -> list[dict]:
        """List all detection rules with their MITRE IDs and severity."""
        return [
            {
                "mitre_id": mid,
                "name": rule["name"],
                "event_ids": rule["event_ids"],
                "severity": rule["severity"],
            }
            for mid, rule in DETECTION_RULES.items()
        ]
