"""Sydney Airport's endorsed ANEF 2045 chart: the data file, the geometry, and the rule that uses them.

No network and no pyproj: the module is pure Python over a committed file. The geometry tests use a synthetic square so the expected answers are known
without trusting the real data; the data tests check the real file against facts that hold whatever the lines are (closed, nested, labelled, placed).
"""
import json
import math
from pathlib import Path

import pytest

from services import lmr_area_decision as d
from services import sydney_anef as sa

ROOT = Path(__file__).resolve().parent.parent
DOC = json.loads(sa.DATA_PATH.read_text(encoding="utf-8"))
FACTS = d.LawFacts.load()
LAT0, LON0 = -33.94, 151.17


# ---- the data file ---------------------------------------------------------------------------------------------------------------------------
def test_four_closed_rings_labelled_20_25_30_35_with_real_detail():
    assert [c["anef"] for c in DOC["contours"]] == [20, 25, 30, 35]
    assert DOC["levels_read_from_labels_on_the_chart"] == [20, 25, 30, 35]
    for c in DOC["contours"]:
        r = c["ring_lonlat"]
        assert len(r) >= 100, "a contour with few points is hand-drawn, not read from the chart"
        assert r[0] == r[-1], "a contour must be a closed ring"


def _inside(ring, x, y):  # written here on purpose: not the module's own point-in-polygon
    c = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def test_each_contour_lies_wholly_inside_the_one_outside_it_and_in_sydney():
    rings = [c["ring_lonlat"] for c in DOC["contours"]]
    for outer, inner in zip(rings, rings[1:]):
        assert all(_inside(outer, x, y) for x, y in inner)
    f = DOC["frame_lonlat"]
    for r in rings:
        assert all(f["west"] <= x <= f["east"] and f["south"] <= y <= f["north"] for x, y in r)
        assert all(151.0 < x < 151.3 and -34.1 < y < -33.8 for x, y in r)


def test_the_source_and_the_measured_accuracy_are_recorded():
    s, a = DOC["source"], DOC["accuracy"]
    assert s["url"].startswith("https://www.sydneyairport.com.au/") and s["endorsed_by_airservices_australia"] == "2026-02-26"
    assert len(s["pdf_sha256"]) == 64 and s["pdf_page"] == 25
    assert a["share_of_chart_road_points_within_m"]["20"] >= 0.99
    assert a["share_of_chart_road_points_within_m"]["30"] == 1.0, "the margin assumes no chart road point is further than the stated bound from a real road"
    assert max(a["chance_share_within_20m_when_shifted"]) <= 0.5, "the alignment must beat a wrong alignment by a wide margin"
    assert a["alignment_bound_m"] == 30.0 and a["margin_m"] == math.ceil(a["half_drawn_line_width_m"] + a["alignment_bound_m"]) and a["margin_m"] >= 67


def test_the_georeference_file_belongs_to_the_same_pdf_and_was_accepted():
    g = json.loads((ROOT / "data" / "anef" / "sydney_anef_2045_georef.json").read_text(encoding="utf-8"))
    assert g["accepted"] is True and g["pdf_sha256"] == DOC["source"]["pdf_sha256"]
    assert g["share_within_m"]["15"] >= 0.99 and abs(g["ground_m_per_pt"] - 42.2) < 0.5  # the chart's own scale bar says 42.2 m per point


def test_real_geography_that_holds_whatever_the_lines_are():
    centre = sa.classify_all(-33.9461, 151.1772)  # the airport itself
    assert all(centre[k]["state"] == "inside" for k in ("20", "25", "30", "35"))
    for lat, lng in ((-33.8148, 151.0017), (-33.7500, 150.6900)):  # Parramatta, Penrith: wholly outside the chart's map frame
        r = sa.classify_all(lat, lng)
        assert all(v["state"] == "outside" and v["outside_frame"] is True for v in r.values())
    assert sa.classify_all(-33.9461, 151.1772)["25"]["outside_frame"] is False


# ---- the geometry, on a synthetic 1 km square so the answers are known ----------------------------------------------------------------------
def _square(half_m=500.0):
    dlat = half_m / 111319.49
    dlon = half_m / (111319.49 * math.cos(math.radians(LAT0)))
    ring = [[LON0 - dlon, LAT0 - dlat], [LON0 + dlon, LAT0 - dlat], [LON0 + dlon, LAT0 + dlat], [LON0 - dlon, LAT0 + dlat], [LON0 - dlon, LAT0 - dlat]]
    return ring, dlat, dlon


