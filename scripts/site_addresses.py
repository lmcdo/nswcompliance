#!/usr/bin/env python3
"""Address-only single sites: the chapter's street address -> NSW address register -> parcels.

prior-art-checked: called by scripts/build_site_boundaries.py --addresses, which owns the load.
Reuses its verbatim_on_page / address register endpoint and nsw_cadastre_lots. No other script
turns a DCP's street address range into parcels (grep of scripts/ for the register endpoint,
2026-10-11: only point lookups by single address exist).

PROOF (each check must pass or the site is held -- DQ-143, 2026-10-11)
  1 verbatim   the address text is on the cited PDF page
  2 named      every number the chapter names exactly (range ends, single numbers) is in the register
  3 neighbours no register address on the same street within 10 numbers that is NOT in the range --
               next door either side, or across the street -- has its point inside the outline
  4 area       within 10% of the area the chapter states (when it states one)
  5 fallback   Inner West only, as build_site_boundaries check 5
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

import build_site_boundaries as b

NEIGHBOUR_SPAN = 10


def parse_numbers(spec: str) -> tuple[set[str], set[str]]:
    """'15-33' -> (odd 15..33, {'15','33'}); '20-21' -> ({'20','21'}, ...); '22,30-40'; '2,2A'.

    Returns (every number in the site, the numbers the chapter names exactly). A range whose ends
    share parity is one side of the street (NSW numbering convention); otherwise every number."""
    site: set[str] = set()
    named: set[str] = set()
    for part in (p.strip() for p in spec.split(",") if p.strip()):
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            a, z = int(m.group(1)), int(m.group(2))
            step = 2 if a % 2 == z % 2 else 1
            site.update(str(n) for n in range(a, z + 1, step))
            named.update({str(a), str(z)})
        else:
            site.add(part.upper())
            named.add(part.upper())
    return site, named


def _base_numbers(address: str, street: str, suburb: str) -> list[str]:
    """'1/23-25 BRIGHTON AVENUE CROYDON PARK' -> ['23', '25']; '2A ...' -> ['2A']."""
    head = address[: -len(f" {street} {suburb}")] if address.endswith(f" {street} {suburb}") else ""
    base = head.split("/")[-1].strip()
    return [x for x in re.split(r"\s*-\s*", base) if x]


def register(street: str, suburb: str) -> list[tuple[str, float, float]]:
    """Every address point on the street in that suburb: (address, x, y). Pages through results."""
    out, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"where": f"address LIKE '% {street} {suburb}'", "outFields": "address",
                                    "returnGeometry": "true", "outSR": 4326, "f": "json",
                                    "resultOffset": offset, "resultRecordCount": 1000})
        d = json.load(urllib.request.urlopen(urllib.request.Request(f"{b.ADDRESS_POINTS}?{q}", headers=b.UA),
                                             timeout=90))
        feats = d.get("features") or []
        out += [(f["attributes"]["address"], f["geometry"]["x"], f["geometry"]["y"]) for f in feats]
        if not d.get("exceededTransferLimit") or not feats:
            return out
        offset += len(feats)


def _lettered(nums: set[str]) -> bool:
    return any(re.search(r"[A-Z]", n) for n in nums)


def _int(token: str) -> int | None:
    m = re.match(r"\d+", token)
    return int(m.group(0)) if m else None


def prove_address(cur, site: dict) -> dict:
    site_nums, named = parse_numbers(site["numbers"])
    r: dict = {"precinct_id": site["precinct_id"], "lots_listed": 0, "missing_lots": [], "checks": {}}
    r["checks"]["1_verbatim"] = b.verbatim_on_page({**site, "lots_verbatim": site["address_verbatim"]})
    points = register(site["street"], site["suburb"])
    inside, near, found = [], [], set()
    lo = min(_int(n) for n in site_nums if _int(n) is not None) - NEIGHBOUR_SPAN
    hi = max(_int(n) for n in site_nums if _int(n) is not None) + NEIGHBOUR_SPAN
    for addr, x, y in points:
        nums = _base_numbers(addr, site["street"], site["suburb"])
        if not nums:
            continue
        found.update(nums)
        # A lettered number (149A, 22B) is a subdivided part of its base number, so it belongs to
        # the site when the base number does -- unless the chapter names lettered numbers itself.
        if any(n in site_nums or (str(_int(n)) in site_nums and not _lettered(site_nums)) for n in nums):
            inside.append((addr, x, y))
        elif any(lo <= (_int(n) or -1) <= hi for n in nums):
            near.append((addr, x, y))
    r["missing_named"] = sorted(named - found)
    r["checks"]["2_named"] = not r["missing_named"] and bool(inside)
    r["site_addresses"] = sorted({a for a, _, _ in inside})
    pts = [f"POINT({x} {y})" for _, x, y in inside]
    cur.execute("SELECT array_agg(DISTINCT l.lotidstring), ST_AsText(ST_Multi(ST_Union(l.geom))),"
                " ST_Area(ST_Union(l.geom)::geography) FROM nsw_cadastre_lots l"
                " JOIN unnest(%s::text[]) p(wkt) ON ST_Contains(l.geom, ST_GeomFromText(p.wkt, 4326))",
                (pts,))
    lots, r["wkt"], area = cur.fetchone()
    r["lots"], r["lots_listed"], r["area_m2"] = sorted(lots or []), len(lots or []), round(area or 0)
    leaked = []
    for addr, x, y in near:
        cur.execute("SELECT ST_Contains(ST_GeomFromText(%s, 4326), ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
                    (r["wkt"], x, y))
        if r["wkt"] and cur.fetchone()[0]:
            leaked.append(addr)
    r["neighbours_checked"], r["neighbours_inside"] = len(near), sorted(set(leaked))
    r["checks"]["3_neighbours"] = bool(r["wkt"]) and not leaked
    stated = site.get("stated_area_m2")
    r["checks"]["4_area"] = (abs(r["area_m2"] - stated) <= b.AREA_TOLERANCE * stated) if stated else None
    if site["lga"] == "Inner West" and r["wkt"]:
        r["fallback_exposed_lots"] = b.fallback_exposed(cur, r["wkt"])
        r["checks"]["5_fallback"] = r["fallback_exposed_lots"] == 0
    r["ok"] = all(v is not False for v in r["checks"].values())
    return r
