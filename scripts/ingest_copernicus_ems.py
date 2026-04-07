#!/usr/bin/env python3
"""
Ingest Copernicus EMS flood extent polygons into copernicus_flood_events.

STEP 1 — Download products
  Go to: https://emergency.copernicus.eu/mapping/list-of-activations-rapid
  Filter by country "Australia". For each activation below, open its page
  and download the "Observed Flood Extent" (product code RTP03) GeoJSON.

  Known Australian activations (2022 La Niña gap period):
    EMSR531  SE Queensland / NE NSW  2022-02-26 – 2022-03-05
    EMSR536  NSW floods              2022-03-01 – 2022-03-15
    EMSR575  NSW / QLD floods        2022-10-10 – 2022-11-30

  Save files as e.g.:
    downloads/EMSR531_flood.geojson
    downloads/EMSR536_flood.geojson
    downloads/EMSR575_flood.geojson

STEP 2 — Run (from repo root, venv active):
  python scripts/ingest_copernicus_ems.py \\
      --activation EMSR531 "SE Queensland / NE NSW floods" 2022-02-26 2022-03-05 downloads/EMSR531_flood.geojson \\
      --activation EMSR536 "NSW floods Mar 2022" 2022-03-01 2022-03-15 downloads/EMSR536_flood.geojson \\
      --activation EMSR575 "NSW / QLD floods Oct-Nov 2022" 2022-10-10 2022-11-30 downloads/EMSR575_flood.geojson

Usage:
  --activation ID NAME START END FILE   Add one activation. Repeat for each.
  --dry-run                             Print feature counts without writing to DB.
  --clear-activation ID                 Delete all rows for an activation before re-ingesting.
"""
import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras


@dataclass
class ActivationSpec:
    activation_id: str
    event_name: str
    event_date_start: date
    event_date_end: date
    geojson_path: Path


def _get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


def _geometry_to_multipolygon_wkt(geom: dict) -> Optional[str]:
    """
    Convert a GeoJSON geometry dict to a WKT MULTIPOLYGON string.
    Accepts Polygon or MultiPolygon; skips other types.
    """
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return None

    def ring_wkt(ring) -> str:
        return "(" + ",".join(f"{p[0]} {p[1]}" for p in ring) + ")"

    def polygon_wkt(poly_coords) -> str:
        return "(" + ",".join(ring_wkt(r) for r in poly_coords) + ")"

    if gtype == "Polygon":
        return f"MULTIPOLYGON({polygon_wkt(coords)})"

    if gtype == "MultiPolygon":
        parts = ",".join(polygon_wkt(p) for p in coords)
        return f"MULTIPOLYGON({parts})"

    return None  # Point, LineString etc — skip


def ingest_activation(
    conn,
    spec: ActivationSpec,
    dry_run: bool = False,
    clear_first: bool = False,
) -> int:
    """Ingest one activation's GeoJSON file. Returns number of features inserted."""
    path = spec.geojson_path
    if not path.exists():
        print(f"  ERROR: file not found: {path}", file=sys.stderr)
        return 0

    with path.open() as f:
        data = json.load(f)

    features = data.get("features") or []
    if not features:
        print(f"  WARNING: no features in {path}")
        return 0

    # Filter to flood/delineation features (skip AOI boundaries, reference layers)
    # Copernicus EMS product properties vary; accept all polygon-type geometries
    valid = []
    for feat in features:
        geom = feat.get("geometry")
        if not geom:
            continue
        wkt = _geometry_to_multipolygon_wkt(geom)
        if wkt:
            # Classify flood_type from properties if available
            props = feat.get("properties") or {}
            raw_type = (
                props.get("obj_type") or props.get("flood_type") or props.get("type") or "observed"
            ).lower()
            flood_type = "estimated" if "estim" in raw_type else "observed"
            valid.append((wkt, flood_type))

    print(f"  {spec.activation_id}: {len(valid)} polygon features from {len(features)} total")

    if dry_run:
        return len(valid)

    inserted = 0
    with conn.cursor() as cur:
        if clear_first:
            cur.execute(
                "DELETE FROM copernicus_flood_events WHERE activation_id = %s",
                (spec.activation_id,),
            )
            print(f"  Cleared existing rows for {spec.activation_id}")

        for wkt, flood_type in valid:
            try:
                cur.execute(
                    """
                    INSERT INTO copernicus_flood_events
                        (activation_id, event_name, event_date_start, event_date_end,
                         geometry, flood_type, country, source_url)
                    VALUES (%s, %s, %s, %s,
                            ST_GeomFromText(%s, 4326),
                            %s, 'AU',
                            %s)
                    """,
                    (
                        spec.activation_id,
                        spec.event_name,
                        spec.event_date_start,
                        spec.event_date_end,
                        wkt,
                        flood_type,
                        f"https://emergency.copernicus.eu/mapping/list-of-components/{spec.activation_id}",
                    ),
                )
                inserted += 1
            except Exception as e:
                print(f"  SKIP feature ({e})", file=sys.stderr)

    conn.commit()
    return inserted


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--activation",
        nargs=5,
        metavar=("ID", "NAME", "START", "END", "FILE"),
        action="append",
        default=[],
        help="Add one activation: ID 'Event name' YYYY-MM-DD YYYY-MM-DD path/to/file.geojson",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse files only, no DB writes")
    parser.add_argument("--clear-activation", metavar="ID", action="append", default=[],
                        help="Delete existing rows for this activation before re-ingesting")
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.activation:
        print("No activations specified. Use --activation ID NAME START END FILE", file=sys.stderr)
        sys.exit(1)

    specs = []
    for act in args.activation:
        activation_id, event_name, start_str, end_str, file_path = act
        try:
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str)
        except ValueError as e:
            print(f"Invalid date for {activation_id}: {e}", file=sys.stderr)
            sys.exit(1)
        specs.append(ActivationSpec(
            activation_id=activation_id.upper(),
            event_name=event_name,
            event_date_start=start,
            event_date_end=end,
            geojson_path=Path(file_path),
        ))

    if args.dry_run:
        print("DRY RUN — no DB writes")
        for spec in specs:
            ingest_activation(None, spec, dry_run=True)
        return

    conn = _get_conn()
    total = 0
    try:
        for spec in specs:
            clear = spec.activation_id in [c.upper() for c in args.clear_activation]
            print(f"Ingesting {spec.activation_id} ({spec.event_name}) ...")
            n = ingest_activation(conn, spec, clear_first=clear)
            print(f"  Inserted {n} rows")
            total += n
    finally:
        conn.close()

    print(f"\nDone. Total rows inserted: {total}")
    print("Run the migration first if table does not exist:")
    print("  psql $DATABASE_URL < migrations/027_copernicus_flood_events.sql")


if __name__ == "__main__":
    main()
