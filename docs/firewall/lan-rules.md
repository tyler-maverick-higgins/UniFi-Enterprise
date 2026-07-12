# UniFi LAN Firewall Rules
> Eirdom — Zone-Based Firewall Reference
> Last Updated: April 2026

---

## Overview

Eirdom uses the **UniFi Zone-Based Firewall** introduced in UniFi Network
8.x. Rather than writing rules per-VLAN interface, zone-based firewall
groups networks into zones and rules are written zone-to-zone. This is
significantly cleaner than the legacy per-interface rule approach.

**Configure in:** UniFi Network → Firewall & Security → Zones

---

## Zone Definitions

| Zone Name | Member Networks | Description |
|-----------|----------------|-------------|
| `WAN` | WAN interface | Internet (auto-created by UniFi) |
| `CORPORATE` | VLAN 10 | Trusted — AD domain devices |
| `IOT` | VLAN 20 | Smart home and streaming devices |
| `GUEST` | VLAN 30 | Guest internet access only |
| `CAMERAS` | VLAN 40 | Protect cameras, access control, SuperLink |
| `DOCKER` | VLAN 50 | Docker host, Traefik, all services |
| `SECURITY` | VLAN 60 | Wazuh, Security Onion — monitoring |
| `MANAGEMENT` | VLAN 1 | UniFi infrastructure devices |

---

## UniFi Objects

UniFi Objects let you define reusable references to IPs, ports, and
devices that can be used across multiple rules. When something changes
you update the object once and all rules referencing it update
automatically.

**Configure in:** UniFi Network → Firewall & Security → Objects

### Client Objects

| Object Name | Type | Value | Used In |
|-------------|------|-------|---------|
| `obj_my_device` | Client | DHCP reservation IP | ARR stack access, UDM access, camera access, NetBox admin |

> Create this by going to UniFi Network → Clients → (your device) →
> Settings → Fixed IP → assign reservation. Then create a Client Object
> referencing that IP in Firewall & Security → Objects → Add Object →
> Client.

### Port Objects

| Object Name | Ports | Used In |
|-------------|-------|---------|
| `obj_port_https_ssh` | 443, 22 | My device → UDM management |
| `obj_port_traefik` | 443 | All service access through Traefik |
| `obj_port_ldap` | 389 | Docker services → AD LDAP authentication |

### IP Objects

| Object Name | Type | Value | Used In |
|-------------|------|-------|---------|
| `obj_udm_pro_max` | IP | 10.1.1.1 | My device → gateway management |
| `obj_traefik` | IP | 10.1.50.10 | Service access rules |
| `obj_eirdom_dc01` | IP | 10.1.10.10 | DNS and LDAP target — EIRDOM-DC-01 |
| `obj_wazuh` | IP | 10.1.60.10 | Security monitoring |
| `obj_security_onion` | IP | 10.1.60.20 | Security monitoring |

> `obj_eirdom_dc01` replaces separate DNS and LDAP destination entries.
> Using a named object means if the DC IP ever changes, one update
> covers both the DNS rule and the LDAP rule simultaneously.

---

## Rule Philosophy

- **Default deny between all zones** — no inter-zone traffic is permitted
  unless explicitly allowed by a rule below.
- **Internet access is allowed per zone** — zones that need internet
  access have an explicit allow to WAN.
- **All service access goes through Traefik** — no direct container port
  access from any zone. All HTTP/HTTPS traffic hits `10.1.50.10:443`
  and Traefik routes internally.
- **Least privilege** — every rule opens the minimum ports to the minimum
  destinations for the minimum set of sources.
- **My device is a named object** — rules granting elevated access
  reference `obj_my_device` so they are easy to identify and update.

---

## Zone-Based Firewall Rules

Rules are listed in priority order within each zone pair. UniFi
evaluates rules top to bottom and stops at the first match.

---

### CORPORATE → WAN

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `corp_wan_allow` | CORPORATE | WAN | Any | Allow |

---

### CORPORATE → DOCKER

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `corp_docker_jellyfin` | CORPORATE | `obj_traefik` | TCP 443 | Allow |
| 2 | `corp_docker_jellyseerr` | CORPORATE | `obj_traefik` | TCP 443 | Allow |
| 3 | `corp_docker_netbox` | CORPORATE | `obj_traefik` | TCP 443 | Allow |
| 4 | `corp_docker_arr_mydevice` | `obj_my_device` | `obj_traefik` | TCP 443 | Allow |
| 5 | `corp_docker_deny` | CORPORATE | DOCKER | Any | Deny |

> Rules 1, 2, and 3 allow all CORPORATE devices to reach Jellyfin,
> Jellyseerr, and NetBox through Traefik. Rule 4 additionally allows
> your device to reach the full ARR stack and all other services —
> also through Traefik on 443. Rule 5 denies all other CORPORATE →
> DOCKER traffic.

