"""Where a lot sits against the ANEF 25 contour of Sydney Airport's endorsed 2045 chart.

prior-art-checked: 2026-11-08. grep of services/ for anef: only the Western Sydney portal band rule in lmr_area_inputs.py exists (Sydney's own chart was
"not held"). The data file comes from scripts/anef/build_sydney_anef_2045.py; this module only reads it. Pure Python: no network, no PDF, no pyproj.

The law (SEPP Housing 2021 s164(1)(h)) excludes land in an ANEF contour of 25 or greater. The chart gives the 25 line to a measured accuracy; a lot
closer to the line than that margin cannot be placed on one side of it, and is reported as such, never guessed.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "anef" / "sydney_anef_2045.json"
LAW_LEVEL = 25  # the contour the law's level is compared with; the level itself is read from law_facts by the caller, which passes it in


class SydneyAnefError(Exception):
    """The data file is missing or unreadable."""


@lru_cache(maxsize=1)
def load(path: str = str(DATA_PATH)) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SydneyAnefError(f"Sydney ANEF 2045 data unreadable: {exc}") from exc


def _ring_metres(ring: list, lon0: float, lat0: float) -> list[tuple[float, float]]:
    kx = math.radians(1.0) * 6378137.0 * math.cos(math.radians(lat0))
    ky = math.radians(1.0) * 6378137.0
    return [((lon - lon0) * kx, (lat - lat0) * ky) for lon, lat in ring]


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


def _sample_points(lat: float, lng: float, ring: Optional[list]) -> list[tuple[float, float]]:
    """Points that stand for the lot: its outline (one ring of [lon, lat]) densified to about 10 m, or the single point when no outline is held."""
    if not ring:
        return [(lng, lat)]
    pts: list[tuple[float, float]] = []
    for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
        n = max(1, int(math.hypot((x2 - x1) * 91000.0, (y2 - y1) * 111000.0) / 10.0))
        pts += [(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n) for k in range(n)]
    return pts or [(lng, lat)]


def classify_all(lat: float, lng: float, ring: Optional[list] = None) -> Optional[dict]:
    """classify() at every contour level the chart has, keyed by the level as text ("20", "25", ...); None outside the chart's map frame.
    The caller compares the right one with the law's level, which is read from the saved law and never typed here."""
    if classify(lat, lng, ring, LAW_LEVEL) is None:
        return None
    return {f"{c['anef']:g}": classify(lat, lng, ring, c["anef"]) for c in load()["contours"]}  # noqa: bracket-access -- committed file; a missing key raises and gather() reports "no answer"


def classify(lat: float, lng: float, ring: Optional[list] = None, level: float = LAW_LEVEL) -> Optional[dict]:
    """None when the lot is outside the chart's map frame (the chart says nothing there).

    Otherwise {"state": "inside" | "outside" | "near", "margin_m", "inside_by_m", "outside_by_m", "level", "contour_levels"}:
      inside   some part of the lot is inside the `level` contour by more than the margin
      outside  every part of the lot is outside it by more than the margin
      near     neither: the lot is within the margin of the line (or straddles it), so the chart cannot place it
    `level` must be one of the chart's contour levels (20, 25, 30, 35)."""
    doc = load()
    # Every key below comes from the committed data file, which tests/test_sydney_anef.py checks. A missing key raises and gather() reports "no answer";
    # it is never turned into a default, because a default here would be a guess about where an aircraft-noise line is.
    f = doc["frame_lonlat"]  # noqa: bracket-access -- committed file, fails closed
    if not (f["west"] <= lng <= f["east"] and f["south"] <= lat <= f["north"]):  # noqa: bracket-access -- committed file, fails closed
        return None
    contour = next((c for c in doc["contours"] if c["anef"] == level), None)  # noqa: bracket-access -- committed file, fails closed
    if contour is None:
        raise SydneyAnefError(f"the chart has no ANEF {level:g} contour")
    margin = float(doc["accuracy"]["margin_m"])  # noqa: bracket-access -- committed file, fails closed
    poly = _ring_metres(contour["ring_lonlat"], lng, lat)  # noqa: bracket-access -- committed file, fails closed
    deepest_inside: Optional[float] = None  # the lot's most-inside point, in metres inside the line
    nearest = float("inf")  # the lot's closest point to the line, either side
    for x, y in _sample_points(lat, lng, ring):
        px, py = _ring_metres([[x, y]], lng, lat)[0]
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
            "nearest_m": round(nearest, 1), "level": level,
            "contour_levels": [c["anef"] for c in doc["contours"]]}  # noqa: bracket-access -- committed file, fails closed
