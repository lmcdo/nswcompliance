#!/usr/bin/env python3
"""
NSW Estuary Inundation 2025 -> spatial_overlays (layer_type='coastal_inundation').

prior-art-checked: reuses the spatial_overlays overlay contract + upsert key
(instrument_key, layer_type, source_oid) from scripts/ingest_flood_studies.py.
Large-geometry load path: bulk-copy raw polygons to a staging table via
GeoDataFrame.to_postgis, then let PostGIS transform (EPSG:28356 -> 4326) and
simplify (ST_SimplifyPreserveTopology) server-side — geometry processing in C,
not Python (the source polygons are ~0.5-0.7 MB each; Python row-by-row is too slow).

Source: "NSW Estuarine Inundation - 2025" (SEED; NSW Department of Climate Change,
Energy, the Environment and Water), CC-BY 4.0, published 2025-11-24.
SCOPE: estuarine TIDAL inundation ONLY — not open-coast/surf, not riverine flood
(that is the LEP flood layer). The renderer must scope wording to "estuarine tidal
inundation" and never imply general coastal safety.

Frequency tiers (how often land is under tidal water): f1=1 d/yr (0.274%),
f2=3.65 d/yr (1%), f3=36.5 d/yr (10%), f4=182.5 d/yr (50%). Nested (f1 largest).
PRIMARY (connected) extents only; isolated (_Iso) excluded (secondary).

Simplified server-side to SIMPLIFY_M metres = the source's own ~5 m raster
resolution (no material precision loss; nothing extra to disclose) — keeps every
report's spatial-intersection query fast/cheap.

Loads SSP3-7.0 (to match the NARCliM climate section) at 2050 and 2100.

Usage:
  python scripts/ingest_coastal_inundation.py --dry-run   # parse + spot-check, NO DB write
  python scripts/ingest_coastal_inundation.py --live      # staging load + server-side simplify upsert
"""
import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from shapely.geometry import Point
from sqlalchemy import create_engine, text

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

DATA_DIR = project_root / "data" / "coastal_inundation"
LAYER_TYPE = "coastal_inundation"
INSTRUMENT_BASE = "estuary_inund_2025_s370"
CURRENCY_DATE = "2025-11-24"          # SEED publication date (verified)
SCENARIO_LABEL = "SSP3-7.0"
SIMPLIFY_M = 5                        # metres — the source's own ~5 m resolution
SRC_EPSG = 28356
STAGING = "coastal_inundation_staging"
TIERS = {"f1": (1.0, "0.274%"), "f2": (3.65, "1%"),
         "f3": (36.5, "10%"), "f4": (182.5, "50%")}
YEARS = {2050: "y050s370", 2100: "y100s370"}


def _load_tier(stem: str, tier: str) -> gpd.GeoDataFrame:
    """Validated PRIMARY polygons in native EPSG:28356 (reproject + simplify happen server-side)."""
    extract = DATA_DIR / stem
    if not extract.exists():
        with zipfile.ZipFile(DATA_DIR / f"{stem}.zip") as z:
            z.extractall(extract)
    g = gpd.read_file(extract / f"Inund_NSW_{stem}{tier}.shp")
    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
    if (~g.geometry.is_valid).any():
        g["geometry"] = g.geometry.make_valid()
    g = g[g.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    return g


def build_frame(verbose: bool = True) -> gpd.GeoDataFrame:
    """One GeoDataFrame (native 28356) carrying the spatial_overlays columns. Asserts every
    (instrument_key, source_oid) is unique so the upsert can NEVER silently drop a polygon."""
    parts = []
    for year, stem in YEARS.items():
        for tier, (days, pct) in TIERS.items():
            g = _load_tier(stem, tier)
            ik = f"{INSTRUMENT_BASE}_y{year}_{tier}"
            val = f"{SCENARIO_LABEL} · {year} · exceeded {days} days/year ({pct})"
            oids = []
            for idx, feat in g.iterrows():
                m = re.search(r"Inund_(\d+)", str(feat.get("layer") or ""))
                oids.append(int(m.group(1)) if m else int(idx))
            if len(set(oids)) != len(oids):
                raise ValueError(f"duplicate source_oid in {ik} — upsert would drop a polygon")
            parts.append(gpd.GeoDataFrame(
                {"instrument_key": ik, "lga_name": None, "layer_type": LAYER_TYPE,
                 "value": val, "value_numeric": days, "currency_date": CURRENCY_DATE,
                 "source_oid": oids, "geometry": list(g.geometry.values)},
                crs=g.crs,
            ))
            if verbose:
                print(f"  {year} {tier} [{days} d/yr]: {len(parts[-1])} estuaries")
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=f"EPSG:{SRC_EPSG}")


