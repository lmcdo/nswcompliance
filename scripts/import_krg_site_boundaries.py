#!/usr/bin/env python3
"""
Ku-ring-gai DCP Part 14 — Import small-site urban precinct boundaries
======================================================================
For precincts defined by a list of specific addresses (not a drawn boundary map),
this script:
  1. Geocodes each address via the NSW_Property MapServer (maps.six.nsw.gov.au)
  2. Unions all returned lot polygons into a single MultiPolygon
  3. Inserts into dcp_precinct_boundaries

Used for precincts 14G–14O where the DCP defines the precinct by listing
specific affected properties rather than showing a geographic boundary map.

Add new precincts to PRECINCTS below as you read through each PDF.
Each address can include an alternate in parentheses — both are tried if the
primary returns no result.

Usage:
    python3 scripts/import_krg_site_boundaries.py
    python3 scripts/import_krg_site_boundaries.py --dry-run
    python3 scripts/import_krg_site_boundaries.py --precinct 14J
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

NSW_PROPERTY_URL = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Property/MapServer/4/query"
)

# ---------------------------------------------------------------------------
# Precinct definitions
# Each entry:
#   precinct_id   : matches the DCP section (14J, 14K, etc.)
#   name          : human-readable name
#   suburb        : used in address geocoding
#   source_doc    : DCP section reference
#   addresses     : list of street addresses. Where a property has dual frontage
#                   the DCP shows "Primary Address (Alternate Address)" — list both
#                   and the script tries primary first, then alternate.
#                   Format each as a plain string: "56 Ridge Street"
# ---------------------------------------------------------------------------
PRECINCTS = [
    {
        "precinct_id": "14J",
        "name": "Holford Crescent, Gordon",
        "suburb": "GORDON",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14J",
        "addresses": [
            # Primary address           # Alternate (from DCP parenthetical)
            # DCP says "24-28 Holford Crescent" — cadastral DB has 24 as separate lot;
            # 28 returns no result (may be merged/unsubdivided). Use 24 only.
            "24 Holford Crescent",      # (58A Ryde Road — not in cadastral DB)
            "52 Ryde Road",             # (30-34 Holford Crescent)
            "30-34 Holford Crescent",   # alternate
            "36 Holford Crescent",      # (48 Ryde Road)
            "48 Ryde Road",             # alternate
            "46 Ryde Road",             # (38 Holford Crescent)
            "38 Holford Crescent",      # alternate
            "50 Ridge Street",          # (23-29 Holford Crescent)
            "23-29 Holford Crescent",   # alternate
            "52A Ridge Street",         # (31 Holford Crescent)
            "31 Holford Crescent",      # alternate
            "54A Ridge Street",         # (33 Holford Crescent)
            "33 Holford Crescent",      # alternate
            "56 Ridge Street",          # (35 Holford Crescent)
            "35 Holford Crescent",      # alternate
            "60 Ridge Street",          # (41 Holford Crescent)
            "41 Holford Crescent",      # alternate
            "64 Ridge Street",          # (43 Holford Crescent)
            "43 Holford Crescent",      # alternate
            "66 Ridge Street",          # (45 Holford Crescent)
            "45 Holford Crescent",      # alternate
            "70 Ridge Street",          # (Nar-rang Park)
        ],
    },
    # 14G (Pymble Business Park) is area-based, not address-based — needs QGIS. Not included here.

    {
        "precinct_id": "14H",
        "name": "Screen Australia Site, Lindfield",
        "suburb": "LINDFIELD",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14H",
        # DCP says "101 Eton Road" but cadastral DB has this as strata lot "101/1-3 ETON ROAD".
        # The land parcel is at 1-3 Eton Road but that query also returns empty.
        # TODO: Look up Lot/DP via NSW Cadastre layer or QGIS — needs manual investigation.
        "addresses": [
            "1-3 Eton Road",   # may need Lot/DP approach — see TODO above
        ],
    },
    {
        "precinct_id": "14I",
        "name": "Killara Golf Club",
        "suburb": "KILLARA",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14I",
        "addresses": [
            "556 Pacific Highway",
        ],
    },
    {
        "precinct_id": "14K",
        "name": "45-47 Tennyson Avenue and 105 Eastern Road, Turramurra",
        "suburb": "TURRAMURRA",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14K",
        "addresses": [
            "45-47 Tennyson Avenue",   # cadastral DB has this as one combined lot
            "105 Eastern Road",
        ],
    },
    {
        "precinct_id": "14L",
        "name": "62 (Part) and 64-66 Pacific Highway, Roseville",
        "suburb": "ROSEVILLE",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14L",
        # Note: DCP says "62 (part)" — cadastral lookup returns the full lot.
        # The precinct covers only part of 62; acceptable for address matching purposes.
        # "64-66" is one combined lot in the cadastral DB.
        "addresses": [
            "62 Pacific Highway",
            "64 Pacific Highway",   # cadastral lot covers the full 64-66 site; 66 is merged into 64
        ],
    },
    {
        "precinct_id": "14M",
        "name": "47 Warrane Road, Roseville Chase",
        "suburb": "ROSEVILLE CHASE",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14M",
        # Address "47 Warrane Road, Roseville Chase" returns no result from NSW_Property layer.
        # Former East Roseville Bowling Club — may be registered under a different address
        # or suburb. TODO: Look up via NSW Cadastre DP layer or QGIS.
        "addresses": [
            "47 Warrane Road",
        ],
    },
    {
        "precinct_id": "14N",
        "name": "8A, 14, 16 Buckingham Road, Killara",
        "suburb": "KILLARA",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14N",
        "addresses": [
            "8A Buckingham Road",
            "14 Buckingham Road",
            "16 Buckingham Road",
        ],
    },
    {
        "precinct_id": "14O",
        "name": "Pymble Golf Club, St Ives",
        "suburb": "ST IVES",
        "source_doc": "Ku-ring-gai DCP 2024 Part 14 Section 14O",
        "addresses": [
            "4 Cowan Road",
            "12 Cowan Road",
            "14 Cowan Road",
        ],
    },
]


def geocode_address(street: str, suburb: str) -> dict | None:
    """
    Query NSW_Property MapServer for a street address.
    Returns GeoJSON Polygon geometry or None if not found.
    """
    # NSW_Property address field format: "NUMBER STREET SUBURB" (uppercase, no comma)
    search = f"{street.upper()}%{suburb.upper()}%"
    params = urllib.parse.urlencode({
        "where": f"address LIKE '{search}'",
        "outFields": "propid,address",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    })
    url = f"{NSW_PROPERTY_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        features = data.get("features", [])
        if features:
            return features[0]["geometry"]
        return None
    except Exception as e:
        print(f"    [ERROR] geocoding '{street}, {suburb}': {e}")
        return None


def merge_polygons(polygons: list[dict]) -> dict:
    """
    Merge a list of Polygon GeoJSON geometries into a single MultiPolygon
    by collecting all rings. No external dependencies.
    """
    rings = []
    for g in polygons:
        if g["type"] == "Polygon":
            rings.append(g["coordinates"])
        elif g["type"] == "MultiPolygon":
            rings.extend(g["coordinates"])
    return {"type": "MultiPolygon", "coordinates": rings}


def process_precinct(precinct: dict, dry_run: bool) -> dict | None:
    """
    Geocode all addresses for a precinct, deduplicate by propid,
    and return the merged MultiPolygon geometry.
    Returns None if no lots could be resolved.
    """
    suburb = precinct["suburb"]
    addresses = precinct["addresses"]

    print(f"\n  Geocoding {len(addresses)} address entries...")
    seen_coords: set[str] = set()  # deduplicate by coordinate fingerprint
    polygons: list[dict] = []

    for addr in addresses:
        geom = geocode_address(addr, suburb)
        time.sleep(0.2)  # be polite

        if geom is None:
            print(f"    [MISS]  {addr}, {suburb}")
            continue

        # Deduplicate: same lot may be returned for both primary and alternate address
        fingerprint = str(geom["coordinates"][0][0])  # first coord of outer ring
        if fingerprint in seen_coords:
            print(f"    [DUP]   {addr}, {suburb} — same lot already captured")
            continue

        seen_coords.add(fingerprint)
        polygons.append(geom)
        print(f"    [OK]    {addr}, {suburb}")

    if not polygons:
        print(f"  [FAIL] No lots resolved for {precinct['precinct_id']}")
        return None

    print(f"  {len(polygons)} unique lots resolved")

    if dry_run:
        return {"type": "MultiPolygon", "coordinates": []}  # placeholder

    return merge_polygons(polygons)


def upsert_precinct(cur, precinct: dict, geom: dict) -> None:
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
            'api',
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
            "precinct_id": precinct["precinct_id"],
            "name":        precinct["name"],
            "geom":        json.dumps(geom),
            "source_doc":  precinct["source_doc"],
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import KRG small-site precinct boundaries")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--precinct", help="Only process this precinct_id (e.g. 14J)")
    args = parser.parse_args()

    targets = PRECINCTS
    if args.precinct:
        targets = [p for p in PRECINCTS if p["precinct_id"] == args.precinct]
        if not targets:
            print(f"[ERROR] Precinct '{args.precinct}' not found in PRECINCTS list")
            sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    ok = 0
    failed = 0
    for precinct in targets:
        print(f"\n{'='*60}")
        print(f"Precinct {precinct['precinct_id']} — {precinct['name']}")
        print(f"{'='*60}")

        geom = process_precinct(precinct, args.dry_run)
        if geom is None:
            failed += 1
            continue

        if args.dry_run:
            print(f"  [dry-run] Would upsert {precinct['precinct_id']} | {precinct['name']}")
            ok += 1
            continue

        upsert_precinct(cur, precinct, geom)
        print(f"  Upserted {precinct['precinct_id']}")
        ok += 1

    if not args.dry_run:
        conn.commit()
        print(f"\nCommitted. {ok} upserted, {failed} failed.")
    else:
        conn.rollback()
        print(f"\n[dry-run] {ok} would upsert, {failed} failed.")

    cur.close()
    conn.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
