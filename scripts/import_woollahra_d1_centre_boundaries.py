#!/usr/bin/env python3
"""Import the land outlines of Woollahra DCP 2015 Chapter D1's nine neighbourhood centres. Dry run unless --commit.

prior-art-checked: dcp_precinct_boundaries held no Woollahra centre (2026-10-15: 15 rows, all HCAs). The live D1 rules
keyed by hand to these centre names (28 rows) therefore reached no address, and the other ~190 reached every one.
Same shape as import_cb_centre_boundaries.py (unique (precinct_id, lga), backup, proof inside the transaction).

THE LAND (data/woollahra_d1_centres/centres.geojson), no model drew anything:
  D1 p7: "This chapter applies to the following centres, as identified on Map A". Each centre is the Woollahra LEP
  2014 zone E1 polygon (spatial_overlays) holding the street numbers that centre's section and map print, named by
  the NSW address register points inside it. Two are not E1 land: South Head Roundabout is the E1 lot 145 New South
  Head Road (MAP 2 shades exactly that lot), and Darling Point Road is the cadastre lot SP2501 holding the one shop
  MAP 9 shades. D1.1 (all centres) is their union. precinct_id = the key the live D1 rules already carry.

PROOF before the transaction commits: every PDF-named address is found in its centre by the site's own lookup, and the
same-street neighbours 17-45 m away are found in none of them.

Usage:  python scripts/import_woollahra_d1_centre_boundaries.py [--commit]
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "woollahra_d1_centres" / "centres.geojson"
BACKUP_DIR = REPO / "data" / "db_rollback_backups"
LGA = "Woollahra"
FORMER_COUNCIL = "Woollahra"
CONFIDENCE = {"lep_zone_e1_named_by_address_register": 0.9, "lep_zone_mu1_named_by_address_register": 0.9, "cadastre_lot_from_dcp_map": 0.8,
              "union_of_d1_centres": 0.9}
LOOKUP_SQL = """SELECT precinct_id FROM dcp_precinct_boundaries
                 WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AND LOWER(lga) = LOWER(%s)"""


def load() -> list[dict]:
    src = Path(sys.argv[sys.argv.index("--src") + 1]) if "--src" in sys.argv else SRC   # D5/D6 centres reuse this
    return json.loads(src.read_text(encoding="utf-8"))["features"]


def prove(cur, feats: list[dict]) -> list[str]:
    """What the site's lookup returns for each test address, against what the plan says it must."""
    ids = {f["properties"]["precinct_id"] for f in feats}
    problems = []
    for f in feats:
        p = f["properties"]
        for addr, (x, y) in p["inside"].items():
            cur.execute(LOOKUP_SQL, (x, y, LGA))
            if p["precinct_id"] not in {r[0] for r in cur.fetchall()}:
                problems.append(f"{addr}: not found in {p['precinct_id']}")
        for addr, (x, y) in p["outside"].items():
            cur.execute(LOOKUP_SQL, (x, y, LGA))
            hit = {r[0] for r in cur.fetchall()} & ids
            if hit:
                problems.append(f"{addr}: neighbour found inside {sorted(hit)}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--src", help="another centres geojson (default: the D1 file)")
    a = ap.parse_args()
    feats = load()
    for f in feats:
        p = f["properties"]
        print(f"  {p['section']:5} {p['precinct_id']:32} {p['area_sqm']:9.0f} m2  {p['method']}")
    load_dotenv(REPO.parents[2] / ".env" if (REPO.parents[2] / ".env").exists() else REPO / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=15, options="-c statement_timeout=30000")
    try:
        cur = conn.cursor()
        cur.execute("SELECT current_database()")
        print(f"database: {cur.fetchone()[0]}")
        ids = [f["properties"]["precinct_id"] for f in feats]
        cur.execute("""SELECT id, precinct_id, precinct_name, lga, ST_AsGeoJSON(boundary) FROM dcp_precinct_boundaries
                        WHERE LOWER(lga) = LOWER(%s) AND precinct_id = ANY(%s)""", (LGA, ids))
        existing = cur.fetchall()
        print(f"existing rows with these ids: {len(existing)}")
        if existing:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            bpath = BACKUP_DIR / f"woollahra_d1_boundaries_before_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
            bpath.write_text(json.dumps([list(map(str, r)) for r in existing], indent=1), encoding="utf-8")
            print(f"backup: {bpath}")
        for f in feats:
            p = f["properties"]
            cur.execute("""
                INSERT INTO dcp_precinct_boundaries
                    (precinct_id, precinct_name, lga, former_council, boundary, centroid, source_document,
                     extraction_method, confidence_score, boundary_description, area_sqm, perimeter_m,
                     created_at, updated_at)
                VALUES (%(id)s, %(name)s, %(lga)s, %(fc)s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
                        ST_PointOnSurface(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)), %(src)s, %(method)s,
                        %(conf)s, %(quote)s, %(area)s, %(per)s, now(), now())
                ON CONFLICT (precinct_id, lga) DO UPDATE SET
                    precinct_name = EXCLUDED.precinct_name, boundary = EXCLUDED.boundary, centroid = EXCLUDED.centroid,
                    source_document = EXCLUDED.source_document, extraction_method = EXCLUDED.extraction_method,
                    confidence_score = EXCLUDED.confidence_score, boundary_description = EXCLUDED.boundary_description,
                    area_sqm = EXCLUDED.area_sqm, perimeter_m = EXCLUDED.perimeter_m, updated_at = now()
            """, {"id": p["precinct_id"], "name": p["precinct_name"], "lga": LGA, "fc": FORMER_COUNCIL,
                  "geom": json.dumps(f["geometry"]), "src": p["source"], "method": p["method"],
                  "conf": CONFIDENCE[p["method"]], "quote": p["quote"], "area": p["area_sqm"],
                  "per": p["perimeter_m"]})
        problems = prove(cur, feats)
        for pr in problems:
            print(f"  [PROOF FAILED] {pr}")
        print(f"proof: {'PASS' if not problems else f'{len(problems)} failure(s)'} "
              f"({sum(len(f['properties']['inside']) for f in feats)} inside, "
              f"{sum(len(f['properties']['outside']) for f in feats)} outside)")
        if problems or not a.commit:
            conn.rollback()
            print("rolled back" + ("" if problems else " (dry run: pass --commit)"))
            return 1 if problems else 0
        conn.commit()
        print(f"committed {len(feats)} outlines")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
