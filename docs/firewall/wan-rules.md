# UniFi WAN Firewall Rules
> Eirdom — WAN Firewall Reference
> Last Updated: April 2026

---

## Overview

The Eirdom WAN firewall is built around a **zero inbound exposure**
architecture. The UDM-Pro-Max has no port forwards and no inbound rules
permitting external traffic — all public access flows exclusively through
the Cloudflare Tunnel, which initiates an outbound-only connection from
VLAN 50. Even if the public IP is discovered, an external portscan
returns zero open ports.

WAN rules focus on:
- Blocking all inbound traffic by default
- Blocking all published DoD IP ranges
- Blocking inbound traffic from 13 high-risk countries via GeoIP
- Strong outbound defaults with explicit logging

**Configure in:** UniFi Network → Firewall & Security → WAN

---

## Architecture Reminder

```
Internet → Cloudflare Edge (TLS, WAF, DDoS protection)
               ↓
         Cloudflare Tunnel (outbound-only from DOCKER VLAN 50)
               ↓
         Traefik (internal routing to containers)
               ↓
         WordPress / Jellyfin / services
```

> The UDM-Pro-Max WAN interface has **zero inbound port forwards**.
> No rule in this document opens an inbound port. Any rule suggesting
> otherwise should be treated as a misconfiguration.

---

## DoD IP Block List

The United States Department of Defense publishes its allocated IP ranges
via ARIN. These ranges are frequently spoofed in scanning and attack
traffic. Blocking them at the WAN prevents this traffic from reaching
any internal zone.

**Configure in:** UniFi Network → Firewall & Security → Objects →
Add Object → IP Group → Name: `obj_dod_networks`

Add the following CIDR ranges to the group:

```
6.0.0.0/8
7.0.0.0/8
11.0.0.0/8
21.0.0.0/8
22.0.0.0/8
26.0.0.0/8
28.0.0.0/8
29.0.0.0/8
30.0.0.0/8
33.0.0.0/8
55.0.0.0/8
214.0.0.0/8
215.0.0.0/8
```

> These are the primary DoD/DISA allocated /8 blocks as published by
> ARIN. Review periodically as allocations can change. Current
> allocations can be verified at https://search.arin.net by searching
> for "Department of Defense".

---

## GeoIP Block List

UniFi Network supports GeoIP-based firewall rules natively on the
UDM-Pro-Max. The following 13 countries are blocked inbound based on
consistent patterns of ransomware, state-sponsored attacks, botnets,
scanning activity, and cyber espionage.

**Configure in:** UniFi Network → Firewall & Security → GeoIP Filtering

| # | Country | Reason |
|---|---------|--------|
| 1 | Russia | Primary source of ransomware gangs, REvil, Conti, LockBit |
| 2 | China | Large-scale scanning, APT groups, state-sponsored espionage |
| 3 | Iran | State-sponsored cyber espionage, critical infrastructure attacks |
| 4 | North Korea | Lazarus Group, state-sponsored financial and espionage attacks |
| 5 | Ukraine | High conflict-related activity, significant botnet infrastructure |
| 6 | Belarus | State-aligned threat actors, close coordination with Russian groups |
| 7 | Romania | Historically high volume of credential stuffing and fraud |
| 8 | Poland | Elevated scanning and brute force origination |
| 9 | Turkey | Significant botnet hosting and DDoS origination |
| 10 | Pakistan | Persistent scanning, credential attacks, phishing infrastructure |
| 11 | Nigeria | High volume of fraud, BEC attacks, and social engineering |
| 12 | Nepal | Elevated botnet and proxy traffic |
| 13 | Albania | Elevated scanning and credential attack traffic |

> **GeoIP limitations:** GeoIP blocks are based on IP geolocation
> databases which are not 100% accurate. Sophisticated threat actors
> use VPNs, proxies, and compromised infrastructure in non-blocked
> countries to bypass GeoIP controls. GeoIP is a useful layer of
> defense but should not be relied upon as a primary security control.
> IDS/IPS (see `ids-ips.md`) provides deeper protection.

> **CDN and cloud traffic:** Cloudflare, AWS, Azure, and other major
> CDNs route traffic through global PoPs. If you observe unexpected
> blocks of legitimate services after enabling GeoIP, check whether
> the CDN is routing through a blocked country's infrastructure.
> Cloudflare Tunnel traffic originates from Cloudflare's edge IPs
> which are outside all blocked regions.

---

## WAN Inbound Rules

All inbound rules default to **Deny**. The UDM-Pro-Max implicit deny
covers all inbound traffic — the rules below add explicit named deny
entries for logging and auditing purposes.

| # | Rule Name | Source | Destination | Protocol/Port | Action | Log |
|---|-----------|--------|-------------|--------------|--------|-----|
| 1 | `wan_in_dod_block` | `obj_dod_networks` | Any | Any | Drop | Yes |
| 2 | `wan_in_geoip_block` | GeoIP Block List | Any | Any | Drop | Yes |
| 3 | `wan_in_bogon_block` | Bogon Networks | Any | Any | Drop | Yes |
| 4 | `wan_in_invalid_state` | Any (invalid state) | Any | Any | Drop | Yes |
| 5 | `wan_in_default_deny` | Any | Any | Any | Drop | Yes |

### Rule Notes

**Rule 1 — DoD Block:**
Drops all traffic sourced from the DoD IP group defined above. Logged
so you can monitor for spoofed DoD traffic hitting the WAN.

**Rule 2 — GeoIP Block:**
Drops all inbound traffic originating from the 13 blocked countries.
Uses UniFi's native GeoIP filtering. Logged for monitoring.

