# UniFi Wireless Configuration
> Eirdom — UniFi Wireless Reference
> Last Updated: April 2026

---

## Access Points

| Hostname | Model | Location | Role |
|----------|-------|----------|------|
| AP-MAIN-01 | U7 Pro | Living Room / Central | Primary indoor coverage |
| AP-MAIN-02 | U7 Pro | Hallway / Secondary | Secondary indoor coverage |
| AP-WALL-01 | U7 Pro Wall | Office | In-wall coverage, wired clients |
| AP-OUT-01 | U7 Pro Outdoor | Garage / Exterior | Outdoor + garage coverage |
| AP-LITE-01 | U7 Lite | Bedroom Wing | Lightweight indoor coverage |
| AP-LITE-02 | U7 Lite | Basement / Server Room | Coverage fill |

> Update hostnames and locations to match your physical deployment.

### U7 Series Capabilities

| Feature | U7 Lite | U7 Pro | U7 Pro Wall | U7 Pro Outdoor |
|---------|---------|--------|-------------|----------------|
| Wi-Fi Standard | Wi-Fi 7 | Wi-Fi 7 | Wi-Fi 7 | Wi-Fi 7 |
| Bands | 2.4 + 5 GHz | 2.4 + 5 + 6 GHz | 2.4 + 5 + 6 GHz | 2.4 + 5 + 6 GHz |
| Max Speed | 8.7 Gbps | 18.1 Gbps | 18.1 Gbps | 18.1 Gbps |
| Spatial Streams | 2x2 | 4x4 | 4x4 | 4x4 |
| PoE | 802.3af | 802.3at | 802.3bt | 802.3at |
| Outdoor Rated | No | No | No | Yes (IP67) |

> **WARNING:** The U7 Pro Wall requires 802.3bt (PoE++) — confirm your switch port
> supports it before deployment. The USW-Pro-48-PoE supports PoE++ on select ports.

---

## SSIDs

### Overview

| SSID | Band | Security | VLAN | Subnet | Purpose |
|------|------|----------|------|--------|---------|
| Eirdom | 2.4 / 5 / 6 GHz | WPA3-Enterprise (802.1X) | 10 | 10.1.10.0/24 | Trusted — domain-joined devices and family |
| Eirdom-IoT | 2.4 GHz | WPA3-Personal | 20 | 10.1.20.0/24 | IoT and smart home devices |
| Eirdom-Guest | 2.4 / 5 GHz | WPA3-Personal | 30 | 10.1.30.0/24 | Guest access — internet only |

---

### SSID: Eirdom (Trusted)

**Purpose:** Primary network for domain-joined computers, phones, and trusted family devices.

| Setting | Value |
|---------|-------|
| SSID | `Eirdom` |
| Security Protocol | WPA3-Enterprise |
| Authentication | 802.1X — RADIUS via NPS (EIRDOM-DC-01) |
| RADIUS Server | 10.1.10.10 |
| RADIUS Port | 1812 |
| RADIUS Accounting Port | 1813 |
| VLAN | 10 |
| Band Steering | Enabled |
| BSS Transition | Enabled |
| Broadcast on 2.4 GHz | Yes |
| Broadcast on 5 GHz | Yes |
| Broadcast on 6 GHz | Yes |
| PMF (Protected Management Frames) | Required |
| Fast Roaming (802.11r) | Enabled |
| Hide SSID | No |
| Client Device Isolation | Disabled |
| Multicast Enhancement | Enabled |
| High Performance Devices Only | Disabled |

**RADIUS Profile (configured in UniFi → Settings → Profiles → RADIUS):**

| Setting | Value |
|---------|-------|
| Profile Name | `Eirdom-NPS` |
| RADIUS Auth Server | 10.1.10.10 |
| Auth Port | 1812 |
| RADIUS Accounting | Enabled |
| Accounting Server | 10.1.10.10 |
| Accounting Port | 1813 |
| Shared Secret | _(stored in password manager)_ |

> **NOTE:** 802.1X requires the `Eirdom-WiFi-Profile` GPO to be applied to
> domain-joined Windows machines, which pushes the EAP-PEAP / MSCHAPv2
> credential profile automatically. Non-domain devices must be manually
> configured with domain credentials.

> **TIP:** After PKI deployment is complete, replace the NPS self-signed
> certificate with one issued by EIRDOM-SUB-01 (Eirdom Issuing CA) to
> eliminate certificate trust warnings on non-domain devices.

---