> **Note:** All rules resolve to the same destination (`obj_traefik`
> on port 443) because all services are behind Traefik. They are
> written as separate named rules for clarity and auditability.
> NetBox (rule 3) uses its own AD LDAP authentication — it does not
> go through Authentik ForwardAuth.

---

### CORPORATE → CAMERAS

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `corp_cameras_mydevice` | `obj_my_device` | CAMERAS | Any | Allow |
| 2 | `corp_cameras_deny` | CORPORATE | CAMERAS | Any | Deny |

> Camera access for non-privileged CORPORATE devices is handled
> entirely through UniFi Fabric assignments and the Protect app —
> not through direct network access. Only `obj_my_device` gets
> unrestricted network-level access to VLAN 40. All other CORPORATE
> devices access Protect through the UDM interface.

---

### CORPORATE → MANAGEMENT

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `corp_mgmt_udm_mydevice` | `obj_my_device` | `obj_udm_pro_max` | `obj_port_https_ssh` | Allow |
| 2 | `corp_mgmt_deny` | CORPORATE | MANAGEMENT | Any | Deny |

> Only your device can reach the UDM-Pro-Max, and only on HTTPS (443)
> and SSH (22). No other CORPORATE device can reach VLAN 1 at all.
> Switch management (10.1.1.2, 10.1.1.3) is accessible only through
> the UniFi Network application on the UDM — not directly.

---

### CORPORATE → SECURITY

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `corp_security_deny` | CORPORATE | SECURITY | Any | Deny |

> Security monitoring infrastructure is not directly accessible from
> CORPORATE. Access to Wazuh and Security Onion dashboards is handled
> through Traefik reverse proxy routes, not via direct VLAN access
> from workstations.

---

### IOT → WAN

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `iot_wan_allow` | IOT | WAN | Any | Allow |

---

### IOT → DOCKER

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `iot_docker_jellyfin` | IOT | `obj_traefik` | TCP 443 | Allow |
| 2 | `iot_docker_deny` | IOT | DOCKER | Any | Deny |

> IoT devices can only reach Jellyfin, and only through Traefik on
> port 443. This covers smart TVs and streaming devices using the
> Jellyfin app. All other DOCKER destinations are explicitly denied.
> IoT devices cannot reach Jellyseerr, the ARR stack, NetBox, Traefik
> dashboard, or any other service on VLAN 50.

---

### IOT → CORPORATE

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `iot_corporate_deny` | IOT | CORPORATE | Any | Deny |

---

### IOT → CAMERAS

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `iot_cameras_deny` | IOT | CAMERAS | Any | Deny |

---

### IOT → MANAGEMENT

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `iot_mgmt_deny` | IOT | MANAGEMENT | Any | Deny |

---

### GUEST → WAN

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `guest_wan_allow` | GUEST | WAN | Any | Allow |

---

### GUEST → ALL INTERNAL ZONES

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `guest_corporate_deny` | GUEST | CORPORATE | Any | Deny |
| 2 | `guest_iot_deny` | GUEST | IOT | Any | Deny |
| 3 | `guest_cameras_deny` | GUEST | CAMERAS | Any | Deny |
| 4 | `guest_docker_deny` | GUEST | DOCKER | Any | Deny |
| 5 | `guest_security_deny` | GUEST | SECURITY | Any | Deny |
| 6 | `guest_mgmt_deny` | GUEST | MANAGEMENT | Any | Deny |

> Guests get internet only. No internal zone is reachable from GUEST
> under any circumstance.

---

### CAMERAS → MANAGEMENT

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `cameras_mgmt_protect` | CAMERAS | `obj_udm_pro_max` | TCP 7443, 7444 | Allow |
| 2 | `cameras_mgmt_deny` | CAMERAS | MANAGEMENT | Any | Deny |

> Cameras, Access Hubs, and SuperLink Gateways need to communicate
> with the Protect NVR and Access controller running on the UDM-Pro-Max.
> Ports 7443 and 7444 are the Protect adoption and streaming ports.
> All other MANAGEMENT destinations are denied.

---

### CAMERAS → ALL OTHER ZONES

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `cameras_corporate_deny` | CAMERAS | CORPORATE | Any | Deny |
| 2 | `cameras_iot_deny` | CAMERAS | IOT | Any | Deny |
| 3 | `cameras_guest_deny` | CAMERAS | GUEST | Any | Deny |
| 4 | `cameras_docker_deny` | CAMERAS | DOCKER | Any | Deny |
| 5 | `cameras_security_deny` | CAMERAS | SECURITY | Any | Deny |

> Cameras are fully isolated. They can only reach the UDM for Protect
> and Access. A compromised camera cannot reach any other segment.

---

### DOCKER → WAN

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `docker_wan_allow` | DOCKER | WAN | Any | Allow |

