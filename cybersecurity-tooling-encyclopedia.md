# The Cybersecurity Tooling Encyclopedia
### The Real-World Tools Red Teams, Blue Teams, and SOCs Use — Organized by Operational Purpose

> **Framing and scope.** This is the practical companion to the five conceptual masterclasses (Red Team, Blue Team, SOC, Mission Encyclopedia, Enterprise Assets). Those documents deliberately kept tools at the *category* level so the methodology stayed in focus. This one names the actual instruments — organized by **team** and by **function**, with each tool's operational purpose, who uses it, and whether it's open-source or commercial.
>
> **Two honest caveats.** (1) **Currency:** the core toolchain is remarkably stable (Nmap, Wireshark, Splunk, Zeek, BloodHound, Volatility have been industry staples for years), but the edges move — new C2 frameworks emerge, EDR/SIEM vendors consolidate and rename products, and "market leaders" shift. Treat vendor-specific and ranking details as accurate-as-of-recently, and verify current versions, licensing, and standing before any procurement or operational decision. (2) **Offensive tools** are described by *operational purpose only* — what they're for, as they appear in MITRE ATT&CK software pages, vendor threat reports, and security curricula — with no usage tutorials, evasion procedures, or weaponization detail. Many of these are *dual-use*: the same tool a red team uses for an authorized engagement is used by criminals and studied by defenders. Naming and purpose is reference; the *how* stays out, consistent with the prior volumes.
>
> The recurring truth from every prior document applies here too: **tools execute decisions; judgment makes them.** A tool list is an inventory, not a capability — the skill is knowing which instrument serves which purpose, and when *not* to reach for one.

A legend used throughout:

| Tag | Meaning |
|---|---|
| `OSS` | Open-source / free |
| `COMM` | Commercial / paid |
| `FREEMIUM` | Free tier + paid tiers |
| `DUAL-USE` | Used by both authorized testers and real adversaries |
| `BUILT-IN` | Native OS / cloud feature, not a third-party product |

---

# PART 1 — RED TEAM / OFFENSIVE TOOLING

> Organized along the attack lifecycle (the structure from the Red Team masterclass). Purpose-level descriptions only.

## 1.1 Reconnaissance & OSINT (passive intelligence)

| Tool | Type | Operational purpose |
|---|---|---|
| **Maltego** | `COMM`/`FREEMIUM` | Visual link-analysis of relationships between people, domains, infrastructure |
| **theHarvester** | `OSS` | Gather emails, subdomains, hosts, names from public sources |
| **Recon-ng** | `OSS` | Modular web-recon framework for structured OSINT collection |
| **SpiderFoot** | `OSS`/`COMM` | Automated OSINT aggregation across hundreds of data sources |
| **Shodan** | `FREEMIUM` | Search engine for internet-connected devices/services (exposed-asset discovery) |
| **Censys** | `FREEMIUM` | Internet-wide scan data; certificate and host intelligence |
| **FOFA / ZoomEye** | `FREEMIUM` | Chinese-origin internet-asset search engines (notably used by some APTs for edge-device discovery) |
| **crt.sh / Certificate Transparency** | `OSS` | Discover subdomains/infrastructure via public TLS certificate logs |
| **Amass** | `OSS` | In-depth DNS/subdomain enumeration and attack-surface mapping (OWASP) |
| **Google Dorking** | technique | Advanced search-operator queries to surface exposed info |
| **LinkedIn / job postings / public filings** | data sources | Org structure, tech stack, personnel intelligence (ORGINT/HUMINT) |

## 1.2 Scanning, enumeration & attack-surface mapping (active)

| Tool | Type | Operational purpose |
|---|---|---|
| **Nmap** | `OSS` | The canonical network/port/service scanner and host discovery tool |
| **Masscan** | `OSS` | Extremely fast internet-scale port scanner |
| **RustScan** | `OSS` | Fast port scanner that feeds Nmap |
| **Nuclei** | `OSS` | Template-based vulnerability/misconfiguration scanner at scale |
| **Aquatone / EyeWitness** | `OSS` | Screenshot and triage web-app attack surfaces |
| **dnsrecon / dnsenum / fierce** | `OSS` | DNS enumeration and zone analysis |

## 1.3 Vulnerability discovery

| Tool | Type | Operational purpose |
|---|---|---|
| **Nessus** | `COMM` | Industry-standard vulnerability scanner |
| **OpenVAS / Greenbone** | `OSS` | Open-source vulnerability scanning |
| **Qualys / Rapid7 InsightVM** | `COMM` | Enterprise vulnerability management + scanning |
| **Nikto** | `OSS` | Web-server vulnerability scanner |

