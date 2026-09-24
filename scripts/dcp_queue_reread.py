#!/usr/bin/env python3
# prior-art-checked: reuse not viable because the only writers of
# needs_extraction are r2_monitor / manual_verify (set it when a PDF's bytes
# CHANGE) and dcp_extract_changed (clears it after a read). Nothing queues an
# UNCHANGED chapter for a re-read on purpose, which is what DQ-111 needs: the
# PDF is the same, the reader that read it was wrong.
"""Queue named DCP chapters for a re-read by the Railway dcp-extract job.

Sets needs_extraction = TRUE on the named active chapters and nothing else.
Railway's daily dcp-extract (03:00 UTC) re-reads them with the fixed reader in
review mode, and the fidelity gate grades every rule as it is queued --
including its clause number (DQ-111). Nothing reaches served data until a rule
is approved (scripts/dcp_approve_graded.py, which refuses any rule whose clause
number is not proven) and committed (dcp-commit, 09:00 UTC).

Dry run by default. Re-reading is run on Railway, never from this machine
(memory: feedback-dry-run-does-not-cover-the-review-queue).

    python scripts/dcp_queue_reread.py --chapter ashfield/chapter-a-miscellaneous
    python scripts/dcp_queue_reread.py --dq111-top 11 --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
ROOT = Path(__file__).resolve().parent.parent

#: The 11 chapters holding 83% of the DQ-111 rows that code cannot correct,
#: measured 2026-09-24 (plan ce-citation-integrity-PROMPT-2026-09-24.md §11).
DQ111_TOP = [
    "northern_beaches/warringah-dcp-2011-full",
    "leichhardt/part-g-s1-site-specific",
    "ashfield/chapter-a-miscellaneous",
    "campbelltown/campbelltown-dcp-part3-low-medium",
    "leichhardt/part-c-s1-general",
    "ashfield/chapter-c-sustainability",
    "ashfield/chapter-f-dev-category",
    "leichhardt/part-c-s2-urban-character",
    "ashfield/chapter-e1-heritage",
    "leichhardt/tree-management-technical-manual",
    "ashfield/chapter-b-public-domain",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--chapter", action="append", default=[], metavar="COUNCIL/CHAPTER_KEY")
    ap.add_argument("--dq111-top", type=int, default=0, help="Queue the first N of DQ111_TOP.")
    ap.add_argument("--apply", action="store_true", help="Write. Without it nothing changes.")
    args = ap.parse_args()
    wanted = list(dict.fromkeys(args.chapter + DQ111_TOP[: args.dq111_top]))
    pairs = []
    for w in wanted:
        council, _, chapter = w.partition("/")
        if not council or not chapter:
            print(f"ERROR: {w!r} is not COUNCIL/CHAPTER_KEY")
            return 2
        pairs.append((council, chapter))
    if not pairs:
        print("Nothing named. Use --chapter or --dq111-top.")
        return 2

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        found = []
        for council, chapter in pairs:
            cur.execute("SELECT id, needs_extraction FROM dcp_chapter_registry "
                        "WHERE council = %s AND chapter_key = %s AND is_active", (council, chapter))
            rows = cur.fetchall()
            if len(rows) != 1:
                print(f"ERROR: {council}/{chapter} matches {len(rows)} active registry rows; "
                      f"nothing written.")
                return 2
            found.append((council, chapter, rows[0][0], rows[0][1]))
        for council, chapter, rid, flagged in found:
            print(f"  {'already queued' if flagged else 'will queue':>15}  {council}/{chapter}  (id {rid})")
        todo = [f for f in found if not f[3]]
        if not args.apply:
            print(f"\nDRY RUN -- {len(todo)} chapter(s) would be queued. Re-run with --apply.")
            return 0
        ids = [f[2] for f in todo]
        if ids:
            cur.execute("UPDATE dcp_chapter_registry SET needs_extraction = TRUE "
                        "WHERE id = ANY(%s) AND is_active AND NOT needs_extraction", (ids,))
            if cur.rowcount != len(ids):
                conn.rollback()
                print(f"FATAL: expected {len(ids)} rows, would have written {cur.rowcount}; rolled back.")
                return 2
            conn.commit()
        print(f"\nQUEUED {len(ids)} chapter(s). Railway dcp-extract re-reads them at 03:00 UTC.")
        print("UNDO:  UPDATE dcp_chapter_registry SET needs_extraction = FALSE WHERE id = ANY("
              f"ARRAY{ids});")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
