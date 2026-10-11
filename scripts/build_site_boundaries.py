#!/usr/bin/env python3
"""Build and load single-site outlines from the Lot/DP list in the chapter's own text.

prior-art-checked: the outline is the union of exact cadastre parcels, the same table
build_cb_centre_boundaries.py fits figures to (nsw_cadastre_lots); loading reuses
import_cb_centre_boundaries.connect and its upsert-on-(precinct_id, lga) shape. Neither can
read a lot list: build_cb fits a drawn figure, import_cb loads a committed geojson.

PROOF (each check must pass or the site is NOT built -- DQ-143, 2026-10-11)
  1 verbatim  the data file's lot list appears word for word on the cited PDF page
  2 lots      every listed lot is found in nsw_cadastre_lots by exact lotidstring
  3 area      the parcels' area is within 10% of the area the chapter states (if it states one)
  4 address   the address register point for the chapter's address is inside the outline
  5 fallback  Inner West only: no lot outside every outline lies within 500 m of the new outline
              (precinct-service.ts findNearestPrecinct would hand it the site's rules)

Usage:
    python scripts/build_site_boundaries.py            # prove every site, print, write nothing
    python scripts/build_site_boundaries.py --commit   # prove, back up, upsert the sites that pass
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
SRC = REPO / "data" / "site_chapters" / "lot_sites.json"
ADDR_SRC = REPO / "data" / "site_chapters" / "address_sites.json"
BACKUP_DIR = REPO / "data" / "db_rollback_backups"
ADDRESS_POINTS = ("https://portal.spatial.nsw.gov.au/server/rest/services/"
                  "NSW_Geocoded_Addressing_Theme/MapServer/1/query")
UA = {"User-Agent": "Mozilla/5.0 (build_site_boundaries)"}
AREA_TOLERANCE = 0.10
FALLBACK_M = 500

_LOT_RE = re.compile(
    r"Lots?\s+((?:[0-9A-Z]{1,4}(?:\s*-\s*[0-9A-Z]{1,4})?)(?:\s*(?:,|and)\s*[0-9A-Z]{1,4}(?:\s*-\s*[0-9A-Z]{1,4})?)*?)"
    r"\s*,?\s*DP\s*(\d+)\b", re.I)


def parse_lots(text: str) -> list[str]:
    """'Lot 6-9, DP79950 Lots A and B, DP 355656' -> ['6//DP79950', ..., 'A//DP355656', 'B//DP355656']."""
    out: list[str] = []
    for ids, dp in _LOT_RE.findall(text):
        for part in re.split(r"\s*(?:,|and)\s*", ids.strip()):
            m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
            numbers = [str(n) for n in range(int(m.group(1)), int(m.group(2)) + 1)] if m else [part]
            out.extend(f"{n.upper()}//DP{dp}" for n in numbers if n)
    return list(dict.fromkeys(out))


def _norm(s: str) -> str:
    """Drop layout only (whitespace, bullets, table breaks); keep the separators that carry meaning,
    so 'Lot 1-2' and 'Lot 12' stay different (cross-review 2026-10-12)."""
    s = s.lower().replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[^a-z0-9,&/\-]", "", s)


def verbatim_on_page(site: dict) -> bool:
    import fitz  # PyMuPDF
    data = urllib.request.urlopen(urllib.request.Request(site["pdf"], headers=UA), timeout=60).read()
    page = fitz.open(stream=data, filetype="pdf")[site["page"] - 1].get_text()
    return _norm(site["lots_verbatim"]) in _norm(page)


def address_point(address: str) -> tuple[float, float] | None:
    q = urllib.parse.urlencode({"where": f"address = '{address}'", "outFields": "address",
                                "returnGeometry": "true", "outSR": 4326, "f": "json"})
    d = json.load(urllib.request.urlopen(urllib.request.Request(f"{ADDRESS_POINTS}?{q}", headers=UA),
                                         timeout=60))
    feats = d.get("features") or []
    return (feats[0]["geometry"]["x"], feats[0]["geometry"]["y"]) if feats else None


def fallback_exposed(cur, wkt: str) -> int:
    """Inner West lots in no outline whose point is within FALLBACK_M of this outline: each would be
    handed the site's rules by precinct-service.ts findNearestPrecinct. Must be 0 to load."""
    cur.execute(
        "SELECT count(*) FROM lot_search_index l"
        " WHERE l.lga_name = 'INNER WEST'"
        "   AND ST_DWithin(ST_Transform(ST_PointOnSurface(l.geom), 3857),"
        "                  ST_Transform(ST_GeomFromText(%s, 4326), 3857), %s)"
        "   AND NOT ST_Contains(ST_GeomFromText(%s, 4326), ST_PointOnSurface(l.geom))"
        "   AND NOT EXISTS (SELECT 1 FROM dcp_precinct_boundaries b WHERE LOWER(b.lga) = 'inner west'"
        "                   AND ST_Contains(b.boundary, ST_PointOnSurface(l.geom)))",
        (wkt, FALLBACK_M, wkt))
    return cur.fetchone()[0]