## 1.4 Web application testing

| Tool | Type | Operational purpose |
|---|---|---|
| **Burp Suite** | `COMM`/`FREEMIUM` | The dominant web-app testing proxy/scanner (intercept, analyze, test) |
| **OWASP ZAP** | `OSS` | Open-source web-app testing proxy/scanner |
| **sqlmap** | `OSS` `DUAL-USE` | Automated detection/exploitation of SQL-injection flaws |
| **ffuf / gobuster / dirb** | `OSS` | Content/directory/parameter discovery (fuzzing) |
| **wpscan** | `OSS` | WordPress-focused vulnerability scanner |

## 1.5 Exploitation frameworks

| Tool | Type | Operational purpose |
|---|---|---|
| **Metasploit Framework** | `OSS`/`COMM` `DUAL-USE` | The classic exploitation + post-exploitation framework (Meterpreter payload) |
| **Exploit-DB / searchsploit** | `OSS` | Archive of public exploit code for research/reference |
| **Impacket** | `OSS` `DUAL-USE` | Python library + tools for working with network protocols (SMB, Kerberos, etc.) — foundational for AD work |

## 1.6 Command & Control (C2) frameworks

> The "remote-control" backbone of an engagement (Red Team masterclass §3.13). Heavily `DUAL-USE` — these appear constantly in real intrusions and threat reports.

| Tool | Type | Operational purpose |
|---|---|---|
| **Cobalt Strike** | `COMM` `DUAL-USE` | The dominant commercial adversary-simulation C2 (Beacon); also widely abused by criminals (cracked versions) |
| **Sliver** | `OSS` `DUAL-USE` | Popular open-source cross-platform C2 framework |
| **Mythic** | `OSS` | Modular, multi-agent open-source C2 platform |
| **Havoc** | `OSS` `DUAL-USE` | Modern open-source C2 framework |
| **Brute Ratel (BRc4)** | `COMM` `DUAL-USE` | Commercial adversary-simulation C2 with evasion focus (also abused) |
| **Empire / Starkiller** | `OSS` `DUAL-USE` | PowerShell/Python post-exploitation C2 (community-maintained) |
| **Metasploit / Meterpreter** | `OSS` `DUAL-USE` | C2 capability within Metasploit |

## 1.7 Credential access & cracking

> Purpose-level only; these recover/analyze authentication material in authorized testing.

| Tool | Type | Operational purpose |
|---|---|---|
| **Mimikatz** | `OSS` `DUAL-USE` | The reference tool for extracting/working with Windows credentials and tickets (the most-cited credential tool in threat reports) |
| **Hashcat** | `OSS` `DUAL-USE` | GPU-accelerated password-hash cracking |
| **John the Ripper** | `OSS` `DUAL-USE` | Versatile password-hash cracking |
| **Responder** | `OSS` `DUAL-USE` | LLMNR/NBT-NS/mDNS poisoning to capture network authentication |
| **Rubeus** | `OSS` `DUAL-USE` | Kerberos interaction/abuse toolkit (ticket requests, roasting) |
| **Hydra / Medusa** | `OSS` `DUAL-USE` | Network login brute-forcing |
| **LaZagne** | `OSS` `DUAL-USE` | Recover credentials stored locally by many applications |

## 1.8 Active Directory & identity attack-path analysis

> The "identity graph" navigation from the Red Team and Asset masterclasses.

| Tool | Type | Operational purpose |
|---|---|---|
| **BloodHound / SharpHound** | `OSS` `DUAL-USE` | Graph the AD/Entra trust+permission relationships; find shortest paths to high privilege |
| **PowerView (PowerSploit)** | `OSS` `DUAL-USE` | Ad-hoc AD enumeration via PowerShell |
| **PingCastle** | `FREEMIUM` | AD security posture assessment (also used defensively) |
| **CrackMapExec / NetExec** | `OSS` `DUAL-USE` | Swiss-army knife for AD/network enumeration and action at scale |
| **ADRecon** | `OSS` | AD data collection/reporting (red and blue) |
| **Certify / Certipy** | `OSS` `DUAL-USE` | Assess/abuse Active Directory Certificate Services misconfigurations |

## 1.9 Lateral movement & post-exploitation utilities

