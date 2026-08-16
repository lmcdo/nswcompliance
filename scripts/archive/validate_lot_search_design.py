#!/usr/bin/env python3
"""Validate lot_search_index design assumptions against production DB.

All queries are READ-ONLY. Safe to run against production.
Usage: python scripts/validate_lot_search_design.py
"""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

conn = psycopg2.connect(DB_URL, options="-c statement_timeout=60000")
conn.autocommit = True
cur = conn.cursor()


def run_query(label, sql, show_plan=False):
    """Run a query, print results and timing."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    t0 = time.time()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        elapsed = (time.time() - t0) * 1000
        cols = [d[0] for d in cur.description] if cur.description else []

        if show_plan:
            for r in rows:
                print(f"  {r[0]}")
        else:
            if cols:
                # Print header
                widths = [max(len(str(c)), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
                header = " | ".join(str(c).ljust(w) for c, w in zip(cols, widths))
                print(f"  {header}")
                print(f"  {'-+-'.join('-'*w for w in widths)}")
                for r in rows:
                    line = " | ".join(str(v).ljust(w) for v, w in zip(r, widths))
                    print(f"  {line}")

        print(f"\n  [{len(rows)} rows, {elapsed:.0f}ms]")
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        print(f"  ERROR: {e} [{elapsed:.0f}ms]")


# ── TEST 1: Bbox query speed ──
run_query(
    "TEST 1: Bbox query on nsw_cadastre_lots (Inner West area)",
    """
    EXPLAIN ANALYZE
    SELECT lotidstring, planlotarea, shape_area, urbanity
    FROM nsw_cadastre_lots
    WHERE ST_Intersects(geom, ST_MakeEnvelope(151.13, -33.91, 151.19, -33.86, 4326))
    LIMIT 50
    """,
    show_plan=True,
)

# ── TEST 2: Overlay spatial join via cadastre (build script rewrite test) ──
run_query(
    "TEST 2: Zone assignment via nsw_cadastre_lots JOIN spatial_overlays (Inner West)",
    """
    EXPLAIN ANALYZE
    SELECT DISTINCT ON (c.lotidstring)
        c.lotidstring, so.value
    FROM nsw_cadastre_lots c
    JOIN spatial_overlays so ON ST_Intersects(c.geom, so.geom)
    WHERE so.layer_type = 'zone'
      AND so.lga_name = 'INNER WEST'
    ORDER BY c.lotidstring, ST_Area(ST_Intersection(c.geom, so.geom)) DESC
    LIMIT 10
    """,
    show_plan=True,
)

# ── TEST 3: Table sizes ──
run_query(
    "TEST 3: Table sizes",
    """
    SELECT
        relname AS table_name,
        pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
        pg_size_pretty(pg_relation_size(c.oid)) AS data_size,
        pg_size_pretty(pg_indexes_size(c.oid)) AS index_size,
        reltuples::bigint AS approx_rows
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND relname IN ('nsw_cadastre_lots', 'spatial_overlays', 'dcp_setback_controls',
                      'regulatory_provisions', 'development_applications',
                      'complying_development_certificates')
    ORDER BY pg_total_relation_size(c.oid) DESC
    """,
)

# ── TEST 3b: DB size ──
run_query(
    "TEST 3b: Total database size",
    "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size",
)

# ── TEST 3c: Average geometry size ──
run_query(
    "TEST 3c: Average geometry size in nsw_cadastre_lots (sampled)",
    """
    SELECT
        pg_size_pretty(avg(pg_column_size(geom))::bigint) AS avg_geom_size,
        pg_size_pretty((avg(pg_column_size(geom)) * 3220617)::bigint) AS est_total_geom_all_nsw,
        count(*) AS sample_size
    FROM (SELECT geom FROM nsw_cadastre_lots TABLESAMPLE SYSTEM(0.1)) sample
    """,
)

# ── TEST 4: Lot counts per DCP LGA ──
run_query(
    "TEST 4: Lot counts per DCP LGA (may take 30-60s)",
    """
    SELECT
        so.lga_name,
        COUNT(DISTINCT c.lotidstring) AS lot_count
    FROM nsw_cadastre_lots c
    JOIN spatial_overlays so ON ST_Intersects(c.geom, so.geom)
    WHERE so.layer_type = 'zone'
      AND so.lga_name IN (
          SELECT DISTINCT UPPER(REPLACE(lga_slug, '_', ' '))
          FROM dcp_setback_controls
          WHERE is_current = TRUE
      )
    GROUP BY so.lga_name
    ORDER BY lot_count DESC
    """,
)

# ── TEST 5: NSW overlay coverage ──
run_query(
    "TEST 5: LGAs with zone data in spatial_overlays",
    """
    SELECT
        COUNT(DISTINCT lga_name) AS lgas_with_zones,
        COUNT(*) AS total_zone_overlays
    FROM spatial_overlays
    WHERE layer_type = 'zone'
    """,
)

# ── TEST 5b: All LGAs with zone data ──
run_query(
    "TEST 5b: All LGAs with zone data (count per LGA)",
    """
    SELECT lga_name, COUNT(*) AS zone_count
    FROM spatial_overlays
    WHERE layer_type = 'zone' AND lga_name IS NOT NULL
    GROUP BY lga_name
    ORDER BY zone_count DESC
    """,
)

# ── TEST 6: GIST indexes ──
run_query(
    "TEST 6: GIST indexes on key tables",
    """
    SELECT tablename, indexname
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND tablename IN ('nsw_cadastre_lots', 'spatial_overlays')
      AND indexdef ILIKE '%%gist%%'
    ORDER BY tablename, indexname
    """,
)

# ── TEST 7: DCP LGA slugs ──
run_query(
    "TEST 7: DCP setback controls by LGA",
    """
    SELECT lga_slug, COUNT(*) AS control_count
    FROM dcp_setback_controls
    WHERE is_current = TRUE
    GROUP BY lga_slug
    ORDER BY control_count DESC
    """,
)

# ── TEST 8: Scalar storage estimate ──
run_query(
    "TEST 8: Estimated scalar-only storage (no geometry)",
    """
    SELECT
        pg_size_pretty(avg(
            coalesce(pg_column_size(lotidstring), 0) +
            coalesce(pg_column_size(planlotarea), 0) +
            coalesce(pg_column_size(shape_area), 0) +
            coalesce(pg_column_size(urbanity), 0)
        )::bigint) AS avg_scalar_row_size,
        pg_size_pretty((avg(
            coalesce(pg_column_size(lotidstring), 0) +
            coalesce(pg_column_size(planlotarea), 0) +
            coalesce(pg_column_size(shape_area), 0) +
            coalesce(pg_column_size(urbanity), 0)
        ) * 3220617)::bigint) AS est_scalar_all_nsw,
        count(*) AS sample_size
    FROM (SELECT * FROM nsw_cadastre_lots TABLESAMPLE SYSTEM(0.1)) sample
    """,
)

conn.close()
print(f"\n{'='*70}")
print("  ALL TESTS COMPLETE")
print(f"{'='*70}")
