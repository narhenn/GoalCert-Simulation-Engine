# GoalCert Live-Fire Range — Setup & Demo Guide

This turns GoalCert from a tabletop simulation into a **real cyber range**: the same role-based
live sessions (Red / Blue / SOC, human or auto-pilot), but mapped Red actions now execute **real
free/open-source tools** against **real vulnerable targets**, and detections come from the targets'
**real service logs**.

It is **off by default** — every existing simulation, mission and test behaves exactly as before
until a host arms **Live-fire** on a session.

---

## What's integrated (Phase 1 — local Docker range)

| Function | Tool (free / OSS) | Status |
|---|---|---|
| Network recon & service discovery | **Nmap** | ✅ integrated |
| Web vulnerability scanning | **Nikto** | ✅ integrated |
| SMB / AD enumeration & cred testing | **NetExec (nxc)** | ✅ integrated |
| Active Directory credential attacks | **Impacket** | ✅ integrated (needs the Phase-2 Windows lab) |
| Detection | **Live target-log inspection** | ✅ integrated (no SIEM needed) |

Everything else (Metasploit, BloodHound, Caldera, Wazuh, Sysmon, Suricata, Velociraptor, TheHive…)
is shown in the in-app **Tool Catalog** as `Roadmap`, plus a reserved `Provided` slot for
GoalCert-managed tooling — visible but not wired yet. One tool per function; room to grow.

### The lab (an isolated Docker network — never exposed to your LAN/internet)
- `attacker` — real **Kali Linux** with nmap / nikto / impacket / netexec **+ a browser shell (ttyd)**
- `target-web` — **DVWA** intentionally-vulnerable web app
- `target-files` — **Samba** file server with a weak account

Run as a shared range (`-p gclab`, the engine's default) or one isolated range per session (Phase 3).
Host ports for DVWA and the Kali shell are assigned dynamically — the setup script prints them, and
the **Live-fire panel** shows an **"Open Kali terminal"** button.

---

## Prerequisites (Mac + Windows, identical)

- **Docker Desktop** (the only hard requirement for the lab) — give it ≥ 4 GB RAM
- The GoalCert backend (Python) and frontend (Node) you already run

> **Cross-platform note:** the lab runs in Docker, so it works the same on Windows and Intel Macs.
> On **Apple-Silicon Macs**, Docker runs the x86 images via emulation (slower but functional); for a
> production multi-user range you'd move the lab to a server/cloud backend (the `LabBackend`
> interface is already built for that — see *Growing this* below).

---

## One-time setup

**Windows (PowerShell):**
```powershell
pwsh infrastructure/lab-setup.ps1
```
**macOS / Linux:**
```bash
bash infrastructure/lab-setup.sh
```
This builds the Kali image, pulls the targets, starts the range, and smoke-tests a real nmap. Run it
once before a demo so everything is cached and starts instantly.

You can also drive the lab from the app: **POST `/api/lab/up`** / **`/api/lab/down`**, or the
**Start range / Stop** buttons in the Live-fire panel (host only).

---

## Running a live-fire session (the demo)

1. **Start the lab** (setup script, or the *Start range* button in the session's Live-fire panel).
2. **Start the backend & frontend** as usual.
3. Go to **Live Multiplayer**, start a **mission** (e.g. *Identity Security Assessment* or
   *Red Team Operation*), and enter the room as **host**.
4. In the right-hand **Live-fire range** panel, confirm `Range up · attacker ready`, then click
   **Arm**. The header shows a red **`LIVE-FIRE · REAL TOOLS`** badge.
   - Leave Blue/SOC on **auto** (or have teammates take them) — same role model as before.
5. Take the **Red** seat and run an action that's backed by a real tool:
   - **Active service fingerprinting** → real `nmap -sV` against `target-web`
   - **Web vulnerability scan** → real `nikto`
   - **SMB enumeration** → real `nxc smb`
6. Watch the **Operation log**: each action shows a terminal block with the **real command**, the
   **real tool output**, and a green **DETECTED** badge when the target's log caught it — which the
   SOC seat picks up in its alert queue.

> The Active-Directory actions (LSASS dump, DCSync, Kerberoast, lateral move) are mapped to Impacket
> but show **"needs the Windows-AD lab (Phase 2)"** on the Docker range — honest, and they light up
> automatically once the Windows lab backend is added.

**Stop the lab when done:**
```
docker compose -f infrastructure/docker-compose.lab.yml -p gclab down
```

---

## How it fits together

```
Red action (human or auto)
   │  (live-fire armed + lab up + action is mapped)
   ▼
session.execute_red_action ──queues──▶ manager.run_live_fire ──asyncio.to_thread──▶
   lab.run_in_attacker("nmap …")  →  docker compose -p <proj> exec attacker  →  real Kali tool  →  target
                                                                         │
   SOC alert queue ◀── detection ◀── lab.run_in_target(grep service log) ◀┘
```

- `app/lab/base.py` — the provider-agnostic `LabBackend` interface (the seam)
- `app/lab/docker_lab.py` — the Docker implementation (this lab)
- `app/lab/tools.py` — the tool registry (integrated / roadmap / provided)
- `app/lab/live_fire.py` — maps live Red actions → real commands + detection probes
- `app/live/session.py` — additive hook: queues a job when armed, attaches the result to the event
- `app/api/lab.py` — `/api/lab/status` · `/tools` · `/live-fire` · `/up` · `/down`

The modeled simulation still runs underneath and remains the scoring backbone; real output and real
detection are layered on top, so the match logic and all 68 backend tests are unaffected.

---

## Growing this (the roadmap the architecture already supports)

- **Phase 2 — Windows-AD lab:** add a `LabBackend` (Vagrant/VirtualBox locally, or Proxmox/cloud)
  that provisions a Domain Controller + workstation with Sysmon. The Impacket actions become real;
  swap the detection probe for the already-scaffolded **Wazuh**/**Sysmon** bridges.
- **Phase 3 — multi-user product:** move the backend to a server/cloud, add browser access
  (Guacamole/Kasm) and per-session isolation (WireGuard). Nothing in the engine changes — only a new
  `LabBackend` implementation behind the same interface.
- **More tools per function:** flip a `Tool` from `planned` to `integrated` in `tools.py` and add its
  `FireSpec` mapping in `live_fire.py`.

---

## Safety
The lab network (`172.30.0.0/24`) is isolated and not published to your host LAN. The vulnerable
targets must never be exposed to the internet. Use snapshots/`down`+`up` to reset between sessions.
Only run this against the bundled targets or systems you are explicitly authorized to test.
