#!/usr/bin/env python3
# prior-art-checked: no existing comparison of railway.*.toml against the live
# Railway schedule -- grepped scripts/, .github/workflows/, services/ for
# cronSchedule and railway api. run_monitors.py names the jobs but never reads
# their schedules; the toml files declare them but nothing checks they apply.
"""Do the cron schedules in railway.*.toml match what Railway actually runs?

WHY THIS EXISTS. On 2026-09-10, six of eight services ran a different schedule
from their own config file, and nobody had noticed:

    dcp-extract          file: daily        live: Mondays only
    dcp-extract-all      file: quarterly    live: every Monday
    property-alerts      file: Sundays      live: no cron at all
    brief-drift-check    file: Mondays      live: no cron at all
    maintenance-security file: Mondays      live: no cron at all
    maintenance-mutation file: monthly      live: no cron at all

The consequence was not theoretical. Extraction had been demoted to weekly, so
council chapters flagged as changed sat unprocessed for up to seven days while
the watchdog reported them as "stuck >48h" every week -- an alarm that could
not be satisfied, on a pipeline everyone believed was nightly.

Railway applies config-as-code ONLY where no dashboard value is set. A value
typed into the dashboard silently wins forever after, and the file becomes a
comment that reads like configuration. Editing the file is therefore not
sufficient, and there is no signal when the two diverge. This is that signal.

Needs RAILWAY_TOKEN, and it must be an ACCOUNT token (Railway account settings
-> Tokens), sent as "Authorization: Bearer". A project-scoped token authenticates
but is Not Authorized for the project(id:) query, which returns HTTP 200 with an
errors array rather than a 401 -- so the wrong token type looks like a broken
query, not a permission problem.

In CI a missing token is a FAILURE, not a skip: a gate
that quietly passes when its credential is absent is how .qa reports stopped
being enforced for ten weeks. Locally, no token skips loudly with exit 0.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://backboard.railway.com/graphql/v2"
PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "bbf07e70-b9ce-4776-9523-090be5b84753")
#: The production environment. serviceInstances exist per environment, so an
#: unfiltered query would compare a staging schedule against a production file.
ENVIRONMENT_ID = os.environ.get(
    "RAILWAY_ENVIRONMENT_ID", "8bde9fcd-b5f0-4cd8-8ca2-e405995f112f")

#: config file -> Railway service name.
#: Derived from the filename everywhere except the two cases where they differ,
#: which are listed explicitly rather than guessed. railway.toml is the web app
#: and railway.monitors.toml is SHARED by two services and declares no cron of
#: its own, so neither can be checked -- recorded here, not silently dropped.
FILE_TO_SERVICE = {
    "railway.alerts.toml": "property-alerts",
    "railway.brief-drift.toml": "brief-drift-check",
}
UNCHECKABLE = {
    "railway.toml": "the nswcompliance web app, not a cron service",
    "railway.monitors.toml": (
        "shared by monitor-satellite and monitor-watchdog and declares no "
        "cronSchedule, so the file cannot express either service's schedule"
    ),
}

#: Services whose file declares a cron that is deliberately NOT applied, with
#: the reason. An exception list is how a ratchet rots, so this one runs BOTH
#: ways, exactly like the DQ ledger: an entry whose service HAS a cron is a
#: failure too, because that means the job was switched on and nobody removed
#: the exception -- or the exception was always wrong. It can never sit here
#: quietly agreeing with whatever happens to be true.
INTENTIONALLY_DISABLED = {
    "property-alerts": (
        "Emails real subscribers about development applications near their "
        "property, and has never run. Switching it on cold could send a backlog "
        "of stale alerts in one go. Held 2026-09-10 pending a "
        "run_alerts_dispatch.py --dry-run showing what would actually go out."
    ),
}

_CRON_RE = re.compile(r'^\s*cronSchedule\s*=\s*"([^"]*)"', re.MULTILINE)


def declared_schedules() -> tuple[dict[str, str], list[str]]:
    """Every railway.*.toml that declares a cron, mapped to its service name."""
    declared: dict[str, str] = {}
    skipped: list[str] = []
    for path in sorted(ROOT.glob("railway*.toml")):
        name = path.name
        if name in UNCHECKABLE:
            skipped.append(f"{name} ({UNCHECKABLE[name]})")
            continue
        m = _CRON_RE.search(path.read_text(encoding="utf-8"))
        if not m:
            skipped.append(f"{name} (declares no cronSchedule)")
            continue
        service = FILE_TO_SERVICE.get(name) or name[len("railway."):-len(".toml")]
        declared[service] = m.group(1).strip()
    return declared, skipped


def live_schedules(token: str) -> dict[str, str | None]:
    query = (
        "query { project(id: \"%s\") { services { edges { node { name "
        "serviceInstances { edges { node { cronSchedule environmentId } } } "
        "} } } } }" % PROJECT_ID
    )
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # REQUIRED. Without an explicit User-Agent, urllib sends
            # "Python-urllib/3.x" and Cloudflare rejects the request with a bare
            # HTTP 403 "error code: 1010" before it ever reaches Railway. That
            # looks exactly like a bad token and cost real time to tell apart,
            # so it is pinned here with the reason attached.
            "User-Agent": "compliance-engine-cron-drift-check/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        payload = json.loads(resp.read())
    if payload.get("errors"):
        raise RuntimeError(f"Railway API returned errors: {payload['errors']}")
    out: dict[str, str | None] = {}
    for edge in payload["data"]["project"]["services"]["edges"]:
        node = edge["node"]
        for inst in node["serviceInstances"]["edges"]:
            if inst["node"].get("environmentId") != ENVIRONMENT_ID:
                continue
            out[node["name"]] = inst["node"].get("cronSchedule")
    return out


def compare(declared: dict[str, str], live: dict[str, str | None]) -> list[str]:
    """Every disagreement, as a human-readable line. Empty means clean."""
    problems = []
    for service, want in sorted(declared.items()):
        if service in INTENTIONALLY_DISABLED:
            got = live.get(service)
            if got is not None:
                problems.append(
                    f"  {service}: listed as intentionally disabled, but Railway "
                    f"now runs '{got}'. Either it was switched on and the "
                    f"exception was left behind, or the exception was never "
                    f"true. Remove it from INTENTIONALLY_DISABLED."
                )
            continue
        if service not in live:
            problems.append(
                f"  {service}: declares '{want}' but NO SUCH SERVICE exists in "
                f"the production environment -- renamed, deleted, or the file "
                f"maps to the wrong name."
            )
            continue
        got = live[service]
        if got is None:
            problems.append(
                f"  {service}: file says '{want}', Railway has NO CRON AT ALL. "
                f"This job never runs."
            )
        elif got.split() != want.split():
            problems.append(f"  {service}: file says '{want}', Railway runs '{got}'.")
    return problems


def main() -> int:
    token = os.environ.get("RAILWAY_TOKEN")
    if not token:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("RAILWAY-CRON: FAILED -- RAILWAY_TOKEN is not set in CI.")
            print("  A drift check that passes without its credential is not a check.")
            return 1
        print("RAILWAY-CRON: SKIPPED -- no RAILWAY_TOKEN in the environment.")
        print("  This is a local skip. In CI a missing token FAILS.")
        return 0

    declared, skipped = declared_schedules()
    try:
        live = live_schedules(token)
    except (urllib.error.URLError, RuntimeError, KeyError) as exc:
        print(f"RAILWAY-CRON: FAILED -- could not read the live schedules: {exc}")
        print("  Unreachable is not clean. Exit 1.")
        return 1

    problems = compare(declared, live)
    for line in skipped:
        print(f"  not checked: {line}")
    for service, reason in sorted(INTENTIONALLY_DISABLED.items()):
        print(f"  intentionally OFF: {service} -- {reason}")
    if problems:
        print(f"\nRAILWAY-CRON: FAILED -- {len(problems)} service(s) do not run what "
              f"their config file declares:")
        print("\n".join(problems))
        print("\n  Railway applies config-as-code only where no dashboard value is")
        print("  set. Fix the live value (Settings > Cron Schedule, or the")
        print("  serviceInstanceUpdate mutation) or correct the file -- but the")
        print("  file alone will not change what runs.")
        return 1
    checked = len(declared) - len(INTENTIONALLY_DISABLED)
    print()
    print(f"RAILWAY-CRON: PASSED -- {checked} service(s) match their config "
          f"file, {len(INTENTIONALLY_DISABLED)} intentionally off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
