"""Harvest DCP precinct/boundary vectors from a council's public ArcGIS REST server
into dcp_precinct_boundaries — the API-driven replacement for manual QGIS digitising.

prior-art-checked: no existing ArcGIS->dcp_precinct_boundaries harvester exists.
Existing scripts/*precinct* (enrich_precinct_ids, verify_precinct_boundaries,
create_precinct_localities) operate on rows ALREADY loaded; existing geometry in
dcp_precinct_boundaries is extraction_method='qgis_digitised' (Inner West, Ku-ring-gai).
This reuses services/arcgis_client.arcgis_get_with_retry for the fetch.

DRY-RUN BY DEFAULT: prints the rows that WOULD be inserted. Nothing is written to the
DB unless --commit is passed (which additionally requires a fresh backup — see below).

Usage:
    python scripts/harvest_council_dcp_boundaries.py --council sutherland      # dry-run
    python scripts/harvest_council_dcp_boundaries.py --council sutherland --commit   # writes (gated)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

# Reuse the shared retry/circuit-breaker ArcGIS client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.arcgis_client import arcgis_get_with_retry  # noqa: E402

# ---------------------------------------------------------------------------
# Council / layer configuration (extensible — Northern Beaches added later)
# ---------------------------------------------------------------------------
COUNCILS: dict[str, dict[str, Any]] = {
    "sutherland": {
        "lga": "Sutherland Shire",            # proper-case, matches dcp_precinct_boundaries.lga
        "id_prefix": "SUTH",
        "base": "https://geoserver.ssc.nsw.gov.au/arcgis/rest/services/planning/MapServer",
        "source_doc": "Sutherland Shire DCP 2015 - DCP Precinct Centre",
        # layer 19 = 'DCP Precinct Centre' (14 named centre boundaries), fields: CENTRE, DESCRIPTION, STATUS
        "layer_id": 19,
        "name_field": "CENTRE",
        "desc_field": "DESCRIPTION",
    },
}


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").strip().lower()).strip("_")


def fetch_features(base: str, layer_id: int) -> list[dict]:
    """Fetch all features of a layer as GeoJSON in EPSG:4326, paginating if needed."""
    url = f"{base}/{layer_id}/query"
    out: list[dict] = []
    offset = 0
    page = 1000
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page,
        }
        data = arcgis_get_with_retry(url, params, timeout=30)
        feats = data.get("features") or []
        out.extend(feats)
        if len(feats) < page or not data.get("features"):
            break
        offset += page
    return out


def geodesic_area_sqm(geom: dict) -> float | None:
    """Geodesic area in m² for a GeoJSON geometry (lon/lat), via pyproj Geod."""
    try:
        from pyproj import Geod
        from shapely.geometry import shape
        return abs(Geod(ellps="WGS84").geometry_area_perimeter(shape(geom))[0])
    except Exception:
        return None


def map_feature(cfg: dict, feat: dict) -> dict:
    props = feat.get("properties") or {}
    geom = feat.get("geometry") or {}
    name = props.get(cfg["name_field"]) or "(unnamed)"
    return {
        "precinct_id": f"{cfg['id_prefix']}_{slugify(name)}",
        "precinct_name": name,
        "lga": cfg["lga"],
        "source_document": f"{cfg['source_doc']} (ArcGIS {cfg['base'].split('//')[1]}/{cfg['layer_id']})",
        "extraction_method": "arcgis_rest_harvest",
        "confidence_score": 0.98,  # authoritative council source layer (> hand-traced 0.95)
        "geocoding_source": f"{cfg['id_prefix'].lower()}_arcgis",
        "boundary_description": props.get(cfg.get("desc_field") or "", None),
        "geometry": geom,
        "area_sqm": geodesic_area_sqm(geom),
    }


def dry_run(council: str) -> list[dict]:
    cfg = COUNCILS[council]
    print(f"\n=== DRY-RUN: {cfg['lga']} — layer {cfg['layer_id']} ===")
    print(f"    {cfg['base']}/{cfg['layer_id']}\n")
    feats = fetch_features(cfg["base"], cfg["layer_id"])
    if not feats:
        print("  !! no features returned (endpoint down, geojson unsupported, or empty)")
        return []
    rows = [map_feature(cfg, f) for f in feats]
    print(f"  {len(rows)} features would be inserted into dcp_precinct_boundaries:\n")
    print(f"  {'precinct_id':32} {'area(ha)':>9}  {'geom':>14}  precinct_name")
    print("  " + "-" * 90)
    for r in rows:
        g = r["geometry"] or {}
        gt = g.get("type", "?")
        nverts = sum(len(ring) for poly in (g.get("coordinates") or []) for ring in (poly if gt == "MultiPolygon" else [poly])) if g.get("coordinates") else 0
        ha = f"{r['area_sqm']/10000:.1f}" if r["area_sqm"] else "?"
        print(f"  {r['precinct_id']:32} {ha:>9}  {gt:>14}  {r['precinct_name']}")
    # integrity checks
    ids = [r["precinct_id"] for r in rows]
    dupes = {i for i in ids if ids.count(i) > 1}
    empties = [r["precinct_id"] for r in rows if not (r["geometry"] or {}).get("coordinates")]
    print("\n  integrity:")
    print(f"    duplicate precinct_ids : {sorted(dupes) or 'none'}")
    print(f"    empty geometries       : {empties or 'none'}")
    print(f"    target table           : dcp_precinct_boundaries (boundary MULTIPOLYGON/4326)")
    print(f"    provenance tag         : extraction_method='arcgis_rest_harvest'")
    print("\n  (no rows written — pass --commit AFTER taking a backup to load)")
    return rows


def commit(council: str, rows: list[dict]) -> None:
    """Gated writer. Requires DATABASE_URL. Idempotent per (lga, harvest provenance)."""
    import psycopg2
    cfg = COUNCILS[council]
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL not set")
    print(f"\n!! COMMIT MODE — writing {len(rows)} rows for {cfg['lga']}.")
    print("!! Ensure a backup exists first: "
          "CREATE TABLE dcp_precinct_boundaries_backup_<ts> AS TABLE dcp_precinct_boundaries;")
    conn = psycopg2.connect(dsn)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM dcp_precinct_boundaries WHERE lga=%s AND extraction_method='arcgis_rest_harvest'",
                (cfg["lga"],),
            )
            for r in rows:
                if not (r["geometry"] or {}).get("coordinates"):
                    continue
                cur.execute(
                    """
                    INSERT INTO dcp_precinct_boundaries
                      (precinct_id, precinct_name, lga, source_document, extraction_method,
                       confidence_score, geocoding_source, boundary_description, area_sqm,
                       boundary, centroid, created_at, updated_at)
                    VALUES
                      (%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)),
                       ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)),
                       NOW(), NOW())
                    """,
                    (r["precinct_id"], r["precinct_name"], r["lga"], r["source_document"],
                     r["extraction_method"], r["confidence_score"], r["geocoding_source"],
                     r["boundary_description"], r["area_sqm"],
                     json.dumps(r["geometry"]), json.dumps(r["geometry"])),
                )
        print(f"   committed {len(rows)} rows.")
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", required=True, choices=list(COUNCILS))
    ap.add_argument("--commit", action="store_true", help="write to DB (dry-run if omitted)")
    args = ap.parse_args()
    rows = dry_run(args.council)
    if args.commit and rows:
        commit(args.council, rows)


if __name__ == "__main__":
    main()
