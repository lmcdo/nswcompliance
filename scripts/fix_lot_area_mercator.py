#!/usr/bin/env python3
# prior-art-checked: no existing repair script touches lot_search_index.lot_area_m2.
# Sweeps 2026-08-10 against main b5a4c1cf: scripts/ holds build_lot_search_index.py
# (the builder, whose area source is fixed in this same branch) and
# build_cdc_lot_link.py (reads the column, never writes it); services/lot_search.py
# only SELECTs it; no migration alters it.
"""Repair lot_search_index.lot_area_m2 where it came from a Web Mercator area.

THE DEFECT
----------
build_lot_search_index.py filled the column with
``COALESCE(c.planlotarea, c.shape_area)``. ``planlotarea`` is the surveyed
figure and is correct. ``shape_area`` is an area computed on the flat Web
Mercator projection, which stretches distance by 1/cos(latitude) and therefore
area by 1/cos^2(latitude) -- about +45% in Sydney and worse further south.

Measured over a 5,000-lot sample of nsw_cadastre_lots on 2026-08-10:

    planlotarea / true                 1.0003
    shape_area  / true                 1.4390
    shape_area * cos^2(lat) / true     1.0028   <- identifies the projection

686,145 of 3,220,617 cadastre lots carry a planlotarea. The other 79% took the
inflated fallback.

WHAT THIS CHANGES AND WHAT IT DOES NOT
--------------------------------------
Only rows whose area came from the fallback -- ``planlotarea IS NULL``. Rows
carrying a surveyed area are already correct and are never touched, so a bad
run cannot damage them.

It does NOT recompute the ca_* capacity columns, which were derived from the
inflated area. Those are marked stale by setting computed_at = NULL, and the
recompute is a separate, deliberate run:

    python scripts/build_lot_search_index.py --phase compute --all-lgas \
        --trigger lot_area_mercator_fix

Deliberately WITHOUT --recompute. That flag resets computed_at across the whole
LGA, which would also discard and redo the ~600k lots that carry a surveyed
planlotarea and were always correct. The compute phase already selects on
computed_at IS NULL, so nulling exactly the repaired rows here targets the
recompute precisely.

Leaving computed_at set would be worse than nulling it: the table would then
hold a corrected area beside a capacity figure derived from the old one, with
nothing marking the disagreement. A null reads as "not computed", which is
true, rather than as a number that is quietly wrong.

ROLLBACK
--------
No CSV -- 2.5M rows of it would be unusable. The previous value is exactly
``nsw_cadastre_lots.shape_area``, a column this script never writes to, so the
old state is fully reconstructible:

    UPDATE lot_search_index l SET lot_area_m2 = c.shape_area
      FROM nsw_cadastre_lots c
     WHERE c.lotidstring = l.lotidstring AND c.planlotarea IS NULL;

RESUMABILITY
------------
The batch filter is ``lot_area_m2 IS DISTINCT FROM ST_Area(geom::geography)``,
so a repaired row stops matching and the pending set strictly shrinks. Killing
the script and re-running it resumes rather than repeating, and running it on
an already-clean table is a no-op. That costs a re-scan per batch (~12s per
50,000) and is worth it for a job against production.

USAGE
    python scripts/fix_lot_area_mercator.py --dry-run
    python scripts/fix_lot_area_mercator.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import psycopg2
import psycopg2.extras

#: Measured against production 2026-08-10: a 20,000-row keyset batch scans in
#: 12.3s, and writing 20,000 rows costs roughly a further 36s at the ~550
#: rows/s this table sustains -- about 48s, comfortably inside the ceiling.
#: 50,000 was tried first and is NOT safe: ~31s of scan plus ~91s of writes
#: lands past the 120s statement timeout, which is how the first run died.
BATCH = 20_000
#: Supabase's hard per-statement limit.
STATEMENT_TIMEOUT_MS = 120_000


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set. Source the repo-root .env first.")
    return psycopg2.connect(url, connect_timeout=25)


def survey(cur) -> dict:
    """Counts over the target set. Safe to call before and after the write."""
    cur.execute(
        """
        SELECT count(*) AS affected,
               count(*) FILTER (WHERE l.computed_at IS NOT NULL) AS with_capacity,
               count(*) FILTER (
                   WHERE l.lot_area_m2 IS DISTINCT FROM ST_Area(l.geom::geography)
               ) AS still_wrong
          FROM lot_search_index l
          JOIN nsw_cadastre_lots c ON c.lotidstring = l.lotidstring
         WHERE c.planlotarea IS NULL
           AND l.geom IS NOT NULL
        """
    )
    return dict(cur.fetchone())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="Counts only, no writes.")
    g.add_argument("--apply", action="store_true", help="Perform the repair.")
    args = ap.parse_args()

    conn = connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")

    before = survey(cur)
    print("BEFORE")
    print(f"  rows whose area came from shape_area : {before['affected']:,}")
    print(f"  ...still holding the wrong value     : {before['still_wrong']:,}")
    print(f"  ...with capacity derived from it     : {before['with_capacity']:,}")

    if args.dry_run:
        print("\nDRY RUN — nothing written.")
        conn.close()
        return 0

    print(f"\nAPPLYING in batches of {BATCH:,}...")
    total = 0
    scanned = 0
    cursor = ""      # sorts before every lotidstring
    t0 = time.time()
    while True:
        # KEYSET PAGINATION, and the reason matters.
        #
        # The first version selected candidates with
        # ``lot_area_m2 IS DISTINCT FROM ST_Area(...) LIMIT 50000`` and no
        # cursor. Every batch then had to scan PAST all the rows it had
        # already repaired to find 50,000 that still needed work, so batch
        # cost grew with progress and the run died on the statement timeout
        # after 250,000 rows. Walking the primary key instead makes each
        # batch a bounded index range whatever has gone before.
        #
        # The consequence: the cursor must advance over EVERY target row, so
        # the already-repaired ones cannot be filtered out of the candidate
        # SELECT -- doing that would return 0 rows for a fully-repaired range
        # and read as "finished". The skip belongs in the UPDATE's WHERE,
        # below, where it saves the write without stalling the cursor.
        #
        # geom IS NOT NULL is load-bearing, not decoration: without it a row
        # with no geometry would take ST_Area(NULL) = NULL and have its area
        # blanked. There are no such rows today; the invariant should not
        # depend on that staying true.
        cur.execute(
            """
            WITH todo AS (
                SELECT l.lotidstring,
                       ST_Area(l.geom::geography) AS true_area
                  FROM lot_search_index l
                  JOIN nsw_cadastre_lots c ON c.lotidstring = l.lotidstring
                 WHERE c.planlotarea IS NULL
                   AND l.geom IS NOT NULL
                   AND l.lotidstring > %s
                 ORDER BY l.lotidstring
                 LIMIT %s
            ), upd AS (
                UPDATE lot_search_index l
                   SET lot_area_m2 = todo.true_area,
                       computed_at = NULL
                  FROM todo
                 WHERE todo.lotidstring = l.lotidstring
                   AND l.lot_area_m2 IS DISTINCT FROM todo.true_area
                RETURNING 1
            )
            SELECT (SELECT count(*) FROM todo)  AS seen,
                   (SELECT count(*) FROM upd)   AS written,
                   (SELECT max(lotidstring) FROM todo) AS next_cursor
            """,
            (cursor, BATCH),
        )
        row = cur.fetchone()
        conn.commit()

        seen = row["seen"]
        total += row["written"]
        scanned += seen
        if row["next_cursor"] is not None:
            cursor = row["next_cursor"]
        if seen:
            rate = scanned / max(time.time() - t0, 0.001)
            print(f"  scanned {scanned:,} / written {total:,} "
                  f"({rate:,.0f} rows/s)", flush=True)
        if seen < BATCH:
            break

    after = survey(cur)
    print("\nAFTER")
    print(f"  rows updated                 : {total:,}")
    print(f"  still holding a wrong area   : {after['still_wrong']:,}   (0 = done)")
    print(f"  still holding stale capacity : {after['with_capacity']:,}"
          f"   (0 = all marked for recompute)")
    print("\nNEXT, deliberately and separately:")
    print("  python scripts/build_lot_search_index.py --phase compute "
          "--all-lgas --trigger lot_area_mercator_fix")
    print("  (no --recompute: that would also redo the ~600k lots that were "
          "always correct)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
