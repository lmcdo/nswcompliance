"""The one daily DCP-currency alarm (QA metric C): is every served chapter watched and checked?

Red is keyed by (council, chapter_key, reason) and compared with a recorded baseline that may only
SHRINK (v6 resolution 5). A new key is red even when an old key cleared the same day: a plain count
would let the two cancel out.

Reasons (each a stored query below; spec ~/.claude/plans/ce-verifyops-v5-SPEC-2026-10-22.md, v6):
  unwatched               a council serving rules (provisions OR setbacks) has no active, non-inert chapter
  no_url                  an active chapter has no link of its own, so its file is never checked
  no_list_page            a council with active chapters has no list page stored, so a new document
                          it publishes can never be found
  list_not_read_2d        a council with a stored list page had no list read OK in 2 days
  not_checked_8d          an active chapter with a link was not content-checked in 8 days
  last_run_unchecked      the chapter's latest result is not a check (blocked, 429, error, ...)
  missing_from_last_run   the latest full run finished without any result for the chapter
  etag_lied_30d           a spot re-download found new bytes behind an unchanged tag
  new_doc_undecided_3d    a new council document has waited > N1 = 3 days for a decision
  update_unpublished_33d  a changed chapter is not re-extracted N1 + N2 = 33 days after the change
                          (no recorded change date counts as old)
  no_run_2d               no FULL monitor run (mode daily/force) finished in 2 days; a one-council
                          run does not count (key council='*')
  run_unfinished          a FULL run started > 6 h ago never finished and no later full run has
                          (killed: Railway removes a running cron container when a new image
                          deploys -- run 1, 2026-10-22)
  deployed_not_main       the latest full run's git_sha is NULL, unknown to git, or a file the monitor
                          image COPYs (Dockerfile.monitors) differs between it and origin/main

prior-art-checked: DQ-117 (dq_probe_live.py) checks the fleet MEDIAN url_last_checked, so one
chapter can go unchecked for ever under a green median; DQ-70 checks extraction hashes. Neither is
per chapter or per council. Baseline ratchet pattern: scripts/page_integrity/lint_producers.py.

Usage:
    python scripts/verifyops_coverage.py              # exit 1 on any red key not in the baseline
    python scripts/verifyops_coverage.py --update     # drop cleared keys (shrink-only)
    python scripts/verifyops_coverage.py --update --allow-raise "first Railway run 2026-10-xx"
Exit 2 = could not look (no database, or migration 116 not applied). Never a pass.

The 2-day windows assume the DAILY cron (railway.dcp-monitor.toml `0 2 * * *`, 2026-10-23). The
baseline is written only after the first daily run (v7 step 5).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / ".claude" / "verifyops_red_baseline.json"

N1_DAYS = 3   # alert -> human decision (user, 2026-10-22)
N2_DAYS = 30  # decision -> re-extracted rules live (user, 2026-10-22)

_ACTIVE = "r.is_active AND NOT COALESCE(r.is_inert, FALSE)"
_HAS_URL = "r.council_url IS NOT NULL AND btrim(r.council_url) <> ''"
_CHECKED = ("'unchanged_etag','unchanged_hash','unchanged_head','reexport','changed','etag_lied'")

QUERIES: dict[str, str] = {
    "unwatched": """
        SELECT c, '*' FROM (
            SELECT DISTINCT source_council AS c FROM regulatory_provisions
             WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL
            UNION
            SELECT DISTINCT lga FROM dcp_setback_controls WHERE is_current AND lga IS NOT NULL) s
        WHERE NOT EXISTS (SELECT 1 FROM dcp_chapter_registry r
                          WHERE r.council = s.c AND r.is_active AND NOT COALESCE(r.is_inert, FALSE))""",
    "no_url": f"""
        SELECT r.council, r.chapter_key FROM dcp_chapter_registry r
        WHERE {_ACTIVE} AND NOT ({_HAS_URL})""",
    "no_list_page": f"""
        SELECT DISTINCT r.council, '*' FROM dcp_chapter_registry r
        WHERE {_ACTIVE}
          AND NOT EXISTS (SELECT 1 FROM dcp_chapter_registry p
                          WHERE p.council = r.council AND p.is_active AND p.council_page_url IS NOT NULL
                            AND btrim(p.council_page_url) <> '')""",
    "list_not_read_2d": f"""
        SELECT DISTINCT r.council, '*' FROM dcp_chapter_registry r
        WHERE {_ACTIVE} AND r.council_page_url IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM dcp_monitor_council_results c
                          WHERE c.council = r.council AND c.outcome = 'ok'
                            AND c.checked_at > NOW() - INTERVAL '2 days')""",
    "not_checked_8d": f"""
        SELECT r.council, r.chapter_key FROM dcp_chapter_registry r
        WHERE {_ACTIVE} AND {_HAS_URL}
          AND NOT EXISTS (SELECT 1 FROM dcp_monitor_chapter_results x
                          WHERE x.chapter_id = r.id AND x.outcome IN ({_CHECKED})
                            AND x.checked_at > NOW() - INTERVAL '8 days')""",
    "last_run_unchecked": f"""
        SELECT r.council, r.chapter_key FROM dcp_chapter_registry r
        JOIN LATERAL (SELECT outcome FROM dcp_monitor_chapter_results x
                      WHERE x.chapter_id = r.id ORDER BY x.id DESC LIMIT 1) last ON TRUE
        WHERE {_ACTIVE} AND {_HAS_URL} AND last.outcome NOT IN ({_CHECKED})""",
    "missing_from_last_run": f"""
        SELECT r.council, r.chapter_key FROM dcp_chapter_registry r
        JOIN LATERAL (SELECT id FROM dcp_monitor_runs WHERE mode IN ('daily', 'force')
                        AND finished_at IS NOT NULL ORDER BY id DESC LIMIT 1) last_run ON TRUE
        WHERE {_ACTIVE} AND {_HAS_URL}
          AND NOT EXISTS (SELECT 1 FROM dcp_monitor_chapter_results x
                          WHERE x.chapter_id = r.id AND x.run_id = last_run.id)""",
    "etag_lied_30d": f"""
        SELECT DISTINCT r.council, r.chapter_key FROM dcp_chapter_registry r
        JOIN dcp_monitor_chapter_results x ON x.chapter_id = r.id
        WHERE {_ACTIVE} AND x.outcome = 'etag_lied' AND x.checked_at > NOW() - INTERVAL '30 days'""",
    "new_doc_undecided_3d": f"""
        SELECT r.council, r.chapter_key FROM dcp_chapter_registry r
        WHERE r.registration_status = 'auto_detected'
          AND r.created_at < NOW() - INTERVAL '{N1_DAYS} days'""",
    "update_unpublished_33d": f"""
        SELECT r.council, r.chapter_key FROM dcp_chapter_registry r
        WHERE {_ACTIVE} AND r.needs_extraction
          AND COALESCE(r.url_last_changed, '-infinity'::timestamptz)
              < NOW() - INTERVAL '{N1_DAYS + N2_DAYS} days'""",
    "no_run_2d": """
        SELECT '*', '*' WHERE NOT EXISTS (SELECT 1 FROM dcp_monitor_runs
                                          WHERE mode IN ('daily', 'force')
                                            AND finished_at > NOW() - INTERVAL '2 days')""",
    "run_unfinished": """
        SELECT '*', '*' WHERE EXISTS (SELECT 1 FROM dcp_monitor_runs u
                                      WHERE u.mode IN ('daily', 'force') AND u.finished_at IS NULL
                                        AND u.started_at < NOW() - INTERVAL '6 hours'
                                        -- a later full run that finished makes it old news; else
                                        -- killed run 1 (2026-10-22) stays red for ever
                                        AND NOT EXISTS (SELECT 1 FROM dcp_monitor_runs f
                                                        WHERE f.mode IN ('daily', 'force')
                                                          AND f.finished_at IS NOT NULL
                                                          AND f.id > u.id))""",
}

DOCKERFILE = ROOT / "Dockerfile.monitors"


def image_paths(dockerfile: str) -> list[str]:
    """Source paths the monitor image COPYs (first argument of each COPY line)."""
    out: set[str] = set()
    for line in dockerfile.splitlines():
        parts = line.split()
        if not parts or parts[0] != "COPY" or any(t.startswith("--from") for t in parts):
            continue
        args = [t for t in parts[1:] if not t.startswith("--")]  # --chown/--chmod keep their source
        if len(args) >= 2:
            out.update(args[:-1])
    return sorted(out)


def deployed_not_main(sha: str | None, paths: list[str], main: str = "origin/main",
                      git=subprocess.run) -> bool:
    """True (red) unless the deployed sha is known AND no image file differs from origin/main.
    Compares the image's own files, not main's HEAD: Railway skips merges that touch none of them."""
    if not sha or not re.fullmatch(r"[0-9a-f]{40}", sha) or not paths:  # 'main' would diff main itself
        return True
    r = git(["git", "diff", "--quiet", sha, main, "--", *paths],
            cwd=ROOT, capture_output=True)
    return r.returncode != 0  # 1 = differs, 128 = sha unknown: both red


def deploy_keys(conn) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT git_sha FROM dcp_monitor_runs WHERE mode IN ('daily', 'force') "
                "ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    if row is None:
        return []  # no run at all is no_run_2d's job
    # The Dockerfile itself defines the image too (base image, build steps), not only what it copies.
    paths = [DOCKERFILE.name, *image_paths(DOCKERFILE.read_text(encoding="utf-8"))]
    return [key("*", "*", "deployed_not_main")] if deployed_not_main(row[0], paths) else []


def key(council: str, chapter: str, reason: str) -> str:
    return f"{council}|{chapter}|{reason}"


def measure(conn) -> list[str]:
    """Every red key today, sorted. Raises if a table is missing (caller exits 2)."""
    out: set[str] = set()
    cur = conn.cursor()
    for reason, sql in QUERIES.items():
        cur.execute(sql)
        out.update(key(c, ch, reason) for c, ch in cur.fetchall())
    cur.close()
    out.update(deploy_keys(conn))
    return sorted(out)


#: v7 step 5: refuse --update when more active chapters than this went unchecked in the latest full
#: run, so a half-broken run (rate limits) is never frozen as normal. Run 2: 81/547 = 14.8%.
MAX_UNCHECKED = 0.10
#: A baselined key still red after this many days alarms again (v6 resolution 4).
MAX_BASELINED_DAYS = 30
CHECKED = frozenset(x.strip("'") for x in _CHECKED.split(","))
_LAST_RUN_ROWS = """
    SELECT x.council, x.chapter_key, x.outcome FROM dcp_monitor_chapter_results x
    WHERE x.run_id = (SELECT id FROM dcp_monitor_runs WHERE mode IN ('daily','force')
                      AND finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1)"""


def unchecked_share(active: list[tuple[str, str]], rows: list[tuple[str, str, str]]) -> tuple[int, int]:
    """(active chapters the run did not content-check, active chapters). No row counts as unchecked."""
    done = {(c, k) for c, k, outcome in rows if outcome in CHECKED}
    act = set(active)
    return len(act - done), len(act)


def baselined_ages(since: dict[str, str], now: list[str], today: date) -> list[tuple[str, int]]:
    """(key, days) for every key both baselined and red today, oldest first.
    A key with no recorded date, or a date after today, counts as over the limit: it cannot
    prove it is recent (Sol, 2026-10-23: a typo'd future date would stay quiet for a year)."""
    out = []
    for k in now:
        if k in since:
            try:
                days = (today - date.fromisoformat(since[k])).days
            except (TypeError, ValueError):
                days = -1
            if days < 0:
                days = MAX_BASELINED_DAYS + 1
            out.append((k, days))
    return sorted(out, key=lambda kd: (-kd[1], kd[0]))


def compare(baseline: list[str], now: list[str]) -> tuple[list[str], list[str]]:
    """(new reds not in the baseline, baseline keys that cleared)."""
    b, n = set(baseline), set(now)
    return sorted(n - b), sorted(b - n)


def coverage(now: list[str], active: list[tuple[str, str]]) -> str:
    """Metric C as a line: active chapters with no red key of their own, of their council
    ('council|*') or of the fleet ('*|*'), out of all active chapters. Keys for rows that are not
    active chapters (new documents awaiting a decision) are red but never counted here, so C can
    neither go negative nor be lowered by them (first live run 2026-10-22 printed -24/547)."""
    chapters, councils, fleet = set(), set(), False
    for k in now:
        council, _, rest = k.partition("|")
        chapter = rest.partition("|")[0]
        if council == "*":
            fleet = True
        elif chapter == "*":
            councils.add(council)
        elif chapter:
            chapters.add((council, chapter))
    green = 0 if fleet else sum(1 for c, ch in active if c not in councils and (c, ch) not in chapters)
    return f"C = {green}/{len(active)} active chapters with no red key"


def main(argv: list[str] | None = None, conn=None, today: date | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--update", action="store_true", help="write the baseline (shrink-only)")
    ap.add_argument("--allow-raise", metavar="REASON", help="with --update: accept new keys (state why)")
    args = ap.parse_args(argv)

    if conn is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            print("VERIFYOPS: DATABASE_URL is not set - could not look (not a pass)")
            return 2
        import psycopg2
        conn = psycopg2.connect(url, options="-c statement_timeout=30000")
    try:
        now = measure(conn)
        cur = conn.cursor()
        cur.execute(f"SELECT r.council, r.chapter_key FROM dcp_chapter_registry r WHERE {_ACTIVE}")
        active = [tuple(r) for r in cur.fetchall()]
        cur.execute(_LAST_RUN_ROWS)
        run_rows = [tuple(r) for r in cur.fetchall()]
        cur.close()
    except Exception as exc:  # noqa: BLE001 - a missing table means we could not look
        print(f"VERIFYOPS: could not measure ({type(exc).__name__}: {str(exc).splitlines()[0]})")
        print("  If 'dcp_monitor_' is named above, apply migrations/116_dcp_monitor_results.sql first.")
        return 2

    today = today or date.today()
    doc = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    base_keys = doc.get("keys") or []
    since, why = doc.get("since") or {}, doc.get("why") or {}
    # A key with no recorded date is treated as baselined long ago (see baselined_ages).
    since = {k: since.get(k, "") for k in base_keys}
    new, cleared = compare(base_keys, now)
    ages = baselined_ages(since, now, today)
    expired = [k for k, d in ages if d > MAX_BASELINED_DAYS]
    print(f"VERIFYOPS: {len(now)} red keys today; baseline {len(base_keys)}; "
          f"{len(new)} new; {len(cleared)} cleared; {len(expired)} baselined > {MAX_BASELINED_DAYS} days")
    print(f"  {coverage(now, active)}")
    for k in new[:60]:
        print(f"  NEW RED  {k}")
    for k in expired[:60]:
        print(f"  EXPIRED  {k}  (baselined > {MAX_BASELINED_DAYS} days and still red: alarming again)")
    for k, d in ages[:60]:
        if d <= MAX_BASELINED_DAYS:
            print(f"  baselined but still red for {d} days  {k}")
    for k in cleared[:60]:
        print(f"  cleared  {k}  (run with --update to lock in)")

    if args.update:
        bad, total = unchecked_share(active, run_rows)
        if not total or bad / total > MAX_UNCHECKED:  # no finished run: every chapter unchecked
            print(f"REFUSED: the latest full run left {bad}/{total} active chapters unchecked "
                  f"(limit {MAX_UNCHECKED:.0%}). A half-broken run is not a baseline.")
            return 1
        if new and not args.allow_raise:
            print("REFUSED: new red keys (shrink-only). Fix them, or --allow-raise 'reason'.")
            return 1
        keys = now if args.allow_raise else sorted(set(base_keys) - set(cleared))
        stamp = today.isoformat()
        # A key keeps its first date: re-raising never resets the 30-day clock.
        doc["since"] = {k: since.get(k) or stamp for k in keys}
        doc["why"] = {k: why.get(k) or args.allow_raise for k in keys}
        doc["keys"] = keys
        if args.allow_raise:
            doc["raised"] = (doc.get("raised") or []) + [args.allow_raise]
        BASELINE.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"baseline written: {len(keys)} keys ({bad}/{total} active chapters unchecked in the latest run)")
        # Writing the baseline never makes an expired key green (Sol, 2026-10-23).
        return 1 if expired else 0
    return 1 if new or expired else 0

if __name__ == "__main__":
    sys.exit(main())
