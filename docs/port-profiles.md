# UniFi Switch Port Profiles
> Eirdom — Port Profile Reference
> Last Updated: April 2026

---

## Overview

Port profiles are templates applied to switch ports that define VLAN
behavior, PoE policy, and speed settings. Defining profiles centrally
means you configure once and apply consistently across all ports. Any
future change to a profile propagates to every port using it
automatically.

**Configure in:** UniFi Network → Settings → Profiles → Switch Ports

---

## Switch Hardware — USW-Pro-Max-48-PoE

Both the core and distribution switches are USW-Pro-Max-48-PoE units.
Understanding the port layout is essential for planning PoE++ device
placement before cable runs are finalized.

| Port Range | Qty | Speed | PoE Standard | Max Per Port | Notes |
|-----------|-----|-------|-------------|-------------|-------|
| Ports 1–24 | 24 | 1 GbE | 802.3at (PoE+) | 30W | Standard access and AP ports |
| Ports 25–32 | 8 | 1 GbE | 802.3bt (PoE++) | 60W | High-power 1G ports |
| Ports 33–40 | 8 | 2.5 GbE | 802.3at (PoE+) | 30W | 2.5G access ports |
| Ports 41–48 | 8 | 2.5 GbE | 802.3bt (PoE++) | 60W | High-power 2.5G ports |
| SFP+ 1–4 | 4 | 10 GbE | None | — | Uplinks only |
| **Total PoE Budget** | | | | **720W per switch** | |

> **Etherlighting:** The USW-Pro-Max-48-PoE supports Etherlighting on all
> RJ45 ports. Each port illuminates to indicate link speed, port location,
> and native VLAN/network color when used with compatible Ubiquiti
> Etherlighting patch cables. This gives you an immediate visual map of
> what VLAN each port belongs to when standing at the rack — a significant
> operational advantage during initial deployment and troubleshooting.

> **PoE++ availability:** With 8 x 1GbE PoE++ ports and 8 x 2.5GbE PoE++
> ports per switch, there are 16 x 60W PoE++ ports available. All
> high-power devices in the Eirdom fleet (U7 Pro Wall, Access Door Hubs)
> have dedicated PoE++ ports without any constraint. The separate
> `profile_trunk_ap_poepp` profile from earlier planning is no longer
> needed — assign U7 Pro Wall to any 2.5GbE PoE++ port using
> `profile_trunk_ap`.

---

## PoE Standards Reference

| Standard | Max Wattage | Also Known As | Eirdom Devices |
|----------|------------|---------------|---------------|
| 802.3af | 15.4W (12.95W at PD) | PoE | SuperLink Gateway, G6 Bullet, G6 Turret, AI Theta, G4 Doorbell |
| 802.3at | 30W (25.5W at PD) | PoE+ | U7 Pro, U7 Pro Outdoor, U7 Lite, G6 180 |
| 802.3bt Type 3 | 60W (51W at PD) | PoE++ | U7 Pro Wall, Access Door Hub |
| 802.3bt Type 4 | 100W (71.3W at PD) | PoE++ Ultra | Not currently used |

> **IMPORTANT — Access Hub wiring note:** The UA-Hub-Door and
> UA-Hub-Door-Mini connect to the switch via PoE++ and then power the
> Access Readers (UA-G2-Pro, UA-G3-Pro) from their own internal PoE
> ports. Readers do NOT connect directly to the switch — they connect
> to the hub. Plan switch port PoE budget based on the hub's total draw,
> not the individual reader wattage. Run Cat6 from the switch to the hub
> location, then separate Cat6 from the hub to each reader.

> **IMPORTANT — AI Theta wiring note:** The AI Theta Hub connects to the
> switch via a single PoE Cat6 run. The camera lenses (wide-angle and 360)
> connect to the hub via USB-C — not directly to the switch. Only one
> Cat6 drop is needed per AI Theta deployment, at the hub location.

---

## Profile Definitions

---

### `profile_disabled`

**Purpose:** Applied to all unused switch ports. Prevents unauthorized
devices from connecting to any VLAN.

| Setting | Value |
|---------|-------|
| Port Enabled | No |
| Native VLAN | — |
| Tagged VLANs | None |
| PoE | Disabled |
| Speed | Auto |
| Storm Control | N/A |

> **Best practice:** All unoccupied ports should use this profile. In
> UniFi, a disabled port shows as dark in the topology view and dark in
> Etherlighting, making it easy to audit active vs inactive ports at a
> glance.

---

### `profile_mgmt`

