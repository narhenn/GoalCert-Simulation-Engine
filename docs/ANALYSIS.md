# GoalCert Simulation Engine — Complete Guide & System Analysis

> A single reference for **what the system does, how to run it, how to play every team, how to test
> every feature**, plus a **code architecture review and gap analysis**. Reflects the build through
> mission types + standalone-mission decoupling (40 backend tests passing).

---

## Table of contents
1. [What it is](#1-what-it-is)
2. [How to run it](#2-how-to-run-it)
3. [The two modes](#3-the-two-modes)
4. [Live Multiplayer — full walkthrough](#4-live-multiplayer--full-walkthrough)
5. [Playing the RED team — every action](#5-playing-the-red-team--every-action)
6. [Playing the SOC — every action](#6-playing-the-soc--every-action)
7. [Playing the BLUE team — every action](#7-playing-the-blue-team--every-action)
8. [Adversary profiles](#8-adversary-profiles)
9. [Mission types (the 12 dedicated missions)](#9-mission-types-the-12-dedicated-missions)
10. [Auto-pilot (no-AI deterministic drivers)](#10-auto-pilot)
11. [Win conditions & scoring](#11-win-conditions--scoring)
12. [Precompute mode (single-operator)](#12-precompute-mode)
13. [Testing every feature](#13-testing-every-feature)
14. [Architecture](#14-architecture)
15. [Gaps & known issues](#15-gaps--known-issues)

---

## 1. What it is

A **model-driven cyber-security simulation platform** with two engines:

- **Precompute (single-operator):** the engine deterministically plays *all* teams (Red/Blue/SOC/Mgmt/OT) against a composed environment, producing a full After-Action Report. Same inputs → identical timeline.
- **Live multiplayer (human-driven):** multiple people join one session, pick a role, and drive a team in real time on a shared world. Any empty seat auto-pilots (deterministic, no AI). You pick a **mission** that defines the goals and flow all teams operate inside.

Faithful to four source docs in the repo: `red-team-masterclass.md`, `blue-team-masterclass.md`, `soc-masterclass.md`, `cybersecurity-mission-encyclopedia.md`.

---

## 2. How to run it

### Local dev (fastest, zero infra — SQLite, auto-seeds)
```bash
# Backend → http://localhost:8000
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000

# Frontend → http://localhost:5173 (proxies /api and /ws to :8000)
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**. Interactive API docs at **http://localhost:8000/docs**.

### Docker (Postgres-backed)
```bash
docker compose up --build      # → http://localhost:8080
```

### Tests
```bash
cd backend && uv run pytest -q                  # 40 passed
cd backend && uv run pytest tests/test_live.py -q   # multiplayer suite
cd frontend && npx tsc -b && npm run build      # typecheck + production build
```

---

## 3. The two modes

| | Precompute (single-operator) | Live multiplayer |
|---|---|---|
| Sidebar entry | **Scenario Library** | **Live Multiplayer** |
| Who acts | Engine plays everyone; you watch & tune | Humans drive Red/SOC/Blue; empty seats auto-pilot |
| Time | Deterministic, precomputed, replayed | Real-time, wall-clock |
| Inputs | difficulty, readiness, controls, per-team workflow toggles, focus role, phase range | mission, adversary profile, roles, automation |
| Output | Full AAR report + leaderboard | Live consoles + end-of-match scorecards |
| Entry URL | `/library` → `/launch/:id` → `/sim/:runId` → `/reports/:runId` | `/live` → `/live/:sessionId` |

---

## 4. Live Multiplayer — full walkthrough

**To play with others on one machine:** open the app in **two browser windows** (e.g. a normal window + an incognito window), both at `http://localhost:5173`.

1. **Host:** sidebar → **Live Multiplayer** (`/live`). Type your operator name.
2. You see three sections: **Dedicated missions** (12 cards) · **Pre-built scenarios** (Black Phoenix) · **Open sessions**.
3. Click a **mission** card → **Go Live**. You're now in the **lobby** (`/live/:sessionId`).
4. **Joiner:** open `/live` in window 2 → the running session appears under **Open sessions** → **Join** → enter a name.
5. **In the lobby:**
   - **Mission card** — shows the chosen mission's briefing + each team's success criteria. (Dedicated missions are *locked*; if you launched Black Phoenix as a scenario, the host can pick any mission here.)
   - **Choose your role** — Red / Blue / SOC are playable; Mgmt / OT are reserved (spectate). Seats with no human show an **AUTO** badge.
   - **Adversary profile** (host) — nation-state / ransomware / cybercrime / insider.
   - **Automation (host)** — force any seat to **Auto** / **Human** / **Default** (default = auto when unoccupied).
   - Host clicks **Start mission**.
6. **During play** each role gets its own console (details in sections 5–7). Spectators get a Red/SOC/Blue **lens toggle**. Everyone shares a **team chat** and a live **operation log**.
7. **Match ends** as a race (section 11): banner shows the winner + Red/SOC/Blue scores.

**Roles & control:** you can only act for the role you claimed. Multiple people can claim the same role (co-op). If you leave a seat empty, the auto-driver plays it so the match still runs.

---

## 5. Playing the RED team — every action

**Goal:** reach the mission objective (and, for stealth missions, stay under the radar). Red operates a guided lifecycle from `red-team-masterclass.md`.

### How to act (UI)
- The Red console shows a **lifecycle stage rail** (Planning → Recon → Weaponise → Initial Access → Foothold → Internal Recon → Privilege → Lateral → Persistence → Evasion/C2 → Impact). Click a stage (or **All**) to filter.
- Each **action card** shows: label, MITRE id, **noise cost** (🔊), points, an **OPSEC note**, and whether it needs a target.
- **Targeted actions** show a dropdown — pick a target asset, then **Execute**. **Auto-target** actions resolve the target for you. Greyed-out actions show *why* they're locked.
- Track your **objectives**, **detection-risk (OPSEC) budget meter**, **credentials**, **footholds**, and **intel**. When the primary objective is met, click **Capture proof & conclude** (the disciplined finish that earns a discipline bonus).

### Key mechanics
- **Noise / OPSEC budget:** every action spends noise; your budget comes from the adversary profile. Controls watching the target raise the cost (×1.4). Staying under budget earns a **stealth bonus**; going over costs a **penalty** (weighted by the mission's stealth weight — 0 for Pen Test/Purple/BAS, 1.5 for Red Team).
- **Fog of war:** you only see assets you've discovered. Recon reveals the external surface; **Map the identity graph** (or network discovery) reveals the internal estate.
- **Evasion:** `evade.amsi` / `evade.low_slow` permanently lower your per-action noise and can make quiet actions slip past detection coverage.

### Stage 1 — Planning
| Action | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|
| **Define objective, ROE & PIRs** (`plan.review`) | always (first move) | locks the mission; reveals the external surface | 0 | 5 |

### Stage 2 — Reconnaissance
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **Passive OSINT & identity harvest** (`recon.osint`) | T1591/T1589 | after planning | reveals external surface; satisfies "recon done" | 2 | 12 |
| **Active service fingerprinting** (`recon.fingerprint`) | T1595 | after recon | reveals exposed services (enables exposed-service entry) | 6 | 10 |
| **Map suppliers & trust** (`recon.supply_chain`) | T1591.002 | after recon | reveals weak third-party trust to abuse | 1 | 10 |

### Stage 3 — Weaponise & Infra
| Action | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|
| **Stand up resilient C2** (`infra.c2`) | after recon | C2 ready (needed for phishing) | 0 | 8 |
| **Build look-alike domain + lure** (`infra.lure`) | after recon | weaponised (needed for phishing) | 0 | 8 |

### Stage 4 — Initial Access (pick **one** vector)
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **Log in with valid credentials** (`access.valid_creds`) | T1078 | after recon | quietest entry; foothold on an endpoint + user creds | 2 | 45 |
| **Spear-phish → execute → beacon** (`access.phish`) | T1566.001 | C2 + lure ready | foothold on an endpoint; classic but louder | 6 | 50 |
| **Exploit exposed service** (`access.exposed_service`) | T1190 | after fingerprinting | foothold on a perimeter server; loudest | 8 | 45 |

### Stage 5 — Foothold
| Action | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|
| **Migrate to stable process** (`foothold.stabilize`) | have a foothold | makes access survivable | 2 | 12 |
| **Characterise defensive tooling** (`foothold.characterize`) | have a foothold | learn what's watching before making noise | 1 | 10 |

### Stage 6 — Internal Recon
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **Local host & session recon** (`intrecon.host`) | T1033/T1057 | foothold | local context | 2 | 10 |
| **Map the identity / trust graph** (`intrecon.identity_graph`) | T1482/T1069 | foothold | **reveals the internal estate**; finds path to objective | 4 | 18 |
| **Network & segmentation discovery** (`intrecon.network`) | T1046/T1018 | foothold | reveals internal estate (noisier) | 6 | 12 |

### Stage 7 — Privilege & Credentials
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **Abuse a legitimate admin path** (`privesc.abuse_delegation`) | T1078 | internal recon + user creds | → privileged (quiet) | 3 | 55 |
| **Dump credentials (LSASS)** (`cred.lsass`) | T1003.001 | foothold | → privileged (strong EDR signal) | 6 | 55 |
| **Kerberoast service accounts** (`cred.kerberoast`) | T1558.003 | foothold + DC target | → privileged | 4 | 55 |
| **DCSync — replicate domain secrets** (`cred.dcsync`) | T1003.006 | privileged + DC target | → **Domain Admin** (objective: domain_admin) | 8 | 100 |

### Stage 8 — Lateral Movement
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **Lateral movement to a host** (`lateral.move`) | privileged + reachable target | take a new foothold closer to the objective (repeatable) | 4 | 35 |
| **Pivot across IT/OT boundary** (`lateral.pivot_ot`) | foothold + reachable MES | reach the OT segment (enables PLC attack) | 6 | 80 |

> *Reachable* = a foothold in the target's zone, OR no segmentation, OR you hold privileged+ credentials. Blue's **segmentation** blocks cross-zone moves.

### Stage 9 — Persistence
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **Scheduled task / service** (`persist.task`) | foothold | survive reboots | 3 | 40 |
| **Forge a Golden Ticket** (`persist.golden_ticket`) | Domain Admin | durable identity persistence (survives until krbtgt ×2) | 4 | 55 |
| **Cloud account persistence** (`persist.cloud`) | privileged + cloud target | cloud re-entry (objective: cloud) | 3 | 45 |
| **Re-establish via persistence** (`persist.reestablish`) | a contained host + you still have persistence | **retake a host Blue contained but didn't eradicate** (repeatable) | 4 | 30 |

### Stage 10 — Defense Evasion & C2
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **AMSI bypass / in-memory** (`evade.amsi`) | foothold | lowers your future noise floor | 1 | 10 |
| **Operate low & slow** (`evade.low_slow`) | foothold | lowers noise further (patience as tradecraft) | 1 | 10 |
| **DNS-over-HTTPS fallback C2** (`c2.fallback`) | C2 ready | C2 survives a single block | 0 | 8 |

### Stage 11 — Objective & Impact
| Action | MITRE | Unlocks when | What it does | 🔊 | Pts |
|---|---|---|---|---|---|
| **Collect & stage data** (`collect.stage`) | foothold + reachable file-share/ERP | stages data for exfil | 3 | 30 |
| **Exfiltrate over DNS** (`exfil.dns`) | staged | quiet exfil (objective: exfil) | 4 | 110 |
| **Exfiltrate to cloud** (`exfil.cloud`) | staged | fast/loud exfil (objective: exfil) | 7 | 120 |
| **Impair defenses (disable EDR)** (`impact.disable_tools`) | privileged + foothold | blind endpoint EDR | 7 | 60 |
| **Deploy ransomware** (`impact.ransomware`) | privileged | take systems down (objective: ransomware) — benign marker | 10 | 180 |
| **Modify PLC setpoints** (`impact.ot_modify`) | in OT + PLC target | physical-process impact (objective: ot_impact) — benign marker | 8 | 180 |
| **Capture proof & conclude** (`objective.capture_proof`) | primary objective met | end the op cleanly for a **discipline bonus** | 0 | 0 |

---

## 6. Playing the SOC — every action

**Goal:** make Red's activity visible, then **triage → classify → escalate** so Blue can respond. The SOC owns **detection coverage** and **MTTA**. SOC sits between Red's telemetry and Blue's response.

### How to act (UI)
- The **Alert queue** is the centre of the SOC console. Every Red action you have coverage for raises an alert (status **new** → **triaged** → **escalated**). Uncovered Red actions show as "uncovered" (a teaching signal).
- For each **new** alert click **Triage & classify** (assigns a P-level, records MTTA). Then click **Escalate to IR** — this **declares an incident** on the asset and hands it to Blue.
- The **Detection & ops** panel holds capability actions (turn on telemetry/correlation/intel/SOAR/hunt). These improve what you can see.
- Watch **coverage %**, **new-alert count**, **triaged/escalated** counts.

> Detection coverage comes from environment controls **plus** the monitoring SOC (and Blue) enable. Turn on EDR + Identity monitoring early so Red's first moves actually alert.

### Visibility & Detection (capabilities)
| Action | What it does | Pts |
|---|---|---|
| **Verify telemetry sources** (`soc.collect`) | confirm sources are feeding (no dead log source) | 8 |
| **Onboard endpoint detection** (`soc.edr_monitoring`) | coverage for endpoint behaviours (LSASS, persistence, exec) | 10 |
| **Onboard identity monitoring** (`soc.identity_monitoring`) | coverage for credential/lateral/priv-esc (the modern perimeter) | 12 |
| **Onboard network + DNS** (`soc.network_monitoring`) | coverage for movement, beaconing, exfil | 10 |
| **Enable correlation rules** (`soc.correlation`) | links signals into multi-stage cases | 10 |
| **Operationalise threat intel** (`soc.intel`) | faster, higher-confidence triage | 10 |
| **Enable SOAR auto-enrichment** (`soc.soar`) | auto-context before a human sees it | 10 |

### Triage / Investigate / Escalate / Hunt / Improve
| Action | Unlocks when | What it does | Pts |
|---|---|---|---|
| **Triage alert** (`soc.triage`) | a **new** alert exists | validate evidence, classify P-level, record MTTA | 12 |
| **Investigate & scope** (`soc.investigate`) | a host is compromised | scope the intrusion (helps Blue contain completely) | 16 |
| **Escalate alert** (`soc.escalate`) | a **triaged** alert exists | **declare an incident** on the asset → Blue responds (bonus if P1/P0) | 15 |
| **Threat hunt** (`soc.hunt`) | a host is compromised | find persistence the alerts missed | 16 |
| **Tune detections** (`soc.tune`) | always | feed findings back; quieter queue | 8 |

---

## 7. Playing the BLUE team — every action

**Goal:** **contain → eradicate → recover** and **fully evict** Red before the objective. Blue's actions **mutate the shared world to hinder Red**. Scored on coverage, MTTC, containment & eviction completeness, and damage prevented.

### How to act (UI)
- Stage rail: **Prepare → See → Decide → Hunt → Contain → Eradicate → Recover → Learn**.
- **Targeted actions** (isolate / reimage / restore) show a dropdown of eligible assets (compromised / contained / down). **Execute**.
- Watch **coverage %**, **MTTC**, **contained/footholds**, **prevented**, and your **objectives** (detect → contain → eradicate → recover → evict).
- **The cat-and-mouse:** if you contain a host but Red still has persistence, Red **re-establishes** it. To win, **scope → hunt → eradicate persistence → krbtgt ×2 → then contain** so eviction sticks.

### Preparation
| Action | What it does | Pts |
|---|---|---|
| **Ready playbooks & pre-authorise** (`prepare.playbooks`) | pre-authorised, faster response | 10 |
| **Isolate & test immutable backups** (`prepare.backups`) | enables **recovery/restore** (ransomware survival) | 12 |
| **Harden: MFA, patch edge, least priv** (`prepare.harden`) | readiness posture | 12 |
| **Tier admin access (PAM)** (`prepare.tiering`) | readiness posture | 10 |

### Visibility & Detection (adds to coverage, same domains as SOC)
| Action | What it does | Pts |
|---|---|---|
| **Deploy endpoint monitoring** (`see.edr`) | endpoint coverage | 10 |
| **Enable identity monitoring** (`see.identity`) | identity coverage | 12 |
| **Centralise logs + correlation** (`see.siem`) | SIEM coverage | 10 |
| **Network detection** (`see.network`) | network coverage | 10 |
| **Data monitoring (DLP)** (`see.data`) | data coverage | 10 |
| **Monitor monitoring health** (`see.health`) | catch dead sensors / blind spots | 8 |

### Decide / Hunt
| Action | Unlocks when | What it does | Pts |
|---|---|---|---|
| **Triage by criticality** (`triage.prioritize`) | always | rank the queue properly | 8 |
| **Investigate & scope** (`investigate.scope`) | a host is compromised | find every foothold **before** containing (avoids partial containment) | 18 |
| **Hunt for persistence** (`hunt.persistence`) | always | find persistence so eradication is complete | 16 |

### Containment (these change Red's world)
| Action | Unlocks when | Effect on Red | Pts |
|---|---|---|---|
| **EDR-isolate a host** (`contain.isolate`) | a host is compromised | **removes that foothold** (repeatable). Partial-containment penalty if other footholds remain unscoped; DC penalty without the DC gate | 20 |
| **DC decision gate** (`contain.dc_gate`) | always | lets you handle a DC safely (block VLANs, not isolate) — avoids the DC penalty | 15 |
| **Block egress + DNS sinkhole** (`contain.block_egress`) | always | **exfiltration fails**; credit if data was already staged | 18 |
| **Disable / reset accounts** (`contain.disable_accounts`) | always | **drops Red's stolen privilege** (Golden Ticket survives until krbtgt ×2) | 16 |
| **Emergency VLAN segmentation** (`contain.segment`) | always | **blocks cross-zone lateral & the IT→OT pivot** | 18 |

### Eradication
| Action | Unlocks when | Effect on Red | Pts |
|---|---|---|---|
| **Remove all persistence** (`eradicate.persistence`) | persistence exists | clears persistence → **defeats Red's re-establish** | 20 |
| **krbtgt reset ×2** (`eradicate.krbtgt`) | always | invalidates Golden Tickets + drops domain creds | 20 |
| **Reimage contained hosts** (`eradicate.reimage`) | a host is contained | rebuild from clean baseline (repeatable) | 12 |

### Recovery & Lessons
| Action | Unlocks when | What it does | Pts |
|---|---|---|---|
| **Restore from clean backups** (`recover.restore`) | backups ready + a down asset | bring impacted systems back (counts as damage prevented) | 15 |
| **Validate eviction & raise vigilance** (`recover.validate`) | always | heightened watch for re-entry | 12 |
| **Lessons learned & conclude** (`learn.aar`) | always | end the operation | 0 |

---

## 8. Adversary profiles

Chosen by the host (or forced by a mission). Sets the Red **noise budget** and how harshly overspend is punished.

| Profile | Budget | Overspend penalty | Notes |
|---|---|---|---|
| **Nation-state** | 220 | ×3.0 | Patient, very quiet; staying unseen is the point |
| **Cybercrime** | 130 | ×1.2 | Opportunistic, tooling-heavy |
| **Insider** | 170 | ×2.0 | **Assumed-breach** — starts inside with valid access + internal map |
| **Ransomware** | 95 | ×0.6 | Fast & noisy; speed over stealth |

---

## 9. Mission types (the 12 dedicated missions)

Each mission is **standalone**: it brings its **own tailored environment** (built from the asset catalog) and **re-points the objective, reweights stealth, and may force the adversary character / start state**. Black Phoenix is **separate** (a pre-built scenario you can also launch live, where the mission is chosen in the lobby).

| Mission | Goal (win condition) | Stealth weight | Forced profile | Env blocks (data/cloud/OT) | The idea |
|---|---|---|---|---|---|
| **Red Team Operation** | topology headline (e.g. OT impact) | 1.5 | — | ✓/✓/✓ | objective undetected; stealth paramount |
| **Adversary Emulation** | topology headline | 1.3 | — | ✓/✓/✓ | in-character vs a named actor |
| **Penetration Test** | topology headline | **0** | — | ✓/✓/✓ | breadth; stealth not scored |
| **Purple Team Exercise** | topology headline | **0** | — | ✓/✓/✓ | coverage is the win |
| **Security Validation (BAS)** | topology headline | **0** | — | ✓/✓/✓ | run the technique set; measure control coverage |
| **Ransomware Simulation** | ransomware | 0.5 | ransomware | ✓/✗/✗ | time-to-impact + backup survival |
| **Insider Threat Simulation** | exfil | 0.8 | insider | ✓/✗/✗ | assumed-breach; behavioural detection |
| **Attack Surface Assessment** | map the surface | 0.3 | — | ✗/✓/✗ | short recon-led flow |
| **Cloud Security Assessment** | cloud persistence | 1.0 | — | ✗/✓/✗ | control-plane + identity |
| **Identity Security Assessment** | Domain Admin | 1.0 | — | ✗/✗/✗ | path to Tier 0 |
| **Supply Chain Assessment** | exfil | 1.0 | — | ✓/✗/✗ | entry via trusted supplier |
| **Social Engineering Assessment** | initial foothold | 0.5 | — | ✗/✗/✗ | human-layer phishing entry |

Every mission's env always includes the **corp foothold terrain** (endpoints, DC, email) + the **SOC appliances** + the **8 standard controls**; data / cloud / OT blocks are added per the table.

---

## 10. Auto-pilot

Any seat with **no human operator** is driven by a **deterministic auto-driver** (no AI) that walks its playbook one action per tick (~3s):

- **Auto-Red** walks the kill-chain toward the mission objective (and re-establishes via persistence if contained).
- **Auto-SOC** stands up detection, then triages + escalates the queue.
- **Auto-Blue** prepares + monitors, then scopes → eradicates → contains → recovers toward full eviction.

The host's **Automation** panel can force any seat to Auto/Human/Default. So you can: play 1-v-1, play Red vs auto-Blue+SOC, defend as Blue vs auto-Red, or spectate a full **auto-vs-auto** match.

---

## 11. Win conditions & scoring

**Race to outcome:**
- **Red wins** the moment its **primary objective** is met.
- **Blue wins** by **full eviction** first (no active footholds **and** no persistence).
- Either interactive role can **conclude** manually; the match also ends that way.

**Scoring at match end:**
- **Red:** action points + objective bonus (+200 primary / +75 secondary) + **stealth bonus** (remaining budget × mission stealth weight) + **discipline bonus** (concluded cleanly after the objective) − overspend penalty.
- **SOC:** detection points (per detected behaviour) + triage/escalation points; reports coverage %, MTTA, triaged/escalated.
- **Blue:** action points + **eviction bonus** (+200) + **prevention bonus** (+75 each for exfil/ransomware/OT prevented); reports MTTC, containment/eviction completeness.

**Mission After-Action Report (all teams).** On conclusion the system builds a full report
(`live/live_report.py`) shown to everyone in the room and available at
`GET /api/live/sessions/{id}/report`: verdict + outcome stats, a **per-team scorecard** (score
breakdown, KPIs, strengths/weaknesses, action timeline), the **attack path with detection coverage**
(each Red step flagged detected/missed), and **prioritised recommendations**. *(Currently in-memory +
snapshot; durable DB persistence is the remaining follow-up — see gaps.)*

---

## 12. Precompute mode

The original single-operator engine (deterministic):
1. **Scenario Library** (`/library`) → **Operation Black Phoenix** → **Configure & Launch**.
2. Select assets, toggle controls (EDR/SIEM/segmentation/DLP/MFA/backups/email-sec), set **difficulty** + **team readiness**, toggle **per-team workflow tasks**, choose a **focus role**, optional **phase range** → **Launch**.
3. **Active Simulation** (`/sim/:runId`): streamed timeline — phase tracker, console, network map, alert feed, **per-team workboards**, **lens switcher**, score strip; controls: **pause / resume / speed / manual inject**.
4. **After-Action Report** (`/reports/:runId`): exec summary, attack timeline, MITRE map, scorecard, regulatory & financial impact, recommendations, maturity score, corrective actions.
5. **Emergence demo:** Easy + all controls on (collapses at phishing) vs Expert + controls off (full ransomware + OT). Same engine, deterministically different.
6. Also: **Dashboard**, **Leaderboard**, **Asset Catalog**, **Scenario Builder**.

---

## 13. Testing every feature

### A. Automated
```bash
cd backend && uv run pytest -q          # 40 passed — engine determinism, emergence, API, WS, live
cd backend && uv run pytest tests/test_live.py -q   # live: create/join, Red lifecycle, Red↔Blue
                                                    # eviction, egress-block, SOC pipeline, auto, missions
cd frontend && npx tsc -b && npm run build
```

### B. Manual — live multiplayer matrix
| Feature | How to test | What to observe |
|---|---|---|
| Create + join | Window 1 launch a mission; Window 2 `/live` → Join | session appears in Open sessions; both in lobby |
| Role pick | claim Red in W1, Blue in W2 | role chips highlight; AUTO badge clears |
| Automation | host Automation panel → set SOC = Auto | SOC plays itself; alerts get triaged/escalated |
| Red play | run plan→recon→infra→phish→lsass→… | OPSEC meter rises; fog reveals; objective ticks |
| SOC play | enable EDR+identity; triage then escalate an alert | coverage %, MTTA; asset shows "incident" |
| Blue play | scope → hunt → eradicate → isolate | foothold removed; eviction objective completes |
| Cat-and-mouse | Blue isolates **without** eradicating | Red `persist.reestablish` retakes the host |
| Containment bites | Blue **block egress**, then Red tries exfil | exfil fails; "prevented" increments |
| Win (Red) | drive Red to its objective | banner "Red wins"; scorecards |
| Win (Blue) | evict fully before objective | banner "Blue wins" |
| Mission report | let any match conclude | all-teams AAR appears: per-team scorecards, attack-path coverage, recommendations |
| Missions | launch Pen Test vs Identity vs Cloud vs Ransomware | different env + goal + stealth weighting |
| BP as scenario | launch Black Phoenix from Pre-built scenarios | mission selectable in lobby (not locked) |
| Spectator | join as Observer | Red/SOC/Blue lens toggle; chat works |
| Auto-vs-auto | Observer host, leave all seats empty | full match resolves on its own |

### C. Manual — precompute matrix
| Feature | How to test |
|---|---|
| Launch + emergence | Library → Black Phoenix → Easy/all-on vs Expert/all-off |
| Live replay controls | Active Sim → pause / speed / manual inject / lens switch |
| AAR | open the report; check scorecard + MITRE map + financials |
| Catalog / Builder / Leaderboard / Dashboard | open each page |

### D. API probes
```bash
curl -s localhost:8000/api/health
curl -s localhost:8000/api/live/missions | jq '.[].id'
curl -s -X POST localhost:8000/api/live/sessions -H 'content-type: application/json' \
  -d '{"mission_id":"ransomware_sim","host_name":"H"}' | jq
curl -s -X POST localhost:8000/api/runs -H 'content-type: application/json' \
  -d '{"scenario_id":"operation_black_phoenix","config":{"difficulty":"Expert","readiness":20,"duration_min":60}}' | jq '.summary'
```

---

## 14. Architecture

```
backend/app/
  engine/            deterministic precompute core (pure; no web/db)
    models/          asset & control behaviour models + registries
    catalog/         MITRE technique specs
    resolve/         preconditions, resolution, detection (swappable seams)
    run.py           event-queue multi-actor orchestrator (precompute)
    workflows.py     v2 Roles & Workflows (IRP-grounded); posture.py aggregates them
    scenario.py      scenario = playbook + topology + decision gates + regulatory
  live/   ★          live, human-driven multiplayer
    red_playbook.py  Red lifecycle as data (34 actions)
    blue_playbook.py Blue lifecycle as data (24 actions)
    soc_playbook.py  SOC lifecycle as data (12 actions)
    missions.py      12 standalone missions + per-mission environments
    session.py       LiveSession: shared World + 3 team states + resolution + scoring
    auto.py          deterministic auto-drivers (the Driver seam; AIDriver later)
    manager.py       in-memory registry + WS broadcast hub + auto-tick loop
  api/  ws/  db/  reports/  services/  scenarios/
frontend/src/        React/TS — Library, Launch, ActiveSim, Reports + Live{Sessions,Room},
                     {Red,Blue,Soc}Console, hooks/useLiveSocket
```

**Two engines, one catalog.** The precompute engine (`engine/`) is pure & deterministic and feeds the AAR/leaderboard. The live engine (`live/`) is a separate real-time interpreter with its own playbooks, scoring and detection model. They share the **World/asset/control catalog** but not the resolution logic or `RunConfig`.

**Live data flow:** `Red action → execute_red_action` mutates the shared `World` + spends OPSEC budget → `_record_detection` (coverage = env controls ∪ SOC/Blue monitoring) raises an **alert** → SOC triages/escalates (declares incident) → Blue contains/eradicates/recovers, mutating the World to hinder Red → `_check_match_end`. The `manager` ticker drives auto seats every ~3s and broadcasts a full snapshot to all sockets on every change.

**The VM seam:** an `AssetInstance` is where a real plugged-in VM (or cloud tenant / PLC simulator) will eventually back the asset — the catalog is the interface; today every asset is a "dumb" simulated state machine.

---

## 15. Gaps & known issues

### 🔴 High — correctness / will bite you
1. **No live-session cleanup → memory leak.** `manager.remove` is never called; completed/abandoned sessions live forever. *Fix: TTL reaper.*
2. **No match timeout / stalemate.** If neither win condition triggers, a match can run indefinitely. *Fix: max tick/time budget → draw.*
3. **Live matches aren't *durably* persisted.** A full all-teams After-Action Report is now generated on conclusion and shown in-room + via REST (`live/live_report.py`), **but** it lives only in the in-memory session — it's lost on server restart and doesn't yet feed the precompute Reports page / leaderboard / history. *Fix: write a `Run`+`Report` (or a dedicated live-report table) on match end.*
4. **Live mode ignores difficulty/readiness/`RunConfig`.** Detection is binary (control present ∪ monitoring on); the rich control-efficacy/difficulty scaling is unused live. *Fix: feed efficacy into `bp.detects` + noise.*
5. **Live engine is not deterministic.** Wall-clock based; MTTD/MTTC quantise to the ~3s tick. Determinism guarantees apply to precompute only. *Fix: logical sim-clock.*

### 🟠 Medium — robustness / ops / security
6. **No authentication/authorization.** A player is a server-issued id in the WS query string; host actions gated only by `player_id == host_id`. Fine on a trusted LAN, not the open internet. No rate limiting.
7. **Two parallel engines (precompute v2 vs live v3) will diverge.** Techniques/detection/containment/gates implemented twice. *Long-term: unify behind one resolution interface.*
8. **Detection coverage is shared between SOC & Blue** (`session.coverage_pct`) — both consoles show the same %.
9. **WS robustness:** malformed JSON kills a connection's receiver; no frontend auto-reconnect; no host migration if the host leaves.
10. **Single-process only.** In-memory registry + asyncio ticker = can't scale to >1 backend replica. *Fix: shared store + pub/sub (Redis) later.*

### 🟡 Medium — realism / depth (mostly by-design)
11. **No fog-of-war for Blue** (purple mode by design) — Blue sees everything.
12. **Mgmt / OT not playable** (reserved spectator seats).
13. **Several actions are representational** (score only, no mechanical effect): Blue `prepare.harden`/`prepare.tiering`, SOC `soc.tune`/`soc.collect`, Red `c2.fallback`.
14. **Appliance assets are decorative in live mode** (`siem_platform`/`edr_platform`/`firewall`/`vuln_mgmt`/`digital_twin` show on the map; detection uses the *controls*).
15. **Mission `needs` is informational** — a custom env missing a required asset would make Red's objective unreachable (→ stalemate, see #2).

### 🟡 Low — UX / testing / polish
16. **No frontend tests**; no tests for the asyncio ticker or concurrency/load.
17. **Frontend bundle >500 KB** (single chunk) — worth code-splitting.
18. **No reconnect UX** — socket drop shows "reconnecting…" but needs a manual refresh.
19. **No spectator cap / max players.**
20. **Auto-driver is greedy/fixed-order** (not strategic) — a human easily out-thinks it (intended: AIDriver later).

**Net:** the design (data-driven playbooks, the Driver seam, missions-as-data, catalog-as-VM-seam) is solid and extensible. The biggest real risks are **operational** (cleanup/persistence/timeout, single-process) and the **two-engine split**. None block local demo/testing today.
