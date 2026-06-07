# GoalCert Simulation Engine

A **model-driven cyber-security simulation platform**. A single operator composes an
environment (picks the assets and their controls), launches a scenario, and **watches the
engine play every actor** — Red attacks, Blue/SOC detect & respond — while outcomes
*emerge* from the modelled assets, controls and the operator's configuration. Fully
deterministic: the same inputs always produce the same timeline.

The flagship scenario, **Operation Black Phoenix**, encodes the 8-phase Red/Blue/SOC
exercise (phishing → domain-admin → exfiltration → ransomware → OT/PLC impact).

---

## How it works (five layers)

1. **Asset models** (`backend/app/engine/models/assets.py`) — each asset type (endpoint, DC,
   email, file share, ERP, MES, cloud, OT PLC, SIEM/EDR/firewall appliances…) has a state
   machine and emits characteristic telemetry when an effect hits it.
2. **Control models** (`models/controls.py`) — EDR, SIEM, firewall/IDS, segmentation, DLP,
   MFA, backups, email security. They detect and/or prevent techniques with deterministic,
   config-scaled efficacy.
3. **Technique catalog** (`catalog/techniques.py`) — MITRE-aligned attacker capabilities,
   each declaring preconditions, effects, emitted telemetry, and which controls detect/prevent it.
4. **Scenario** (`scenario.py`) — an attacker *playbook* (technique sequence) + a recommended
   environment. Expresses **intent**, not outcomes.
5. **Engine** (`run.py`) — an event-queue resolver. Detections and containments are scheduled
   into the future and interleave with later attack steps, so **blue containment can truncate
   the attack** (emergent). Produces a full timeline + scores + KPIs (MTTD/MTTR/detection rate).

Adding a new scenario = a new playbook reusing the catalog. Adding a new asset/control/technique
= one model in the catalog. No engine changes.

### Layer 6 — Roles & Workflows (v2, role-based simulation)

On top of the five layers, **every team is a first-class actor with its own workflow**
(`backend/app/engine/workflows.py`): Red kill-chain, SOC tiered triage/escalation, Blue NIST
incident response, Management escalation/regulatory, and OT safety-ops. The engine drives them
**reactively and deterministically**: Red telemetry → controls raise alerts → **SOC** triages,
classifies a P-level and escalates → **Blue** contains (with decision gates like *isolate-DC needs
CISO approval* and *memory-first*) which mutates the world and can truncate Red → **Management**
notifies against regulatory deadlines → **OT** switches to manual ops.

- **Role = lens.** Every team always acts; the operator picks a **focus role** to observe and be
  scored on. Switching the lens (live or in the report) is free — *same timeline, different view*.
- **Per-role scoring + KPIs:** MTTD / MTTA / MTTC, detection / containment / prevention rates,
  escalation accuracy, threat-hunt success — scored separately for Red / SOC / Blue / Mgmt / OT.
- **Live per-team sub-reports:** each team emits `TASK` status events, so the *Active Simulation*
  page shows **side-by-side workboards** of every team's tasks (pending → active → done / blocked)
  updating in real time, plus a lens switcher and per-role score strip.
- **One mission, many drills:** run the full 8-phase Black Phoenix, or a **single-phase drill**
  (`phase_range`) as a focused exercise. The three per-team Black Phoenix framings
  (`…_red/_soc/_blue`) all reuse the same workflow catalog.
- **Future-proof seam:** workflows resolve through a `Driver` interface — `ScriptedDriver` today,
  a drop-in `AIDriver` (the workflow JSON becomes the agent's action space) later, with no engine
  change. Same for `AIReportGenerator`.

### Layer 7 — Live Multiplayer (v3, human-driven roles)

On top of the precompute engine, a **live interactive** mode lets multiple people play one mission
together in real time (the `HumanDriver` seam the v2 design reserved). Backend in
`backend/app/live/`, served over `POST/GET /api/live/sessions` + the `/ws/live/{id}` WebSocket.

- **Lobby with no links.** A host starts a scenario "live"; it appears in the **Live Multiplayer**
  list; teammates click it, enter a name and **pick a role**. No accounts — a player is a name + a
  server-issued id.
- **Human Red operator.** Red is driven through a **guided, mission-oriented lifecycle** faithful to
  `red-team-masterclass.md`: Planning → Recon → Weaponise → Initial Access → Foothold → Internal
  Recon → Privilege/Credentials → Lateral → Persistence → Defense Evasion/C2 → Objective/Impact
  (`live/red_playbook.py`). Every action is checked against the live `World`, spends a
  **detection-risk budget** (OPSEC §7.4), reveals intel through **fog-of-war recon**, and is scored
  on objective progress + **stealth/discipline**. Pick an **adversary profile** (nation-state /
  ransomware / cybercrime / insider) to set the budget and character.
- **Human Blue defender.** Blue runs the defensive lifecycle from `blue-team-masterclass.md`:
  Prepare → See (visibility/detection) → Decide (triage & scope-before-contain) → Hunt → Contain →
  Eradicate → Recover → Learn (`live/blue_playbook.py`), with the appendix decision-checklist as the
  spine. Scored on **detection coverage, MTTC, containment & eviction completeness, damage prevented**.
- **Human SOC analyst.** SOC sits between Red and Blue (`live/soc_playbook.py`, from
  `soc-masterclass.md`): Red's detected telemetry raises an **alert queue**; the SOC stands up
  detection coverage, then **triages → classifies a P-level → escalates (declares an incident)**,
  which hands the asset to Blue. Scored on coverage, MTTA, triage throughput and escalation. The
  three roles chain: *Red telemetry → SOC alert/triage/escalate → Blue contain/eradicate/recover.*
- **Auto-pilot for any empty seat (no AI).** A seat with no human operator is driven by a
  **deterministic auto-driver** (`live/auto.py`) that walks its masterclass playbook one action per
  tick — so you can play 1-v-1, watch Red-vs-auto-Blue+SOC, or spectate a full auto-vs-auto match.
  The host can force any seat to Auto/Human in the lobby. These are the `Driver` seam the design
  reserved — a future `AIDriver` drops in with no other change.
- **Dedicated missions (the flow & goals all teams run inside).** Live Multiplayer is **mission-first**:
  you launch one of 12 **standalone** missions from the offensive/validation family (`live/missions.py`,
  from `cybersecurity-mission-encyclopedia.md` §2): Red Team Op · Adversary Emulation · Penetration
  Test · Purple Team · Security Validation (BAS) · Ransomware Sim · Insider Threat Sim · Attack-Surface
  · Cloud · Identity · Supply-Chain · Social-Engineering. Each mission is **self-contained** — it brings
  its **own tailored environment** (built from the asset catalog; Cloud→cloud-heavy, Identity→AD-heavy,
  Ransomware→file-shares+backups, …) and **re-points the objective/win condition, reweights stealth,
  forces the adversary character, and sets the start state** (e.g. Identity → path-to-Domain-Admin;
  Insider → assumed-breach + exfil; Pen Test → breadth, stealth not scored; Purple → coverage-focused).
  Each team's success criteria are shown per mission. *(Future: these asset instances get backed by
  real plugged-in VMs for an accurate sim — the catalog model is the seam.)*
