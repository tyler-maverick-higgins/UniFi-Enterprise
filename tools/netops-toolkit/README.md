# Eirdom NetOps Toolkit

**AI-Powered Network Documentation & Automation for UniFi Home Infrastructure**

> Inspired by [GTalksTech/netops-toolkit](https://github.com/GTalksTech/netops-toolkit/tree/main/scripts/netmiko/ai-network-documentation) — adapted from Netmiko/Cisco to UniFi API for the Eirdom home lab.

## What This Does

Instead of SSH'ing into Cisco gear with Netmiko, this toolkit hits the **UniFi Controller API** on your UDM-Pro-Max to pull live network state, then feeds it to **Claude AI** to auto-generate human-readable documentation.

```
UDM-Pro-Max API ──► Python Collector ──► Claude API ──► Markdown / DOCX Reports
```

### Generated Documentation Includes

- **Network Topology** — devices, ports, uplinks, mesh paths
- **VLAN & Subnet Map** — all networks with DHCP scopes, gateways, DNS
- **Firewall Rule Audit** — inter-VLAN rules, WAN rules, threat management
- **Wireless Report** — SSIDs, security modes, channel utilization, client counts
- **Client Inventory** — all connected devices with IPs, MACs, VLANs, signal quality
- **Port Profile Map** — switch port assignments, PoE status, LLDP neighbors
- **Change Diff Report** — compares current state to last snapshot, highlights drift

## Architecture

```
┌─────────────────────────────────────────────────┐
│  EIRDOM-DOCKER-01  (10.1.50.10)                 │
│                                                  │
│  ┌──────────────┐    ┌──────────────────────┐   │
│  │  eirdom-     │    │  Claude API          │   │
│  │  netops-     │───►│  (api.anthropic.com) │   │
│  │  toolkit     │    └──────────────────────┘   │
│  └──────┬───────┘                                │
│         │ HTTPS (API calls)                      │
│         ▼                                        │
│  ┌──────────────┐                                │
│  │  UDM-Pro-Max │                                │
│  │  (10.1.1.1)  │                                │
│  └──────────────┘                                │
└─────────────────────────────────────────────────┘
```

## Quick Start

### 1. Clone & Configure

```bash
git clone git@github.com:YOUR_USER/eirdom-netops-toolkit.git
cd eirdom-netops-toolkit
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your credentials
```

### 2. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run a Full Documentation Snapshot

```bash
python scripts/collect_and_document.py
```

This will:
1. Authenticate to the UDM-Pro-Max API
2. Pull all device, network, client, firewall, and wireless data
3. Save raw JSON snapshots to `output/snapshots/`
4. Send structured data to Claude API for documentation generation
5. Output Markdown reports to `output/reports/`

### 4. Run Individual Collectors

```bash
# Just pull device inventory
python scripts/unifi_collector.py --target devices

# Just pull firewall rules
python scripts/unifi_collector.py --target firewall

# Just pull wireless info
python scripts/unifi_collector.py --target wireless

# Pull everything
python scripts/unifi_collector.py --target all
```

### 5. Generate AI Documentation from Existing Snapshot

```bash
python scripts/ai_documenter.py --snapshot output/snapshots/2026-04-11_full.json
```

### 6. Diff Against Previous Snapshot

```bash
python scripts/diff_report.py \
  --old output/snapshots/2026-04-04_full.json \
  --new output/snapshots/2026-04-11_full.json
```

## Project Structure

```
eirdom-netops-toolkit/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── config/
│   ├── config.example.yaml      # Template config (no secrets)
│   └── config.yaml              # Your actual config (gitignored)
├── scripts/
│   ├── unifi_collector.py       # Pulls data from UDM-Pro-Max API
│   ├── ai_documenter.py         # Sends data to Claude, gets docs
│   ├── collect_and_document.py  # End-to-end: collect → document
│   └── diff_report.py           # Compare two snapshots for drift
├── templates/
│   └── prompts.yaml             # Claude prompt templates per report type
└── output/
    ├── snapshots/               # Raw JSON from UniFi API (timestamped)
    └── reports/                 # AI-generated Markdown reports
```

## Configuration

### config/config.yaml

```yaml
unifi:
  controller_url: "https://10.1.1.1"   # UDM-Pro-Max
  username: "eirdom-netops"             # Dedicated local admin account
  password: "${UNIFI_PASSWORD}"         # Resolved from env var
  site: "default"
  verify_ssl: false                     # Self-signed cert on UDM

claude:
  api_key: "${ANTHROPIC_API_KEY}"       # Resolved from env var
  model: "claude-sonnet-4-20250514"
  max_tokens: 8192

output:
  snapshot_dir: "output/snapshots"
  report_dir: "output/reports"
  format: "markdown"                    # markdown | docx
```

### Environment Variables

```bash
export UNIFI_PASSWORD="your-unifi-password"
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Security Notes

- **Create a dedicated read-only UniFi local admin** (`eirdom-netops`) — do NOT use your primary admin account
- **Never commit** `config.yaml`, `.env`, or any file with credentials
- API key and password are resolved from environment variables at runtime
- Raw snapshots may contain MAC addresses and IPs — treat `output/` as sensitive
- The `.gitignore` excludes all sensitive paths by default

## Scheduling (Cron)

Add to crontab on EIRDOM-DOCKER-01 for weekly automated documentation:

```bash
# Every Sunday at 2 AM — full collection + AI doc generation
0 2 * * 0 cd /opt/eirdom/netops-toolkit && /opt/eirdom/netops-toolkit/venv/bin/python scripts/collect_and_document.py >> /var/log/eirdom-netops.log 2>&1
```

## Integration with Eirdom Infrastructure

| Component | How It Connects |
|-----------|----------------|
| UDM-Pro-Max | API target — all network data comes from here |
| EIRDOM-DC-01 | DNS resolution for internal hostnames in reports |
| Wazuh | Forward script logs for audit trail |
| Git Repo | Store configs + generated docs with version history |
| Cloudflare | Not involved — this is internal-only tooling |

## License

Private — Eirdom home lab use only.
