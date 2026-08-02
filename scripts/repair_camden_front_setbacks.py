#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing script repairs an
# adjudicated control value. scripts/update_needs_review_controls.py is the
# closest — it also writes a handful of hand-verified rows — but it is a
# one-shot bound to its own 8 rows with no dry-run, no backup table and no
# optimistic guard. The SAFETY shape here (dry-run default, backup table,
# per-row guard on the value read at plan time, printed rollback) is copied from
# scripts/link_controls_to_provisions.py; the repair itself is new.
"""Repair two Camden front-setback controls adjudicated against the source PDF.

WHAT AND WHY
------------
Both rows were read against `data/dcps/camden-part4-residential-dwelling-controls.pdf`
(Camden DCP 2019, Part 4), Table 4-2 on PDF page 11 / printed page P4-8. Evidence
and the full adjudication of all 25 flagged controls:
`docs/qa/controls-adjudication-2026-08.md`.

**Control 690 — front_setback 3.5 m -> 4.5 m.**
Table 4-2 states the front setback where there are not 2 dwelling houses within
40 m, by lot size:

    < or equal to 900m2   4.5m   (A reduced front setback of 3.5m where the
                                  development is fronting open space.)
    >900m2-1,500m2        6.5m
    >1,500m2              10m

3.5 m is the *fronting-open-space exception*, and separately the battle-axe
figure. The row's own `condition` describes the general fallback case, for which
the smallest tier is **4.5 m**. So the exception had been stored as the rule,
understating the requirement — the dangerous direction.

**Control 692 — retired, not corrected.**
Its 4 m comes from P4-20: *"driveway crossover (minimum 4m for double garage)"* —
a driveway width. Camden prescribes no 4 m front setback, so there is no correct
value to substitute. Retiring it is the honest action; inventing a replacement
would be the same class of error in reverse.

WHAT THIS DOES NOT DO
---------------------
The 6.5 m and 10 m tiers are still absent from `dcp_setback_controls`, and this
does not add them: only these two rows were authorised. Camden 693 and 695 are
already `is_current = FALSE` and are untouched.

`last_verified_at` IS set on 690 because the source was read directly for this
repair. It is deliberately NOT set on 692 — a retired row is not a verified one.

SAFETY
------
Dry-run by default. Backup table first, asserting every planned id is present.
Per-row UPDATE guarded on the values read at plan time, so a concurrent edit
skips rather than clobbers. Rollback SQL printed. Idempotent: re-running after a
successful apply plans zero writes.
"""
from __future__ import annotations

import argparse
import os
import sys

SOURCE = ("data/dcps/camden-part4-residential-dwelling-controls.pdf "
          "Table 4-2, printed page P4-8")

# (id, expected current value_min, expected is_current, new value_min,
#  new is_current, new condition, review_reason)
PLAN = [
    (
        690, "3.5", True, "4.5", True,
        "Lot <= 900m2 (Table 4-2). Applies where there are not 2 dwelling houses "
        "within 40m on the same side of the primary road; otherwise the setback is "
        "the average of those 2. A reduced 3.5m applies only where the development "
        "fronts open space. Tiers >900-1500m2 = 6.5m and >1500m2 = 10m are NOT yet "
        "stored.",
        f"[adjudicated 2026-08-03] was 3.5m, which is the fronting-open-space "
        f"exception, not the rule. Corrected to 4.5m per {SOURCE}.",
    ),
    (
        692, "4.0", True, None, False,
        None,
        f"[adjudicated 2026-08-03] retired: the 4m came from 'driveway crossover "
        f"(minimum 4m for double garage)' at printed page P4-20 — a driveway width, "
        f"not a setback. Camden prescribes no 4m front setback in {SOURCE}, so "
        f"there is no correct value to substitute.",
    ),
]


