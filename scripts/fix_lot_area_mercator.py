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

WHY THERE IS NO WHOLE-TABLE PROGRESS QUERY
------------------------------------------
Three runs died on the statement timeout, and the third died on the query that
was only there to FIND the resume point. Any predicate of the form
``lot_area_m2 IS DISTINCT FROM ST_Area(geom::geography)`` over the full target
set computes geodesic area for ~2.5M polygons, and it gets slower as the run
proceeds because each repaired row leaves a dead tuple behind for the scan to
step over. Raising statement_timeout does not save it -- 300s was tried and
also expired. So progress is tracked by a CURSOR FILE, which costs nothing,
and the run never asks the database a whole-table question.

ROLLBACK
--------
No CSV -- 2.5M rows of it would be unusable. The previous value is exactly
``nsw_cadastre_lots.shape_area``, a column this script never writes to, so the
old state is fully reconstructible:

    UPDATE lot_search_index l SET lot_area_m2 = c.shape_area
      FROM nsw_cadastre_lots c
     WHERE c.lotidstring = l.lotidstring AND c.planlotarea IS NULL;

USAGE
    python scripts/fix_lot_area_mercator.py --dry-run
    python scripts/fix_lot_area_mercator.py --apply
    python scripts/fix_lot_area_mercator.py --apply --restart   # ignore cursor
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras

#: The batch size is ADAPTIVE, because two fixed guesses both died.
#:
#: Writing a row here costs ~5.5ms, not the ~1.8ms first assumed: lot_area_m2
#: appears in three indexes (idx_lsi_area, idx_lsi_lga_zone_area,
#: idx_lsi_zone_area_gfa), so each row rewrites three index entries and the
#: update cannot be HOT. Measured batch times at 20,000 rows climbed 13s, 10s,
#: 47s, 85s, 99s, 103s as the run moved from already-repaired rows into
#: unrepaired ones -- then past the cap. So rather than guess a third time,
#: aim at a wall-clock target and let the loop find its own size.
#: With the cursor bound on both sides of the join (see the batch query) the
#: per-batch cost is once again proportional to rows, so growing the batch
#: genuinely helps. It did not before, which is what made the earlier
#: shrink-on-slow behaviour actively harmful.
BATCH_START = 20_000
BATCH_MIN = 500
BATCH_MAX = 50_000
TARGET_LOW_S = 30.0
TARGET_HIGH_S = 70.0

#: Raised from the 120s default. Verified settable on this connection (SHOW
#: reported 5min), so a slow batch degrades into a retry rather than a death.
STATEMENT_TIMEOUT_MS = 300_000

#: Where the keyset cursor lives between runs. Kill the script at any point and
#: the next run resumes from the last committed batch instead of re-scanning.
CURSOR_FILE = Path(
    os.environ.get("LOT_AREA_FIX_CURSOR_FILE", ".lot_area_fix_cursor")
)


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set. Source the repo-root .env first.")
    return psycopg2.connect(url, connect_timeout=25)


def load_cursor() -> str:
    if CURSOR_FILE.exists():
        return CURSOR_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_cursor(value: str) -> None:
    CURSOR_FILE.write_text(value, encoding="utf-8")


