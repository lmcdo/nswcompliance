#!/usr/bin/env python3
"""Re-derive Inner West lots' former council from the former LGA boundaries themselves.

prior-art-checked: reuse not viable -- scripts/build_lot_search_index.py Step 9 assigns
former_council from dcp_precinct_boundaries, and Step 9b gives every lot outside a precinct the
NEAREST precinct's council. Precincts do not tile the former councils, so that guess is wrong
wherever the nearest outline belongs to a neighbour: 162/137 Victoria Street Ashfield (former
Ashfield, ABS ASGS 2015 LGA 10150) sits 520 m from Marrickville precinct 16 and 618 m from
Ashfield Part 1, so it got Marrickville and the whole Marrickville DCP (3,255 rules) on prod
2026-10-15. Measured that day: 1,947 Inner West lots disagree with the ABS polygons, 1,770 of
them more than 50 m inside former Ashfield (1,185 tagged leichhardt, 755 marrickville).

Authority: ABS ASGS 2015 LGA polygons Ashfield (A) / Leichhardt (A) / Marrickville (A), the
last edition before the 2016 amalgamation. Each former council's DCP applies to its former LGA.
ABS polygons are generalised, so a lot is only re-assigned when its point-on-surface is more
than --margin metres inside one polygon; edge lots are reported, never changed.

    python scripts/repair_former_council_from_abs.py            # dry run: counts
    python scripts/repair_former_council_from_abs.py --apply    # backup, then update
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ABS_URL = "https://geo.abs.gov.au/arcgis/rest/services/ASGS2015/LGA/MapServer/0/query"
FORMER = {"ashfield": "Ashfield (A)", "leichhardt": "Leichhardt (A)", "marrickville": "Marrickville (A)"}
BACKUP_DIR = Path(__file__).resolve().parent.parent / "data" / "db_rollback_backups"


def decide(current: str | None, abs_council: str | None, depth_m: float | None, margin_m: float) -> str | None:
    """The council to write, or None to leave the lot alone.

    Only a lot clearly inside one former LGA (deeper than the margin) is changed, and only when
    it disagrees. Outside every polygon, or near an edge, the stored value stands.
    """
    if not abs_council or depth_m is None or depth_m <= margin_m:
        return None
    if (current or "").lower() == abs_council:
        return None
    return abs_council


def fetch_polygons() -> dict[str, str]:
    out = {}
    for slug, name in FORMER.items():
        q = urllib.parse.urlencode({"where": f"lga_name_2015='{name}'", "outFields": "lga_name_2015",
                                    "returnGeometry": "true", "outSR": 4326, "f": "geojson"})
        with urllib.request.urlopen(f"{ABS_URL}?{q}", timeout=60) as r:
            feats = json.load(r).get("features") or []
        if len(feats) != 1:  # never guess a boundary
            raise RuntimeError(f"ABS returned {len(feats)} polygons for {name}")
        out[slug] = json.dumps(feats[0]["geometry"])
    return out


SQL = """
WITH a AS (SELECT * FROM (VALUES ('ashfield', ST_SetSRID(ST_GeomFromGeoJSON(%(ashfield)s), 4326)),
                                 ('leichhardt', ST_SetSRID(ST_GeomFromGeoJSON(%(leichhardt)s), 4326)),
                                 ('marrickville', ST_SetSRID(ST_GeomFromGeoJSON(%(marrickville)s), 4326))) v(fc, g))
SELECT l.lotidstring, l.former_council, a.fc,
       ST_Distance(ST_Boundary(a.g)::geography, ST_PointOnSurface(l.geom)::geography)
FROM lot_search_index l
JOIN a ON ST_Contains(a.g, ST_PointOnSurface(l.geom))
WHERE l.lga_name = 'INNER WEST' AND l.geom IS NOT NULL
  AND l.former_council IS DISTINCT FROM a.fc
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--margin", type=float, default=20.0, help="metres inside a polygon before a lot is moved")
    a = ap.parse_args()
    import psycopg2

    polys = fetch_polygons()
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 120000")
    cur.execute("SELECT current_database()")
    print("database:", cur.fetchone()[0])
    cur.execute(SQL, polys)
    rows = cur.fetchall()
    changes = [(lot, old, decide(old, fc, depth, a.margin)) for lot, old, fc, depth in rows]
    changes = [c for c in changes if c[2]]
    by: dict[tuple, int] = {}
    for _, old, new in changes:
        by[(old, new)] = by.get((old, new), 0) + 1
    print(f"disagree {len(rows)}; change {len(changes)}; left (edge within {a.margin} m) {len(rows) - len(changes)}")
    for (old, new), n in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {old} -> {new}: {n}")
    if not a.apply or not changes:
        print("dry run: nothing written" if not a.apply else "nothing to change")
        return 0
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bk = BACKUP_DIR / f"lot_former_council_pre_abs_{datetime.now():%Y-%m-%dT%H%M%S}.json"
    bk.write_text(json.dumps([{"lotidstring": lot, "former_council": old} for lot, old, _ in changes]),
                  encoding="utf-8")
    print("backup:", bk)
    cur.executemany("UPDATE lot_search_index SET former_council = %s "
                    "WHERE lotidstring = %s AND lga_name = 'INNER WEST'",
                    [(new, lot) for lot, _, new in changes])
    conn.commit()
    print(f"updated {len(changes)} lots")
    return 0


if __name__ == "__main__":
    sys.exit(main())
