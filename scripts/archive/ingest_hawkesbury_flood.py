#!/usr/bin/env python3
"""
Ingest Hawkesbury-Nepean River Flood Study (May 2024) flood extents into spatial_overlays.

Source: https://data.nsw.gov.au/data/dataset/2024-hawkesbury-nepean-river-flood-study
Data: flood-extents.zip — 12 AEP scenario shapefiles (vector polygons)
CRS input: EPSG:7856 (GDA2020 / MGA Zone 56) → reprojected to EPSG:4326

Stored as:
  layer_type = 'flood'
  instrument_key = 'HNRFS_2024_<SCENARIO>'  (e.g. HNRFS_2024_100AEP)
  value = '<SCENARIO>'                        (e.g. '100AEP', 'PMF')
  lga_name = 'HAWKESBURY'                    (primary council; study also covers Penrith, The Hills, Wollondilly)
  currency_date = 2024-05-01
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from shapely.geometry import mapping
import json

load_dotenv()

EXTENTS_DIR = project_root / "data" / "hawkesbury_flood" / "extents" / "Flood Extents"
LGA_NAME = "HAWKESBURY"
CURRENCY_DATE = date(2024, 5, 1)

# AEP scenario → display label and numeric ARI (1-in-N years)
# AEP = Annual Exceedance Probability; 100AEP = 1% AEP = 1-in-100-year event
SCENARIO_MAP = {
    # X in XAEP = ARI (average recurrence interval) in years.
    # AEP% = 1/ARI × 100. Example: 20AEP → ARI=20yr → AEP=5%.
    "2AEP":    ("50% AEP (1-in-2 year)",     2),
    "5AEP":    ("20% AEP (1-in-5 year)",     5),
    "10AEP":   ("10% AEP (1-in-10 year)",   10),
    "20AEP":   ("5% AEP (1-in-20 year)",    20),
    "50AEP":   ("2% AEP (1-in-50 year)",    50),
    "100AEP":  ("1% AEP (1-in-100 year)",  100),
    "200AEP":  ("0.5% AEP (1-in-200 year)", 200),
    "500AEP":  ("0.2% AEP (1-in-500 year)", 500),
    "1000AEP": ("0.1% AEP (1-in-1000 year)", 1000),
    "2000AEP": ("0.05% AEP (1-in-2000 year)", 2000),
    "5000AEP": ("0.02% AEP (1-in-5000 year)", 5000),
    "PMF":     ("Probable Maximum Flood (PMF)", 999999),
}


def scenario_from_filename(path: Path) -> str | None:
    """Extract scenario key (e.g. '100AEP', 'PMF') from shapefile name."""
    name = path.stem
    # Match DesignXXXAEP or DesignPMF
    m = re.search(r"Design(\d+AEP|PMF)", name, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def geom_to_wkt_4326(geom_7856) -> str:
    """Convert a shapely geometry from EPSG:7856 to WKT in EPSG:4326."""
    from pyproj import Transformer
    from shapely.ops import transform as shp_transform

    transformer = Transformer.from_crs("EPSG:7856", "EPSG:4326", always_xy=True)

    def _transform(x, y, z=None):
        return transformer.transform(x, y)

    return shp_transform(_transform, geom_7856).wkt


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    shapefiles = sorted(EXTENTS_DIR.glob("*.shp"))
    if not shapefiles:
        print(f"ERROR: No shapefiles found in {EXTENTS_DIR}")
        sys.exit(1)

    print(f"Found {len(shapefiles)} shapefiles")

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    total_inserted = 0

    try:
        for shp_path in shapefiles:
            scenario = scenario_from_filename(shp_path)
            if not scenario:
                print(f"  [skip] cannot parse scenario from {shp_path.name}")
                continue

            label, ari = SCENARIO_MAP.get(scenario, (scenario, None))
            instrument_key = f"HNRFS_2024_{scenario}"

            print(f"\n[{scenario}] {shp_path.name}")
            gdf = gpd.read_file(shp_path)
            print(f"  {len(gdf)} features, CRS={gdf.crs}")

            if len(gdf) == 0:
                print("  [skip] empty")
                continue

            # Reproject to WGS84
            gdf = gdf.to_crs("EPSG:4326")

            has_fid = "fid_1" in gdf.columns
            rows = []
            for idx, row in gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                if has_fid and row["fid_1"] is not None:
                    source_oid = int(row["fid_1"])
                else:
                    source_oid = int(idx) + 1  # 1-based row index
                rows.append((
                    instrument_key,
                    LGA_NAME,
                    "flood",
                    scenario,          # value = scenario key e.g. "100AEP"
                    float(ari) if ari else None,  # value_numeric = ARI in years
                    CURRENCY_DATE,
                    source_oid,
                    geom.wkt,
                ))

            if not rows:
                print("  [skip] no valid rows")
                continue

            execute_values(
                cur,
                """
                INSERT INTO spatial_overlays
                    (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
                VALUES %s
                ON CONFLICT (instrument_key, layer_type, source_oid) DO UPDATE
                    SET value = EXCLUDED.value,
                        value_numeric = EXCLUDED.value_numeric,
                        currency_date = EXCLUDED.currency_date,
                        geom = EXCLUDED.geom,
                        synced_at = now()
                """,
                rows,
                template="(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)), now())",
            )
            conn.commit()
            print(f"  Upserted {len(rows)} features (instrument_key={instrument_key})")
            total_inserted += len(rows)

        print(f"\n[DONE] Total upserted: {total_inserted}")

        # Verify
        cur.execute(
            "SELECT value, MIN(value_numeric) as ari, COUNT(*) FROM spatial_overlays WHERE layer_type='flood' AND lga_name='HAWKESBURY' GROUP BY value ORDER BY MIN(value_numeric)"
        )
        print("\n[HAWKESBURY FLOOD COUNTS]")
        for r in cur.fetchall():
            print(f"  {r[0]}: {r[1]} polygons")

        cur.execute("SELECT COUNT(*) FROM spatial_overlays WHERE layer_type='flood'")
        print(f"\nTotal flood features in spatial_overlays: {cur.fetchone()[0]}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
