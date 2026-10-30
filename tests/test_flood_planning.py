"""The one answer to "is this lot on the council's flood planning map?"
(services/flood_planning.py). One test per rule, each named for the wrong
answer it prevents. Measured basis (2026-10-28, 310 saved checks): 102 moved
from a false "outside" to "not known"; 3 extreme-flood-only points stopped
counting as the planning map.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))
import flood_planning as fp  # noqa: E402


class Cur:
    """A cursor that answers each query in turn with a scripted result."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.sql = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.sql.append(sql)
        self.params = getattr(self, "params", []) + [params]
        if sql.startswith(("SET LOCAL", "SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT")):
            return
        self.current = self.answers.pop(0)

    def fetchall(self):
        return self.current

    def fetchone(self):
        return self.current[0] if self.current else None


def conn_with(*answers):
    c = MagicMock()
    c.cursor.return_value = Cur(answers)
    return c


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    monkeypatch.setitem(fp._covered_cache, "councils", None)
    monkeypatch.setitem(fp._covered_cache, "at", 0.0)


HIT_FPA = [("Flood Planning Area", "NSW_FLOOD_RISK_BALLINA", "BALLINA")]


def test_a_planning_line_hit_is_yes():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(HIT_FPA))
    assert s["value"] is True and s["council"] == "BALLINA"


def test_a_frequent_flood_hit_is_yes():
    s = fp.flood_planning_status(-34.07, 150.81, conn_with([("5.0%AEP", "CTFS", "CAMPBELLTOWN")]))
    assert s["value"] is True


def test_an_extreme_flood_only_hit_is_not_the_planning_map():
    # hits: PMF only; council; covered set; distance (none within 50 m)
    s = fp.flood_planning_status(-34.07, 150.81, conn_with(
        [("PMF", "CTFS", "CAMPBELLTOWN")], [("CAMPBELLTOWN",)], [("CAMPBELLTOWN",)], [(None,)]))
    assert s["value"] is False
    assert "extreme" in s["reason"]


def test_a_council_we_hold_no_map_for_is_unknown_never_no():
    # ... study area (no); nearest planning line (none within 200 m)
    s = fp.flood_planning_status(-29.04, 153.25, conn_with(
        [], [("RICHMOND VALLEY",)], [("BALLINA",), ("TWEED",)], [(False,)], [(None,)]))
    assert s["value"] is None
    assert s["reason"] == "we do not hold this council's flood planning map for this area"


def test_a_partial_council_map_gives_no_only_inside_its_study_area():
    """Bellingen's map covers one river study area (2026-10-29): inside it a
    clear point is 'no'; elsewhere in the council it stays 'not known'."""
    inside = fp.flood_planning_status(-30.45, 152.9, conn_with(
        [], [("BELLINGEN",)], [("BALLINA",)], [(True,)], [(None,)]))
    assert inside["value"] is False
    fp._covered_cache.update(councils=None, at=0.0)  # each call reads the covered list afresh
    outside = fp.flood_planning_status(-30.45, 152.9, conn_with(
        [], [("BELLINGEN",)], [("BALLINA",)], [(False,)], [(None,)]))
    assert outside["value"] is None and "for this area" in outside["reason"]


def test_partial_maps_never_count_a_whole_council_as_covered():
    c = conn_with([], [("BALLINA",)], [("BALLINA",)], [(None,)])
    fp.flood_planning_status(-28.86, 153.56, c)
    covered_sql = [q for q in c.cursor.return_value.sql if "DISTINCT lga_name" in q]
    assert covered_sql and "NOT LIKE 'PARTIAL" in covered_sql[0]


def test_an_unknown_council_is_unknown(monkeypatch):
    monkeypatch.setattr(fp, "requests", MagicMock(get=MagicMock(side_effect=OSError("down"))))
    s = fp.flood_planning_status(-33.0, 151.0, conn_with([], []))
    assert s["value"] is None and s["reason"] == "council could not be identified"


def test_the_spatial_services_fallback_names_the_council(monkeypatch):
    resp = MagicMock(json=lambda: {"features": [{"attributes": {"lganame": "Cumberland"}}]})
    resp.raise_for_status = lambda: None
    monkeypatch.setattr(fp, "requests", MagicMock(get=MagicMock(return_value=resp)))
    s = fp.flood_planning_status(-33.85, 150.98, conn_with([], [], [("BALLINA",)]))
    assert s["council"] == "CUMBERLAND" and s["value"] is None


