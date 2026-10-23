"""Measure the % of each council (LGA) area mapped as bush fire prone land.

prior-art-checked: no existing script measures BFPL coverage by LGA; spatial_overlays
bushfire rows are incomplete (306 vs 381 features in a Ku-ring-gai test box), so the
official service is read directly.

Sources (both public, read only):
  LGA polygon: NSW Spatial Services Administrative Boundaries, layer 8 (lganame).
  BFPL:        NSW RFS Bush Fire Prone Land MapServer layer 0 (all categories + buffer).

BFPL pieces are clipped to the LGA and unioned, so overlapping categories are not
double counted. Areas are taken in EPSG:3577 (GDA94 Australian Albers, equal area).

Usage:
  python scripts/measure_bfpl_coverage.py "KU-RING-GAI" WAVERLEY
  BFPL_PAGE=100 BFPL_TILES=4 python scripts/measure_bfpl_coverage.py "CLARENCE VALLEY"
Prints one tab-separated line per LGA, or ERROR. A failure is printed, never a guess.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from pyproj import Transformer
from shapely import make_valid, union_all
from shapely.geometry import box, shape
from shapely.ops import transform

LGA_SVC = ("https://portal.spatial.nsw.gov.au/server/rest/services/"
           "NSW_Administrative_Boundaries_Theme/FeatureServer/8/query")
BFPL_SVC = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/0/query"
PAGE = int(os.environ.get("BFPL_PAGE", "100"))
TILES = int(os.environ.get("BFPL_TILES", "1"))
TO_ALBERS = Transformer.from_crs(4326, 3577, always_xy=True).transform


def _get(url: str, params: dict) -> dict:
    """GET JSON with retries; the BFPL service returns transient 500/502s."""
    q = urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(f"{url}?{q}", timeout=180) as r:
                body = json.load(r)
            # ArcGIS reports some failures as HTTP 200 with an "error" body; an
            # empty result must be an explicit features list, never a missing one.
            if "error" in body or not isinstance(body.get("features"), list):
                raise ValueError(f"bad response: {str(body)[:200]}")
            return body
        except (urllib.error.HTTPError, ValueError):
            if attempt == 5:
                raise
            time.sleep(20 * (attempt + 1))
    raise RuntimeError("unreachable")


def lga_geom(name: str):
    """The LGA polygon, by its Spatial Services lganame."""
    fc = _get(LGA_SVC, {"where": f"lganame='{name}'", "outFields": "lganame",
                        "returnGeometry": "true", "outSR": "4326", "f": "geojson"})
    geoms = [make_valid(shape(f["geometry"])) for f in fc["features"]]
    if not geoms:
        raise ValueError(f"no LGA polygon for {name}")
    return union_all(geoms)


def tiles(g, n: int):
    """Split g into an n x n grid of pieces (for very large LGAs)."""
    minx, miny, maxx, maxy = g.bounds
    dx, dy = (maxx - minx) / n, (maxy - miny) / n
    for i in range(n):
        for j in range(n):
            t = box(minx + i * dx, miny + j * dy, minx + (i + 1) * dx, miny + (j + 1) * dy).intersection(g)
            if not t.is_empty:
                yield t


def bfpl_in(g) -> list:
    """Every BFPL feature meeting g's bounding box, clipped to g."""
    minx, miny, maxx, maxy = g.bounds
    out, offset = [], 0
    while True:
        fc = _get(BFPL_SVC, {
            "geometry": f"{minx},{miny},{maxx},{maxy}", "geometryType": "esriGeometryEnvelope",
            "inSR": "4326", "spatialRel": "esriSpatialRelIntersects", "outFields": "d_Category",
            "returnGeometry": "true", "outSR": "4326", "f": "geojson",
            "orderByFields": "OBJECTID", "resultOffset": offset, "resultRecordCount": PAGE})
        feats = fc["features"]
        for f in feats:
            if f.get("geometry"):
                p = make_valid(shape(f["geometry"])).intersection(g)
                if not p.is_empty:
                    out.append(p)
        if len(feats) < PAGE and not fc.get("exceededTransferLimit"):
            return out
        offset += len(feats)


def measure(name: str) -> tuple:
    """(percent mapped BFPL, LGA km2, pieces) for one LGA."""
    lga = lga_geom(name)
    parts = []
    for t in tiles(lga, TILES):
        parts += bfpl_in(t)
    bf = union_all(parts) if parts else None
    a_lga = transform(TO_ALBERS, lga).area
    a_bf = transform(TO_ALBERS, bf).area if bf is not None else 0.0
    return a_bf / a_lga * 100, a_lga / 1e6, len(parts)


if __name__ == "__main__":
    failed = 0
    for lga_name in sys.argv[1:]:
        try:
            pct, km2, n = measure(lga_name)
            print(f"{lga_name}\t{pct:.3f}%\tLGA {km2:.0f} km2\t{n} pieces", flush=True)
        except Exception as e:  # report and move on
            print(f"{lga_name}\tERROR {type(e).__name__}: {e}", flush=True)
            failed += 1
    sys.exit(1 if failed else 0)
