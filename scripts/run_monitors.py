#!/usr/bin/env python3
"""Unified monitor runner for Railway cron jobs.

Set MONITOR_NAME env var to one of:
  satellite-freshness | legislation | dcp-monitor | dcp-watchdog
  regulatory-freshness | security | mutation-health | stats-refresh

Each monitor runs its script, pings healthchecks.io on completion,
and sends Telegram alerts on failure.

The `security`, `mutation-health` and `stats-refresh` jobs are the weekly
maintenance tasks migrated off GitHub Actions; they ship in the heavier
`Dockerfile.maintenance` image rather than `Dockerfile.monitors`.
"""

import os
import subprocess
import sys
import traceback

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
    "dcp-extract": {
        # Extract-to-review: re-extract changed chapters in memory and enqueue the
        # diff to dcp_review_queue for human approval. --review = NO provision
        # commit. Restores the step dropped in the GitHub Actions -> Railway
        # migration (#506). Needs DATABASE_URL + R2_* creds on the Railway service.
        "cmd": ["python", "scripts/dcp_extract_changed.py", "--review"],
    },
    "dcp-extract-all": {
        # Scheduled re-extract-ALL (the targeted-semantic-detection cadence): re-extract
        # EVERY active chapter and diff vs the approved baseline, not just byte-change-
        # flagged ones. Identical detector to dcp-extract; only the chapter set differs
        # (--all drops the needs_extraction filter, keeps is_active + r2_current_path).
        # Runs on a slow cadence (quarterly) so PDF re-exports that flip the byte signal
        # no longer gate detection, and a silent in-place amendment is still caught.
        # --review = NO provision commit; diffs go to dcp_review_queue for human approval.
        "cmd": ["python", "scripts/dcp_extract_changed.py", "--all", "--review"],
    },
    "dcp-commit": {
        # Commit-on-approve: commit chapters whose every dcp_review_queue row a human
        # marked 'approved' (currency-guarded). Reuses extract_chapter. --commit makes
        # it write; without it the worker is a dry run. The human gate is the queue.
        "cmd": ["python", "scripts/dcp_commit_approved.py", "--commit"],
    },
    "dcp-watchdog": {
        "cmd": ["python", "scripts/dcp_watchdog.py"],
    },
    "property-alerts": {
        # Property-alerts delivery: email each active subscriber about new
        # development applications near their address (the last mile on the
        # existing threat_radar subscription/check machinery). Needs
        # DATABASE_URL + RESEND_API_KEY on the Railway service. Exit 2 =
        # per-subscription send failures (dispatcher already Telegram-alerted).
        "cmd": ["python", "scripts/run_alerts_dispatch.py"],
    },
    "regulatory-freshness": {
        "cmd": ["python", "scripts/regulatory_freshness_monitor.py"],
    },
    # --- Weekly maintenance jobs (migrated off GitHub Actions, 2026-06) ---
    # These ship in Dockerfile.maintenance, not Dockerfile.monitors.
    "security": {
        "cmd": ["python", "scripts/security_scan.py"],
    },
    "mutation-health": {
        "cmd": ["python", "scripts/mutation_health.py"],
    },
    "stats-refresh": {
        "cmd": ["python", "scripts/refresh_stats_job.py"],
    },
}


def send_telegram(msg: str) -> None:
    """Best-effort crash report to Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg[:4000]},
            timeout=10,
        )
    except Exception:
        pass


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
    # Diagnostic: log which env vars are set (names only, not values)
    diag_keys = ["MONITOR_NAME", "DATABASE_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "HC_PING_URL"]
    present = [k for k in diag_keys if os.environ.get(k)]
    missing = [k for k in diag_keys if not os.environ.get(k)]
    print(f"[run_monitors] Env present: {present}")
    print(f"[run_monitors] Env missing: {missing}")

    monitor_name = os.environ.get("MONITOR_NAME", "").strip()
    if monitor_name not in MONITORS:
        msg = (
            f"Unknown MONITOR_NAME={monitor_name!r}. "
            f"Expected one of: {', '.join(MONITORS)}"
        )
        print(msg, file=sys.stderr)
        send_telegram(f"🚨 run_monitors: {msg}\nEnv missing: {missing}")
        return 1

    config = MONITORS[monitor_name]
    hc_url = os.environ.get("HC_PING_URL") or ""

    print(f"[run_monitors] Starting: {monitor_name}")
    result = subprocess.run(config["cmd"], env=os.environ.copy(), capture_output=True, text=True)
    exit_code = result.returncode
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Exit code 0 = healthy, 2 = degraded (still a "successful run" for heartbeat)
    failed = exit_code not in (0, 2)
    ping_healthcheck(hc_url, failed=failed)

    if failed:
        print(f"[run_monitors] {monitor_name} failed with exit code {exit_code}")
        stderr_tail = (result.stderr or "")[-2000:]
        send_telegram(f"🚨 {monitor_name} failed (exit {exit_code})\nEnv missing: {missing}\n{stderr_tail}")
    elif exit_code == 2:
        print(f"[run_monitors] {monitor_name} completed with warnings (exit 2)")
    else:
        print(f"[run_monitors] {monitor_name} completed successfully")

    # Railway (and most schedulers) mark ANY non-zero exit as a failed run.
    # Exit 2 from a monitor means it ran fine and simply *found something*
    # (legislation_monitor / r2_monitor / dcp_watchdog all use 2 = "changes
    # detected" / "stale chapters found"). That is a healthy run, not a crash —
    # the monitor already sent its own Telegram alert. Report success to the OS
    # so the cron dashboard isn't permanently red on every findings run.
    # Real failures (exit 1, crashes) still propagate as non-zero.
    return 0 if exit_code == 2 else exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        monitor = os.environ.get("MONITOR_NAME", "unknown")
        send_telegram(f"🚨 run_monitors CRASH ({monitor}):\n{tb[-3000:]}")
        sys.exit(1)