### SSID: Eirdom-IoT

**Purpose:** Smart home devices, TVs, speakers, thermostats, and any device that
does not support WPA3-Enterprise or should not have access to corporate resources.

| Setting | Value |
|---------|-------|
| SSID | `Eirdom-IoT` |
| Security Protocol | WPA3-Personal (WPA2/WPA3 transition mode) |
| VLAN | 20 |
| Band Steering | Disabled |
| Broadcast on 2.4 GHz | Yes |
| Broadcast on 5 GHz | No |
| Broadcast on 6 GHz | No |
| PMF (Protected Management Frames) | Optional |
| Fast Roaming (802.11r) | Disabled |
| Hide SSID | No |
| Client Device Isolation | Enabled |
| Multicast Enhancement | Enabled |
| High Performance Devices Only | Disabled |

> **Why 2.4 GHz only:** The vast majority of IoT devices only support 2.4 GHz.
> Limiting to 2.4 GHz reduces co-channel interference on 5 and 6 GHz bands,
> which are reserved for high-performance trusted and guest devices.

> **Why WPA2/WPA3 transition mode:** Many IoT devices do not support WPA3.
> Transition mode allows both WPA2 and WPA3 clients to connect to the same SSID.

> **Why Client Device Isolation is enabled:** IoT devices should never communicate
> directly with each other unless explicitly required. This prevents a compromised
> device from laterally attacking others on the same VLAN.

---

### SSID: Eirdom-Guest

**Purpose:** Internet-only access for guests. Fully isolated from all internal VLANs.
Includes a captive portal with terms and conditions — guests must accept before
gaining internet access.

| Setting | Value |
|---------|-------|
| SSID | `Eirdom-Guest` |
| Security Protocol | WPA3-Personal |
| VLAN | 30 |
| Band Steering | Enabled |
| Broadcast on 2.4 GHz | Yes |
| Broadcast on 5 GHz | Yes |
| Broadcast on 6 GHz | No |
| PMF (Protected Management Frames) | Optional |
| Fast Roaming (802.11r) | Disabled |
| Hide SSID | No |
| Client Device Isolation | Enabled |
| Multicast Enhancement | Disabled |
| Guest Portal | Enabled — see configuration below |
| Rate Limiting | 25 Mbps down / 10 Mbps up per client |

> **Why no 6 GHz:** 6 GHz is Wi-Fi 7 / WPA3-only. Guest devices are often older
> and may not support it. Limiting to 2.4/5 GHz ensures maximum compatibility.

---

### Guest Portal Configuration

Configured in **UniFi Network → Settings → Guest Hotspot**.

#### Step 1 — Basic Settings

| Setting | Value |
|---------|-------|
| Guest Hotspot | Enabled |
| Linked Network | Eirdom-Guest (VLAN 30) |
| Authentication | Click-through (no password — guests just accept terms) |
| Expiration | 8 hours (guests must re-accept after 8 hours) |
| Landing Page | Terms and Conditions (custom — see content below) |
| Redirect URL | `https://eirdom.homes` (after accepting, redirected to family site) |

> **Authentication choice:** Click-through (no separate portal password) keeps
> the experience smooth — guests connect to `Eirdom-Guest`, open a browser,
> accept the terms, and get internet. No second password to share.
> The WPA3 pre-shared key for the SSID itself provides the first layer of access
> control — only people you've given the WiFi password to can even reach the portal.

#### Step 2 — Appearance

| Setting | Value |
|---------|-------|
| Portal Title | `Welcome to Eirdom` |
| Logo | Upload the Eirdom family logo or monogram |
| Background | Dark neutral or family photo |
| Button Color | Match home colour scheme |
| Button Text | `I Agree — Connect to Internet` |

#### Step 3 — Rate Limiting

| Setting | Value |
|---------|-------|
| Download Limit | 25 Mbps per client |
| Upload Limit | 10 Mbps per client |
| Purpose | Prevents a single guest device saturating the connection |

#### Step 4 — WLAN Schedule (optional)

Consider scheduling the guest SSID to broadcast only during hours when
guests are actually likely — e.g. 7 AM to 11 PM. This reduces the attack
surface during overnight hours when no guests are present.

**Settings → WiFi → Eirdom-Guest → Advanced → WLAN Schedule**

---

### Guest Portal Page Content

This is the text to paste into the UniFi Guest Portal terms field.
It is intentionally plain and friendly — not a wall of legal text that
nobody reads.

---

