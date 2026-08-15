#!/usr/bin/env python3
"""
City of Sydney DCP 2012 — Import precinct boundaries to dcp_precinct_boundaries
================================================================================
Imports three GeoJSON files (locality areas, specific areas, specific sites)
into the dcp_precinct_boundaries PostGIS table.

MultiPolygon handling:
  All geometries are normalised to MULTIPOLYGON via ST_Multi() on insert.
  This matches the column type (MULTIPOLYGON, 4326) and means one row = one
  precinct, always. No risk of duplicate-row confusion from non-contiguous
  precincts like "Central Sydney 7".

Slug collision handling (pre-processed before insert):
  Three cases found in CoS source data:
  1. Identical geometry, different DCP section (North Alexandria x2)
     -> Deduplicate: keep first, skip rest.
  2. Same name, same section, different geometry (Darlinghurst Road x5)
     -> Merge into one MultiPolygon row (non-contiguous parcels of one site).
  3. Same name, different sections, different geometry (Neighbourhoods x2)
     -> Disambiguate slug with _s{section} suffix.

Prerequisites:
  Run migration first:
    python3 scripts/run_migration_alter_boundary_multipolygon.py
  (changes boundary column from POLYGON to MULTIPOLYGON, preserving existing rows)

Usage:
    python3 scripts/import_cos_dcp_boundaries.py
    python3 scripts/import_cos_dcp_boundaries.py --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

GEOJSON_DIR = Path(__file__).parent.parent / "data" / "boundaries" / "city-of-sydney"

# Each entry: (geojson_file, name_field, precinct_id_prefix, source_doc)
SOURCES = [
    (
        "cos_dcp_locality_areas.geojson",
        "LocalityName",
        "cos_locality",
        "Sydney DCP 2012 Section 2 — Locality Statements",
    ),
    (
        "cos_dcp_specific_areas.geojson",
        "AreaName",
        "cos_specific",
        "Sydney DCP 2012 Section 5 — Specific Areas",
    ),
    (
        "cos_dcp_specific_sites.geojson",
        "SiteName",
        "cos_site",
        "Sydney DCP 2012 Section 6 — Specific Sites",
    ),
]


def slugify(name: str, prefix: str) -> str:
    """Generate a stable precinct_id from name and prefix."""
    slug = name.lower()
    for ch in " /,()&'\"":
        slug = slug.replace(ch, "_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    slug = slug.strip("_")
    return f"{prefix}__{slug}"


def slug_section(section: str) -> str:
    """Sanitise a DCP section value for use as a slug suffix (e.g. '2.10.2' -> 's2_10_2')."""
    s = section.replace(".", "_").replace(" ", "_").strip("_")
    return f"s{s}"


def _geom_coords_equal(g1: dict, g2: dict) -> bool:
    """True if two GeoJSON geometry dicts have identical coordinates."""
    return g1.get("type") == g2.get("type") and g1.get("coordinates") == g2.get("coordinates")


def _merge_to_multipolygon(geoms: list[dict]) -> dict:
    """
    Merge a list of Polygon/MultiPolygon GeoJSON geometries into a single
    MultiPolygon by collecting all rings. No external dependencies needed.
    """
    rings: list = []
    for g in geoms:
        if g["type"] == "Polygon":
            rings.append(g["coordinates"])
        elif g["type"] == "MultiPolygon":
            rings.extend(g["coordinates"])
        else:
            raise ValueError(f"Cannot merge geometry type: {g['type']}")
    return {"type": "MultiPolygon", "coordinates": rings}


def resolve_features(features: list[dict], name_field: str, prefix: str) -> list[tuple[str, str, dict]]:
    """
    Pre-process a feature list to resolve slug collisions.
    Returns list of (precinct_id, precinct_name, geom) tuples ready for insert.

    Three collision cases:
      1. Identical geometry -> deduplicate, keep first.
      2. Same section -> non-contiguous parcels -> merge into MultiPolygon.
      3. Different sections -> genuinely different precincts -> disambiguate with _s{section}.
    """
    # Group by base slug
    slug_groups: dict[str, list[dict]] = {}
    for feat in features:
        props = feat.get("properties") or {}
        geom = feat.get("geometry")
        name = props.get(name_field, "").strip()
        if not name or not geom:
            continue
        slug = slugify(name, prefix)
        slug_groups.setdefault(slug, []).append(feat)

    result: list[tuple[str, str, dict]] = []

    for slug, group in slug_groups.items():
        if len(group) == 1:
            feat = group[0]
            name = feat["properties"].get(name_field, "").strip()
            result.append((slug, name, feat["geometry"]))
            continue

        # Multiple features share this slug
        name = group[0]["properties"].get(name_field, "").strip()
        sections = [f["properties"].get("Section", "") for f in group]
        geoms = [f["geometry"] for f in group]

        # Case 1: identical geometries — deduplicate
        if all(_geom_coords_equal(geoms[0], g) for g in geoms[1:]):
            print(f"  [DEDUP] {slug} — {len(group)} identical geometries, keeping first "
                  f"(sections: {sections})")
            result.append((slug, name, geoms[0]))
            continue

        # Case 2: same section — non-contiguous parcels, merge into MultiPolygon
        if len(set(sections)) == 1:
            merged = _merge_to_multipolygon(geoms)
            print(f"  [MERGE] {slug} — {len(group)} parcels in section '{sections[0]}' "
                  f"merged into MultiPolygon")
            result.append((slug, name, merged))
            continue

        # Case 3: different sections — genuinely different precincts, disambiguate
        print(f"  [DISAMBIG] {slug} — {len(group)} features in different sections {sections}")
        for feat in group:
            section = feat["properties"].get("Section", "")
            disambig_slug = f"{slug}_{slug_section(section)}"
            result.append((disambig_slug, name, feat["geometry"]))

    return result


def import_source(cur, geojson_path: Path, name_field: str, prefix: str, source_doc: str, dry_run: bool) -> int:
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    features = data["features"]

    resolved = resolve_features(features, name_field, prefix)
    inserted = 0

    for precinct_id, name, geom in resolved:
        geom_json = json.dumps(geom)

        if dry_run:
            print(f"  [dry-run] {precinct_id} | {name} | {geom['type']}")
            inserted += 1
            continue

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
                %(precinct_name)s,
                'City of Sydney',
                NULL,
                ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
                %(source_doc)s,
                'api',
                1.0
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
                "precinct_id":   precinct_id,
                "precinct_name": name,
                "geom":          geom_json,
                "source_doc":    source_doc,
            },
        )
        inserted += 1

    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Import CoS DCP boundaries")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing to DB")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    total = 0
    for filename, name_field, prefix, source_doc in SOURCES:
        path = GEOJSON_DIR / filename
        if not path.exists():
            print(f"[ERROR] Not found: {path}")
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        type_counts: dict[str, int] = {}
        for f in data["features"]:
            t = (f.get("geometry") or {}).get("type", "null")
            type_counts[t] = type_counts.get(t, 0) + 1

        print(f"\n[{filename}]")
        print(f"  Features: {len(data['features'])} | Geometry types: {type_counts}")

        n = import_source(cur, path, name_field, prefix, source_doc, args.dry_run)
        print(f"  {'Would insert/upsert' if args.dry_run else 'Inserted/upserted'}: {n}")
        total += n

    if not args.dry_run:
        conn.commit()
        print(f"\nCommitted. Total rows upserted: {total}")
    else:
        conn.rollback()
        print(f"\n[dry-run] Total rows planned: {total}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
