# GoalCert Live-Fire — End-to-End Demo Runbook

A step-by-step script to run the demo and **prove** it uses real VMs/tools. ~5 min to set up,
~5 min to present. Phase 1 (Docker range) is the main act; Phase 2 (AD) and Phase 3 (multi-tenant)
are optional deeper beats.

---

## Part 0 — One-time setup (do this BEFORE demo day)

You only do this once; images get cached so demo-day start is instant.

```powershell
# 1. Docker Desktop must be running.
# 2. Build + pull + start the range (project "gclab"), and smoke-test it:
pwsh infrastructure/lab-setup.ps1        # macOS/Linux: bash infrastructure/lab-setup.sh
```
The script prints two URLs at the end — **note them down**:
- `DVWA in a browser:  http://localhost:<port>`
- `Kali shell (ttyd):  http://localhost:<port>`

(Ports are dynamic. You can re-query any time:
`docker compose -f infrastructure/docker-compose.lab.yml -p gclab port target-web 80`.)

---

## Part 1 — Start the three processes (demo day)

Open **three terminals**:

**Terminal 1 — the lab** (if not already up from Part 0):
```powershell
docker compose -f infrastructure/docker-compose.lab.yml -p gclab up -d
docker compose -f infrastructure/docker-compose.lab.yml -p gclab ps      # 3 services "running"
```

**Terminal 2 — backend** (FastAPI on :8000):
```powershell
cd backend
uv run uvicorn app.main:app --reload --port 8000
#   (or:  .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000)
```

**Terminal 3 — frontend** (Vite on :5173, proxies to :8000):
```powershell
cd frontend
npm run dev
```

Sanity check (optional): `curl http://localhost:8000/api/lab/status` → `"up": true, "attacker_ready": true`.

---

## Part 2 — Pre-stage the "proof" windows (the credibility kit)

Arrange your screen so the audience sees GoalCert **and** the real machinery side by side:

1. **Browser tab A** — GoalCert: `http://localhost:5173`
2. **Browser tab B** — DVWA: the `http://localhost:<port>` from Part 0 (the real vulnerable app)
3. **Browser tab C** — leave ready for the Kali shell (you'll open it from the UI mid-demo)
4. **A terminal running the live target log** — this is the money shot:
   ```powershell
   docker compose -f infrastructure/docker-compose.lab.yml -p gclab logs -f target-web
   ```
   Keep it visible; it will light up the instant you attack.
5. (Optional) another terminal with `docker ps` showing the real Kali + target containers.

---

## Part 3 — The demo script (what to click + what to say)

### Beat 1 — "This isn't a tabletop. It's real infrastructure." (30s)
- Show `docker ps`: *"A real Kali Linux attack box and real vulnerable targets, running now."*
- Show DVWA tab: *"This is a real, deliberately vulnerable web app — our target."*

### Beat 2 — Start a live mission (1 min)
- GoalCert → **Live Multiplayer** (left nav).
- Pick a mission — **Red Team Operation** or **Penetration Test** — enter your name → you're the **host** in the room.
- Lobby: under **Choose your role** click **Red**. Pick an adversary profile (e.g. *Nation-state*). Leave Blue/SOC on **Auto** (they'll react automatically). Click **Start mission**.

### Beat 3 — Arm live-fire (30s)
- Right-hand **Live-fire range** panel → it shows `Range up · attacker ready`.
- Click **Arm**. The header now shows a red **`LIVE-FIRE · REAL TOOLS`** badge.
- *"From here, what I click runs real tools, not a script."*

### Beat 4 — Fire real tools, watch real detection (2 min) ← the core
In the **Operator actions** panel, run these in order (click **Execute** on each):
1. **Define objective, ROE & PIRs** (`plan.review`) — sets up.
2. **Passive OSINT & identity harvest** (`recon.osint`).
3. **Active service fingerprinting** (`recon.fingerprint`) — **this runs real `nmap -sV`.**
   - In the **Operation log**, a terminal block appears: the **real command**, the **real nmap
     output** (open ports/services), and a green **DETECTED** badge.
   - Glance at **Terminal 4 (target-web logs)** — *it just lit up with the scan*. That live
     correlation is the proof.
4. **Exploit an exposed internet-facing service** (`access.exposed_service`) — **real `nikto`** web
   scan; more real output + another **DETECTED**.
- *"GoalCert ran real Kali tools against a real target and detected them from the target's real logs —
  and the SOC seat is working those alerts."* (Switch the spectator lens to **SOC** to show the alert
  queue if you want.)

### Beat 5 — Hand them the keyboard (1 min) ← kills any "it's scripted" doubt
- In the Live-fire panel, click **Open Kali terminal (real shell)** → a real **root Kali prompt** opens
  in the browser.
- Type live:
  ```bash
  whoami            # root
  nmap target-web   # they watch a real scan run
  nxc smb target-files -u guest -p ''   # real SMB enumeration
  ```
- *"That's a real Kali shell in your browser — same box GoalCert drives. Nothing is faked."*

### Beat 6 — The story (30s)
- *"Same role-based engine as before — Red/Blue/SOC, human or auto — but now backed by real VMs and
  real tools. This is the TryHackMe/Hack-The-Box layer, with our structured purple-team scoring on top."*

---

## Part 4 — Optional deeper beats

**Phase 2 — real Active Directory (if you've provisioned the DC, see `LIVE-FIRE-AD-SETUP.md`):**
- Set `GOALCERT_LAB_BACKEND=windows_ad`, restart backend, arm live-fire, drive Red to **DCSync** →
  real `impacket-secretsdump` dumps real domain hashes (incl. `krbtgt`); show the DC's Event Viewer.

**Phase 3 — multi-tenant isolation (impressive for "it's a product"):**
- *"Every team gets their own private range."* Show it via the API:
  ```powershell
  curl -X POST http://localhost:8000/api/lab/session/teamA/up     # returns teamA's own terminal_url
  curl -X POST http://localhost:8000/api/lab/session/teamB/up     # a SEPARATE isolated range
  ```
  Each gets its own network + its own Kali shell URL. Tear down: `.../session/teamA/down`.

---

## Part 5 — Reset / teardown

- **Reset DVWA between runs:** in the DVWA tab → *Setup → Create / Reset Database*.
- **Fresh range:** `docker compose -f infrastructure/docker-compose.lab.yml -p gclab restart`
- **Stop everything:** `docker compose -f infrastructure/docker-compose.lab.yml -p gclab down`
  (and Ctrl-C the backend/frontend terminals).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Live-fire panel says "Range stopped" | `docker compose -f infrastructure/docker-compose.lab.yml -p gclab up -d` |
| "Arm" button disabled | Range isn't up yet, or attacker still booting — wait, hit the refresh icon |
| Action runs but no real output block | Live-fire not armed, or the action isn't tool-backed (only recon/web/SMB actions are on the Docker range) |
| `nmap` shows "Operation not permitted" | The attacker needs NET_RAW — already set in compose; recreate: `... up -d --force-recreate attacker` |
| Backend can't reach the lab | Lab must be project **`gclab`** (the engine's default). The setup script uses `-p gclab`. |
| DVWA tab won't load | Re-query the port: `docker compose -f infrastructure/docker-compose.lab.yml -p gclab port target-web 80` |

**Pre-flight (run this 10 min before you present):**
```powershell
docker compose -f infrastructure/docker-compose.lab.yml -p gclab ps     # 3 running
curl http://localhost:8000/api/lab/status                                # up:true, attacker_ready:true
# open http://localhost:5173 and confirm a mission starts + Arm works
```
