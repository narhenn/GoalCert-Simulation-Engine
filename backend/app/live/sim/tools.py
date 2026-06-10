"""Per-team, per-scenario tool catalogs for the immersive workspaces.

A `Tool` is one thing a team can *do*. `kind` decides how the engine runs it:
  - "real" — executes a real tool against the Docker lab (via its `fire_action` FireSpec) and streams
    real output; also applies its topology `effect`.
  - "sim"  — a scripted attacker step (exploit/worm/encrypt): applies `effect` + prints `command_hint`
    as authentic synthetic terminal output. Never touches the lab.
  - "act"  — a Blue response (isolate/segment/patch/sinkhole/restore): mutates the topology; `mitigates`
    names the lever it bends.
  - "view" — a SOC investigation lens (zeek/suricata/splunk/…): surfaces telemetry, no state change.

`schema` = the fields the tool-workspace form renders (target range, host, vlan pair…). `unlocks_after`
gates the Red kill-chain so capabilities open up as prerequisites are met. The engine interprets
`effect`; the frontend renders `name/summary/does/how/outcome/schema/command_hint`.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolField:
    key: str
    label: str
    type: str = "text"                 # text | select | host | hosts | vlanpair | alert
    options: tuple[tuple[str, str], ...] = ()   # (value, label) for select
    default: str = ""
    filter: str = ""                   # for host/hosts/alert: which subset (e.g. "vulnerable", "infected")

    def public(self) -> dict:
        return {"key": self.key, "label": self.label, "type": self.type,
                "options": [list(o) for o in self.options], "default": self.default, "filter": self.filter}


@dataclass(frozen=True)
class Tool:
    id: str
    team: str                          # red | blue | soc
    name: str
    stage: str
    kind: str                          # real | sim | act | view
    effect: str                        # engine effect key
    summary: str
    does: str = ""
    how: str = ""
    outcome: str = ""
    unlocks_after: tuple[str, ...] = ()
    fire_action: str = ""              # FireSpec action_id (real tools)
    command_hint: str = ""             # synthetic command shown for sim tools
    schema: tuple[ToolField, ...] = ()
    mitigates: str = ""                # blue lever
    once: bool = False

    def public(self, available: bool, reason: str = "") -> dict:
        return {
            "id": self.id, "team": self.team, "name": self.name, "stage": self.stage, "kind": self.kind,
            "summary": self.summary, "does": self.does, "how": self.how, "outcome": self.outcome,
            "fire_action": self.fire_action, "command_hint": self.command_hint,
            "mitigates": self.mitigates, "once": self.once,
            "schema": [f.public() for f in self.schema],
            "available": available, "reason": reason,
        }


def _scan_field() -> ToolField:
    return ToolField("scan", "Scan type", "select",
                     options=(("sn", "Host discovery (-sn)"), ("sv", "Service/version (-sV)"),
                              ("smb", "SMB scripts (--script smb-os-discovery)")), default="sn")


# ===========================================================================
#  W1 — WannaCry SMB worm
# ===========================================================================
_W1: list[Tool] = [
    # ---------------- RED ----------------
    Tool("nmap", "red", "Nmap", "Host Discovery", "real", "reveal_hosts",
         summary="Find live hosts on the reachable subnets.",
         does="Sweep the subnet for live hosts — the worm's first move.",
         how="Real nmap host-discovery sweep against the lab (T1046).",
         outcome="Reveals neighbours on the topology map and the SOC's first (quiet) scan signal.",
         fire_action="intrecon.network",
         schema=(ToolField("range", "Target range", "select",
                           options=(("subnet", "Local subnet (10.0.0.0/24)"), ("all", "All VLANs")), default="subnet"),
                 _scan_field())),
    Tool("netexec", "red", "NetExec (SMB Enum)", "SMB Enumeration", "real", "mark_vulnerable",
         summary="Find which hosts still speak vulnerable SMBv1.",
         does="Enumerate SMB and flag the legacy-SMBv1 (vulnerable) hosts + their shares.",
         how="Real NetExec SMB enumeration against the file target (T1018).",
         outcome="Vulnerable hosts turn amber — the worm's target list.",
         unlocks_after=("nmap",), fire_action="intrecon.identity_graph"),
    Tool("eternalblue", "red", "EternalBlue", "Exploit", "sim", "exploit",
         summary="Exploit a vulnerable SMBv1 host for code execution.",
         does="Fire the SMBv1 exploit at a chosen vulnerable host.",
         how="Simulated (T1210) — success probability that emits an IDS exploit signature; no exploit code runs.",
         outcome="Target turns orange (exploited) — and lights up the loudest early SOC signal.",
         unlocks_after=("netexec",), command_hint="msf6 exploit(windows/smb/ms17_010_eternalblue) > run",
         schema=(ToolField("host", "Target host", "host", filter="exploitable"),)),
    Tool("payload", "red", "Payload Dropper", "Payload", "sim", "infect",
         summary="Drop and launch the worm payload.",
         does="Write the payload to the exploited host and execute it.",
         how="Simulated file-write + process spawn (T1059.003).",
         outcome="Host turns solid red (infected) — the worm is resident.",
         unlocks_after=("eternalblue",), command_hint="meterpreter > upload w1.bin && execute -f w1.bin",
         schema=(ToolField("host", "Target host", "host", filter="exploited"),)),
    Tool("persistence", "red", "Service Creator", "Persistence", "sim", "persist",
         summary="Survive reboot via a service/auto-run.",
         does="Register a service so the payload re-launches at boot.",
         how="Simulated service creation (T1543).",
         outcome="Host gains a persistence anchor — reimaging now required to clean it.",
         unlocks_after=("payload",), command_hint="sc create W1Persistence binPath= C:\\w1.bin start= auto"),
    Tool("dns_killswitch", "red", "DNS Query (Kill-switch)", "C2", "sim", "killswitch_check",
         summary="Perform the worm's kill-switch lookup.",
         does="Make the single hardcoded outbound check that decides continue-or-abort.",
         how="Simulated DNS/HTTP callback (T1071.001) to a newly-seen domain.",
         outcome="If the domain is unreachable, the worm commits to spreading + encrypting.",
         unlocks_after=("payload",), command_hint="nslookup iuqerfsodp9ifjaposdfjhgosurijfaewrwergwea[.]com"),
    Tool("propagate", "red", "SMB Propagation Engine", "Lateral Movement", "sim", "start_propagation",
         summary="Unleash the worm — auto-spread across reachable SMBv1 hosts.",
         does="Each infected host scans + exploits reachable vulnerable neighbours, every tick.",
         how="Simulated population spread (T1021.002) gated by R-value + VLAN reachability.",
         outcome="The red zone expands across VLANs until contained, patched, segmented or sinkholed.",
         unlocks_after=("payload",), command_hint="[worm] scanning 445/tcp across reachable subnets…", once=True),
    Tool("shadow_delete", "red", "Shadow Copy Deletion", "Disable Recovery", "sim", "disable_recovery",
         summary="Wipe local recovery before encrypting.",
         does="Delete shadow copies + backup catalog on infected hosts.",
         how="Simulated (T1490) — high-fidelity ransomware precursor telemetry.",
         outcome="Local restore is gone; recovery now depends on offline backups.",
         unlocks_after=("payload",), command_hint="vssadmin delete shadows /all /quiet", once=True),
    Tool("ransomware", "red", "Ransomware Engine", "Impact", "sim", "encrypt",
         summary="Encrypt every infected host and demand ransom.",
         does="Encrypt files, rename to .locked, drop the ransom note + lock screen.",
         how="Simulated file-state flips (T1486) — no real cipher.",
         outcome="Infected hosts go black (impacted); the victim desktops show the ransom note.",
         unlocks_after=("shadow_delete",), command_hint="w1.bin --encrypt --ext .locked --note", once=True),

    # ---------------- BLUE ----------------
    Tool("edr_quarantine", "blue", "EDR Quarantine", "Contain", "act", "isolate",
         summary="Network-isolate a compromised host.",
         does="Quarantine a host at the EDR level — it stops spreading.",
         how="EDR network containment.", outcome="Host turns blue (contained) and leaves the spread set.",
         mitigates="isolate", schema=(ToolField("host", "Host", "host", filter="containable"),)),
    Tool("disable_smbv1", "blue", "Vuln Scanner + Disable SMBv1", "Eradicate", "act", "patch_hosts",
         summary="Remove SMBv1 from exposed hosts.",
         does="Disable the vulnerable service on chosen hosts.",
         how="GPO/config push.", outcome="Those hosts stop being targetable (vector removed).",
         mitigates="patch", schema=(ToolField("hosts", "Hosts", "hosts", filter="vulnerable"),)),
    Tool("segment", "blue", "Firewall Manager", "Contain", "act", "segment",
         summary="Sever a VLAN boundary on TCP/445.",
         does="Cut the inter-VLAN 445 edge so the worm can't cross.",
         how="Emergency segmentation — the single most effective W1 containment.",
         outcome="Caps the blast radius to already-infected VLANs.",
         mitigates="segment",
         schema=(ToolField("edge", "VLAN boundary", "select",
                          options=(("fin|hr", "Finance ↔ HR"), ("fin|srv", "Finance ↔ Server"),
                                   ("hr|srv", "HR ↔ Server")), default="fin|srv"),)),
    Tool("sinkhole", "blue", "DNS Manager (Sinkhole)", "Contain", "act", "sinkhole",
         summary="Sinkhole the kill-switch domain.",
         does="Point the kill-switch domain at a sinkhole so every host's check 'succeeds'.",
         how="DNS sinkhole / internal redirect.",
         outcome="Trips the kill switch fleet-wide — infected hosts go dormant, new encryption halts.",
         mitigates="sinkhole", once=True),
    Tool("wsus", "blue", "WSUS (Mass Patch)", "Eradicate", "act", "patch_all",
         summary="Patch SMBv1 across the whole fleet.",
         does="Disable SMBv1 everywhere at once.", how="Emergency WSUS/GPO rollout.",
         outcome="Removes the worm's vector fleet-wide — new infections stop.",
         mitigates="patch", once=True),
    Tool("restore", "blue", "Veeam (Restore)", "Recover", "act", "restore",
         summary="Restore an impacted host from clean backups.",
         does="Rebuild + restore an impacted host.", how="Restore from offline backups (only if preserved).",
         outcome="Impacted host returns to service (recovered).",
         mitigates="restore", schema=(ToolField("host", "Host", "host", filter="impacted"),)),

    # ---------------- SOC ----------------
    Tool("zeek", "soc", "Zeek", "Network Discovery", "view", "view",
         summary="Spot the port-445 scan fan-out.",
         does="Inspect network-flow for one-source-to-many TCP/445 scans.",
         how="Zeek conn logs / horizontal-scan heuristic.", outcome="Confirms early reconnaissance."),
    Tool("suricata", "soc", "Suricata", "Exploit", "view", "view",
         summary="See the SMB exploit signature.",
         does="Inspect IDS alerts for the SMBv1 exploit pattern.",
         how="Suricata signature match.", outcome="Highest-confidence early signal."),
    Tool("splunk", "soc", "Splunk", "Investigation", "view", "view",
         summary="Query the telemetry — 445 events, exploits, infected hosts.",
         does="Search the SIEM to scope the incident.", how="SPL over the event stream.",
         outcome="Builds the incident picture."),
    Tool("sysmon", "soc", "Sysmon", "Host Telemetry", "view", "view",
         summary="See host events — new services, shadow deletion, mass rename.",
         does="Inspect endpoint telemetry for persistence + ransomware precursors.",
         how="Sysmon process/file/registry events.", outcome="Catches the mid/late funnel tells."),
    Tool("threat_hunt", "soc", "Threat Hunting Console", "Hunt", "act", "hunt",
         summary="Reveal infected hosts that didn't alert.",
         does="Hunt IOCs/services to surface undetected footholds.",
         how="IOC + service-name sweep.", outcome="Reveals hidden infected hosts to the defenders."),
    Tool("soc_triage", "soc", "Triage Alert", "Triage", "act", "triage",
         summary="Disposition a new alert.",
         does="Classify and confirm a new alert.", how="Alert triage workflow.",
         outcome="Confirms a true positive, ready to escalate.",
         schema=(ToolField("alert", "Alert", "alert", filter="new"),)),
    Tool("soc_escalate", "soc", "Escalate to IR", "Escalate", "act", "escalate",
         summary="Declare an incident and hand to Blue.",
         does="Escalate a triaged alert — declares an incident on the affected host.",
         how="Incident declaration.", outcome="Hands Blue a scoped incident (containment bonus).",
         schema=(ToolField("alert", "Alert", "alert", filter="triaged"),)),
]


CATALOGS: dict[str, list[Tool]] = {
    "scn-wannacry-w1": _W1,
    # R5 and C5 catalogs are added when their topologies land.
}


def catalog(scenario_id: str) -> list[Tool]:
    return CATALOGS.get(scenario_id, [])


def by_id(scenario_id: str) -> dict[str, Tool]:
    return {t.id: t for t in catalog(scenario_id)}