| Tool | Type | Operational purpose |
|---|---|---|
| **Impacket suite** (psexec, wmiexec, smbexec, secretsdump) | `OSS` `DUAL-USE` | Remote execution and credential extraction over native protocols |
| **Evil-WinRM** | `OSS` `DUAL-USE` | Windows Remote Management shell for movement/admin |
| **PsExec (Sysinternals)** | `BUILT-IN`-adjacent `DUAL-USE` | Legitimate Microsoft remote-execution tool (heavily abused) |
| **Living-off-the-Land binaries (LOLBAS)** | technique/reference | Native signed OS binaries used to blend in (catalogued at lolbas-project.github.io) |

## 1.10 Payload tooling & defense-evasion (purpose-level only)

> Named for reference (they appear in every threat report); **no procedures.** These exist to test whether defensive controls detect modern tradecraft.

| Tool/category | Type | Operational purpose (conceptual) |
|---|---|---|
| **Veil / Shellter / msfvenom** | `OSS` `DUAL-USE` | Payload generation/encoding for testing detection |
| **Obfuscation/loader tooling** | `OSS`/`COMM` `DUAL-USE` | Test whether EDR/AV detect non-default payload forms |
| **Sysinternals Suite** | `BUILT-IN`-adjacent | Legitimate Microsoft tools (Procmon, PsExec, etc.) used for both admin and testing |

*(Specific evasion mechanics are intentionally omitted — the prior documents treat evasion at the philosophy level for exactly this reason.)*

## 1.11 Cloud offensive assessment

| Tool | Type | Operational purpose |
|---|---|---|
| **Pacu** | `OSS` `DUAL-USE` | AWS exploitation/assessment framework |
| **ScoutSuite** | `OSS` | Multi-cloud (AWS/Azure/GCP) security posture auditing |
| **Prowler** | `OSS` | AWS/Azure/GCP security assessment + compliance checks |
| **ROADtools / AzureHound / MicroBurst** | `OSS` `DUAL-USE` | Azure/Entra ID enumeration and attack-path analysis |
| **Cloud provider CLIs** | `BUILT-IN` `DUAL-USE` | Native AWS/Azure/gcloud CLIs used for both ops and assessment |

## 1.12 Wireless, hardware & physical

| Tool | Type | Operational purpose |
|---|---|---|
| **Aircrack-ng suite** | `OSS` `DUAL-USE` | Wi-Fi security assessment (capture/analysis/cracking) |
| **WiFi Pineapple** | `COMM` | Wireless auditing hardware platform |
| **Flipper Zero** | `COMM` `DUAL-USE` | Multi-tool for RFID/NFC/sub-GHz/hardware testing |
| **Proxmark3** | `COMM` | RFID/access-card research and testing |
| **Rubber Ducky / Bash Bunny (Hak5)** | `COMM` `DUAL-USE` | USB-based payload-injection testing devices |
| **LAN Turtle / Packet Squirrel** | `COMM` | Covert network-access testing hardware |

## 1.13 Phishing & social-engineering infrastructure (authorized assessments)

| Tool | Type | Operational purpose |
|---|---|---|
| **GoPhish** | `OSS` | Open-source phishing-simulation campaign framework |
| **Evilginx** | `OSS` `DUAL-USE` | Reverse-proxy phishing framework used to test MFA-phishing resilience |
| **SET (Social-Engineer Toolkit)** | `OSS` `DUAL-USE` | Social-engineering attack-simulation framework |
| **King Phisher** | `OSS` | Phishing campaign toolkit |
| *(Commercial awareness platforms in §2 / Part 3)* | | Sanctioned phishing-simulation programs |

## 1.14 Red-team reporting, collaboration & infrastructure management

| Tool | Type | Operational purpose |
|---|---|---|
| **Cobalt Strike / Mythic team servers** | `COMM`/`OSS` | Multi-operator engagement coordination |
| **GhostWriter** | `OSS` | Red-team reporting + engagement/infrastructure management |
| **PlumHound / BloodHound reporting** | `OSS` | Turn graph findings into reportable output |
| **Redirectors / domain fronting infra** | technique | Resilient, deniable C2 infrastructure (concept-level) |

---

# PART 2 — BLUE TEAM / DEFENSIVE TOOLING

> Organized by defensive function (the structure from the Blue Team masterclass).

## 2.1 SIEM (Security Information & Event Management) — the analytics backbone

