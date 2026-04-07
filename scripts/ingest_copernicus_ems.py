#!/usr/bin/env python3
"""
Ingest NSW 2022 La Niña flood extent polygons into copernicus_flood_events.

Three datasets covering the full 2022 event sequence:

  EMSR567  Feb–Mar 2022  Copernicus EMS Rapid Mapping (QLD/NSW La Niña)
                          Lismore, Grafton, Ballina, Newcastle, Sydney, Nowra etc.
                          Source: Copernicus S3 bucket (public, no auth)

  202207   Jul 2022      NSW Spatial Services FeatureServer (~12,000 polygons)
                          Source: portal.data.nsw.gov.au

  202210   Oct 2022      NSW Spatial Services FeatureServer (58 polygons)
                          Source: portal.spatial.nsw.gov.au

Usage:
  python scripts/ingest_copernicus_ems.py               # ingest all three
  python scripts/ingest_copernicus_ems.py --source 202210
  python scripts/ingest_copernicus_ems.py --dry-run
  python scripts/ingest_copernicus_ems.py --clear       # delete existing rows first

Requires (all in services/requirements.txt):
  requests, psycopg2-binary, shapely, geopandas
"""
import argparse
import io
import json
import logging
import os
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import geopandas as gpd
import psycopg2
import psycopg2.extras
import requests
from shapely.geometry import MultiPolygon, shape
from shapely.ops import unary_union

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data source definitions
# ---------------------------------------------------------------------------

@dataclass
class FloodSource:
    source_id: str          # stored in activation_id column
    event_name: str
    event_date_start: date
    event_date_end: date
    kind: str               # "copernicus_s3" | "featureserver"
    url: str                # base URL (S3 activation prefix or FeatureServer layer URL)


SOURCES = [
    FloodSource(
        source_id="EMSR567",
        event_name="NSW/QLD Floods Feb–Mar 2022 — La Niña (Copernicus EMSR567)",
        event_date_start=date(2022, 2, 26),
        event_date_end=date(2022, 3, 15),
        kind="copernicus_s3",
        url="https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations/EMSR567",
    ),
    FloodSource(
        source_id="NSW-202207",
        event_name="NSW Floods July 2022",
        event_date_start=date(2022, 7, 1),
        event_date_end=date(2022, 7, 31),
        kind="featureserver",
        url="https://portal.data.nsw.gov.au/arcgis/rest/services/FloodExtent_202207/FeatureServer/0",
    ),
    FloodSource(
        source_id="NSW-202210",
        event_name="NSW Floods October 2022",
        event_date_start=date(2022, 10, 1),
        event_date_end=date(2022, 11, 30),
        kind="featureserver",
        url=(
            "https://portal.spatial.nsw.gov.au/portal/sharing/servers/"
            "02630b024f0e41588ab7beb2bcbd8049/rest/services/FloodExtent_202210/FeatureServer/0"
        ),
    ),
]

SOURCE_MAP = {s.source_id: s for s in SOURCES}


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

def _get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    # Load .env from repo root if running locally
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                dsn = line.split("=", 1)[1].strip()
                break
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


# ---------------------------------------------------------------------------
# Copernicus S3 ingest (EMSR567)
# ---------------------------------------------------------------------------

def _list_emsr567_vector_zips(base_url: str) -> list[str]:
    """
    Build list of vector ZIP URLs for all EMSR567 AOIs.
    Naming convention: EMSR567_AOI{nn}_DEL_PRODUCT_r1_RTP01_v1_vector.zip
    We try both RTP01 (first estimate) and RDEL (delineation) product codes.
    """
    urls = []
    for aoi in range(1, 17):  # AOI01–AOI16
        aoi_str = f"AOI{aoi:02d}"
        # Try delineation product first (most accurate), fall back to first estimate
        for product in ["DEL_PRODUCT_r1_RTP01_v1", "DEL_PRODUCT_r1_RTP02_v1"]:
            url = f"{base_url}/EMSR567_{aoi_str}_{product}_vector.zip"
            urls.append(url)
    return urls


def _fetch_s3_zip_geometries(zip_url: str) -> list:
    """Download a Copernicus S3 vector ZIP, extract flood extent polygons."""
    try:
        r = requests.get(zip_url, timeout=60)
        if r.status_code == 404:
            return []
        r.raise_for_status()
    except Exception as e:
        log.debug(f"  Skip {zip_url.split('/')[-1]}: {e}")
        return []

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            # Find shapefiles (prefer .shp) or GeoJSON files
            shp_names = [n for n in zf.namelist() if n.endswith(".shp")]
            geojson_names = [n for n in zf.namelist() if n.endswith(".geojson")]

            geoms = []
            for name in shp_names + geojson_names:
                try:
                    # Extract relevant files to an in-memory VFS using geopandas
                    # We write to a temp location since geopandas needs file paths
                    import tempfile
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zf.extractall(tmpdir)
                        target = Path(tmpdir) / name
                        if not target.exists():
                            # name may include subdirectory
                            for f in Path(tmpdir).rglob("*.shp"):
                                target = f
                                break
                            else:
                                for f in Path(tmpdir).rglob("*.geojson"):
                                    target = f
                                    break
                        if target.exists():
                            gdf = gpd.read_file(str(target))
                            gdf = gdf.to_crs(epsg=4326)
                            for geom in gdf.geometry:
                                if geom and not geom.is_empty:
                                    geoms.append(geom)
                except Exception as e2:
                    log.debug(f"    Parse error in {name}: {e2}")
            return geoms
    except Exception as e:
        log.warning(f"  ZIP parse error {zip_url.split('/')[-1]}: {e}")
        return []


