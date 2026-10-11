#!/usr/bin/env python3
"""Load the seven Canterbury-Bankstown heritage conservation areas chapter 4.3 names, plus their union.

prior-art-checked: Woollahra's and Parramatta's HCA outlines came from the same state layer
(extraction_method 'eplanning_epi_heritage') through importers that no longer run; this fetches it
directly. Loading reuses import_cb_centre_boundaries.connect and the upsert-on-(precinct_id, lga)
shape of import_woollahra_b2_union.py.

WHY (DQ-143/DQ-146, 2026-10-11): chapter 4.3 "Within Canterbury-Bankstown, there are seven Heritage
Conservations Areas (HCA). These are: Ashbury HCA, Crinan Street Shops HCA, Duntroon Street HCA,
Floss Street HCA, Melford Street HCA, Railway Street HCA, Starkey Street HCA" (p4). Its rules carry
only a generic heritage tag, so every heritage property in the council was shown them; 8 sat in a
layer the page never reads. Section 21 is "Specific controls for the Ashbury HCA".

PROOF (refuses to write unless all pass)
  1 the chapter's list is on page 4 of the registered PDF, word for word
  2 each listed name matches exactly one feature of the state layer for Canterbury-Bankstown LEP 2023
  3 the layer holds no other conservation area for that LEP (seven listed, seven mapped)
  4 every area's interior point lies inside the union

Usage:
    python scripts/import_cb_heritage_areas.py            # dry run
    python scripts/import_cb_heritage_areas.py --commit   # prove, back up, upsert 8 rows
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dq_db  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO / "data" / "db_rollback_backups"
PDF = ("https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/canterbury_bankstown/"
       "v1.0-baseline/chapter-4-3-heritage-conservation-areas.pdf")
PAGE = 4
LIST_VERBATIM = ("These are: Ashbury HCA Crinan Street Shops HCA Duntroon Street HCA Floss Street HCA "
                 "Melford Street HCA Railway Street HCA Starkey Street HCA")
NAMES = ("Ashbury", "Crinan Street Shops", "Duntroon Street", "Floss Street", "Melford Street",
         "Railway Street", "Starkey Street")
LAYER = ("https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/"
         "EPI_Primary_Planning_Layers/MapServer/0/query")
EPI = "Canterbury-Bankstown Local Environmental Plan 2023"
LGA = FORMER = "Canterbury-Bankstown"
UNION_ID = "C-B 4.3 heritage conservation areas"
UA = {"User-Agent": "Mozilla/5.0 (import_cb_heritage_areas)"}


def precinct_id(name: str) -> str:
    return f"{name} HCA"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fetch_areas() -> list[dict]:
    q = urllib.parse.urlencode({"where": f"EPI_NAME = '{EPI}' AND LAY_CLASS LIKE 'Conservation Area%'",
                                "outFields": "OBJECTID,H_NAME,H_ID", "returnGeometry": "true",
                                "outSR": 4326, "f": "json"})
    d = json.load(urllib.request.urlopen(urllib.request.Request(f"{LAYER}?{q}", headers=UA), timeout=90))
    if d.get("error"):
        raise RuntimeError(d["error"])
    return d["features"]


def prove(features: list[dict]) -> tuple[dict, dict]:
    """Checks 1-3. Returns (checks, {listed name: feature})."""
    import fitz
    page = fitz.open(stream=urllib.request.urlopen(urllib.request.Request(PDF, headers=UA), timeout=60).read(),
                     filetype="pdf")[PAGE - 1].get_text()
    checks = {"1_list_on_page": _norm(LIST_VERBATIM) in _norm(page)}
    matched = {}
    for name in NAMES:
        hits = [f for f in features if f["attributes"]["H_NAME"].lower().startswith(name.lower())]
        if len(hits) == 1:
            matched[name] = hits[0]
    checks["2_each_name_one_area"] = len(matched) == len(NAMES)
    checks["3_no_other_area"] = len(features) == len(NAMES)
    return checks, matched


def wkt_of(feature: dict) -> str:
    from shapely.geometry import MultiPolygon, Polygon
    rings = feature["geometry"]["rings"]
    polys = [Polygon(r) for r in rings]
    shells = [p for p in polys if p.exterior.is_ccw is False] or polys  # Esri: shells clockwise
    return MultiPolygon([p.buffer(0) for p in shells]).buffer(0).wkt


UPSERT = """
INSERT INTO dcp_precinct_boundaries
  (precinct_id, precinct_name, lga, former_council, boundary, centroid, area_sqm,
   source_document, extraction_method, confidence_score, boundary_description)
