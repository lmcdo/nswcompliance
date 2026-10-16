"""Code first pass over an audit run's packets: flag the rules a person must read; sample 10% of the rest.

Severe classes this catches (from runs 1-2): wrong plan for the house, place-limited rule outside its place,
heritage-area rule on a house outside that area, words/numbers not on the shown page (splices, truncation).
It never labels anything "right" -- unflagged rules are only sampled. Usage:

    python scripts/address_audit/flag_packets.py 2026-10-16-run7   # writes <run>/to_read.jsonl + prints counts
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "data" / "address_audit"
PLACE = re.compile(
    r"\b(?:in|within|at|of) (?:the )?(?:former )?([A-Z][a-z]+(?: [A-Z][a-z]+){0,3}) "
    r"(?:local centre|town centre|centre|precinct|local government area|LGA|area|business park|corridor|site|HCA|"
    r"heritage conservation area|estate)\b"
    r"|\bbounded by\b|\bIn [A-Z][a-z]+(?: [A-Z][a-z]+)?,"
    r"|\b\d+[A-Z]?(?:-\d+)? [A-Z][a-z]+ (?:Street|Road|Avenue|Parade|Drive|Lane|Highway|Place)\b"
    r"|\b(?:Street|Road|Avenue|Parade|Drive|Highway)\b",
)
HERITAGE = re.compile(r"heritage conservation area|\bHCA\b|contributory|heritage item", re.I)
NUM = re.compile(r"\d+(?:\.\d+)?")
IN_PLACE = re.compile(r"In [A-Z][a-z]+(?: [A-Z][a-z]+)?|former [A-Z][a-z]+ Local Government Area", re.I)
#: The plan's own council -> the ABS 2015 former LGA it covers (only where one council slug is one former LGA).
ABS_FORMER = {"ashfield": "Ashfield (A)", "leichhardt": "Leichhardt (A)", "marrickville": "Marrickville (A)",
              "northern_beaches": "Warringah (A)"}
#: A DCP that covers only its own LEP's land (Part A "land to which this plan applies").
PLAN_LEP = {"northern_beaches": "Warringah Local Environmental Plan 2011",
            "city_of_sydney": "Sydney Local Environmental Plan 2012"}
_ABS = {}


def abs_former(x: float, y: float) -> str | None:
    """The ABS 2015 LGA containing the point (one HTTP call per point, cached)."""
    import urllib.parse, urllib.request
    k = (round(x, 6), round(y, 6))
    if k not in _ABS:
        q = urllib.parse.urlencode({"geometry": f"{x},{y}", "geometryType": "esriGeometryPoint", "inSR": 4326,
                                    "spatialRel": "esriSpatialRelIntersects", "outFields": "lga_name_2015",
                                    "returnGeometry": "false", "f": "json"})
        u = f"https://geo.abs.gov.au/arcgis/rest/services/ASGS2015/LGA/MapServer/0/query?{q}"
        fs = json.load(urllib.request.urlopen(u, timeout=60)).get("features") or []
        _ABS[k] = fs[0]["attributes"]["lga_name_2015"] if fs else None
    return _ABS[k]


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def on_page(rule: str, page: str) -> float:
    w, pg = norm(rule).split(), norm(page)
    grams = [" ".join(w[i:i + 6]) for i in range(0, max(1, len(w) - 5), 3)]
    return sum(g in pg for g in grams) / max(1, len(grams))


def flags(p: dict) -> list[str]:
    out = []
    prop, rule, page = p.get("property") or {}, p.get("rule_text") or "", p.get("pdf_page_text") or ""
    fc = norm(prop.get("formerCouncil")).replace(" ", "_")
    if p.get("council") and fc and norm(p["council"]).replace(" ", "_") not in (fc, fc.replace("city_of_", "")):
        out.append(f"plan council {p['council']} != house {prop.get('formerCouncil')}")
    for m in PLACE.finditer(rule):
        place = (m.group(1) or m.group(0)).strip()
        if norm(place) not in norm(p.get("address")):
            out.append(f"names a place: {m.group(0)[:50]}")
            break
    co = prop.get("coords") or {}
    if p.get("council") in ABS_FORMER and co.get("lat"):
        got = abs_former(co["lon"], co["lat"])
        if got and got != ABS_FORMER[p["council"]]:
            out.append(f"house is in {got}; plan is {p['council']}")
    lep = PLAN_LEP.get(p.get("council"))
    names = [i.get("name") for i in (prop.get("land_application") or [])]
    if lep and names and lep not in names:
        out.append(f"land application {names}; plan needs {lep}")
    head = re.sub(r"\s+", " ", (page or "")[:300])
    ch = (p.get("chapter") or "").lower()
    if any(w in ch for w in ("unique-env", "scenic", "foreshore", "amendment", "estate", "corridor", "-site")):
        out.append(f"chapter may be area-limited: {ch}")
    for src, txt in (("rule", rule), ("page heading", head), ("chapter", (p.get("chapter") or "").replace("-", " ").title())):
        m = IN_PLACE.search(txt) or (PLACE.search(txt) if src != "rule" else None)
        if m and norm(m.group(1) if m.lastindex else m.group(0)) not in norm(p.get("address")):
            out.append(f"{src} names a place: {m.group(0)[:50]}")
            break
    if (p.get("rule_gate") or {}).get("layer") == "precinct":
        out.append("precinct-layer rule: check the house is in that area")
    her = prop.get("heritage") or {}
    if HERITAGE.search(rule) and not her.get("hcaName") and her.get("heritageType", "").startswith("Item") is False:
        out.append("heritage-area wording; house not in an HCA")
    if (p.get("rule_gate") or {}).get("marker") == "heritage" and not her.get("hcaName"):
        out.append("heritage-marked rule; house in no HCA")
    if re.search(r"heritage", head, re.I) and not her.get("isHeritage"):
        out.append("heritage page; house not heritage")
    score = on_page(rule, page)
    if score < 0.9:
        out.append(f"words on shown page {score:.2f}")
    missing = [n for n in NUM.findall(rule) if n not in page]
    if missing:
        out.append(f"numbers not on page: {missing[:4]}")
    return out


def main() -> int:
    run = HERE / sys.argv[1]
    packets = [json.loads(l) for l in open(run / "packets.jsonl", encoding="utf-8")]
    rnd = random.Random(7)
    picked = []
    for p in packets:
        f = flags(p)
        if f or rnd.random() < 0.10:
            picked.append({**p, "flags": f or ["random 10% sample"]})
    with open(run / "to_read.jsonl", "w", encoding="utf-8") as fh:
        for p in picked:
            fh.write(json.dumps(p, ensure_ascii=False, default=str) + "\n")
    n_flag = sum(1 for p in picked if p["flags"] != ["random 10% sample"])
    print(f"packets {len(packets)} | flagged {n_flag} | random sample {len(picked) - n_flag} | to read {len(picked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
