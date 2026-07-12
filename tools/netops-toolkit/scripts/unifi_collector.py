#!/usr/bin/env python3
"""
Eirdom NetOps Toolkit — UniFi API Collector

Connects to the UDM-Pro-Max API and pulls live network state data,
saving timestamped JSON snapshots for AI documentation generation
and drift detection.

Usage:
    python unifi_collector.py --target all
    python unifi_collector.py --target devices
    python unifi_collector.py --target firewall
    python unifi_collector.py --config /path/to/config.yaml --output /path/to/output
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import requests
import yaml
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COLLECTOR_VERSION = "1.1.0"

# Request timeouts — connect timeout, read timeout (seconds)
REQUEST_TIMEOUT = (10, 30)

# Retry configuration for transient failures
RETRY_TOTAL = 3
RETRY_BACKOFF_FACTOR = 1.0
RETRY_STATUS_FORCELIST = (429, 500, 502, 503, 504)

# UDM API endpoints
_ENDPOINT_DEVICES        = "stat/device"
_ENDPOINT_CLIENTS        = "stat/sta"
_ENDPOINT_HEALTH         = "stat/health"
_ENDPOINT_SYSINFO        = "stat/sysinfo"
_ENDPOINT_DPI            = "stat/sitedpi"
_ENDPOINT_DHCP_LEASES    = "stat/dhcplease"
_ENDPOINT_NETWORKS       = "rest/networkconf"
_ENDPOINT_WLAN           = "rest/wlanconf"
_ENDPOINT_FIREWALL_RULES = "rest/firewallrule"
_ENDPOINT_FIREWALL_GROUPS= "rest/firewallgroup"
_ENDPOINT_PORT_CONF      = "rest/portconf"
_ENDPOINT_RADIUS         = "rest/radiusprofile"
_ENDPOINT_ROUTING        = "rest/routing"
_ENDPOINT_PORT_FORWARD   = "rest/portforward"

# ---------------------------------------------------------------------------
# Logging — structured output for both interactive and cron use
# ---------------------------------------------------------------------------

def setup_logging(log_dir: Path | None = None, verbose: bool = False) -> logging.Logger:
    """
    Configure logging with RichHandler for console and FileHandler for
    persistent log files. Returns the module-level logger.

    When running as a cron job, log_dir should point to the output/logs
    directory so failures are auditable without a terminal.
    """
    level = logging.DEBUG if verbose else logging.INFO

    handlers: list[logging.Handler] = [
        RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
        )
    ]

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"collector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )

    return logging.getLogger("eirdom.collector")


log = logging.getLogger("eirdom.collector")
console = Console()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config(config_path: str | Path) -> dict[str, Any]:
    """
    Load config.yaml with environment variable substitution.

    Resolves ${ENV_VAR} patterns using the current environment and any
    .env file present in the working directory. Raises FileNotFoundError
    if the config file does not exist.
    """
    load_dotenv()

    path = Path(config_path).resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Copy config/config.example.yaml to config/config.yaml and fill in your values."
        )

    raw = path.read_text(encoding="utf-8")

    # Substitute ${ENV_VAR} placeholders with environment values
    for key, value in os.environ.items():
        raw = raw.replace(f"${{{key}}}", value)

    config = yaml.safe_load(raw)

    _validate_config(config)
    return config


def _validate_config(config: dict[str, Any]) -> None:
    """Raise ValueError for missing or invalid required config keys."""
    required = {
        "unifi": ["controller_url", "username", "password", "site"],
        "output": ["snapshot_dir", "report_dir"],
    }
    for section, keys in required.items():
        if section not in config:
            raise ValueError(f"Config missing required section: [{section}]")
        for key in keys:
            if key not in config[section]:
                raise ValueError(f"Config missing required key: [{section}].{key}")

    url = config["unifi"]["controller_url"]
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid controller_url — must start with http:// or https://: {url}")


# ---------------------------------------------------------------------------
# HTTP Session Factory
# ---------------------------------------------------------------------------

def _build_session(verify_ssl: bool) -> requests.Session:
    """
    Build a requests.Session with retry logic and connection pooling.

    Retries on transient server errors (5xx, 429) with exponential backoff.
    SSL verification is disabled for UDM self-signed certificates on LAN.
    """
    if not verify_ssl:
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    session = requests.Session()
    session.verify = verify_ssl

    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_FORCELIST,
        allowed_methods={"GET", "POST"},
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# ---------------------------------------------------------------------------
# UniFi API Client
# ---------------------------------------------------------------------------

class UniFiAuthError(Exception):
    """Raised when authentication to the UniFi controller fails."""


class UniFiAPIError(Exception):
    """Raised when an API call returns an unexpected response."""


class UniFiClient:
    """
    Minimal UniFi Controller / UDM-Pro API client.

    Supports both UDM-Pro (new API at /api/auth/login) and legacy
    controllers (/api/login). Use as a context manager to ensure
    the session is properly closed and the UDM logout endpoint is called.

    Example:
        with UniFiClient(config) as client:
            snapshot = client.collect_all()
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._base_url: str = config["unifi"]["controller_url"].rstrip("/")
        self._site: str = config["unifi"]["site"]
        self._is_udm: bool = config["unifi"].get("is_udm", True)
        self._verify_ssl: bool = config["unifi"].get("verify_ssl", False)
        self._session: requests.Session = _build_session(self._verify_ssl)
        self._authenticated: bool = False
        self._login(config["unifi"]["username"], config["unifi"]["password"])

    def __enter__(self) -> "UniFiClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """Log out from the controller and close the HTTP session."""
        if self._authenticated:
            try:
                logout_url = (
                    f"{self._base_url}/api/auth/logout"
                    if self._is_udm
                    else f"{self._base_url}/api/logout"
                )
                self._session.post(logout_url, timeout=REQUEST_TIMEOUT)
                log.debug("Logged out from UniFi controller")
            except Exception as exc:
                log.debug("Logout request failed (non-fatal): %s", exc)
            finally:
                self._authenticated = False
        self._session.close()

    # ── Authentication ────────────────────────────────────────────────────

    def _login(self, username: str, password: str) -> None:
        """
        Authenticate against the UniFi controller.

        Raises UniFiAuthError on failure rather than calling sys.exit()
        so callers can handle the error appropriately (e.g. retry, alert).
        """
        login_url = (
            f"{self._base_url}/api/auth/login"
            if self._is_udm
            else f"{self._base_url}/api/login"
        )
        try:
            resp = self._session.post(
                login_url,
                json={"username": username, "password": password},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.ConnectionError as exc:
            raise UniFiAuthError(
                f"Cannot reach UniFi controller at {self._base_url}\n"
                f"Check that the controller is online and the URL is correct.\n"
                f"Detail: {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise UniFiAuthError(
                f"Connection timed out reaching {self._base_url}"
            ) from exc

        if resp.status_code in (401, 403):
            raise UniFiAuthError(
                f"Authentication failed (HTTP {resp.status_code}) — "
                f"check username and password in config.yaml"
            )
        if resp.status_code != 200:
            raise UniFiAuthError(
                f"Unexpected login response: HTTP {resp.status_code} — {resp.text[:200]}"
            )

        self._authenticated = True
        log.info("Authenticated to UniFi controller at %s", self._base_url)

    # ── Internal HTTP helpers ─────────────────────────────────────────────

    def _api_url(self, endpoint: str) -> str:
        """Build the full API URL for a site-scoped endpoint."""
        if self._is_udm:
            return f"{self._base_url}/proxy/network/api/s/{self._site}/{endpoint}"
        return f"{self._base_url}/api/s/{self._site}/{endpoint}"

    def _get(self, endpoint: str) -> list[Any] | dict[str, Any]:
        """
        Perform a GET request and return the 'data' value from the response.

        Raises UniFiAPIError on non-2xx responses after retries are exhausted.
        """
        url = self._api_url(endpoint)
        log.debug("GET %s", url)

        try:
            resp = self._session.get(url, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout as exc:
            raise UniFiAPIError(f"Request timed out: GET {endpoint}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise UniFiAPIError(f"Connection error: GET {endpoint} — {exc}") from exc

        if not resp.ok:
            raise UniFiAPIError(
                f"API error: GET {endpoint} returned HTTP {resp.status_code} — {resp.text[:200]}"
            )

        try:
            body = resp.json()
        except ValueError as exc:
            raise UniFiAPIError(
                f"Invalid JSON response from {endpoint}: {resp.text[:200]}"
            ) from exc

        return body.get("data", body)

    def _get_safe(
        self, endpoint: str, name: str
    ) -> list[Any] | dict[str, Any]:
        """
        Wrapper around _get() that catches errors and returns an empty list.

        Used for optional endpoints that may not be available on all
        controller versions (e.g. DPI stats, DHCP leases). Logs the
        failure at WARNING level so it appears in log files.
        """
        try:
            data = self._get(endpoint)
            count = len(data) if isinstance(data, list) else 1
            log.debug("  • %-20s %d items", name, count)
            return data
        except UniFiAPIError as exc:
            log.warning("  • %-20s UNAVAILABLE — %s", name, exc)
            return []

    # ── Collection Methods ────────────────────────────────────────────────

    def get_devices(self) -> list[Any]:
        """All adopted UniFi devices (APs, switches, gateways)."""
        return self._get(_ENDPOINT_DEVICES)  # type: ignore[return-value]

    def get_active_clients(self) -> list[Any]:
        """All currently connected clients (wired and wireless)."""
        return self._get(_ENDPOINT_CLIENTS)  # type: ignore[return-value]

    def get_networks(self) -> list[Any]:
        """All configured networks / VLANs."""
        return self._get(_ENDPOINT_NETWORKS)  # type: ignore[return-value]

    def get_wlan_conf(self) -> list[Any]:
        """All wireless network (SSID) configurations."""
        return self._get(_ENDPOINT_WLAN)  # type: ignore[return-value]

    def get_firewall_rules(self) -> list[Any]:
        """All firewall rules (LAN in/out, WAN in/out, guest)."""
        return self._get(_ENDPOINT_FIREWALL_RULES)  # type: ignore[return-value]

    def get_firewall_groups(self) -> list[Any]:
        """Firewall groups (IP groups, port groups)."""
        return self._get(_ENDPOINT_FIREWALL_GROUPS)  # type: ignore[return-value]

    def get_port_conf(self) -> list[Any]:
        """Switch port profiles."""
        return self._get(_ENDPOINT_PORT_CONF)  # type: ignore[return-value]

    def get_radius_profiles(self) -> list[Any]:
        """RADIUS profiles (for 802.1X)."""
        return self._get(_ENDPOINT_RADIUS)  # type: ignore[return-value]

    def get_routing(self) -> list[Any]:
        """Static routes."""
        return self._get(_ENDPOINT_ROUTING)  # type: ignore[return-value]

    def get_sysinfo(self) -> dict[str, Any]:
        """System info (controller version, uptime, etc.)."""
        result = self._get(_ENDPOINT_SYSINFO)
        # sysinfo returns a list with one item on some firmware versions
        if isinstance(result, list) and result:
            return result[0]
        return result  # type: ignore[return-value]

    def get_health(self) -> list[Any]:
        """Site health summary (WAN, LAN, WLAN subsystems)."""
        return self._get(_ENDPOINT_HEALTH)  # type: ignore[return-value]

    def get_dpi_stats(self) -> list[Any]:
        """Deep packet inspection stats (optional — may not be enabled)."""
        return self._get_safe(_ENDPOINT_DPI, "dpi_stats")  # type: ignore[return-value]

    def get_port_forward(self) -> list[Any]:
        """
        Port forwarding rules.

        This should return an EMPTY list for Eirdom. Any entries here
        indicate an unexpected inbound port forward — flag as a security issue.
        """
        return self._get(_ENDPOINT_PORT_FORWARD)  # type: ignore[return-value]

    def get_dhcp_leases(self) -> list[Any]:
        """Active DHCP leases (UDM firmware 4.x+, optional)."""
        return self._get_safe(_ENDPOINT_DHCP_LEASES, "dhcp_leases")  # type: ignore[return-value]

    def collect_all(self) -> dict[str, Any]:
        """
        Pull all available data and return as a structured snapshot dict.

        Required endpoints raise on failure. Optional endpoints (DPI, DHCP
        leases) return empty lists if unavailable, with a WARNING log entry.
        """
        log.info("Collecting full network snapshot from %s", self._base_url)

        snapshot: dict[str, Any] = {
            "collected_at": datetime.now().isoformat(),
            "collector_version": COLLECTOR_VERSION,
            "controller_url": self._base_url,
            "site": self._site,
            # Required — raise on failure
            "sysinfo":          self.get_sysinfo(),
            "health":           self.get_health(),
            "devices":          self.get_devices(),
            "networks":         self.get_networks(),
            "wlan_conf":        self.get_wlan_conf(),
            "firewall_rules":   self.get_firewall_rules(),
            "firewall_groups":  self.get_firewall_groups(),
            "port_conf":        self.get_port_conf(),
            "port_forward":     self.get_port_forward(),
            "radius_profiles":  self.get_radius_profiles(),
            "routing":          self.get_routing(),
            "active_clients":   self.get_active_clients(),
            # Optional — return [] if unavailable
            "dpi_stats":        self.get_dpi_stats(),
            "dhcp_leases":      self.get_dhcp_leases(),
        }

        totals = {
            k: len(v) if isinstance(v, list) else 1
            for k, v in snapshot.items()
            if k not in ("collected_at", "collector_version", "controller_url", "site")
        }
        log.info(
            "Snapshot complete — %s",
            ", ".join(f"{k}: {v}" for k, v in totals.items()),
        )

        return snapshot


# ---------------------------------------------------------------------------
# Snapshot Persistence
# ---------------------------------------------------------------------------

def save_snapshot(snapshot: dict[str, Any], output_dir: str | Path) -> Path:
    """
    Serialize snapshot to a timestamped JSON file.

    Raises OSError if the output directory cannot be created or the
    file cannot be written (e.g. disk full).
    """
    out_path = Path(output_dir)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(
            f"Cannot create snapshot output directory: {out_path} — {exc}"
        ) from exc

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = out_path / f"{timestamp}_full.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, default=str)
    except OSError as exc:
        raise OSError(f"Cannot write snapshot file: {filename} — {exc}") from exc

    log.info("Snapshot saved → %s", filename)
    return filename


# ---------------------------------------------------------------------------
# Terminal Summary
# ---------------------------------------------------------------------------

def print_summary(snapshot: dict[str, Any]) -> None:
    """Print a quick summary table and flag any security issues."""
    table = Table(title="Eirdom Network Snapshot Summary", show_lines=True)
    table.add_column("Category", style="cyan", min_width=20)
    table.add_column("Count", style="green", justify="right")
    table.add_column("Status", justify="center")

    display_keys = [
        ("devices",        "Devices"),
        ("networks",       "Networks / VLANs"),
        ("wlan_conf",      "SSIDs"),
        ("firewall_rules", "Firewall Rules"),
        ("active_clients", "Active Clients"),
        ("port_forward",   "Port Forwards"),
        ("routing",        "Static Routes"),
        ("radius_profiles","RADIUS Profiles"),
        ("dhcp_leases",    "DHCP Leases"),
    ]

    security_issues: list[str] = []

    for key, label in display_keys:
        data = snapshot.get(key, [])
        count = len(data) if isinstance(data, list) else 1

        if key == "port_forward" and count > 0:
            status = "[red]⚠ UNEXPECTED[/red]"
            security_issues.append(
                f"{count} port forward(s) detected — Eirdom should have ZERO inbound port forwards"
            )
        else:
            status = "[green]✓[/green]"

        table.add_row(label, str(count), status)

    console.print(table)

    if security_issues:
        console.print("\n[bold red]SECURITY ISSUES DETECTED:[/bold red]")
        for issue in security_issues:
            console.print(f"  [red]⚠  {issue}[/red]")
            log.warning("SECURITY: %s", issue)

    # Log summary to file as well
    log.info(
        "Summary — devices: %d, networks: %d, clients: %d, port_forwards: %d",
        len(snapshot.get("devices", [])),
        len(snapshot.get("networks", [])),
        len(snapshot.get("active_clients", [])),
        len(snapshot.get("port_forward", [])),
    )


# ---------------------------------------------------------------------------
# CLI Target Registry
# ---------------------------------------------------------------------------

# Maps CLI --target names to UniFiClient method names.
# Using a dict of callables (resolved at runtime) rather than strings
# + getattr avoids silent failures if method names change.
TARGETS: dict[str, str] = {
    "all":      "collect_all",
    "devices":  "get_devices",
    "networks": "get_networks",
    "wireless": "get_wlan_conf",
    "firewall": "get_firewall_rules",
    "clients":  "get_active_clients",
    "ports":    "get_port_conf",
    "health":   "get_health",
    "forward":  "get_port_forward",
}


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Main entry point. Returns an exit code (0 = success, 1 = failure).

    Designed to be called by cron or interactively. All errors are logged
    before returning a non-zero exit code — no unhandled exceptions reach
    the caller.
    """
    parser = argparse.ArgumentParser(
        description="Eirdom NetOps — UniFi API Collector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join([
            "Targets:",
            *[f"  {k:<12} {v}" for k, v in {
                "all":      "Full snapshot (default)",
                "devices":  "Adopted UniFi devices",
                "networks": "VLANs and network configs",
                "wireless": "SSID configurations",
                "firewall": "Firewall rules",
                "clients":  "Currently connected clients",
                "ports":    "Switch port profiles",
                "health":   "Site health summary",
                "forward":  "Port forwards (should be empty)",
            }.items()],
        ]),
    )
    parser.add_argument(
        "--target", "-t",
        choices=list(TARGETS.keys()),
        default="all",
        help="Data category to collect (default: all)",
    )
    parser.add_argument(
        "--config", "-c",
        default=None,
        help="Path to config.yaml (default: config/config.yaml relative to script dir)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Override snapshot output directory",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable file logging (console only — use for interactive runs)",
    )
    args = parser.parse_args()

    # Resolve config path relative to the script's own directory
    # so the script works regardless of where it is invoked from
    script_dir = Path(__file__).parent.parent  # tools/netops-toolkit/
    config_path = Path(args.config) if args.config else script_dir / "config" / "config.yaml"

    # Set up logging
    log_dir: Path | None = None
    if not args.no_log_file:
        # Load config minimally just to get output dir for log path
        try:
            _cfg = load_config(config_path)
            _snapshot_dir: str = _cfg.get("output", {}).get("snapshot_dir", "output/snapshots")
            log_dir = (script_dir / _snapshot_dir).parent / "logs"
        except Exception:
            log_dir = script_dir / "output" / "logs"

    setup_logging(log_dir=log_dir, verbose=args.verbose)

    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError) as exc:
        log.error("Configuration error: %s", exc)
        return 1

    try:
        with UniFiClient(config) as client:
            if args.target == "all":
                snapshot = client.collect_all()
                print_summary(snapshot)
                output_dir = args.output or config["output"]["snapshot_dir"]
                # Resolve relative to script dir
                output_path = (
                    Path(output_dir)
                    if Path(output_dir).is_absolute()
                    else script_dir / output_dir
                )
                save_snapshot(snapshot, output_path)
            else:
                method_name = TARGETS[args.target]
                method = getattr(client, method_name)
                data = method()
                console.print_json(json.dumps(data, indent=2, default=str))

    except UniFiAuthError as exc:
        log.error("Authentication failed: %s", exc)
        return 1
    except UniFiAPIError as exc:
        log.error("API error: %s", exc)
        return 1
    except OSError as exc:
        log.error("File system error: %s", exc)
        return 1
    except KeyboardInterrupt:
        log.info("Interrupted by user")
        return 130  # Standard SIGINT exit code
    except Exception as exc:
        log.exception("Unexpected error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())