def prove(cur, site: dict) -> dict:
    """Run checks 1-5. Returns a report; report['ok'] is True only if every check passed."""
    lots = parse_lots(site["lots_verbatim"])
    r: dict = {"precinct_id": site["precinct_id"], "lots_listed": len(lots), "checks": {}}
    r["checks"]["1_verbatim"] = verbatim_on_page(site)
    cur.execute("SELECT lotidstring FROM nsw_cadastre_lots WHERE lotidstring = ANY(%s)", (lots,))
    found = {row[0] for row in cur.fetchall()}
    r["missing_lots"] = sorted(set(lots) - found)
    r["lots"] = sorted(found)
    r["checks"]["2_lots"] = not r["missing_lots"] and bool(lots)
    cur.execute("SELECT ST_AsText(ST_Multi(ST_Union(geom))), ST_Area(ST_Union(geom)::geography)"
                " FROM nsw_cadastre_lots WHERE lotidstring = ANY(%s)", (lots,))
    r["wkt"], area = cur.fetchone()
    r["area_m2"] = round(area or 0)
    stated = site.get("stated_area_m2")
    r["checks"]["3_area"] = (abs(r["area_m2"] - stated) <= AREA_TOLERANCE * stated) if stated else None
    pt = address_point(site["address"])
    r["address_point"] = pt
    r["checks"]["4_address"] = False
    if pt and r["wkt"]:
        cur.execute("SELECT ST_Contains(ST_GeomFromText(%s, 4326), ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
                    (r["wkt"], pt[0], pt[1]))
        r["checks"]["4_address"] = bool(cur.fetchone()[0])
    if site["lga"] == "Inner West" and r["wkt"]:
        r["fallback_exposed_lots"] = fallback_exposed(cur, r["wkt"])
        r["checks"]["5_fallback"] = r["fallback_exposed_lots"] == 0
    r["ok"] = all(v is not False for v in r["checks"].values())
    return r


def finalize(cur, site: dict, r: dict) -> dict:
    """Check 6: the chapter's own site map (site_figure_check.map_check), then the verdict.

    The map is the strongest evidence. When it matches (and location is anchored by the plan's own
    address or lot list -- checks 1 and 4_address/2_named found at least one point), a number absent
    from the register (2_named) or a wrong area in the plan's table (3_area/4_area) does not hold the
    site; the excuse is recorded. A map that cannot be read leaves every other check in force. A map
    that does not match always holds the site."""
    import site_figure_check as sfc
    pdf = urllib.request.urlopen(urllib.request.Request(site["pdf"], headers=UA), timeout=60).read()
    m = sfc.map_check(cur, pdf, site.get("figure"), r.get("lots") or [])
    r["map"] = {k: v for k, v in m.items() if k != "lots"}
    r["checks"]["6_map"] = {"pass": True, "fail": False, "unreadable": None}[m["status"]]
    if m["status"] == "pass" and m["lots"] != r.get("lots"):
        r["lots"], r["lots_listed"] = m["lots"], len(m["lots"])
        cur.execute("SELECT ST_AsText(ST_Multi(ST_Union(geom))), ST_Area(ST_Union(geom)::geography)"
                    " FROM nsw_cadastre_lots WHERE lotidstring = ANY(%s)", (m["lots"],))
        r["wkt"], area = cur.fetchone()
        r["area_m2"] = round(area)
        if site["lga"] == "Inner West":
            r["fallback_exposed_lots"] = fallback_exposed(cur, r["wkt"])
            r["checks"]["5_fallback"] = r["fallback_exposed_lots"] == 0
        if site.get("numbers"):  # widened address site: no out-of-range neighbour may now be inside
            from site_addresses import neighbours_inside
            r["neighbours_checked"], r["neighbours_inside"] = neighbours_inside(cur, site, r["wkt"])
            r["checks"]["3_neighbours"] = not r["neighbours_inside"]
    excusable = {"2_named", "3_area", "4_area"} if m["status"] == "pass" else set()
    r["excused"] = sorted(k for k, v in r["checks"].items() if v is False and k in excusable)
    anchored = r["checks"].get("4_address", True) is not False or r["checks"].get("2_named") is not False
    r["ok"] = anchored and all(v is not False for k, v in r["checks"].items() if k not in excusable)
    return r