**Rule 3 — Bogon Block:**
Bogon networks are IP ranges that should never appear as a source on
the public internet — private RFC1918 ranges, loopback, link-local,
and unallocated space. Traffic sourced from these ranges on the WAN
interface is always spoofed or malformed.

Add the following to an IP Group named `obj_bogon_networks`:

```
0.0.0.0/8
10.0.0.0/8
100.64.0.0/10
127.0.0.0/8
169.254.0.0/16
172.16.0.0/12
192.0.0.0/24
192.0.2.0/24
192.168.0.0/16
198.18.0.0/15
198.51.100.0/24
203.0.113.0/24
224.0.0.0/4
240.0.0.0/4
255.255.255.255/32
```

**Rule 4 — Invalid State:**
Drops packets that do not match any known connection state (NEW,
ESTABLISHED, RELATED). This catches malformed packets, idle scans,
and fragmented attack traffic that doesn't correspond to a legitimate
connection.

**Rule 5 — Default Deny:**
Explicit named default deny with logging enabled. UniFi's implicit
deny would catch anything that reaches this point, but an explicit
named rule ensures it appears in logs with a recognisable label rather
than as unclassified dropped traffic.

---

## WAN Outbound Rules

Outbound traffic from all internal zones to the WAN is permitted by
default via the zone allow rules in `lan-rules.md`. The following
outbound WAN rules apply at the WAN interface level for traffic
leaving the network.

| # | Rule Name | Source | Destination | Protocol/Port | Action | Log |
|---|-----------|--------|-------------|--------------|--------|-----|
| 1 | `wan_out_spoofed_src_block` | Non-RFC1918 src from LAN | WAN | Any | Drop | Yes |
| 2 | `wan_out_default_allow` | Any | Any | Any | Allow | No |

### Rule Notes

**Rule 1 — Spoofed Source Block:**
Drops outbound packets that claim a source IP outside your assigned
subnets. This prevents any compromised internal device from launching
spoofed-source attacks outbound through your WAN. Legitimate internal
traffic always originates from your RFC1918 subnets — anything else
is malformed or malicious.

**Rule 2 — Default Allow:**
Permits all legitimate outbound traffic. Outbound restrictions are
handled at the zone level in `lan-rules.md`, not at the WAN interface.

---

## WAN Local Rules

WAN Local rules govern traffic destined for the UDM-Pro-Max itself
rather than traffic passing through it. These protect the gateway's
management plane from direct internet attack.

| # | Rule Name | Source | Destination | Protocol/Port | Action | Log |
|---|-----------|--------|-------------|--------------|--------|-----|
| 1 | `wan_local_dod_block` | `obj_dod_networks` | UDM | Any | Drop | Yes |
| 2 | `wan_local_geoip_block` | GeoIP Block List | UDM | Any | Drop | Yes |
| 3 | `wan_local_icmp_limit` | Any | UDM | ICMP | Allow (rate limited) | No |
| 4 | `wan_local_default_deny` | Any | UDM | Any | Drop | Yes |

### Rule Notes

**Rule 3 — ICMP Rate Limit:**
Allows ICMP (ping) to the WAN interface but rate-limited to prevent
ICMP flood attacks. UniFi supports rate limiting on firewall rules —
set to a maximum of 5 packets/second. This allows legitimate network
diagnostics (ISP troubleshooting, MTU detection) while preventing
abuse.

**Rule 4 — Default Deny to UDM:**
No service on the UDM-Pro-Max should be directly reachable from the
WAN. This rule ensures nothing reaches the gateway management plane
from the internet regardless of what ports or services may be running.

---

## Logging & Monitoring

All deny rules have logging enabled. Logs flow to Wazuh via syslog
for correlation and alerting.

**Configure syslog forwarding in:** UniFi Network → System →
Syslog → Server IP: `10.1.60.10` (EIRDOM-WAZUH-01) → Port: 514

Recommended Wazuh alert thresholds for WAN traffic:

| Event | Threshold | Action |
|-------|-----------|--------|
| DoD block hits | > 10/min | Alert |
| GeoIP block hits | > 50/min | Alert |
| Bogon block hits | > 5/min | Alert |
| Invalid state drops | > 100/min | Alert |
| Default deny hits | > 20/min | Alert |

> Tune thresholds after the first week of operation once you have a
> baseline for normal background noise on your WAN IP.

---

## Periodic Maintenance

| Task | Frequency | Notes |
|------|-----------|-------|
| Review DoD IP allocations | Quarterly | Verify against ARIN |
| Review GeoIP country list | Quarterly | Adjust based on threat intel |
| Review WAN deny logs | Weekly | Look for patterns in blocked traffic |
| Verify zero open inbound ports | Monthly | External portscan from a non-Cloudflare IP |

> **External portscan test:** Use a service like ShieldsUP
> (grc.com/shieldsup) or nmap from a VPS to confirm zero open inbound
> ports on your WAN IP. All ports should return stealth (no response)
> rather than closed (RST response) — stealth means the firewall is
> silently dropping rather than actively refusing.

---

## Related Documentation

- [`lan-rules.md`](lan-rules.md) — Zone-based LAN firewall rules
- [`ids-ips.md`](ids-ips.md) — UniFi IDS/IPS configuration
- [`vlans.md`](vlans.md) — VLAN reference and subnet table
- [`Eirdom_Infrastructure_Guide_v3.docx`](../docs/Eirdom_Infrastructure_Guide_v3.docx) — Full infrastructure guide