@pytest.fixture
def square(monkeypatch):
    ring, dlat, dlon = _square()
    doc = {"frame_lonlat": {"west": LON0 - 0.1, "east": LON0 + 0.1, "south": LAT0 - 0.1, "north": LAT0 + 0.1},
           "accuracy": {"margin_m": 50.0}, "contours": [{"anef": 25, "ring_lonlat": ring}]}
    monkeypatch.setattr(sa, "load", lambda: doc)
    return dlat, dlon


def at(dlat, dlon, east_m=0.0, north_m=0.0):
    return LAT0 + north_m / 111319.49, LON0 + east_m / (111319.49 * math.cos(math.radians(LAT0)))


@pytest.mark.parametrize("east_m,state", [(0, "inside"), (380, "inside"), (460, "near"), (470, "near"), (520, "near"), (560, "outside"), (900, "outside")])
def test_a_point_is_inside_near_or_outside_by_its_distance_from_the_line(square, east_m, state):
    lat, lng = at(*square, east_m=east_m)
    assert sa.classify(lat, lng)["state"] == state


@pytest.mark.parametrize("east_m,north_m", [(-560, 0), (0, 560), (0, -560), (-600, 600)])
def test_outside_on_every_side_not_just_the_east(square, east_m, north_m):
    lat, lng = at(*square, east_m=east_m, north_m=north_m)
    assert sa.classify(lat, lng)["state"] == "outside"


def test_a_concave_contour_puts_the_notch_outside_and_the_arms_inside(monkeypatch):
    """A U-shaped 25 line: the notch cut into the top is outside it. A ray that crosses the line twice must come out outside."""
    pts_m = [(-500, -500), (500, -500), (500, 500), (150, 500), (150, 0), (-150, 0), (-150, 500), (-500, 500), (-500, -500)]
    kx, ky = 111319.49 * math.cos(math.radians(LAT0)), 111319.49
    ring = [[LON0 + x / kx, LAT0 + y / ky] for x, y in pts_m]
    doc = {"frame_lonlat": {"west": LON0 - 0.1, "east": LON0 + 0.1, "south": LAT0 - 0.1, "north": LAT0 + 0.1},
           "accuracy": {"margin_m": 50.0}, "contours": [{"anef": 25, "ring_lonlat": ring}]}
    monkeypatch.setattr(sa, "load", lambda: doc)
    assert sa.classify(LAT0 + 300 / ky, LON0)["state"] == "outside"            # in the notch
    assert sa.classify(LAT0 + 250 / ky, LON0 - 325 / kx)["state"] == "inside"  # in the left arm
    assert sa.classify(LAT0 - 250 / ky, LON0)["state"] == "inside"             # in the base


def test_a_lot_with_any_part_deep_inside_is_inside_even_if_it_crosses_the_line(square):
    deep = at(*square, east_m=300)   # 200 m inside the east edge
    out = at(*square, east_m=700)    # 200 m outside it
    ring = [[deep[1], deep[0]], [out[1], deep[0]], [out[1], out[0]], [deep[1], out[0]], [deep[1], deep[0]]]
    lat, lng = at(*square, east_m=500)
    r = sa.classify(lat, lng, ring)
    assert r["state"] == "inside" and r["inside_by_m"] > 50


def test_a_lot_wholly_outside_but_within_the_margin_of_the_line_is_near_not_clear(square):
    a, b = at(*square, east_m=520), at(*square, east_m=620)
    ring = [[a[1], a[0]], [b[1], a[0]], [b[1], b[0]], [a[1], b[0]], [a[1], a[0]]]
    r = sa.classify(*at(*square, east_m=570), ring)
    assert r["state"] == "near" and r["nearest_m"] < 50


def test_a_lot_wholly_outside_by_more_than_the_margin_is_outside(square):
    a, b = at(*square, east_m=700), at(*square, east_m=800)
    ring = [[a[1], a[0]], [b[1], a[0]], [b[1], b[0]], [a[1], b[0]], [a[1], a[0]]]
    assert sa.classify(*at(*square, east_m=750), ring)["state"] == "outside"


def test_a_lot_wholly_outside_the_map_frame_is_outside_every_contour(square):
    """The frame wholly contains the outermost line, so a lot entirely outside it is outside every contour."""
    r = sa.classify(LAT0 + 0.5, LON0)
    assert r["state"] == "outside" and r["outside_frame"] is True and r["nearest_m"] is None
    assert all(v["outside_frame"] for v in sa.classify_all(LAT0, LON0 + 0.5).values())


