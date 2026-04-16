#!/usr/bin/env python3
"""
Ingest NSW Spatial Services planning layers into spatial_overlays table.

Phase 1: IWLEP zone layer only (LGA_NAME='Inner West')
Phase 2: All IWLEP layers + SEPPs statewide

Usage:
    python scripts/ingest_spatial_overlays.py --lga "Inner West" --layer zone
    python scripts/ingest_spatial_overlays.py --all-layers --lga "Inner West"
    python scripts/ingest_spatial_overlays.py --all-layers  # full NSW
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from shapely.geometry import shape

load_dotenv()

BASE_URLS = {
    "Planning": "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning",
    "Fire":     "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire",
}

# Maps source_council slug -> ArcGIS LGA_NAME value (verified)
# Ashfield, Leichhardt, Marrickville are all Inner West LGA post-merger
LGA_NAME_MAP = {
    "inner_west":    "INNER WEST",
    "ashfield":      "INNER WEST",
    "leichhardt":    "INNER WEST",
    "marrickville":  "INNER WEST",
    "city_of_sydney": "SYDNEY",
    "ku_ring_gai":   "KU-RING-GAI",
    "waverley":      "WAVERLEY",
    "woollahra":     "WOOLLAHRA",
}

# All NSW LGAs (129 total) — verified from ArcGIS zone layer 2026-04-13
# Greater Sydney (33) + Regional NSW (96) — excludes LORD HOWE ISLAND (no planning data)
ALL_LGA_NAMES = sorted([
    # Greater Sydney
    "INNER WEST", "SYDNEY", "KU-RING-GAI", "WAVERLEY", "WOOLLAHRA",
    "BAYSIDE", "BLACKTOWN", "BLUE MOUNTAINS", "BURWOOD", "CAMDEN",
    "CAMPBELLTOWN", "CANADA BAY", "CANTERBURY-BANKSTOWN", "CITY OF PARRAMATTA",
    "CUMBERLAND", "FAIRFIELD", "GEORGES RIVER", "HAWKESBURY", "HORNSBY",
    "HUNTERS HILL", "LANE COVE", "LIVERPOOL", "MOSMAN", "NORTH SYDNEY",
    "NORTHERN BEACHES", "PENRITH", "RANDWICK", "RYDE", "STRATHFIELD",
    "SUTHERLAND SHIRE", "THE HILLS SHIRE", "WILLOUGHBY", "WOLLONDILLY",
    # Regional NSW
    "ALBURY CITY", "ARMIDALE REGIONAL", "BALLINA", "BALRANALD",
    "BATHURST REGIONAL", "BEGA VALLEY", "BELLINGEN", "BERRIGAN",
    "BLAND", "BLAYNEY", "BOGAN", "BOURKE", "BREWARRINA", "BROKEN HILL",
    "BYRON", "CABONNE", "CARRATHOOL", "CENTRAL COAST", "CENTRAL DARLING",
    "CESSNOCK", "CLARENCE VALLEY", "COBAR", "COFFS HARBOUR", "COOLAMON",
    "COONAMBLE", "COOTAMUNDRA-GUNDAGAI REGIONAL", "COWRA", "DUBBO REGIONAL",
    "DUNGOG", "EDWARD RIVER", "EUROBODALLA", "FEDERATION", "FORBES",
    "GILGANDRA", "GLEN INNES SEVERN", "GOULBURN MULWAREE", "GREATER HUME SHIRE",
    "GRIFFITH", "GUNNEDAH", "GWYDIR", "HAY", "HILLTOPS", "INVERELL",
    "JUNEE", "KEMPSEY", "KIAMA", "KYOGLE", "LACHLAN", "LAKE MACQUARIE",
    "LEETON", "LISMORE", "LITHGOW CITY", "LIVERPOOL PLAINS", "LOCKHART",
    "MAITLAND", "MID-COAST", "MID-WESTERN REGIONAL", "MOREE PLAINS",
    "MURRAY RIVER", "MURRUMBIDGEE", "MUSWELLBROOK", "NAMBUCCA VALLEY",
    "NARRABRI", "NARRANDERA", "NARROMINE", "NEWCASTLE", "OBERON",
    "ORANGE", "PARKES", "PORT MACQUARIE-HASTINGS", "PORT STEPHENS",
    "QUEANBEYAN-PALERANG REGIONAL", "RICHMOND VALLEY", "SHELLHARBOUR",
    "SHOALHAVEN", "SINGLETON", "SNOWY MONARO REGIONAL", "SNOWY VALLEYS",
    "TAMWORTH REGIONAL", "TEMORA", "TENTERFIELD", "TWEED", "UPPER HUNTER",
    "UPPER LACHLAN SHIRE", "URALLA", "WAGGA WAGGA", "WALCHA", "WALGETT",
    "WARREN", "WARRUMBUNGLE", "WEDDIN", "WENTWORTH", "WINGECARRIBEE",
    "WOLLONGONG", "YASS VALLEY",
])

# ArcGIS layer config — verified field names
# Principal_Planning_Layers/MapServer: GET ?f=json for layer index
# Protection/MapServer, Hazard/MapServer: same pattern
LAYER_CONFIG = {
    # LEP layers
    "zone":         {"service": "Principal_Planning_Layers", "layer_id": 11, "value_field": "SYM_CODE"},
    "heritage":     {"service": "Principal_Planning_Layers", "layer_id": 8,  "value_field": "CLASSIFCTN"},
    "height":       {"service": "Principal_Planning_Layers", "layer_id": 7,  "value_field": "MAX_B_H_M", "numeric": True},
    "fsr":          {"service": "Principal_Planning_Layers", "layer_id": 4,  "value_field": "SYM_CODE"},
    "lot_size":     {"service": "Principal_Planning_Layers", "layer_id": 14, "value_field": "LOT_SIZE", "numeric": True},
    # Protection layers
    "acid_sulfate": {"service": "Protection", "layer_id": 1,  "value_field": "LAY_CLASS"},
    "biodiversity": {"service": "Protection", "layer_id": 10, "value_field": "LAY_CLASS"},
    "riparian":     {"service": "Protection", "layer_id": 7,  "value_field": "LAY_CLASS"},
    "wetlands":     {"service": "Protection", "layer_id": 11, "value_field": "LAY_CLASS"},
    # Hazard layers
    "flood":        {"service": "Hazard",     "layer_id": 1,  "value_field": "LAY_CLASS"},
    "landslide":    {"service": "Hazard",     "layer_id": 2,  "value_field": "LAY_CLASS"},
    # Development Control layers
    "additional_permitted_uses": {"service": "Development_Control", "layer_id": 5, "value_field": "APU_CODE"},
    "active_street_frontages":   {"service": "Development_Control", "layer_id": 4, "value_field": "LAY_CLASS"},
    "key_sites":                 {"service": "Development_Control", "layer_id": 6, "value_field": "LAY_CLASS"},
    # Additional LEP layers
    "land_reservation":          {"service": "Principal_Planning_Layers", "layer_id": 16, "value_field": "LAY_CLASS"},
    "foreshore_building_line":   {"service": "Principal_Planning_Layers", "layer_id": 18, "value_field": "LAY_CLASS"},
    # Bushfire — no LGA_NAME field, use bbox for Greater Sydney
    # bbox: minLon, minLat, maxLon, maxLat (EPSG:4283 ~= 4326)
    "bushfire": {
        "base": "Fire", "service": "BFPL", "layer_id": 0,
        "value_field": "d_Category",
        "filter_mode": "bbox",
        "bbox": "150.5,-34.3,151.6,-33.4",
    },
    # ANEF — 29 features statewide, ingest all
    "anef": {
        "service": "Protection", "layer_id": 2,
        "value_field": "ANEF_CODE",
        "filter_mode": "all",
    },
    # TOD (Transport Oriented Development) — SEPP Housing 2021 statewide maps
    # Replaces walking-distance approximation with actual precinct polygon intersection
    "tod_precinct": {
        "service": "SEPP_Housing_2021", "layer_id": 3,
        "value_field": "LAY_CLASS",
        "filter_mode": "all",
    },
    "tod_accelerated": {
        "service": "SEPP_Housing_2021", "layer_id": 4,
        "value_field": "LAY_CLASS",
        "filter_mode": "all",
    },
    "tod_deferred": {
        "service": "SEPP_Housing_2021", "layer_id": 5,
        "value_field": "LAY_CLASS",
        "filter_mode": "all",
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Council-published FeatureServer layers
# These are hosted on council ArcGIS Online organisations, not mapprod3.
# Coordinates are returned in WGS84 (outSR=4326 requested) so no reprojection needed.
# ──────────────────────────────────────────────────────────────────────────────
COUNCIL_FEATURESERVER_CONFIG: dict[str, dict] = {
    # Inner West Council — Special Entertainment Precincts
    # Source: services-ap1.arcgis.com/dp2UIID5MUpTUFVA (public, 10,950 views confirmed)
    # Layer 19 of Adopted_Planning_Layers FeatureServer
    # 159 polygon features — adopted + draft SEPs across Inner West LGA
    "sep": {
        "base_url": "https://services-ap1.arcgis.com/dp2UIID5MUpTUFVA/arcgis/rest/services/Adopted_Planning_Layers/FeatureServer",
        "layer_id": 19,
        "value_field": "LAY_CLASS",       # "Inner West Special Entertainment Precinct" | "Draft Special Entertainment Precinct"
        "instrument_field": "EPI_NAME",   # "Inner West Local Environmental Plan 2022"
        "lga_name": "INNER WEST",
        "description": "Inner West Special Entertainment Precincts (LEP 2022)",
    },
}


def fetch_page(service: str, layer_id: int, where: str, offset: int, base: str = "Planning", bbox: str | None = None) -> dict:
    import time
    base_url = BASE_URLS.get(base, BASE_URLS["Planning"])
    url = f"{base_url}/{service}/MapServer/{layer_id}/query"
    params: dict = {
        "returnGeometry": "true",
        "outFields": "*",
        "resultOffset": offset,
        "resultRecordCount": 1000,
        "f": "geojson",
    }
    if bbox:
        params["geometry"] = bbox
        params["geometryType"] = "esriGeometryEnvelope"
        params["inSR"] = "4283"
        params["spatialRel"] = "esriSpatialRelIntersects"
        params["where"] = "1=1"
    else:
        params["where"] = where
    for attempt in range(3):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 500:
            wait = 10 * (attempt + 1)
            print(f"    [warn] 500 from ArcGIS (attempt {attempt+1}/3) — retrying in {wait}s ...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    # All retries exhausted — return empty to skip this LGA/layer
    print(f"    [skip] 500 after 3 retries — skipping offset={offset}")
    return {"features": []}


def fetch_page_by_oids(service: str, layer_id: int, oids: list[int], base: str = "Planning") -> dict:
    base_url = BASE_URLS.get(base, BASE_URLS["Planning"])
    url = f"{base_url}/{service}/MapServer/{layer_id}/query"
    params = {
        "objectIds": ",".join(str(o) for o in oids),
        "returnGeometry": "true",
        "outFields": "*",
        "f": "geojson",
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def parse_currency_date(val) -> date | None:
    if not val:
        return None
    try:
        # May come as "YYYY-MM-DD" or epoch ms
        if isinstance(val, (int, float)):
            from datetime import datetime
            return datetime.utcfromtimestamp(val / 1000).date()
        return date.fromisoformat(str(val)[:10])
    except Exception:
        return None


def geom_to_multipolygon_wkt(geojson_geom: dict) -> str | None:
    """Convert GeoJSON geometry to MultiPolygon WKT, normalising type."""
    try:
        geom = shape(geojson_geom)
        if geom.is_empty:
            return None
        if geom.geom_type == "Polygon":
            from shapely.geometry import MultiPolygon
            geom = MultiPolygon([geom])
        elif geom.geom_type not in ("MultiPolygon",):
            # Unexpected type — skip
            return None
        return geom.wkt
    except Exception:
        return None


def fetch_page_featureserver(base_url: str, layer_id: int, offset: int) -> dict:
    """Fetch a page of features from a council ArcGIS FeatureServer.

    Requests outSR=4326 so the server reprojects from the council's native CRS
    (typically WKID 28356 — GDA94 MGA Zone 56) to WGS84 before returning.
    """
    import time
    url = f"{base_url}/{layer_id}/query"
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "resultOffset": offset,
        "resultRecordCount": 1000,
        "f": "geojson",
    }
    for attempt in range(3):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 500:
            wait = 10 * (attempt + 1)
            print(f"    [warn] 500 from council FeatureServer (attempt {attempt+1}/3) — retrying in {wait}s ...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    print(f"    [skip] 500 after 3 retries — skipping offset={offset}")
    return {"features": []}


def ingest_council_layer(cur, layer_type: str, dry_run: bool = False) -> int:
    """Ingest a layer from a council-published ArcGIS FeatureServer."""
    config = COUNCIL_FEATURESERVER_CONFIG[layer_type]
    base_url = config["base_url"]
    layer_id = config["layer_id"]
    value_field = config["value_field"]
    instrument_field = config.get("instrument_field", "EPI_NAME")
    lga_name = config["lga_name"]

    offset = 0
    total = 0
    print(f"  Fetching council layer '{layer_type}' ({config['description']}) ...")

    while True:
        data = fetch_page_featureserver(base_url, layer_id, offset)
        features = data.get("features", [])
        if not features:
            break

        rows = []
        for f in features:
            props = f.get("properties") or f.get("attributes") or {}
            geojson_geom = f.get("geometry")
            if not geojson_geom:
                continue

            wkt = geom_to_multipolygon_wkt(geojson_geom)
            if not wkt:
                continue

            value_str = str(props[value_field]) if props.get(value_field) is not None else None
            instrument_key = props.get(instrument_field) or "unknown"
            source_oid = props.get("OBJECTID")
            currency_date = parse_currency_date(
                props.get("CURRENCY_DATE") or props.get("COMMENCED_DATE")
            )

            rows.append((
                instrument_key,
                lga_name,
                layer_type,
                value_str,
                None,   # value_numeric — not applicable for SEP
                currency_date,
                source_oid,
                wkt,
            ))

        if rows and not dry_run:
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

        total += len(rows)
        print(f"    offset={offset} -> {len(rows)} features (total: {total})")

        if not data.get("exceededTransferLimit", False):
            break
        offset += 1000

    return total


def ingest_layer(
    cur,
    layer_type: str,
    lga_name: str | None = None,
    dry_run: bool = False,
) -> int:
    config = LAYER_CONFIG[layer_type]
    service = config["service"]
    layer_id = config["layer_id"]
    value_field = config["value_field"]
    is_numeric = config.get("numeric", False)
    base = config.get("base", "Planning")
    filter_mode = config.get("filter_mode", "lga")  # "lga" | "bbox" | "all"
    bbox = config.get("bbox")

    if filter_mode == "bbox":
        where = "1=1"
    elif filter_mode == "all":
        where = "1=1"
        lga_name = None  # don't filter by LGA
    else:
        where = f"LGA_NAME='{lga_name}'" if lga_name else "1=1"

    offset = 0
    total = 0
    use_bbox = filter_mode == "bbox"
    label = f"bbox={bbox}" if use_bbox else f"where={where!r}"
    print(f"  Fetching {layer_type} layer (service={service}, layer={layer_id}, {label}) ...")

    # For bbox layers, ArcGIS 500s on offset pagination — use OID-range batching instead
    oid_batches: list[list[int]] | None = None
    if use_bbox:
        base_url = BASE_URLS.get(base, BASE_URLS["Planning"])
        url = f"{base_url}/{service}/MapServer/{layer_id}/query"
        oid_resp = requests.get(url, params={
            "geometry": bbox, "geometryType": "esriGeometryEnvelope",
            "inSR": "4283", "spatialRel": "esriSpatialRelIntersects",
            "where": "1=1", "returnIdsOnly": "true", "f": "json",
        }, timeout=60)
        oid_resp.raise_for_status()
        all_oids = sorted(oid_resp.json().get("objectIds") or [])
        print(f"    {len(all_oids)} OIDs retrieved, batching in 500s ...")
        oid_batches = [all_oids[i:i+500] for i in range(0, len(all_oids), 500)]

    batch_iter = iter(oid_batches) if oid_batches else None

    while True:
        if batch_iter is not None:
            batch = next(batch_iter, None)
            if batch is None:
                break
            data = fetch_page_by_oids(service, layer_id, batch, base=base)
        else:
            data = fetch_page(service, layer_id, where, offset, base=base, bbox=None)
        features = data.get("features", [])

        if not features:
            break

        rows = []
        for f in features:
            props = f.get("properties") or f.get("attributes") or {}
            geojson_geom = f.get("geometry")

            if not geojson_geom:
                continue

            wkt = geom_to_multipolygon_wkt(geojson_geom)
            if not wkt:
                continue

            raw_value = props.get(value_field)
            value_str = str(raw_value) if raw_value is not None else None
            value_num = None
            if is_numeric and raw_value is not None:
                try:
                    value_num = float(raw_value)
                except (TypeError, ValueError):
                    pass

            instrument_key = props.get("EPI_NAME") or props.get("INSTRUMENT_NAME") or "unknown"
            feat_lga = props.get("LGA_NAME") or lga_name
            currency_date = parse_currency_date(props.get("CURRENCY_DATE") or props.get("DATE_CURRENCY"))
            source_oid = props.get("OBJECTID")

            rows.append((
                instrument_key,
                feat_lga,
                layer_type,
                value_str,
                value_num,
                currency_date,
                source_oid,
                wkt,
            ))

        if rows and not dry_run:
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

        total += len(rows)
        print(f"    batch/offset={offset} -> {len(rows)} features (total so far: {total})")

        if batch_iter is None:
            if not data.get("exceededTransferLimit", False):
                break
            offset += 1000

    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lga", help="Single ArcGIS LGA_NAME (e.g. 'WAVERLEY'). Omit for all onboarded LGAs.")
    parser.add_argument("--layer", choices=list(LAYER_CONFIG.keys()), help="Single mapprod3 layer to ingest")
    parser.add_argument("--all-layers", action="store_true", help="Ingest all configured mapprod3 layers")
    parser.add_argument("--council-layer", choices=list(COUNCIL_FEATURESERVER_CONFIG.keys()),
                        help="Single council FeatureServer layer to ingest (e.g. 'sep')")
    parser.add_argument("--all-council-layers", action="store_true", help="Ingest all council FeatureServer layers")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not write to DB")
    args = parser.parse_args()

    if not args.layer and not args.all_layers and not args.council_layer and not args.all_council_layers:
        parser.error("Specify --layer <name>, --all-layers, --council-layer <name>, or --all-council-layers")

    mapprod3_layers = list(LAYER_CONFIG.keys()) if args.all_layers else ([args.layer] if args.layer else [])
    council_layers = list(COUNCIL_FEATURESERVER_CONFIG.keys()) if args.all_council_layers else ([args.council_layer] if args.council_layer else [])
    lgas = [args.lga] if args.lga else ALL_LGA_NAMES

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    try:
        # Council FeatureServer layers (SEP etc.)
        for layer_type in council_layers:
            print(f"\n[COUNCIL / {layer_type.upper()}]")
            try:
                count = ingest_council_layer(cur, layer_type, dry_run=args.dry_run)
                if not args.dry_run:
                    conn.commit()
                print(f"  Done: {count} features {'(dry run)' if args.dry_run else 'upserted'}")
            except Exception as e:
                conn.rollback()
                print(f"  [ERROR] council/{layer_type}: {e} — skipping")

        for layer_type in mapprod3_layers:
            config = LAYER_CONFIG[layer_type]
            filter_mode = config.get("filter_mode", "lga")
            if filter_mode in ("bbox", "all"):
                # Single global ingest — not per-LGA
                print(f"\n[GLOBAL / {layer_type.upper()}]")
                count = ingest_layer(cur, layer_type, lga_name=None, dry_run=args.dry_run)
                if not args.dry_run:
                    conn.commit()
                print(f"  Done: {count} features {'(dry run -- not written)' if args.dry_run else 'upserted'}")
            else:
                for lga in lgas:
                    print(f"\n[{lga} / {layer_type.upper()}]")
                    try:
                        count = ingest_layer(cur, layer_type, lga_name=lga, dry_run=args.dry_run)
                        if not args.dry_run:
                            conn.commit()
                        print(f"  Done: {count} features {'(dry run -- not written)' if args.dry_run else 'upserted'}")
                    except Exception as e:
                        conn.rollback()
                        print(f"  [ERROR] {lga}/{layer_type}: {e} — skipping")

        # Verify
        if not args.dry_run:
            cur.execute("SELECT layer_type, COUNT(*) FROM spatial_overlays GROUP BY layer_type ORDER BY layer_type")
            print("\n[DB COUNTS]")
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
