# UniFi VLAN Configuration
> Eirdom — VLAN & Network Reference
> Last Updated: April 2026

---

## Network Topology Overview

```
Internet
    │
    ▼
UDM-Pro-Max (10.1.1.1) — Gateway / Firewall / UniFi Controller / Protect NVR
    │
    │  (10G SFP+ uplink)
    ▼
USW-Pro-Max-48-PoE — CORE (Garage, 10.1.1.2)
│  720W PoE Budget | 16x 2.5GbE PoE++ | 8x 1GbE PoE++ | 4x 10G SFP+
│  Etherlighting — port color = native VLAN
│
├── All house Cat6 home-runs (APs, wall plates, camera drops)
│
│  (10G SFP+ trunk)
▼
USW-Pro-Max-48-PoE — DISTRIBUTION (Garage / Server Room, 10.1.1.3)
│  720W PoE Budget | 16x 2.5GbE PoE++ | 8x 1GbE PoE++ | 4x 10G SFP+
│  Etherlighting — port color = native VLAN
│
├── EIRDOM-PVE-01      (10.1.10.5)   — 2.5GbE, VLAN-aware trunk
├── EIRDOM-DOCKER-01   (10.1.50.10)  — 2.5GbE, VLAN 50
├── EIRDOM-WAZUH-01    (10.1.60.10)  — via Proxmox vmbr0
├── EIRDOM-SONION-01   (10.1.60.20)  — via Proxmox vmbr0
└── Access Door Hubs   (VLAN 40)     — PoE++ ports
```

> All ethernet runs in the house are Cat6 home-runs terminating at the
> core switch in the garage. There are no intermediate switches inside
> the house.

> **Etherlighting:** Both switches support Etherlighting — each port
> illuminates to indicate link speed, port location, and native VLAN
> color when used with Ubiquiti Etherlighting patch cables. This gives
> an immediate visual VLAN map when standing at the rack, which is
> particularly useful during initial deployment and troubleshooting.

---

## VLAN Reference Table

| VLAN ID | Name | Subnet | Gateway | DHCP | Purpose |
|---------|------|--------|---------|------|---------|
| 1 | Management | 10.1.1.0/24 | 10.1.1.1 | UDM (Shadow Mode) | UniFi devices — switches, APs, UDM itself |
| 10 | Corporate | 10.1.10.0/24 | 10.1.10.1 | EIRDOM-DC-01 via Relay | AD domain, servers, trusted workstations |
| 20 | IoT | 10.1.20.0/24 | 10.1.20.1 | UDM (Shadow Mode) | Smart home, TVs, speakers, thermostats |
| 30 | Guest | 10.1.30.0/24 | 10.1.30.1 | UDM (Shadow Mode) | Guest Wi-Fi — internet only |
| 40 | Cameras | 10.1.40.0/24 | 10.1.40.1 | UDM (Shadow Mode) | UniFi Protect cameras, access control, SuperLink |
| 50 | Docker | 10.1.50.0/24 | 10.1.50.1 | UDM (Shadow Mode) | Docker host, Traefik, Cloudflare Tunnel, media |
| 60 | Security | 10.1.60.0/24 | 10.1.60.1 | UDM (Shadow Mode) | Wazuh, Security Onion — monitoring only |

---

## DHCP Configuration

All VLANs use the UDM-Pro-Max as the DHCP gateway with **Shadow Mode
enabled**, with the exception of VLAN 10 which relays to EIRDOM-DC-01.

### Shadow Mode

Shadow Mode allows the UDM to remain aware of all DHCP leases on the
network even when an external DHCP server (like Windows Server) is
handling assignments. This keeps the UniFi client list accurate and
allows the UDM to enforce firewall rules by hostname and IP.

**Configure in:** UniFi Network → Settings → Networks → (edit each
network) → DHCP → Enable Shadow Mode

### VLAN 10 — DHCP Relay to Active Directory

VLAN 10 DHCP is handled exclusively by EIRDOM-DC-01. The UDM acts as
a relay only — it does not issue leases on this segment.