def test_an_unknown_height_layer_council_uses_the_fallback(monkeypatch):
    resp = MagicMock(json=lambda: {"features": [{"attributes": {"lganame": "Ballina"}}]})
    resp.raise_for_status = lambda: None
    monkeypatch.setattr(fp, "requests", MagicMock(get=MagicMock(return_value=resp)))
    s = fp.flood_planning_status(-28.86, 153.56, conn_with([], [("UNKNOWN",)], [("TWEED",)]))
    assert s["council"] == "BALLINA"


def test_near_the_line_is_unknown_not_no():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [], [("BALLINA",)], [("BALLINA",)], [(32.4,)]))
    assert s["value"] is None and s["nearest_m"] == 32.4


def test_clear_of_the_line_in_a_held_council_is_no():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [], [("BALLINA",)], [("BALLINA",)], [(None,)]))
    assert s["value"] is False
    assert s["reason"] == "not on the council's flood planning map"


def test_coverage_and_distance_use_the_planning_line_only():
    """'Do we hold this council's map' and 'how near is the line' must ask about
    the planning line, never extreme-flood (PMF) lines, which are far wider."""
    c = conn_with([], [("BALLINA",)], [("BALLINA",)], [(None,)])
    fp.flood_planning_status(-28.86, 153.56, c)
    lists = [p for params in c.cursor.return_value.params if params
             for p in params if isinstance(p, list)]
    assert lists, "no category list was passed to the queries"
    for values in lists:
        assert "PMF" not in values and "0.2%AEP" not in values
        assert "Flood Planning Area" in values


def test_a_not_flood_row_never_makes_a_yes():
    s = fp.flood_planning_status(-32.4, 151.7, conn_with(
        [("Transitional Land", "EPI", "DUNGOG")], [("DUNGOG",)], [], ))
    assert s["value"] is not True


def test_an_unclassified_flood_value_at_the_point_is_unknown_never_no():
    """A new value (e.g. 'Flood Planning Area 2') may be a planning line."""
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [("Flood Planning Area 2", "K", "BALLINA")]))
    assert s["value"] is None and "unclassified" in s["reason"]


def test_a_database_error_is_unknown_never_no():
    c = MagicMock()
    c.cursor.side_effect = RuntimeError("db down")
    s = fp.flood_planning_status(-33.0, 151.0, c)
    assert s["value"] is None and s["reason"] == "flood planning map could not be checked"


def test_dict_rows_are_read_like_tuples():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [{"value": "Flood Planning Area", "instrument_key": "K", "lga_name": "BALLINA"}]))
    assert s["value"] is True


@pytest.mark.database
@pytest.mark.skipif(os.environ.get("PYTEST_REAL_DB") != "1", reason="needs PYTEST_REAL_DB=1 and DATABASE_URL")
def test_every_stored_flood_value_is_classified():
    """A new value in the flood layer must be sorted before it can mislead."""
    import psycopg2
    with psycopg2.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
        cur.execute("SELECT DISTINCT value FROM spatial_overlays WHERE layer_type = 'flood'")
        unclassified = [v for (v,) in cur.fetchall() if fp.category_of(v) == "unclassified"]
    assert unclassified == []


def test_the_endpoint_returns_the_producer_answer(monkeypatch):
    import services.flood_truth as ft
    monkeypatch.setattr(fp, "flood_planning_status", lambda lat, lng, conn, **kw: {
        "value": None, "reason": "we do not hold this council's flood planning map",
        "council": "NEWCASTLE", "category": None, "nearest_m": None, "hits": [1]})
    monkeypatch.setattr(ft, "_flood_conn", lambda fresh=False: MagicMock())
    out = ft.flood_planning(ft.FloodPlanningRequest(lat=-32.93, lng=151.78))
    assert out == {"value": None, "reason": "we do not hold this council's flood planning map",
                   "council": "NEWCASTLE", "category": None, "nearest_m": None, "whole_lot": None,
                   "council_info_text": None}


def test_the_endpoint_never_raises(monkeypatch):
    import services.flood_truth as ft
    monkeypatch.setattr(ft, "_flood_conn", lambda fresh=False: (_ for _ in ()).throw(RuntimeError("down")))
    out = ft.flood_planning(ft.FloodPlanningRequest(lat=-32.93, lng=151.78))
    assert out["value"] is None


LOT = "POLYGON((153.5 -28.9,153.6 -28.9,153.6 -28.8,153.5 -28.8,153.5 -28.9))"


