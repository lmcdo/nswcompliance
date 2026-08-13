#!/usr/bin/env python3
# prior-art-checked: reuse not viable because scripts/extract_dcp_stated_dates.py
# derives dates from a PDF it can parse, and these three commencement clauses are
# in documents that are NOT in data/dcps and are stated in three different shapes
# (a numbered 'Commencement of this Plan' clause, a 'Date on Which the BDCP Takes
# Effect' clause, and an 'Important Dates' block). Teaching the extractor all
# three to write three rows once would be a parser built for a backfill. This
# follows the house one-off repair pattern (repair_canada_bay_rear_setback.py):
# explicit values, verbatim evidence, dry-run default, guarded UPDATEs.
"""DQ-62: replace three amendment/consolidation dates with the commencement each
plan states in its own text, and correct one stale registry plan name.

Every value below is a VERBATIM read from the plan's own commencement clause,
not a search-engine summary (that distinction is why #947 held two dates rather
than writing them). Dry-run by default.
"""
import argparse
import json
import os
import sys

from dotenv import load_dotenv

# (lga, iso date, evidence) — the date is the "came into effect" value, never
# the adoption date sitting beside it in the same sentence.
DATES = [
    ("strathfield", "2006-05-03",
     'Strathfield Consolidated DCP 2005, clause 1.2 "Commencement of this Plan" '
     '(strathfield.nsw.gov.au general-introduction-of-scdcp-2005-131020.pdf, read '
     '2026-08-13): "This DCP was adopted by Council on 4 April 2006 and came into '
     'effect on 3 May 2006." The cover of the same document reads "Adopted by '
     'Council: 6 October 2020 / In force: 13 October 2020" — that is the '
     'consolidation stamp (currency), not the commencement, and it is what the '
     'previous stored value 2020-09-08 came from.'),
    ("burwood", "2013-03-01",
     'Burwood DCP, clause 1.4 "Date on Which the BDCP Takes Effect" '
     '(burwood.nsw.gov.au burwood-development-control-plan-dcp.pdf, read '
     '2026-08-13): "This Plan was adopted by Burwood Council on 12 February 2013 '
     'and came into effect on 1 March 2013." The cover of the same document reads '
     '"Adopted by Council: 17 February 2026 / Effective: 5 March 2026" — the '
     'current consolidation, and the source of the previous stored value '
     '2026-03-05.'),
    ("the_hills", "2013-03-26",
     'The Hills DCP 2012, Part A Introduction, section 8 "Important Dates & '
     'Document Specifications" (thehills.nsw.gov.au '
     'the-hills-dcp-2012-part-a-introduction.pdf, read 2026-08-13): "Adoption '
     'date: 12 March 2013 / Date in force: 26 March 2013". Section 9 "List of '
     'Amendments" immediately follows and its earliest row is adopted 28/05/2013, '
     'in force 11/06/2013, so no amendment precedes this date. The previous '
     'stored value 2022-05-06 was "In Force 6 May 2022", an amendment.'),
]

# fairfield is NOT a wrong date. The file data/dcps/fairfield-citywide-dcp-2013.pdf
# is actually the Fairfield CityWide DCP **2024** (title page, 567pp), whose
# clause 1.7 states "This Development Control Plan came into effect on 22 August
# 2024" — so the stored date is right and the REGISTRY NAME is stale, which is
# what made the DQ-62 probe flag it. Correcting the name, not the date.
REGISTRY_RENAME = ("fairfield", "Fairfield DCP 2013", "Fairfield City Wide DCP 2024")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write. Default: dry run.")
    args = ap.parse_args()

    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 2

    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")

    print("=== BEFORE ===")
    cur.execute(
        "SELECT lga, stated_date FROM dcp_plan_as_at WHERE lga = ANY(%s) ORDER BY lga",
        ([d[0] for d in DATES],),
    )
    before = dict(cur.fetchall())
    for lga, new, _ev in DATES:
        print(f"  {lga:14s} {before.get(lga)}  ->  {new}")
    cur.execute(
        "SELECT count(*) FROM dcp_chapter_registry WHERE council=%s AND dcp_name=%s",
        (REGISTRY_RENAME[0], REGISTRY_RENAME[1]),
    )
    n_reg = cur.fetchone()[0]
    print(f"  registry: {n_reg} fairfield row(s) {REGISTRY_RENAME[1]!r} -> {REGISTRY_RENAME[2]!r}")

    if not args.apply:
        print(f"\nDRY RUN — nothing written. --apply would update {len(DATES)} "
              f"stated_date rows and {n_reg} registry rows.")
        conn.close()
        return 0

    written = 0
    try:
        for lga, new, ev in DATES:
            # Guarded on the OLD value: if another session already corrected
            # this row, the update must miss rather than overwrite their work.
            cur.execute(
                """
                UPDATE dcp_plan_as_at
                   SET stated_date = %s, stated_date_precision = 'day',
                       stated_date_kind = 'effective', stated_evidence = %s,
                       updated_at = now()
                 WHERE lga = %s AND stated_date = %s
                """,
                (new, ev, lga, before[lga]),
            )
            if cur.rowcount != 1:
                raise SystemExit(f"{lga}: expected 1 row, got {cur.rowcount} — aborting")
            written += cur.rowcount

        cur.execute(
            "UPDATE dcp_chapter_registry SET dcp_name = %s, updated_at = now() "
            "WHERE council = %s AND dcp_name = %s",
            (REGISTRY_RENAME[2], REGISTRY_RENAME[0], REGISTRY_RENAME[1]),
        )
        renamed = cur.rowcount
        if renamed != n_reg:
            raise SystemExit(f"registry: expected {n_reg}, got {renamed} — aborting")

        # Nothing may leave an amendment date in the commencement column.
        cur.execute("SELECT count(*) FROM dcp_plan_as_at WHERE stated_date_kind = 'amended'")
        if cur.fetchone()[0]:
            raise SystemExit("a row still carries stated_date_kind='amended' — aborting")

        conn.commit()
        print(f"\nwrote {written} dates + {renamed} registry renames")
        cur.execute(
            "SELECT lga, stated_date FROM dcp_plan_as_at WHERE lga = ANY(%s) ORDER BY lga",
            ([d[0] for d in DATES],),
        )
        print("=== AFTER ===")
        for lga, d in cur.fetchall():
            print(f"  {lga:14s} {d}")
        return 0
    except BaseException as exc:
        conn.rollback()
        print(f"ROLLED BACK: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
