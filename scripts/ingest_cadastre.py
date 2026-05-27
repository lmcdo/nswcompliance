#!/usr/bin/env python3
"""
Ingest NSW Cadastre lot polygons into nsw_cadastre_lots table.

Source: NSW Spatial Services FeatureServer Layer 8
URL: https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme/FeatureServer/8
License: CC-BY 4.0 (commercial use OK)
Records: ~3.35M lots statewide

API notes:
  - Returns Esri JSON (rings), NOT GeoJSON (f=geojson returns 503)
  - OBJECTID-based filtering doesn't work; use where=1=1 + offset pagination
  - outSR=4326 reprojects from native EPSG:3857 to WGS84
  - Max page size: 2,000

Usage:
    # Count records (no DB writes)
    python scripts/ingest_cadastre.py --count

    # Dry run — parse but don't write to DB
    python scripts/ingest_cadastre.py --dry-run --limit 5000

    # Ingest with LGA spatial filter (requires zone data in spatial_overlays)
    python scripts/ingest_cadastre.py --lga "INNER WEST"

    # Ingest all NSW (~3.35M lots, ~20-30 min)
    python scripts/ingest_cadastre.py --scope all

    # Incremental sync (lots modified since last run)
    python scripts/ingest_cadastre.py --incremental
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from shapely.geometry import Polygon, MultiPolygon

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FEATURESERVER_URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services"
    "/NSW_Land_Parcel_Property_Theme/FeatureServer/8"
)

PAGE_SIZE = 2000  # FeatureServer max

# Fields to fetch (reduces payload vs outFields=*)
# Field names verified against layer metadata — all lowercase except Shape__*
OUT_FIELDS = ",".join([
    "lotidstring", "lotnumber", "sectionnumber", "planlabel", "plannumber",
    "planlotarea", "Shape__Area",
    "urbanity", "stratumlevel", "hasstratum", "itstitlestatus",
    "createdate", "modifieddate", "cadid", "objectid",
])


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def get_count(where: str = "1=1", spatial_params: Optional[dict] = None) -> int:
    """Get total record count from FeatureServer."""
    params: dict = {"where": where, "returnCountOnly": "true", "f": "json"}
    if spatial_params:
        params.update(spatial_params)
    resp = requests.get(f"{FEATURESERVER_URL}/query", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("count", 0)


def fetch_page(
    where: str,
    offset: int,
    spatial_params: Optional[dict] = None,
) -> dict:
    """Fetch a page of Esri JSON features with retry."""
    params: dict = {
        "where": where,
        "outFields": OUT_FIELDS,
        "returnGeometry": "true",
        "outSR": "4326",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "f": "json",
    }
    if spatial_params:
        params.update(spatial_params)

    for attempt in range(3):
        try:
            resp = requests.get(
                f"{FEATURESERVER_URL}/query",
                params=params,
                timeout=90,
            )
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            wait = 15 * (attempt + 1)
            print(f"    [warn] {type(e).__name__} (attempt {attempt+1}/3) — retrying in {wait}s ...")
            time.sleep(wait)
            continue
        if resp.status_code in (500, 503):
            wait = 10 * (attempt + 1)
            print(f"    [warn] {resp.status_code} (attempt {attempt+1}/3) — retrying in {wait}s ...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            print(f"    [warn] API error: {data['error'].get('message', data['error'])}")
            return {"features": []}
        return data

    print(f"    [skip] failed after 3 retries — offset={offset}")
    return {"features": []}


def parse_epoch_ms(val) -> Optional[datetime]:
    """Convert ArcGIS epoch-millisecond timestamp to datetime."""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return datetime.utcfromtimestamp(val / 1000)
        return datetime.fromisoformat(str(val)[:19])
    except Exception:
        return None


def esri_rings_to_multipolygon_wkt(rings: list[list[list[float]]]) -> Optional[str]:
    """Convert Esri JSON rings to MultiPolygon WKT.

    Esri convention: exterior rings are clockwise, holes are counter-clockwise.
    Shapely convention: exterior rings are counter-clockwise.
    Shapely's Polygon constructor handles orientation automatically.

    Each exterior ring starts a new polygon; subsequent counter-clockwise
    rings (positive signed area) are holes of the preceding exterior ring.
    """
    if not rings:
        return None
    try:
        polygons = []
        current_exterior = None
        current_holes: list = []

        for ring in rings:
            if len(ring) < 4:
                continue
            # Esri: clockwise = exterior, counter-clockwise = hole
            # Signed area: negative = clockwise (exterior in Esri)
            signed_area = sum(
                (ring[i][0] - ring[i - 1][0]) * (ring[i][1] + ring[i - 1][1])
                for i in range(len(ring))
            )
            if signed_area >= 0:
                # Counter-clockwise in Esri = hole
                if current_exterior is not None:
                    current_holes.append(ring)
                # If no exterior yet, treat as exterior (some datasets are inconsistent)
                else:
                    current_exterior = ring
            else:
                # Clockwise in Esri = exterior ring → flush previous polygon
                if current_exterior is not None:
                    polygons.append(Polygon(current_exterior, current_holes))
                    current_holes = []
                current_exterior = ring

        # Flush last polygon
        if current_exterior is not None:
            polygons.append(Polygon(current_exterior, current_holes))

        if not polygons:
            return None

        valid_polygons = [p for p in polygons if p.is_valid and not p.is_empty]
        if not valid_polygons:
            return None

        multi = MultiPolygon(valid_polygons)
        return multi.wkt
    except Exception:
        return None


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------

def build_rows(features: list[dict]) -> list[tuple]:
    """Extract DB rows from Esri JSON features."""
    rows = []
    for f in features:
        attrs = f.get("attributes", {})
        geom = f.get("geometry", {})
        rings = geom.get("rings")
        if not rings:
            continue

        wkt = esri_rings_to_multipolygon_wkt(rings)
        if not wkt:
            continue

        lotid = attrs.get("lotidstring")
        if not lotid:
            continue

        shape_area = attrs.get("Shape__Area")
        if shape_area is None:
            continue

        rows.append((
            lotid,
            attrs.get("lotnumber"),
            attrs.get("sectionnumber"),
            attrs.get("planlabel"),
            attrs.get("plannumber"),
            attrs.get("planlotarea"),
            float(shape_area),
            attrs.get("urbanity"),
            attrs.get("stratumlevel"),
            attrs.get("hasstratum"),
            attrs.get("itstitlestatus"),
            parse_epoch_ms(attrs.get("createdate")),
            parse_epoch_ms(attrs.get("modifieddate")),
            attrs.get("cadid"),
            attrs.get("objectid"),
            wkt,
        ))
    return rows


def upsert_rows(cur, rows: list[tuple]) -> None:
    """Bulk upsert rows into nsw_cadastre_lots."""
    execute_values(
        cur,
        """
        INSERT INTO nsw_cadastre_lots
            (lotidstring, lotnumber, sectionnumber, planlabel, plannumber,
             planlotarea, shape_area, urbanity, stratumlevel,
             hasstratum, itstitlestatus, createdate, modifieddate,
             cadid, objectid, geom, synced_at)
        VALUES %s
        ON CONFLICT (lotidstring) DO UPDATE SET
            lotnumber      = EXCLUDED.lotnumber,
            sectionnumber  = EXCLUDED.sectionnumber,
            planlabel      = EXCLUDED.planlabel,
            plannumber     = EXCLUDED.plannumber,
            planlotarea    = EXCLUDED.planlotarea,
            shape_area     = EXCLUDED.shape_area,
            urbanity       = EXCLUDED.urbanity,
            stratumlevel   = EXCLUDED.stratumlevel,
            hasstratum     = EXCLUDED.hasstratum,
            itstitlestatus = EXCLUDED.itstitlestatus,
            createdate     = EXCLUDED.createdate,
            modifieddate   = EXCLUDED.modifieddate,
            cadid          = EXCLUDED.cadid,
            objectid       = EXCLUDED.objectid,
            geom           = EXCLUDED.geom,
            synced_at      = now()
        """,
        rows,
        template=(
            "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
            " ST_Multi(ST_GeomFromText(%s, 4326)), now())"
        ),
    )


def validate_ingest(cur, label: str) -> None:
    """Post-ingest validation checks."""
    cur.execute("SELECT COUNT(*) FROM nsw_cadastre_lots")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM nsw_cadastre_lots WHERE geom IS NULL")
    null_geom = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM nsw_cadastre_lots WHERE shape_area <= 0")
    zero_area = cur.fetchone()[0]

    cur.execute(
        "SELECT urbanity, COUNT(*) FROM nsw_cadastre_lots "
        "GROUP BY urbanity ORDER BY COUNT(*) DESC"
    )
    urbanity_dist = cur.fetchall()

    print(f"\n--- Validation ({label}) ---")
    print(f"  Total rows:      {total:,}")
    print(f"  NULL geom:       {null_geom} (expect 0)")
    print(f"  Zero/neg area:   {zero_area}")
    print(f"  Urbanity distribution:")
    for u, c in urbanity_dist:
        print(f"    {u or 'NULL'}: {c:,}")

    if null_geom > 0:
        print("  [WARN] Data quality issue — NULL geometries")
    else:
        print("  [OK] All geometries populated")


# ---------------------------------------------------------------------------
# Ingest orchestration
# ---------------------------------------------------------------------------

def reconnect_db(db_url: str):
    """Create a fresh DB connection."""
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def ingest(
    where: str,
    label: str,
    dry_run: bool = False,
    conn=None,
    db_url: Optional[str] = None,
    limit: Optional[int] = None,
    spatial_params: Optional[dict] = None,
) -> int:
    """Paginate through FeatureServer and upsert into DB."""
    total_count = get_count(where, spatial_params)
    effective_count = min(total_count, limit) if limit else total_count
    print(f"\n=== Ingesting {label}: {total_count:,} lots{f' (limit: {limit:,})' if limit else ''} ===")
    if total_count == 0:
        print("  No lots to ingest.")
        return 0, conn

    expected_pages = (effective_count + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"  Pages: ~{expected_pages} (at {PAGE_SIZE}/page)")

    cur = conn.cursor() if conn else None
    offset = 0
    ingested = 0
    start_time = time.time()

    while offset < effective_count:
        page_start = time.time()
        data = fetch_page(where, offset, spatial_params)
        features = data.get("features", [])

        if not features:
            if offset + PAGE_SIZE < effective_count:
                print(f"    [warn] empty page at offset={offset} — skipping")
                offset += PAGE_SIZE
                continue
            break

        rows = build_rows(features)
        if rows and cur and not dry_run:
            for attempt in range(5):
                try:
                    upsert_rows(cur, rows)
                    conn.commit()
                    break
                except (psycopg2.OperationalError, psycopg2.errors.QueryCanceled) as e:
                    if not db_url or attempt == 4:
                        raise
                    wait = 30 * (attempt + 1)
                    print(f"    [warn] DB error (attempt {attempt + 1}/5): {type(e).__name__} — reconnecting in {wait}s ...")
                    time.sleep(wait)
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = reconnect_db(db_url)
                    cur = conn.cursor()

        ingested += len(rows)
        elapsed = time.time() - start_time
        page_time = time.time() - page_start
        pct = min(100.0, (offset + len(features)) / effective_count * 100)

        rate = ingested / elapsed if elapsed > 0 else 0
        remaining = effective_count - (offset + len(features))
        eta_secs = remaining / rate if rate > 0 else 0
        eta_str = f"{eta_secs / 60:.1f}min" if eta_secs > 60 else f"{eta_secs:.0f}s"

        print(
            f"    page {offset // PAGE_SIZE + 1}/{expected_pages} "
            f"({pct:.1f}%) — {len(rows)} rows "
            f"({page_time:.1f}s) — total: {ingested:,} — ETA: {eta_str}"
        )

        offset += PAGE_SIZE

    elapsed = time.time() - start_time
    print(f"\n  Done: {ingested:,} lots ingested in {elapsed:.1f}s")

    if cur and not dry_run:
        validate_ingest(cur, label)
        cur.close()

    return ingested, conn


def get_lga_bbox(conn, lga_name: str) -> Optional[tuple[float, float, float, float]]:
    """Get LGA bounding box from spatial_overlays zone layer."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ST_XMin(ST_Extent(geom)), ST_YMin(ST_Extent(geom)),
               ST_XMax(ST_Extent(geom)), ST_YMax(ST_Extent(geom))
        FROM spatial_overlays
        WHERE layer_type = 'zone' AND lga_name = %s
        """,
        (lga_name,),
    )
    row = cur.fetchone()
    cur.close()
    if not row or row[0] is None:
        return None
    return row


def get_last_sync(conn) -> Optional[datetime]:
    """Get most recent modifieddate for incremental sync."""
    cur = conn.cursor()
    cur.execute("SELECT MAX(modifieddate) FROM nsw_cadastre_lots")
    row = cur.fetchone()
    cur.close()
    return row[0] if row and row[0] else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest NSW Cadastre lots")
    parser.add_argument("--count", action="store_true", help="Count records only (no DB)")
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't write to DB")
    parser.add_argument("--lga", type=str, help="Filter by LGA name (e.g. 'INNER WEST')")
    parser.add_argument(
        "--scope", choices=["sydney", "all"],
        help="'sydney' (~1.38M lots) or 'all' (~3.35M lots)"
    )
    parser.add_argument("--incremental", action="store_true", help="Sync lots modified since last run")
    parser.add_argument("--limit", type=int, help="Max lots to ingest (for testing)")
    args = parser.parse_args()

    if args.count:
        print(f"Total NSW lots: {get_count():,}")
        return

    where = "1=1"
    label = "all NSW"
    spatial_params: Optional[dict] = None

    # DB connection
    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("[error] DATABASE_URL not set. Use --dry-run for no-DB mode.")
        sys.exit(1)

    conn = None
    if db_url:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False

    try:
        # Incremental mode
        if args.incremental and conn:
            last_sync = get_last_sync(conn)
            if last_sync:
                epoch_ms = int(last_sync.timestamp() * 1000)
                where = f"modifieddate > {epoch_ms}"
                label = f"incremental (since {last_sync.strftime('%Y-%m-%d')})"
                print(f"[info] Incremental sync: modified since {last_sync}")
            else:
                print("[info] No existing data — running full ingest")

        # LGA spatial filter
        if args.lga:
            if not conn:
                print("[error] --lga requires DB connection (for spatial_overlays bbox lookup)")
                sys.exit(1)
            bbox_row = get_lga_bbox(conn, args.lga)
            if not bbox_row:
                print(f"[error] No zone data for LGA '{args.lga}' in spatial_overlays.")
                print("[hint] Run ingest_spatial_overlays.py for this LGA first.")
                sys.exit(1)
            xmin, ymin, xmax, ymax = bbox_row
            buf = 0.001  # ~100m buffer
            envelope = f"{xmin - buf},{ymin - buf},{xmax + buf},{ymax + buf}"
            spatial_params = {
                "geometry": envelope,
                "geometryType": "esriGeometryEnvelope",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
            }
            label = args.lga
            print(f"  LGA bbox: {envelope}")

        _, conn = ingest(
            where=where,
            label=label,
            dry_run=args.dry_run,
            conn=conn,
            db_url=db_url,
            limit=args.limit,
            spatial_params=spatial_params,
        )

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
