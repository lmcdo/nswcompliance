# prior-art-checked: tests/test_lmr_map_copy.py and tests/test_lmr_flood_study.py test flood_distance's results and the rule built on it; neither compares the vectorised
# implementation with the plain method it replaced. This file holds that plain method as the reference, so a faster rewrite cannot silently change a figure.
"""flood_distance must return exactly what the plain method returns: every flood area near the lot projected to metres and measured one by one.

The reference below is that plain method (the code before 2026-11-25, which took 7 to 11 s for a lot in the Hawkesbury-Nepean basin). The fast code projects all
areas in one numpy call, measures them in C and looks near the lot first, widening only when the nearest thing found is farther than the box searched."""
from __future__ import annotations

import math
import random
from pathlib import Path

import pytest

from services import lmr_map_copy as mc

MAPS = Path(__file__).resolve().parents[1] / "data" / "law" / "maps"


def _reference(copy: mc.MapCopy, key: str, lat: float, lng: float, rings):
    from shapely.geometry import Point, Polygon
    from shapely.ops import transform

    lay = copy.layer(mc.COPY_KEYS[key])
    target = Point(lng, lat)
    if rings and len(rings) >= 4:
        target = Polygon(rings)
    mx, my = 111320.0 * math.cos(math.radians(lat)), 110540.0

    def metric(g):
        return transform(lambda x, y, z=None: ((x - lng) * mx, (y - lat) * my), g)

    cand = list(lay.tree.query(target.buffer(mc.FLOOD_SEARCH_DEG)))
    inside = any(lay.geoms[i].intersects(target) for i in cand)
    nearest = edge = None
    if cand:
        t_m = metric(target)
        nearest = 0.0 if inside else min(t_m.distance(metric(lay.geoms[i])) for i in cand)
        edge = min(t_m.distance(metric(lay.geoms[i].boundary)) for i in cand)
    return {"inside": inside, "edge_m": None if edge is None else round(edge, 1), "nearest_m": None if nearest is None else round(nearest, 1), "polygons": len(cand)}


def _square(lat, lng, h=0.0002):
    return [[lng - h, lat - h], [lng + h, lat - h], [lng + h, lat + h], [lng - h, lat + h], [lng - h, lat - h]]


@pytest.fixture(scope="module")
def copy():
    return mc.MapCopy(MAPS)


def _points():
    rnd = random.Random(11)
    inside_basin = [(rnd.uniform(-33.95, -33.45), rnd.uniform(150.35, 151.30)) for _ in range(5)]
    far_away = [(rnd.uniform(-34.6, -32.9), rnd.uniform(149.5, 152.0)) for _ in range(2)]
    return inside_basin + far_away


@pytest.mark.parametrize("with_outline", [False, True])
def test_the_fast_flood_distance_equals_the_plain_method(copy, with_outline):
    seen = set()
    for lat, lng in _points():
        rings = _square(lat, lng) if with_outline else None
        got = copy.flood_distance("hn_pmf", lat, lng, rings)
        want = _reference(copy, "hn_pmf", lat, lng, rings)
        assert got is not None
        assert {k: got[k] for k in want} == want, (lat, lng)
        seen.add("inside" if want["inside"] else ("none" if want["nearest_m"] is None else "near"))
    assert {"near"} <= seen, "the sample should include a lot near a flood area"


def test_a_flood_area_found_in_the_first_box_but_a_nearer_edge_outside_it_is_still_found(copy):
    """The first box is small; a lot inside a big flood area has its nearest edge farther away. The widening must find it: the answer is the same as searching everything."""
    lat, lng = -33.7238, 150.8818   # a point inside the PMF extent whose nearest edge is about 110 m away at this scale, found only after widening is possible
    got = copy.flood_distance("hn_pmf", lat, lng, None)
    want = _reference(copy, "hn_pmf", lat, lng, None)
    assert {k: got[k] for k in want} == want


def test_the_polygon_count_is_still_the_whole_search_box_not_the_first_small_box(copy):
    lat, lng = -33.7238, 150.8818
    got = copy.flood_distance("hn_pmf", lat, lng, None)
    assert got["polygons"] == _reference(copy, "hn_pmf", lat, lng, None)["polygons"] > 1


# ---- synthetic layers: the cases real data rarely makes, where the first small search box is not enough ----
LAT, LNG = -33.70, 150.80   # a lot here: one degree east is about 92.6 km, one degree north about 110.5 km, so the same degrees are not the same metres


def _fake_copy(polygons):
    from datetime import date

    from shapely.geometry import box

    geoms = [box(*p) for p in polygons]
    lay = mc._Layer(geoms, [{} for _ in geoms], date(2026, 11, 22), 0, 400)
    c = mc.MapCopy(MAPS)
    c.layer = lambda name, today=None: lay   # every flood layer name returns the synthetic layer
    return c


def _same(copy, lat=LAT, lng=LNG):
    got = copy.flood_distance("hn_pmf", lat, lng, None)
    want = _reference(copy, "hn_pmf", lat, lng, None)
    assert {k: got[k] for k in want} == want
    return got


def test_a_nearer_area_just_outside_the_first_box_beats_a_farther_one_inside_it():
    # north area 0.0099 deg away (about 1,094 m, inside the 0.01 deg box); east area 0.0101 deg away (about 935 m, just outside the box) is nearer in metres
    north = (LNG - 0.0001, LAT + 0.0099, LNG + 0.0001, LAT + 0.0110)
    east = (LNG + 0.0101, LAT - 0.0001, LNG + 0.0110, LAT + 0.0001)
    got = _same(_fake_copy([north, east]))
    assert 930 < got["nearest_m"] < 940, got


def test_the_nearest_edge_can_be_farther_than_the_nearest_area_and_a_smaller_area_beyond_the_box_has_the_nearer_edge():
    # the lot is inside a big area whose own edge is about 2.2 km away; a small area 0.016 deg east (about 1.5 km) is outside the first box and has the nearer edge
    big = (LNG - 0.025, LAT - 0.025, LNG + 0.025, LAT + 0.025)
    small = (LNG + 0.016, LAT - 0.0001, LNG + 0.017, LAT + 0.0001)
    got = _same(_fake_copy([big, small]))
    assert got["inside"] is True and got["nearest_m"] == 0.0 and 1450 < got["edge_m"] < 1560, got


def test_no_flood_area_within_the_search_distance_is_none_not_zero():
    far = (LNG + 0.5, LAT + 0.5, LNG + 0.51, LAT + 0.51)
    got = _same(_fake_copy([far]))
    assert got["nearest_m"] is None and got["edge_m"] is None and got["inside"] is False