def test_whole_lot_clear_in_a_held_council_is_a_real_no():
    # trusted-lot check; hits (none on lot or point); council; covered
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [], [("BALLINA",)], [("BALLINA",)]), lot_wkt=LOT)
    assert s["value"] is False and s["whole_lot"] is True
    assert s["reason"].startswith("no part of the lot")


def test_a_hit_anywhere_on_the_lot_is_yes():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [("Flood Planning Area", "K", "BALLINA")]), lot_wkt=LOT)
    assert s["value"] is True


def test_an_untrusted_lot_outline_falls_back_to_the_point_rule():
    """A stale or neighbouring outline is ignored, never used for a 'no'."""
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(False,)], [], [("BALLINA",)], [("BALLINA",)], [(120.0,)]), lot_wkt=LOT)
    assert s["whole_lot"] is False
    assert s["value"] is None and s["nearest_m"] == 120.0


def test_council_info_sentence_uses_only_what_is_held():
    s = fp.council_info_sentence({"certificate_label": "Flood Certificates (City of Newcastle)",
                                  "certificate_url": "https://www.ncc.nsw.gov.au/x", "data_sources": []})
    assert s.startswith("For this council, the council issues Flood Certificates")
    assert "https://www.ncc.nsw.gov.au/x" in s
    assert fp.council_info_sentence(None) is None
    assert fp.council_info_sentence({"data_sources": []}) is None


def test_council_info_falls_back_to_the_flood_study_link():
    s = fp.council_info_sentence({"data_sources": [{"url": "https://flooddata.ses.nsw.gov.au/dataset/x"}]})
    assert "flood studies are listed at https://flooddata.ses.nsw.gov.au/dataset/x" in s


def test_the_answer_carries_council_info(monkeypatch):
    monkeypatch.setattr(fp, "_council_info", lambda conn, council: {
        "certificate_label": "Flood Certificates", "certificate_url": "https://u", "data_sources": []})
    s = fp.flood_planning_status(-32.93, 151.78, conn_with(
        [], [("NEWCASTLE",)], [("BALLINA",)], [(False,)]))
    assert s["value"] is None and s["council_info_text"].startswith("For this council")


# -- Heddon Greta, 2026-10-28: 44.7 m2 of the lot on Cessnock's PARTIAL 1% AEP
# map, the address point 6 m off it. Every surface sent the point only.

def test_a_point_beside_a_partial_council_line_says_near_never_not_held():
    """Point only, outside the study area, a planning line 5.9 m away: 'near',
    not 'we do not hold this council's map' (we hold it right there)."""
    s = fp.flood_planning_status(-32.80, 151.51, conn_with(
        [], [("CESSNOCK",)], [("BALLINA",)], [(False,)], [(5.9,)]))
    assert s["value"] is None and s["nearest_m"] == 5.9
    assert "whole lot was not checked" in s["reason"]


def test_the_lot_on_a_partial_council_line_is_yes():
    s = fp.flood_planning_status(-32.80, 151.51, conn_with(
        [(True,)], [("1%AEP", "PARTIAL_CESSNOCK_1PCT_1pctAEP", "CESSNOCK")]), lot_wkt=LOT)
    assert s["value"] is True and s["whole_lot"] is True


def test_a_whole_lot_clear_outside_a_partial_study_area_stays_not_known():
    """The lot was tested and touches nothing, but the council map covers only
    its study areas: still not known, never 'no', and no distance query."""
    c = conn_with([(True,)], [], [("CESSNOCK",)], [("BALLINA",)], [(False,)])
    s = fp.flood_planning_status(-32.80, 151.51, c, lot_wkt=LOT)
    assert s["value"] is None and "for this area" in s["reason"]


