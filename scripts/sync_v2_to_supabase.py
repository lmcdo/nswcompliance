#!/usr/bin/env python3
"""
Sync v2_ enriched columns from local PostgreSQL to Supabase production.
This syncs only the v2_ enrichment data, not the full database.

⚠ THIS IS A PRODUCTION WRITE, AND IT DOES NOT DO WHAT ITS NAME SAYS.
`get_local_connection()` defaults to `localhost/nsw_planning`, so the code reads
as "copy from a local mirror". It is not what runs. `load_dotenv()` above puts
the repo's `.env` on top, and `.env` sets PGHOST/PGDATABASE/PGUSER/PGPASSWORD to
the Supabase pooler -- so BOTH ends resolve to production. Measured 2026-09-24:
`current_database()` = postgres at the pooler address on the so-called local
side, 63,921 rows, `source_council` present. It is a production self-copy of 16
columns over 48,802 actionable rows, committing every 100, with no backup and no
rollback if it dies halfway.

THAT IS ENVIRONMENT-DEPENDENT, WHICH IS THE DANGEROUS PART. On a machine where
the PG* variables are NOT set -- a fresh clone, CI, another developer -- the same
file falls back to its hardcoded `localhost/nsw_planning`. That database exists
on this machine and is stale: 46,585 provisions, no `source_council` column at
all, and **200 rows carrying a retired B or IN zone code**, the series abolished
by the 2022 employment-zone reform. `v2_applicable_zones` is a HARD filter on
the served answer (`for-property/route.ts:1012`), so pushing a retired code
DELETES that row from every answer for the SUCCESSOR zone, silently. Same file,
same command, two completely different payloads depending on a dotfile.

Until 2026-09-24 the only thing in front of either path was
`input("Continue? (yes/no): ")`. A prompt asks whether the operator meant to run
it; it cannot tell them the payload is wrong. Two gates were added, both
refusing rather than warning:
  * DRY RUN BY DEFAULT. `--apply` is required to write anything, matching every
    other production-write script here.
  * ZONE VALIDITY, checked against the TARGET's own `lep_zone_coverage` before a
    single UPDATE is issued, using `validate_zone_code_validity.py`'s own loaders
    rather than a second copy of the rule. On the first run it refused: one
    canterbury_bankstown row (id=122333) carrying R5.

WHAT THESE GATES DO NOT COVER, stated because a half-covered check that reads as
total is worse than none. The zone gate is three-state and SKIPS any row whose
council does not resolve to an LGA, so it cannot see a statewide instrument, and
on the stale-mirror path it would skip every row (no `source_council` column ->
the export raises before the gate is reached, which fails closed, but for the
wrong reason). Nothing here checks the other 15 columns, and nothing checks that
the source is fresher than the target.
"""
import argparse
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

# argparse prints this module's docstring as --help, and that docstring
# carries a warning glyph. On a Windows console stdout defaults to cp1252,
# which cannot encode it, so `--help` died with a UnicodeEncodeError before
# printing a single option. Same reconfigure as scripts/dcp_approve_graded.py.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

V2_COLUMNS = [
    'v2_is_actionable',
    'v2_dcp_layer',
    'v2_dcp_part',
    'v2_topic',
    'v2_provision_type',
    'v2_precinct_id',
    'v2_marker',
    'v2_display_behavior',
    'v2_applicable_zones',
    'v2_applicable_dev_types',
    'v2_site_condition_required',
    'v2_has_numeric_value',
    'pdf_page',  # Added for page offset sync
    # DQ-11 heritage sub-categorization columns
    'v2_heritage_type',
    'v2_heritage_element',
    'v2_heritage_hca'
]

