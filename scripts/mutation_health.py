#!/usr/bin/env python3
"""Weekly mutation-testing health check — Railway maintenance cron.

Replaces `.github/workflows/mutation-weekly.yml`. Runs mutmut across the
three covered service files and reports the kill rate to Telegram (replacing
the old GitHub-issue mechanism, which was Actions-specific).

This is the "are our tests decaying?" early-warning signal. It complements the
pre-push mutation-baseline ratchet (which only stops the test *count* dropping)
by measuring actual kill-rate decay. Running in a clean Linux container also
sidesteps the mutmut WSL crash hazard noted for local runs.

Dispatched via run_monitors.py with MONITOR_NAME=mutation-health.

Exit codes:
  0  all services at/above the warning threshold
  2  one or more services below threshold (degraded — still a successful run)
  1  mutmut could not run at all
"""

import os
import sqlite3
import subprocess
import sys

WARN_THRESHOLD = 65.0  # percent kill rate

SERVICES = [
    ("flood_truth", "services/flood_truth.py", "tests/test_flood_truth.py"),
    ("threat_radar", "services/threat_radar.py", "tests/test_threat_radar_mutation.py"),
    ("granny_flat", "services/granny_flat.py", "tests/test_granny_flat_mutation.py"),
]


def send_telegram(msg: str) -> None:
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


def run_one(name: str, src: str, tests: str) -> dict:
    """Run mutmut for a single service; return parsed counts (or error)."""
    if not (os.path.exists(src) and os.path.exists(tests)):
        return {"name": name, "skipped": True}

    # Fresh cache each run so counts are not cumulative across weeks.
    for stale in (".mutmut-cache",):
        try:
            os.remove(stale)
        except OSError:
            pass

    runner = f"python -m pytest {tests} -x -q --no-header --tb=no"
    cmd = [
        "python", "-m", "mutmut", "run",
        f"--paths-to-mutate={src}",
        "--tests-dir=tests/",
        f"--runner={runner}",
        "--no-progress",
    ]
    # mutmut exits non-zero when mutants survive; that is expected, not an error.
    subprocess.run(cmd, capture_output=True, text=True, timeout=2400)

    try:
        conn = sqlite3.connect(".mutmut-cache")
        cur = conn.cursor()
        cur.execute("SELECT status, count(*) FROM Mutant GROUP BY status")
        counts = dict(cur.fetchall())
        conn.close()
    except Exception as e:  # noqa: BLE001 — surface the parse failure, don't crash the batch
        return {"name": name, "error": str(e)}

    total = sum(counts.values())
    killed = counts.get("ok_killed", 0)
    survived = counts.get("bad_survived", 0)
    pct = round(killed / total * 100, 1) if total else 0.0
    return {
        "name": name,
        "total": total,
        "killed": killed,
        "survived": survived,
        "pct": pct,
    }


def main() -> int:
    results = [run_one(*svc) for svc in SERVICES]

    ran = [r for r in results if not r.get("skipped") and "error" not in r]
    if not ran:
        send_telegram("🚨 mutation-health: no services could be scanned (mutmut/deps?)")
        print("No services scanned", file=sys.stderr)
        return 1

    overall_killed = sum(r["killed"] for r in ran)
    overall_total = sum(r["total"] for r in ran)
    overall_pct = round(overall_killed / overall_total * 100, 1) if overall_total else 0.0

    lines = [f"🧬 Weekly mutation health — overall {overall_killed}/{overall_total} ({overall_pct}%)", ""]
    below = False
    for r in results:
        if r.get("skipped"):
            lines.append(f"  ⏭ {r['name']}: skipped (file/tests missing)")
            continue
        if "error" in r:
            lines.append(f"  ❓ {r['name']}: parse error ({r['error'][:80]})")
            continue
        emoji = "🟢" if r["pct"] >= 70 else "🟡" if r["pct"] >= WARN_THRESHOLD else "🔴"
        if r["pct"] < WARN_THRESHOLD:
            below = True
        lines.append(f"  {emoji} {r['name']}: {r['killed']}/{r['total']} ({r['pct']}%), {r['survived']} survived")

    summary = "\n".join(lines)
    print(summary)
    send_telegram(summary)
    return 2 if below else 0


if __name__ == "__main__":
    sys.exit(main())