| Tool | Type | Operational purpose |
|---|---|---|
| **Splunk (Enterprise Security)** | `COMM` | Market-leading log analytics + SIEM; powerful search (SPL) |
| **Microsoft Sentinel** | `COMM` | Cloud-native SIEM (KQL); deep Microsoft-ecosystem integration |
| **Elastic Security (ELK)** | `OSS`/`COMM` | Search/analytics stack widely used as a SIEM |
| **IBM QRadar** | `COMM` | Long-established enterprise SIEM |
| **Google Security Operations (Chronicle)** | `COMM` | Cloud-scale security analytics (YARA-L) |
| **LogRhythm / Exabeam / Securonix** | `COMM` | SIEM platforms (Exabeam/Securonix strong on UEBA) |
| **Wazuh** | `OSS` | Open-source SIEM/XDR platform |
| **Graylog** | `OSS`/`COMM` | Open-source-rooted log management/SIEM |

## 2.2 EDR / XDR (Endpoint & Extended Detection and Response)

| Tool | Type | Operational purpose |
|---|---|---|
| **CrowdStrike Falcon** | `COMM` | Leading cloud-native EDR/XDR |
| **Microsoft Defender for Endpoint / XDR** | `COMM` | EDR/XDR integrated across the Microsoft estate |
| **SentinelOne (Singularity)** | `COMM` | Autonomous EDR/XDR |
| **Palo Alto Cortex XDR** | `COMM` | Extended detection/response across endpoint+network+cloud |
| **Trellix / Trend Micro / Sophos / Cybereason / Bitdefender** | `COMM` | Established EDR/XDR vendors |
| **Wazuh / OSSEC** | `OSS` | Open-source endpoint detection/HIDS |
| **Velociraptor** | `OSS` | Endpoint visibility + DFIR hunting (also in §3 DFIR) |

## 2.3 Network detection — NDR, IDS/IPS, traffic analysis

| Tool | Type | Operational purpose |
|---|---|---|
| **Zeek (formerly Bro)** | `OSS` | Network-traffic analysis framework producing rich connection logs |
| **Suricata** | `OSS` | High-performance IDS/IPS + network security monitoring |
| **Snort** | `OSS` | The classic signature-based IDS/IPS |
| **Wireshark / tshark** | `OSS` | The standard packet-capture and protocol analyzer |
| **Arkime (Moloch)** | `OSS` | Large-scale full-packet capture + search |
| **Darktrace / Vectra / ExtraHop / Corelight** | `COMM` | Commercial NDR (Corelight is enterprise Zeek; others ML-driven) |
| **Security Onion** | `OSS` | All-in-one IDS/NSM/log distro (Suricata+Zeek+Elastic) |

## 2.4 Detection engineering (detection-as-code)

| Tool | Type | Operational purpose |
|---|---|---|
| **Sigma** | `OSS` | Vendor-agnostic detection-rule language (converts to SIEM queries) |
| **YARA** | `OSS` | Pattern-matching for files/memory (malware identification) |
| **YARA-L** | — | Detection language used in Google SecOps/Chronicle |
| **Sigma CLI / Uncoder.io** | `OSS`/`FREEMIUM` | Convert Sigma to specific SIEM/EDR query languages |
| **Detection-as-code pipelines** (git + CI) | `OSS` | Version, test, and deploy detections like software |
| **Elastic Detection Rules / Splunk ESCU** | `OSS`/`COMM` | Curated, maintained detection rule repositories |

## 2.5 Threat hunting platforms & query tools

| Tool | Type | Operational purpose |
|---|---|---|
| **Velociraptor** | `OSS` | Fleet-wide hunting via its VQL query language |
| **osquery** | `OSS` | Query endpoints like a database (SQL over OS state) |
| **Hunting in SIEM/EDR** (SPL/KQL/VQL) | — | Hypothesis-driven queries across telemetry |
| **Jupyter Notebooks + MSTICPy** | `OSS` | Notebook-based, repeatable hunting/analysis |
| **HELK / SOF-ELK** | `OSS` | Hunting-oriented Elastic stacks |

## 2.6 Deception technology & honeypots

| Tool | Type | Operational purpose |
|---|---|---|
| **Canarytokens** | `OSS`/`FREEMIUM` | Lightweight tripwires (files/URLs/credentials) that alert on access |
| **Thinkst Canary** | `COMM` | High-quality deception devices/decoys |
| **T-Pot** | `OSS` | Multi-honeypot platform |
| **Cowrie / Dionaea / Honeyd** | `OSS` | Classic honeypots (SSH/telnet, malware, network) |
| **Commercial deception** (e.g., deception grids) | `COMM` | Enterprise-wide decoy/lure fabric |

## 2.7 Identity security — IAM, PAM, ITDR

