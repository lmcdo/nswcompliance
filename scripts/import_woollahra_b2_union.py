#!/usr/bin/env python3
"""Load one outline that is the union of outlines already loaded (Woollahra B2, Ku-ring-gai 14B).

prior-art-checked: modelled on import_cb_centre_boundaries.py (upsert on the (precinct_id, lga)
unique key, former_council set, proof after write). No new geometry is drawn: the outline is the
ST_Union of the eleven outlines already in dcp_precinct_boundaries, each loaded 2026-07-29 from
the NSW ePlanning heritage layer (EPI_Primary_Planning_Layers/0, Woollahra LEP 2014).

WHY: Woollahra DCP 2015 B2 "applies to the following neighbourhood HCAs" (p5). B2.1's general
controls apply to all eleven, and a rule carries one v2_precinct_id, so it needs one id whose
outline is the eleven together. precinct-service.ts returns EVERY outline containing a lot, so a
house in Etham Avenue HCA gets both 'Etham Avenue HCA' and this id.

Ku-ring-gai 14B (2026-10-15): 14B.1-14B.7 apply to the whole Turramurra centre, which Figure
14B.1-1 (p2) draws as precincts T1-T4 together. Id '14B': Ku-ring-gai outline rows carry no
former_council, so precinct-service.ts attributes them by the ^14[A-O] id pattern.

Usage:
    python scripts/import_woollahra_b2_union.py [--union krg_14b]            # dry run
    python scripts/import_woollahra_b2_union.py [--union krg_14b] --commit   # backup, upsert, prove
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
#: Each union: its members (the union refuses to build from any other set) and outlines whose interior
#: point must NOT fall inside it (neighbours with chapters of their own).
UNIONS: dict[str, dict] = {
    "woollahra_b2": {
        "lga": "Woollahra", "id": "Woollahra B2 neighbourhood HCAs",
        "name": "Woollahra DCP 2015 B2 neighbourhood HCAs (all eleven)",
        "members": (
            "Etham Avenue HCA", "Darling Point Road HCA", "Mona Road HCA", "Loftus Street and Mona Road HCA",
            "Aston Gardens HCA", "Victoria Road HCA", "Balfour Road HCA", "Beresford Estate HCA",
            "Rose Bay Gardens Estate HCA", "Kent Road HCA", "Bell Street HCA",
        ),
        "outside": ("Paddington HCA", "Woollahra HCA"),
        "src": "Woollahra DCP 2015 B2 p5 'applies to the following neighbourhood HCAs' <- "
               "ST_Union of the eleven B2.2-B2.12 outlines already loaded from NSW ePlanning "
               "EPI_Primary_Planning_Layers/0 (Woollahra LEP 2014)",
    },
    "cb_8_3_4": {
        "lga": "Canterbury-Bankstown", "id": "8.3.4",
        "name": "Canterbury-Bankstown DCP 2023 Ch 8.3 Section 4 Rookwood Village Centre (sites found in the register)",
        "members": ("8.3.4a", "8.3.4b"),
        "outside": ("8.3.6",),
        "src": "Ch 8.3 p11 '324-326 Hume Highway ...; 342 Hume Highway and 2-8 George Street; 348 ...; 350 Hume Highway and "
               "18 George Street' <- union of the address-proved sites (2-8 and 18 George St are not in the NSW address register)",
    },
    "cb_part7": {
        "lga": "Canterbury-Bankstown", "id": "C-B Part 7 centres",
        "name": "Canterbury-Bankstown DCP 2023 Part 7 local and village centres (mapped so far)",
        "members": ("7.2", "7.5", "7.6"), "outside": ("6.2", "8.3.6"),
        "src": "Ch 7.1 applies to the Part 7 centres; union of the mapped outlines 7.2 (City West), 7.5, 7.6",
    },
    "cb_part6": {
        "lga": "Canterbury-Bankstown", "id": "C-B Part 6 centres",
        "name": "Canterbury-Bankstown DCP 2023 Part 6 strategic centres (mapped so far: Bankstown)",
        "members": ("6.2",), "outside": ("7.5", "7.6"),
        "src": "Ch 6.1 applies to the Part 6 strategic centres (Bankstown, Campsie); Campsie 6.3 not yet mapped",
    },
    "woollahra_d3": {
        "lga": "Woollahra", "id": "Woollahra D3 centres",
        "name": "Woollahra DCP 2015 D3 general controls for neighbourhood and mixed use centres (all twelve)",
        "members": (
            "Hopetoun Avenue Centre", "South Head Roundabout Centre", "Vaucluse Shopping Village", "Plumer Road Centre",
            "O'Sullivan Road Centre", "Streatfield Road Centre", "Bellevue Hill Shops", "Manning Road Centre",
            "Darling Point Road Centre", "New South Head Road Corridor Edgecliff", "Rose Bay North Centre",
            "Rose Bay South Centre",
        ),
        # Centres with chapters of their own that D3 does not name.
        "outside": ("Double Bay Centre", "Rose Bay Centre"),
        "src": "Woollahra DCP 2015 D3 p5 'This chapter contains controls for the following centres, as identified on "
               "Map A' (the nine D1 neighbourhood centres and the three D2 mixed use centres) <- ST_Union of those twelve "
               "outlines already loaded",
    },
    "krg_14b": {
        "lga": "Ku-ring-gai", "id": "14B",
        "name": "Ku-ring-gai DCP Part 14B Turramurra Local Centre (precincts T1-T4)",
        "members": ("14B_T1", "14B_T2", "14B_T3", "14B_T4"),
        # 14K Tennyson Ave Turramurra and 14O Pymble Golf Club: nearby sites with Parts of their own.
        "outside": ("14K", "14O"),
        "src": "Ku-ring-gai DCP Part 14B p2 Figure 14B.1-1 'Turramurra Local Centre Precinct Plan' (T1-T4) <- "
               "ST_Union of the four 14B.8-14B.11 precinct outlines already loaded",
    },
}

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
    ap.add_argument("--union", choices=sorted(UNIONS), default="woollahra_b2")
    args = ap.parse_args()
    u = UNIONS[args.union]
    LGA, UNION_ID, MEMBERS = u["lga"], u["id"], u["members"]

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

        params = {"id": UNION_ID, "name": u["name"], "lga": LGA, "members": list(MEMBERS),
                  "src": u["src"], "desc": "Union of: " + "; ".join(MEMBERS)}
        if not args.commit:
            print("DRY RUN - would upsert 1 row:", json.dumps({k: v for k, v in params.items() if k != "members"}))
            return 0

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bpath = BACKUP_DIR / f"{args.union}_union_pre_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
        bpath.write_text(json.dumps(before, indent=1), encoding="utf-8")
        cur.execute(UPSERT, params)
        _prove(cur, u)
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


def _prove(cur, u: dict) -> None:
    """Every member's interior point is inside the union; no `outside` outline's point is. Raises."""
    LGA, UNION_ID, MEMBERS, OUTSIDE = u["lga"], u["id"], u["members"], u["outside"]
    probe = ("SELECT ST_Contains((SELECT boundary FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s),"
             " (SELECT ST_PointOnSurface(boundary) FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s))")
    for pid in MEMBERS + OUTSIDE:
        cur.execute(probe, (LGA, UNION_ID, LGA, pid))
        inside = cur.fetchone()[0]
        if inside != (pid in MEMBERS):
            raise RuntimeError(f"proof failed: point of {pid} inside union = {inside}")
    print(f"proved: {len(MEMBERS)} member points inside, {len(OUTSIDE)} other outlines outside")


if __name__ == "__main__":
    sys.exit(main())