def get_local_connection():
    """Connect to local PostgreSQL database."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'nsw_planning'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres')
    )

def get_supabase_connection():
    """Connect to Supabase production database."""
    url = os.getenv('SUPABASE_DB_URL')
    if not url:
        print("ERROR: SUPABASE_DB_URL not set in .env")
        sys.exit(1)
    return psycopg2.connect(url)

def export_v2_data(local_conn):
    """Export v2_ enriched provisions from local database."""
    cur = local_conn.cursor(cursor_factory=RealDictCursor)

    # source_council is SELECTed but is NOT in V2_COLUMNS, so it is never
    # written. It is here only so the zone gate below can resolve each row to
    # an LGA -- without it the check would have nothing to compare against and
    # would pass every row, which is the failure mode it exists to prevent.
    columns_str = ', '.join(['id'] + V2_COLUMNS)
    cur.execute(f"""
        SELECT {columns_str}, source_council
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        ORDER BY id
    """)

    rows = cur.fetchall()
    print(f"  Exported {len(rows)} enriched provisions from local")
    return rows


def rows_with_retired_zones(supa_conn, data):
    """Rows whose zones are not in their own LGA's land-use table.

    THE PRE-WRITE HALF OF DQ-30, the twin of the gate in
    `retag_applicability_slug_docids.py`. Ground truth is loaded from the
    TARGET database, not the local mirror: the question is whether these values
    are valid where they are about to land, and the mirror's copy of
    `lep_zone_coverage` may itself be as stale as the rows being synced.

    Three-state, matching the checker it borrows from: a council that does not
    resolve to an LGA is UNVERIFIABLE and skipped rather than passed or failed,
    because every statewide instrument has a NULL council and failing them all
    would just get the gate switched off.
    """
    from validate_zone_code_validity import load_ground_truth, load_slug_resolution

    cur = supa_conn.cursor()
    truth = load_ground_truth(cur)
    slug_key = load_slug_resolution(cur, truth)

    bad = []
    for row in data:
        council = row.get('source_council')
        key = slug_key.get(council)
        if not key:
            continue
        allowed = truth.get(key, set())
        offending = sorted({
            z.upper() for z in (row.get('v2_applicable_zones') or [])
            if isinstance(z, str) and z != 'ALL' and z.upper() not in allowed
        })
        if offending:
            bad.append((row['id'], council, offending))
    return bad

def sync_to_supabase(supa_conn, data):
    """Sync v2_ data to Supabase by updating existing rows."""
    cur = supa_conn.cursor()

    # Build UPDATE query
    set_clauses = ', '.join([f"{col} = data.{col}" for col in V2_COLUMNS])
    columns_str = ', '.join(['id'] + V2_COLUMNS)

    updated = 0
    errors = 0

    for row in data:
        try:
            # Build values for this row
            values = [row['id']]
            for col in V2_COLUMNS:
                val = row.get(col)
                values.append(val)

            # Create parameterized UPDATE
            set_parts = []
            params = []
            for i, col in enumerate(V2_COLUMNS):
                set_parts.append(f"{col} = %s")
                params.append(row.get(col))
            params.append(row['id'])  # For WHERE clause

            sql = f"""
                UPDATE regulatory_provisions
                SET {', '.join(set_parts)}
                WHERE id = %s
            """
            cur.execute(sql, params)
            updated += 1

            if updated % 100 == 0:
                print(f"    Updated {updated} rows...")
                supa_conn.commit()

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    Error on id {row['id']}: {e}")

    supa_conn.commit()
    print(f"  Synced {updated} provisions to Supabase ({errors} errors)")
    return updated, errors

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written to production.")
    args = ap.parse_args()

    print("=" * 60)
    print("SYNC V2_ COLUMNS TO SUPABASE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Export from local
    print("\n1. Connecting to LOCAL database...")
    local_conn = get_local_connection()
    print("   Connected")

    print("\n2. Exporting v2_ enriched provisions...")
    data = export_v2_data(local_conn)
    local_conn.close()

    if not data:
        print("   No enriched provisions found. Nothing to sync.")
        sys.exit(0)

    # Import to Supabase
    print("\n3. Connecting to SUPABASE database...")
    supa_conn = get_supabase_connection()
    print("   Connected")

    # THE GATE, before anything is written and before anyone is asked to type
    # "yes". A confirmation prompt asks whether the operator MEANT to run it;
    # it cannot tell them the payload is wrong, and on 2026-09-24 it was: 200
    # of these rows carried zone codes the 2022 employment-zone reform retired.
    print("\n4. Checking zone codes against the TARGET's land-use tables...")
    bad = rows_with_retired_zones(supa_conn, data)
    if bad:
        by_shape = {}
        for pid, council, zones in bad:
            by_shape.setdefault((council, tuple(zones)), []).append(pid)
        print(f"   {len(bad):,} row(s) carry a zone code not in their LGA's table:")
        for (council, zones), ids in sorted(
                by_shape.items(), key=lambda kv: -len(kv[1]))[:15]:
            print(f"     {len(ids):6,} row(s)  {council}: {list(zones)}"
                  f"   e.g. id={ids[0]}")
        print(f"\nERROR: nothing was written. v2_applicable_zones is a HARD "
              f"filter on the served answer, so syncing a retired code DELETES "
              f"each of these rows from every answer for the successor zone. "
              f"Repair the mirror first -- scripts/validate_zone_code_validity.py "
              f"names the rule, scripts/backfill_invalid_zone_codes.py applies it.",
              file=sys.stderr)
        supa_conn.close()
        sys.exit(2)
    print("   clean")

    if not args.apply:
        print(f"\nDRY RUN — {len(data):,} rows would be synced, nothing written. "
              f"Re-run with --apply to execute.")
        supa_conn.close()
        sys.exit(0)

    print("\nThis will UPDATE v2_ columns in Supabase production database.")
    print("Make sure you have run the migration first:")
    print("  psql $SUPABASE_DB_URL -f migrations/001_add_v2_columns.sql")
    print()

    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        supa_conn.close()
        sys.exit(0)

    print("\n5. Syncing to Supabase...")
    updated, errors = sync_to_supabase(supa_conn, data)
    supa_conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print(f"  Updated: {updated} provisions")
    print(f"  Errors: {errors}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Suggest verification
    print("\nVerify sync by running:")
    print("  python scripts/compare_local_supabase.py")

if __name__ == "__main__":
    main()
