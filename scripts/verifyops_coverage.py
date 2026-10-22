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

prior-art-checked: DQ-117 (dq_probe_live.py) checks the fleet MEDIAN url_last_checked, so one
chapter can go unchecked for ever under a green median; DQ-70 checks extraction hashes. Neither is
per chapter or per council. Baseline ratchet pattern: scripts/page_integrity/lint_producers.py.

Usage:
    python scripts/verifyops_coverage.py              # exit 1 on any red key not in the baseline
    python scripts/verifyops_coverage.py --update     # drop cleared keys (shrink-only)
    python scripts/verifyops_coverage.py --update --allow-raise "first Railway run 2026-10-xx"
Exit 2 = could not look (no database, or migration 116 not applied). Never a pass.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
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
}


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
    return sorted(out)


def compare(baseline: list[str], now: list[str]) -> tuple[list[str], list[str]]:
    """(new reds not in the baseline, baseline keys that cleared)."""
    b, n = set(baseline), set(now)
    return sorted(n - b), sorted(b - n)


def coverage(now: list[str], served: int) -> str:
    """Metric C as a line: chapters with no red key / active chapters."""
    red_chapters = set()
    for k in now:
        council, _, rest = k.partition("|")
        chapter = rest.partition("|")[0]
        if chapter and chapter != "*":
            red_chapters.add(f"{council}|{chapter}")
    return f"C = {served - len(red_chapters)}/{served} active chapters with no red key"


def main(argv: list[str] | None = None, conn=None) -> int:
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
        cur.execute(f"SELECT count(*) FROM dcp_chapter_registry r WHERE {_ACTIVE}")
        served = cur.fetchone()[0]
        cur.close()
    except Exception as exc:  # noqa: BLE001 - a missing table means we could not look
        print(f"VERIFYOPS: could not measure ({type(exc).__name__}: {str(exc).splitlines()[0]})")
        print("  If 'dcp_monitor_' is named above, apply migrations/116_dcp_monitor_results.sql first.")
        return 2

    doc = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    base_keys = doc.get("keys") or []
    new, cleared = compare(base_keys, now)
    print(f"VERIFYOPS: {len(now)} red keys today; baseline {len(base_keys)}; "
          f"{len(new)} new; {len(cleared)} cleared")
    print(f"  {coverage(now, served)}")
    for k in new[:60]:
        print(f"  NEW RED  {k}")
    for k in cleared[:60]:
        print(f"  cleared  {k}  (run with --update to lock in)")

    if args.update:
        if new and not args.allow_raise:
            print("REFUSED: new red keys (shrink-only). Fix them, or --allow-raise 'reason'.")
            return 1
        doc["keys"] = now if args.allow_raise else sorted(set(base_keys) - set(cleared))
        if args.allow_raise:
            doc["raised"] = (doc.get("raised") or []) + [args.allow_raise]
        BASELINE.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"baseline written: {len(doc['keys'])} keys")
        return 0
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