def build_plan(cur) -> tuple[list, list]:
    """Rows still matching their expected pre-state, and rows PROVEN repaired.

    A row matching neither its pre-state nor its intended post-state is a
    divergence, and classifying it as done would be a silent failure — e.g.
    690 hand-edited to 9.9m would previously land in `done` and --apply would
    exit 0 while the invalid setback stayed served (Sol finding, 2026-08-03).
    """
    cur.execute(
        """SELECT id, value_min, is_current, condition
           FROM dcp_setback_controls WHERE id = ANY(%s) ORDER BY id""",
        ([row[0] for row in PLAN],),
    )
    live = {r[0]: r for r in cur.fetchall()}
    todo, done = [], []
    for spec in PLAN:
        (control_id, expect_val, expect_cur,
         new_val, new_cur, new_cond, _reason) = spec
        row = live.get(control_id)
        if row is None:
            raise SystemExit(f"ERROR: control {control_id} not found. Refusing to "
                             f"guess at a table that has changed shape.")
        actual_val = None if row[1] is None else f"{float(row[1]):g}"
        expected = None if expect_val is None else f"{float(expect_val):g}"
        if actual_val == expected and row[2] == expect_cur:
            todo.append(spec)
            continue
        # Intended post-state: corrected value (or unchanged value for a pure
        # retirement), target currency, and the new condition where one is set.
        target_val = expected if new_val is None else f"{float(new_val):g}"
        post_ok = (actual_val == target_val and row[2] == new_cur
                   and (new_cond is None or row[3] == new_cond))
        if post_ok:
            done.append((control_id, actual_val, row[2]))
        else:
            print(f"ERROR: control {control_id} matches neither its pre-state "
                  f"nor its intended post-state (value={actual_val}, "
                  f"current={row[2]}). Refusing to classify a divergence as "
                  f"done. Exiting 2.", file=sys.stderr)
            raise SystemExit(2)
    return todo, done


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--backup-table",
                    default="dcp_setback_controls_camden_repair_20260803")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is not a "
              "pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    try:
        todo, done = build_plan(cur)
        print("\n=== camden front-setback repair ===")
        print(f"  rows in plan            : {len(PLAN)}")
        print(f"  still to write          : {len(todo)}")
        print(f"  already in target state : {len(done)}  {done if done else ''}")
        for spec in todo:
            control_id, old_val, _, new_val, new_cur = spec[:5]
            change = (f"value_min {old_val} -> {new_val}" if new_val
                      else f"is_current True -> {new_cur}")
            print(f"    control {control_id}: {change}")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0
        if not todo:
            print("\nNothing to write.")
            return 0

        ids = [spec[0] for spec in todo]
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
            f"SELECT id, value_min, value_max, is_current, condition, review_reason,"
            f" reviewed_at, last_verified_at FROM dcp_setback_controls "
            f"WHERE id = ANY(%s)", (ids,))
        cur.execute(
            f"SELECT count(*) FROM unnest(%s::int[]) AS wanted(id) WHERE NOT EXISTS "
            f"(SELECT 1 FROM {args.backup_table} b WHERE b.id = wanted.id)", (ids,))
        missing = cur.fetchone()[0]
        conn.commit()
        if missing:
            print(f"ERROR: {missing} of {len(ids)} rows are NOT in "
                  f"{args.backup_table}; it is from an earlier run and cannot roll "
                  f"this one back. Pass a fresh --backup-table. Aborting before any "
                  f"UPDATE.", file=sys.stderr)
            return 2
        print(f"  backed up {len(ids)} rows to {args.backup_table}")

        written = 0
        for spec in todo:
            (control_id, old_val, old_cur, new_val,
             new_cur, new_cond, reason) = spec
            if new_val is not None:
                cur.execute(
                    """UPDATE dcp_setback_controls
                          SET value_min = %s, condition = %s, review_reason = %s,
                              reviewed_at = NOW(), last_verified_at = CURRENT_DATE,
                              needs_review = FALSE
                        WHERE id = %s AND value_min = %s AND is_current = %s""",
                    (new_val, new_cond, reason, control_id, old_val, old_cur))
            else:
                # Retirement only. last_verified_at is deliberately NOT set: a
                # retired row is not a verified one.
                cur.execute(
                    """UPDATE dcp_setback_controls
                          SET is_current = %s, review_reason = %s, reviewed_at = NOW(),
                              needs_review = FALSE
                        WHERE id = %s AND value_min = %s AND is_current = %s""",
                    (new_cur, reason, control_id, old_val, old_cur))
            written += cur.rowcount
        conn.commit()
        print(f"  updated {written} rows ({len(todo) - written} skipped by the guard)")
        print(f"\nROLLBACK:\n  UPDATE dcp_setback_controls t SET value_min = b.value_min,"
              f" is_current = b.is_current, condition = b.condition,"
              f" review_reason = b.review_reason, reviewed_at = b.reviewed_at,"
              f" last_verified_at = b.last_verified_at"
              f" FROM {args.backup_table} b WHERE t.id = b.id;")
        if written != len(todo):
            print(f"\nPARTIAL APPLY: {len(todo) - written} of {len(todo)} rows were "
                  f"skipped because their values changed after planning. Re-run to "
                  f"rebuild the plan. Exiting 2 so this is not read as clean.",
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
