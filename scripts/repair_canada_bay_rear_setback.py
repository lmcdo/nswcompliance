#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no committed script repairs this
# row, and scripts/repair_camden_front_setbacks.py is a one-shot bound to its own
# two Camden ids. The SAFETY shape (dry-run default, backup table asserting every
# planned id, per-row guard on values read at plan time, printed rollback) is
# copied from that script; the ruling and the rule-2b quote replacement are new.
"""Repair canada_bay control 701: a SIDE setback served as the REAR setback.

WHAT AND WHY
------------
Control 701 (canada_bay / dwelling_house / rear_setback) serves 1.5 m. Its own
400-char-truncated `source_text` is the C6 SIDE-boundary table — "The second
storey of all dwellings are to be set back a minimum of 1500mm from side boun…"
— so the stored number is the second-storey SIDE setback, filed as the rear.
Canada Bay's true general rear setback is stored NOWHERE, and the served value
understates it 4x, in the direction that matters.

Read directly from `data/dcps/canada-bay-part-e-single-dwellings.pdf`, printed
page E-15 (PDF page 15; the document states "Version: 3, Version Date:
26/06/2025"), heading "Rear setbacks - single street frontage":

    C9. All development (not including an outbuilding or secondary dwelling)
    is to have a minimum rear setback of 6.0 metres measured from the outside
    face of the development (wall, balcony, deck, post, roof etc). Refer to
    Canada Bay LEP definition of 'building line or setback'.

Evidence level STRONG: the clause states the control, the value and its
qualification in one place, read from the source PDF for this repair.

RULE 2b (docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md)
----------------------------------------------------------------------
Camden 690 was corrected value-only and the standing gate immediately failed it,
because `source_text` still held the quote supporting the OLD value. So here the
C9 quote is written in the SAME statement as the value: a correction must carry
the evidence for the new value, not just the number.

WHAT THIS DOES NOT DO
---------------------
C10 (upper-floor living room rear 9.0 m), C11 (secondary dwelling rear 3.0 m)
and C12 (corner-lot rear 1.5 m for the dwelling oriented to the secondary
frontage) are still absent from `dcp_setback_controls`; this repairs the one
authorised row and records the gaps in `condition`. Only id 701 is touched.

SAFETY
------
Dry-run by default. Backup table first, asserting the planned id is present.
UPDATE guarded on id + control_type + value_min + is_current + the exact
source_text read at plan time (and `condition IS NULL`, its observed pre-state —
IS NULL, never `= NULL`), so a concurrent edit skips rather than clobbers.
Rollback SQL printed. Idempotent: re-running after a successful apply plans zero
writes.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONTROL_ID = 701
EXPECT_VALUE = "1.5"
EXPECT_QUOTE_MARKER = "1500mm from side boun"   # the misfiled SIDE table
EXPECT_QUOTE_LEN = 400                          # truncated at the extractor cap

SOURCE = ("data/dcps/canada-bay-part-e-single-dwellings.pdf C9, printed page "
          "E-15 (PDF page 15; doc states Version 3, 26/06/2025)")

NEW_VALUE = "6.0"
NEW_SOURCE_TEXT = (
    "C9. All development (not including an outbuilding or secondary dwelling) "
    "is to have a minimum rear setback of 6.0 metres measured from the outside "
    "face of the development (wall, balcony, deck, post, roof etc). Refer to "
    "Canada Bay LEP definition of 'building line or setback'."
)
NEW_CONDITION = (
    "Rear setbacks - single street frontage (p.E-15); excludes outbuildings "
    "and secondary dwellings. NOT yet stored: upper-floor living room 9.0m "
    "(C10), secondary dwelling 3.0m (C11), corner-lot rear 1.5m for the "
    "dwelling oriented to the secondary frontage (C12)."
)
REASON = (
    "[adjudicated 2026-08-03] was 1.5m — the second-storey SIDE setback from "
    "the C6 side-boundary table, carried by a 400-char truncated quote; not a "
    "rear control, and no true rear value was stored anywhere for canada_bay. "
    f"Corrected to 6.0m per {SOURCE}. Quote replaced in the same write "
    "(extraction-doc rule 2b: a correction must carry the evidence for the "
    "new value)."
)


def build_plan(cur):
    """Return the live pre-state if it still matches, else None (already done
    or diverged — caller reports which)."""
    cur.execute(
        """SELECT id, value_min, control_type, is_current, source_text, condition
             FROM dcp_setback_controls WHERE id = %s""", (CONTROL_ID,))
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"ERROR: control {CONTROL_ID} not found. Refusing to "
                         f"guess at a table that has changed shape.")
    _, value_min, control_type, is_current, source_text, condition = row
    pre_ok = (
        value_min is not None and f"{float(value_min):g}" == EXPECT_VALUE
        and control_type == "rear_setback"
        and is_current is True
        and source_text is not None
        and EXPECT_QUOTE_MARKER in source_text
        and len(source_text) == EXPECT_QUOTE_LEN
        and condition is None
    )
    return row if pre_ok else None


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--backup-table",
                    default="dcp_setback_controls_cb701_repair_20260803")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is not "
              "a pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    try:
        plan = build_plan(cur)
        print("\n=== canada_bay 701 rear-setback repair ===")
        if plan is None:
            cur.execute(
                """SELECT value_min, control_type, is_current,
                          left(source_text, 60)
                     FROM dcp_setback_controls WHERE id = %s""", (CONTROL_ID,))
            print(f"  pre-state no longer matches — already repaired or "
                  f"diverged. Live row: {cur.fetchone()}")
            print("  Nothing planned, nothing written.")
            return 0
        print(f"  rows to write (predicted): 1")
        print(f"  control {CONTROL_ID}: value_min {EXPECT_VALUE} -> {NEW_VALUE}, "
              f"quote -> C9 (rule 2b), condition scoped")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0

        old_source_text = plan[4]
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
            f"SELECT id, value_min, value_max, condition, source_text, "
            f"section_ref, review_reason, reviewed_at, last_verified_at, "
            f"needs_review, is_current, control_type "
            f"FROM dcp_setback_controls WHERE id = %s", (CONTROL_ID,))
        cur.execute(
            f"SELECT count(*) FROM {args.backup_table} WHERE id = %s",
            (CONTROL_ID,))
        backed_up = cur.fetchone()[0]
        conn.commit()
        if backed_up != 1:
            print(f"ERROR: expected 1 row in {args.backup_table} for id "
                  f"{CONTROL_ID}, found {backed_up} — it is from an earlier run "
                  f"and cannot roll this one back. Pass a fresh --backup-table. "
                  f"Aborting before any UPDATE.", file=sys.stderr)
            return 2
        print(f"  backed up 1 row to {args.backup_table}")

        cur.execute(
            """UPDATE dcp_setback_controls
                  SET value_min = %s, source_text = %s, condition = %s,
                      review_reason = %s, reviewed_at = NOW(),
                      last_verified_at = CURRENT_DATE, needs_review = FALSE
                WHERE id = %s AND control_type = 'rear_setback'
                  AND value_min = %s AND is_current = TRUE
                  AND source_text = %s AND condition IS NULL""",
            (NEW_VALUE, NEW_SOURCE_TEXT, NEW_CONDITION, REASON,
             CONTROL_ID, EXPECT_VALUE, old_source_text))
        written = cur.rowcount
        conn.commit()
        print(f"  updated {written} row(s) (predicted 1)")
        print(f"\nROLLBACK:\n  UPDATE dcp_setback_controls t SET "
              f"value_min = b.value_min, value_max = b.value_max, "
              f"condition = b.condition, source_text = b.source_text, "
              f"section_ref = b.section_ref, review_reason = b.review_reason, "
              f"reviewed_at = b.reviewed_at, "
              f"last_verified_at = b.last_verified_at, "
              f"needs_review = b.needs_review "
              f"FROM {args.backup_table} b WHERE t.id = b.id;")
        if written != 1:
            print(f"\nPARTIAL APPLY: the guard skipped the row — its values "
                  f"changed after planning. Re-run to rebuild the plan. Exiting "
                  f"2 so this is not read as clean.", file=sys.stderr)
            return 2

        cur.execute(
            """SELECT value_min, left(source_text, 40), is_current
                 FROM dcp_setback_controls WHERE id = %s""", (CONTROL_ID,))
        after = cur.fetchone()
        print(f"\n  post-write verify: value_min={after[0]}, quote starts "
              f"{after[1]!r}, served={after[2]}")
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
