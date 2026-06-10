"""Live host-graph topology — the heart of the immersive scenario, shared by every team view.

A `Topology` is VLANs of named `Host`s with TCP/445 reachability edges. Hosts move through the W1
state machine (healthy→vulnerable→exploited→infected→propagating→encrypting→impacted, +dormant/
contained/eradicated/recovered). The engine mutates this graph; the frontend renders it as the
structured VLAN map (colour per state, scan rays, strike flashes, expanding red zone).

We model ~24 *named, representative* hosts across 3 VLANs plus an `extra_hosts` counter for the rest
of the 250-host hospital — enough to feel like a real network without drawing 250 nodes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Per-host lifecycle (W1 design doc §8/§12). Colour mapping lives in the frontend.
HOST_STATES = (
    "healthy", "vulnerable", "exploited", "infected", "propagating",
    "encrypting", "impacted", "dormant", "contained", "eradicated", "recovered",
)
# States that count as "the worm holds this host" (a live foothold that can spread / be encrypted).
LIVE_INFECTED = {"infected", "propagating", "encrypting"}


@dataclass
class Host:
    id: str
    name: str
    vlan: str
    role: str = "workstation"          # workstation | fileserver | database | domain_controller | backup | appserver | email
    state: str = "healthy"
    vulnerable: bool = False           # exposes legacy SMBv1 (the worm's vector)
    revealed: bool = False             # discovered by Red's recon yet?
    patient_zero: bool = False
    flags: set[str] = field(default_factory=set)   # persistent, recovery_disabled, encrypted

    def public(self) -> dict:
        return {
            "id": self.id, "name": self.name, "vlan": self.vlan, "role": self.role,
            "state": self.state, "vulnerable": self.vulnerable, "revealed": self.revealed,
            "patient_zero": self.patient_zero, "flags": sorted(self.flags),
        }


@dataclass
class Vlan:
    id: str
    name: str
    reachable: tuple[str, ...] = ()    # vlan ids reachable from here on TCP/445

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "reachable": list(self.reachable)}


@dataclass
class Topology:
    hosts: dict[str, Host]
    vlans: dict[str, Vlan]
    extra_hosts: int = 0               # unnamed remainder of the fleet (still counts toward totals)
    cut_edges: set[tuple[str, str]] = field(default_factory=set)   # segmented vlan pairs (a,b) unordered

    # ---- queries -------------------------------------------------------------
    def by_vlan(self, vlan_id: str) -> list[Host]:
        return [h for h in self.hosts.values() if h.vlan == vlan_id]

    def reachable_vlans(self, vlan_id: str) -> set[str]:
        out = set()
        for dst in self.vlans[vlan_id].reachable:
            pair = tuple(sorted((vlan_id, dst)))
            if pair not in self.cut_edges:
                out.add(dst)
        return out

    def spread_targets(self, src: Host) -> list[Host]:
        """Healthy+vulnerable hosts the worm could reach from an infected `src` (reachability-gated)."""
        reach = self.reachable_vlans(src.vlan)
        return [h for h in self.hosts.values()
                if h.vlan in reach and h.vulnerable and h.state in ("healthy", "vulnerable")]

    def counts(self) -> dict[str, int]:
        c = {s: 0 for s in HOST_STATES}
        for h in self.hosts.values():
            c[h.state] = c.get(h.state, 0) + 1
        return c

    def total_hosts(self) -> int:
        return len(self.hosts) + self.extra_hosts

    def infected_count(self) -> int:
        return sum(1 for h in self.hosts.values() if h.state in LIVE_INFECTED)

    def impacted_count(self) -> int:
        return sum(1 for h in self.hosts.values() if h.state == "impacted")

    def cut_edge(self, a: str, b: str) -> None:
        self.cut_edges.add(tuple(sorted((a, b))))

    def public(self) -> dict:
        return {
            "vlans": [v.public() for v in self.vlans.values()],
            "hosts": [h.public() for h in self.hosts.values()],
            "extra_hosts": self.extra_hosts,
            "cut_edges": [list(e) for e in sorted(self.cut_edges)],
            "counts": self.counts(),
            "total_hosts": self.total_hosts(),
        }


# ===========================================================================
#  W1 — 250-host hospital. Finance / HR user VLANs + a Server VLAN.
# ===========================================================================
def build_w1() -> Topology:
    hosts: dict[str, Host] = {}

    def add(hid: str, name: str, vlan: str, role: str = "workstation",
            vulnerable: bool = False, state: str = "healthy", pz: bool = False) -> None:
        hosts[hid] = Host(id=hid, name=name, vlan=vlan, role=role, vulnerable=vulnerable,
                          state=state, patient_zero=pz)

    # Finance VLAN — patient zero lives here, already infected and unaware.
    add("fin-014", "FIN-WS-014", "fin", vulnerable=True, state="infected", pz=True)
    for i in (1, 2, 3, 5, 8, 11, 17, 22, 26):
        add(f"fin-{i:03d}", f"FIN-WS-{i:03d}", "fin", vulnerable=(i % 3 != 0))
    # HR VLAN
    for i in (1, 2, 4, 7, 9, 13, 18):
        add(f"hr-{i:03d}", f"HR-WS-{i:03d}", "hr", vulnerable=(i % 2 == 1))
    # Server VLAN — the crown jewels (downing these cascades the business impact).
    add("file-01", "FILE-01", "srv", role="fileserver", vulnerable=True)
    add("db-01", "DB-01", "srv", role="database", vulnerable=False)
    add("dc-01", "DC-01", "srv", role="domain_controller", vulnerable=False)
    add("bkp-01", "BKP-01", "srv", role="backup", vulnerable=False)
    add("app-01", "APP-01", "srv", role="appserver", vulnerable=True)
    add("mail-01", "MAIL-01", "srv", role="email", vulnerable=False)

    vlans = {
        "fin": Vlan("fin", "Finance VLAN", reachable=("fin", "hr", "srv")),
        "hr": Vlan("hr", "HR VLAN", reachable=("hr", "fin", "srv")),
        "srv": Vlan("srv", "Server VLAN", reachable=("srv",)),
    }
    # Patient zero is revealed to Red from the start (assumed breach).
    hosts["fin-014"].revealed = True
    return Topology(hosts=hosts, vlans=vlans, extra_hosts=250 - len(hosts))