- **Black Phoenix is separate.** It stays its own thing — a pre-built **scenario** you can launch live
  (mission chosen in the lobby) and the flagship of the single-operator precompute mode. Missions are
  not nested under it.
- **Red vs Blue on one shared World (purple mode).** Both act in real time on the *same* world: Red's
  actions are visible to Blue; Blue's containment **mutates the world to hinder Red** — isolating a
  foothold removes it, blocking egress stops exfil, segmentation blocks the lateral/OT pivot,
  credential reset drops stolen privilege, eradication prevents Red's persistence re-establish. It's
  a **race**: Red wins by proving the objective; Blue wins by **fully evicting** Red first. Detection
  coverage comes from environment controls + the monitoring Blue enables (`detects()` in
  `blue_playbook.py`); threat-hunting finds the rest.
- **Reserved seats.** Mgmt / OT are joinable spectator seats today and plug into the same session
  next, with no engine change.
- Adding a Red/Blue/SOC action = one entry in `live/{red,blue,soc}_playbook.py`; the session
  interprets it generically (same philosophy as the technique catalog).

Try it: **Live Multiplayer → Go Live** (pick a scenario, choose Red), then open the session in a
second browser, join, and pick **Blue** or **SOC** — or leave seats empty and they auto-pilot. The
host's **Automation** panel forces any seat to Auto/Human.

---

## Run it — local dev (fastest, zero infra)

The backend defaults to a local **SQLite** DB and seeds itself on startup.

**Backend** (Python 3.11+, [uv](https://docs.astral.sh/uv/)):
```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 20+):
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** (Vite proxies `/api` and `/ws` to the backend on :8000).

## Run it — Docker (Postgres-backed)
```bash
docker compose up --build
```
Then open **http://localhost:8080** (web → nginx → api → Postgres).

---

## Try the headline demo

1. **Library → Operation Black Phoenix** → opens *Configure & Launch*.
2. **Select assets** for the environment and **toggle controls** (EDR / SIEM / segmentation /
   DLP / MFA / backups / email security); set **difficulty** and **team readiness**.
3. **Launch** → the *Active Simulation* streams live: phase tracker, console telemetry, a
   network map whose nodes change state, an alert feed, and operator controls
   (pause / resume / speed / manual inject).
4. On completion, open the **After-Action Report** (exec summary, attack timeline, MITRE map,
   scorecard, regulatory & financial impact, recommendations, maturity score, corrective actions).

**See emergence:** run it once at **Easy** with all controls on (the kill-chain collapses at
phishing), then again at **Expert** with controls off (full ransomware + OT impact). Same engine,
different posture → deterministically different outcome.

---

## Tests
```bash
cd backend
uv run pytest -q
```
Covers engine determinism, full 8-phase coverage, strong-vs-weak **emergence**, asset-selection
impact (removing SIEM degrades detection), the disable-EDR-cancels-alerts behaviour, and the
REST + WebSocket API end-to-end.

---

## Layout
```
backend/app/
  engine/        # pure deterministic simulation core (no web/db deps)
    models/      # asset & control behaviour models + registries
    catalog/     # technique specs + registry
    resolve/     # preconditions, resolution, detection, response (swappable seams)
    run.py       # the event-queue orchestrator
  scenarios/     # playbook authoring + Operation Black Phoenix
  services/      # compute/persist runs + live streaming RunManager
  reports/       # deterministic AAR generator
  db/ api/ ws/   # persistence, REST routers, WebSocket
frontend/src/    # React + TS UI (dashboard, library, launch+asset-selection, active sim,
                 # builder, leaderboard, reports)
```

## Notes & roadmap
- **Deterministic, no AI** by design; the resolver interfaces in `engine/resolve/` are seams for
  a future `AIResolver` / real-tool adapters (SIEM/EDR), and a `seed` field reserves a future
  stochastic mode.
- Schema is created via `create_all` for the POC; swap in Alembic migrations for production.
- No auth yet (single-operator POC) — a token-auth seam can wrap the routers later.
