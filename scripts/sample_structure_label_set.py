#!/usr/bin/env python3
# prior-art-checked: four sweeps, 2026-08-08 against origin/main af7982a8.
# (1) DB: no table matching %label%/%ground%/%annot%/%truth%/%calibrat% exists.
# (2) Frontend: /internal holds only dcp-review and setback-review, both text
#     queues over existing rows; neither samples anything and neither shows
#     imagery. (3) Python: `git ls-tree | grep -iE "scripts/.*(label|recall|
#     ground_truth|annotate|sample)"` returns only repair_dq41_null_label_
#     derived_dates.py, an unrelated date repair. (4) Plans: the calibration
#     plan lists granny-flat recall as "blocked -- needs the user to hand-label
#     ~50-100 blocks; no other source of truth exists with zero users", i.e.
#     the tooling was never built. This is that tooling.
"""Draw a reproducible sample of lots for human structure labelling.

WHY A SCRIPT AND NOT A HAND-PICKED LIST
---------------------------------------
The number this feeds is detection recall -- how often the imagery scan misses
a structure that is really there. A sample chosen by a person who has already
seen the detector's output is worthless, because the choice itself encodes the
answer. So the sample is drawn:

  * BEFORE anyone looks at any tile,
  * from a filter written down here rather than applied by eye,
  * ordered by md5(lotidstring || seed) so the same seed always yields the
    same lots and a reader can re-run it and get the identical set.

The seed and the method string are stored on every row, so the sample can be
audited later without trusting anyone's memory of how it was drawn.

THE LGA NAME TRAP (measured, not assumed)
-----------------------------------------
Three tables spell the same council three ways:

    lot_search_index.lga_name    'INNER WEST'      (upper case)
    lga_registry.display_name    'Inner West'      (title case)
    dcp_setback_controls.lga     'inner_west'      (lower snake)

Filtering lot_search_index on 'Inner West' returns ZERO rows and looks like a
legitimately empty result. Five councils also fail the obvious
upper(replace(slug,'_',' ')) rule and need the explicit map below.

And one genuine trap: 'NORTH SYDNEY' is a different council that also matches
LIKE '%SYDNEY%'. Matching is exact equality here, never LIKE.

USAGE
    python scripts/sample_structure_label_set.py --dry-run          # default
    python scripts/sample_structure_label_set.py --write            # insert
    python scripts/sample_structure_label_set.py --n 120 --seed 7 --write
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import psycopg2
import psycopg2.extras

# --- LGA slug -> lot_search_index.lga_name -------------------------------
# 20 of 25 resolve by rule; these 5 do not. Verified live 2026-08-08 by
# counting matching lots for each: the rule returns 0 for every entry here.
LGA_NAME_OVERRIDES: dict[str, str] = {
    "canterbury_bankstown": "CANTERBURY-BANKSTOWN",
    "ku_ring_gai": "KU-RING-GAI",
    "city_of_sydney": "SYDNEY",          # NOT 'NORTH SYDNEY' -- different council
    "the_hills": "THE HILLS SHIRE",
    "parramatta": "CITY OF PARRAMATTA",
}


def lga_slug_to_index_name(slug: str) -> str:
    """Map a council slug to the exact lot_search_index.lga_name string.

    Exact equality only. A LIKE match here would pull 'NORTH SYDNEY' into a
    'SYDNEY' sample.
    """
    if slug in LGA_NAME_OVERRIDES:
        return LGA_NAME_OVERRIDES[slug]
    return slug.replace("_", " ").upper()


# Councils to sample from. Deliberately a spread of built form rather than the
# densest or the easiest: inner-city terraces, post-war suburban, large-lot
# leafy, and greenfield. Detection difficulty varies with tree cover and lot
# size, so a sample from one of these alone would not generalise.
DEFAULT_LGAS = [
    "inner_west",            # dense terrace, small lots, heavy street trees
    "canterbury_bankstown",  # post-war suburban, mixed
    "ku_ring_gai",           # large lots, very heavy canopy -- the hard case
    "blacktown",             # newer suburban, open, larger yards
]

# Residential zones only. A structure on industrial or rural land is a
# different detection problem and is not what this product answers.
#
# noqa: zone-codes -- suppressed deliberately, with the reason. The DQ-30 rule
# targets REGULATORY LOOKUP tables that decide a user's answer and go stale
# when an LEP is amended. This is neither: it is the scope of a research
# sample. It decides which lots a human is asked to look at, is served to
# nobody, and determines no one's compliance outcome. If NSW introduced a new
# residential zone tomorrow the consequence here is that the sample would not
# include it -- a stated limitation, not a wrong answer.
# Checked before suppressing: shared/zone-taxonomy.json holds only
# legacyToCurrentAliases and legacyZones, and enrichment/config/zone_taxonomy.py
# exposes get_zone_aliases / is_legacy_zone / get_current_zone. Neither offers a
# "which zones are residential" grouping, so there is nothing to import.
DEFAULT_ZONES = ["R1", "R2", "R3"]

# Lot size band. Below ~300 m2 there is rarely room for a secondary structure;
# above ~1200 m2 the tile framing starts to clip the lot, which would measure
# the tile, not the detector.
DEFAULT_MIN_AREA = 300.0
DEFAULT_MAX_AREA = 1200.0

SAMPLE_METHOD = (
    "stratified: zone in {zones}, lot_area_m2 in [{lo},{hi}], "
    "lga in {lgas}; ordered by md5(lotidstring || seed); "
    "equal quota per LGA"
)


def _connect():
    """Read the same PG* credentials the rest of the repo uses."""
    host = os.environ.get("PGHOST") or os.environ.get("DB_HOST")
    if not host:
        sys.exit(
            "No database credentials. Source the repo-root .env (PGHOST/PGUSER/"
            "PGPASSWORD/PGDATABASE) before running."
        )
    return psycopg2.connect(
        host=host,
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER") or os.environ.get("DB_USER"),
        password=os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD"),
        dbname=os.environ.get("PGDATABASE") or os.environ.get("DB_NAME", "postgres"),
        sslmode=os.environ.get("PGSSLMODE", "require"),
        connect_timeout=20,
    )


def draw_sample(
    conn,
    lgas: list[str],
    zones: list[str],
    seed: int,
    n_total: int,
    min_area: float,
    max_area: float,
) -> list[dict]:
    """Return n_total lots, split as evenly as possible across `lgas`.

    Per-LGA quota rather than one global ORDER BY, because a single global
    ordering would let the largest council dominate the sample purely by
    having more lots.
    """
    per_lga = max(1, n_total // len(lgas))
    remainder = n_total - per_lga * len(lgas)

    rows: list[dict] = []
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # 16.5s measured for one LGA-set at LIMIT 100 (EXPLAIN ANALYZE, 2026-08-08).
    # Raise the ceiling so a multi-LGA draw cannot be cut off mid-way.
    cur.execute("SET statement_timeout = '180s'")

    for i, slug in enumerate(lgas):
        quota = per_lga + (1 if i < remainder else 0)
        index_name = lga_slug_to_index_name(slug)
        cur.execute(
            """
            SELECT lotidstring,
                   lga_name,
                   zone_code,
                   lot_area_m2,
                   ST_Y(ST_Centroid(geom)) AS lat,
                   ST_X(ST_Centroid(geom)) AS lng
            FROM lot_search_index
            WHERE lga_name = %s
              AND zone_code = ANY(%s)
              AND lot_area_m2 BETWEEN %s AND %s
              AND geom IS NOT NULL
            ORDER BY md5(lotidstring || %s)
            LIMIT %s
            """,
            (index_name, zones, min_area, max_area, str(seed), quota),
        )
        got = cur.fetchall()
        # A council that returns nothing is reported, never silently dropped --
        # a silently short sample is how a biased set gets called complete.
        if not got:
            print(
                f"  !! {slug} ({index_name}): 0 lots matched. Check the name "
                f"mapping before trusting this sample.",
                file=sys.stderr,
            )
        elif len(got) < quota:
            print(
                f"  !  {slug} ({index_name}): {len(got)} of {quota} requested",
                file=sys.stderr,
            )
        for r in got:
            r["lga_slug"] = slug
            rows.append(dict(r))
    cur.close()
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-id", default="gf-recall-001",
                    help="Name for this sampling run; rows carry it.")
    ap.add_argument("--seed", type=int, default=42,
                    help="Ordering seed. Same seed = same lots.")
    ap.add_argument("--n", type=int, default=100, help="Total lots to draw.")
    ap.add_argument("--lgas", nargs="*", default=DEFAULT_LGAS)
    ap.add_argument("--zones", nargs="*", default=DEFAULT_ZONES)
    ap.add_argument("--min-area", type=float, default=DEFAULT_MIN_AREA)
    ap.add_argument("--max-area", type=float, default=DEFAULT_MAX_AREA)
    ap.add_argument("--write", action="store_true",
                    help="Insert into structure_labels. Default is dry-run.")
    args = ap.parse_args()

    method = SAMPLE_METHOD.format(
        zones=",".join(args.zones), lo=args.min_area, hi=args.max_area,
        lgas=",".join(args.lgas),
    )

    print(f"sample_id : {args.sample_id}")
    print(f"seed      : {args.seed}")
    print(f"method    : {method}")
    print(f"mode      : {'WRITE' if args.write else 'DRY-RUN (no insert)'}")
    print()

    conn = _connect()
    if not args.write:
        conn.set_session(readonly=True, autocommit=True)

    rows = draw_sample(
        conn, args.lgas, args.zones, args.seed, args.n,
        args.min_area, args.max_area,
    )

    print(f"\ndrew {len(rows)} lots:")
    by_lga: dict[str, int] = {}
    for r in rows:
        by_lga[r["lga_slug"]] = by_lga.get(r["lga_slug"], 0) + 1
    for slug, n in sorted(by_lga.items()):
        print(f"  {slug:24} {n:4}")

    if not rows:
        print("\nNOTHING DRAWN -- not writing. Check the LGA name mapping.",
              file=sys.stderr)
        return 1

    if not args.write:
        print("\nDry run. Re-run with --write to insert.")
        print("First 3 rows:")
        for r in rows[:3]:
            print(f"  {r['lotidstring']:22} {r['lga_name']:22} "
                  f"{r['zone_code']:4} {r['lot_area_m2']:8.0f} m2  "
                  f"{r['lat']:.5f},{r['lng']:.5f}")
        return 0

    # Address is the natural key the labelling UI shows and the uniqueness
    # constraint uses. lot_search_index has no address column, so the lot id
    # stands in until the UI resolves one; it is stable and unambiguous.
    cur = conn.cursor()
    inserted = 0
    for r in rows:
        cur.execute(
            """
            INSERT INTO structure_labels
                (sample_id, sample_seed, sample_method, address, lat, lng,
                 lotidstring, lga_name, zone_code, lot_area_m2, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            ON CONFLICT (sample_id, address) DO NOTHING
            """,
            (args.sample_id, args.seed, method, r["lotidstring"],
             r["lat"], r["lng"], r["lotidstring"], r["lga_name"],
             r["zone_code"], r["lot_area_m2"]),
        )
        inserted += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    print(f"\ninserted {inserted} new rows "
          f"({len(rows) - inserted} already present -- re-running is safe)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