**Configure in:** UniFi Network → Settings → Networks → Corporate →
DHCP Mode → DHCP Relay → Relay Server: `10.1.10.10`

### DHCP Scopes (UDM-Managed VLANs)

| VLAN | Range Start | Range End | Lease Time | DNS |
|------|------------|-----------|------------|-----|
| 1 — Management | 10.1.1.100 | 10.1.1.200 | 24h | 10.1.1.1 |
| 20 — IoT | 10.1.20.100 | 10.1.20.250 | 24h | 10.1.20.1 |
| 30 — Guest | 10.1.30.100 | 10.1.30.250 | 4h | 1.1.1.1, 9.9.9.9 |
| 40 — Cameras | 10.1.40.100 | 10.1.40.200 | 24h | 10.1.40.1 |
| 50 — Docker | 10.1.50.100 | 10.1.50.250 | 24h | 10.1.10.10 |
| 60 — Security | 10.1.60.100 | 10.1.60.200 | 24h | 10.1.10.10 |

> **NOTE:** Guest DNS is set to public resolvers (Cloudflare + Quad9)
> intentionally. Guests should not query the internal AD DNS server.

> **NOTE:** VLAN 50 and 60 DNS points to EIRDOM-DC-01 (10.1.10.10) so
> Docker services and security tools can resolve internal hostnames like
> `jellyfin.eirdom.homes` and `wazuh.eirdom.homes`.

---

## Static IP Assignments

All servers and infrastructure devices use static IPs configured at
the OS level — not as DHCP reservations — so they remain consistent
regardless of DHCP server availability.

### VLAN 1 — Management

| IP Address | Hostname | Device | Role |
|------------|----------|--------|------|
| 10.1.1.1 | udm-pro-max | UDM-Pro-Max | Gateway / Firewall / Controller |
| 10.1.1.2 | usw-core-01 | USW-Pro-Max-48-PoE (Core) | Core Switch |
| 10.1.1.3 | usw-dist-01 | USW-Pro-Max-48-PoE (Distribution) | Distribution Switch |

### VLAN 10 — Corporate

| IP Address | Hostname | Device | Role |
|------------|----------|--------|------|
| 10.1.10.1 | — | UDM-Pro-Max | VLAN 10 Gateway |
| 10.1.10.5 | EIRDOM-PVE-01 | Proxmox Host | Primary Hypervisor |
| 10.1.10.10 | EIRDOM-DC-01 | Windows Server 2025 VM | AD DS, DNS, DHCP, NPS |
| 10.1.10.12 | EIRDOM-SUB-01 | Windows Server 2025 VM | Subordinate / Issuing CA |

> EIRDOM-RCA-01 (Offline Root CA) has no network IP — it is air-gapped
> with no network adapter attached in Proxmox.

### VLAN 50 — Docker

| IP Address | Hostname | Device | Role |
|------------|----------|--------|------|
| 10.1.50.1 | — | UDM-Pro-Max | VLAN 50 Gateway |
| 10.1.50.10 | EIRDOM-DOCKER-01 | Docker Host | Traefik, Cloudflared, ARR Stack, Jellyfin, WordPress |

### VLAN 60 — Security

| IP Address | Hostname | Device | Role |
|------------|----------|--------|------|
| 10.1.60.1 | — | UDM-Pro-Max | VLAN 60 Gateway |
| 10.1.60.10 | EIRDOM-WAZUH-01 | Ubuntu 24.04 LTS VM | Wazuh Manager + Indexer + Dashboard |
| 10.1.60.20 | EIRDOM-SONION-01 | Oracle Linux 9 VM | Security Onion 3.0 Standalone |

---

## Switch Port Profiles (Summary)

Full profile definitions are in [`port-profiles.md`](port-profiles.md).
Summary for quick reference:

