#!/usr/bin/env python3
"""Unified monitor runner for Railway cron jobs.

Set MONITOR_NAME env var to one of:
  satellite-freshness | legislation | dcp-monitor | dcp-watchdog

Each monitor runs its script, pings healthchecks.io on completion,
and sends Telegram alerts on failure.
"""

import os
import subprocess
import sys

import requests

MONITORS = {
    "satellite-freshness": {
        "cmd": ["python", "scripts/satellite_freshness_monitor.py", "--verbose"],
    },
    "legislation": {
        "cmd": ["python", "scripts/legislation_monitor.py", "--source", "pco"],
    },
    "dcp-monitor": {
        "cmd": ["python", "scripts/r2_monitor.py"],
        # No --council flag = runs all councils sequentially
    },
    "dcp-watchdog": {
        "cmd": ["python", "scripts/dcp_watchdog.py"],
    },
    "regulatory-freshness": {
        "cmd": ["python", "scripts/regulatory_freshness_monitor.py"],
    },
}


def ping_healthcheck(url: str, failed: bool = False) -> None:
    """Ping healthchecks.io endpoint."""
    if not url:
        return
    target = f"{url}/fail" if failed else url
    try:
        requests.get(target, timeout=10)
    except Exception as e:
        print(f"Healthcheck ping failed: {e}", file=sys.stderr)


def main() -> int:
    monitor_name = os.environ.get("MONITOR_NAME", "").strip()
    if monitor_name not in MONITORS:
        print(
            f"Unknown MONITOR_NAME={monitor_name!r}. "
            f"Expected one of: {', '.join(MONITORS)}",
            file=sys.stderr,
        )
        return 1

    config = MONITORS[monitor_name]
    hc_url = os.environ.get("HC_PING_URL", "")

    print(f"[run_monitors] Starting: {monitor_name}")
    result = subprocess.run(config["cmd"], env=os.environ.copy())
    exit_code = result.returncode

    # Exit code 0 = healthy, 2 = degraded (still a "successful run" for heartbeat)
    failed = exit_code not in (0, 2)
    ping_healthcheck(hc_url, failed=failed)

    if failed:
        print(f"[run_monitors] {monitor_name} failed with exit code {exit_code}")
    elif exit_code == 2:
        print(f"[run_monitors] {monitor_name} completed with warnings (exit 2)")
    else:
        print(f"[run_monitors] {monitor_name} completed successfully")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