**Purpose:** Management-only access for infrastructure devices that only
need VLAN 1. Used for reserved management drop ports.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 1 (Management) |
| Tagged VLANs | None |
| PoE | Disabled |
| Speed | Auto (1G) |
| Storm Control | Enabled |

---

### `profile_trunk_all`

**Purpose:** Full trunk carrying all VLANs. Used exclusively on the
inter-switch uplink between core and distribution, and the UDM-Pro-Max
uplink. Should appear on very few ports.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 1 (Management) |
| Tagged VLANs | 10, 20, 30, 40, 50, 60 |
| PoE | Disabled |
| Speed | Auto (10G on SFP+ uplinks) |
| Storm Control | Enabled |

> **WARNING:** Only use this profile on switch uplinks. Never apply to
> an end-device port — doing so exposes that device to all VLANs
> simultaneously.

---

### `profile_trunk_ap`

**Purpose:** Trunk for all Access Point uplinks. Carries the three
SSIDs (Trusted, IoT, Guest) but excludes camera, docker, and security
VLANs. APs have no business seeing those segments.

Covers all U7 series APs including the U7 Pro Wall — assign the Pro
Wall to a 2.5GbE PoE++ port (ports 41–48) to satisfy its 802.3bt
power requirement. No separate profile needed.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 1 (Management) |
| Tagged VLANs | 10, 20, 30 |
| PoE | Auto (802.3at) — use PoE++ port for U7 Pro Wall |
| Speed | Auto |
| Storm Control | Enabled |

> **U7 Pro Wall:** Assign to a 2.5GbE PoE++ port (ports 41–48 on the
> USW-Pro-Max-48-PoE). The profile itself is identical — the PoE++
> capability comes from the port, not the profile.

> **U7 Lite:** Requires only 802.3af. Any PoE port on the switch works.

> **U7 Pro / U7 Pro Outdoor:** Require 802.3at. Any PoE+ or PoE++ port
> works.

---

### `profile_corporate`

**Purpose:** Standard access port for trusted wired devices —
workstations, laptops, and any device that should land on VLAN 10.
No PoE — corporate devices use their own power supplies.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 10 (Corporate) |
| Tagged VLANs | None |
| PoE | Disabled |
| Speed | Auto |
| Storm Control | Enabled |

---

### `profile_corporate_25g`

**Purpose:** Same as `profile_corporate` but assigned to 2.5GbE ports
for high-throughput wired workstations, NAS units, or future devices
that benefit from multi-gigabit connectivity.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 10 (Corporate) |
| Tagged VLANs | None |
| PoE | Disabled |
| Speed | Auto (2.5G) |
| Storm Control | Enabled |

---

### `profile_iot`

**Purpose:** Access port for wired IoT devices isolated on VLAN 20.
Smart hubs, wired smart TVs, media players, and similar devices that
don't belong on the trusted network.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 20 (IoT) |
| Tagged VLANs | None |
| PoE | Auto (802.3af) |
| Speed | Auto (1G) |
| Storm Control | Enabled |

> **PoE note:** Enabled at 802.3af to accommodate wired IoT devices that
> may be PoE-powered (smart displays, hubs, etc.). Disable PoE on
> specific ports if the connected device has its own power supply.

---

### `profile_camera`

**Purpose:** Access port for all UniFi Protect cameras, doorbells, and
sensor devices. Devices land on VLAN 40, fully isolated from all other
VLANs by firewall rules. Profile is set to 802.3at to cover the entire
G6 fleet including the G6 180 which requires PoE+.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 40 (Cameras) |
| Tagged VLANs | None |
| PoE | Auto (802.3at) |
| Speed | Auto (1G) |
| Storm Control | Enabled |

**Eirdom camera fleet PoE reference:**

| Device | Location | PoE Standard | Max Draw | Notes |
|--------|----------|-------------|---------|-------|
| G6 180 | House sides + garage sides (×4) | 802.3at | 15W | Dual sensor, 180° panoramic |
| G6 Bullet | Garage interior (×1) | 802.3af | 9.9W | Standard PoE |
| G6 Turret | Front door area (×1) | 802.3af | 12.5W | Standard PoE |
| AI Theta Hub | Interior rooms (×1) | 802.3af | 12.5W | Hub only — lenses connect via USB-C |
| G4 Doorbell Pro PoE (doorbell) | Front door (×1) | 802.3af | 3W | Separate drop from chime |
| G4 Doorbell Pro PoE (chime) | Interior (×1) | 802.3af | 7W | Separate drop from doorbell |

