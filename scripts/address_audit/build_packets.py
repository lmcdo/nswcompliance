"""Address audit packet builder (run 2, 2026-10-15). Rebuilt: run 1's builder lived in a deleted job tmp.

Method: 13 LGAs that serve a council DCP, 2 random address points each, Inner West 6 (three former
councils). Random point inside the LGA polygon (NSW Administrative Boundaries layer 8) -> nearest NSW
address point within 80 m -> production /api/property -> /api/provisions/for-property with the
same params the assessment page sends (lib/dcp-provisions-query.ts) -> 10 random served rules ->
DB row facts + the PDF page text of the page shown to the user.

    python build_packets.py --seed 20261015 --out run2
"""
from __future__ import annotations

import argparse, hashlib, json, os, random, sys, time, urllib.parse, urllib.request
from pathlib import Path

import fitz  # pymupdf
import psycopg2
from shapely.geometry import Point, shape

BASE = "https://verify.plotdetect.com.au"
UA = {"User-Agent": "Mozilla/5.0 (address-audit)"}
LGA_URL = ("https://portal.spatial.nsw.gov.au/server/rest/services/"
           "NSW_Administrative_Boundaries_Theme/FeatureServer/8/query")
ADDR_URL = ("https://portal.spatial.nsw.gov.au/server/rest/services/"
            "NSW_Geocoded_Addressing_Theme/MapServer/1/query")
LGAS = {"CITY OF PARRAMATTA": 2, "CANTERBURY-BANKSTOWN": 2, "SYDNEY": 2, "WOOLLAHRA": 2, "INNER WEST": 6,
        "KU-RING-GAI": 2, "WAVERLEY": 2, "NORTHERN BEACHES": 2, "WOLLONGONG": 2, "BLACKTOWN": 2,
        "PENRITH": 2, "GEORGES RIVER": 2, "HORNSBY": 2}
HERE = Path(__file__).resolve().parents[2] / "data" / "address_audit"  # run dirs live here
PDF_CACHE = Path(__file__).resolve().parent / ".pdf_cache"


def get(url: str, timeout: int = 120):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retry then raise
            if attempt == 2:
                raise
            time.sleep(3)


def lga_shape(name: str):
    q = urllib.parse.urlencode({"where": f"lganame='{name}'", "outFields": "lganame",
                                "returnGeometry": "true", "outSR": 4326, "f": "geojson"})
    feats = json.loads(get(f"{LGA_URL}?{q}"))["features"]
    if not feats:
        raise RuntimeError(f"no LGA polygon for {name}")
    from shapely.ops import unary_union
    return unary_union([shape(f["geometry"]) for f in feats])


