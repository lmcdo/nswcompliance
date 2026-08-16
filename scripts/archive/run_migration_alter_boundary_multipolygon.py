#!/usr/bin/env python3
"""
Migration: ALTER dcp_precinct_boundaries.boundary from POLYGON to MULTIPOLYGON
===============================================================================
Converts the column type in place using ST_Multi() to wrap existing Polygon rows.
Safe to run multiple times (idempotent — checks current type first).

Run this BEFORE import_cos_dcp_boundaries.py.

Usage:
    python3 scripts/run_migration_alter_boundary_multipolygon.py
    python3 scripts/run_migration_alter_boundary_multipolygon.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Check current column type
    cur.execute("""
        SELECT type, coord_dimension
        FROM geometry_columns
        WHERE f_table_name = 'dcp_precinct_boundaries'
          AND f_geometry_column = 'boundary'
    """)
    row = cur.fetchone()
    if row:
        current_type = row[0]
        print(f"Current boundary column type: {current_type}")
        if current_type == "MULTIPOLYGON":
            print("Already MULTIPOLYGON — nothing to do.")
            conn.close()
            return
    else:
        print("Could not determine current type from geometry_columns — proceeding anyway.")

    # Check existing row count
    cur.execute("SELECT COUNT(*) FROM dcp_precinct_boundaries")
    count = cur.fetchone()[0]
    print(f"Existing rows: {count}")

    if args.dry_run:
        print("[dry-run] Would run: ALTER TABLE dcp_precinct_boundaries ALTER COLUMN boundary TYPE GEOMETRY(MULTIPOLYGON, 4326) USING ST_Multi(boundary)")
        conn.close()
        return

    print("Altering column...")
    cur.execute("""
        ALTER TABLE dcp_precinct_boundaries
        ALTER COLUMN boundary TYPE GEOMETRY(MULTIPOLYGON, 4326)
        USING ST_Multi(boundary)
    """)
    conn.commit()

    # Also alter centroid to GEOMETRY(MULTIPOINT) is NOT needed — centroid stays POINT.
    # But we need to update the trigger function since ST_Centroid works on MultiPolygon too.

    # Verify
    cur.execute("""
        SELECT type FROM geometry_columns
        WHERE f_table_name = 'dcp_precinct_boundaries'
          AND f_geometry_column = 'boundary'
    """)
    row = cur.fetchone()
    print(f"Column type after migration: {row[0] if row else 'unknown'}")
    print("Done.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