**Portal Title:** `Welcome to Eirdom`

**Subtitle:** `Guest Wi-Fi Access`

---

**Terms and Conditions text:**

```
Welcome, and thank you for visiting.

By connecting to this network you agree to the following:

• This network is provided for personal internet access only.
  Please do not use it for illegal activity, torrenting, or
  commercial purposes.

• You are responsible for your own device security. We recommend
  keeping your device's software up to date.

• Network traffic may be monitored for security purposes.

• Your access expires after 8 hours. Reconnect at any time using
  the same WiFi password.

• We reserve the right to disconnect any device at any time.

Enjoy your visit.
— The Higgins Family
```

---

> **Why keep it short:** Most captive portal terms are ignored because
> they are too long. A short, plain-language list that guests will
> actually read is more effective than pages of legal boilerplate.
> The key points covered are: no illegal use, monitoring disclosure,
> session expiry, and right to disconnect. These are the four things
> that actually matter.

---

### Guest Portal Password Rotation

The `Eirdom-Guest` SSID uses a WPA3 pre-shared key that should be
rotated regularly. Suggested schedule:

| Event | Action |
|-------|--------|
| After any visit | Optional — rotate if you don't want the guest to reconnect |
| Monthly | Rotate as standard practice |
| After a contractor finishes work | Always rotate |
| If the password is shared beyond intended recipients | Rotate immediately |

Update the password in **UniFi Network → Settings → WiFi → Eirdom-Guest**.
No other configuration changes are needed — the portal re-appears
automatically on next connection.

---

## RF Profiles

### Profile: High Performance (Trusted + Guest)

Applied to APs broadcasting `Eirdom` and `Eirdom-Guest`.

| Setting | 2.4 GHz | 5 GHz | 6 GHz |
|---------|---------|-------|-------|
| Channel Width | 20 MHz | 80 MHz | 160 MHz |
| Tx Power | Auto (Medium) | Auto (High) | Auto (High) |
| Min RSSI | -80 dBm | -75 dBm | -70 dBm |
| BSS Color | Auto | Auto | Auto |
| Target Wake Time (TWT) | Enabled | Enabled | Enabled |
| OFDMA | Enabled | Enabled | Enabled |
| MU-MIMO | Enabled | Enabled | Enabled |

### Profile: IoT (2.4 GHz Only)

Applied to APs broadcasting `Eirdom-IoT`.

| Setting | 2.4 GHz |
|---------|---------|
| Channel Width | 20 MHz |
| Tx Power | Auto (Low-Medium) |
| Min RSSI | -85 dBm |
| BSS Color | Auto |
| Target Wake Time (TWT) | Enabled |

> **Why 20 MHz on 2.4 GHz across all profiles:** There are only three
> non-overlapping channels on 2.4 GHz (1, 6, 11). Using 40 MHz cuts the
> available non-overlapping channels in half and significantly increases
> co-channel interference in a multi-AP environment.

---

## Channel Planning

### 2.4 GHz

Only channels 1, 6, and 11 are non-overlapping. Assign one per AP in
overlapping coverage areas.

| AP | 2.4 GHz Channel |
|----|----------------|
| AP-MAIN-01 | 1 |
| AP-MAIN-02 | 6 |
| AP-WALL-01 | 11 |
| AP-OUT-01 | 6 |
| AP-LITE-01 | 1 |
| AP-LITE-02 | 11 |

### 5 GHz

Use UNII-1 and UNII-3 channels with 80 MHz width. Avoid DFS channels if
possible (channels 52–144 require radar detection and may cause random
channel changes).

| AP | 5 GHz Channel |
|----|--------------|
| AP-MAIN-01 | 36 (UNII-1) |
| AP-MAIN-02 | 149 (UNII-3) |
| AP-WALL-01 | 157 (UNII-3) |
| AP-OUT-01 | 165 (UNII-3) |
| AP-LITE-01 | 40 (UNII-1) |
| AP-LITE-02 | 44 (UNII-1) |

### 6 GHz

6 GHz has 59 non-overlapping 20 MHz channels and significantly less
interference than 2.4 and 5 GHz. UniFi handles 6 GHz channel assignment
well in Auto mode — leave at Auto unless experiencing specific issues.

> **TIP:** Let UniFi auto-assign 6 GHz channels initially. After the
> network has been running for 2-4 weeks, review the AI-driven channel
> optimization in UniFi Network → WiFi → Optimization for manual tuning
> recommendations.

---

## Roaming Configuration

