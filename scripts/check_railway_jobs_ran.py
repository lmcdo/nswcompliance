#!/usr/bin/env python3
# prior-art-checked: check_railway_cron_drift.py compares SCHEDULES only; run_monitors.py
# alerts from INSIDE a run, so it is silent when the run never starts. Nothing read a
# job's runs from outside Railway -- grepped scripts/, .github/workflows/ for
# latestDeployment, deploymentInstanceExecutions and CRASHED.
"""Did every scheduled Railway job run when it was due, and did its last run succeed?

WHY THIS EXISTS. dcp-extract crashed on all six runs from 2026-10-16 to 2026-10-21, and
dcp-commit the same: Dockerfile.monitors did not copy a module both import. The daily
freshness alarm passed on each of those days. The only alerting lived in
run_monitors.py, inside the job -- and a job that dies on an import, or never starts,
cannot report its own death. Railway's run history (measured 2026-10-21) also showed
maintenance-mutation crashing every month since July and dcp-monitor ending in a
failure on every run since at least 2026-09-01. Nobody had seen any of it.

This reads each job's RUN HISTORY from outside, and goes red on:
  * the last run CRASHED, or ended SKIPPED/REMOVED/STOPPED;
  * a run was due (by its cron) more than GRACE ago and none started;
  * a run or a deploy has been unfinished for more than STUCK;
  * the latest deploy FAILED (the job runs older code, or nothing);
  * anything it does not recognise. Unknown is red.

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

#: How late a run may start before it counts as missed.
GRACE = timedelta(hours=2)
#: How long a run or a deploy may sit unfinished before it counts as stuck.
STUCK = timedelta(hours=6)
#: Run outcomes. EXITED = exit 0, or the 2 run_monitors uses for "changes found";
#: CRASHED = any other exit. SKIPPED / REMOVED / STOPPED = it did not finish.
RUN_OK = {"EXITED"}
RUN_IN_PROGRESS = {"CREATED", "INITIALIZING", "RUNNING", "RESTARTING"}
#: Latest deployment (build + deploy) outcomes.
DEPLOY_OK = {"SUCCESS", "SLEEPING"}
DEPLOY_IN_PROGRESS = {"BUILDING", "DEPLOYING", "INITIALIZING", "QUEUED", "WAITING"}


def _when(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _field_matches(spec: str, value: int) -> bool:
    for part in spec.split(","):
        part, _, step_txt = part.partition("/")
        step = int(step_txt or 1)
        if part == "*":
            lo, hi = 0, 10 ** 6
        elif "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
        else:
            lo = hi = int(part)
        if lo <= value <= hi and (value - lo) % step == 0:
            return True
    return False


def last_due(cron: str, now: datetime) -> datetime | None:
    """The most recent minute at or before `now` the 5-field cron fires, within 40 days.

    Enough cron for the schedules in railway.*.toml: numbers, lists, ranges, steps, *.
    Day-of-month and day-of-week combine with OR when both are restricted, as cron does.
    """
    minute, hour, dom, month, dow = cron.split()
    t = now.replace(second=0, microsecond=0)
    for _ in range(40 * 24 * 60):
        dom_ok = _field_matches(dom, t.day)
        dow_ok = _field_matches(dow, (t.weekday() + 1) % 7)  # cron: Sunday = 0
        day_ok = (dom_ok or dow_ok) if (dom != "*" and dow != "*") else (dom_ok and dow_ok)
        if (day_ok and _field_matches(month, t.month) and _field_matches(hour, t.hour)
                and _field_matches(minute, t.minute)):
            return t
        t -= timedelta(minutes=1)
    return None


def _graphql(token: str, query: str) -> dict:
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
    return payload["data"]


def fetch(token: str) -> list[dict]:
    """Every scheduled job in production: schedule, latest deployment, last few runs."""
    jobs_query = (
        'query { project(id: "%s") { services(first: 100) { pageInfo { hasNextPage } '
        "edges { node { id name serviceInstances { edges { node { environmentId "
        "cronSchedule latestDeployment { status createdAt } } } } } } } } }" % PROJECT_ID
    )
    services = _graphql(token, jobs_query)["project"]["services"]
    if services["pageInfo"]["hasNextPage"]:
        raise RuntimeError("more than 100 services -- page through them before trusting a pass")
    out = []
    for edge in services["edges"]:
        for inst in edge["node"]["serviceInstances"]["edges"]:
            node = inst["node"]
            if node.get("environmentId") != ENVIRONMENT_ID or not node.get("cronSchedule"):
                continue
            runs_query = (
                'query { deploymentInstanceExecutions(input: { serviceId: "%s", '
                'environmentId: "%s" }, first: 3) { edges { node { createdAt status } } } }'
                % (edge["node"]["id"], ENVIRONMENT_ID)
            )
            runs = [e["node"] for e in _graphql(token, runs_query)["deploymentInstanceExecutions"]["edges"]]
            out.append({"name": edge["node"]["name"], **node, "runs": runs})
    return out


def judge(jobs: list[dict], now: datetime) -> tuple[list[str], int]:
    """(problems, number of scheduled jobs checked). Pure: no network.

    Judged on the job's RUNS, not its status alone: a status reads SUCCESS after a
    deploy that has never run, and stays SUCCESS if the scheduler stops firing
    (cross-review, 2026-10-21).
    """
    problems: list[str] = []
    checked = 0
    for job in sorted(jobs, key=lambda j: j["name"]):
        cron = job.get("cronSchedule")
        if not cron:
            continue
        checked += 1
        name = job["name"]
        runs = sorted(job.get("runs") or [], key=lambda r: r.get("createdAt") or "", reverse=True)
        last = runs[0] if runs else None

        due = last_due(cron, now - GRACE)
        if due is None:
            problems.append(f"  {name}: cannot work out when '{cron}' was last due -- unknown counts as red")
        elif last is None or _when(last["createdAt"]) < due - timedelta(minutes=1):
            seen = last["createdAt"][:16] if last else "never"
            problems.append(f"  {name}: a run was due {due:%Y-%m-%d %H:%M} UTC and none happened (last run: {seen})")

        if last is not None:
            status = (last.get("status") or "").upper()
            if status == "CRASHED":
                problems.append(f"  {name}: last run ({last['createdAt'][:16]}) exited with an error")
            elif status in RUN_IN_PROGRESS:
                if now - _when(last["createdAt"]) > STUCK:
                    problems.append(f"  {name}: a run started {last['createdAt'][:16]} is still {status} -- stuck")
            elif status not in RUN_OK:
                problems.append(f"  {name}: last run is {status or 'missing'} -- it did not finish cleanly")

        dep = job.get("latestDeployment") or {}
        dstatus = (dep.get("status") or "").upper()
        if dstatus in ("FAILED", "CRASHED"):
            problems.append(f"  {name}: latest deploy {dstatus} -- the job runs older code, or nothing")
        elif dstatus in DEPLOY_IN_PROGRESS:
            if dep.get("createdAt") and now - _when(dep["createdAt"]) > STUCK:
                problems.append(f"  {name}: a deploy started {dep['createdAt'][:16]} is still {dstatus} -- stuck")
        elif dstatus not in DEPLOY_OK:
            problems.append(f"  {name}: latest deploy status {dstatus or 'missing'} -- unknown counts as red")
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
        jobs = fetch(token)
    except (urllib.error.URLError, RuntimeError, KeyError, TypeError) as exc:
        print(f"RAILWAY-JOBS: FAILED -- could not read job state: {exc}")
        print("  Unreachable is not clean. Exit 1.")
        return 1
    problems, checked = judge(jobs, datetime.now(timezone.utc))
    if checked == 0:
        print("RAILWAY-JOBS: FAILED -- no scheduled jobs found. That is not a pass.")
        return 1
    if problems:
        print(f"RAILWAY-JOBS: FAILED -- {len(problems)} problem(s) across {checked} scheduled jobs:")
        print("\n".join(problems))
        print("  See `railway logs -s <job>` for the run, `--build` for a failed build.")
        return 1
    print(f"RAILWAY-JOBS: PASSED -- all {checked} scheduled jobs ran when due and their last run succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