> **G6 180 note:** The G6 180 is the only camera in the fleet that
> requires 802.3at (PoE+). Profile is set to 802.3at so all cameras
> including the G6 180 work from the same profile. 802.3at is backward
> compatible with all 802.3af cameras in the fleet.

> **G4 Doorbell Pro PoE kit note:** The kit includes two separate PoE
> devices — the doorbell unit at the front door and the chime inside the
> house. Plan for two Cat6 drops: one to the doorbell mounting location
> and one to the chime location. Both use `profile_camera` on VLAN 40.

> **AI Theta indoor note:** The AI Theta Hub is rated for indoor use
> only. Do not deploy in unconditioned spaces such as the garage or
> exterior locations.

---

### `profile_access_hub`

**Purpose:** Access port for UniFi Access Door Hubs (UA-Hub-Door,
UA-Hub-Door-Mini). The hub connects to the switch and then powers
Access Readers from its own internal PoE ports. Assign to a 1GbE or
2.5GbE PoE++ port (ports 25–32 or 41–48).

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 40 (Cameras) |
| Tagged VLANs | None |
| PoE | 802.3bt (PoE++) |
| Speed | Auto |
| Storm Control | Enabled |

> **VLAN note:** Access Hubs are managed through UniFi Access (part of
> the Protect ecosystem) and share VLAN 40 with cameras. All physical
> security devices — cameras, access control, doorbells, SuperLink — sit
> on the same isolated VLAN managed through the UDM-Pro-Max.

> **PoE budget:** The UA-Hub-Door draws up to 50W total when powering
> connected readers, lock hardware, and peripherals. The USW-Pro-Max-48-PoE
> provides 60W per PoE++ port, giving each hub 10W of headroom above its
> maximum rated draw.

> **Readers connect to the hub, not the switch.** Run Cat6 from the
> switch to the hub location, then separate Cat6 from the hub to each
> reader. Do not run reader drops back to the switch.

---

### `profile_superlink`

**Purpose:** Access port for UniFi SuperLink Gateways (USL-Gateway).
Connects back to the switch via PoE and communicates with wireless
SuperLink sensors up to 2km line-of-sight. Placed on VLAN 40 with
cameras and access control devices.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 40 (Cameras) |
| Tagged VLANs | None |
| PoE | Auto (802.3af) |
| Speed | Auto (100M) |
| Storm Control | Enabled |

> **PoE note:** The SuperLink Gateway draws only 3.4W — standard 802.3af
> is more than sufficient. USB-C power is available as an alternative but
> PoE is the preferred deployment method.

> **Placement tip:** Mount the SuperLink Gateway as high and centrally as
> possible to maximize wireless sensor range. A single Cat6 run for PoE
> means it can be placed in locations awkward for cameras or APs.

---

### `profile_docker`

**Purpose:** Dedicated access port for the Docker host
(EIRDOM-DOCKER-01). Assigned to a 2.5GbE port on the distribution
switch to provide multi-gigabit throughput for Jellyfin transcoding,
Traefik routing, and ARR stack traffic simultaneously.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 50 (Docker) |
| Tagged VLANs | None |
| PoE | Disabled |
| Speed | Auto (2.5G) |
| Storm Control | Enabled |

> **Why 2.5GbE:** EIRDOM-DOCKER-01 runs Jellyfin (4K streams), Traefik
> (all internal and external routing), the full ARR stack, and
> Cloudflared simultaneously. 2.5GbE provides meaningful headroom over
> 1GbE for concurrent high-bandwidth workloads without requiring 10GbE
> NIC hardware in the server.

---

### `profile_server`

**Purpose:** Access port for the Proxmox hypervisor host
(EIRDOM-PVE-01). Assigned to a 2.5GbE port on the distribution switch.
The switch port carries VLAN-tagged traffic for all VMs via the
Proxmox VLAN-aware bridge (vmbr0).

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 10 (Corporate) |
| Tagged VLANs | 10, 60 |
| PoE | Disabled |
| Speed | Auto (2.5G) |
| Storm Control | Enabled |

> **NOTE:** Native VLAN 10 carries the Proxmox host management IP
> (10.1.10.5). Tagged VLAN 10 and 60 carry VM traffic for VMs on those
> segments. Each VM inside Proxmox is assigned the appropriate VLAN tag
> on its virtual NIC — the physical switch port just needs to pass the
> tags through.

---

### `profile_security`

**Purpose:** SPAN / mirror port for Security Onion's passive capture
NIC (EIRDOM-SONION-01). Receives mirrored traffic only — no IP address
on the Security Onion side. All VLANs tagged so Security Onion sees
traffic from every segment simultaneously.

