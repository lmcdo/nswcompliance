#!/usr/bin/env python3
"""Load the Ku-ring-gai DCP Part 18R.1 Greenweb polygons into spatial_overlays.

prior-art-checked: reuse not viable. scripts/ingest_spatial_overlays.py pulls NSW Planning Portal
FeatureServer layers by service URL; Greenweb is a council DCP map with no service, registered by hand
from the PDF map sheets to the cadastre (data/krg_greenweb/greenweb_2021.geojson.gz). No script writes
layer_type 'greenweb' (grep of scripts/ and migrations/, 2026-10-20).

Dry run by default: reads the file, validates it, reads the table, prints what --commit would do, writes
nothing and opens the connection read-only. --commit backs up the existing 'greenweb' rows of this LGA
to data/db_rollback_backups/ and then replaces them (DELETE ... WHERE layer_type = 'greenweb' AND
lga_name = 'KU-RING-GAI', then INSERT) in ONE transaction.

Columns match spatial_overlays as read 2026-10-20: instrument_key (NOT NULL), lga_name, layer_type
(NOT NULL), value, value_numeric, currency_date, geom (MULTIPOLYGON, 4326), synced_at, source_oid.
(instrument_key, layer_type, source_oid) is UNIQUE, so source_oid is the 1-based feature index.

Source / currency note (the table has no note column; it is kept here and in the backup manifest):
the maps are the Greenweb sheets of Ku-ring-gai DCP Part 18R.1, consolidated 2021-07-21. Registration
to the cadastre is approximate (linework correlation about 0.9; IoU 0.976 against the LEP biodiversity
layer for the four categories the LEP also maps). A lot is flagged when any part of it overlaps a patch.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parents[1]
GEOJSON = REPO / "data" / "krg_greenweb" / "greenweb_2021.geojson.gz"  # gzip: the repo caps files at 2 MB
BACKUP_DIR = REPO / "data" / "db_rollback_backups"

LAYER_TYPE = "greenweb"
LGA_NAME = "KU-RING-GAI"
INSTRUMENT_KEY = "Ku-ring-gai DCP Part 18R.1 Greenweb maps"
CURRENCY_DATE = date(2021, 7, 21)
EXPECTED_CATEGORIES = {
    "core", "support", "landscape (remnant)", "corridor (and buffer)", "canopy (remnant)",
}
_TIMEOUT_MS = 30_000


def load_features(path: Path = GEOJSON) -> list[dict]:
    """Features of the file, or raise if it is not the five Greenweb categories."""
    import gzip
    raw = path.read_bytes()
    fc = json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)
    feats = fc.get("features") or []
    cats = [f["properties"]["category"] for f in feats]
    if set(cats) != EXPECTED_CATEGORIES or len(cats) != len(set(cats)):
        raise ValueError(f"expected exactly {sorted(EXPECTED_CATEGORIES)}, file has {sorted(cats)}")
    for f in feats:
        if f["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"{f['properties']['category']}: geometry is {f['geometry']['type']}")
    return feats


def _connect(readonly: bool):
    import os

    from dotenv import load_dotenv
    import psycopg2

    from dq_db import main_checkout

    load_dotenv(main_checkout() / ".env")
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("No DATABASE_URL")
    conn = psycopg2.connect(url, connect_timeout=15)
    conn.set_session(readonly=readonly)
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {_TIMEOUT_MS}")
    return conn


def existing_rows(cur) -> list[tuple]:
    cur.execute(
        "SELECT id, instrument_key, lga_name, layer_type, value, value_numeric, currency_date, synced_at,"
        " source_oid, ST_AsGeoJSON(geom) FROM spatial_overlays WHERE layer_type = %s",
        (LAYER_TYPE,),
    )
    return cur.fetchall()


def backup_existing(rows: list[tuple], stamp: str) -> Path:
    """Write the existing 'greenweb' rows (with geometry) to data/db_rollback_backups/."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"spatial_overlays_greenweb_pre_load_{stamp}.json"
    cols = ["id", "instrument_key", "lga_name", "layer_type", "value", "value_numeric",
            "currency_date", "synced_at", "source_oid", "geom_geojson"]
    path.write_text(
        json.dumps({"table": "spatial_overlays", "where": f"layer_type = '{LAYER_TYPE}'",
                    "rows": [dict(zip(cols, r)) for r in rows]}, default=str),
        encoding="utf-8",
    )
    return path


INSERT_SQL = (
    "INSERT INTO spatial_overlays (instrument_key, lga_name, layer_type, value, currency_date, geom, source_oid)"
    " VALUES (%s, %s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), %s)"
)


def run(commit: bool) -> int:
    feats = load_features()
    size_mb = GEOJSON.stat().st_size / 1e6
    print(f"file: {GEOJSON.relative_to(REPO)}  {size_mb:.2f} MB  {len(feats)} features")

    conn = _connect(readonly=not commit)
    try:
        cur = conn.cursor()
        # Geometry validity and area, computed by PostGIS from the file itself (no write).
        report = []
        for f in feats:
            cur.execute(
                "SELECT ST_IsValid(g), ST_NumGeometries(ST_Multi(g)),"
                " ST_Area(ST_Transform(g, 28356)) / 10000.0"
                " FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) AS g) t",
                (json.dumps(f["geometry"]),),
            )
            valid, parts, ha = cur.fetchone()
            report.append((f["properties"]["category"], valid, parts, ha))
            print(f"  {f['properties']['category']:<24} valid={valid} parts={parts:<5} area={ha:,.1f} ha")
        if not all(r[1] for r in report):
            print("ABORT: an invalid geometry would be loaded")
            return 1

        rows = existing_rows(cur)
        print(f"existing layer_type='{LAYER_TYPE}' rows: {len(rows)}")
        print(f"would DELETE {sum(1 for r in rows if r[2] == LGA_NAME)} rows (layer_type='{LAYER_TYPE}' "
              f"AND lga_name='{LGA_NAME}') and INSERT {len(feats)} rows "
              f"(instrument_key='{INSTRUMENT_KEY}', currency_date={CURRENCY_DATE})")
        if not commit:
            print("DRY RUN: nothing written. Re-run with --commit to apply.")
            return 0

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        print(f"backup: {backup_existing(rows, stamp)}")
        cur.execute("DELETE FROM spatial_overlays WHERE layer_type = %s AND lga_name = %s",
                    (LAYER_TYPE, LGA_NAME))
        for i, f in enumerate(feats, start=1):
            cur.execute(INSERT_SQL, (INSTRUMENT_KEY, LGA_NAME, LAYER_TYPE, f["properties"]["category"],
                                     CURRENCY_DATE, json.dumps(f["geometry"]), i))
        conn.commit()
        print(f"committed: {len(feats)} rows")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commit", action="store_true", help="back up, then replace the greenweb rows (default: dry run)")
    return run(ap.parse_args().commit)


if __name__ == "__main__":
    sys.exit(main())