| Profile | Native VLAN | Tagged VLANs | PoE | Speed | Used For |
|---------|------------|--------------|-----|-------|----------|
| `profile_disabled` | — | None | Off | — | Unused ports |
| `profile_mgmt` | 1 | None | Off | 1G | Management drops |
| `profile_trunk_all` | 1 | 10,20,30,40,50,60 | Off | 10G | Switch + UDM uplinks |
| `profile_trunk_ap` | 1 | 10,20,30 | 802.3at | Auto | All AP uplinks |
| `profile_corporate` | 10 | None | Off | Auto | Wired workstations |
| `profile_corporate_25g` | 10 | None | Off | 2.5G | High-throughput devices |
| `profile_iot` | 20 | None | 802.3af | 1G | Wired IoT devices |
| `profile_camera` | 40 | None | 802.3at | 1G | Protect cameras, doorbells |
| `profile_access_hub` | 40 | None | 802.3bt | Auto | UniFi Access Door Hubs |
| `profile_superlink` | 40 | None | 802.3af | 100M | SuperLink Gateways |
| `profile_docker` | 50 | None | Off | 2.5G | Docker host NIC |
| `profile_server` | 10 | 10, 60 | Off | 2.5G | Proxmox hypervisor |
| `profile_security` | 1 | 10,20,30,40,50,60 | Off | 1G | Security Onion SPAN |

---

## Core Switch — USW-Pro-Max-48-PoE (10.1.1.2)

Located in the garage. All house Cat6 home-runs terminate here.
720W PoE budget. Etherlighting on all RJ45 ports.

### Uplinks

| Port | Speed | Profile | Connected To | Notes |
|------|-------|---------|-------------|-------|
| SFP+ 1 | 10G | `profile_trunk_all` | UDM-Pro-Max | WAN/LAN uplink |
| SFP+ 2 | 10G | `profile_trunk_all` | USW-Pro-Max-48-PoE (Distribution) | Inter-switch trunk |
| SFP+ 3–4 | 10G | `profile_disabled` | _(reserved)_ | Future uplinks |

### AP Ports (PoE)

| Port | Speed | Profile | AP | Location | Notes |
|------|-------|---------|-----|----------|-------|
| 2 | 1G PoE+ | `profile_trunk_ap` | AP-MAIN-01 (U7 Pro) | Living Room | 802.3at |
| 3 | 1G PoE+ | `profile_trunk_ap` | AP-MAIN-02 (U7 Pro) | Hallway | 802.3at |
| 4 | 2.5G PoE++ | `profile_trunk_ap` | AP-WALL-01 (U7 Pro Wall) | Office | 802.3bt required |
| 5 | 1G PoE+ | `profile_trunk_ap` | AP-OUT-01 (U7 Pro Outdoor) | Garage / Exterior | 802.3at |
| 6 | 1G PoE+ | `profile_trunk_ap` | AP-LITE-01 (U7 Lite) | Bedroom Wing | 802.3af |
| 7 | 1G PoE+ | `profile_trunk_ap` | AP-LITE-02 (U7 Lite) | Server Room | 802.3af |

### Camera & Security Ports (PoE)

| Port | Speed | Profile | Device | Location | Notes |
|------|-------|---------|--------|----------|-------|
| 8 | 1G PoE+ | `profile_camera` | G6 180 | House — Left Side | 802.3at |
| 9 | 1G PoE+ | `profile_camera` | G6 180 | House — Right Side | 802.3at |
| 10 | 1G PoE+ | `profile_camera` | G6 180 | Garage — Left Side | 802.3at |
| 11 | 1G PoE+ | `profile_camera` | G6 180 | Garage — Right Side | 802.3at |
| 12 | 1G PoE+ | `profile_camera` | G6 Bullet | Garage Interior | 802.3af |
| 13 | 1G PoE+ | `profile_camera` | G6 Turret | Front Door Area | 802.3af |
| 14 | 1G PoE+ | `profile_camera` | G4 Doorbell Pro (doorbell) | Front Door | 802.3af |
| 15 | 1G PoE+ | `profile_camera` | G4 Doorbell Pro (chime) | Interior | 802.3af |
| 16 | 1G PoE | `profile_superlink` | SuperLink Gateway 1 | Interior — High Mount | 802.3af |
| 17 | 1G PoE | `profile_superlink` | SuperLink Gateway 2 | Garage — High Mount | 802.3af |