def target_count(cur) -> int:
    """How many rows are in scope at all.

    Deliberately does NOT evaluate ST_Area: this is a plain join on
    planlotarea IS NULL, which stays affordable. The count of rows still
    holding the wrong value is the expensive question and is not asked --
    see the module docstring.
    """
    cur.execute(
        """
        SELECT count(*) AS n
          FROM lot_search_index l
          JOIN nsw_cadastre_lots c ON c.lotidstring = l.lotidstring
         WHERE c.planlotarea IS NULL
           AND l.geom IS NOT NULL
        """
    )
    return cur.fetchone()["n"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="Counts only, no writes.")
    g.add_argument("--apply", action="store_true", help="Perform the repair.")
    ap.add_argument("--restart", action="store_true",
                    help="Ignore any saved cursor and start from the beginning.")
    args = ap.parse_args()

    conn = connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")

    if args.dry_run:
        print(f"rows in scope (planlotarea IS NULL): {target_count(cur):,}")
        print(f"saved cursor: {load_cursor() or '(none — would start at the beginning)'}")
        print("\nDRY RUN — nothing written.")
        conn.close()
        return 0

    cursor = "" if args.restart else load_cursor()
    inclusive = False
    if cursor:
        print(f"resuming from saved cursor {cursor}")
    else:
        print("starting from the beginning of the key order")

    print(f"APPLYING, adaptive batch from {BATCH_START:,} "
          f"(target {TARGET_LOW_S:.0f}-{TARGET_HIGH_S:.0f}s/batch)...")
    total = 0
    scanned = 0
    batch = BATCH_START
    t0 = time.time()

    while True:
        # KEYSET PAGINATION, and the reason matters.
        #
        # The first version selected candidates with
        # ``lot_area_m2 IS DISTINCT FROM ST_Area(...) LIMIT 50000`` and no
        # cursor, so every batch scanned PAST the rows it had already repaired
        # and batch cost grew with progress. Walking the primary key instead
        # makes each batch a bounded index range whatever has gone before.
        #
        # The consequence: the cursor must advance over EVERY row in scope, so
        # already-repaired rows cannot be filtered out of the candidate SELECT
        # -- a fully-repaired range would return 0 and read as "finished". The
        # skip belongs in the UPDATE's WHERE, where it saves the write without
        # stalling the cursor.
        #
        # geom IS NOT NULL is load-bearing, not decoration: without it a row
        # with no geometry would take ST_Area(NULL) = NULL and have its area
        # blanked. There are no such rows today; the invariant should not
        # depend on that staying true.
        sql = f"""
            WITH todo AS (
                SELECT l.lotidstring,
                       ST_Area(l.geom::geography) AS true_area
                  FROM lot_search_index l
                  JOIN nsw_cadastre_lots c ON c.lotidstring = l.lotidstring
                 WHERE c.planlotarea IS NULL
                   AND l.geom IS NOT NULL
                   AND l.lotidstring {'>=' if inclusive else '>'} %s
                   -- THE SAME BOUND ON BOTH SIDES, and it is not redundant.
                   -- The join is a merge of two lotidstring index scans. With
                   -- the bound on l alone, the cadastre side still began at
                   -- the start of its index and fast-forwarded to the cursor
                   -- on EVERY batch -- a cost that grew as the cursor advanced
                   -- and was identical for a 500-row batch and a 20,000-row
                   -- one (~70s either way). That is why shrinking the batch
                   -- cut throughput 16x for no saving. Measured 2026-08-10:
                   -- 60,271ms to the first row without this line, 331ms for
                   -- the whole 20,000 with it. The join key is UNIQUE, so
                   -- c.lotidstring = l.lotidstring and bounding both is
                   -- semantically free -- it only lets the planner seek.
                   AND c.lotidstring {'>=' if inclusive else '>'} %s
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
        """
        t_batch = time.time()
        try:
            cur.execute(sql, (cursor, cursor, batch))
        except psycopg2.errors.QueryCanceled:
            # A timeout is information, not a failure: this batch was too big
            # for the current stretch of the table. Roll back, halve, retry the
            # SAME cursor. Dying here is what cost the earlier runs.
            conn.rollback()
            if batch <= BATCH_MIN:
                print(f"  ! timeout at the minimum batch of {BATCH_MIN:,} — "
                      f"stopping rather than spinning.", flush=True)
                raise
            batch = max(BATCH_MIN, batch // 2)
            print(f"  ! batch timed out — retrying at {batch:,}", flush=True)
            continue

        row = cur.fetchone()
        conn.commit()
        elapsed = time.time() - t_batch

        seen = row["seen"]
        total += row["written"]
        scanned += seen
        if row["next_cursor"] is not None:
            cursor = row["next_cursor"]
            inclusive = False
            save_cursor(cursor)      # only after the commit it describes
        if seen:
            rate = scanned / max(time.time() - t0, 0.001)
            print(f"  scanned {scanned:,} / written {total:,} "
                  f"({rate:,.0f} rows/s, batch {batch:,} in {elapsed:.0f}s)",
                  flush=True)
        if seen < batch:
            break

        # Steer toward the target window. Grow gently, shrink hard -- an
        # oversized batch costs a whole wasted attempt, an undersized one only
        # costs a little overhead.
        if elapsed < TARGET_LOW_S:
            batch = min(BATCH_MAX, int(batch * 1.5))
        elif elapsed > TARGET_HIGH_S:
            batch = max(BATCH_MIN, int(batch * 0.6))

    print(f"\nDONE — reached the end of the key order.")
    print(f"  rows scanned in scope : {scanned:,}")
    print(f"  rows rewritten        : {total:,}")
    print("  (rows already correct from an earlier run are scanned but not "
          "rewritten, so 'rewritten' counts only this run's work.)")
    if CURSOR_FILE.exists():
        CURSOR_FILE.unlink()
        print(f"  cleared {CURSOR_FILE}")

    print("\nNEXT, deliberately and separately:")
    print("  python scripts/build_lot_search_index.py --phase compute "
          "--all-lgas --trigger lot_area_mercator_fix")
    print("  (no --recompute: that would also redo the ~600k lots that were "
          "always correct)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
