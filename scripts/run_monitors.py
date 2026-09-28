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
import re
import subprocess
import sys
import traceback
from urllib.parse import urlparse

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
    "dcp-rules": {
        # Rule formulation: turn committed provision TEXT into structured, queryable
        # rules (v2_extracted_rules + v2_extraction_status). Runs after dcp-commit.
        #
        # This pipeline was written, works, and was never scheduled. Measured
        # 2026-09-22 across the served set: 6,117 provisions complete, 1,737
        # review_needed and 11,389 with NO VERDICT AT ALL -- 59% of what is served --
        # because nothing ever ran it. A dry run over 500 of those untouched rows:
        # 463 complete deterministically (92.6%), 31 needing the LLM, 6 needing a
        # human, 0 errors. The numbers a planner reads were instead being produced by
        # hand-run per-council scripts (enrichment/extractors/extract_*.py,
        # scripts/insert_*.py), which is why they kept going stale.
        #
        # Fill-blanks-only by default: it selects on v2_extraction_status IS NULL, so
        # repeated runs are safe and it can never overwrite a review_needed verdict a
        # human has acted on. --reprocess-all exists for a deliberate re-sweep after
        # the extractor itself changes, and is NOT used here.
        "cmd": ["python", "enrichment/rule_extraction_pipeline.py",
                "--phase", "deterministic"],
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


#: Exit code for "the monitor ran fine, and this service has no working
#: dead-man's switch". Distinct from 1 (the monitor crashed) and from 2 (the
#: monitor ran and found something) so the dashboard can tell the three apart.
#: The work still happens -- refusing to run the monitor would trade a data
#: outage for a monitoring outage -- but the run reports itself unmonitored.
EXIT_NO_DEADMAN_SWITCH = 3

#: The only hosts that issue a healthchecks.io ping URL. A value that is not on
#: one of them is not a dead-man's switch, whatever else it is.
_HC_HOSTS = ("hc-ping.com", "healthchecks.io", "www.healthchecks.io")

#: Substrings that mark a check NAME somebody typed to FILL THE VARIABLE IN
#: rather than to point at a check. Matched against the URL PATH only, never the
#: host: a real slug may legitimately contain "example", and deciding "is this
#: healthchecks.io at all" is the host's job, below.
#:
#: Measured 2026-09-28 across the Railway fleet: six services -- dcp-monitor,
#: dcp-extract, dcp-extract-all, dcp-commit, mutation-health and
#: satellite-freshness -- shared the single literal value
#: `https://hc-ping.com/placeholder-satellite`, and four more carried nothing at
#: all. So the fleet had no dead-man's switch anywhere, and every one of those
#: services looked exactly like a service that had one.
_PLACEHOLDER_MARKERS = ("placeholder", "example", "changeme", "change-me",
                        "todo", "xxx", "your-", "<", "dummy", "fixme")

#: A trailing UUID is healthchecks.io's opaque per-check form. It carries no
#: stage name, so `names_another_stage` cannot be decided for it -- see the
#: docstring's stated limit.
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def deadman_switch_problem(monitor_name: str, url: str) -> str | None:
    """Why this service has NO working dead-man's switch, or None when it has one.

    THE POINT OF THE WHOLE FILE. `ping_healthcheck` used to open with
    `if not url: return`, so a service with no `HC_PING_URL` silently had no
    dead-man's switch and was indistinguishable from a healthy one -- which is
    the in-band-alarm defect this function exists to remove. On 2026-09-16
    `dcp-watchdog` alerted `Env missing: ['HC_PING_URL']` and the only reason
    anyone knows is that it crashed for an unrelated reason on the same run.

    Four distinct ways to have no switch while looking like you do. All four were
    live on 2026-09-28; the first three were measured, the fourth is the shape
    the shared value would have taken had it named a real check:

    1. NOT SET.        `ping_healthcheck` returned early and said nothing.
    2. NOT A CHECK.    A value that does not point at healthchecks.io at all.
    3. A PLACEHOLDER.  `https://hc-ping.com/placeholder-satellite` -- a string
       typed to fill the variable in. Measured 2026-09-28: a bare slug with no
       ping key answers `400 invalid url format`, and `requests.get` does not
       raise on 400, so the ping was swallowed twice over.
    4. ANOTHER STAGE'S CHECK. One URL shared across stages means any single
       surviving stage holds the check green while the others are dead. This is
       also why a misconfigured service must NOT ping: pinging another stage's
       check actively suppresses that stage's alarm.

    STATED LIMIT, because a check that overclaims is worse than one that does
    not exist. Case 4 is decidable only for the slug form
    (`hc-ping.com/<ping-key>/<slug>`), where the last segment is human-readable.
    healthchecks.io's other form is `hc-ping.com/<uuid>`, which is opaque by
    design and carries no stage name, so two services sharing one UUID are NOT
    caught here and cannot be from inside a single process. That residual needs
    a fleet-wide check that reads every service's variable and asserts
    distinctness; it is not this function's job and this function does not
    pretend to do it.
    """
    url = (url or "").strip()
    if not url:
        return "HC_PING_URL is not set, so nothing alerts when this stage goes silent"

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in _HC_HOSTS:
        return (f"HC_PING_URL={url!r} does not point at healthchecks.io "
                f"(expected one of {', '.join(_HC_HOSTS)})")

    path = parsed.path.lower()
    for marker in _PLACEHOLDER_MARKERS:
        if marker in path:
            return (f"HC_PING_URL={url!r} is a placeholder, not a check -- pinging it "
                    f"404s, and a 404 is not an alarm")

    segments = [s for s in parsed.path.split("/") if s]
    if not segments:
        return f"HC_PING_URL={url!r} names no check"

    slug = segments[-1]
    if _UUID_RE.match(slug):
        return None  # opaque form: nothing more is decidable here. See the limit above.

    # Slug form. It must name THIS stage, or this service is holding another
    # stage's check green.
    #
    # LONGEST MATCH WINS, and that is not fussiness. Substring containment alone
    # passes `dcp-extract` pointed at the slug `dcp-extract-all`, because one
    # stage's name is a prefix of the other's -- found by forcing this function to
    # fail, 2026-09-28, which is the only way a guard is ever known to work
    # (memory/feedback-detect-a-guard-by-forcing-its-failure.md). Resolving the
    # slug to the LONGEST stage name it contains makes the two distinguishable,
    # and still accepts a decorated slug like `plotdetect-dcp-monitor`.
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    norm_slug = _norm(slug)
    named = sorted((n for n in MONITORS if _norm(n) and _norm(n) in norm_slug),
                   key=lambda n: len(_norm(n)), reverse=True)
    if not named:
        return (f"HC_PING_URL slug {slug!r} names no known stage, so nobody can tell "
                f"which stage's silence it would report")
    if named[0] != monitor_name:
        return (f"HC_PING_URL slug {slug!r} names stage {named[0]!r}, not this one "
                f"({monitor_name!r}), so this service is pinging another stage's "
                f"check and holding it green")
    return None


def ping_healthcheck(url: str, failed: bool = False) -> bool:
    """Ping healthchecks.io. True only when the ping is KNOWN to have landed.

    Two silences removed, both of which made a dead ping read as a live one:

    - `requests.get` does not raise on 4xx/5xx, and this function used to ignore
      the response entirely. So a deleted, renamed or mistyped check answered 404
      and the run reported nothing. A ping that does not land is not a ping.
    - A transport exception printed to stderr, where `run_monitors` ships only the
      last 2,000 bytes of a failing child's stderr and nothing at all from a
      succeeding one. The caller now gets a return value it has to act on.
    """
    target = f"{url}/fail" if failed else url
    try:
        resp = requests.get(target, timeout=10)
    except Exception as e:
        print(f"Healthcheck ping FAILED (not delivered): {e}", file=sys.stderr)
        return False
    if resp.status_code >= 400:
        print(f"Healthcheck ping REJECTED: HTTP {resp.status_code} from "
              f"healthchecks.io -- this URL is not a usable check, so nothing is "
              f"watching this stage.", file=sys.stderr)
        return False
    # A 2xx IS NOT ENOUGH, and assuming it was is the hole this function had when
    # first written. MEASURED against the live service 2026-09-28:
    #
    #   GET https://hc-ping.com/<a-uuid-that-is-not-a-check>   -> 200  "OK (not found)"
    #   GET https://hc-ping.com/<the-same>/fail                -> 200  "OK (not found)"
    #   GET https://hc-ping.com/not-a-real-slug                -> 400  "invalid url format"
    #
    # So healthchecks.io answers 200 for a well-formed ping to a check that does not
    # exist, and says so only in the BODY. A deleted, renamed or mistyped UUID would
    # therefore have passed the status check and been recorded as a live heartbeat --
    # the same "looks watched, isn't" state this whole guard exists to remove, just
    # one layer deeper. Found by the real-layer test, not by reading the docs.
    if "not found" in (resp.text or "").lower():
        print(f"Healthcheck ping NOT RECORDED: healthchecks.io answered "
              f"{resp.status_code} {resp.text.strip()[:60]!r}. The check this URL "
              f"names does not exist, so this run left no heartbeat and this "
              f"stage's silence is unreadable.", file=sys.stderr)
        return False
    return True


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

    # LOUD AT STARTUP, not silent forever. Rule 4 of the June design -- "silence is
    # an alarm" -- is the only one of the four that was never wired, and this is the
    # line where it was lost: ping_healthcheck opened with `if not url: return`.
    #
    # The alert goes out BEFORE the monitor runs, because a stage that later dies
    # mid-run may never reach the end of this function, and the one thing a reader
    # needs to know is that this run is not being watched.
    switch_problem = deadman_switch_problem(monitor_name, hc_url)
    if switch_problem:
        print(f"[run_monitors] NO DEAD-MAN'S SWITCH on {monitor_name}: "
              f"{switch_problem}", file=sys.stderr)
        send_telegram(
            f"🚨 {monitor_name} has NO dead-man's switch\n{switch_problem}\n\n"
            f"This stage can stop running and nothing will alert. Silence from it "
            f"means nothing until this is fixed."
        )

    print(f"[run_monitors] Starting: {monitor_name}")
    result = subprocess.run(config["cmd"], env=os.environ.copy(), capture_output=True, text=True)
    exit_code = result.returncode
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Exit code 0 = healthy, 2 = degraded (still a "successful run" for heartbeat)
    failed = exit_code not in (0, 2)
    # DO NOT ping a URL that is not this stage's own check. A shared or wrong URL
    # pinged from here holds ANOTHER stage's alarm green, so a bad value is worse
    # than no value: it silences a switch that was working.
    if switch_problem:
        print(f"[run_monitors] not pinging {monitor_name}'s healthcheck: "
              f"{switch_problem}", file=sys.stderr)
    elif not ping_healthcheck(hc_url, failed=failed):
        switch_problem = ("the healthcheck ping did not land, so this run left no "
                          "heartbeat and this stage's silence is unreadable")
        send_telegram(f"🚨 {monitor_name}: {switch_problem}")

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
    #
    # A broken dead-man's switch is reported on its own code, and only when the
    # monitor itself is fine: a crash is the more urgent fact and must not be
    # relabelled. Telegram is in-band -- same container, same env, same network as
    # the job, and send_telegram swallows its own failures twice over -- so the
    # exit code is the carrier that does not depend on the alert channel working.
    resolved = 0 if exit_code == 2 else exit_code
    if resolved == 0 and switch_problem:
        print(f"[run_monitors] exiting {EXIT_NO_DEADMAN_SWITCH}: {monitor_name} ran "
              f"fine but is not being watched", file=sys.stderr)
        return EXIT_NO_DEADMAN_SWITCH
    return resolved


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        monitor = os.environ.get("MONITOR_NAME", "unknown")
        send_telegram(f"🚨 run_monitors CRASH ({monitor}):\n{tb[-3000:]}")
        sys.exit(1)