| Tool | Type | Operational purpose |
|---|---|---|
| **Microsoft Entra ID (+ Identity Protection)** | `COMM` | Cloud identity platform + identity-risk detection |
| **Okta** | `COMM` | Identity/SSO platform |
| **CyberArk / Delinea / BeyondTrust** | `COMM` | Privileged Access Management (vaulting, JIT, session control) |
| **SailPoint / Saviynt** | `COMM` | Identity Governance & Administration (certification, lifecycle) |
| **ITDR capabilities** (in XDR/identity suites) | `COMM` | Identity Threat Detection & Response |
| **PingCastle / Purple Knight** | `FREEMIUM` | AD security posture assessment (defensive) |

## 2.8 Vulnerability management

| Tool | Type | Operational purpose |
|---|---|---|
| **Tenable (Nessus / Tenable.io)** | `COMM` | Vulnerability scanning + management |
| **Qualys VMDR** | `COMM` | Cloud vulnerability management |
| **Rapid7 InsightVM** | `COMM` | Vulnerability management + risk prioritization |
| **OpenVAS / Greenbone** | `OSS` | Open-source vulnerability scanning |
| **Risk-based prioritization** (EPSS, CISA KEV) | reference | Prioritize by real exploitability, not just CVSS |

## 2.9 Email security

| Tool | Type | Operational purpose |
|---|---|---|
| **Proofpoint / Mimecast / Abnormal Security** | `COMM` | Email gateway + anti-phishing/BEC (Abnormal is behavioral) |
| **Microsoft Defender for Office 365** | `COMM` | Email/collaboration threat protection |
| **DMARC/DKIM/SPF tooling** | `OSS`/`COMM` | Email-authentication to fight spoofing |

## 2.10 Cloud security (CSPM / CNAPP / CWPP)

| Tool | Type | Operational purpose |
|---|---|---|
| **Wiz / Orca Security** | `COMM` | Agentless cloud-native application protection (CNAPP) |
| **Palo Alto Prisma Cloud** | `COMM` | Comprehensive CNAPP across posture+workload+identity |
| **Microsoft Defender for Cloud** | `COMM` | Multi-cloud posture + workload protection |
| **Prowler / ScoutSuite / CloudSploit** | `OSS` | Open-source cloud posture assessment |
| **AWS Security Hub / GuardDuty, Azure Defender, GCP SCC** | `BUILT-IN` | Native cloud security/detection services |

## 2.11 Data security & DLP

| Tool | Type | Operational purpose |
|---|---|---|
| **Microsoft Purview** | `COMM` | Data classification, governance, DLP |
| **Forcepoint / Symantec / Digital Guardian DLP** | `COMM` | Data-loss prevention across endpoints/network/cloud |
| **Varonis** | `COMM` | Data access governance + monitoring |
| **Cloud-native DLP** (Macie, etc.) | `BUILT-IN` | Provider data-classification/protection |

## 2.12 Asset management & attack-surface management

| Tool | Type | Operational purpose |
|---|---|---|
| **Axonius / runZero** | `COMM`/`FREEMIUM` | Cyber asset attack surface management (CAASM); unified inventory |
| **External ASM** (Censys ASM, Microsoft Defender EASM) | `COMM` | Continuous external attack-surface discovery |
| **ServiceNow CMDB** | `COMM` | Configuration management database (asset source of truth) |

## 2.13 Hardening, configuration & benchmarks

| Tool | Type | Operational purpose |
|---|---|---|
| **CIS Benchmarks / CIS-CAT** | `FREEMIUM` | Secure-configuration baselines + assessment |
| **Microsoft Security Compliance Toolkit** | `BUILT-IN` | Baseline GPOs and config assessment |
| **OpenSCAP / Lynis** | `OSS` | Configuration/compliance scanning (Linux) |
| **Ansible / Terraform (policy-as-code)** | `OSS`/`COMM` | Enforce hardened config + guardrails as code |

---

# PART 3 — SOC OPERATIONS TOOLING

> Organized by the operations-floor functions from the SOC masterclass.

