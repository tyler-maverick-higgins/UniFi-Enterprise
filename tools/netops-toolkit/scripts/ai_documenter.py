#!/usr/bin/env python3
"""
Eirdom NetOps Toolkit — AI Documentation Generator
Takes a UniFi API snapshot and generates human-readable documentation via Claude.

Usage:
    python ai_documenter.py --snapshot output/snapshots/2026-04-11_full.json
    python ai_documenter.py --snapshot output/snapshots/2026-04-11_full.json --sections devices firewall
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config(config_path: str = "config/config.yaml") -> dict:
    load_dotenv()
    with open(config_path, "r") as f:
        raw = f.read()
    for key, value in os.environ.items():
        raw = raw.replace(f"${{{key}}}", value)
    return yaml.safe_load(raw)


def load_prompts(prompts_path: str = "templates/prompts.yaml") -> dict:
    with open(prompts_path, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Data Preparation — Trim snapshot to fit context windows
# ---------------------------------------------------------------------------

def trim_clients(clients: list, max_clients: int = 200) -> list:
    """Trim client list to avoid blowing up token count."""
    if len(clients) <= max_clients:
        return clients

    # Keep essential fields only
    trimmed = []
    for c in clients[:max_clients]:
        trimmed.append({
            "hostname": c.get("hostname", c.get("name", "unknown")),
            "mac": c.get("mac"),
            "ip": c.get("ip"),
            "network": c.get("network"),
            "is_wired": c.get("is_wired"),
            "rssi": c.get("rssi"),
            "signal": c.get("signal"),
            "ap_mac": c.get("ap_mac"),
            "sw_mac": c.get("sw_mac"),
            "sw_port": c.get("sw_port"),
            "uptime": c.get("uptime"),
            "satisfaction": c.get("satisfaction"),
        })
    return trimmed


def trim_devices(devices: list) -> list:
    """Keep key fields from device records to reduce token usage."""
    trimmed = []
    for d in devices:
        record = {
            "name": d.get("name"),
            "model": d.get("model"),
            "model_long": d.get("model_in_lts", d.get("model_in_eol")),
            "type": d.get("type"),
            "mac": d.get("mac"),
            "ip": d.get("ip"),
            "version": d.get("version"),
            "uptime": d.get("uptime"),
            "state": d.get("state"),
            "adopted": d.get("adopted"),
            "num_sta": d.get("num_sta"),
            "satisfaction": d.get("satisfaction"),
        }

        # Include port table for switches
        if d.get("type") == "usw":
            port_table = d.get("port_table", [])
            record["port_summary"] = {
                "total_ports": len(port_table),
                "ports_up": sum(1 for p in port_table if p.get("up")),
                "poe_ports": sum(1 for p in port_table if p.get("poe_enable")),
            }
            # Include per-port detail
            record["ports"] = [
                {
                    "port_idx": p.get("port_idx"),
                    "name": p.get("name"),
                    "up": p.get("up"),
                    "speed": p.get("speed"),
                    "poe_enable": p.get("poe_enable"),
                    "poe_power": p.get("poe_power"),
                    "lldp_table": p.get("lldp_table", []),
                }
                for p in port_table
            ]

        # Include radio table for APs
        if d.get("type") == "uap":
            radio_table = d.get("radio_table", [])
            record["radios"] = [
                {
                    "radio": r.get("radio"),
                    "channel": r.get("channel"),
                    "tx_power": r.get("tx_power"),
                    "satisfaction": r.get("satisfaction"),
                    "num_sta": r.get("num_sta"),
                }
                for r in radio_table
            ]

        # Include uplink info
        uplink = d.get("uplink", {})
        if uplink:
            record["uplink"] = {
                "type": uplink.get("type"),
                "uplink_mac": uplink.get("uplink_mac"),
                "uplink_device_name": uplink.get("uplink_device_name"),
                "port_idx": uplink.get("port_idx"),
                "speed": uplink.get("speed"),
            }

        trimmed.append(record)
    return trimmed


def prepare_section_data(snapshot: dict, section: str) -> dict:
    """Prepare the data payload for a given documentation section."""
    data_map = {
        "device_inventory": {
            "device_data": json.dumps(trim_devices(snapshot.get("devices", [])), indent=2),
        },
        "network_map": {
            "network_data": json.dumps(snapshot.get("networks", []), indent=2),
        },
        "firewall_audit": {
            "firewall_data": json.dumps({
                "rules": snapshot.get("firewall_rules", []),
                "groups": snapshot.get("firewall_groups", []),
                "port_forwards": snapshot.get("port_forward", []),
            }, indent=2),
        },
        "wireless_report": {
            "wlan_data": json.dumps(snapshot.get("wlan_conf", []), indent=2),
            "ap_data": json.dumps(
                [d for d in trim_devices(snapshot.get("devices", []))
                 if d.get("type") == "uap"],
                indent=2,
            ),
        },
        "client_inventory": {
            "client_data": json.dumps(
                trim_clients(snapshot.get("active_clients", [])),
                indent=2,
            ),
        },
        "port_profile_map": {
            "port_data": json.dumps({
                "switches": [d for d in trim_devices(snapshot.get("devices", []))
                             if d.get("type") == "usw"],
                "port_profiles": snapshot.get("port_conf", []),
            }, indent=2),
        },
    }
    return data_map.get(section, {})


# ---------------------------------------------------------------------------
# Claude API Interaction
# ---------------------------------------------------------------------------

def generate_documentation(
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Send a documentation request to Claude and return the response text."""
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

