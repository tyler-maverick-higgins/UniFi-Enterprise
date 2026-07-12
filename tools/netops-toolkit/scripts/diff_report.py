#!/usr/bin/env python3
"""
Eirdom NetOps Toolkit — Snapshot Diff Report
Compares two network snapshots and generates a change report via Claude AI.

Usage:
    python diff_report.py \
        --old output/snapshots/2026-04-04_full.json \
        --new output/snapshots/2026-04-11_full.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
import yaml
from deepdiff import DeepDiff
from dotenv import load_dotenv
from rich.console import Console

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
# Diff Logic
# ---------------------------------------------------------------------------

TRACKED_SECTIONS = [
    "devices",
    "networks",
    "wlan_conf",
    "firewall_rules",
    "port_forward",
    "routing",
    "port_conf",
]


def compute_diff(old_snapshot: dict, new_snapshot: dict) -> dict:
    """Compute a structured diff between two snapshots."""
    diffs = {}

    for section in TRACKED_SECTIONS:
        old_data = old_snapshot.get(section, [])
        new_data = new_snapshot.get(section, [])

        diff = DeepDiff(old_data, new_data, ignore_order=True, verbose_level=2)

        if diff:
            # Convert DeepDiff to serializable dict
            diffs[section] = json.loads(diff.to_json())

    # Client count comparison (not full diff — too noisy)
    old_clients = len(old_snapshot.get("active_clients", []))
    new_clients = len(new_snapshot.get("active_clients", []))
    diffs["client_count"] = {
        "old": old_clients,
        "new": new_clients,
        "delta": new_clients - old_clients,
    }

    return diffs


def generate_diff_summary(diffs: dict) -> str:
    """Create a human-readable summary of what changed."""
    lines = []
    for section, diff in diffs.items():
        if section == "client_count":
            delta = diff["delta"]
            direction = "more" if delta > 0 else "fewer"
            lines.append(
                f"- **Clients**: {diff['new']} active "
                f"({abs(delta)} {direction} than previous snapshot)"
            )
        elif diff:
            change_count = sum(len(v) if isinstance(v, dict) else 1
                               for v in diff.values())
            lines.append(f"- **{section}**: {change_count} changes detected")
        else:
            lines.append(f"- **{section}**: No changes")

    return "\n".join(lines) if lines else "No changes detected."


# ---------------------------------------------------------------------------
# AI-Powered Change Report
# ---------------------------------------------------------------------------

def generate_ai_diff_report(
    config: dict,
    prompts: dict,
    old_snapshot: dict,
    new_snapshot: dict,
    diffs: dict,
) -> str:
    """Send the diff to Claude for a detailed change analysis."""
    api_key = config["claude"]["api_key"]
    model = config["claude"]["model"]
    max_tokens = config["claude"]["max_tokens"]

    system_prompt = prompts["system_prompt"]
    template = prompts["templates"]["change_diff"]

    # Build a trimmed version of the diff for the AI prompt
    # (full snapshots would be too large)
    diff_payload = {
        "structured_diff": diffs,
        "old_summary": {
            "collected_at": old_snapshot.get("collected_at"),
            "device_count": len(old_snapshot.get("devices", [])),
            "network_count": len(old_snapshot.get("networks", [])),
            "firewall_rule_count": len(old_snapshot.get("firewall_rules", [])),
            "client_count": len(old_snapshot.get("active_clients", [])),
            "port_forward_count": len(old_snapshot.get("port_forward", [])),
        },
        "new_summary": {
            "collected_at": new_snapshot.get("collected_at"),
            "device_count": len(new_snapshot.get("devices", [])),
            "network_count": len(new_snapshot.get("networks", [])),
            "firewall_rule_count": len(new_snapshot.get("firewall_rules", [])),
            "client_count": len(new_snapshot.get("active_clients", [])),
            "port_forward_count": len(new_snapshot.get("port_forward", [])),
        },
    }

    user_prompt = template["prompt"].format(
        old_timestamp=old_snapshot.get("collected_at", "unknown"),
        new_timestamp=new_snapshot.get("collected_at", "unknown"),
        old_snapshot=json.dumps(diff_payload["old_summary"], indent=2),
        new_snapshot=json.dumps({
            **diff_payload["new_summary"],
            "diff_details": diff_payload["structured_diff"],
        }, indent=2),
    )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Eirdom NetOps — Snapshot Diff Report"
    )
    parser.add_argument(
        "--old",
        required=True,
        help="Path to the older snapshot JSON file",
    )
    parser.add_argument(
        "--new",
        required=True,
        help="Path to the newer snapshot JSON file",
    )
    parser.add_argument(
        "--config", "-c",
        default="config/config.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Only show raw diff, skip AI analysis",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Override output directory",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    prompts = load_prompts()

    # Load snapshots
    with open(args.old, "r") as f:
        old_snapshot = json.load(f)
    with open(args.new, "r") as f:
        new_snapshot = json.load(f)

    console.print(f"[cyan]Old snapshot:[/cyan] {old_snapshot.get('collected_at')}")
    console.print(f"[cyan]New snapshot:[/cyan] {new_snapshot.get('collected_at')}")

    # Compute diff
    console.print("\n[bold]Computing differences...[/bold]")
    diffs = compute_diff(old_snapshot, new_snapshot)
    summary = generate_diff_summary(diffs)
    console.print(f"\n{summary}")

    if not any(v for k, v in diffs.items() if k != "client_count"):
        console.print("\n[green]No configuration changes detected.[/green]")
        if args.no_ai:
            return

    # Generate AI report
    if not args.no_ai:
        console.print("\n[bold]Generating AI change report...[/bold]")
        ai_report = generate_ai_diff_report(
            config, prompts, old_snapshot, new_snapshot, diffs
        )

        out_dir = Path(args.output or config["output"]["report_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d")
        report_file = out_dir / f"{timestamp}_change_report.md"

        report_content = (
            f"# Eirdom Network Change Report\n\n"
            f"**Generated:** {datetime.now().isoformat()}\n\n"
            f"**Old snapshot:** {old_snapshot.get('collected_at')}\n\n"
            f"**New snapshot:** {new_snapshot.get('collected_at')}\n\n"
            f"---\n\n"
            f"## Quick Summary\n\n{summary}\n\n---\n\n"
            f"{ai_report}\n"
        )

        with open(report_file, "w") as f:
            f.write(report_content)

        console.print(f"\n[green]✓ Change report saved to {report_file}[/green]")
    else:
        # Dump raw diff
        console.print_json(json.dumps(diffs, indent=2, default=str))


if __name__ == "__main__":
    main()