def _engine():
    url = os.environ["DATABASE_URL"]
    for pfx in ("postgresql://", "postgres://"):
        if url.startswith(pfx):
            return create_engine("postgresql+psycopg2://" + url[len(pfx):])
    return create_engine(url)


def _tier_of(instrument_key: str) -> str:
    m = re.search(r"_(f\d)$", instrument_key)
    return m.group(1) if m else "?"


def spot_check(frame: gpd.GeoDataFrame):
    """In-memory two-way join check on the 2100 tiers (reproject a copy to 4326)."""
    f = frame[frame["instrument_key"].str.contains("y2100")].to_crs(4326)

    def hits(lat, lng):
        sel = f[f.intersects(Point(lng, lat))]
        return sorted({_tier_of(k) for k in sel["instrument_key"]})

    pt = f.iloc[0].geometry.representative_point()
    print("\n=== spot-check (2100) ===")
    print(f"  estuary interior ({pt.y:.5f},{pt.x:.5f}) -> {hits(pt.y, pt.x)}  [EXPECT f1-f4]")
    print(f"  Katoomba inland (-33.71260,150.31171) -> {hits(-33.71260, 150.31171)}  [EXPECT none]")


def live_load(frame: gpd.GeoDataFrame):
    eng = _engine()
    print(f"\nstaging {len(frame)} polygons -> {STAGING} (bulk copy) ...")
    frame.to_postgis(STAGING, eng, if_exists="replace", index=False)
    try:
        with eng.begin() as conn:
            before = conn.execute(
                text("SELECT count(*) FROM spatial_overlays WHERE layer_type=:lt"), {"lt": LAYER_TYPE}
            ).scalar()
            print("server-side transform + simplify + upsert ...")
            conn.execute(text(f"""
                INSERT INTO spatial_overlays
                    (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
                SELECT instrument_key, lga_name, layer_type, value, value_numeric, currency_date::date, source_oid,
                       -- simplify (metres) -> WGS84 -> repair any self-intersections
                       -- ST_SimplifyPreserveTopology can introduce (ST_MakeValid + keep
                       -- polygons only), so an invalid geometry can never reach the table.
                       ST_Multi(ST_CollectionExtract(ST_MakeValid(
                           ST_Transform(ST_SimplifyPreserveTopology(ST_SetSRID(geometry, {SRC_EPSG}), {SIMPLIFY_M}), 4326)
                       ), 3)),
                       now()
                FROM {STAGING}
                ON CONFLICT (instrument_key, layer_type, source_oid) DO UPDATE
                    SET value = EXCLUDED.value, value_numeric = EXCLUDED.value_numeric,
                        currency_date = EXCLUDED.currency_date, geom = EXCLUDED.geom, synced_at = now()
            """))
            after = conn.execute(
                text("SELECT count(*) FROM spatial_overlays WHERE layer_type=:lt"), {"lt": LAYER_TYPE}
            ).scalar()
        print(f"COMMITTED. coastal_inundation rows: {before} -> {after} (+{after - before})")
    finally:
        with eng.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {STAGING}"))
        print(f"dropped staging table {STAGING}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="parse + spot-check, no DB write")
    ap.add_argument("--live", action="store_true", help="staging load + server-side simplify upsert")
    args = ap.parse_args()
    if not (args.dry_run or args.live):
        ap.error("choose --dry-run or --live")
    print("=== build frame (SSP3-7.0, 2050+2100, primary f1-f4, native EPSG:28356) ===")
    frame = build_frame()
    print(f"total polygons: {len(frame)}")
    spot_check(frame)
    if args.dry_run:
        print("\nDRY RUN — nothing written to the database.")
        return
    live_load(frame)


if __name__ == "__main__":
    main()
