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
  requests, psycopg2-binary, shapely
"""
import argparse
import io
import json
import logging
import math
import os
import sys
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

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
    conn = _connect_raw()
    # Event names carry an en dash and an n-tilde; never let a Windows client
    # default re-encode them.
    conn.set_client_encoding("UTF8")
    return conn


def _connect_raw():
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

# Only the observed flood extent is flood evidence. Every Copernicus vector
# package also carries the area of interest, the satellite image footprint
# (up to 48,000 km2 per AOI), roads, buildings, rivers and land use. The first
# ingest merged all of them into one 86,349 km2 shape; the observedEventA
# layers alone total ~334 km2 (measured 2026-10-28, 13 AOIs).
OBSERVED_LAYERS = ("observedEventA",)
# A wrong layer is hundreds of times bigger than any real 2022 extent (largest
# real: NSW-202210 at 842 km2), so a merged shape over this is refused.
MAX_EXTENT_KM2 = 5000.0
_EARTH_RADIUS_M = 6371008.8


class ExtentRejected(RuntimeError):
    """The merged extent cannot be a flood extent; nothing is written."""


def _ring_area_m2(coords) -> float:
    # Spherical polygon area (Chamberlain & Duquette 2007). Within ~0.5% of the
    # geodesic area at NSW latitudes -- plenty for a 5,000 km2 guard, and no
    # pyproj needed.
    pts = list(coords)
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        total += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    return abs(total) * _EARTH_RADIUS_M ** 2 / 2


def area_km2(geom) -> float:
    """Area of a lon/lat (EPSG:4326) polygon or multipolygon, in km2."""
    polys = geom.geoms if hasattr(geom, "geoms") else [geom]
    m2 = 0.0
    for p in polys:
        if p.geom_type != "Polygon":
            continue
        m2 += _ring_area_m2([c[:2] for c in p.exterior.coords[:-1]])
        m2 -= sum(_ring_area_m2([c[:2] for c in r.coords[:-1]]) for r in p.interiors)
    return m2 / 1e6


def check_extent(source_id: str, merged) -> float:
    """Refuse an empty extent, or one too big to be flooded land. Returns km2."""
    if merged is None or merged.is_empty:
        raise ExtentRejected(f"{source_id}: no observed flood extent found -- nothing written")
    minx, miny, maxx, maxy = merged.bounds
    if not (110 <= minx and maxx <= 160 and -45 <= miny and maxy <= -9):
        raise ExtentRejected(
            f"{source_id}: bounds {merged.bounds} are not lon/lat in Australia -- nothing written")
    km2 = area_km2(merged)
    if km2 > MAX_EXTENT_KM2:
        raise ExtentRejected(
            f"{source_id}: merged extent {km2:,.0f} km2 > {MAX_EXTENT_KM2:,.0f} km2 -- "
            "a non-flood layer was included; nothing written")
    return km2


def is_observed_layer(name: str) -> bool:
    """True for an observed-flood-extent layer, judged by its file name.

    Each layer ships as .shp and as GeoJSON (.json, lon/lat, no crs member);
    the GeoJSON gives the identical 3,259 polygons / 333.8 km2 without GDAL.
    """
    base = Path(name).name
    return base.endswith(".json") and any(f"_{lay}_" in base for lay in OBSERVED_LAYERS)


def _list_emsr567_vector_zips(base_url: str) -> list[list[str]]:
    """
    Vector ZIP URLs per EMSR567 AOI, in order of preference.
    Naming convention: EMSR567_AOI{nn}_DEL_PRODUCT_r1_RTP01_v1_vector.zip
    Delineation (DEL) products only. RTP01 and RTP02 were byte-identical for
    every AOI that had both (2026-10-28), so the first one found is used.
    """
    return [
        [f"{base_url}/EMSR567_AOI{aoi:02d}_DEL_PRODUCT_r1_{rtp}_v1_vector.zip"
         for rtp in ("RTP01", "RTP02")]
        for aoi in range(1, 17)  # AOI01-AOI16
    ]


def _read_observed_geometries(zip_bytes: bytes) -> list:
    """Observed-flood-extent polygons from one vector ZIP. Other layers ignored."""
    geoms = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not is_observed_layer(name):
                continue
            for feat in json.loads(zf.read(name)).get("features") or []:
                if not feat.get("geometry"):
                    continue
                geom = shape(feat["geometry"])
                if geom.is_empty:
                    continue
                geoms.append(geom if geom.is_valid else geom.buffer(0))
    return geoms


def _fetch_s3_zip_geometries(zip_url: str) -> Optional[list]:
    """Observed flood polygons from one ZIP; None when the ZIP is not there."""
    try:
        r = requests.get(zip_url, timeout=60)
        if r.status_code in (403, 404):
            return None
        r.raise_for_status()
    except Exception as e:
        log.debug(f"  Skip {zip_url.split('/')[-1]}: {e}")
        return None
    return _read_observed_geometries(r.content)


def build_emsr567_extent(source: FloodSource):
    """Download every AOI, keep observed flood polygons only, union, check."""
    all_geoms = []
    for candidates in _list_emsr567_vector_zips(source.url):
        for url in candidates:
            geoms = _fetch_s3_zip_geometries(url)
            if geoms is None:
                continue
            log.info(f"  {Path(url).name}: {len(geoms)} observed-flood polygons")
            all_geoms.extend(geoms)
            break
    log.info(f"EMSR567: unioning {len(all_geoms)} polygons ...")
    merged = unary_union(all_geoms) if all_geoms else None
    if merged is not None and merged.geom_type == "Polygon":
        merged = MultiPolygon([merged])
    km2 = check_extent(source.source_id, merged)
    log.info(f"EMSR567: merged -> {len(merged.geoms)} polygons, {km2:,.1f} km2")
    return merged


def ingest_emsr567(source: FloodSource, conn, dry_run: bool = False,
                   dump_geojson: Optional[Path] = None) -> int:
    log.info("EMSR567: fetching Copernicus S3 vector packages ...")
    merged = build_emsr567_extent(source)
    if dump_geojson:
        dump_geojson.write_text(json.dumps(merged.__geo_interface__), encoding="utf-8")
        log.info(f"EMSR567: extent written to {dump_geojson}")
    if dry_run:
        log.info("DRY RUN: skipping DB insert")
        return 1
    _insert_row(conn, source, merged)
    log.info("EMSR567: inserted 1 merged row")
    return 1


def _insert_row(conn, source: FloodSource, merged) -> None:
    """Insert and commit. With --clear, the DELETE before it lands in this same commit."""
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
                json.dumps(merged.__geo_interface__),
                source.url,
            ),
        )
    conn.commit()


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

    km2 = check_extent(source.source_id, merged)
    log.info(f"{source.source_id}: merged -> {len(merged.geoms)} polygons, {km2:,.1f} km2")
    if dry_run:
        log.info("DRY RUN: skipping DB insert")
        return 1

    _insert_row(conn, source, merged)
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
                   help="Delete existing rows for the target source(s) before re-ingesting "
                        "(same transaction as the insert, so a refused extent deletes nothing)")
    p.add_argument("--dump-geojson", type=Path,
                   help="EMSR567 only: write the merged extent to this GeoJSON file")
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
                log.info(f"  Deleting existing rows for {source.source_id} (commits with the insert)")

            if source.kind == "copernicus_s3":
                n = ingest_emsr567(source, conn, dry_run=args.dry_run,
                                  dump_geojson=args.dump_geojson)
            else:
                n = ingest_featureserver(source, conn, dry_run=args.dry_run)

            log.info(f"  Done: {n} row(s) inserted")

    finally:
        if conn:
            conn.close()

    log.info("Ingest complete.")


if __name__ == "__main__":
    main()