## 3.1 SIEM (operational view)
*(Same platforms as §2.1 — Splunk, Sentinel, Elastic, QRadar, Chronicle — here used as the analyst's investigation and correlation surface.)*

## 3.2 SOAR (Security Orchestration, Automation & Response)

| Tool | Type | Operational purpose |
|---|---|---|
| **Palo Alto Cortex XSOAR** | `COMM` | Leading SOAR (playbooks, case mgmt, integrations) |
| **Splunk SOAR (Phantom)** | `COMM` | Automation/orchestration tied to Splunk |
| **Microsoft Sentinel (Logic Apps)** | `COMM` | Native automation/playbooks in Sentinel |
| **Tines** | `COMM` | No-code security automation |
| **Shuffle** | `OSS` | Open-source SOAR |
| **Swimlane / FortiSOAR** | `COMM` | Enterprise SOAR platforms |

## 3.3 Case management & ticketing

| Tool | Type | Operational purpose |
|---|---|---|
| **TheHive (+ Cortex)** | `OSS` | Open-source incident case management + observable analysis |
| **Jira / ServiceNow SecOps** | `COMM` | Ticketing + security incident workflow |
| **XSOAR / Sentinel incidents** | `COMM` | Built-in case management within the platform |
| **DFIR-IRIS** | `OSS` | Open-source incident-response case management |

## 3.4 Threat Intelligence Platforms (TIP) & feeds

| Tool | Type | Operational purpose |
|---|---|---|
| **MISP** | `OSS` | Open-source threat-intel sharing/management platform |
| **OpenCTI** | `OSS` | Open-source CTI knowledge management (STIX-based) |
| **Anomali / ThreatConnect / Recorded Future** | `COMM` | Commercial TIPs + intelligence feeds |
| **Mandiant / CrowdStrike / Microsoft intel** | `COMM` | Premium threat-intelligence services |
| **MITRE ATT&CK + Navigator** | `OSS` | The behavior taxonomy + coverage-mapping tool |

## 3.5 Analyst enrichment & investigation utilities

| Tool | Type | Operational purpose |
|---|---|---|
| **VirusTotal** | `FREEMIUM` | Multi-engine file/URL/hash reputation and intelligence |
| **urlscan.io** | `FREEMIUM` | Analyze and screenshot suspicious URLs safely |
| **AbuseIPDB / GreyNoise** | `FREEMIUM` | IP reputation; GreyNoise separates targeted from internet-background noise |
| **Shodan / Censys** | `FREEMIUM` | Pivot on infrastructure during investigations |
| **CyberChef** | `OSS` | The "Swiss-army knife" for decoding/transforming data |
| **WHOIS / DomainTools** | `FREEMIUM`/`COMM` | Domain registration intelligence and pivoting |
| **Hybrid Analysis / Joe Sandbox / ANY.RUN** | `FREEMIUM`/`COMM` | Cloud malware sandboxing for detonation analysis |

## 3.6 Malware analysis & sandboxing

| Tool | Type | Operational purpose |
|---|---|---|
| **Cuckoo / CAPE Sandbox** | `OSS` | Automated dynamic malware analysis |
| **ANY.RUN** | `FREEMIUM` | Interactive online malware sandbox |
| **Ghidra** | `OSS` | NSA-released software reverse-engineering suite |
| **IDA Pro / Binary Ninja** | `COMM` | Industry disassemblers/decompilers |
| **x64dbg / OllyDbg** | `OSS` | Windows debuggers for dynamic analysis |
| **PEStudio / pefile** | `FREEMIUM`/`OSS` | Static PE-file inspection |

## 3.7 DFIR — digital forensics & incident response

| Tool | Type | Operational purpose |
|---|---|---|
| **Velociraptor** | `OSS` | Scalable endpoint DFIR + hunting (fleet collection) |
| **KAPE** | `FREEMIUM` | Rapid forensic artifact collection + processing |
| **Autopsy / The Sleuth Kit** | `OSS` | Disk forensics platform |
| **Volatility (2/3)** | `OSS` | The standard memory-forensics framework |
| **FTK / EnCase / X-Ways** | `COMM` | Commercial forensic suites (court-grade) |
| **Eric Zimmerman's tools** | `OSS` | Windows artifact parsers (registry, $MFT, shellbags, etc.) |
| **Plaso / log2timeline** | `OSS` | Super-timeline generation from many artifact sources |
| **chainsaw / Hayabusa** | `OSS` | Fast Windows event-log threat hunting (Sigma-compatible) |

## 3.8 Telemetry collection & instrumentation

| Tool | Type | Operational purpose |
|---|---|---|
| **Sysmon (Sysinternals)** | `BUILT-IN`-adjacent | Rich Windows endpoint telemetry (process, network, image-load, etc.) — foundational for detection |
| **osquery** | `OSS` | Cross-platform OS instrumentation as queryable tables |
| **Winlogbeat / Filebeat / Fluentd / Fluent Bit** | `OSS` | Log shippers feeding the SIEM/pipeline |
| **Elastic Agent / Splunk UF** | `OSS`/`COMM` | Vendor telemetry collection agents |
| **OpenTelemetry** | `OSS` | Open standard for telemetry collection |
| **SwiftOnSecurity Sysmon config / Olaf Hartong's modular config** | `OSS` | Community-curated Sysmon configurations |

## 3.9 Dashboards, metrics & reporting

| Tool | Type | Operational purpose |
|---|---|---|
| **Grafana / Kibana** | `OSS` | Visualization and operational dashboards |
| **SIEM-native dashboards** | `COMM` | MTTD/MTTR/coverage/queue-health views |
| **Power BI / Tableau** | `COMM` | Executive/program-level security reporting |

---

# PART 4 — SHARED / PURPLE / CROSS-CUTTING TOOLING

## 4.1 Adversary emulation & breach-and-attack simulation (BAS)

| Tool | Type | Operational purpose |
|---|---|---|
| **MITRE Caldera** | `OSS` | Automated, ATT&CK-mapped adversary emulation (agent + server) |
| **Atomic Red Team** | `OSS` | Library of small, per-technique tests mapped to ATT&CK (Red Canary) |
| **Prelude Operator** | `FREEMIUM` | Caldera-derived emulation platform |
| **Stratus Red Team** | `OSS` | Cloud-focused attack emulation |
| **PurpleSharp** | `OSS` | Windows/AD adversary-simulation for detection testing |
| **AttackIQ / SafeBreach / Cymulate** | `COMM` | Commercial BAS platforms (continuous control validation) |
| **Infection Monkey** | `OSS` | Automated breach/segmentation testing |

## 4.2 Purple-team tracking & coverage management

| Tool | Type | Operational purpose |
|---|---|---|
| **VECTR** | `FREEMIUM` | Track purple-team exercises and detection-coverage over time |
| **MITRE ATT&CK Navigator** | `OSS` | Visualize and track ATT&CK coverage |
| **DeTT&CT** | `OSS` | Score data-source and detection coverage against ATT&CK |

## 4.3 Reference frameworks & knowledge bases (not tools, but the shared language)

| Resource | Operational purpose |
|---|---|
| **MITRE ATT&CK** | The behavior taxonomy red/blue/SOC all map to |
| **MITRE D3FEND** | Defensive countermeasure knowledge base |
| **MITRE Engenuity ATT&CK Evaluations** | Independent EDR efficacy testing |
| **Adversary Emulation Library** | Public, actor-specific emulation plans |
| **Lockheed Martin Cyber Kill Chain** | The intrusion narrative model |
| **Pyramid of Pain** | Guides detection durability strategy |
| **Sigma / YARA rule repos (SigmaHQ, etc.)** | Shared detection content |
| **LOLBAS / GTFOBins** | Catalogs of native binaries usable for living-off-the-land (red and blue reference) |
| **CISA advisories / KEV catalog** | Authoritative TTP/IOC + known-exploited-vulnerability references |

---

# PART 5 — How Teams Select Tools

The selection logic is identical across all three disciplines and echoes the prior masterclasses: **capability first, integration second, sustainability third.**

```
1. CAPABILITY GAP   What function is missing/weak? (not "what's the hot product")
2. PURPOSE FIT      Does it serve the actual operational need + threat model?
3. INTEGRATION      Does it produce/consume the data the rest of the stack needs?
                    (Isolated tools create swivel-chair toil and tool sprawl)
4. SIGNAL/CONTROL   Quality of output; for offensive: OPSEC + predictability;
                    for defensive: fidelity + low false-positive burden
5. SUSTAINABILITY   Can the team actually RUN it? (An unstaffed best-in-class
                    tool loses to a well-run modest one)
6. COST/LICENSING   Total cost of ownership incl. people to operate it
7. RESPONSE, not just detection  Can it DO something, or only alarm?
```

**Open-source vs. commercial:** OSS offers control, transparency, and no license cost but demands in-house expertise to operate and maintain; commercial offers support, integration, and managed updates at cost. Mature programs run a *blend* — commercial backbone (SIEM/EDR) plus open-source specialists (Zeek, Velociraptor, Sigma, Sysmon) where they add unique value.

**The recurring warning from the SOC masterclass:** *tool sprawl* — too many disconnected tools — is itself a primary cause of SOC failure (gaps, swivel-chair toil, alert fatigue). The goal is an *integrated toolchain*, not a trophy cabinet.

---

# PART 6 — Tool-to-Function Mapping Matrix

A compressed cross-reference: which tool categories serve which purpose, across the attack-defense lifecycle.

| Lifecycle phase (ATT&CK-ish) | Red Team tooling | Blue Team / SOC detection tooling |
|---|---|---|
| **Recon** | Maltego, theHarvester, Shodan, Amass, Nmap | External ASM (Censys/Defender EASM), GreyNoise |
| **Initial Access** | GoPhish, Evilginx, Metasploit, exploit tooling | Email security (Proofpoint/Defender), WAF, EDR |
| **Execution** | C2 frameworks, scripting, LOLBins | EDR + Sysmon, behavioral detection, Sigma |
| **Persistence** | C2 implants, scheduled tasks, RMM abuse | EDR persistence detection, autoruns hunting, Velociraptor |
| **Priv-Esc** | BloodHound, Certify, kernel/AD abuse | ITDR, PingCastle, EDR, identity monitoring |
| **Credential Access** | Mimikatz, Rubeus, Responder, Hashcat | Sysmon EID 10 (LSASS), AD 4769/4768, EDR, deception |
| **Discovery** | BloodHound/SharpHound, PowerView, NetExec | UEBA, AD-query detections, hunting (osquery/VQL) |
| **Lateral Movement** | Impacket, Evil-WinRM, PsExec, pass-the-* | NDR (Zeek/Suricata), EDR, identity analytics |
| **C2** | Cobalt Strike, Sliver, Mythic, Havoc | NDR, DNS analytics, beacon detection, TIP/IOC match |
| **Exfiltration** | Rclone, C2 channels | DLP, NDR, egress monitoring, CASB |
| **Impact** | (ransomware/wiper emulation — no harm) | EDR behavioral, backup-targeting detection, immutable backups |
| **Cross-cutting** | Caldera, Atomic Red Team, VECTR (purple) | SIEM, SOAR, case mgmt, DFIR (Velociraptor/Volatility/KAPE) |

---

# PART 7 — Caveats and Honest Limitations

- **Currency.** The core toolchain is stable, but vendor names, ownership, product branding, and "market leader" status shift regularly through acquisitions and rebrands. Verify current state before procurement or operational reliance. Treat any ranking language here as illustrative, not authoritative-as-of-today.
- **Dual-use reality.** Many offensive tools (Cobalt Strike, Mimikatz, BloodHound, Impacket) are used *both* by authorized red teams and by real criminals/nation-states — which is exactly why defenders study them and why they appear in threat reports. Naming and purpose is reference material; this document intentionally contains no usage, evasion, or weaponization instructions, consistent with the prior five volumes.
- **Not exhaustive.** The security-tool ecosystem has thousands of products; this lists the widely-used, widely-referenced instruments per function. Niche, regional, and emerging tools exist in every category.
- **Tools ≠ capability.** The unifying lesson of the entire series bears final repetition: a tool inventory is not a security program. **Tools execute decisions; judgment makes them.** The red operator's OPSEC discipline, the blue engineer's detection logic, and the SOC analyst's triage reasoning are what turn these instruments into outcomes. An organization that buys the whole list and lacks the people, process, and judgment to wield it is *less* secure than one that masters a focused, integrated subset.
- **No procurement advice.** This is an educational reference, not a buying recommendation; tool fit depends entirely on your environment, threat model, maturity, and staffing (see the Mission Encyclopedia's maturity model for sequencing).

---

### Appendix: The minimal effective toolchain (by maturity)

```
STARTING OUT (foundational, mostly free):
  Detect/SOC:  Wazuh or Elastic (SIEM) · Sysmon + Sigma · Suricata/Zeek
               (Security Onion bundles these) · VirusTotal · TheHive
  Harden:      CIS Benchmarks · Nessus Essentials/OpenVAS
  Validate:    Atomic Red Team

GROWING (add capability + integration):
  + EDR (commercial) · SOAR (Tines/Shuffle) · MISP/OpenCTI (intel)
  + Velociraptor (DFIR/hunt) · osquery · VECTR (purple) · Caldera
  + Identity monitoring · cloud posture (Prowler/ScoutSuite)

MATURE (scale + optimize):
  + Commercial SIEM/XDR at scale · BAS platform · CNAPP (Wiz/Prisma)
  + PAM (CyberArk/Delinea) · IGA (SailPoint) · premium threat intel
  + Full DFIR suite · deception (Thinkst Canary) · ASM

REMEMBER: integrate, don't accumulate. Tool sprawl is a failure mode,
not a maturity signal. Master a focused, connected toolchain.
```