ALL_SECTIONS = [
    "device_inventory",
    "network_map",
    "firewall_audit",
    "wireless_report",
    "client_inventory",
    "port_profile_map",
]


def run_documenter(
    snapshot_path: str,
    config: dict,
    prompts: dict,
    sections: list | None = None,
    output_dir: str | None = None,
):
    """Generate AI documentation from a snapshot file."""

    # Load snapshot
    with open(snapshot_path, "r") as f:
        snapshot = json.load(f)

    collected_at = snapshot.get("collected_at", "unknown")
    console.print(f"[cyan]Snapshot from: {collected_at}[/cyan]")

    # Initialize Claude client
    api_key = config["claude"]["api_key"]
    model = config["claude"]["model"]
    max_tokens = config["claude"]["max_tokens"]
    claude_client = anthropic.Anthropic(api_key=api_key)

    system_prompt = prompts["system_prompt"]
    network_context = yaml.dump(config.get("network_context", {}))

    sections_to_run = sections or ALL_SECTIONS
    out_dir = Path(output_dir or config["output"]["report_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    report_parts = []
    report_parts.append(f"# Eirdom Network Documentation\n")
    report_parts.append(f"**Generated:** {datetime.now().isoformat()}\n")
    report_parts.append(f"**Snapshot:** {collected_at}\n")
    report_parts.append(f"**Domain:** ad.eirdom.homes\n\n---\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for section in sections_to_run:
            template = prompts["templates"].get(section)
            if not template:
                console.print(f"[yellow]⚠ No template for section: {section}[/yellow]")
                continue

            task = progress.add_task(
                f"Generating: {template['name']}...", total=None
            )

            # Build the user prompt
            section_data = prepare_section_data(snapshot, section)
            user_prompt = template["prompt"].format(
                network_context=network_context,
                **section_data,
            )

            try:
                result = generate_documentation(
                    claude_client, model, max_tokens, system_prompt, user_prompt
                )
                report_parts.append(f"\n{result}\n\n---\n")
                progress.update(task, description=f"[green]✓ {template['name']}[/green]")
            except Exception as e:
                error_msg = f"\n## {template['name']}\n\n> **ERROR:** {e}\n\n---\n"
                report_parts.append(error_msg)
                progress.update(
                    task, description=f"[red]✗ {template['name']}: {e}[/red]"
                )

    # Write combined report
    report_content = "\n".join(report_parts)
    report_file = out_dir / f"{timestamp}_network_documentation.md"
    with open(report_file, "w") as f:
        f.write(report_content)

    console.print(f"\n[green]✓ Report saved to {report_file}[/green]")
    console.print(f"  Sections generated: {len(sections_to_run)}")
    return report_file


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Eirdom NetOps — AI Documentation Generator"
    )
    parser.add_argument(
        "--snapshot", "-s",
        required=True,
        help="Path to the JSON snapshot file",
    )
    parser.add_argument(
        "--sections",
        nargs="+",
        choices=ALL_SECTIONS,
        default=None,
        help="Specific sections to generate (default: all)",
    )
    parser.add_argument(
        "--config", "-c",
        default="config/config.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Override output directory",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    prompts = load_prompts()
    run_documenter(args.snapshot, config, prompts, args.sections, args.output)


if __name__ == "__main__":
    main()