def address_near(x: float, y: float) -> str | None:
    d = 0.0008
    q = urllib.parse.urlencode({"geometry": f"{x-d},{y-d},{x+d},{y+d}", "geometryType": "esriGeometryEnvelope",
                                "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                                "outFields": "address", "returnGeometry": "false", "f": "json"})
    feats = json.loads(get(f"{ADDR_URL}?{q}")).get("features", [])
    addrs = sorted({f["attributes"]["address"] for f in feats if f["attributes"].get("address")})
    return addrs


def for_property_params(p: dict) -> dict:
    c = p.get("constraints") or {}
    q = {"groupBy": "toc"}
    if c.get("formerCouncil"):
        q["former_council"] = c["formerCouncil"]
    if c.get("zone"):
        q["zone"] = c["zone"]
    q["heritage"] = "true" if (p.get("heritage") or {}).get("isHeritage") else "false"
    hca = (p.get("heritage") or {}).get("hcaName") or c.get("hcaName")
    if hca:
        q["hca"] = hca
    if c.get("precinctId"):
        q["precinct_id"] = c["precinctId"]
    la = c.get("landApplicationInstruments")
    if la:
        q["land_application"] = json.dumps([{"name": i["name"], "type": i["type"]} for i in la],
                                           separators=(",", ":"), ensure_ascii=False)
    if c.get("landFacts"):
        q["land_facts"] = json.dumps(c["landFacts"], separators=(",", ":"), ensure_ascii=False)
    if (c.get("dcpFloodMap") or {}).get("inFloodArea") is True:
        q["flood"] = "true"
    if c.get("bushfireProne") is True:
        q["bushfire"] = "true"
    if c.get("acidSulfateSoils"):
        q["acid_sulfate"] = "true"
    if (c.get("riparianLand") or {}).get("inRiparianArea") is True:
        q["riparian"] = "true"
    return q


def pdf_page_text(url: str, page: int | None) -> str | None:
    if not url or not page:
        return None
    PDF_CACHE.mkdir(exist_ok=True)
    f = PDF_CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".pdf")
    if not f.exists():
        f.write_bytes(get(url, timeout=300))
    doc = fitz.open(f)
    if not 1 <= page <= doc.page_count:
        return f"<page {page} outside 1..{doc.page_count}>"
    return doc[page - 1].get_text()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-address", type=int, default=10)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    out = HERE / a.out
    out.mkdir(parents=True, exist_ok=True)
    previous = set()
    for f in list(HERE.glob("*/packets.jsonl")):
        for line in open(f, encoding="utf-8", errors="replace"):
            previous.add(json.loads(line)["address"].upper())

    addrs: list[tuple[str, str, dict]] = []
    unfound: list[dict] = []
    for lga, n in LGAS.items():
        poly = lga_shape(lga)
        minx, miny, maxx, maxy = poly.bounds
        got = 0
        while got < n:
            x, y = rnd.uniform(minx, maxx), rnd.uniform(miny, maxy)
            if not poly.contains(Point(x, y)):
                continue
            near = address_near(x, y)
            if not near:
                continue
            addr = rnd.choice(near)
            if addr.upper() in previous or any(addr == b for _, b, _ in addrs):
                continue
            try:  # the product must find the address; a 404 is recorded and redrawn
                prop = json.loads(get(f"{BASE}/api/property?address={urllib.parse.quote(addr)}"))
            except Exception as e:  # noqa: BLE001
                unfound.append({"lga": lga, "address": addr, "error": str(e)})
                continue
            for _ in range(2):  # a cold first lookup can return empty constraints; the page retries too
                if ((prop.get("data") or {}).get("constraints") or {}).get("formerCouncil"):
                    break
                time.sleep(5)
                prop = json.loads(get(f"{BASE}/api/property?address={urllib.parse.quote(addr)}"))
            if not prop.get("success") or not prop.get("data"):
                unfound.append({"lga": lga, "address": addr, "error": prop.get("error")})
                continue
            addrs.append((lga, addr, prop))
            got += 1
            print(lga, addr, flush=True)

    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    summary, packets = [], []
    for idx, (lga, addr, prop) in enumerate(addrs):
        tag = f"{idx:03d}"
        p = prop.get("data") or {}
        if not prop.get("success") or not p:
            summary.append({"idx": tag, "address": addr, "lga": lga, "error": prop.get("error")})
            continue
        q = for_property_params(p)
        if "former_council" not in q:
            summary.append({"idx": tag, "address": addr, "lga": lga, "error": "no formerCouncil (page fetches nothing)",
                            "constraints": {k: (p.get("constraints") or {}).get(k) for k in ("lga", "zone")}})
            continue
        fp = json.loads(get(f"{BASE}/api/provisions/for-property?{urllib.parse.urlencode(q)}", timeout=180))
        rows = {r["id"]: r for layer in (fp.get("data") or {}).get("by_layer", []) for r in layer["provisions"]}
        c = p.get("constraints") or {}
        prop_view = {"zone": c.get("zone"), "lga": c.get("lga"), "formerCouncil": c.get("formerCouncil"),
                     "precinctId": c.get("precinctId"), "heritage": p.get("heritage"),
                     "flood": q.get("flood"), "bushfire": q.get("bushfire"),
                     "coords": p.get("coordinates"), "land_application": c.get("landApplicationInstruments")}
        summary.append({"idx": tag, "address": addr, "lga": lga, "served": len(rows), "params": q,
                        "property": prop_view, "precinct_warning": fp.get("meta", {}).get("precinct_warning")})
        print(tag, addr, len(rows), flush=True)
        for rid in rnd.sample(sorted(rows), min(a.per_address, len(rows))):
            r = rows[rid]
            cur.execute("""SELECT rp.source_council, rp.source_chapter_key, d.pdf_name, d.r2_pdf_url,
                                  rp.quote_status, rp.quote_reason, rp.quote_page, rp.v2_applicable_zones,
                                  rp.ref_number, rp.citation_status
                           FROM regulatory_provisions rp LEFT JOIN documents d ON d.id = rp.document_id
                           WHERE rp.id = %s""", (rid,))
            dbr = cur.fetchone()
            shown = r.get("pdf_page")
            text = None
            try:
                text = pdf_page_text(dbr[3] if dbr else None, shown)
            except Exception as e:  # noqa: BLE001
                text = f"<pdf error {e}>"
            packets.append({
                "rule_key": f"{tag}:{rid}", "address": addr, "council": dbr[0] if dbr else None,
                "property": prop_view, "rule_text": r.get("provision_text"),
                "chapter": dbr[1] if dbr else None, "document": dbr[2] if dbr else None,
                "ref_number": dbr[8] if dbr else None,
                "rule_gate": {"precinct": r.get("v2_precinct_id"), "marker": r.get("v2_marker"),
                              "zones": dbr[7] if dbr else None, "layer": r.get("v2_dcp_layer"),
                              "part": r.get("v2_dcp_part")},
                "stored_word_check": {"status": dbr[4], "reason": dbr[5], "quote_page": dbr[6],
                                      "citation_status": dbr[9]} if dbr else None,
                "shown_page": shown, "printed_page": r.get("pdf_printed_page"),
                "source_url": dbr[3] if dbr else None, "pdf_page_text": text})
    summary.append({"unfound_redrawn": unfound})
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "packets.jsonl", "w", encoding="utf-8") as f:
        for pk in packets:
            f.write(json.dumps(pk, ensure_ascii=False, default=str) + "\n")
    print("addresses", len(addrs), "packets", len(packets),
          "errors", sum(1 for s in summary if "error" in s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
