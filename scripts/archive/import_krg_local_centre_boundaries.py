#!/usr/bin/env python3
"""
Ku-ring-gai DCP Part 14 — Import local centre precinct boundaries from GeoPackage
==================================================================================
Reads digitised polygons from the QGIS GeoPackage (krg-local-centres.gpkg) and
upserts into dcp_precinct_boundaries.

Polygons are digitised in QGIS by tracing over georeferenced DCP precinct maps.
Each feature has a precinct_id field (e.g. "14B_T1") that maps to a full name
and source document via PRECINCT_META below.

Add new entries to PRECINCT_META as each local centre is digitised.

Usage:
    python3 scripts/import_krg_local_centre_boundaries.py
    python3 scripts/import_krg_local_centre_boundaries.py --dry-run
    python3 scripts/import_krg_local_centre_boundaries.py --precinct 14B_T1
"""

import argparse
import json
import os
import sys
from pathlib import Path

import fiona
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

GPKG_PATH = (
    Path(__file__).parent.parent
    / "ku-ring-gai"
    / "precinct-maps"
    / "krg-local-centres.gpkg"
)
LAYER_NAME = "local_centre_precincts"

# ---------------------------------------------------------------------------
# Metadata for each digitised sub-precinct
# precinct_id -> (precinct_name, source_doc)
# ---------------------------------------------------------------------------
PRECINCT_META = {
    # 14B Turramurra Local Centre
    "14B_T1": (
        "Precinct T1: Pacific Highway and Ray Street Retail Area",
        "Ku-ring-gai DCP 2024 Part 14 Section 14B.8",
    ),
    "14B_T2": (
        "Precinct T2: Rohini Street and Eastern Road Retail Centre",
        "Ku-ring-gai DCP 2024 Part 14 Section 14B.9",
    ),
    "14B_T3": (
        "Precinct T3: Kissing Point Road Retail Area",
        "Ku-ring-gai DCP 2024 Part 14 Section 14B.10",
    ),
    "14B_T4": (
        "Precinct T4: Hillview Area",
        "Ku-ring-gai DCP 2024 Part 14 Section 14B.11",
    ),
    # 14A Gordon Local Centre — add when digitised
    # "14A_G1": ("Precinct G1: ...", "Ku-ring-gai DCP 2024 Part 14 Section 14A.x"),
    # 14C Pymble Local Centre — add when digitised
    # 14D St Ives Local Centre — add when digitised
    # 14E Lindfield Local Centre — add when digitised
    # 14F Roseville Local Centre — add when digitised
}


def geojson_from_fiona(geom) -> dict:
    """Convert a fiona geometry to a GeoJSON dict."""
    return dict(geom)


def upsert_precinct(cur, precinct_id: str, name: str, source_doc: str, geom: dict) -> None:
    cur.execute(
        """
        INSERT INTO dcp_precinct_boundaries (
            precinct_id,
            precinct_name,
            lga,
            former_council,
            boundary,
            source_document,
            extraction_method,
            confidence_score
        )
        VALUES (
            %(precinct_id)s,
            %(name)s,
            'Ku-ring-gai',
            NULL,
            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
            %(source_doc)s,
            'qgis_digitised',
            0.95
        )
        ON CONFLICT (precinct_id, lga) DO UPDATE SET
            precinct_name     = EXCLUDED.precinct_name,
            boundary          = EXCLUDED.boundary,
            source_document   = EXCLUDED.source_document,
            extraction_method = EXCLUDED.extraction_method,
            confidence_score  = EXCLUDED.confidence_score,
            updated_at        = NOW()
        """,
        {
            "precinct_id": precinct_id,
            "name":        name,
            "geom":        json.dumps(geom),
            "source_doc":  source_doc,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import KRG local centre precinct boundaries")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--precinct", help="Only process this precinct_id (e.g. 14B_T1)")
    args = parser.parse_args()

    if not GPKG_PATH.exists():
        print(f"[ERROR] GeoPackage not found: {GPKG_PATH}")
        sys.exit(1)

    # Read features from GeoPackage
    # fiona field name may be 'precinct_id' or 'precincts_id' depending on how layer was created
    with fiona.open(str(GPKG_PATH), layer=LAYER_NAME) as src:
        features = list(src)
        crs = src.crs

    print(f"CRS: {crs}")
    print(f"Features in GeoPackage: {len(features)}")

    # Detect field name
    if features:
        props = features[0]["properties"]
        if "precinct_id" in props:
            id_field = "precinct_id"
        elif "precincts_id" in props:
            id_field = "precincts_id"
        else:
            print(f"[ERROR] No precinct_id field found. Fields: {list(props.keys())}")
            sys.exit(1)
        print(f"Using field: {id_field}")

    ok = 0
    skipped = 0
    failed = 0

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    for feat in features:
        precinct_id = feat["properties"].get(id_field, "").strip()

        if not precinct_id:
            print(f"  [SKIP] Feature with empty {id_field}")
            skipped += 1
            continue

        if args.precinct and precinct_id != args.precinct:
            continue

        if precinct_id not in PRECINCT_META:
            print(f"  [SKIP] {precinct_id} — not in PRECINCT_META (add it first)")
            skipped += 1
            continue

        name, source_doc = PRECINCT_META[precinct_id]
        geom = geojson_from_fiona(feat["geometry"])

        print(f"\n  {precinct_id} — {name}")
        print(f"  Geometry type: {geom['type']}")

        if args.dry_run:
            print(f"  [dry-run] Would upsert")
            ok += 1
            continue

        upsert_precinct(cur, precinct_id, name, source_doc, geom)
        print(f"  Upserted")
        ok += 1

    if not args.dry_run:
        conn.commit()
        print(f"\nCommitted. {ok} upserted, {skipped} skipped, {failed} failed.")
    else:
        conn.rollback()
        print(f"\n[dry-run] {ok} would upsert, {skipped} skipped.")

    cur.close()
    conn.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