| Setting | Value |
|---------|-------|
| Port Enabled | Yes |
| Native VLAN | 1 |
| Tagged VLANs | 10, 20, 30, 40, 50, 60 |
| PoE | Disabled |
| Speed | Auto (1G) |
| Storm Control | Disabled |
| Mirror Source | UDM-Pro-Max uplink port on distribution switch |

> **Storm Control note:** Disabled intentionally. Security Onion needs
> to see all traffic including broadcast storms — blocking them would
> produce blind spots in the capture stream.

> **Configure port mirroring in:** UniFi Network → Devices →
> (Distribution Switch) → Settings → Port Mirroring → Mirror the UDM
> uplink port to this port.

---

## Profile Summary Table

| Profile | Native VLAN | Tagged VLANs | PoE | Speed | Primary Use |
|---------|------------|--------------|-----|-------|-------------|
| `profile_disabled` | — | None | Off | — | Unused ports |
| `profile_mgmt` | 1 | None | Off | 1G | Management-only drops |
| `profile_trunk_all` | 1 | 10,20,30,40,50,60 | Off | 10G | Switch uplinks, UDM uplink |
| `profile_trunk_ap` | 1 | 10,20,30 | 802.3at | Auto | All AP uplinks (use PoE++ port for U7 Pro Wall) |
| `profile_corporate` | 10 | None | Off | Auto | Wired workstations |
| `profile_corporate_25g` | 10 | None | Off | 2.5G | High-throughput workstations, NAS |
| `profile_iot` | 20 | None | 802.3af | 1G | Wired IoT devices |
| `profile_camera` | 40 | None | 802.3at | 1G | All Protect cameras, doorbells |
| `profile_access_hub` | 40 | None | 802.3bt | Auto | UniFi Access Door Hubs |
| `profile_superlink` | 40 | None | 802.3af | 100M | SuperLink Gateways |
| `profile_docker` | 50 | None | Off | 2.5G | Docker host NIC |
| `profile_server` | 10 | 10, 60 | Off | 2.5G | Proxmox hypervisor |
| `profile_security` | 1 | 10,20,30,40,50,60 | Off | 1G | Security Onion SPAN port |

---

## PoE Budget Planning

Each USW-Pro-Max-48-PoE has a 720W PoE budget. The Eirdom device fleet
is split across both switches — the core handles APs and house drops,
the distribution handles servers and physical security devices.

### Core Switch — Camera & AP Load

| Device | Qty | Max Draw | Total |
|--------|-----|---------|-------|
| U7 Pro | 2 | 25.5W | 51W |
| U7 Pro Wall | 1 | 51W | 51W |
| U7 Pro Outdoor | 1 | 25.5W | 25.5W |
| U7 Lite | 2 | 12.95W | 25.9W |
| G6 180 | 4 | 15W | 60W |
| G6 Bullet | 1 | 9.9W | 9.9W |
| G6 Turret | 1 | 12.5W | 12.5W |
| AI Theta Hub | 1 | 12.5W | 12.5W |
| G4 Doorbell Pro (doorbell) | 1 | 3W | 3W |
| G4 Doorbell Pro (chime) | 1 | 7W | 7W |
| SuperLink Gateway | 2 | 3.4W | 6.8W |
| **Core Switch Total** | | | **~265W of 720W (37%)** |

### Distribution Switch — Server & Access Load

| Device | Qty | Max Draw | Total |
|--------|-----|---------|-------|
| Access Door Hub | 2 | 50W | 100W |
| **Distribution Switch Total** | | | **~100W of 720W (14%)** |

> Both switches are well within budget. The core sits at ~37% utilization
> and the distribution at ~14%, leaving substantial headroom on both for
> future expansion — additional cameras, APs, access control points, or
> new Protect devices as the lineup evolves.

> **PoE++ port allocation — core switch:** The U7 Pro Wall (51W) needs
> one PoE++ port. Assign to ports 41–48 (2.5GbE PoE++). All 15 remaining
> PoE++ ports on the core are available for future use.

> **PoE++ port allocation — distribution switch:** Two Access Door Hubs
> (50W each) need two PoE++ ports. Assign to ports 25–32 (1GbE PoE++) or
> 41–48 (2.5GbE PoE++). 14 remaining PoE++ ports available.

---

## Related Documentation

- [`vlans.md`](vlans.md) — VLAN reference, switch port assignments, and static IP table
- [`wireless.md`](wireless.md) — AP configuration, SSID settings, and RF profiles
- [`firewall-rules.md`](firewall-rules.md) — Inter-VLAN firewall rules