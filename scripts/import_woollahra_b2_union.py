#!/usr/bin/env python3
"""Load one outline covering all eleven Woollahra B2 neighbourhood HCAs.

prior-art-checked: modelled on import_cb_centre_boundaries.py (upsert on the (precinct_id, lga)
unique key, former_council set, proof after write). No new geometry is drawn: the outline is the
ST_Union of the eleven outlines already in dcp_precinct_boundaries, each loaded 2026-07-29 from
the NSW ePlanning heritage layer (EPI_Primary_Planning_Layers/0, Woollahra LEP 2014).

WHY: Woollahra DCP 2015 B2 "applies to the following neighbourhood HCAs" (p5). B2.1's general
controls apply to all eleven, and a rule carries one v2_precinct_id, so it needs one id whose
outline is the eleven together. precinct-service.ts returns EVERY outline containing a lot, so a
house in Etham Avenue HCA gets both 'Etham Avenue HCA' and this id.

Usage:
    python scripts/import_woollahra_b2_union.py            # dry run: prints what it would write
    python scripts/import_woollahra_b2_union.py --commit   # backup, upsert, prove
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dq_db  # noqa: E402  (finds the main checkout's .env from a worktree)

REPO = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO / "data" / "db_rollback_backups"
LGA = "Woollahra"
UNION_ID = "Woollahra B2 neighbourhood HCAs"
#: Exactly the eleven B2.2-B2.12 areas; the union refuses to build from any other count.
MEMBERS = (
    "Etham Avenue HCA", "Darling Point Road HCA", "Mona Road HCA", "Loftus Street and Mona Road HCA",
    "Aston Gardens HCA", "Victoria Road HCA", "Balfour Road HCA", "Beresford Estate HCA",
    "Rose Bay Gardens Estate HCA", "Kent Road HCA", "Bell Street HCA",
)
#: Lots that must NOT fall in the union: the two large HCAs that have chapters of their own.
OUTSIDE = ("Paddington HCA", "Woollahra HCA")

UPSERT = """
INSERT INTO dcp_precinct_boundaries
  (precinct_id, precinct_name, lga, former_council, boundary, centroid, area_sqm,
   source_document, extraction_method, confidence_score, boundary_description)
SELECT %(id)s, %(name)s, %(lga)s, %(lga)s, u.g, ST_Centroid(u.g), ST_Area(u.g::geography),
       %(src)s, 'union_of_loaded_outlines', 0.9, %(desc)s
  FROM (SELECT ST_Multi(ST_Union(boundary)) AS g FROM dcp_precinct_boundaries
         WHERE lga = %(lga)s AND precinct_id = ANY(%(members)s)) u
ON CONFLICT (precinct_id, lga) DO UPDATE SET
  boundary = EXCLUDED.boundary, centroid = EXCLUDED.centroid, area_sqm = EXCLUDED.area_sqm,
  source_document = EXCLUDED.source_document, extraction_method = EXCLUDED.extraction_method,
  boundary_description = EXCLUDED.boundary_description, updated_at = now()
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    conn = dq_db.connect() if not args.commit else _write_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT precinct_id, area_sqm FROM dcp_precinct_boundaries"
                    " WHERE lga = %s AND precinct_id = ANY(%s)", (LGA, list(MEMBERS)))
        found = dict(cur.fetchall())
        missing = sorted(set(MEMBERS) - set(found))
        if missing:
            print(f"REFUSED: member outlines missing {missing}")
            return 1
        print(f"members: {len(found)} outlines, {sum(found.values()):,.0f} m2 summed")

        cur.execute("SELECT row_to_json(b) FROM (SELECT precinct_id, lga, area_sqm, source_document"
                    " FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s) b", (LGA, UNION_ID))
        before = [r[0] for r in cur.fetchall()]
        print(f"existing '{UNION_ID}' rows: {len(before)}")

        params = {"id": UNION_ID, "name": "Woollahra DCP 2015 B2 neighbourhood HCAs (all eleven)",
                  "lga": LGA, "members": list(MEMBERS),
                  "src": "Woollahra DCP 2015 B2 p5 'applies to the following neighbourhood HCAs' <- "
                         "ST_Union of the eleven B2.2-B2.12 outlines already loaded from NSW ePlanning "
                         "EPI_Primary_Planning_Layers/0 (Woollahra LEP 2014)",
                  "desc": "Union of: " + "; ".join(MEMBERS)}
        if not args.commit:
            print("DRY RUN - would upsert 1 row:", json.dumps({k: v for k, v in params.items() if k != "members"}))
            return 0

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bpath = BACKUP_DIR / f"woollahra_b2_union_pre_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
        bpath.write_text(json.dumps(before, indent=1), encoding="utf-8")
        cur.execute(UPSERT, params)
        _prove(cur)
        conn.commit()
        print(f"COMMITTED 1 row; backup {bpath}")
        return 0
    finally:
        conn.close()


def _write_connection():
    """The write connection the Canterbury-Bankstown loader uses (reused, not re-implemented)."""
    from import_cb_centre_boundaries import connect
    w = connect()
    w.autocommit = False
    return w


def _prove(cur) -> None:
    """Every member's interior point is inside the union; neither the Paddington nor the Woollahra HCA point is. Raises."""
    probe = ("SELECT ST_Contains((SELECT boundary FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s),"
             " (SELECT ST_PointOnSurface(boundary) FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s))")
    for pid in MEMBERS + OUTSIDE:
        cur.execute(probe, (LGA, UNION_ID, LGA, pid))
        inside = cur.fetchone()[0]
        if inside != (pid in MEMBERS):
            raise RuntimeError(f"proof failed: point of {pid} inside union = {inside}")
    print(f"proved: 11 member points inside, {len(OUTSIDE)} other HCAs outside")


if __name__ == "__main__":
    sys.exit(main())
