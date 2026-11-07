"""Where a lot sits against the ANEF 25 contour of Sydney Airport's endorsed 2045 chart.

prior-art-checked: 2026-11-08. grep of services/ for anef: only the Western Sydney portal band rule in lmr_area_inputs.py exists (Sydney's own chart was
"not held"). The data file comes from scripts/anef/build_sydney_anef_2045.py; this module only reads it. Pure Python: no network, no PDF, no pyproj.

The law (SEPP Housing 2021 s164(1)(h)) excludes land in an ANEF contour of 25 or greater. The chart gives the 25 line to a measured accuracy; a lot
closer to the line than that margin cannot be placed on one side of it, and is reported as such, never guessed.

The chart's map frame wholly contains the outermost (20) line, so a lot entirely outside the frame is outside every contour on the chart.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "anef" / "sydney_anef_2045.json"
LAW_LEVEL = 25  # the level used when a caller does not name one; the decision passes the law's own level, read from law_facts
_M_PER_DEG = math.radians(1.0) * 6378137.0  # metres per degree of latitude (and of longitude at the equator)
MAX_INTERIOR_SAMPLES = 50  # noqa: regulatory-number -- grid size when a lot encloses part of a contour, not a planning figure
OUTLINE_STEP_M = 5.0  # noqa: regulatory-number -- the lot outline is sampled at most this far apart; a sampling step, not a planning figure


class SydneyAnefError(Exception):
    """The data file is missing or unreadable."""


@lru_cache(maxsize=1)
def load(path: str = str(DATA_PATH)) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SydneyAnefError(f"Sydney ANEF 2045 data unreadable: {exc}") from exc


def _inside(poly: list[tuple[float, float]], x: float, y: float) -> bool:
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _dist_to_ring(poly: list[tuple[float, float]], x: float, y: float) -> float:
    best = float("inf")
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        d = math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
        if d < best:
            best = d
    return best


def _outline_points(lat: float, lng: float, ring: Optional[list]) -> list[tuple[float, float]]:
    """The lot's outline (one ring of [lon, lat]) densified to OUTLINE_STEP_M between points, as (lon, lat); the address point alone when no outline is held."""
    if not ring or len(ring) < 4:   # fewer than 4 points (a closed triangle) is not a lot outline
        return [(lng, lat)]
    pts: list[tuple[float, float]] = []
    for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
        n = max(1, math.ceil(math.hypot((x2 - x1) * 91000.0, (y2 - y1) * 111000.0) / OUTLINE_STEP_M))
        pts += [(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n) for k in range(n)]
    pts.append((ring[-1][0], ring[-1][1]))
    return pts


def classify_all(lat: float, lng: float, ring: Optional[list] = None) -> dict:
    """classify() at every contour level the chart has, keyed by the level as text ("20", "25", ...).
    The caller compares the right one with the law's level, which is read from the saved law and never typed here."""
    return {f"{c['anef']:g}": classify(lat, lng, ring, c["anef"]) for c in load()["contours"]}  # noqa: bracket-access -- committed file; a missing key raises and gather() reports "no answer"


def classify(lat: float, lng: float, ring: Optional[list] = None, level: float = LAW_LEVEL) -> dict:
    """{"state": "inside" | "outside" | "near", "margin_m", "inside_by_m", "nearest_m", "level", "outside_frame", "contour_levels"}
      inside   some part of the lot is inside the `level` contour by more than the margin
      outside  every part of the lot is outside it by more than the margin (or the whole lot is outside the chart's map frame)
      near     neither: the lot is within the margin of the line (or straddles it), so the chart cannot place it
    The lot is its outline when one is held, else the address point. `level` must be one of the chart's levels (20, 25, 30, 35)."""
    doc = load()
    # Every key below comes from the committed data file, which tests/test_sydney_anef.py checks. A missing key raises and gather() reports "no answer";
    # it is never turned into a default, because a default here would be a guess about where an aircraft-noise line is.
    contour = next((c for c in doc["contours"] if c["anef"] == level), None)  # noqa: bracket-access -- committed file, fails closed
    if contour is None:
        raise SydneyAnefError(f"the chart has no ANEF {level:g} contour")
    margin = float(doc["accuracy"]["margin_m"])  # noqa: bracket-access -- committed file, fails closed
    levels = [c["anef"] for c in doc["contours"]]  # noqa: bracket-access -- committed file, fails closed
    f = doc["frame_lonlat"]  # noqa: bracket-access -- committed file, fails closed
    pts = _outline_points(lat, lng, ring)
    on_map = any(f["west"] <= x <= f["east"] and f["south"] <= y <= f["north"] for x, y in pts)  # noqa: bracket-access -- committed file, fails closed
    if not on_map and ring and len(ring) >= 4:  # a lot big enough to enclose the whole map has no boundary point on it
        corners = [(f["west"], f["south"]), (f["east"], f["south"]), (f["east"], f["north"]), (f["west"], f["north"])]  # noqa: bracket-access -- committed file, fails closed
        on_map = any(_inside(ring, x, y) for x, y in corners)
    if not on_map:
        # no part of the lot is on the chart's map; the frame wholly contains the outermost contour, so the lot is outside every contour
        return {"state": "outside", "margin_m": margin, "inside_by_m": None, "nearest_m": None, "level": level, "outside_frame": True, "contour_levels": levels}
    kx, ky = _M_PER_DEG * math.cos(math.radians(lat)), _M_PER_DEG
    poly = [((x - lng) * kx, (y - lat) * ky) for x, y in contour["ring_lonlat"]]  # noqa: bracket-access -- committed file, fails closed
    samples = [((x - lng) * kx, (y - lat) * ky) for x, y in pts]
    encloses = False
    if ring and len(ring) >= 4:
        lot = [((x - lng) * kx, (y - lat) * ky) for x, y in ring]
        # A lot that encloses part of the contour has none of its boundary inside the line, so its inside must be sampled too.
        encloses = any(_inside(lot, vx, vy) for vx, vy in poly)
        if encloses:
            xs, ys = [p[0] for p in lot], [p[1] for p in lot]
            step = max(10.0, max(max(xs) - min(xs), max(ys) - min(ys)) / MAX_INTERIOR_SAMPLES)
            gx = [min(xs) + step * (i + 0.5) for i in range(int((max(xs) - min(xs)) / step) + 1)]
            gy = [min(ys) + step * (j + 0.5) for j in range(int((max(ys) - min(ys)) / step) + 1)]
            samples += [(x, y) for x in gx for y in gy if _inside(lot, x, y)]
    deepest_inside: Optional[float] = None  # the lot's most-inside point, in metres inside the line
    nearest = 0.0 if encloses else float("inf")  # the lot's closest point to the line, either side; a lot that holds part of the line touches it
    for px, py in samples:
        d = _dist_to_ring(poly, px, py)
        nearest = min(nearest, d)
        if _inside(poly, px, py):
            deepest_inside = d if deepest_inside is None else max(deepest_inside, d)
    if deepest_inside is not None and deepest_inside > margin:
        state = "inside"
    elif deepest_inside is None and nearest > margin:
        state = "outside"
    else:
        state = "near"
    return {"state": state, "margin_m": margin, "inside_by_m": None if deepest_inside is None else round(deepest_inside, 1),
            "nearest_m": round(nearest, 1), "level": level, "outside_frame": False, "contour_levels": levels}
