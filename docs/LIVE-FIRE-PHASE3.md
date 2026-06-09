# GoalCert Live-Fire — Phase 3: Multi-User Product

Phase 1 made attacks/detection real on a shared Docker range. Phase 2 made the Active-Directory
attacks real on a Windows DC. **Phase 3 turns it into a multi-user product** — the THM/HTB-style step:
a real attacker shell in the browser, and a private isolated range per session.

Two pieces ship **and are verified locally now**; the third is the hosted-deployment path that uses
the same interfaces.

---

## 3A — Real Kali shell in the browser (shipped, verified)

The attacker box now runs **ttyd**, serving an interactive shell over HTTP. In a live session's
**Live-fire range** panel (when the range is up) there's an **"Open Kali terminal (real shell)"**
button — it opens a real root Kali prompt in a new tab with `nmap` / `nikto` / `impacket` / `nxc`
preinstalled. This is the strongest demo proof: hand the audience the keyboard and let them run
`nmap target-web` themselves.

- Backend: `DockerComposeLab.attacker_terminal_url()` resolves the mapped host port for ttyd (7681);
  `GET /api/lab/status` returns `terminal_url`.
- It's a genuine shell on the same container the engine drives — what they type and what GoalCert
  scores hit the same real tools and targets.

## 3B — Per-session isolated ranges (shipped, verified)

Each live session can get its **own** range — its own Docker compose **project** (`gc-<session>`),
its own **network**, and its own **random host ports** — so concurrent teams/users can't see or touch
each other. This is the local, verifiable equivalent of the per-user environments THM/HTB spin up.

- `SessionLabPool` (`app/lab/pool.py`) provisions/teardowns one range per session, with a concurrency
  cap (`GOALCERT_LAB_POOL_MAX`, default 3).
- API: `POST /api/lab/session/{id}/up` · `POST /api/lab/session/{id}/down` ·
  `GET /api/lab/session/{id}/status` (each returns that session's own `terminal_url`).
- Live-fire automatically uses a session's own range if one is provisioned, else the shared range
  (`manager.run_live_fire`: `get_pool().get(sid) or get_lab()`).

> Verified: two sessions get two isolated ranges on separate networks with distinct terminal ports;
> real `nmap` runs inside each; teardown frees the slot.

---

## 3C — Hosted deployment (the production path)

Everything above runs on one host. To serve real users over the internet, move the compute off the
laptop and put access behind a gateway. The `LabBackend` + `SessionLabPool` interfaces are the seam —
no engine changes, just a new backend.

### Compute — where the ranges run
| Option | Use it for | Notes |
|---|---|---|
| **Proxmox VE** on a server/mini-PC | Best price/perf for AD ranges | clone-from-template + snapshot reset; a `ProxmoxLabBackend` implements `LabBackend` |
| **Cloud** (AWS/Azure/GCP) | Elastic scale, no hardware | one VM/stack per session; tag + auto-expire to control cost |
| **Docker on a beefy host** | Container targets at scale | what we run now, just centralized |

A `ProxmoxLab`/`CloudLab` implements the same `status/up/down/run_in_attacker/run_in_target` methods
the engine already calls; `SessionLabPool` swaps `DockerComposeLab` for it.

### Access — browser, no client install
| Tool (free/OSS) | Gives the user | When |
|---|---|---|
| **ttyd** (already integrated) | a terminal (Kali shell) | shell-only attackers — works today |
| **Apache Guacamole** | full **RDP/VNC/SSH desktop** in the browser | needed to give a human a Windows/Kali *desktop* (Phase 2 AD work) |
| **Kasm Workspaces** | streamed containerized desktops | polished, heavier; commercial tiers exist (community is free) |

Put Guacamole (or Kasm) in front; map each session's attacker/desktop to a per-user connection.

### Network isolation
- **WireGuard** per session: each user gets a config that lands them on *their* range's network only.
- Or keep it browser-only (Guacamole/ttyd over HTTPS) and never expose the range networks at all —
  simplest and safest.
- Each session range already has its own Docker/Proxmox network; the gateway enforces who reaches which.

### Reference topology
```
  Users (browser only) ──HTTPS──▶  Reverse proxy (TLS)
                                      │
                                      ├─▶ GoalCert backend/frontend  (control plane: scoring, timeline)
                                      └─▶ Guacamole / ttyd           (access plane: shells & desktops)
                                                │
                              SessionLabPool ──▶ Proxmox / Cloud / Docker   (compute plane)
                                                │   one isolated range per session
                                                ▼
                                     attacker + targets (+ Windows DC for AD)
                                                │
                                     Sysmon/Wazuh telemetry ──▶ detection bridge ──▶ SOC queue
```

### Build order for hosting
1. Stand up the compute host (Proxmox or a cloud account) and put the range there.
2. Implement `ProxmoxLabBackend`/`CloudLabBackend` (same `LabBackend` interface) and point
   `SessionLabPool` at it.
3. Front it with Guacamole (full desktops) + a TLS reverse proxy; keep range networks private.
4. Add accounts/quotas + per-session TTL/auto-reap (cost + hygiene).

---

## What to install for each phase (recap)
- **Phase 1 (now):** Docker Desktop. `infrastructure/lab-setup.ps1`/`.sh`.
- **Phase 2 (AD):** a Windows DC (Vagrant+VirtualBox / cloud / Proxmox) + `pip install impacket pywinrm`
  on the host. See `docs/LIVE-FIRE-AD-SETUP.md`.
- **Phase 3 hosting:** a compute host (Proxmox/cloud) + Apache Guacamole + a TLS reverse proxy
  (+ optional WireGuard).

## Safety
Per-session ranges are isolated networks and are never exposed to your LAN beyond the random localhost
ports Docker maps. In a hosted deployment, keep range networks private and reach them only through the
gateway. Cap concurrency and auto-reap idle ranges. Only target the bundled vulnerable systems.
