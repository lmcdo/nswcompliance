#!/usr/bin/env python3
# prior-art-checked: needs_review is the existing "not served" switch -- fetch_dcp_setbacks and
# granny_flat exclude it, and /internal/setback-review is where a person fixes and releases a row.
# update_needs_review_controls.py is a one-off with its rows hardcoded; nothing selects rows by
# "a number that cannot be located on its page", so this adds only that selection.
"""Hold served setback numbers that cannot be located on the council's page.

A served number must show where it is printed: its proven clause, or its page (OC-8, reworded
2026-09-26). On 2026-09-26, 13 rows had neither: their stored text is a summary rather than the
council's sentence, several point at the wrong document (Georges River LEP clauses filed under a
DCP PDF; Bayside Part 4B rules filed under Part 3), and their number appears on many pages, so no
page could be chosen without guessing (measure_control_page_corrections.py --missing-page-only).

This sets needs_review, which removes them from every report until a person re-reads each one
from the right document in /internal/setback-review. It never changes a value or a citation.

SAFETY: dry run by default; the rows' full pre-state is backed up first; each UPDATE repeats the
selection (so a row fixed in the meantime is skipped); the count after is checked.

  python scripts/hold_unlocatable_controls.py
  python scripts/hold_unlocatable_controls.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REASON = ("2026-09-26: no page and no proven clause; stored text is a summary, not the council's "
          "sentence. Re-read from the right document and set pdf_page before releasing.")

#: Served, carries a number, and nothing shows where it is printed. External (state-law) rows
#: are cited by their clause and are never selected.
SELECTION = """
    is_current AND (needs_review IS NULL OR needs_review = FALSE)
    AND (value_min IS NOT NULL OR value_max IS NOT NULL)
    AND pdf_page IS NULL
    AND coalesce(to_jsonb(dcp_setback_controls) ->> 'citation_status', '')
        NOT IN ('proven', 'imprecise', 'external')
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    args = ap.parse_args()

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        cur.execute(f"SELECT id, lga, control_type, value_min, value_max, unit, section_ref, "
                    f"source_chapter_key, needs_review, review_reason FROM dcp_setback_controls "
                    f"WHERE {SELECTION} ORDER BY lga, id")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        print(f"served numbers with no page and no proven clause: {len(rows)}")
        for r in rows:
            print(f"  id={r['id']:<6} {r['lga']:<22} {r['control_type']:<20} "
                  f"{r['value_min'] or r['value_max']}{r['unit'] or ''}  ref={r['section_ref']}")
        if not rows:
            print("nothing to hold.")
            return 0
        if not args.apply:
            print("DRY RUN -- nothing written. Re-run with --apply.")
            return 0

        backup = ROOT / "data" / "db_rollback_backups" / (
            f"dcp_setback_controls_pre_hold_unlocatable_{datetime.now():%Y-%m-%d_%H%M}.json")
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(json.dumps({
            "taken_at": datetime.now(timezone.utc).isoformat(),
            "undo": "UPDATE dcp_setback_controls SET needs_review = <needs_review>, "
                    "review_reason = <review_reason> WHERE id = <id>",
            "rows": rows}, indent=2, default=str), encoding="utf-8")
        print(f"backup written: {backup.relative_to(ROOT)}")

        cur.execute(f"UPDATE dcp_setback_controls SET needs_review = TRUE, review_reason = %s "
                    f"WHERE id = ANY(%s) AND {SELECTION}", (REASON, [r["id"] for r in rows]))
        held = cur.rowcount
        conn.commit()
        cur.execute(f"SELECT count(*) FROM dcp_setback_controls WHERE {SELECTION}")
        left = cur.fetchone()[0]
        print(f"held {held} of {len(rows)}; served numbers still unlocatable: {left}")
        return 0 if left == 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