def test_the_flood_check_hands_the_lot_to_the_one_answer(monkeypatch):
    """/pipeline/flood used to call the one answer with the point only."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import services.flood_truth as ft
    seen = {}

    def fake(lat, lng, conn, lot_wkt=None):
        seen["lot_wkt"] = lot_wkt
        return {"value": True, "hits": [], "council": "CESSNOCK"}

    monkeypatch.setattr(fp, "flood_planning_status", fake)
    monkeypatch.setattr(ft, "_get_conn", lambda: MagicMock())
    ft._query_ses_flood_study(-32.80, 151.51, LOT)
    assert seen["lot_wkt"] == LOT


def test_partial_council_near_check_counts_only_that_councils_lines():
    c = conn_with([], [("CESSNOCK",)], [("BALLINA",)], [(False,)], [(5.9,)])
    fp.flood_planning_status(-32.80, 151.51, c)
    cur = c.cursor.return_value
    i = next(n for n, q in enumerate(cur.sql) if "ST_Distance" in q)
    assert "lga_name = %s" in cur.sql[i] and cur.params[i][-2:] == ("CESSNOCK", "CESSNOCK")


def test_a_lot_that_only_touches_the_line_is_not_yes():
    """A shared edge or a sliver under 1 m2 is not 'on the map' -- and not a clean no."""
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [("Flood Planning Area", "K", "BALLINA", 0.3)]), lot_wkt=LOT)
    assert s["value"] is None and s["nearest_m"] == 0.0
    assert s["reason"].startswith("only the edge of the lot")


def test_a_real_part_of_the_lot_on_the_line_is_yes():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [("Flood Planning Area", "K", "BALLINA", 44.7)]), lot_wkt=LOT)
    assert s["value"] is True


def test_the_address_point_on_the_line_is_yes_whatever_the_lot_overlap():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [("Flood Planning Area", "K", "BALLINA", None)]), lot_wkt=LOT)
    assert s["value"] is True


def test_an_edge_touch_of_an_extreme_line_alone_still_gives_the_real_no():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [("PMF", "K", "BALLINA", 0.0)], [("BALLINA",)], [("BALLINA",)]), lot_wkt=LOT)
    assert s["value"] is False


def test_an_edge_touch_with_a_larger_extreme_overlap_is_not_a_clean_no():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [("PMF", "K", "BALLINA", 5.0), ("Flood Planning Area", "K", "BALLINA", 0.3)]), lot_wkt=LOT)
    assert s["value"] is None and s["reason"].startswith("only the edge of the lot")


def test_dict_rows_read_the_lot_overlap_by_name():
    s = fp.flood_planning_status(-28.86, 153.56, conn_with(
        [(True,)], [{"value": "Flood Planning Area", "instrument_key": "K", "lga_name": "BALLINA", "lot_m2": 0.3}]),
        lot_wkt=LOT)
    assert s["value"] is None and s["council"] == "BALLINA"


def test_the_hit_query_names_the_overlap_and_unions_the_pieces():
    c = conn_with([(True,)], [("Flood Planning Area", "K", "BALLINA", 3.0)])
    fp.flood_planning_status(-28.86, 153.56, c, lot_wkt=LOT)
    sql = " ".join(c.cursor.return_value.sql)
    assert "AS lot_m2" in sql and "ST_UnaryUnion(ST_Collect" in sql


def test_a_dropped_pooled_connection_is_retried_on_a_fresh_one(monkeypatch):
    """A pooled connection the pooler closed while idle gives 'could not be checked';
    the endpoint retries once on a fresh connection and discards the dead one."""
    import services.flood_truth as ft
    got, returned = [], []
    monkeypatch.setattr(ft, "_flood_conn", lambda fresh=False: got.append(fresh) or ("fresh" if fresh else "pooled"))
    monkeypatch.setattr(ft, "_flood_conn_return", lambda conn, discard=False: returned.append((conn, discard)))
    answers = {"pooled": {"value": None, "reason": "flood planning map could not be checked"},
               "fresh": {"value": True, "reason": "on the council's flood planning map"}}
    monkeypatch.setattr(fp, "flood_planning_status", lambda lat, lng, conn, **kw: answers[conn])
    out = ft.flood_planning(ft.FloodPlanningRequest(lat=-32.93, lng=151.78))
    assert out["value"] is True and got == [False, True]
    assert returned == [("pooled", True), ("fresh", False)]


def test_a_good_pooled_answer_uses_one_connection_and_keeps_it(monkeypatch):
    import services.flood_truth as ft
    got, returned = [], []
    monkeypatch.setattr(ft, "_flood_conn", lambda fresh=False: got.append(fresh) or "pooled")
    monkeypatch.setattr(ft, "_flood_conn_return", lambda conn, discard=False: returned.append((conn, discard)))
    monkeypatch.setattr(fp, "flood_planning_status", lambda lat, lng, conn, **kw: {"value": False, "reason": "x"})
    assert ft.flood_planning(ft.FloodPlanningRequest(lat=-32.93, lng=151.78))["value"] is False
    assert got == [False] and returned == [("pooled", False)]


def test_the_near_edge_check_adds_no_extra_timeout_trip():
    c = conn_with([(150.0,)])
    with c.cursor() as cur:
        fp._nearest_yes_m(cur, -33.0, 151.0)
    assert not any(q.startswith("SET LOCAL") for q in c.cursor.return_value.sql)
