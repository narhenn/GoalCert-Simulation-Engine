# GoalCert Simulation Engine v2 — Role-Based Scenario Simulation
### Design specification + build roadmap (delta from your v1 plan)

> **What you asked for, restated so we're aligned:** decouple the *scenario* (Black Phoenix as a described mission) from the *teams*; let the operator **pick a role** (Red / Blue / SOC / Management / OT) and simulate; show **what each team does and how well it performs**; for that you need an explicit **workflow for each team** (sourced from the Incident Response Plan); and you need a **working asset simulation** the scenarios run *on top of* — 1 asset now, 3 later. Below: (Part 1) the new mental model, (Part 2) the full Black Phoenix scenario written as a multi-track timeline, (Part 3) every team's workflow as data, (Part 4) how an asset is actually simulated with a worked example, (Part 5) the scenario library + role selection, (Part 6) gap analysis vs v1, (Part 7) the step-by-step roadmap, (Part 8) data/API changes, (Part 9) decisions + things you didn't mention but need.

---

## PART 1 — THE NEW MENTAL MODEL

### 1.1 v1 vs v2 in one line each
- **v1:** *World (assets+controls) → attacker playbook runs → outcomes emerge → engine auto-plays a single "blue response" step.* Roles were implicit and invisible.
- **v2:** *World (assets+controls) → a **multi-actor scenario** where Red, SOC, Blue, Management, OT each have an **explicit workflow** → operator **picks a role to focus on** → engine drives every role → live view + report are **lensed** on the chosen role.*

You are **not** throwing v1 away. The five layers of v1 (asset models, control models, technique catalog, scenario-as-playbook, environment composer) all stay. You are adding a **sixth layer** above them — the **Role & Workflow layer** — and upgrading the engine loop and the scenario format to be multi-track.

### 1.2 The unifying concept
Four things, cleanly separated so each is reusable:

| Concept | What it is | Reusable across | Source of truth |
|---|---|---|---|
| **World** | Live instances of assets + controls with mutable state | every scenario | v1 catalog (assets/controls) |
| **Scenario** | A *described mission* = a multi-track, phase-aligned timeline of intents. Does **not** hardcode outcomes | one mission (e.g. Black Phoenix) | `scenarios/definitions/*.json` |
| **Role / Workflow** | A team's procedure: the ordered, trigger-driven **actions** it performs (Red kill-chain, Blue NIST response, SOC triage/escalation, Mgmt decisions, OT ops) | every scenario | **new** `roles/workflows/*.json` catalog |
| **Run** | `World + Scenario + chosen role + config` resolved deterministically into a timeline + per-role scores | n/a (instance) | DB |

The important idea: **team workflows become a catalog, exactly like assets/controls/techniques.** A scenario doesn't *contain* the Blue workflow — it *references* it. That is literally how you "define the scenario alone." Swap the Black Phoenix narrative, keep the same Blue/SOC workflows; or author a new "Insider Threat" scenario that reuses the same SOC triage workflow with a different attacker playbook.

### 1.3 The six layers (v1's five + the new one)
```
Layer 6  ROLES & WORKFLOWS   ← NEW. Red/Blue/SOC/Mgmt/OT procedures as data. Each step is a resolvable action.
Layer 5  ENVIRONMENT COMPOSER + ROLE SELECTION  ← extended: operator also picks the FOCUS ROLE + who is scripted/AI
Layer 4  SCENARIO (multi-track playbook)  ← extended: not just a Red playbook — a per-actor timeline
Layer 3  TECHNIQUE CATALOG (Red capabilities, MITRE)  ← unchanged (these are Red's actions)
Layer 2  CONTROL MODELS (EDR/SIEM/FW/seg/DLP/MFA/backup/email)  ← unchanged (the detection bridge)
Layer 1  ASSET MODELS (endpoint/DC/email/OT/...)  ← unchanged (the stage every action lands on)
```

### 1.4 How "pick a role and simulate" works — concretely
Three ways a role can be **driven**; v2 only needs the first, but the seam matters for "agentic later":

| Driver | When | Mechanism |
|---|---|---|
| `ScriptedDriver` | **now (POC)** | Workflow steps execute in defined order, each resolved deterministically by `f(world, config)` |
| `AIDriver` | later | At each decision point an LLM agent is given world-state + the role's objectives and *chooses* the next action from the role's allowed action set |
| `HumanDriver` | future | A real participant performs the action; engine validates/scores it |

**Role selection = two settings per run:**
1. **Focus role** — which team the operator wants to observe/be scored on (drives the live view + report lens). *Every* role still acts; you're choosing a camera, not muting others.
2. **Per-role driver** — which roles are scripted vs AI (in the POC: all `ScriptedDriver`). This is the dial that becomes "let the AI play Red / play Blue" later, with **zero engine changes**.

So "I pick Red Team on Black Phoenix" →engine runs all tracks → live view shows Red's kill-chain progress, which TTPs succeeded/were blocked, beacon health, time budget per phase; the report scores Red (phishing success, priv-esc achieved, exfil, etc.). Pick **Blue** on the same run → same underlying timeline, but the lens shows detections caught, containment actions, MTTD/MTTR, decisions taken. **Same scenario, different lens, different scorecard.**