VALUES (%(id)s, %(name)s, %(lga)s, %(lga)s, ST_Multi(ST_GeomFromText(%(wkt)s, 4326)),
        ST_Centroid(ST_GeomFromText(%(wkt)s, 4326)), ST_Area(ST_GeomFromText(%(wkt)s, 4326)::geography),
        %(src)s, %(method)s, 1.0, %(desc)s)
ON CONFLICT (precinct_id, lga) DO UPDATE SET
  boundary = EXCLUDED.boundary, centroid = EXCLUDED.centroid, area_sqm = EXCLUDED.area_sqm,
  source_document = EXCLUDED.source_document, extraction_method = EXCLUDED.extraction_method,
  boundary_description = EXCLUDED.boundary_description, updated_at = now()
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    features = fetch_areas()
    checks, matched = prove(features)
    print(f"state layer: {len(features)} conservation areas for {EPI}; checks {checks}")
    for name, f in matched.items():
        print(f"  {precinct_id(name):<30} <- OBJECTID {f['attributes']['OBJECTID']} '{f['attributes']['H_NAME']}' "
              f"({f['attributes']['H_ID']})")
    if not all(checks.values()):
        print("REFUSED: a check failed; nothing written.")
        return 1
    if not args.commit:
        print(f"DRY RUN - would upsert {len(matched) + 1} rows ({len(matched)} areas + '{UNION_ID}').")
        return 0
    from import_cb_centre_boundaries import connect
    w = connect()
    try:
        cur = w.cursor()
        ids = [precinct_id(n) for n in matched] + [UNION_ID]
        cur.execute("SELECT row_to_json(b) FROM (SELECT precinct_id, lga, area_sqm, source_document"
                    " FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = ANY(%s)) b", (LGA, ids))
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bpath = BACKUP_DIR / f"cb_heritage_areas_pre_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
        bpath.write_text(json.dumps([r[0] for r in cur.fetchall()], indent=1), encoding="utf-8")
        wkts = []
        for name, f in matched.items():
            wkt = wkt_of(f)
            wkts.append(wkt)
            a = f["attributes"]
            cur.execute(UPSERT, {"id": precinct_id(name), "name": a["H_NAME"], "lga": LGA, "wkt": wkt,
                                 "method": "eplanning_epi_heritage",
                                 "src": f"Canterbury-Bankstown DCP 2023 4.3 p{PAGE} <- NSW ePlanning "
                                        f"EPI_Primary_Planning_Layers/0, {EPI}, H_NAME='{a['H_NAME']}' "
                                        f"(H_ID {a['H_ID']}, OBJECTID {a['OBJECTID']})",
                                 "desc": f"chapter 4.3 lists '{name} HCA'"})
        cur.execute("SELECT ST_AsText(ST_Union(ARRAY(SELECT ST_GeomFromText(w, 4326) FROM unnest(%s::text[]) w)))",
                    (wkts,))
        union = cur.fetchone()[0]
        cur.execute(UPSERT, {"id": UNION_ID, "name": "Canterbury-Bankstown DCP 2023 4.3: all seven HCAs",
                             "lga": LGA, "wkt": union, "method": "union_of_loaded_outlines",
                             "src": f"Canterbury-Bankstown DCP 2023 4.3 p{PAGE} list of seven HCAs <- union of the "
                                    f"seven state outlines above", "desc": "Union of: " + "; ".join(NAMES)})
        for wkt in wkts:  # check 4
            cur.execute("SELECT ST_Contains(ST_GeomFromText(%s, 4326), ST_PointOnSurface(ST_GeomFromText(%s, 4326)))",
                        (union, wkt))
            if not cur.fetchone()[0]:
                raise RuntimeError("an area's interior point is outside the union")
        w.commit()
        print(f"COMMITTED {len(ids)} rows; backup {bpath}")
    finally:
        w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
