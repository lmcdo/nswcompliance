#!/usr/bin/env python3
# prior-art-checked: four sweeps 2026-09-27 on origin/main 3257c3c7. (1) DB: the
# rows are found by DQ-116's own probe, not a new query. (2) Frontend: nothing in
# frontend-nextjs reads or writes v2_is_actionable; it is a serve-set filter.
# (3) Python: scripts/repair_*.py is the established shape for a targeted
# production write (explicit rows, verbatim evidence, dry-run default, CSV
# backup, guarded UPDATE) and this follows repair_dq62_commencement_dates.py;
# no existing repair touches v2_is_actionable. (4) Plans + memory: DQ-116 is the
# only row covering repealed sections.
"""Stop serving a section the council has repealed.

WHY THIS EXISTS, AND WHY IT IS NOT "DELETING THE ROW TO CLEAR A CHECK"
---------------------------------------------------------------------
DQ-116's own passes_when warned that reaching zero by hand would be the wrong
fix. That warning was written when the remedy was assumed to be a chapter
re-read. It is not, and the source settles it: the council's CURRENT chapter --
the R2 object dcp_chapter_registry.r2_current_path names,
source-pdfs/dcps/woollahra/v1.4-2026-09-15/chapter-b3-general-development.pdf,
2,973,719 bytes, 101 pages -- itself prints "B3.3 Floorplate (Repealed)" on page
21 and lists it as repealed in its contents. So a re-read reproduces the row
exactly. The row is FAITHFUL; the defect is that a repealed section is carried
in the SERVED set as an actionable control.

The user's decision, 2026-09-27, asked directly: should a "this control has been
removed" notice appear in a property report? Answer: no. So the fix is to stop
serving it, not to alter what it says. Nothing is deleted and no text is edited
-- the row keeps its words, its page and its history, and stops being served.

WHY v2_is_actionable AND NOT is_current
---------------------------------------
`is_current = FALSE` means "superseded by a newer version of this row", and
would be a lie: there is no newer version, and row 121802 already occupies that
relationship correctly. `v2_is_actionable = FALSE` means "not an actionable
control", which is exactly true of a repeal notice. The served set is
`is_current AND v2_is_actionable`, so this removes it from serving and from
DQ-116 without misstating its version history.

THIS IS A CONTAINMENT, NOT THE DURABLE FIX
------------------------------------------
The durable fix is for `detect_repealed_section` to gate at the point rows are
written, so the next extraction of any chapter does not put one back. Until that
lands, DQ-116 keeps watching: it reads the tagger's own verdict over the served
set, so a new one appears the moment it is served.

Usage::

    python scripts/repair_dq116_repealed_sections_served.py            # dry run
    python scripts/repair_dq116_repealed_sections_served.py --apply
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

BACKUP_DIR = ROOT / "data" / "db_rollback_backups"


def find_rows(cur):
    """The rows DQ-116 flags -- asked of the same detector, never a second copy.

    A parallel query here could drift from the probe, and then the repair and the
    check would disagree about what the defect is.
    """
    from dcp_extract_changed import detect_repealed_section

    cur.execute(
        """SELECT id, source_council, ref_number, section_header, provision_text,
                  pdf_page, v2_is_actionable
             FROM regulatory_provisions
            WHERE is_current AND v2_is_actionable
              AND (provision_text ILIKE %s OR provision_text ILIKE %s
                   OR provision_text ILIKE %s OR section_header ILIKE %s)""",
        ("%(repealed)%", "%(deleted)%", "%repealed%", "%(repealed)%"),
    )
    hits = []
    for rid, council, ref, header, text, page, actionable in cur.fetchall():
        why = detect_repealed_section(header or "", text or "")
        if why:
            hits.append({
                "id": rid,
                "source_council": council or "nsw_statewide",
                "ref_number": ref,
                "pdf_page": page,
                "v2_is_actionable_before": actionable,
                "evidence": why,
            })
    return sorted(hits, key=lambda h: h["id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="Write. Default: dry run.")
    args = ap.parse_args()

    import dq_db

    if not args.apply:
        with dq_db.session() as conn, conn.cursor() as cur:
            rows = find_rows(cur)
        _report(rows)
        print("\nDRY RUN - nothing written. --apply would set "
              "v2_is_actionable = FALSE on %d row(s)." % len(rows))
        return 0

    # The write path needs its own connection: dq_db is read-only by design.
    import os

    from dotenv import load_dotenv
    load_dotenv(dq_db.main_checkout() / ".env")
    import psycopg2

    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("No DATABASE_URL.", file=sys.stderr)
        return 2
    conn = psycopg2.connect(url, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30s'")
        rows = find_rows(cur)
        _report(rows)
        if not rows:
            print("\nNothing to do.")
            return 0

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        backup = BACKUP_DIR / f"regulatory_provisions_pre_dq116_repeal_{stamp}.csv"
        with open(backup, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nbackup written: {backup.relative_to(ROOT)}")

        ids = [r["id"] for r in rows]
        # Guarded: the id list is explicit and the WHERE repeats the serve-set
        # condition, so a row that stopped being served between the read and the
        # write is not touched.
        cur.execute(
            "UPDATE regulatory_provisions SET v2_is_actionable = FALSE "
            "WHERE id = ANY(%s) AND is_current AND v2_is_actionable",
            (ids,),
        )
        changed = cur.rowcount
        conn.commit()
        print(f"updated {changed} row(s) (expected {len(ids)})")

        cur.execute(
            "SELECT count(*) FROM regulatory_provisions "
            "WHERE id = ANY(%s) AND is_current AND v2_is_actionable", (ids,))
        left = cur.fetchone()[0]
        print("still served after the write:", left, "(must be 0)")
        return 0 if left == 0 and changed == len(ids) else 1
    finally:
        conn.close()


def _report(rows) -> None:
    print("Rows DQ-116 flags as a repealed section in the served set: %d" % len(rows))
    for r in rows:
        print("")
        print("  id=%-8s %-16s page=%s" % (r["id"], r["source_council"], r["pdf_page"]))
        print("    ref      : %s" % (r["ref_number"] or "")[:90])
        print("    evidence : %s" % r["evidence"][:160])


if __name__ == "__main__":
    raise SystemExit(main())