### AI Theta Port

| Port | Speed | Profile | Device | Location | Notes |
|------|-------|---------|--------|----------|-------|
| 18 | 1G PoE+ | `profile_camera` | AI Theta Hub | Interior room | Hub only — lenses via USB-C |

### Wall Plate / Access Ports (House Drops)

| Port | Speed | Profile | Location | Notes |
|------|-------|---------|----------|-------|
| 20 | 1G | `profile_corporate` | Office — desk drop 1 | Workstation |
| 21 | 1G | `profile_corporate` | Office — desk drop 2 | Workstation / secondary |
| 22 | 1G | `profile_corporate` | Living Room — media | Smart TV or wired device |
| 23 | 1G | `profile_iot` | Living Room — IoT | Smart hub / Sonos / etc. |
| 24 | 1G | `profile_corporate` | Master Bedroom | Workstation / wired device |
| 25–40 | 1G | `profile_corporate` | _(remaining house drops)_ | Update as drops are finalized |
| 41–46 | 2.5G | `profile_corporate_25g` | _(reserved 2.5G drops)_ | Future high-throughput drops |
| 47–48 | — | `profile_disabled` | _(unused)_ | Disabled |

> Update port assignments as Cat6 drops are finalized during
> construction. Etherlighting will illuminate each active port in the
> color of its native VLAN, making wiring audits straightforward.

---

## Distribution Switch — USW-Pro-Max-48-PoE (10.1.1.3)

Located in the garage server room. All server, VM, and access control
traffic flows through here. 720W PoE budget. Etherlighting on all
RJ45 ports.

### Uplinks

| Port | Speed | Profile | Connected To | Notes |
|------|-------|---------|-------------|-------|
| SFP+ 1 | 10G | `profile_trunk_all` | USW-Pro-Max-48-PoE (Core) | Inter-switch trunk |
| SFP+ 2–4 | 10G | `profile_disabled` | _(reserved)_ | Future uplinks or NAS |

### Server Ports (2.5GbE)

| Port | Speed | Profile | Device | IP | Notes |
|------|-------|---------|--------|----|-------|
| 41 | 2.5G | `profile_server` | EIRDOM-PVE-01 (NIC 1) | 10.1.10.5 | Proxmox mgmt + VM traffic via VLAN-aware vmbr0 |
| 42 | 2.5G | `profile_docker` | EIRDOM-DOCKER-01 | 10.1.50.10 | Docker host — all container traffic |

> **Why 2.5GbE for servers:** EIRDOM-PVE-01 carries all VM traffic
> including AD, PKI, Wazuh, and Security Onion management. EIRDOM-DOCKER-01
> runs Jellyfin 4K streams, Traefik, ARR stack, and Cloudflared
> simultaneously. 2.5GbE provides meaningful headroom over 1GbE without
> requiring 10GbE NIC hardware upgrades.

### Security Onion SPAN Port

| Port | Speed | Profile | Device | Notes |
|------|-------|---------|--------|-------|
| 43 | 1G | `profile_security` | EIRDOM-SONION-01 (Monitor NIC) | Passive SPAN — no IP, mirrors UDM uplink port |

### Access Control Ports (PoE++)

| Port | Speed | Profile | Device | Location | Notes |
|------|-------|---------|--------|----------|-------|
| 25 | 1G PoE++ | `profile_access_hub` | UA-Hub-Door 1 | Front Door | 802.3bt, 50W max |
| 26 | 1G PoE++ | `profile_access_hub` | UA-Hub-Door 2 | Garage / Secondary Door | 802.3bt, 50W max |

### Spare / Future Ports

| Port | Profile | Notes |
|------|---------|-------|
| 1–24 | `profile_disabled` | Reserved for future servers, NAS, or additional VMs |
| 27–40 | `profile_disabled` | Reserved for additional PoE++ devices |
| 44–48 | `profile_disabled` | Reserved |