> DOCKER needs internet access for the Cloudflare Tunnel outbound
> connection, ARR stack indexers and download clients, and container
> image pulls.

---

### DOCKER → CORPORATE

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `docker_corp_dns` | DOCKER | `obj_eirdom_dc01` | TCP/UDP 53 | Allow |
| 2 | `docker_corp_ldap` | DOCKER | `obj_eirdom_dc01` | TCP 389 | Allow |
| 3 | `docker_corp_deny` | DOCKER | CORPORATE | Any | Deny |

> **Rule 1 — DNS:** All Docker services resolve internal hostnames
> like `jellyfin.eirdom.homes` and `netbox.eirdom.homes` via
> EIRDOM-DC-01.
>
> **Rule 2 — LDAP:** Both Authentik and NetBox authenticate users
> against Active Directory via LDAP on port 389. Authentik syncs
> AD users and groups for SSO across all internal services. NetBox
> authenticates directly against AD for its own login. Without this
> rule, AD login fails silently for both services.
>
> **Rule 3 — Deny all else:** No other DOCKER → CORPORATE traffic
> is permitted beyond DNS and LDAP to the DC.

---

### SECURITY → ALL ZONES

| # | Name | Source | Destination | Protocol/Port | Action |
|---|------|--------|-------------|--------------|--------|
| 1 | `security_all_allow` | SECURITY | All Zones | Any | Allow |

> Wazuh and Security Onion require full visibility across all VLANs
> for log collection, agent communication, and passive monitoring.
> Security Onion's capture NIC operates at Layer 2 via SPAN and does
> not generate routed traffic — this rule covers Wazuh agent
> communication and active monitoring traffic from VLAN 60.

---

## Protect Viewport & Camera Access

UniFi Viewport devices and the Protect mobile app authenticate through
the UDM-Pro-Max and do not require direct VLAN 40 access from client
devices. Access works as follows:

- **Viewport devices** — connect to the UDM-Pro-Max Protect interface.
  Assign Viewport devices to VLAN 10 (Corporate). No direct VLAN 40
  access needed.
- **Mobile app (cloud)** — routes through Cloudflare and the UDM
  remote access feature. No local firewall rules required.
- **Two privileged workstations** — `obj_my_device` has full CAMERAS
  zone access via `corp_cameras_mydevice`. The second workstation
  should be added as a second named Client Object (e.g.
  `obj_workstation_2`) and added to the same rule.
- **UniFi Fabric assignments** — camera-to-user assignments are
  configured in UniFi Protect → Users, not in firewall rules.

---

## Rule Summary Table

| Zone Pair | Default | Exceptions |
|-----------|---------|-----------|
| CORPORATE → WAN | Allow | — |
| CORPORATE → DOCKER | Deny | Traefik:443 for Jellyfin, Jellyseerr, NetBox; full Traefik:443 for my device |
| CORPORATE → CAMERAS | Deny | Full access for my device only |
| CORPORATE → MANAGEMENT | Deny | UDM 443+22 for my device only |
| CORPORATE → SECURITY | Deny | — |
| IOT → WAN | Allow | — |
| IOT → DOCKER | Deny | Traefik:443 (Jellyfin only) |
| IOT → CORPORATE | Deny | — |
| IOT → CAMERAS | Deny | — |
| IOT → MANAGEMENT | Deny | — |
| GUEST → WAN | Allow | — |
| GUEST → All internal | Deny | — |
| CAMERAS → MANAGEMENT | Deny | UDM 7443+7444 (Protect NVR) |
| CAMERAS → All other | Deny | — |
| DOCKER → WAN | Allow | — |
| DOCKER → CORPORATE | Deny | DNS:53 + LDAP:389 to EIRDOM-DC-01 only |
| SECURITY → All | Allow | Full monitoring visibility |

---

## UniFi Controller Configuration Paths

| Task | Path |
|------|------|
| Create zones | Firewall & Security → Zones → Add Zone |
| Create zone rules | Firewall & Security → Zones → (zone) → Add Rule |
| Create client objects | Firewall & Security → Objects → Add Object → Client |
| Create IP objects | Firewall & Security → Objects → Add Object → IP Address |
| Create port objects | Firewall & Security → Objects → Add Object → Port |
| Assign DHCP reservation | Clients → (device) → Settings → Fixed IP |
| Protect Fabric assignments | Protect → Users → (user) → Camera Access |

---

## Related Documentation

- [`vlans.md`](vlans.md) — VLAN reference, subnet table, static IPs
- [`wireless.md`](wireless.md) — SSID to VLAN mapping
- [`wan-rules.md`](wan-rules.md) — WAN inbound/outbound rules
- [`ids-ips.md`](ids-ips.md) — IDS/IPS configuration
- [`Eirdom_Infrastructure_Guide_v3.docx`](../docs/Eirdom_Infrastructure_Guide_v3.docx) — Full infrastructure guide