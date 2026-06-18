#!/usr/bin/env python3
"""Weekly SAST scan (Semgrep) — Railway maintenance cron.

Replaces the Semgrep job in the old `.github/workflows/security.yml`.
Runs a full Semgrep scan at ERROR severity over the repo and reports the
finding count to Telegram. Dependency-vulnerability scanning (the old
`npm audit` job) is intentionally NOT here — GitHub Dependabot
(`.github/dependabot.yml`) covers that class and runs off Actions minutes.

Dispatched via `run_monitors.py` with MONITOR_NAME=security, which adds the
healthchecks.io ping and the failure Telegram alert. This script also sends
its own success summary so you get the finding count even on a clean run.

Exit codes (consumed by run_monitors.py):
  0  scan ran, zero ERROR findings
  2  scan ran, one or more ERROR findings (degraded — still a successful run)
  1  scan could not run (semgrep missing / crashed)
"""

import json
import os
import subprocess
import sys

# Semgrep rulesets — mirror of the old workflow.
CONFIGS = ["p/security-audit", "p/secrets"]
EXCLUDE = [
    "frontend-nextjs/migratePRPs",
    "node_modules",
    ".next",
    "venv_linux",
    "tests",
]


def send_telegram(msg: str) -> None:
    """Best-effort summary to Telegram (same env as run_monitors.py)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        import requests

        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg[:4000], "disable_web_page_preview": True},
            timeout=10,
        )
    except Exception:
        pass


def main() -> int:
    cmd = ["semgrep", "scan", "--severity", "ERROR", "--json"]
    for c in CONFIGS:
        cmd += ["--config", c]
    for e in EXCLUDE:
        cmd += ["--exclude", e]

    try:
        # Semgrep exits 1 when findings exist; that is not a runner error here.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except FileNotFoundError:
        send_telegram("🚨 security_scan: semgrep not installed in image")
        print("semgrep not found on PATH", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        send_telegram("🚨 security_scan: semgrep timed out (30m)")
        print("semgrep timed out", file=sys.stderr)
        return 1

    try:
        report = json.loads(result.stdout or "{}")
        findings = report.get("results", [])
    except json.JSONDecodeError:
        # Semgrep printed something other than JSON — treat as a runner error.
        print(result.stdout[-2000:], file=sys.stderr)
        print(result.stderr[-2000:], file=sys.stderr)
        send_telegram("🚨 security_scan: semgrep produced no parseable JSON")
        return 1

    n = len(findings)
    # Top offending files for a useful one-glance summary.
    by_path: dict[str, int] = {}
    for f in findings:
        p = f.get("path", "?")
        by_path[p] = by_path.get(p, 0) + 1
    top = sorted(by_path.items(), key=lambda kv: kv[1], reverse=True)[:8]

    if n == 0:
        print("Semgrep: 0 ERROR findings")
        send_telegram("✅ Semgrep weekly scan: 0 ERROR findings")
        return 0

    lines = [f"⚠️ Semgrep weekly scan: {n} ERROR finding(s)", ""]
    lines += [f"  {cnt}× {path}" for path, cnt in top]
    summary = "\n".join(lines)
    print(summary)
    send_telegram(summary)
    # Findings are informational (the old weekly job was continue-on-error).
    return 2


if __name__ == "__main__":
    sys.exit(main())