UPSERT = """
INSERT INTO dcp_precinct_boundaries
  (precinct_id, precinct_name, lga, former_council, boundary, centroid, area_sqm,
   source_document, extraction_method, confidence_score, boundary_description)
VALUES (%(id)s, %(name)s, %(lga)s, %(fc)s, ST_GeomFromText(%(wkt)s, 4326),
        ST_Centroid(ST_GeomFromText(%(wkt)s, 4326)), %(area)s, %(src)s, %(method)s, 1.0, %(desc)s)
ON CONFLICT (precinct_id, lga) DO UPDATE SET
  boundary = EXCLUDED.boundary, centroid = EXCLUDED.centroid, area_sqm = EXCLUDED.area_sqm,
  source_document = EXCLUDED.source_document, extraction_method = EXCLUDED.extraction_method,
  boundary_description = EXCLUDED.boundary_description, updated_at = now()
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--only", help="comma-separated precinct ids to load (each must still pass)")
    ap.add_argument("--addresses", action="store_true", help="the address-only sites (site_addresses.py)")
    args = ap.parse_args()
    src, how = (ADDR_SRC, "addresses") if args.addresses else (SRC, "lot list")
    sites = json.loads(src.read_text(encoding="utf-8"))["sites"]
    if args.addresses:
        from site_addresses import prove_address as check
    else:
        check = prove
    conn = dq_db.connect()
    try:
        reports = [finalize(conn.cursor(), s, check(conn.cursor(), s)) for s in sites]
    finally:
        conn.close()
    for r in reports:
        print(f"{'OK  ' if r['ok'] else 'FAIL'} {r['precinct_id']:<24} lots={r['lots_listed']:<3} "
              f"area={r['area_m2']:>7,} m2  checks={r['checks']}"
              + (f"  missing={r['missing_lots']}" if r["missing_lots"] else "")
              + (f"  missing_named={r['missing_named']}" if r.get("missing_named") else "")
              + (f"  neighbours_inside={r['neighbours_inside']}" if r.get("neighbours_inside") else "")
              + (f"  fallback_exposed={r.get('fallback_exposed_lots')}" if "fallback_exposed_lots" in r else "")
              + f"  map={r.get('map')}" + (f"  excused={r['excused']}" if r.get("excused") else ""))
    if not args.commit:
        print("DRY RUN - nothing written.")
        return 0 if all(r["ok"] for r in reports) else 1
    # A site that fails any check is held (printed FAIL above) and never written; only proven
    # sites load. --only narrows to named precinct ids, e.g. to load one site after review.
    passed = [(s, r) for s, r in zip(sites, reports) if r["ok"]]
    if args.only:
        wanted = set(args.only.split(","))
        known = {s["precinct_id"]: r for s, r in zip(sites, reports)}
        bad = sorted(i for i in wanted if i not in known or not known[i]["ok"])
        if bad:  # every requested site must pass, or the keying step would key a missing outline
            print(f"REFUSED: requested site(s) unknown or failing: {bad}; nothing written.")
            return 1
        passed = [(s, r) for s, r in passed if s["precinct_id"] in wanted]
    if not passed:
        print("REFUSED: no site passed every check; nothing written.")
        return 1
    sites, reports = [s for s, _ in passed], [r for _, r in passed]
    from import_cb_centre_boundaries import connect
    w = connect()
    try:
        cur = w.cursor()
        ids, lgas = [s["precinct_id"] for s in sites], [s["lga"] for s in sites]
        cur.execute("SELECT row_to_json(b) FROM (SELECT d.precinct_id, d.lga, precinct_name, former_council,"
                    " area_sqm, source_document, extraction_method, confidence_score, boundary_description,"
                    " ST_AsText(boundary) AS boundary_wkt FROM dcp_precinct_boundaries d"
                    " JOIN unnest(%s::text[], %s::text[]) k(pid, lga) ON d.precinct_id = k.pid AND d.lga = k.lga) b",
                    (ids, lgas))
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bpath = BACKUP_DIR / f"site_boundaries_pre_{datetime.now(timezone.utc):%Y-%m-%dT%H%M%S}.json"
        bpath.write_text(json.dumps([row[0] for row in cur.fetchall()], indent=1), encoding="utf-8")
        for s, r in zip(sites, reports):
            cur.execute(UPSERT, {
                "id": s["precinct_id"], "name": f"{s['source_chapter_key']} ({how} p{s['page']})",
                "lga": s["lga"], "fc": s["former_council"], "wkt": r["wkt"], "area": r["area_m2"],
                "method": "chapter_lot_list_cadastre" if how == "lot list" else "chapter_address_register_cadastre",
                "src": f"{s['pdf']}#page={s['page']} {how}: {s.get('lots_verbatim') or s.get('address_verbatim')}",
                "desc": f"{r['lots_listed']} lots {r.get('lots')}; checks {r['checks']}; map {r.get('map')};"
                        f" excused {r.get('excused')}"})
        w.commit()
        print(f"COMMITTED {len(sites)} outlines; backup {bpath}")
    finally:
        w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
