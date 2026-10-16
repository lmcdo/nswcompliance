#!/usr/bin/env python3
"""Load one DCP area outline from a Planning Portal LEP map layer (the council's own legal map).

prior-art-checked: reuse not viable -- import_cb_centre_boundaries.py and import_vector_centres.py hard-code their
council (LGA constants, envelope, audit addresses); this takes the layer, filter and council as arguments. Same
write shape: upsert on (precinct_id, lga), backup first, proof inside the transaction (the site's own lookup finds
the outline; listed outside addresses stay outside).

    python scripts/import_lep_map_outline.py --layer Planning_Portal_Local_Provisions/437 \
      --where "EPI_NAME='Warringah Local Environmental Plan 2011' AND LAY_CLASS='Dee Why Town Centre'" \
      --precinct-id "G1 Dee Why Town Centre" --lga "Northern Beaches" --outside 151.2496,-33.7398
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/"
BACKUP_DIR = Path(__file__).resolve().parent.parent / "data" / "db_rollback_backups"
LOOKUP = ("SELECT precinct_id FROM dcp_precinct_boundaries WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(%s,%s),4326))"
          " AND LOWER(lga) = LOWER(%s)")


def fetch(layer: str, where: str) -> dict:
    svc, lid = layer.rsplit("/", 1)
    q = urllib.parse.urlencode({"where": where, "outFields": "*", "returnGeometry": "true", "outSR": 4326, "f": "geojson"})
    for attempt in range(4):
        try:
            req = urllib.request.Request(f"{BASE}{svc}/MapServer/{lid}/query?{q}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001 - retried, then raised
            if attempt == 3:
                raise
            time.sleep(3)
    raise RuntimeError("unreachable")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True)
    ap.add_argument("--where", required=True)
    ap.add_argument("--precinct-id", required=True)
    ap.add_argument("--lga", required=True, help="as the Planning Portal names it, e.g. 'Northern Beaches'")
    ap.add_argument("--outside", action="append", default=[], help="lon,lat that must stay outside")
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    feats = fetch(a.layer, a.where).get("features") or []
    if not feats:
        raise SystemExit("[ABORT] the layer returned no shapes for that filter -- never guess a boundary")
    geom = unary_union([shape(f["geometry"]) for f in feats])
    print(f"{len(feats)} shape(s); bounds {tuple(round(b, 5) for b in geom.bounds)}")
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = 30000")
        cur.execute("SELECT row_to_json(b) FROM (SELECT * FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s) b",
                    (a.lga, a.precinct_id))
        before = [r[0] for r in cur.fetchall()]
        if not a.commit:
            print(f"dry run: would upsert '{a.precinct_id}' ({a.lga}); existing rows {len(before)}")
            return 0
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bk = BACKUP_DIR / f"lep_outline_{a.precinct_id.replace(' ', '_')}_pre_{datetime.now():%Y-%m-%dT%H%M%S}.json"
        bk.write_text(json.dumps(before, default=str), encoding="utf-8")
        cur.execute("""INSERT INTO dcp_precinct_boundaries (precinct_id, precinct_name, lga, former_council, boundary, centroid,
                         source_document, extraction_method, confidence_score, boundary_description, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)),
                               ST_PointOnSurface(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326)), %s, 'nsw_planning_local_provisions', 1.0, %s, now(), now())
                       ON CONFLICT (precinct_id, lga) DO UPDATE SET boundary = EXCLUDED.boundary, centroid = EXCLUDED.centroid,
                         source_document = EXCLUDED.source_document, boundary_description = EXCLUDED.boundary_description, updated_at = now()""",
                    (a.precinct_id, a.precinct_id, a.lga, a.lga, json.dumps(mapping(geom)), json.dumps(mapping(geom)),
                     f"NSW Planning Portal {a.layer}", a.where))
        p = geom.representative_point()
        cur.execute(LOOKUP, (p.x, p.y, a.lga))
        problems = [] if a.precinct_id in {r[0] for r in cur.fetchall()} else ["a point inside is not found by the lookup"]
        for o in a.outside:
            x, y = map(float, o.split(","))
            cur.execute(LOOKUP, (x, y, a.lga))
            if a.precinct_id in {r[0] for r in cur.fetchall()}:
                problems.append(f"outside point {o} resolves to the outline")
        if problems:
            conn.rollback()
            print("[ROLLED BACK] " + "; ".join(problems))
            return 1
        conn.commit()
        print(f"committed '{a.precinct_id}'; backup {bk}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