def test_a_lot_whose_address_point_is_off_the_map_but_whose_outline_reaches_the_line_is_still_measured(monkeypatch):
    ring, _, _ = _square()
    doc = {"frame_lonlat": {"west": LON0 - 0.0054, "east": LON0 + 0.0072, "south": LAT0 - 0.0054, "north": LAT0 + 0.0054},   # about 600 m east of centre
           "accuracy": {"margin_m": 50.0}, "contours": [{"anef": 25, "ring_lonlat": ring}]}
    monkeypatch.setattr(sa, "load", lambda: doc)
    a, b = at(0, 0, east_m=400), at(0, 0, east_m=900)   # the outline runs from 100 m inside the line to well outside the frame
    lot_ring = [[a[1], a[0]], [b[1], a[0]], [b[1], b[0]], [a[1], b[0]], [a[1], a[0]]]
    addr = at(0, 0, east_m=800)
    assert addr[1] > doc["frame_lonlat"]["east"]
    r = sa.classify(addr[0], addr[1], lot_ring)
    assert r["state"] == "inside" and r["outside_frame"] is False and 90 < r["inside_by_m"] < 110   # 100 m inside the line, beyond the 50 m margin


def test_a_lot_that_encloses_the_whole_map_is_measured_not_called_off_the_map(monkeypatch):
    ring, _, _ = _square()
    doc = {"frame_lonlat": {"west": LON0 - 0.01, "east": LON0 + 0.01, "south": LAT0 - 0.01, "north": LAT0 + 0.01},
           "accuracy": {"margin_m": 50.0}, "contours": [{"anef": 25, "ring_lonlat": ring}]}
    monkeypatch.setattr(sa, "load", lambda: doc)
    big = [[LON0 - 0.05, LAT0 - 0.05], [LON0 + 0.05, LAT0 - 0.05], [LON0 + 0.05, LAT0 + 0.05], [LON0 - 0.05, LAT0 + 0.05], [LON0 - 0.05, LAT0 - 0.05]]
    r = sa.classify(LAT0, LON0, big)
    assert r["outside_frame"] is False and r["state"] == "inside"


def test_a_lot_holding_part_of_the_line_is_never_outside_even_if_the_inside_grid_misses(square, monkeypatch):
    """With a one-point grid the sample lands outside the contour; the lot still contains the line, so it cannot be called outside."""
    monkeypatch.setattr(sa, "MAX_INTERIOR_SAMPLES", 1)
    (n_lat, e_lng), (s_lat, w_lng) = at(0, 0, east_m=800, north_m=3000), at(0, 0, east_m=-3000, north_m=-3000)
    ring = [[w_lng, s_lat], [e_lng, s_lat], [e_lng, n_lat], [w_lng, n_lat], [w_lng, s_lat]]
    r = sa.classify(LAT0, LON0, ring)
    assert r["state"] in ("near", "inside") and r["nearest_m"] == 0.0


def test_the_outline_is_sampled_at_five_metres_or_less_and_closed():
    ring, _, _ = _square(10.0)   # a 20 m square
    pts = sa._outline_points(LAT0, LON0, ring)
    assert len(pts) >= 16 and pts[-1] == (ring[-1][0], ring[-1][1])
    assert sa._outline_points(LAT0, LON0, None) == [(LON0, LAT0)]


def test_a_lot_that_encloses_the_whole_contour_is_inside_even_though_no_boundary_point_is(square):
    big = at(0, 0, east_m=2000, north_m=2000), at(0, 0, east_m=-2000, north_m=-2000)
    (n_lat, e_lng), (s_lat, w_lng) = big
    ring = [[w_lng, s_lat], [e_lng, s_lat], [e_lng, n_lat], [w_lng, n_lat], [w_lng, s_lat]]
    r = sa.classify(LAT0, LON0, ring)
    assert r["state"] == "inside" and r["inside_by_m"] > 400


def test_a_level_the_chart_does_not_have_is_an_error_not_a_guess(square):
    with pytest.raises(sa.SydneyAnefError):
        sa.classify(LAT0, LON0, None, level=40)


# ---- the rule --------------------------------------------------------------------------------------------------------------------------------
def lot(**over):
    base = {"lga": "Inner West", "tod_map": {"point": False, "lot": False}, "accelerated": {"point": False, "lot": False},
            "exclusion": {"point": False, "lot": False}, "bushfire": {"point": False, "lot": False},
            "heritage": {"item": False, "conservation_area": False, "state_register": False}, "sched12_straight_m": 5000.0, "straight_m": 300.0,
            "walk": {"m": 450.0, "anchor": "Ashfield station", "entrance_id": "node/1", "valid": True}}
    base.update(over)
    return base