Fast roaming ensures seamless handoff between APs for VoIP, video calls,
and mobile devices moving through the home.

| Setting | Value | Notes |
|---------|-------|-------|
| 802.11r (Fast BSS Transition) | Enabled on Eirdom only | Not enabled on IoT — compatibility issues with some devices |
| 802.11k (Neighbor Reports) | Enabled | Helps clients identify better APs proactively |
| 802.11v (BSS Transition Mgmt) | Enabled | Allows network to suggest roaming to clients |
| Min RSSI Handoff | -75 dBm (5/6 GHz) | Clients kicked when signal drops below threshold |
| Band Steering | Enabled on Eirdom + Guest | Steers capable clients to 5/6 GHz |

---

## AP Groups

UniFi AP Groups control which APs broadcast which SSIDs. Useful for
limiting outdoor SSIDs or reducing unnecessary SSID broadcasts indoors.

| AP Group | Members | SSIDs Broadcast |
|----------|---------|----------------|
| Indoor-Main | AP-MAIN-01, AP-MAIN-02, AP-WALL-01, AP-LITE-01, AP-LITE-02 | Eirdom, Eirdom-IoT, Eirdom-Guest |
| Outdoor | AP-OUT-01 | Eirdom, Eirdom-IoT, Eirdom-Guest |

> **NOTE:** Consider removing `Eirdom-Guest` from the Outdoor AP group
> if you do not want guests connecting from outside the property.

---

## VLAN to SSID Mapping Summary

| SSID | VLAN | Subnet | Gateway | DHCP Server |
|------|------|--------|---------|-------------|
| Eirdom | 10 | 10.1.10.0/24 | 10.1.10.1 | EIRDOM-DC-01 (10.1.10.10) via DHCP Relay |
| Eirdom-IoT | 20 | 10.1.20.0/24 | 10.1.20.1 | UDM-Pro-Max built-in DHCP |
| Eirdom-Guest | 30 | 10.1.30.0/24 | 10.1.30.1 | UDM-Pro-Max built-in DHCP |

> **NOTE:** VLAN 10 DHCP is handled by EIRDOM-DC-01, not the UDM.
> Configure DHCP Relay on VLAN 10 in UniFi Network → Networks → Corporate
> → DHCP → DHCP Relay → 10.1.10.10. VLANs 20 and 30 use the UDM's
> built-in DHCP server.

---

## Security Notes

**Eirdom (Trusted)** uses WPA3-Enterprise with 802.1X. Credentials are
validated against Active Directory via NPS on EIRDOM-DC-01. No pre-shared
key exists — access requires a domain account. This is the highest level
of wireless security available in UniFi.

**Eirdom-IoT** uses a strong WPA3 pre-shared key stored in the password
manager. Rotate this password quarterly or whenever a device is
decommissioned. Client isolation prevents lateral movement between IoT
devices even if one is compromised.

**Eirdom-Guest** uses a separate WPA3 pre-shared key. Rotate monthly or
after any contractor visit. A captive portal requires guests to accept
terms before gaining internet access — configured in UniFi Network →
Settings → Guest Hotspot. Firewall rules on VLAN 30 block all RFC1918
destinations — guests physically cannot reach internal resources
regardless of what SSID settings say.

All AP management traffic runs on VLAN 1 (Management). APs are completely
unreachable from VLAN 20, 30, or any client VLAN.

---

## UniFi Controller Configuration Paths

| Setting Area | Path |
|-------------|------|
| SSIDs | Settings → WiFi |
| RADIUS Profiles | Settings → Profiles → RADIUS |
| Networks / VLANs | Settings → Networks |
| RF Profiles | Settings → WiFi → (edit SSID) → Advanced |
| AP Groups | UniFi Devices → Access Points → AP Groups |
| Channel Plan | WiFi → Optimization → Manual Override |
| Guest Portal | Settings → Guest Hotspot |
| DHCP Relay | Settings → Networks → (edit VLAN 10) → DHCP Relay |

---

## Related Documentation

- [`vlans.md`](vlans.md) — Full VLAN reference and subnet table
- [`firewall-rules.md`](firewall-rules.md) — Inter-VLAN firewall rules
- [`port-profiles.md`](port-profiles.md) — Switch port profiles for AP uplinks
- [`Eirdom_Infrastructure_Guide_v3.docx`](../docs/Eirdom_Infrastructure_Guide_v3.docx) — Full infrastructure guide including AD, NPS, and PKI setup required for 802.1X