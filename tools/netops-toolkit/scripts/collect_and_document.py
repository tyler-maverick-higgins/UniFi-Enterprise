#!/usr/bin/env python3
"""
Eirdom NetOps Toolkit — Collect & Document (End-to-End)
Pulls live data from the UDM-Pro-Max, saves a snapshot, then generates
AI-powered documentation via Claude.

Usage:
    python collect_and_document.py
    python collect_and_document.py --sections device_inventory firewall_audit
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

# Add scripts dir to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from unifi_collector import UniFiClient, load_config, save_snapshot, print_summary
from ai_documenter import load_prompts, run_documenter, ALL_SECTIONS

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Eirdom NetOps — Full Collect + Document Pipeline"
    )
    parser.add_argument(
        "--sections",
        nargs="+",
        choices=ALL_SECTIONS,
        default=None,
        help="Specific doc sections to generate (default: all)",
    )
    parser.add_argument(
        "--config", "-c",
        default="config/config.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect data, skip AI documentation",
    )
    args = parser.parse_args()

    console.rule("[bold cyan]Eirdom NetOps Toolkit[/bold cyan]")

    # ── Phase 1: Collect ──────────────────────────────────────────────────
    console.print("\n[bold]Phase 1: Collecting from UDM-Pro-Max[/bold]\n")
    config = load_config(args.config)
    client = UniFiClient(config)
    snapshot = client.collect_all()
    print_summary(snapshot)
    snapshot_path = save_snapshot(snapshot, config["output"]["snapshot_dir"])

    if args.collect_only:
        console.print("\n[yellow]--collect-only flag set, skipping AI docs.[/yellow]")
        return

    # ── Phase 2: Document ─────────────────────────────────────────────────
    console.print("\n[bold]Phase 2: Generating AI Documentation[/bold]\n")
    prompts = load_prompts()
    report_path = run_documenter(
        str(snapshot_path), config, prompts, args.sections
    )

    # ── Summary ───────────────────────────────────────────────────────────
    console.rule("[bold green]Complete[/bold green]")
    console.print(f"  Snapshot:  {snapshot_path}")
    console.print(f"  Report:    {report_path}")
    console.print(
        "\n  [dim]Tip: commit both files to your private Git repo for "
        "version history.[/dim]"
    )


if __name__ == "__main__":
    main()