def state(s, **kw):
    return {"25": {"state": s, "margin_m": 53.0, "inside_by_m": 300.0 if s == "inside" else None, "nearest_m": 120.0, "level": 25, **kw}}


@pytest.mark.parametrize("depth", [None, "300", True, 10.0, 53.0, float("nan"), -1.0])
def test_excluded_needs_a_depth_beyond_the_margin_or_it_is_no_answer(depth):
    """`inside` rests on how far inside the line the lot is; a missing, non-numeric or too-small depth cannot be called excluded."""
    r = d.decide(lot(sydney_anef=state("inside", inside_by_m=depth)), FACTS)
    assert r["lmr"]["answer"] == "cant_tell" and rule(r)["outcome"] == "unknown" and "inside the line" in rule(r)["detail"]


@pytest.mark.parametrize("nearest", [None, "120", True, 10.0, 53.0, float("nan"), -1.0])
def test_clear_needs_a_distance_beyond_the_margin_or_it_is_no_answer(nearest):
    """`outside` rests on the lot's distance from the line; a missing, non-numeric or too-small distance cannot be called clear."""
    r = d.decide(lot(sydney_anef=state("outside", nearest_m=nearest)), FACTS)
    assert r["lmr"]["answer"] == "cant_tell" and rule(r)["outcome"] == "unknown" and "distance" in rule(r)["detail"]


def rule(r):
    return next(x for x in r["lmr"]["rules"] if x["rule"] == "aircraft_noise_sydney")


def test_inside_the_line_excludes_with_the_clause_and_the_chart_named():
    r = d.decide(lot(sydney_anef=state("inside")), FACTS)
    x = rule(r)
    assert r["lmr"]["answer"] == "no" and x["outcome"] == "excludes" and x["clause"] == "s164(1)(h)" and x["page"] == 79
    assert "2045" in x["detail"] and "Airservices" in x["detail"] and "25" in x["detail"]


def test_clear_of_the_line_is_clear_and_the_answer_stays_yes():
    r = d.decide(lot(sydney_anef=state("outside")), FACTS)
    assert r["lmr"]["answer"] == "yes" and rule(r)["outcome"] == "clear" and "53" in rule(r)["detail"]


def test_within_the_margin_is_no_answer_with_the_reason_never_a_yes_or_no():
    r = d.decide(lot(sydney_anef=state("near")), FACTS)
    assert r["lmr"]["answer"] == "cant_tell" and rule(r)["outcome"] == "unknown"
    assert "within 53 m" in r["headline"] and r["headline"].startswith("Why:")


@pytest.mark.parametrize("bad", ["error", {}, {"20": {"state": "inside"}}, {"25": {"state": "maybe"}}, {"25": None}])
def test_an_unreadable_or_incomplete_chart_answer_is_no_answer_never_clear(bad):
    r = d.decide(lot(sydney_anef=bad), FACTS)
    assert r["lmr"]["answer"] == "cant_tell" and rule(r)["outcome"] == "unknown"


def test_a_lot_wholly_outside_the_chart_is_clear_with_the_reason():
    r = d.decide(lot(sydney_anef={"25": {"state": "outside", "margin_m": 53.0, "outside_frame": True, "level": 25}}), FACTS)
    x = rule(r)
    assert r["lmr"]["answer"] == "yes" and x["outcome"] == "clear" and "wholly outside the map" in x["detail"] and "ANEF 20" in x["detail"]


@pytest.mark.parametrize("margin", [None, "53", True, 0, -5, float("nan"), float("inf")])
def test_a_missing_or_bad_accuracy_figure_is_no_answer_not_a_crash(margin):
    for st in ("inside", "outside", "near"):
        r = d.decide(lot(sydney_anef={"25": {"state": st, "margin_m": margin, "level": 25}}), FACTS)
        assert r["lmr"]["answer"] == "cant_tell" and rule(r)["outcome"] == "unknown" and "accuracy figure" in rule(r)["detail"]


def test_not_measured_adds_no_rule():
    for m in (lot(sydney_anef=None), lot()):  # None and an absent key both mean the measurement was not taken
        r = d.decide(m, FACTS)
        assert r["lmr"]["answer"] == "yes" and not [x for x in r["lmr"]["rules"] if x["rule"] == "aircraft_noise_sydney"]


def test_the_not_checked_list_no_longer_claims_sydney_is_unheld():
    r = d.decide(lot(sydney_anef=state("outside")), FACTS)
    h = next(x for x in r["not_checked"] if x["para"] == "h")
    assert "Sydney Airport's own ANEF" not in h["what"] and "other than Sydney Airport" in h["what"]