def ingest_emsr567(source: FloodSource, conn, dry_run: bool = False) -> int:
    log.info(f"EMSR567: fetching Copernicus S3 vector packages ...")
    zip_urls = _list_emsr567_vector_zips(source.url)
    all_geoms = []

    for url in zip_urls:
        geoms = _fetch_s3_zip_geometries(url)
        if geoms:
            log.info(f"  {url.split('/')[-1]}: {len(geoms)} features")
            all_geoms.extend(geoms)

    if not all_geoms:
        log.warning("EMSR567: no geometries found — check S3 URLs")
        return 0

    log.info(f"EMSR567: unioning {len(all_geoms)} polygons ...")
    merged = unary_union(all_geoms)
    if not isinstance(merged, MultiPolygon):
        merged = MultiPolygon([merged]) if merged.geom_type == "Polygon" else merged

    log.info(f"EMSR567: merged → {merged.geom_type}")
    if dry_run:
        log.info("DRY RUN: skipping DB insert")
        return 1

    geojson_str = json.dumps(merged.__geo_interface__)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO copernicus_flood_events
                (activation_id, event_name, event_date_start, event_date_end,
                 geometry, flood_type, country, source_url)
            VALUES (%s, %s, %s, %s,
                    ST_Multi(ST_GeomFromGeoJSON(%s)),
                    'observed', 'AU', %s)
            """,
            (
                source.source_id,
                source.event_name,
                source.event_date_start,
                source.event_date_end,
                geojson_str,
                source.url,
            ),
        )
    conn.commit()
    log.info("EMSR567: inserted 1 merged row")
    return 1


# ---------------------------------------------------------------------------
# NSW FeatureServer ingest (202207, 202210)
# ---------------------------------------------------------------------------

def _fetch_featureserver_all(layer_url: str, page_size: int = 1000) -> list:
    """Paginate through an ArcGIS FeatureServer/MapServer layer, return all GeoJSON features."""
    features = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "geometryPrecision": 6,
        }
        try:
            r = requests.get(f"{layer_url}/query", params=params, timeout=120)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning(f"  FeatureServer error at offset {offset}: {e}")
            break

        batch = data.get("features", [])
        features.extend(batch)
        log.info(f"  Fetched {len(features)} features so far ...")

        # ArcGIS signals "no more data" by returning fewer than page_size
        if len(batch) < page_size:
            break
        offset += page_size

    return features


def ingest_featureserver(source: FloodSource, conn, dry_run: bool = False) -> int:
    log.info(f"{source.source_id}: fetching from FeatureServer ...")
    features = _fetch_featureserver_all(source.url)
    if not features:
        log.warning(f"{source.source_id}: no features returned")
        return 0

    log.info(f"{source.source_id}: parsing {len(features)} features ...")
    geoms = []
    for feat in features:
        try:
            g = shape(feat["geometry"])
            if g and not g.is_empty and g.is_valid:
                geoms.append(g)
            elif not g.is_valid:
                geoms.append(g.buffer(0))
        except Exception:
            continue

    if not geoms:
        log.warning(f"{source.source_id}: no valid geometries")
        return 0

    log.info(f"{source.source_id}: unioning {len(geoms)} polygons ...")
    merged = unary_union(geoms)
    if merged.geom_type == "Polygon":
        merged = MultiPolygon([merged])

    log.info(f"{source.source_id}: merged → {merged.geom_type}")
    if dry_run:
        log.info("DRY RUN: skipping DB insert")
        return 1

    geojson_str = json.dumps(merged.__geo_interface__)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO copernicus_flood_events
                (activation_id, event_name, event_date_start, event_date_end,
                 geometry, flood_type, country, source_url)
            VALUES (%s, %s, %s, %s,
                    ST_Multi(ST_GeomFromGeoJSON(%s)),
                    'observed', 'AU', %s)
            """,
            (
                source.source_id,
                source.event_name,
                source.event_date_start,
                source.event_date_end,
                geojson_str,
                source.url,
            ),
        )
    conn.commit()
    log.info(f"{source.source_id}: inserted 1 merged row")
    return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", choices=list(SOURCE_MAP.keys()),
                   help="Ingest one source only (default: all three)")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch and parse data but do not write to DB")
    p.add_argument("--clear", action="store_true",
                   help="Delete existing rows for the target source(s) before re-ingesting")
    return p.parse_args()


def main():
    args = parse_args()
    targets = [SOURCE_MAP[args.source]] if args.source else SOURCES

    if args.dry_run:
        log.info("DRY RUN mode — no DB writes")
        conn = None
    else:
        conn = _get_conn()

    try:
        for source in targets:
            log.info(f"=== {source.source_id}: {source.event_name} ===")

            if not args.dry_run and args.clear:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM copernicus_flood_events WHERE activation_id = %s",
                        (source.source_id,),
                    )
                conn.commit()
                log.info(f"  Cleared existing rows for {source.source_id}")

            if source.kind == "copernicus_s3":
                n = ingest_emsr567(source, conn, dry_run=args.dry_run)
            else:
                n = ingest_featureserver(source, conn, dry_run=args.dry_run)

            log.info(f"  Done: {n} row(s) inserted")

    finally:
        if conn:
            conn.close()

    log.info("Ingest complete.")


if __name__ == "__main__":
    main()
