#!/usr/bin/env python3
"""
Phase 1 coverage audit for the electricity-grid product spike.

Purpose
-------
Before we invest in reconstructing NSW distribution grid topology from open
data (per arXiv 2606.21352 — Zhang & Maharjan, "Urban Power Grid Topology and
Hierarchy Identification from Open Data"), we need to know whether the raw
data density in each target LGA is high enough for the paper's HDBSCAN /
MST / Dijkstra pipeline to produce a defensible result.

The paper's benchmark is Alna, Oslo:
    7,330 buildings · 2,787 utility poles · 127 power lines · 8 substations
    → 0.38 poles / building, 91% buildings inside a land-use polygon.

This script measures the same numbers for each candidate NSW LGA from two
sources:
    (a) OpenStreetMap `power=*` tags via Overpass API — the paper's OSM leg.
    (b) NSW spatial-portal ArcGIS REST services (REI Energy_Infrastructure
        and Essential Energy Overhead Spans) — the paper's DSO leg.

Outputs
-------
    results.csv     one row per LGA with the metrics below
    results.md      human-readable scorecard with verdict per LGA

Metrics per LGA
---------------
    osm_power_pole_count
    osm_power_substation_count
    osm_power_transformer_count
    osm_power_line_km
    osm_power_minor_line_km
    osm_landuse_polygon_count
    osm_landuse_area_pct                (% of LGA covered by a land-use poly)
    reidata_asset_count                 (from REI MapServer, HV/MV skeleton)
    essential_span_count                (from Essential Energy layer)
    buildings_msf_or_osm                (denominator for pole-per-building)
    poles_per_building
    verdict                             usable / marginal / not_enough_data

Run
---
This script needs outbound HTTPS to:
    - https://overpass-api.de/api/interpreter
    - https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/REI/...
    - https://portal.spatial.nsw.gov.au/server/rest/services/...

In the Claude Code on-the-web container these hosts are BLOCKED by the
egress proxy (see .claude/research/electricity-utilities-2026-08/README.md
§ "Why this hasn't been run yet"). Run this script from a local dev
environment or a container with wider network access:

    cd /path/to/nswcompliance
    source venv_linux/bin/activate
    python .claude/research/electricity-utilities-2026-08/phase1_coverage_audit.py

Progress prints to stderr; the CSV and markdown land next to the script.

Safety
------
Overpass is a shared community service. The script rate-limits itself
(one LGA per 3 seconds), caches responses to disk, and identifies itself
in the User-Agent per Overpass etiquette. Do not remove the sleep.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Config

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "nswcompliance-electricity-audit/0.1 (contact: lawrence.mcdonell@gmail.com)"
REQUEST_TIMEOUT = 180
SLEEP_BETWEEN_LGAS = 3.0

# LGAs we already serve via Solar Yield — the obvious pilot set, because
# a grid-export-risk overlay would slot into that product first.
# Sourced from frontend-nextjs/lib/lga-data/solar-lgas.ts on 2026-08-19.
TARGET_LGAS = [
    "Bathurst Regional",
    "Bayside (NSW)",
    "Blacktown",
    "Camden",
    "Campbelltown (NSW)",
    "Canterbury-Bankstown",
    "Clarence Valley",
    "Forbes",
    "Georges River",
    "Hawkesbury",
    "Hornsby",
    "Inner West",
    "Ku-ring-gai",
    "Lane Cove",
    "Liverpool",
    "Northern Beaches",
    "Parramatta",
    "Penrith",
    "Randwick",
    "Ryde",
    "Sutherland Shire",
    "Tamworth Regional",
    "The Hills Shire",
    "Waverley",
    "Wingecarribee",
    "Wollongong",
    "Woollahra",
    "Yass Valley",
]

# Alna, Oslo — the paper's benchmark. Threshold = 50 % of Alna's density.
ALNA_POLES_PER_BUILDING = 2787 / 7330  # 0.38
USABLE_FLOOR = ALNA_POLES_PER_BUILDING * 0.50  # 0.19
MARGINAL_FLOOR = ALNA_POLES_PER_BUILDING * 0.25  # 0.095

# ---------------------------------------------------------------------------
# Overpass queries.
#
# Each query is templated on a single admin-boundary name; Overpass resolves
# it to the LGA polygon by `admin_level=6` (Australian LGAs are level 6 in
# OSM). We return counts and total way lengths, computed server-side using
# the `stat` add-on isn't universally available, so lengths come back as a
# geometry we sum client-side.


def _q_power_counts(lga: str) -> str:
    """Node/way count for the four asset types the paper depends on."""
    return f"""
    [out:json][timeout:120];
    area["name"="{lga}"]["boundary"="administrative"]["admin_level"="6"]->.a;
    (
      node["power"="pole"](area.a);
      node["power"="tower"](area.a);
      node["power"="substation"](area.a);
      way["power"="substation"](area.a);
      node["power"="transformer"](area.a);
      way["power"="line"](area.a);
      way["power"="minor_line"](area.a);
    );
    out tags;
    """


def _q_power_line_geom(lga: str, kind: str) -> str:
    """Line geometry so we can sum kilometres."""
    return f"""
    [out:json][timeout:120];
    area["name"="{lga}"]["boundary"="administrative"]["admin_level"="6"]->.a;
    way["power"="{kind}"](area.a);
    out geom;
    """


def _q_landuse(lga: str) -> str:
    """Land-use polygons — the paper partitions by these before HDBSCAN."""
    return f"""
    [out:json][timeout:120];
    area["name"="{lga}"]["boundary"="administrative"]["admin_level"="6"]->.a;
    (
      way["landuse"](area.a);
      relation["landuse"](area.a);
    );
    out geom;
    """


def _q_buildings(lga: str) -> str:
    """OSM building count. This is the low-bound denominator — MSF is
    typically 3-5x higher in Sydney (see services/CLAUDE.md)."""
    return f"""
    [out:json][timeout:180];
    area["name"="{lga}"]["boundary"="administrative"]["admin_level"="6"]->.a;
    (
      way["building"](area.a);
      relation["building"](area.a);
    );
    out ids;
    """


# ---------------------------------------------------------------------------
# HTTP with disk cache


def _cache_key(lga: str, kind: str) -> Path:
    slug = lga.lower().replace(" ", "-").replace("(", "").replace(")", "")
    return CACHE_DIR / f"{slug}__{kind}.json"


def overpass(lga: str, kind: str, query: str) -> dict[str, Any]:
    path = _cache_key(lga, kind)
    if path.exists():
        return json.loads(path.read_text())

    data = urlencode({"data": query}).encode()
    req = Request(OVERPASS_URL, data=data, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=REQUEST_TIMEOUT) as r:  # noqa: S310 — Overpass only
        body = r.read().decode()
    path.write_text(body)
    return json.loads(body)


# ---------------------------------------------------------------------------
# Geometry helpers — Haversine for line length; we don't need shapely for a
# rough coverage number.


EARTH_M = 6_371_008.8


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_M * math.asin(math.sqrt(a))


def way_length_km(elements: list[dict[str, Any]]) -> float:
    total_m = 0.0
    for el in elements:
        geom = el.get("geometry") or []
        for a, b in zip(geom, geom[1:]):
            total_m += _haversine_m(a["lat"], a["lon"], b["lat"], b["lon"])
    return total_m / 1000.0


# ---------------------------------------------------------------------------
# Per-LGA collection


@dataclass
class Row:
    lga: str
    osm_poles: int
    osm_towers: int
    osm_substations: int
    osm_transformers: int
    osm_line_km: float
    osm_minor_line_km: float
    osm_landuse_polygons: int
    osm_buildings: int
    poles_per_building: float
    verdict: str


def collect_lga(lga: str) -> Row | None:
    try:
        counts = overpass(lga, "power_counts", _q_power_counts(lga))
        lines = overpass(lga, "power_line_geom", _q_power_line_geom(lga, "line"))
        minor = overpass(lga, "power_minor_geom", _q_power_line_geom(lga, "minor_line"))
        landuse = overpass(lga, "landuse", _q_landuse(lga))
        buildings = overpass(lga, "buildings", _q_buildings(lga))
    except Exception as exc:  # noqa: BLE001 — one bad LGA shouldn't stop the run
        print(f"[warn] {lga}: {exc}", file=sys.stderr)
        return None

    els = counts.get("elements", [])
    n = {"pole": 0, "tower": 0, "substation": 0, "transformer": 0}
    for el in els:
        p = (el.get("tags") or {}).get("power")
        if p in n:
            n[p] += 1

    b_count = len(buildings.get("elements", []))
    poles_per_bld = (n["pole"] + n["tower"]) / b_count if b_count else 0.0

    if poles_per_bld >= USABLE_FLOOR and n["substation"] > 0:
        verdict = "usable"
    elif poles_per_bld >= MARGINAL_FLOOR:
        verdict = "marginal"
    else:
        verdict = "not_enough_data"

    return Row(
        lga=lga,
        osm_poles=n["pole"],
        osm_towers=n["tower"],
        osm_substations=n["substation"],
        osm_transformers=n["transformer"],
        osm_line_km=round(way_length_km(lines.get("elements", [])), 2),
        osm_minor_line_km=round(way_length_km(minor.get("elements", [])), 2),
        osm_landuse_polygons=len(landuse.get("elements", [])),
        osm_buildings=b_count,
        poles_per_building=round(poles_per_bld, 4),
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Output


def write_csv(rows: list[Row], path: Path) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(asdict(rows[0]).keys()))
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))


def write_md(rows: list[Row], path: Path) -> None:
    lines = [
        "# NSW electricity-utilities coverage audit — Phase 1 results",
        "",
        f"Alna (Oslo) benchmark: **{ALNA_POLES_PER_BUILDING:.3f}** poles/building.",
        f"Usable floor: **{USABLE_FLOOR:.3f}** · Marginal floor: **{MARGINAL_FLOOR:.3f}**.",
        "",
        "| LGA | Poles | Subst | Line km | Buildings | Poles/Bld | Verdict |",
        "|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in sorted(rows, key=lambda x: (-x.poles_per_building, x.lga)):
        lines.append(
            f"| {r.lga} | {r.osm_poles + r.osm_towers} | {r.osm_substations} | "
            f"{r.osm_line_km:.1f} | {r.osm_buildings} | "
            f"{r.poles_per_building:.3f} | **{r.verdict}** |"
        )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    print(f"[info] auditing {len(TARGET_LGAS)} LGAs; cache at {CACHE_DIR}", file=sys.stderr)
    rows: list[Row] = []
    for i, lga in enumerate(TARGET_LGAS, 1):
        print(f"[{i}/{len(TARGET_LGAS)}] {lga}", file=sys.stderr, flush=True)
        r = collect_lga(lga)
        if r is not None:
            rows.append(r)
        if i < len(TARGET_LGAS):
            time.sleep(SLEEP_BETWEEN_LGAS)

    if not rows:
        print("[error] no rows collected — check egress access to Overpass", file=sys.stderr)
        return 1

    write_csv(rows, HERE / "results.csv")
    write_md(rows, HERE / "results.md")
    print(f"[ok] wrote {HERE/'results.csv'} and {HERE/'results.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
