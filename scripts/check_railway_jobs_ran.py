#!/usr/bin/env python3
# prior-art-checked: check_railway_cron_drift.py compares SCHEDULES only; run_monitors.py
# alerts from INSIDE a run, so it is silent when the run never starts. Nothing read a
# job's last outcome from outside Railway -- grepped scripts/, .github/workflows/ for
# latestDeployment, nextCronRunAt and CRASHED.
"""Did every scheduled Railway job run, and did its last run succeed?

WHY THIS EXISTS. From #1285's deploy until 2026-10-21, dcp-extract and dcp-commit
crashed at start-up on every run: Dockerfile.monitors did not copy a module both
import. Railway showed them as Crashed for days. Nothing told anyone, because the
only alerting lives in run_monitors.py, inside the job -- and a job that dies on an
import, or never starts, cannot report its own death.

This reads each job's state from outside, the way a person looking at the dashboard
would, and goes red on:
  * the latest deployment CRASHED (the last run exited non-zero) or FAILED (the
    latest build or deploy failed, so the job is running older code, or nothing);
  * the next scheduled run is in the past by more than GRACE (the scheduler stopped);
  * a status this script does not recognise, or none at all. Unknown is red.

It runs in .github/workflows/freshness-alarm.yml, before the healthchecks.io ping,
so a red job means no ping and the watchdog alerts.

Same token rule as check_railway_cron_drift.py: an ACCOUNT token; missing in CI fails.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_railway_cron_drift import API, ENVIRONMENT_ID, PROJECT_ID  # noqa: E402

#: How late a run may start before the scheduler counts as stopped.
GRACE = timedelta(hours=2)
#: The last run, or the latest deploy, ended badly.
BAD = {"CRASHED", "FAILED"}
#: Fine as they are: done, or on the way.
OK = {"SUCCESS", "BUILDING", "DEPLOYING", "INITIALIZING", "QUEUED", "WAITING", "SLEEPING"}


def fetch(token: str) -> list[dict]:
    """Every service instance in the production environment, as Railway reports it."""
    query = (
        "query { project(id: \"%s\") { services { edges { node { name "
        "serviceInstances { edges { node { environmentId cronSchedule nextCronRunAt "
        "latestDeployment { status createdAt } } } } } } } } }" % PROJECT_ID
    )
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # Without it Cloudflare answers 403 "error code: 1010" (see the drift check).
            "User-Agent": "compliance-engine-jobs-ran-check/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        payload = json.loads(resp.read())
    if payload.get("errors"):
        raise RuntimeError(f"Railway API returned errors: {payload['errors']}")
    out = []
    for edge in payload["data"]["project"]["services"]["edges"]:
        for inst in edge["node"]["serviceInstances"]["edges"]:
            node = inst["node"]
            if node.get("environmentId") == ENVIRONMENT_ID:
                out.append({"name": edge["node"]["name"], **node})
    return out


def judge(instances: list[dict], now: datetime) -> tuple[list[str], int]:
    """(problems, number of scheduled jobs checked). Pure: no network."""
    problems: list[str] = []
    checked = 0
    for inst in sorted(instances, key=lambda i: i["name"]):
        if not inst.get("cronSchedule"):
            continue  # the web app and jobs switched off; the drift check owns those
        checked += 1
        name = inst["name"]
        status = ((inst.get("latestDeployment") or {}).get("status") or "").upper()
        if status in BAD:
            what = ("its last run exited with an error" if status == "CRASHED"
                    else "its latest build or deploy failed, so it runs older code or nothing")
            problems.append(f"  {name}: {status} -- {what}")
        elif status not in OK:
            problems.append(f"  {name}: status {status or 'missing'} -- unknown counts as red")
        nxt = inst.get("nextCronRunAt")
        if not nxt:
            problems.append(f"  {name}: has a schedule but no next run -- the scheduler is not running it")
            continue
        due = datetime.fromisoformat(nxt.replace("Z", "+00:00"))
        if due + GRACE < now:
            problems.append(f"  {name}: next run was due {nxt} and has not happened -- the scheduler stopped")
    return problems, checked


def main() -> int:
    token = os.environ.get("RAILWAY_TOKEN")
    if not token:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("RAILWAY-JOBS: FAILED -- RAILWAY_TOKEN is not set in CI.")
            return 1
        print("RAILWAY-JOBS: SKIPPED -- no RAILWAY_TOKEN in the environment (local only).")
        return 0
    try:
        instances = fetch(token)
    except (urllib.error.URLError, RuntimeError, KeyError) as exc:
        print(f"RAILWAY-JOBS: FAILED -- could not read job state: {exc}")
        print("  Unreachable is not clean. Exit 1.")
        return 1
    problems, checked = judge(instances, datetime.now(timezone.utc))
    if checked == 0:
        print("RAILWAY-JOBS: FAILED -- no scheduled jobs found. That is not a pass.")
        return 1
    if problems:
        print(f"RAILWAY-JOBS: FAILED -- {len(problems)} problem(s) across {checked} scheduled jobs:")
        print("\n".join(problems))
        print("  See `railway logs -s <job>` for the run, `--build` for a failed build.")
        return 1
    print(f"RAILWAY-JOBS: PASSED -- all {checked} scheduled jobs: last run ok, next run on time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
