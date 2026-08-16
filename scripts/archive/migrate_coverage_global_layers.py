#!/usr/bin/env python3
"""
One-time migration: fix spatial_overlays_coverage for global (bbox/all) layers.

Problem:
  bushfire and anef were ingested before the 'ALL' row convention existed.
  This left 128 stale per-LGA rows for bushfire (all feature_count=0) and
  4 per-LGA rows for anef. No 'ALL' row exists for either.

  generate_conveyancing_report.py's covered_layers check queries:
    SELECT layer_type FROM spatial_overlays_coverage WHERE lga_name = <lga>
  Without a feature_count filter this returns bushfire for all 128 LGAs,
  causing the report to show "Clear (PostGIS)" for all properties — even
  LGAs where bushfire data was never properly mapped.

Fix applied:
  1. Delete stale per-LGA rows for global layers (bushfire, anef).
  2. Insert correct 'ALL' rows by counting actual spatial_overlays rows.

Run once. Idempotent.
"""
from __future__ import annotations
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
import psycopg2

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Layers ingested globally (bbox or all filter_mode) — coverage stored as 'ALL', not per-LGA.
GLOBAL_LAYERS = ["bushfire", "anef"]

def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    for layer in GLOBAL_LAYERS:
        # Count actual rows in spatial_overlays
        cur.execute("SELECT COUNT(*) FROM spatial_overlays WHERE layer_type = %s", (layer,))
        actual_count = cur.fetchone()[0]

        # Delete stale per-LGA entries
        cur.execute(
            "DELETE FROM spatial_overlays_coverage WHERE layer_type = %s AND lga_name != 'ALL'",
            (layer,),
        )
        deleted = cur.rowcount

        # Upsert correct 'ALL' row
        cur.execute("""
            INSERT INTO spatial_overlays_coverage (lga_name, layer_type, ingested_at, feature_count)
            VALUES ('ALL', %s, now(), %s)
            ON CONFLICT (lga_name, layer_type) DO UPDATE
                SET feature_count = EXCLUDED.feature_count,
                    ingested_at   = now()
        """, (layer, actual_count))

        print(f"  {layer}: deleted {deleted} stale per-LGA rows, wrote 'ALL' row with {actual_count} features")

    conn.commit()
    cur.close()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
