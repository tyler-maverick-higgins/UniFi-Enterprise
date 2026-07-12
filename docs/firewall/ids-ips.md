# UniFi IDS/IPS Configuration
> Eirdom — Intrusion Detection & Prevention Reference
> Last Updated: April 2026

---

## Overview

The UDM-Pro-Max includes a built-in Intrusion Detection and Prevention
System (IDS/IPS) powered by Suricata, an industry-standard open-source
threat detection engine. When enabled, Suricata inspects traffic passing
through the gateway against a continuously updated ruleset and either
alerts (IDS mode) or alerts and blocks (IPS mode).

Eirdom runs in full **IPS mode** on all security-sensitive VLANs —
the system actively drops matching traffic rather than just logging it.

**Configure in:** UniFi Network → Firewall & Security → IDS/IPS

---

## IDS vs IPS Mode

| Mode | Behavior | Use Case |
|------|----------|----------|
| IDS (Detection only) | Inspects and logs — does not block | Initial deployment, baselining |
| IPS (Prevention) | Inspects, logs, and actively blocks | Production — used by Eirdom |

> **Recommendation:** When first enabling on a new network, run in IDS
> mode for 1–2 weeks to establish a baseline and identify any false
> positives before switching to IPS mode. This prevents legitimate
> traffic from being blocked unexpectedly during initial configuration.

---

## Enabled Networks

IPS is enabled on the following networks. Management (VLAN 1) and
Guest (VLAN 30) are excluded — Management because it only carries
UniFi device traffic, Guest because the performance overhead is not
justified for internet-only browsing traffic that Cloudflare WAF
already filters upstream.

| VLAN | Network | IPS Enabled | Justification |
|------|---------|-------------|---------------|
| 1 | Management | No | UniFi device traffic only — low risk |
| 10 | Corporate | Yes | Primary workstations — highest value target |
| 20 | IoT | Yes | High-risk devices — often unpatched firmware |
| 30 | Guest | No | Internet-only — Cloudflare WAF upstream |
| 40 | Cameras | Yes | Physical security infrastructure |
| 50 | Docker | Yes | Public-facing services, Cloudflare Tunnel endpoint |
| 60 | Security | Yes | Security monitoring infrastructure — must not be compromised |

---

## Threat Categories

UniFi organizes Suricata rules into threat categories. Each category
can be set to **Detect** (log only), **Block** (drop and log), or
**Disabled**.

### Recommended Settings

| Category | Setting | Reason |
|----------|---------|--------|
| Malware | Block | Ransomware, trojans, C2 beacons — always block |
| Botnet | Block | Command and control traffic — always block |
| Exploit | Block | Known exploit attempts — always block |
| Scan | Block | Port and vulnerability scanning — block aggressively |
| Phishing | Block | Credential harvesting domains |
| Tor | Block | Tor exit node traffic — high abuse potential |
| Proxy | Block | Anonymization proxies — frequently abused |
| Adware/Spyware | Block | Data exfiltration risk |
| Coinminer | Block | Cryptomining — indicates compromise |
| DNS | Block | DNS tunneling, DNS rebinding attacks |
| Brute Force | Block | Credential stuffing, SSH brute force |
| DoS | Block | Denial of service traffic |
| Web Attacks | Block | SQLi, XSS, LFI, RFI attempts |
| P2P | Detect | Log only — some legitimate P2P may exist |
| Games | Disabled | No security value |
| Streaming | Disabled | No security value |

> Start all categories at **Detect** for the first 1–2 weeks to
> identify false positives before switching to **Block**. Particularly
> watch the P2P, Proxy, and DNS categories — these occasionally
> trigger on legitimate traffic.

---

## Ruleset

UniFi uses the **Emerging Threats (ET) Open** ruleset by default,
updated automatically. The ET Open ruleset is maintained by Proofpoint
and covers the vast majority of known threat signatures.

**Configure in:** UniFi Network → Firewall & Security → IDS/IPS →
Threat Management → Ruleset

| Setting | Value |
|---------|-------|
| Ruleset | Emerging Threats Open |
| Auto-update | Enabled |
| Update frequency | Daily |

> The ET Pro ruleset (paid) provides faster signature updates and
> additional rules not in the open set. For a home environment ET Open
> is sufficient. If Wazuh or Security Onion begin surfacing threats
> that IPS is not catching, evaluate ET Pro.

---

## Performance Considerations

IPS requires the gateway to perform deep packet inspection on all
enabled VLAN traffic, which consumes CPU resources. The UDM-Pro-Max
has dedicated network processing hardware that handles IPS at wire
speed for typical home network throughput, but there are a few
settings worth tuning.

