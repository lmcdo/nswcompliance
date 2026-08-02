#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no script re-types a control. The
# safety shape (dry-run default, backup table asserting every planned id, per-row
# guard on the value read at plan time, printed rollback) is copied from
# scripts/link_controls_to_provisions.py and scripts/repair_camden_front_setbacks.py;
# the selection and the re-type are new. migrations/054 adds the target type and
# is deliberately separate so schema and data roll back independently.
"""Re-file corner-lot secondary-street setbacks under their own control type.

WHY
---
DQ-40: 31 controls carry a control_type their own source_text contradicts, 28 of
them served. Sixteen-odd are a single cause — the enforced vocabulary had no
`secondary_street_setback`, so extractors filed a genuine control under
`front_setback` and qualified it in `condition`. The VALUES are right and the
conditions are candid; the label is wrong, which puts a corner-lot 2-4 m setback
in the same bucket as a primary 4.5-6 m one.

migrations/054 adds the type. This moves the rows.

SELECTION — deliberately narrow
-------------------------------
A row qualifies only when it is currently `front_setback` AND its own
`source_text` names a secondary street, road or frontage. That wording is the
evidence; `condition` alone is not enough, because a condition is an annotation
while source_text is the quote. Rows whose quote merely mentions a garage or
driveway are NOT swept up here — they are a different defect (a garage setback
filed as a front setback) and need their own ruling.

Both served and retired rows are re-filed: a retired row with the wrong label is
still mislabelled, and leaving it behind would make the vocabulary inconsistent
for anyone reading history.

WHAT IT DOES NOT TOUCH
----------------------
No value, no condition, no source_text, no currency. Only `control_type`, plus a
`review_reason` recording why. If the label was the only thing wrong, the label is
the only thing that changes.
"""
from __future__ import annotations

import argparse
import os
import sys

# The quote must name the secondary street itself. "corner lot" alone is not
# enough — a corner-lot clause can still be about the PRIMARY frontage.
# "secondary" must directly qualify the ROAD, not merely appear near it. A looser
# pattern — (secondary|corner) within 40 chars of (street|road|frontage) — was
# tried first and swept up six rows it had no business touching, most dangerously
# blacktown 107, "Secondary dwelling building setback from street 6m", which is a
# PRIMARY street setback for a granny flat. Also caught: a fencing clause, a duplex
# streetscape clause, a two-dwellings-in-tandem clause and a garage setback.
SELECT_SQL = """
    SELECT id, lga, dev_type, value_min, unit, is_current, control_type,
           source_text AS quote, left(coalesce(condition, ''), 60) AS cond
      FROM dcp_setback_controls
     WHERE control_type = 'front_setback'
       AND source_text ~* 'secondary[ /-]*(corner[ /-]*)?(street|road|frontage)'
       -- Never re-file on TRUNCATED evidence. A quote severed at the extractor's
       -- 400-char limit can mention a secondary street in passing while the
       -- control it actually states is something else entirely: camden 693 is a
       -- FENCE height clause, canada_bay 702 is two dwellings in tandem, and
       -- fairfield 714 is a GARAGE setback. Same doctrine as TRUNCATED_EVIDENCE
       -- in the checker — a cut quote is not evidence, in either direction.
       AND length(source_text) <> 400
       AND id <> ALL(%(exclude)s)
     ORDER BY lga, id
"""

# Rows the pattern reaches but a human read says NO. Listed with the reason, so
# the exclusion is auditable rather than a silent narrowing of the query.
EXCLUDE = {
    714: ("fairfield: the 6 m is a GARAGE setback from the FRONT boundary — "
          "'Garage(s) must be setback a minimum of 6 metres from the front "
          "boundary except in the case of a garage to a secondary [street]'. "
          "The secondary street appears only as the exception, not as the "
          "control. Needs its own ruling as a garage setback."),
}

REASON = ("[DQ-40 2026-08-03] re-filed front_setback -> secondary_street_setback: "
          "the quote names a secondary street, and the vocabulary had no type for "
          "it until migration 054. Value, condition and source_text unchanged.")


def build_plan(cur) -> list[tuple]:
    cur.execute(SELECT_SQL, {"exclude": list(EXCLUDE)})
    return [tuple(r) for r in cur.fetchall()]


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup-table",
                    default="dcp_setback_controls_refile_backup_20260803")
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
        plan = build_plan(cur)
        print(f"\n=== re-file secondary-street setbacks ===")
        print(f"  rows to re-type: {len(plan)}  "
              f"({sum(1 for r in plan if r[5])} served, "
              f"{sum(1 for r in plan if not r[5])} retired)")
        for control_id, lga, dev, vmin, unit, cur_flag, _ct, quote, cond in plan:
            print(f"    {control_id:<5} {lga}/{dev} = {vmin}{unit or ''} "
                  f"served={cur_flag}")
            print(f"          quote: {quote[:90]!r}")
            print(f"          cond : {cond!r}")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0
        if not plan:
            print("\nNothing to re-file.")
            return 0

        ids = [row[0] for row in plan]
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
            f"SELECT id, control_type, review_reason FROM dcp_setback_controls "
            f"WHERE id = ANY(%s)", (ids,))
        cur.execute(
            f"SELECT count(*) FROM unnest(%s::int[]) AS wanted(id) WHERE NOT EXISTS "
            f"(SELECT 1 FROM {args.backup_table} b WHERE b.id = wanted.id)", (ids,))
        missing = cur.fetchone()[0]
        conn.commit()
        if missing:
            print(f"ERROR: {missing} of {len(ids)} rows are NOT in "
                  f"{args.backup_table} — it is from an earlier run and cannot roll "
                  f"this one back. Pass a fresh --backup-table. Aborting before any "
                  f"UPDATE.", file=sys.stderr)
            return 2
        print(f"  backed up {len(ids)} rows to {args.backup_table}")

        written = 0
        for (control_id, _lga, _dev, vmin, _unit, cur_flag, _ct,
             quote, _cond) in plan:
            # Guarded on the FULL evidentiary pre-state read at plan time —
            # type alone is not enough: a row whose source_text was replaced
            # after planning may no longer establish a secondary-street
            # control at all (Sol finding, 2026-08-03). IS NOT DISTINCT FROM
            # for the nullable value_min.
            cur.execute(
                """UPDATE dcp_setback_controls
                      SET control_type = 'secondary_street_setback',
                          review_reason = %s, reviewed_at = NOW()
                    WHERE id = %s AND control_type = 'front_setback'
                      AND source_text = %s
                      AND value_min IS NOT DISTINCT FROM %s
                      AND is_current = %s""",
                (REASON, control_id, quote, vmin, cur_flag))
            written += cur.rowcount
        conn.commit()
        print(f"  re-typed {written} rows ({len(plan) - written} skipped by the guard)")
        # Rollback restores the label on every backed-up row regardless of
        # is_current — a mislabel is a mislabel on retired rows too, and the
        # backup join on id makes any currency filter here redundant.
        print(f"\nROLLBACK:\n  UPDATE dcp_setback_controls t "
              f"SET control_type = b.control_type, review_reason = b.review_reason "
              f"FROM {args.backup_table} b WHERE t.id = b.id;")
        if written != len(plan):
            print(f"\nPARTIAL APPLY: {len(plan) - written} rows skipped. Re-run to "
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