### 1.5 Determinism + emergence still hold (this is the subtle part)
Adding Blue/SOC actions does **not** break v1's "same inputs → same timeline." It strengthens emergence:
- Red emits telemetry → **controls** (modulated by config: enabled? difficulty? readiness?) deterministically produce alerts.
- SOC workflow is **gated on those alerts** — no alert, no triage, no escalation.
- Blue workflow is **gated on SOC escalation** — containment only happens after detection.
- Blue actions **mutate the world** (isolate host, reset creds, block egress), which can **fail Red preconditions downstream**, branching the Red track.

Turn SIEM **off** → fewer/late alerts → SOC escalates late or not at all → Blue contains late → Red reaches Phase 7/8 → high damage, bad MTTD/MTTR. Turn it **on + high readiness** → early detection → fast containment → Red branches/halts at Phase 4. *Deterministically different, never random.* That's the proof you wanted in v1, now visible **per team**.

---

## PART 2 — THE BLACK PHOENIX SCENARIO (written properly, as a multi-track timeline)

This is the "whole scenario for the entire Black Phoenix" *and* the "multiple scenarios inside it" — because each phase is independently runnable/observable per role. Think of it as **one mission, eight phase-tracks, five actor-lanes.**

**Mission framing (scenario meta):**
- **Name:** Operation Black Phoenix · **Type:** APT → Ransomware → OT impact · **Industry:** Critical Infrastructure / Manufacturing · **Difficulty band:** Advanced (configurable) · **Sim duration:** compressed (e.g. 30–60 min wall-clock streaming a 4–8h sim) · **Framework:** NIST 800-61r2 + MITRE ATT&CK (Enterprise + ICS).
- **Recommended topology:** AD Domain Controller, Email Server, employee Workstations, ERP, MES, SIEM, EDR, Vuln-Mgmt, Firewall/IDS, Cloud, OT segment/PLC, File shares.
- **Workflow bindings:** `red → apt_ransomware_killchain`, `soc → tiered_triage_escalation`, `blue → nist_ir_response`, `mgmt → exec_escalation_regulatory`, `ot → ot_safety_ops`.

For each phase below: **Red action(s) + MITRE → target asset effect → telemetry emitted → which control can detect → SOC track → Blue track → Mgmt/OT track → scoring.** This *is* the scenario JSON, in human form.

### Phase 1 — Reconnaissance
| Lane | Content |
|---|---|
| **Red** | OSINT on org, harvest employee identities, fingerprint exposed services, map suppliers, stand up C2 + lookalike domain. **TTPs:** T1591, T1589, T1590, T1595 |
| **Asset effect** | None internal yet (external-facing only). Optional: perimeter/Firewall sees scan probes |
| **Telemetry** | External scan attempts, DNS enumeration, connections from recon infra |
| **Detection surface** | Firewall/IDS, perimeter NDR (low fidelity at this stage) |
| **SOC** | Review perimeter alerts → validate external scanning → produce threat-intel note. *Mostly P3/informational.* |
| **Blue** | Passive: confirm threat hypothesis (IRP B.07), verify log sources healthy |
| **Mgmt/OT** | — |
| **Scoring** | Red: recon completeness. SOC: did it notice recon at all (most teams don't — that's a finding). |

