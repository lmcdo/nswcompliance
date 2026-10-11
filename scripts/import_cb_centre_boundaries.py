#!/usr/bin/env python3
"""Load the three Canterbury-Bankstown centre outlines into dcp_precinct_boundaries.

prior-art-checked: modelled on import_parramatta_part8_boundaries.py (upsert on the
(precinct_id, lga) unique key, former_council set, proof-after-write). The geometry is built
and documented by scripts/build_cb_centre_boundaries.py; this only loads the committed file.

KEYS (each one load-bearing, measured 2026-10-11)
  lga             'Canterbury-Bankstown' -- precinct-service matches LOWER(lga) against the
                  Planning Portal's 'CANTERBURY-BANKSTOWN'.
  former_council  'Canterbury-Bankstown' -- NOT NULL on purpose: a NULL falls back to
                  PRECINCT_ID_PATTERNS, whose default is 'Marrickville', and '6.2' would also
                  match the City of Sydney pattern. councilKey() turns this into
                  'canterbury_bankstown', the rules' source_council.
  precinct_id     the DCP chapter number ('6.2', '7.5', '7.6'), the same value
                  derive_precinct_keys.py writes onto the chapters' rules.

Usage:
    python scripts/import_cb_centre_boundaries.py            # dry-run: prints what it would write
    python scripts/import_cb_centre_boundaries.py --commit   # backup, upsert, prove
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "canterbury_bankstown_precincts" / "centres.geojson"
BACKUP_DIR = REPO / "data" / "db_rollback_backups"

LGA = "Canterbury-Bankstown"
FORMER_COUNCIL = "Canterbury-Bankstown"
EXPECTED_IDS = {"6.2", "7.5", "7.6"}
#: The Planning Portal's state outline is the council's legal map layer (1.0). A figure fitted to
#: the cadastre is positionally ~4 m, and doubtful lots were kept, so it is recorded lower.
CONFIDENCE = {"nsw_planning_local_provisions": 1.0, "dcp_figure_georeferenced_to_cadastre": 0.9}
CB_ENVELOPE = (150.95, -33.99, 151.18, -33.85)

#: Lot points (ST_PointOnSurface of nsw_cadastre_lots, 2026-10-11) of the served-answer audit's
#: three Canterbury-Bankstown addresses. None is in a centre; each must stay in no precinct.
OUTSIDE_ALL = {
    "44 Hood Ave Earlwood (11//DP13148)": (151.116551, -33.929486),
    "44 Lawford St Greenacre (3//DP35333)": (151.061015, -33.889200),
    "5-9 Clack Rd Chester Hill (671//DP1158597)": (150.990406, -33.870217),
}

LOOKUP_SQL = """SELECT precinct_id FROM dcp_precinct_boundaries
                 WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                   AND LOWER(lga) = LOWER(%s)"""


def load_rows() -> list[dict]:
    fc = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for f in fc["features"]:
        p = f["properties"]
        rows.append({
            "precinct_id": p["precinct_id"], "precinct_name": p["precinct_name"],
            "geom": json.dumps(f["geometry"]), "area_sqm": p["area_sqm"], "perimeter_m": p["perimeter_m"],
            "extraction_method": p["method"], "confidence_score": CONFIDENCE[p["method"]],
            "source_document": p["source"], "boundary_description": p["quote"],
        })
    ids = {r["precinct_id"] for r in rows}
    if ids != EXPECTED_IDS:
        raise SystemExit(f"[ABORT] {SRC.name} holds {sorted(ids)}, expected {sorted(EXPECTED_IDS)}")
    return rows


def connect():
    import psycopg2
    from dotenv import dotenv_values
    import os
    url = os.environ.get("DATABASE_URL")
    for d in [REPO, *REPO.parents]:
        if url:
            break
        if (d / ".env").exists():
            url = dotenv_values(d / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("[ABORT] DATABASE_URL not found")
    return psycopg2.connect(url, connect_timeout=15, options="-c statement_timeout=30000")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    rows = load_rows()
    for r in rows:
        print(f"  {r['precinct_id']:<4} {r['precinct_name']:<30} {r['area_sqm'] / 1e4:7.1f} ha  "
              f"{r['extraction_method']} ({r['confidence_score']})")
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT current_database()")
    print(f"database: {cur.fetchone()[0]}")
    cur.execute("""SELECT id, precinct_id, precinct_name, lga, former_council, extraction_method,
                          confidence_score, source_document, boundary_description,
                          ST_AsGeoJSON(boundary) FROM dcp_precinct_boundaries WHERE LOWER(lga) = LOWER(%s)""",
                (LGA,))
    existing = cur.fetchall()
    print(f"existing {LGA} rows: {len(existing)}")
    if not commit:
        print("dry-run: nothing written (pass --commit)")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bpath = BACKUP_DIR / f"cb_precinct_boundaries_before_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
    bpath.write_text(json.dumps([list(map(str, r)) for r in existing], indent=1), encoding="utf-8")
    print(f"backup: {bpath} ({len(existing)} rows)")

    for r in rows:
        cur.execute("""
            INSERT INTO dcp_precinct_boundaries
                (precinct_id, precinct_name, lga, former_council, boundary, centroid,
                 source_document, extraction_method, confidence_score, boundary_description,
                 area_sqm, perimeter_m, created_at, updated_at)
            VALUES (%(precinct_id)s, %(precinct_name)s, %(lga)s, %(fc)s,
                    ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
                    ST_PointOnSurface(ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)),
                    %(source_document)s, %(extraction_method)s, %(confidence_score)s,
                    %(boundary_description)s, %(area_sqm)s, %(perimeter_m)s, now(), now())
            ON CONFLICT (precinct_id, lga) DO UPDATE SET
                precinct_name = EXCLUDED.precinct_name, former_council = EXCLUDED.former_council,
                boundary = EXCLUDED.boundary, centroid = EXCLUDED.centroid,
                source_document = EXCLUDED.source_document,
                extraction_method = EXCLUDED.extraction_method,
                confidence_score = EXCLUDED.confidence_score,
                boundary_description = EXCLUDED.boundary_description,
                area_sqm = EXCLUDED.area_sqm, perimeter_m = EXCLUDED.perimeter_m, updated_at = now()
        """, {**r, "lga": LGA, "fc": FORMER_COUNCIL})

    # Proof, inside the transaction: placed on Earth correctly, found by the SAME lookup the
    # site runs, and the audit addresses still in no precinct.
    problems = []
    cur.execute("""SELECT precinct_id, ST_XMin(boundary), ST_YMin(boundary), ST_XMax(boundary),
                          ST_YMax(boundary), ST_X(centroid), ST_Y(centroid)
                     FROM dcp_precinct_boundaries WHERE lga = %s""", (LGA,))
    got = cur.fetchall()
    if {g[0] for g in got} != EXPECTED_IDS:
        problems.append(f"rows after write: {sorted(g[0] for g in got)}")
    x0, y0, x1, y1 = CB_ENVELOPE
    for pid, a0, b0, a1, b1, cx, cy in got:
        if not (x0 <= a0 and a1 <= x1 and y0 <= b0 and b1 <= y1):
            problems.append(f"{pid} outside the Canterbury-Bankstown envelope")
        cur.execute(LOOKUP_SQL, (cx, cy, "CANTERBURY-BANKSTOWN"))
        if pid not in {r[0] for r in cur.fetchall()}:
            problems.append(f"{pid}: its own centroid is not found by the site's lookup")
    for label, (x, y) in OUTSIDE_ALL.items():
        cur.execute(LOOKUP_SQL, (x, y, "CANTERBURY-BANKSTOWN"))
        hit = [r[0] for r in cur.fetchall()]
        print(f"  lookup {label}: {hit or 'no precinct'}")
        if hit:
            problems.append(f"{label} now resolves to {hit}")
    if problems:
        conn.rollback()
        print("[ROLLED BACK]\n  " + "\n  ".join(problems))
        return 1
    conn.commit()
    print(f"committed {len(rows)} rows; every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