---

## Proxmox VLAN Bridge Reference

Proxmox uses a single VLAN-aware bridge (vmbr0) on EIRDOM-PVE-01. Each
VM is assigned its VLAN at the virtual NIC level — the physical switch
port passes tagged traffic for all relevant VLANs.

| VM | VLAN Tag on vmbr0 | IP Address | Notes |
|----|------------------|------------|-------|
| EIRDOM-DC-01 | 10 | 10.1.10.10 | AD DS, DNS, DHCP, NPS |
| EIRDOM-SUB-01 | 10 | 10.1.10.12 | Subordinate / Issuing CA |
| EIRDOM-RCA-01 | None (no NIC) | Air-gapped | Offline Root CA — no network adapter in Proxmox |
| EIRDOM-WAZUH-01 | 60 | 10.1.60.10 | Wazuh Manager + Indexer + Dashboard |
| EIRDOM-SONION-01 | 60 | 10.1.60.20 | Security Onion — management NIC only |

> **Security Onion dual NIC:** Security Onion has two NICs inside
> Proxmox — a management NIC on VLAN 60 (above), and a dedicated
> monitor/capture NIC that connects to the SPAN port on the distribution
> switch (`profile_security`, port 43). The capture NIC has no IP address.

---

## Inter-VLAN Routing & Firewall Summary

All inter-VLAN routing is handled by the UDM-Pro-Max. See
[`firewall-rules.md`](firewall-rules.md) for the full rule set.

| Source VLAN | Destination | Action | Reason |
|-------------|------------|--------|--------|
| VLAN 10 (Corporate) | All VLANs | Allow | Trusted devices have full access |
| VLAN 20 (IoT) | VLAN 10 | Block | IoT cannot reach corporate |
| VLAN 20 (IoT) | Internet | Allow | IoT gets internet only |
| VLAN 30 (Guest) | All RFC1918 | Block | Guests cannot reach any internal network |
| VLAN 30 (Guest) | Internet | Allow | Guests get internet only |
| VLAN 40 (Cameras) | 10.1.1.1 TCP 7443/7444 | Allow | Cameras to Protect NVR only |
| VLAN 40 (Cameras) | Any | Block | Cameras fully isolated |
| VLAN 50 (Docker) | VLAN 10 TCP/UDP 53 | Allow | Docker resolves internal DNS |
| VLAN 50 (Docker) | Internet | Allow | Tunnel + downloads |
| VLAN 50 (Docker) | VLAN 10 (all else) | Block | Docker cannot reach corporate |
| VLAN 60 (Security) | All VLANs | Allow | Full visibility for monitoring |

---

## UniFi Controller Configuration Paths

| Task | Path |
|------|------|
| Create / edit VLANs | Settings → Networks → Create New Network |
| Configure DHCP scopes | Settings → Networks → (edit) → DHCP |
| Configure DHCP Relay (VLAN 10) | Settings → Networks → Corporate → DHCP → DHCP Relay |
| Enable Shadow Mode | Settings → Networks → (edit) → DHCP → Shadow Mode |
| Create port profiles | Settings → Profiles → Switch Ports |
| Assign port profiles | Devices → (switch) → Ports |
| Configure port mirroring | Devices → (distribution switch) → Settings → Port Mirroring |
| Configure Etherlighting | Devices → (switch) → Settings → Etherlighting |
| RADIUS profile | Settings → Profiles → RADIUS |

---

## Related Documentation

- [`wireless.md`](wireless.md) — SSID configuration, RF profiles, AP groups
- [`firewall-rules.md`](firewall-rules.md) — Full inter-VLAN firewall rule set
- [`port-profiles.md`](port-profiles.md) — Detailed switch port profile definitions
- [`Eirdom_Infrastructure_Guide_v3.docx`](../docs/Eirdom_Infrastructure_Guide_v3.docx) — Full infrastructure guide including Proxmox vmbr0 config, AD DHCP setup, and Security Onion SPAN configuration