### Phase 2 — Initial Compromise *(inject: phishing email from "trusted supplier")*
| Lane | Content |
|---|---|
| **Red** | Deliver weaponized attachment → user executes → payload runs → C2 beacon established → migrate to stable process → disable AV telemetry. **TTPs:** T1566.001, T1204.002, T1059.001, T1055, T1071, T1562.001 |
| **Asset effect** | Workstation: `security_state safe→suspicious→compromised`; beacon process injected; local recon |
| **Telemetry** | Suspicious inbound email; **Office→PowerShell with `-enc`**; new process exec; unusual outbound HTTPS to newly-registered domain |
| **Detection surface** | Email-security (pre-delivery), EDR (process chain), SIEM (process+network correlation), Firewall/proxy (C2 egress) |
| **SOC** | Triage suspicious-email + process alerts → confirm malicious (not FP) → **classify P2, escalate to IR** (severity tree: not privileged host yet) |
| **Blue** | Phishing/Initial-Access playbook: query all recipients, pull headers/DMARC, sandbox-detonate attachment, inspect EDR process tree, block sender, **isolate host + acquire memory FIRST** if executed |
| **Mgmt/OT** | — (P2 doesn't escalate to exec yet) |
| **Scoring** | Red: phishing success (PDF). SOC: MTTD on initial access, triage accuracy. Blue: did memory get captured before isolation (evidence integrity)? |

### Phase 3 — Privilege Escalation
| Lane | Content |
|---|---|
| **Red** | LSASS dump → Kerberoast service accounts → Pass-the-Hash to DC → DCSync for domain hashes → establish DA + DC beacon. **TTPs:** T1003.001, T1558.003, T1550.002, T1003.006, T1078 |
| **Asset effect** | Workstation cached creds → `stolen`; DC `security_state→compromised`; `krbtgt hash obtained`; DA session live |
| **Telemetry** | LSASS accessed by non-system process; EventID 4769 RC4 + multiple TGS; 4624 LogonType 9 (PtH); 4662 DCSync from non-DC |
| **Detection surface** | EDR (LSASS), SIEM/AD-audit (Kerberoast/DCSync/PtH) |
| **SOC** | LSASS alert + AD anomalies → host is privileged (DC) → **P1 escalation**; notify SOC Lead/CISO; widen hunt |
| **Blue** | Credential-Theft playbook: treat all cached creds on host as compromised, reset Kerberoasted service accounts, **DCSync ⇒ P0**, schedule krbtgt reset ×2, begin domain-wide reset |
| **Mgmt/OT** | CISO notified at P1; on DCSync (P0) → exec notification begins |
| **Scoring** | Red: priv-esc + domain compromise. Blue: containment correctness (did they isolate DC without CISO approval — wrong! decision gate). SOC: escalation accuracy. |

### Phase 4 — Lateral Movement
| Lane | Content |
|---|---|
| **Red** | Remote-service creation, RDP, SMB propagation, domain recon, SOCKS pivot through DC toward sensitive VLAN. **TTPs:** T1021.001, T1021.002, T1569.002, T1090, T1046, T1018 |
| **Asset effect** | Additional hosts/servers `→compromised`; reachability to ERP/MES/file-shares opens |
| **Telemetry** | East-west auth anomalies, new admin sessions, ADMIN$ connections, WMI/WinRM workstation→server |
| **Detection surface** | NDR/SIEM (east-west), **segmentation control may BLOCK cross-zone movement outright** |
| **SOC** | Lateral-movement detections → confirm multi-host → keep P1, feed hunt |
| **Blue** | Containment decision matrix: isolate confirmed hosts, **monitor suspected passively**, credential resets, verify VLAN ACLs (CORP/DMZ/OT). *Don't isolate network-wide yet.* |
| **Mgmt/OT** | Ops Manager looped in (business systems now in scope) |
| **Scoring** | Red: hosts reached, sensitive VLAN reached. Blue: containment effectiveness + the segmentation decision. **Branch point:** if segmentation ON+high → Red blocked here. |

### Phase 5 — Persistence
| Lane | Content |
|---|---|
| **Red** | Scheduled tasks, registry Run keys, service persistence, cloud-account persistence. **TTPs:** T1053.005, T1547.001, T1543.003, T1078.004 |
| **Asset effect** | Persistence artefacts attached to hosts (survive isolation/reboot) |
| **Telemetry** | EventID 4698 new task, new Run/RunOnce keys, new services w/ odd binary paths, new cloud identities |
| **Detection surface** | EDR/Sysmon/SIEM; cloud audit log (if enabled) |
| **SOC** | Threat-hunt tasks: hunt persistence, review startup entries, validate cloud identities |
| **Blue** | Eradication prep: enumerate persistence (matches Red's R.E list at AAR), plan removal; **do not recover before eradicating** |
| **Mgmt/OT** | — |
| **Scoring** | Red: persistence achieved + survivability. Blue: hunt success rate (how many persistence mechanisms found vs planted). |

### Phase 6 — Data Exfiltration *(inject: engineering drawings + procedures targeted)*
| Lane | Content |
|---|---|
| **Red** | Stage data, compress+encrypt, exfil to cloud / DNS tunnel. **TTPs:** T1074, T1560.001, T1567.002, T1048.001 |
| **Asset effect** | File-share/ERP read en masse; egress channel active |
| **Telemetry** | Large outbound transfers, unusual cloud-storage access, anomalous DNS (TXT/NULL) volume, DLP triggers |
| **Detection surface** | DLP, NDR, DNS firewall, SIEM (3σ volume) |
| **SOC** | Exfil indicators → confirm → **Privacy Officer notified (NDB clock)** |
| **Blue** | **Block egress at firewall + DNS sinkhole FIRST**, then deal with host; preserve evidence/PCAP |
| **Mgmt/OT** | Privacy Officer + Legal engaged; regulatory clock assessment |
| **Scoring** | Red: exfil success + volume. Blue: time-to-block-egress, evidence preserved. SOC: regulatory trigger recognised. |

### Phase 7 — Ransomware Deployment *(inject: enterprise-wide encryption begins)*
| Lane | Content |
|---|---|
| **Red** | Disable security tools, stop services, encrypt file shares, drop ransom notes, clear logs. **TTPs:** T1562.001, T1489, T1486, T1490, T1070.001/004 |
| **Asset effect** | Hosts/shares `health→degraded/down`; backups targeted |
| **Telemetry** | Mass file rename/encryption, EventID 1102 log clear, service stops, AV disabled |
| **Detection surface** | EDR/AV/FS-audit/SIEM (loud, but late) |
| **SOC** | **Incident declaration; P0** |
| **Blue** | Ransomware playbook (high urgency): emergency VLAN segmentation, mass EDR isolation, **take backups read-only/offline**, identify Patient Zero, identify variant, prioritise un-encrypted critical systems |
| **Mgmt/OT** | **Declare P0** → CISO/CEO/Legal; activate BCP; ACSC notification; NDB/APRA assessment; public-comms + regulatory decisions; *no ransom without Legal* |
| **Scoring** | Red: ransomware deployed + recovery inhibited. Blue: MTTC, % systems saved, backup integrity. Mgmt: notification windows met, decision quality. |

### Phase 8 — OT Environment Attack *(advanced: pivot into manufacturing)*
| Lane | Content |
|---|---|
| **Red** | Modify PLC parameters, manipulate production values, disrupt operations. **TTPs (ICS):** T0836 Modify Parameter, T0831 Manipulation of Control, T0813 Denial of Control, T0880 Loss of Safety |
| **Asset effect** | OT/PLC setpoints altered; safety interlocks challenged; production health degraded |
| **Telemetry** | OT alerts, setpoint deviations, command anomalies on the OT segment |
| **Detection surface** | OT monitoring + segmentation (was the OT VLAN reachable from compromised IT?) |
| **SOC + Ops** | Validate OT alerts, coordinate with plant operators |
| **Blue/OT** | **Switch to manual operations**, protect safety-critical systems, isolate OT segment |
| **Mgmt/OT** | Critical-infrastructure incident reporting; safety-first decisions |
| **Scoring** | Red: OT impact achieved. OT/Blue: safety preserved, time-to-manual. **Branch point:** if IT↔OT segmentation enforced → Phase 8 is *blocked* (the headline emergent result). |

**Why this is both "one whole scenario" and "many scenarios":** the operator can run the full 8-phase mission, *or* the engine can run any phase-track in isolation as a focused drill (e.g. "Phase 3 priv-esc, Blue lens" as a standalone exercise). Same data, different `phase_range` on the run.

---

## PART 3 — TEAM WORKFLOWS (the reusable Role & Workflow catalog)

A workflow is **data**, not code: an ordered/triggered list of **steps**, each step a resolvable action. This is the part lifted directly from your IR plan. One schema, five workflow instances.

### 3.0 The Action/Step schema (one shape for every team)
Every step — whether Red's "LSASS dump" or Blue's "isolate host" or SOC's "escalate to P1" — is the same object:
```jsonc
{
  "id": "blue.containment.isolate_host",
  "actor": "blue",
  "label": "Isolate confirmed-compromised host via EDR",
  "trigger": { "on": "soc_escalation>=P1", "phase": ">=3" },     // when does this fire
  "preconditions": ["edr.enabled", "host.security_state==compromised"], // predicates over world
  "resolution": "deterministic",   // success = f(world, control efficacy, readiness, difficulty)
  "latency_model": { "base_s": 300, "readiness_factor": true },  // modeled MTTR contribution
  "effects": ["host.network_contained=true", "blocks: red.lateral.* from host"],
  "emits": ["containment_log", "evidence: memory_image (if memory_first)"],
  "scoring": { "blue.containment_effectiveness": "+", "evidence_integrity": "if memory_first" },
  "decision_gate": "if host==DC require mgmt.ciso_approval else auto"  // IF/THEN branch
}
```
Red's techniques (v1 Layer 3) are **already** this shape — you're generalising it to all actors. The `resolution`/`latency_model` is the Strategy seam: `ScriptedDeterministic` now, `AIDriver` later.

### 3.1 Red Team workflow — `apt_ransomware_killchain`
7-step kill-chain (your IR plan's chapter 07), each step = one or more techniques, with a **time budget** and **evasion/branch** behaviour:

| Step | Actions (techniques) | Success indicator | If detected/blocked → branch |
|---|---|---|---|
| 1 Recon | OSINT/identity/network/scan | target dossier complete | n/a |
| 2 Weaponise | lookalike domain, macro+PS cradle, C2 stand-up | C2 live, payload passes sandbox | swap macro→ISO/LNK/HTML-smuggling |
| 3 Initial Access | phish → exec → beacon → migrate → disable telemetry | beacon stable in svchost, local admin | C2 blocked → DNS-over-HTTPS / cloud-fronted C2 |
| 4 Priv Esc | LSASS, Kerberoast, PtH, DCSync | DA + krbtgt obtained | EDR caught → LOLBins; AES detect → RC4 |
| 5 Lateral | RDP/SMB/remote-svc, pivot to sensitive VLAN | target VLAN reached | host isolated → SMB beacon via DC; **segmentation → halt** |
| 6 Collect+Exfil | stage, archive+encrypt, cloud/DNS exfil | exfil confirmed | egress blocked → switch channel (DNS↔cloud↔ICMP) |
| 7 Impact+Cleanup | ransomware, disable recovery, clear logs, OT pivot | encryption + OT impact | backups offline → impact reduced |

**Modeling note:** every "if detected → backup TTP" from the IR plan's evasion table becomes a **branch in the Red workflow** keyed on world-state (`if c2_ip.blocked then use dns_c2`). This is what makes Red *react* to Blue deterministically.

### 3.2 SOC workflow — `tiered_triage_escalation`
The alert lifecycle (your IR plan's Identification phase + severity tree + escalation matrix):
```
ALERT arrives (from a control)
  → L1 triage: is it a known FP?  ── yes → P3 ticket, enrich+monitor
  → confirm malicious
  → SEVERITY DECISION GATE:
        privileged host (DC/SWIFT/file-server/C-suite)?  ── yes → P1 (notify SOC Lead, begin IR)
        confirmed malicious on single host?               ── yes → P2 (assign Blue analyst)
        DCSync / domain breach / ransomware spreading?    ── yes → P0 (CEO/Board/Legal/ACSC)
  → ESCALATE per matrix (who/when/channel/content)
  → L2 investigation: pull logs, build process tree, widen hunt
  → hand off to Blue (containment) / Threat Hunter (persistence hunt)
```
**SOC scored on:** MTTD, MTTA, escalation accuracy (did P-level match reality?), false-positive rate, threat-hunt success rate. These are the SOC KPIs straight from the PDF.

### 3.3 Blue Team workflow — `nist_ir_response`
The NIST 6-phase lifecycle is the **spine**; the per-attack-type playbooks are **sub-workflows** triggered by what SOC escalated:

| NIST phase | Key actions (decision-gated) | Scored on |
|---|---|---|
| 1 Preparation | playbooks current, EDR 100%, threat hypothesis (pre-run readiness inputs) | readiness (config input) |
| 2 Identification | confirm/scope/severity with SOC | detection coverage |
| 3 Containment | **memory FIRST**, block egress, isolate hosts, disable accounts, segment review, **widen hunt**; *containment paradox & DC-no-isolate gates* | MTTC, containment correctness, evidence integrity |
| 4 Eradication | full IOC sweep, remove all persistence, delete rogue accounts, **krbtgt ×2**, reimage, patch vector, verify | eradication completeness |
| 5 Recovery | verify-clean → restore priority → validate → full restore + 30-day heightened posture | recovery time, re-infection avoided |
| 6 Lessons Learned | AAR | (feeds report) |

Plus the **response-by-attack-type** sub-playbooks the engine selects automatically: Phishing/Initial-Access, Credential-Theft/PrivEsc, Ransomware (high-urgency), Cloud-Breach. Each is a concrete ordered checklist in the IR plan — encode each as a workflow fragment keyed to the technique family it answers.

### 3.4 Management / IC / Comms workflow — `exec_escalation_regulatory`
Triggered by P-level. Steps = decisions + notifications with **deadlines** (the regulatory table):

| Trigger | Decision/Action | Deadline (modeled) |
|---|---|---|
| P1 declared | CISO/IT/Legal notified, war-room opened (out-of-band) | <30 min |
| P0 / data breach | Privacy Officer, regulator (NDB/OAIC) | breach: 30 days; customers ASAP |
| P0 / financial | AUSTRAC/APRA/SWIFT-CSP | same-day / 72h |
| Ransomware | BCP activation, public comms, no-ransom-without-Legal | immediate |
| Critical-infra OT | ACSC/ASD report | 12h severe / 72h significant |

**Scored on:** were the right people notified, with the right content, within the window? (communication quality + regulatory compliance — both in the PDF + IR plan).

### 3.5 OT / Operations workflow — `ot_safety_ops`
Triggered in Phase 8 (or earlier if IT↔OT reachable): validate OT alerts → coordinate with plant operators → **switch to manual operations** → protect safety-critical systems → isolate OT segment. **Scored on:** time-to-manual, safety preserved (did any safety interlock get defeated?), production impact.

### 3.6 The driver seam (how "agentic later" plugs in with no rewrite)
Each workflow runs through a `Driver`:
- `ScriptedDriver.next_action(world, role)` → returns the next step in the defined order whose `preconditions` hold (branching on decision gates). **This is your POC.**
- `AIDriver.next_action(world, role)` → builds a prompt from `(world snapshot, role objectives, allowed action set)` → LLM picks/justifies the next action → engine resolves it the same way. Same interface, same world, same scoring. The workflow JSON becomes the AI's *action space + guardrails* rather than a fixed script.

> Report generation gets the identical treatment: `DeterministicReportGenerator` (template the scored timeline) now → `AIReportGenerator` (LLM narrates the same scored timeline into the PDF's exec-report sections) later.

---

## PART 4 — ASSET SIMULATION (how it actually works)

This is the part you most want concrete, so here is a **fully worked, runnable model** of one asset, end to end.

### 4.1 What "simulating an asset" means
An asset is a **typed state machine that (a) holds state, (b) emits baseline telemetry every tick, and (c) reacts to technique/response *effects* by changing state and emitting event telemetry.** It knows nothing about scenarios or scoring — it just *behaves*. The engine pushes effects at it; it answers with state changes + telemetry. That telemetry is what controls observe and what the console shows.

### 4.2 Worked example — the **Workstation** asset (your "1 asset for now")
Pick the Workstation first because Phases 2–3 (initial compromise + start of priv-esc) land on it and exercise EDR/email-sec/SIEM — the richest single-asset story.

**Model (Pydantic-style):**
```python
class Workstation(AssetModel):
    type = "workstation"
    # --- state ---
    security_state: Literal["safe","suspicious","compromised"] = "safe"
    health: Literal["nominal","degraded","down"] = "nominal"
    # --- properties (set at compose-time / from readiness) ---
    os = "windows11"
    user_susceptibility: float          # 0..1, phish-click likelihood; = f(team_readiness)
    local_admin: bool                   # enables LSASS dump precondition
    cached_creds: list[CredRef]         # what an LSASS dump would yield
    macro_execution_enabled: bool       # a "vulnerability" toggle
    segment = "CORP"; criticality = "medium"
    running_processes: list[str] = ["explorer.exe","outlook.exe"]
    attached_controls: list[str]        # e.g. ["edr_sensor"]
    # --- baseline ---
    def baseline_telemetry(self, t): 
        return [Telemetry("proc", "normal user activity"), Telemetry("net","baseline egress")]
```

**Reaction rules — the heart of it (effect → state + telemetry):**
```python
REACTIONS = {
  # Phase 2: user opens weaponized doc
  "T1204.002": lambda w, cfg: (
      # success gated by susceptibility AND email-sec letting it through
      effect_if(w.user_susceptibility*(1-cfg.email_sec_eff) > cfg.threshold,
        state="suspicious",
        emit=["proc: WINWORD.EXE -> powershell.exe -enc <b64>",   # the classic detectable chain
              "net: HTTPS to newly-registered-domain[.]xyz"])),
  # Phase 2: payload executes / C2
  "T1059.001": lambda w, cfg: effect(state="compromised",
        emit=["proc: powershell encoded cmd", "net: C2 beacon (jittered)"],
        sets={"beacon": "alive in svchost.exe"}),
  # Phase 3: credential dumping — precondition: local_admin
  "T1003.001": lambda w, cfg: requires(w.local_admin) and effect(
        state="compromised",
        emit=["edr: LSASS accessed by non-system process","win: handle to lsass.exe"],
        sets={"cached_creds": "STOLEN -> available to attacker"}),
}
```

**One simulated run on this single asset (Phase 2→3), tick by tick** — *EDR ON, high readiness* vs *EDR OFF, low readiness*:

| t (sim) | Red action | Workstation reaction | Telemetry emitted | EDR ON / high | EDR OFF / low |
|---|---|---|---|---|---|
| 00:00 | T1566.001 deliver phish | — | inbound suspicious email | email-sec **quarantines** (high eff) → attack stalls, branch to weaker lure | delivered |
| 00:05 | T1204.002 user opens | susceptibility×(1−emailsec) check | WINWORD→powershell `-enc` | low susceptibility → user **doesn't click** (branch) | clicks (high susceptibility) |
| 00:06 | T1059.001 exec+C2 | `safe→compromised`, beacon set | encoded PS + C2 egress | **EDR alert (critical)** at t≈00:06 → SOC P2 → Blue isolates 00:11 (memory first) → **beacon killed** | no alert; beacon persists |
| 00:20 | T1003.001 LSASS dump | needs local_admin; creds→stolen | LSASS-access event | already isolated → **precondition fails, Red branches** | succeeds, creds stolen, priv-esc proceeds |

Same asset, same scenario, **config alone** flips the outcome — and you can *watch it on one box*. MTTD here = 6 min (ON) vs ∞/very-late (OFF); that single number is computed from the asset's emitted telemetry + control efficacy, nothing scripted.

### 4.3 The single-asset POC scope
With only the Workstation modelled, you can fully run **Phases 2–3** (and a degraded Phase 5 persistence on the same host). Phases 4/6/7/8 *reference* assets that don't exist yet → the engine's **coverage validator** marks those techniques `skipped (no target)` and the timeline branches/short-circuits gracefully. That's your honest "1 asset" milestone: a complete, scored, role-lensed run of the initial-compromise + priv-esc story on one box.

### 4.4 Going to 3 assets
Add **AD Domain Controller** and **OT/PLC** (plus reuse Workstation):
- **Workstation** → Phases 2,3,5 (foothold, cred theft, persistence)
- **Domain Controller** → Phases 3,4 (DCSync, pivot hub) — unlocks lateral movement + the "don't-isolate-DC" decision gate
- **OT/PLC** → Phase 8 (setpoint modification, safety interlocks) — unlocks the segmentation emergent headline
This trio exercises **all five team workflows** and the two big branch points (segmentation blocks lateral / blocks OT). Email Server is the natural 4th if you want Phase 2 detection richer.

### 4.5 The asset simulation loop (engine-side, per tick)
```python
for technique_or_response in playbook.walk(sim_clock):     # multi-actor: Red OR Blue OR SOC OR ...
    targets = resolve_selector(world, action.target)        # which asset instance(s)
    for asset in targets:
        if not preconditions_hold(world, action): 
            log("FAILED/BRANCH", action); continue          # ← emergence + branching
        ok = resolve(action, asset, attached_controls, cfg) # deterministic success function
        if ok:
            asset.apply_effects(action.effects)             # state machine transition
            telem = asset.emit(action)                      # ← telemetry stream
            for ctrl in controls_covering(asset):
                alert = ctrl.observe(telem, cfg)            # deterministic efficacy+latency
                if alert: feed_soc_queue(alert)             # → SOC workflow triggers
        record_event(actor, action, ok, telem)              # → run_events (the timeline)
# Blue/SOC/Mgmt actions are interleaved by their workflow triggers reading feed_soc_queue / escalations
update_scores_and_kpis(world, events)                       # per-role
```
Pure function of `(world, models, config)` → identical timeline for identical inputs (your v1 determinism guarantee, preserved).

---

## PART 5 — SCENARIO LIBRARY & ROLE SELECTION

### 5.1 Scenario schema (decoupled from teams — your core requirement)
```jsonc
{
  "schema_version": "2.0",
  "name": "Operation Black Phoenix",
  "type": "apt_ransomware_ot", "industry": "manufacturing", "difficulty_bands": ["std","advanced"],
  "recommended_topology": [ {"role":"workstation","qty":3,"segment":"CORP","criticality":"med"},
                            {"role":"domain_controller","qty":1,"segment":"CORP","criticality":"crit"},
                            {"role":"ot_plc","qty":1,"segment":"OT","criticality":"crit"}, ... ],
  "workflow_bindings": {                                  // ← teams referenced, not embedded
     "red":"apt_ransomware_killchain", "soc":"tiered_triage_escalation",
     "blue":"nist_ir_response", "mgmt":"exec_escalation_regulatory", "ot":"ot_safety_ops" },
  "phases": [ { "n":2, "name":"Initial Compromise",
                "red_steps":["red.step3_initial_access"],   // references into the Red workflow
                "injects":["phishing_supplier_email"],
                "objectives":{"red":["beacon_stable"],"blue":["detect<5m","memory_first"]},
                "scoring_weights":{"red.phishing_success":10,"soc.mttd":15,"blue.evidence":10} }, ... ],
  "report_sections": ["exec_summary","attack_timeline","mitre_map","scorecard",
                      "regulatory_impact","financial_impact","recovery_recs","maturity_score","cap"]
}
```
Adding a new scenario = a new JSON that **reuses the same workflow bindings + catalog**. That's how "multiple scenarios, pick a role for each" works with no new code.

### 5.2 Role selection launch flow (extends v1's launch flow)
1. Pick scenario (library) → 2. **Compose environment** (pick assets from catalog: which, qty, segment, criticality, per-asset/global controls — v1 feature) → 3. **Pick FOCUS ROLE** (Red/Blue/SOC/Mgmt/OT) + set per-role driver (all `scripted` in POC; toggle to `ai` later) → 4. difficulty + team-readiness + duration → launch.

### 5.3 Per-role live view (the "see what each team does")
Same WebSocket stream, role-filtered presentation:
- **Red lens:** kill-chain progress bar, per-step success/blocked, active TTP + MITRE ID, beacon health, time-budget burn, current branch.
- **SOC lens:** alert queue, triage decisions, current P-level, escalation log, MTTD/MTTA live.
- **Blue lens:** NIST phase tracker, containment actions taken, hosts isolated, MTTC, evidence-integrity flags, decision-gate choices.
- **Mgmt lens:** notification timeline vs deadlines, decisions, regulatory clocks.
- **OT lens:** PLC setpoint deviations, manual-ops switch, safety status.

### 5.4 Per-role reports
The PDF's "Final Executive Report" sections become the **all-roles AAR**; each focus role also gets a **role scorecard** (Red findings / Blue detection+containment / SOC KPIs / Mgmt compliance), with the AAR questions from the IR plan ("what was intended vs detected vs missed") as the narrative spine.

---

## PART 6 — GAP ANALYSIS: what v1 had vs what v2 needs

| # | v1 had | v2 needs | Change required |
|---|---|---|---|
| 1 | Implicit roles; engine auto-plays one "blue response" | **Roles first-class + selectable focus** | New Role/Actor layer + run config field `focus_role` + per-role driver |
| 2 | Blue/SOC response = single emergent step | **Full per-team workflows** (NIST 6-phase, SOC triage, Mgmt, OT) | New `roles/workflows/` catalog; encode 5 workflows from IR plan |
| 3 | Action = technique only | **Unified Action interface for all actors** | Generalise technique resolution → `resolve(action)` for red/blue/soc/mgmt/ot |
| 4 | Scenario = attacker playbook | **Multi-track scenario** + `workflow_bindings` | Bump scenario schema to 2.0; phases reference per-actor steps |
| 5 | `run_events.actor` existed but only `red`/`engine` | **All five actors populate the timeline** | Same table — just drive every track |
| 6 | Single composite score | **Per-role scoring + SOC KPIs + decision-gate scoring** | Extend `scoring.py`/`kpis.py`; add P-level + escalation-accuracy + evidence-integrity |
| 7 | Reports = AAR | **Per-role scorecards + PDF exec-report sections + regulatory/financial impact** | Extend report generator |
| 8 | Asset reacts to techniques | **Asset also reacts to Blue *response* effects** (isolate, reset, block) | Add response-effect handlers to asset reaction rules |
| 9 | AI seam reserved (resolver/detection/response) | **+ Driver seam (scripted→AI per role) + AI report seam** | Add `Driver` Strategy; keep `ScriptedDriver` default |
| 10 | — | **Decision gates / IF-THEN branches** (18 in IR plan) | Add `decision_gate` to step schema + evaluator |

**Nothing here is a rewrite.** It's: generalise the action model, add one catalog, bump the scenario schema, and broaden scoring/reports. The v1 engine loop, determinism, WebSocket player, and asset/control/technique catalog are the load-bearing parts and they stay.

---

## PART 7 — ROADMAP (step-by-step, mapped onto your v1 build order)

Phased so each milestone is demoable. I've marked **[NEW]** vs **[MODIFY v1]**.

**Milestone A — Generalise the core (1 asset, 1 role visible)**
1. [MODIFY] Generalise the Action schema (§3.0) so techniques and response steps share one shape; refactor v1 technique resolution to call the generic `resolve(action)`.
2. [MODIFY] Add `actor` to every event path; ensure `run_events` carries red/blue/soc/mgmt/ot.
3. [NEW] Build the **Workstation** asset model fully (§4.2) with reaction rules for both attack effects *and* response effects (isolate/reset).
4. [MODIFY] Confirm EDR + email-sec + SIEM control models produce alerts from Workstation telemetry.
5. [NEW] `ScriptedDriver` + `Driver` interface.
6. **Demo:** run Phases 2–3 on one Workstation, EDR ON vs OFF, byte-identical reruns. *(This is your "1 asset, working simulation" proof.)*

**Milestone B — Team workflows + role selection**
7. [NEW] `roles/workflows/` catalog; author all five workflows (§3.1–3.5) as JSON from the IR plan.
8. [NEW] SOC severity decision tree + escalation matrix as a workflow with decision gates.
9. [NEW] Blue NIST 6-phase + the 4 attack-type sub-playbooks; wire triggers (alert→SOC→escalation→Blue).
10. [MODIFY] Engine loop interleaves multi-actor actions by trigger (§4.5).
11. [NEW] Run config: `focus_role` + per-role driver; coverage validator warns on missing assets.
12. [MODIFY] Per-role scoring + SOC KPIs (MTTD/MTTA/MTTR/MTTC, FP, escalation accuracy, hunt success).
13. **Demo:** same run, switch focus Red↔Blue↔SOC, see different live lens + scorecard.

**Milestone C — Full Black Phoenix on 3 assets**
14. [NEW] Add **Domain Controller** + **OT/PLC** asset models (reaction rules for DCSync, lateral pivot, PLC setpoint, safety interlock).
15. [NEW] Author full Black Phoenix scenario JSON (§2, all 8 phases, multi-track) + recommended topology.
16. [MODIFY] Decision-gate evaluator (don't-isolate-DC, segmentation-blocks-lateral/OT, memory-first).
17. **Emergence test:** seg ON+high vs OFF+low → Phase 8 blocked vs OT impact; per-role MTTD/MTTR differ deterministically.

**Milestone D — Orchestration, reports, frontend, library**
18. [MODIFY] Precompute timeline + WebSocket player (pause/resume/speed/manual-inject) — v1 carries over; manual-inject now can inject *any actor's* action.
19. [MODIFY] Report generator → per-role scorecards + PDF exec-report sections + regulatory/financial impact + maturity score + CAP.
20. [MODIFY] Frontend: role-filtered live views (§5.3), role-selection in launch flow (§5.2), per-role AAR.
21. [NEW] Seed a 2nd scenario (e.g. "Insider Threat" or "Cloud Breach" reusing SOC/Blue workflows) to *prove* genericity.
22. [MODIFY] Dockerize + seed DB + README.

**Milestone E — Agentic (later, no engine change)**
23. [NEW] `AIDriver` for one role (start with SOC or Blue) using the workflow JSON as the action space.
24. [NEW] `AIReportGenerator` narrating the scored timeline into the exec report.

---

## PART 8 — DATA MODEL & API CHANGES (concrete, delta from v1)

**New / changed tables:**
- [NEW] `workflows(id, actor, version, definition JSONB)` — the Role/Workflow catalog.
- [MODIFY] `scenarios` → add `schema_version`, `workflow_bindings JSONB`, multi-track `playbook JSONB`.
- [MODIFY] `runs` → add `focus_role`, `role_drivers JSONB` (e.g. `{"red":"scripted","soc":"scripted"}`), `per_role_scores JSONB`.
- [MODIFY] `run_events` → `actor` enum now `red|blue|soc|mgmt|ot|control|engine`; `payload` carries P-level, decision-gate choice, MITRE id.
- [MODIFY] `reports.content` → per-role scorecard blocks + exec-report sections.

**New / changed API routers:**
- [NEW] `GET /workflows`, `GET /workflows/{actor}` — for the launch UI + builder.
- [MODIFY] `POST /runs` body adds `focus_role`, `role_drivers`.
- [MODIFY] WS stream messages tagged with `actor` so the frontend can lens-filter client-side.
- [MODIFY] `GET /reports/{run_id}` returns per-role sections.

---

## PART 9 — DECISIONS + THINGS YOU DIDN'T MENTION BUT NEED

**One real fork — decide this and I can lock the schema:**
- **Role = lens vs role = the only active team.** Recommended: **lens** (all teams act; you observe one). It's strictly more powerful (one run scores everybody; switching lens is free) and it's the only model that makes the future *AI-vs-AI* and *human-vs-AI* modes work. A "solo drill" mode (only your team active, others minimal) is then just a config preset, not a different engine. **I'll build lens unless you say otherwise.**

**Things you didn't list but the IR plan/PDF imply you'll want — flagging so they don't surprise you:**
1. **Decision gates are not optional.** Half of what makes Blue/SOC *scoreable* is the IF/THEN choices (isolate DC? memory first? block egress before host?). Model them explicitly or the Blue lens has nothing interesting to show.
2. **Readiness must map to concrete model knobs.** "Team readiness = high" has to *mean* something: e.g. lower `user_susceptibility`, higher control efficacy, shorter response `latency`. Define that mapping once, centrally.
3. **Per-role KPIs need a clock model.** MTTD/MTTR/MTTC come from event timestamps; make sure every action has a modeled latency so these aren't zero.
4. **Regulatory/financial/maturity report sections** (PDF) need input data the sim must track: data-volume exfiltrated, systems-down duration, notification timestamps vs deadlines. Capture them as events from the start, not bolted on at report time.
5. **Industry mismatch to reconcile:** your IR plan is written around financial/SWIFT (NDB/APRA/AUSTRAC); Black Phoenix is manufacturing/OT (ACSC/Critical-Infrastructure Act). Keep the IR plan's *structure* (NIST phases, decision gates, escalation mechanics) but swap the *regulatory set* per scenario via the scenario JSON — don't hardcode SWIFT into the engine.
6. **OT safety is a distinct asset behaviour** (interlocks, manual-mode) — don't model the PLC as "just another endpoint" or Phase 8 loses its point.

If you confirm the lens model and the 3-asset trio (Workstation + DC + OT/PLC), the very next deliverable I'd produce is the **Workstation asset  
-model + the five workflow JSONs + the Black Phoenix scenario JSON** as actual files you can drop into `backend/app/`.
