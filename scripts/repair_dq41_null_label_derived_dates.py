#!/usr/bin/env python3
# prior-art-checked: no committed script repairs the DQ-41 cohort; the SAFETY
# shape (dry-run default, asserted backup table, per-row guard on the exact
# observed pre-state, printed rollback, idempotent re-run) is copied from
# scripts/repair_canada_bay_rear_setback.py. scripts/backfill_effective_date.py
# is the RETIRED parser that CREATED these values and must not be touched.
"""DQ-41 authorized repair: null the label-derived YYYY-01-01 effective_dates.

WHAT AND WHY
------------
Migration 040's backfill parsed ``effective_date`` out of ``dcp_version``
labels ("v2016-current" -> 2016-01-01). 528 of the 893 populated dates are
that manufactured-precision cohort: every one lands on 1 January, none records
a basis, and some contradict their own label ("v2014-amended-feb-2026" ->
2014-01-01). Authorized 2026-08-03: null the cohort. Nothing is lost —
``dcp_version`` (the source string) is retained on every row, and
``dcp_plan_as_at`` is the precision-honest home for any future re-derivation.

SCOPE GUARD
-----------
Only rows where ALL of:
  - effective_date is exactly a 1-January date (the label-derivation
    signature), AND
  - effective_date_basis IS NULL (a Jan-1 date carrying a real basis —
    none exist today — must never be nulled by this script).
Non-Jan-1 dates (365 rows) are untouched: their attribution is a separate
question and this authorization covers the Jan-1 cohort only.

SAFETY
------
Dry-run by default. Backup table first (id, effective_date, dcp_version),
asserting the planned row count exactly. UPDATE carries the same predicate as
the plan plus a per-row anti-drift guard (basis still NULL). Rollback SQL
printed. Idempotent: a re-run after a successful apply plans zero writes.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXPECTED_COHORT = 528

COHORT_WHERE = """
    effective_date IS NOT NULL
    AND EXTRACT(MONTH FROM effective_date) = 1
    AND EXTRACT(DAY FROM effective_date) = 1
    AND effective_date_basis IS NULL
"""


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--backup-table",
                    default="dcp_setback_controls_dq41_null_20260803")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is "
              "not a pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    try:
        cur.execute(f"SELECT COUNT(*) FROM dcp_setback_controls WHERE {COHORT_WHERE}")
        cohort = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*), COUNT(effective_date) FROM dcp_setback_controls")
        total, with_date = cur.fetchone()
        print("\n=== DQ-41: null the label-derived YYYY-01-01 effective_dates ===")
        print(f"  table rows: {total}; effective_date set: {with_date}; "
              f"Jan-1 basis-NULL cohort: {cohort} (authorized: {EXPECTED_COHORT})")

        if cohort == 0:
            # Prove the intended post-state before calling it done.
            cur.execute(
                """SELECT COUNT(*) FROM dcp_setback_controls
                    WHERE effective_date IS NOT NULL
                      AND EXTRACT(MONTH FROM effective_date) = 1
                      AND EXTRACT(DAY FROM effective_date) = 1""")
            jan1_any_basis = cur.fetchone()[0]
            if jan1_any_basis == 0:
                print("  already repaired — no Jan-1 effective_date remains. "
                      "Nothing planned, nothing written.")
                return 0
            print(f"  DIVERGED: {jan1_any_basis} Jan-1 dates exist but all "
                  f"carry a basis — outside this authorization. Exiting 2.",
                  file=sys.stderr)
            return 2
        if cohort != EXPECTED_COHORT:
            print(f"  DIVERGED: cohort is {cohort}, authorization covers "
                  f"exactly {EXPECTED_COHORT}. Re-measure before applying. "
                  f"Exiting 2.", file=sys.stderr)
            return 2

        print(f"  rows to write (predicted): {EXPECTED_COHORT} — "
              f"effective_date -> NULL; dcp_version and all control values "
              f"untouched")
        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0

        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name = %s)", (args.backup_table,))
        if cur.fetchone()[0]:
            print(f"ERROR: backup table {args.backup_table} already exists — "
                  f"it is from an earlier run and cannot roll this one back. "
                  f"Pass a fresh --backup-table. Aborting before any UPDATE.",
                  file=sys.stderr)
            return 2
        cur.execute(
            f"CREATE TABLE {args.backup_table} AS "
            f"SELECT id, effective_date, dcp_version "
            f"FROM dcp_setback_controls WHERE {COHORT_WHERE}")
        cur.execute(f"SELECT COUNT(*) FROM {args.backup_table}")
        backed = cur.fetchone()[0]
        if backed != EXPECTED_COHORT:
            conn.rollback()
            print(f"ERROR: backup captured {backed} rows, expected "
                  f"{EXPECTED_COHORT}. Rolled back, nothing written.",
                  file=sys.stderr)
            return 2
        conn.commit()
        print(f"  backed up {backed} rows to {args.backup_table}")

        # Per-row guard: the row must still be in the backed-up pre-state
        # (same Jan-1 date, basis still NULL) at write time.
        # Deliberately NO is_current filter: the authorized 528-row cohort
        # spans current AND retired rows — the label-derived dates are equally
        # unattributed on both, and scoping to is_current would strand the
        # retired rows' manufactured dates for any future resurrection.
        cur.execute(
            f"""UPDATE dcp_setback_controls t
                   SET effective_date = NULL
                  FROM {args.backup_table} b
                 WHERE t.id = b.id
                   AND t.effective_date = b.effective_date
                   AND t.effective_date_basis IS NULL""")
        written = cur.rowcount
        conn.commit()
        print(f"  updated {written} rows (predicted {EXPECTED_COHORT})")

        # The rollback likewise joins by id with no is_current scope — it
        # restores exactly the backed-up rows, current or retired.
        print(f"\nROLLBACK:\n  UPDATE dcp_setback_controls t "
              f"SET effective_date = b.effective_date "
              f"FROM {args.backup_table} b WHERE t.id = b.id;")

        cur.execute(
            """SELECT COUNT(*), COUNT(effective_date),
                      COUNT(*) FILTER (WHERE EXTRACT(MONTH FROM effective_date) = 1
                                         AND EXTRACT(DAY FROM effective_date) = 1)
                 FROM dcp_setback_controls""")
        v_total, v_dates, v_jan1 = cur.fetchone()
        print(f"  post-write verify: rows={v_total} (must be {total}), "
              f"effective_date set={v_dates} (predicted {with_date - EXPECTED_COHORT}), "
              f"Jan-1 remaining={v_jan1} (predicted 0)")
        ok = (written == EXPECTED_COHORT and v_total == total
              and v_dates == with_date - EXPECTED_COHORT and v_jan1 == 0)
        if not ok:
            print("PARTIAL APPLY: counts diverged — investigate before "
                  "re-running. Exiting 2 so this is not read as clean.",
                  file=sys.stderr)
            return 2
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
