#!/usr/bin/env python3
"""Load the Ku-ring-gai Part 14 precinct outlines built by fit_vector_centres.py into dcp_precinct_boundaries.

prior-art-checked: same shape as import_cb_centre_boundaries.py (upsert on (precinct_id, lga), backup first,
proof inside the transaction, rollback on any failure); that loader is fixed to Canterbury-Bankstown's LGA,
envelope and audit addresses, so this carries Ku-ring-gai's.

KEYS
  lga             'Ku-ring-gai' -- what precinct-service matches against the Portal's LGA.
  former_council  'Ku-ring-gai' -- NOT NULL on purpose: ids such as '14D_G1' miss precinct-service's
                  ^14[A-O](_T\\d)?$ fallback pattern, which would attribute a NULL row to another council.
                  councilKey('Ku-ring-gai') = 'ku_ring_gai', the rules' source_council.
PROOF (inside the transaction; any failure rolls everything back)
  a point inside every written outline is found by the site's own lookup;
  the existing 14B_T1 and 14I outlines are still found;
  the address-audit Ku-ring-gai lots (8 Kerela Ave Wahroonga, 44 Barwon Ave South Turramurra) get none of
  the new ids.

Usage:
    python scripts/import_vector_centres.py            # dry run
    python scripts/import_vector_centres.py --commit
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_cb_centre_boundaries as icb  # noqa: E402  (connect, LOOKUP_SQL)

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "ku_ring_gai_precincts" / "centres_vector.geojson"
BACKUP_DIR = REPO / "data" / "db_rollback_backups"
LGA = FORMER_COUNCIL = "Ku-ring-gai"
CONFIDENCE = 0.85
STILL_FOUND = ("14B_T1", "14I")
#: Lot points (ST_PointOnSurface of nsw_cadastre_lots) of the address audit's Ku-ring-gai addresses.
AUDIT_LOT_SQL = """SELECT ST_X(ST_PointOnSurface(l.geom)), ST_Y(ST_PointOnSurface(l.geom))
                     FROM nsw_cadastre_lots l
                    WHERE ST_Contains(l.geom, ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 28356), 4326)) LIMIT 1"""
AUDIT_POINTS_MGA = {"8 Kerela Ave Wahroonga": None, "44 Barwon Ave South Turramurra": None}


def _audit_points() -> dict:
    """Address-register points (MGA56) for the audit addresses, looked up live."""
    import fit_cb_raster_centres as rf
    out = {}
    for label, where in (("8 Kerela Ave Wahroonga", "address LIKE '8 KERELA AVENUE WAHROONGA%'"),
                         ("44 Barwon Ave South Turramurra", "address LIKE '44 BARWON AVENUE SOUTH TURRAMURRA%'")):
        fs = rf._get(rf.ADDR, {"where": where, "outFields": "address", "returnGeometry": "true", "outSR": "28356",
                               "f": "json", "resultRecordCount": 1}).get("features") or []
        if not fs:
            raise SystemExit(f"[ABORT] audit address not in the register: {label}")
        out[label] = (fs[0]["geometry"]["x"], fs[0]["geometry"]["y"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    feats = json.loads(SRC.read_text(encoding="utf-8"))["features"]
    rows = [{"precinct_id": f["properties"]["precinct_id"], "precinct_name": f["properties"]["precinct_name"],
             "geom": json.dumps(f["geometry"]), "source_document": f["properties"]["source"],
             "extraction_method": f["properties"]["method"], "boundary_description": f["properties"]["quote"]}
            for f in feats]
    for r in rows:
        print(f"  {r['precinct_id']:<8} {r['precinct_name']}")
    audit = _audit_points()
    conn = icb.connect()
    try:
        cur = conn.cursor()
        ids = [r["precinct_id"] for r in rows]
        cur.execute("SELECT row_to_json(b) FROM (SELECT precinct_id, lga, former_council, source_document, extraction_method,"
                    " ST_AsGeoJSON(boundary) AS boundary FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = ANY(%s)) b",
                    (LGA, ids))
        before = [x[0] for x in cur.fetchall()]
        print(f"existing rows with these ids: {len(before)}")
        if not a.commit:
            print("dry-run: nothing written (pass --commit)")
            return 0
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bpath = BACKUP_DIR / f"krg_vector_centres_before_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
        bpath.write_text(json.dumps(before, indent=1), encoding="utf-8")
        for r in rows:
            cur.execute("""
                INSERT INTO dcp_precinct_boundaries
                    (precinct_id, precinct_name, lga, former_council, boundary, source_document,
                     extraction_method, confidence_score, boundary_description, created_at, updated_at)
                VALUES (%(precinct_id)s, %(precinct_name)s, %(lga)s, %(fc)s,
                        ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)), %(source_document)s,
                        %(extraction_method)s, %(conf)s, %(boundary_description)s, now(), now())
                ON CONFLICT (precinct_id, lga) DO UPDATE SET
                    precinct_name = EXCLUDED.precinct_name, former_council = EXCLUDED.former_council,
                    boundary = EXCLUDED.boundary, source_document = EXCLUDED.source_document,
                    extraction_method = EXCLUDED.extraction_method, confidence_score = EXCLUDED.confidence_score,
                    boundary_description = EXCLUDED.boundary_description, updated_at = now()
            """, {**r, "lga": LGA, "fc": FORMER_COUNCIL, "conf": CONFIDENCE})
        problems = []
        for pid in list(ids) + list(STILL_FOUND):
            cur.execute("SELECT ST_X(ST_PointOnSurface(boundary)), ST_Y(ST_PointOnSurface(boundary))"
                        " FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s", (LGA, pid))
            pt = cur.fetchone()
            if not pt:
                problems.append(f"{pid}: not in the table after write")
                continue
            cur.execute(icb.LOOKUP_SQL, (pt[0], pt[1], LGA))
            if pid not in {x[0] for x in cur.fetchall()}:
                problems.append(f"{pid}: a point inside it is not found by the site's lookup")
        for label, (x, y) in audit.items():
            cur.execute("SELECT ST_X(p), ST_Y(p) FROM (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 28356), 4326) p) q",
                        (x, y))
            lon, lat = cur.fetchone()
            cur.execute(icb.LOOKUP_SQL, (lon, lat, LGA))
            hit = sorted({x[0] for x in cur.fetchall()} & set(ids))
            print(f"  lookup {label}: {hit or 'none of the new ids'}")
            if hit:
                problems.append(f"{label} now resolves to {hit}")
        if problems:
            conn.rollback()
            print("[ROLLED BACK]\n  " + "\n  ".join(problems))
            return 1
        conn.commit()
        print(f"committed {len(rows)} rows; backup {bpath}; every check passed")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
