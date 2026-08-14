#!/usr/bin/env python3
# prior-art-checked: reuse not viable because nothing in this repo asks how
# long ago a workflow last succeeded. main-red-alarm asks a different question
# — does main's CURRENT HEAD have a successful gates run — and deliberately
# refuses to reason about elapsed time, because for CODE a green run on the
# current HEAD stays valid however long ago it ran. scripts/check_pr_gates.py
# asks whether a run exists for a specific PR head sha. Neither can answer
# "has anybody looked at the data lately", which only makes sense for a check
# whose subject changes without a commit. Sweeps 2026-08-14 on origin/main.
"""Fail when nothing has checked the live data recently.

`data-watch` runs the database checks on a schedule, which is the only trigger
that can see drift — a council amendment or a hand-edited row moves the data
without moving HEAD. But a scheduled workflow is exactly the kind of thing that
stops silently: this repo has already had a watchdog fail 12 runs out of 12 at
`gh: command not found`, and its self-hosted runners do not survive a reboot.

So the freshness question cannot be answered by anything on a schedule — if the
scheduler is dead, so is the thing that would tell you. It is answered HERE, on
a pull-request trigger, because a PR is the one event guaranteed to run.

WHAT IT WILL AND WILL NOT FAIL FOR. A definite, measured staleness fails: the
data-watch last succeeded more than --max-age-hours ago. Everything uncertain
warns and passes — no token (a fork PR cannot see one), no runs yet (the
workflow was just added), an unreachable API. Blocking every merge because
api.github.com hiccuped is the "red for reasons unrelated to the defect" trap
that gets a check deleted within a week, and a deleted check protects nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

WORKFLOW = "data-watch.yml"
DEFAULT_MAX_AGE_HOURS = 48


#: Returned instead of None when the API answers 404. "The workflow is not
#: there" and "I could not ask" are different facts and must not collapse into
#: one message — a renamed or deleted data-watch would otherwise report itself
#: forever as a network problem, which is the silent-pass shape this whole
#: effort exists to remove.
NOT_FOUND = object()


def _api(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "check-data-watch-freshness",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return NOT_FOUND if e.code == 404 else None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    ap.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
    if not token or not args.repo:
        print("data-watch freshness: SKIPPED — no GITHUB_TOKEN/repo in this "
              "environment (a fork PR cannot see one). Not a pass.")
        return 0

    url = (f"https://api.github.com/repos/{args.repo}/actions/workflows/"
           f"{WORKFLOW}/runs?status=success&per_page=1")
    data = _api(url, token)
    if data is NOT_FOUND:
        print(f"data-watch freshness: SKIPPED — GitHub has no workflow named "
              f"{WORKFLOW} on the default branch.")
        print("  Expected on the pull request that ADDS it, and only then. If "
              "you see this after it has merged, the file was renamed or "
              "deleted and nothing is watching the data.")
        return 0
    if data is None:
        print("data-watch freshness: SKIPPED — the Actions API could not be "
              "reached. Not a pass; re-run to get a real answer.")
        return 0

    runs = data.get("workflow_runs") or []
    if not runs:
        print(f"data-watch freshness: SKIPPED — {WORKFLOW} has no successful "
              f"run yet. Expected right after it is added; if this persists, "
              f"the schedule is not firing.")
        return 0

    stamp = runs[0].get("updated_at") or runs[0].get("created_at")
    try:
        when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        print(f"data-watch freshness: SKIPPED — unparseable timestamp {stamp!r}.")
        return 0

    hours = (datetime.now(timezone.utc) - when).total_seconds() / 3600
    print(f"data-watch last succeeded {hours:.1f}h ago "
          f"(limit {args.max_age_hours:.0f}h) — {runs[0].get('html_url', '')}")

    if hours > args.max_age_hours:
        print()
        print("FAILED: nothing has checked the live data within the limit.")
        print("  The database is read by no other trigger. Between pull")
        print("  requests, a council amendment or a bad extraction write is")
        print("  currently unobserved.")
        print("  Clear it by running the workflow — Actions > data-watch >")
        print("  'Run workflow' — and fix whatever it reports. If it will not")
        print("  start at all, the scheduler or the runners are down, which is")
        print("  the thing this check exists to make visible.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
