#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no committed script executes these
# two authorised repairs. The SAFETY shape (dry-run default, backup table
# asserting every planned id, per-row guard on the full pre-state read at plan
# time, all-or-nothing rollback before commit, printed rollback SQL, exact
# post-state proof for skipped rows) is copied from
# scripts/repair_missing_primary_controls.py after its three Sol review rounds;
# only the two rulings are new.
"""Apply the two repairs held fail-closed on 2026-08-03 — now authorised.

Both rows were flagged `needs_review=TRUE` by the DQ-40 close-out (PR #869)
with the repair evidence recorded in their `review_reason`. The user authorised
applying them on 2026-08-03. Rule 2b: each write carries the verbatim quote
supporting the NEW value in the same UPDATE.

FAIRFIELD 716 — rear_setback / secondary_dwelling: 6.0 -> 0.9 m
    The stored 6.0 was 5C.2.3.3 (first-floor walls, Chapter 5C "Dwelling
    Houses on Narrow Lots") misfiled under secondary_dwelling — a 6.7x
    overstatement. The actual granny-flat control is 5B.2.3.1(a), printed
    p.176 (PDF p.32 of data/dcps/fairfield-ch5-dwelling-houses.pdf):
    "Secondary dwellings (granny flats) require minimum side and rear
    setbacks of 900mm." Same clause row 715 (side) already quotes — one
    clause governs both boundaries. Evidence STRONG.

RYDE 682 — side_setback / dwelling_house: 4.0 -> 0.9-1.5 m
    The stored 4.0 came from a design-PREFERENCE clause ("a minimum side
    setback of 4 m is preferred" for northerly aspects), 400-char truncated.
    The general side control is s2.9.2(a)/(b), printed p.26 (PDF p.26 of
    data/dcps/ryde-part3.3-dwelling-houses.pdf): 900mm one storey / 1.5m two
    storey. Range-row shape (value_min 0.9, value_max 1.5) per burwood rows
    1080/1176. Evidence STRONG.

SAFETY: dry-run default; backup table with per-id coverage assertion; guards
pin the complete pre-state read at recon (value, value_max IS NULL, type,
currency, needs_review=TRUE, exact/prefix quote, condition IS NULL); the two
UPDATEs are all-or-nothing (any guard miss rolls back both before commit);
skipped rows must prove the exact intended post-state or the script exits 2.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STAMP = "[adjudicated 2026-08-03, authorised]"

FF_716_OLD_QUOTE = (
    "First floor walls must be set back a minimum of 6 metres from the rear "
    "boundary where the lot adjoins residential properties."
)
FF_716_NEW_QUOTE = (
    "a) Secondary dwellings (granny flats) require minimum side and rear "
    "setbacks of 900mm."
)
FF_716_COND = (
    "Clause covers side and rear (both 900mm). Separation to principal "
    "dwelling 1.8m (5B.2.3.1(b)) and corner secondary-street setback 1.5m "
    "(5B.2.3.1(c)) are NOT stored."
)
FF_716_REASON = (
    f"{STAMP} was 6.0m — 5C.2.3.3 (first-floor walls, Chapter 5C Dwelling "
    f"Houses on Narrow Lots) misfiled under secondary_dwelling, held "
    f"fail-closed since the DQ-40 close-out. Corrected to 0.9m per "
    f"5B.2.3.1(a), printed p.176 (PDF p.32 of "
    f"data/dcps/fairfield-ch5-dwelling-houses.pdf). Quote replaced in the "
    f"same write (rule 2b)."
)

RYDE_682_NEW_QUOTE = (
    "a. The outside walls of a one storey dwelling are to be set back from "
    "the side boundaries not less than 900 mm. b. The outside walls of a two "
    "storey dwelling are to be set back from side boundaries not less than "
    "1.5 m."
)
RYDE_682_COND = (
    "900mm one storey; 1.5m two storey; a second-storey addition to a single "
    "storey dwelling is also 1.5m (s2.9.2(c)). NOT stored: wider-than-long "
    "allotments - one side setback 20% of allotment width or 8m, whichever "
    "is the greater (s2.9.2(d))."
)
RYDE_682_REASON = (
    f"{STAMP} was 4.0m from a design-preference clause ('a minimum side "
    f"setback of 4 m is preferred', northerly aspect), held fail-closed "
    f"since the DQ-40 close-out. Replaced with the general side control "
    f"s2.9.2(a)/(b), printed p.26 (PDF p.26 of "
    f"data/dcps/ryde-part3.3-dwelling-houses.pdf): 900mm one storey / 1.5m "
    f"two storey, range-row per burwood 1080/1176. Quote replaced in the "
    f"same write (rule 2b)."
)

# (id, pre_guard_sql, pre_params, set_sql, set_params, post_guard_sql,
#  post_params, reason, label)
PLAN = [
    (
        716,
        "control_type = 'rear_setback' AND value_min = 6.0 "
        "AND value_max IS NULL AND is_current AND needs_review = TRUE "
        "AND source_text = %s AND condition IS NULL",
        (FF_716_OLD_QUOTE,),
        "value_min = 0.9, source_text = %s, condition = %s, "
        "section_ref = 'fairfield-ch5-dwelling-houses.pdf#5B.2.3.1(a)', "
        "pdf_page = 32, needs_review = FALSE",
        (FF_716_NEW_QUOTE, FF_716_COND),
        "control_type = 'rear_setback' AND value_min = 0.9 AND is_current "
        "AND needs_review = FALSE AND source_text = %s AND condition = %s",
        (FF_716_NEW_QUOTE, FF_716_COND),
        FF_716_REASON,
        "fairfield 716: rear 6.0 -> 0.9 per 5B.2.3.1(a)",
    ),
    (
        682,
        "control_type = 'side_setback' AND value_min = 4.0 "
        "AND value_max IS NULL AND is_current AND needs_review = TRUE "
        "AND length(source_text) = 400 "
        "AND source_text LIKE 'a. Living areas%%' AND condition IS NULL",
        (),
        "value_min = 0.9, value_max = 1.5, source_text = %s, condition = %s, "
        "section_ref = 'ryde-part3.3-dwelling-houses.pdf#2.9.2(a)-(b)', "
        "pdf_page = 26, needs_review = FALSE",
        (RYDE_682_NEW_QUOTE, RYDE_682_COND),
        "control_type = 'side_setback' AND value_min = 0.9 "
        "AND value_max = 1.5 AND is_current AND needs_review = FALSE "
        "AND source_text = %s AND condition = %s",
        (RYDE_682_NEW_QUOTE, RYDE_682_COND),
        RYDE_682_REASON,
        "ryde 682: side 4.0 -> 0.9-1.5 per s2.9.2(a)/(b)",
    ),
]


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--backup-table",
                    default="dcp_setback_controls_authorized_repairs_20260803")
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
        todo, done = [], []
        for spec in PLAN:
            control_id, pre_guard, pre_params = spec[0], spec[1], spec[2]
            post_guard, post_params, reason = spec[5], spec[6], spec[7]
            # pre_guard pins the held pre-state incl. is_current and
            # needs_review = TRUE.
            cur.execute(
                f"SELECT 1 FROM dcp_setback_controls WHERE id = %s "
                f"AND {pre_guard}", (control_id, *pre_params))
            if cur.fetchone():
                todo.append(spec)
                continue
            # Skipped rows must PROVE the exact intended post-state
            # (is_current, needs_review, quote, condition, review_reason) —
            # never classify a divergence as done.
            cur.execute(
                f"SELECT 1 FROM dcp_setback_controls WHERE id = %s "
                f"AND {post_guard} AND review_reason = %s",
                (control_id, *post_params, reason))
            if cur.fetchone():
                done.append(spec)
                continue
            print(f"ERROR: control {control_id} matches neither its held "
                  f"pre-state nor the intended post-state — refusing to "
                  f"classify a divergence as done. Nothing written. "
                  f"Exiting 2.", file=sys.stderr)
            return 2

        print("\n=== authorised held-row repairs ===")
        print(f"  rows to write (predicted): {len(todo)} of {len(PLAN)}"
              f"  (proven already repaired: {[s[0] for s in done]})")
        for spec in todo:
            print(f"    {spec[8]}")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to "
                  "execute.")
            return 0
        if not todo:
            print("\nNothing to write.")
            return 0

        ids = [spec[0] for spec in todo]
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
            f"SELECT id, control_type, value_min, value_max, condition, "
            f"source_text, section_ref, pdf_page, review_reason, reviewed_at, "
            f"last_verified_at, needs_review, is_current "
            f"FROM dcp_setback_controls WHERE id = ANY(%s)", (ids,))
        cur.execute(
            f"SELECT count(*) FROM unnest(%s::int[]) AS wanted(id) "
            f"WHERE NOT EXISTS (SELECT 1 FROM {args.backup_table} b "
            f"WHERE b.id = wanted.id)", (ids,))
        missing = cur.fetchone()[0]
        conn.commit()
        if missing:
            print(f"ERROR: {missing} of {len(ids)} rows are NOT in "
                  f"{args.backup_table} — it is from an earlier run and "
                  f"cannot roll this one back. Pass a fresh --backup-table. "
                  f"Aborting before any write.", file=sys.stderr)
            return 2
        print(f"  backed up {len(ids)} rows to {args.backup_table}")

        written = 0
        for (control_id, pre_guard, pre_params, set_sql, set_params,
             _post_guard, _post_params, reason, _label) in todo:
            # last_verified_at IS set here: the stored content is verified
            # against source in this same pass (unlike the earlier flag-only
            # writes, which deliberately did not stamp it).
            cur.execute(
                f"""UPDATE dcp_setback_controls
                       SET {set_sql}, review_reason = %s, reviewed_at = NOW(),
                           last_verified_at = CURRENT_DATE
                     WHERE id = %s AND {pre_guard}""",
                (*set_params, reason, control_id, *pre_params))
            written += cur.rowcount
        # All-or-nothing: verify before committing.
        if written != len(todo):
            conn.rollback()
            print(f"\nGUARD MISS: {len(todo) - written} of {len(todo)} rows "
                  f"changed after planning. EVERYTHING rolled back — nothing "
                  f"written. Re-run to rebuild the plan. Exiting 2.",
                  file=sys.stderr)
            return 2
        conn.commit()
        print(f"  updated {written} rows (predicted {len(todo)})")
        print(f"\nROLLBACK:\n  UPDATE dcp_setback_controls t SET "
              f"value_min = b.value_min, value_max = b.value_max, "
              f"condition = b.condition, source_text = b.source_text, "
              f"section_ref = b.section_ref, pdf_page = b.pdf_page, "
              f"review_reason = b.review_reason, reviewed_at = b.reviewed_at, "
              f"last_verified_at = b.last_verified_at, "
              f"needs_review = b.needs_review, is_current = b.is_current "
              f"FROM {args.backup_table} b WHERE t.id = b.id;")

        cur.execute(
            """SELECT id, control_type, value_min, value_max, is_current,
                      needs_review, left(source_text, 45)
                 FROM dcp_setback_controls WHERE id = ANY(%s) ORDER BY id""",
            (ids,))
        print("\n  post-write verify:")
        for row in cur.fetchall():
            print(f"    {row}")
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