| Setting | Recommended Value | Notes |
|---------|------------------|-------|
| Max pending packets | 1024 | Default — increase if seeing drop in throughput |
| Inspection mode | Full | Inspect both directions |
| Blocked traffic log | Enabled | Essential for Wazuh integration |
| Alert log | Enabled | Feeds Security Onion via syslog |

> Monitor CPU utilization on the UDM-Pro-Max after enabling IPS on all
> VLANs. Under normal home network load the UDM-Pro-Max handles IPS
> without significant performance impact. If throughput drops
> noticeably during large file transfers or 4K streams, consider
> disabling IPS on VLAN 50 (Docker) during off-hours or tuning the
> max pending packets value.

---

## Suppression & Whitelist

IPS will occasionally generate false positives — legitimate traffic
that matches a threat signature. Common examples include:

- Some game launchers triggering exploit signatures
- Certain VPN clients triggering proxy rules
- Development tools triggering web attack signatures

When a false positive is confirmed, add a suppression rule rather
than disabling the entire category.

**Configure in:** UniFi Network → Firewall & Security → IDS/IPS →
Suppression List → Add Rule

| Field | Value |
|-------|-------|
| Rule SID | _(from the alert log — e.g. 2012345)_ |
| Direction | By source IP or destination IP |
| IP | The specific IP generating the false positive |

> Always suppress by specific SID and IP rather than disabling an
> entire category. Keep a log of all suppressions in this document
> under the Suppression Log section below.

---

## Suppression Log

Document all active suppressions here. Review quarterly and remove
any that are no longer needed.

| Date Added | SID | Direction | IP | Reason | Added By |
|-----------|-----|-----------|-----|--------|----------|
| _(none yet)_ | | | | | |

---

## Syslog Integration

IPS alerts are forwarded to Wazuh via the UDM-Pro-Max syslog
integration for correlation, dashboarding, and alerting.

**Configure syslog in:** UniFi Network → System → Syslog →
Server IP: `10.1.60.10` → Port: `514`

Wazuh includes built-in decoders for Suricata alert format. After
syslog is configured, IPS events appear in the Wazuh dashboard under
Security Events automatically.

Security Onion also receives IPS alert data via the SPAN port on the
distribution switch. Security Onion's Suricata instance performs
independent analysis of the same traffic, providing a second layer of
detection independent of the UDM-Pro-Max ruleset.

---

## Recommended Alert Thresholds (Wazuh)

Configure the following alert rules in Wazuh after baseline is
established:

| Event | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| Malware C2 detected | Any | Critical | Immediate alert |
| Exploit attempt blocked | > 5/hour | High | Alert |
| Botnet communication | Any | Critical | Immediate alert |
| Brute force detected | > 20/min | High | Alert |
| DNS tunneling detected | Any | High | Alert |
| Coinminer detected | Any | Critical | Immediate alert |
| New suppression needed | Any | Medium | Review within 24h |

---

## Initial Deployment Checklist

Follow this order when enabling IPS on a new network to minimize
disruption:

1. Enable IPS in **IDS mode only** on VLAN 10 (Corporate) first.
2. Monitor Wazuh and UniFi alerts for 48 hours — identify false
   positives and add suppressions.
3. Switch VLAN 10 to **IPS (Block) mode**.
4. Repeat steps 1–3 for VLAN 50 (Docker) — most likely source of
   false positives due to ARR stack and download client activity.
5. Enable IDS mode on VLANs 20, 40, and 60 simultaneously — these
   generate less varied traffic and baseline faster.
6. Switch all remaining VLANs to IPS (Block) mode after 1 week.
7. Document any suppressions added during baselining in the
   Suppression Log above.

---

## Periodic Maintenance

| Task | Frequency | Notes |
|------|-----------|-------|
| Review IPS alert dashboard | Daily | First month — weekly thereafter |
| Review and prune suppression list | Quarterly | Remove stale suppressions |
| Verify ruleset auto-update is current | Monthly | Check last update timestamp |
| Review blocked traffic logs in Wazuh | Weekly | Look for patterns |
| Evaluate ET Pro upgrade | Annually | Assess if ET Open is sufficient |
| Cross-reference with Security Onion alerts | Weekly | Compare IPS misses vs SO detections |

---

## Related Documentation

- [`wan-rules.md`](wan-rules.md) — WAN inbound/outbound firewall rules
- [`lan-rules.md`](lan-rules.md) — Zone-based LAN firewall rules
- [`vlans.md`](vlans.md) — VLAN reference and network layout
- [`Eirdom_Infrastructure_Guide_v3.docx`](../docs/Eirdom_Infrastructure_Guide_v3.docx) — Full infrastructure guide including Wazuh and Security Onion deployment