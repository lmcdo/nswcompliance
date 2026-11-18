"""The council-name fallback (services/lmr_area_lga.py) and how the area check uses it.

Properties pinned: the live service is asked first and its answer (even "no council") is never overridden; the fallback is used only when the live
service gives NO answer; a fallback that is unsure (border, nothing near, error) gives no council, so the decision stays "can't tell"; a lot that
contains the point decides; and an answer that used the fallback says so in plain words.
"""
import datetime as dt

import pytest
import requests

from services import lmr_area_decision as d
from services import lmr_area_inputs as inp
from services import lmr_area_lga as lga

FACTS = d.LawFacts.load()
CLEAR = {"point": False, "lot": False}
SNAP = {"source": "snapshot", "as_of": "2026-06-18"}
NO_ANSWER = (False, None)          # the live service stalled or errored
ANSWERED_NONE = (True, None)       # the live service answered and names no council


def lot(**over):
    """A lot that is clear on every rule and 450 m from a station (same shape as tests/test_lmr_area_decision.py)."""
    base = {
        "lga": "Inner West", "tod_map": CLEAR, "accelerated": CLEAR, "exclusion": CLEAR, "bushfire": CLEAR,
        "heritage": {"item": False, "conservation_area": False, "state_register": False},
        "sched12_straight_m": 5000.0, "straight_m": 300.0,
        "walk": {"m": 450.0, "anchor": "Ashfield station", "entrance_id": "node/1", "valid": True},
    }
    base.update(over)
    return base


# ---- _lga_resolved: live first, fallback only when live gives no answer -------------------------------------------------------------

def test_our_own_copy_answers_first_and_the_live_service_is_not_even_asked(monkeypatch):
    def boom(lat, lng):
        raise AssertionError("live service asked although our copy was sure")

    monkeypatch.setattr(inp, "_lga_live", boom)
    assert inp._lga_resolved(-33.75, 150.7, lambda *a: ("PENRITH", "2026-06-18", "the lot at this point")) == (
        "PENRITH", {**SNAP, "how": "the lot at this point"})


def test_when_our_copy_is_unsure_the_live_answer_is_used_and_a_live_no_council_is_never_overridden(monkeypatch):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: (True, "PENRITH"))
    assert inp._lga_resolved(-33.75, 150.7, lambda *a: None, lambda *a: {"council": "HORNSBY", "as_of": "x", "alternatives": []}) == ("PENRITH", None)
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: ANSWERED_NONE)
    assert inp._lga_resolved(-33.75, 150.7, lambda *a: None, lambda *a: {"council": "HORNSBY", "as_of": "x", "alternatives": []}) == (None, None)


def test_when_both_are_unsure_or_silent_our_best_guess_is_given_and_marked_unsure(monkeypatch):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: NO_ANSWER)
    name, src = inp._lga_resolved(-33.75, 150.7, lambda *a: None, lambda *a: {"council": " PENRITH ", "as_of": "2026-06-18", "alternatives": ["BLUE MOUNTAINS"]})
    assert name == "PENRITH" and src == {**SNAP, "unsure": True, "alternatives": ["BLUE MOUNTAINS"]}
    assert inp._lga_resolved(-33.75, 150.7, lambda *a: None, lambda *a: None) == (None, None)
    assert inp._lga_resolved(-33.75, 150.7, None, None) == (None, None)


def test_the_unsure_note_gives_the_reason_the_best_answer_and_the_other_possibility():
    src = {**SNAP, "unsure": True, "alternatives": ["BLUE MOUNTAINS"]}
    r = d.decide(lot(lga="PENRITH", lga_source=src), FACTS)
    n = next(x for x in r["notes"] if "could not be sure" in x)
    assert "border" in n and "best answer is PENRITH" in n and "BLUE MOUNTAINS" in n and "as at 2026-06-18" in n
    assert r["lmr"]["answer"] == "yes"       # an answer is given, not can't tell


def test_fallback_is_used_when_live_gives_no_answer_and_the_source_says_so(monkeypatch):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: NO_ANSWER)
    assert inp._lga_resolved(-33.75, 150.7, lambda *a: (" PENRITH ", "2026-06-18")) == ("PENRITH", SNAP)


@pytest.mark.parametrize("fallback", [
    None,                                         # no fallback supplied
    lambda *a: None,                              # fallback unsure
    lambda *a: (None, "2026-06-18"),              # no name
    lambda *a: ("", "2026-06-18"),                # empty name
    lambda *a: "PENRITH",                         # wrong shape
])
def test_no_usable_fallback_leaves_no_council(monkeypatch, fallback):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: NO_ANSWER)
    assert inp._lga_resolved(-33.75, 150.7, fallback) == (None, None)


def test_a_fallback_that_raises_is_no_answer_not_a_crash(monkeypatch):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: NO_ANSWER)

    def boom(*a):
        raise RuntimeError("db down")

    assert inp._lga_resolved(-33.75, 150.7, boom) == (None, None)


# ---- the live lookup tells "no answer" from "answered, no council" -----------------------------------------------------------------

def _live_returns(monkeypatch, payload):
    monkeypatch.setattr(inp, "_get_json", lambda url, params, post=False, **kw: payload)


def test_live_lookup_distinguishes_no_answer_from_an_empty_answer(monkeypatch):
    _live_returns(monkeypatch, None)
    assert inp._lga_live(-33.75, 150.7) == (False, None)
    _live_returns(monkeypatch, {"features": []})
    assert inp._lga_live(-33.75, 150.7) == (True, None)
    _live_returns(monkeypatch, {"features": [{"attributes": {"lganame": "  "}}]})
    assert inp._lga_live(-33.75, 150.7) == (True, None)
    _live_returns(monkeypatch, {"features": [{"attributes": {"lganame": " PENRITH "}}]})
    assert inp._lga_live(-33.75, 150.7) == (True, "PENRITH")


# ---- fetch_layers carries the source ----------------------------------------------------------------------------------------------

@pytest.fixture
def quiet_layers(monkeypatch):
    monkeypatch.setattr(inp, "_layer", lambda *a: {"point": False, "lot": False})
    monkeypatch.setattr(inp, "_heritage", lambda rings: {"item": False, "conservation_area": False, "state_register": False})
    monkeypatch.setattr(inp, "_noise_bands", lambda *a: None)


def test_fetch_layers_records_the_snapshot_source_only_when_it_was_used(monkeypatch, quiet_layers):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: (True, "HORNSBY"))
    out = inp.fetch_layers(-33.75, 150.7, None, lambda *a: ("PENRITH", "2026-06-18"))
    assert out["lga"] == "PENRITH" and out["lga_source"] == SNAP
    out = inp.fetch_layers(-33.75, 150.7, None, lambda *a: None)
    assert out["lga"] == "HORNSBY" and "lga_source" not in out


def test_fetch_layers_without_a_fallback_is_unchanged(monkeypatch, quiet_layers):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: NO_ANSWER)
    out = inp.fetch_layers(-33.75, 150.7, None)
    assert out["lga"] is None and "lga_source" not in out


# ---- the decision ------------------------------------------------------------------------------------------------------------------

def test_an_answer_that_used_the_snapshot_says_so_and_is_not_cant_tell():
    r = d.decide(lot(lga="PENRITH", lga_source=SNAP), FACTS)
    assert r["lmr"]["answer"] == "yes"
    assert any("our own copy of the lot boundaries as at 2026-06-18" in n and "PENRITH" in n for n in r["notes"])
    assert not any("in time" in n for n in r["notes"])           # an error is not always a timeout, so the note never says so
    assert r["measured"]["lga_source"] == SNAP


def test_the_source_and_the_note_say_which_part_of_the_copy_decided(monkeypatch):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: NO_ANSWER)
    name, src = inp._lga_resolved(-33.75, 150.7, lambda *a: ("PENRITH", "2026-06-18", "the lots around this point"))
    assert name == "PENRITH" and src == {**SNAP, "how": "the lots around this point"}
    r = d.decide(lot(lga=name, lga_source=src), FACTS)
    assert any("(taken from the lots around this point)" in n for n in r["notes"])


def test_area_check_hands_the_fallback_down_to_the_layer_fetch(monkeypatch):
    seen = {}
    monkeypatch.setattr(inp, "fetch_lot_rings", lambda lat, lng: None)
    monkeypatch.setattr(inp, "fetch_layers", lambda lat, lng, rings, lga_fallback=None, lga_guess=None, bushfire_fn=None: seen.update(fb=lga_fallback, g=lga_guess, bf=bushfire_fn) or lot())
    marker = lambda *a: ("PENRITH", "2026-06-18")  # noqa: E731
    g = lambda *a: None  # noqa: E731
    bf = lambda *a: None  # noqa: E731
    inp.area_check(-33.75, 150.7, lga_fallback=marker, lga_guess=g, bushfire_fn=bf)
    assert seen["fb"] is marker and seen["g"] is g and seen["bf"] is bf


def test_the_api_route_passes_the_snapshot_lookup_as_the_fallback(monkeypatch):
    from services import housing_sepp_gates_api as api

    seen = {}
    monkeypatch.setattr(inp, "area_check", lambda lat, lng, **kw: seen.update(kw) or {"ok": True})
    assert api.housing_sepp_area_check(-33.75, 150.7) == {"ok": True}
    assert seen["lga_fallback"] is lga.lga_from_snapshot and seen["lga_guess"] is lga.lga_best_guess and seen["bushfire_fn"] is lga.bushfire_from_snapshot and seen["lot_fn"] is lga.lot_outline_from_snapshot and "flood_fn" in seen


def test_a_normal_live_answer_adds_no_source_field_anywhere(monkeypatch):
    r = d.decide(lot(lga="PENRITH"), FACTS)
    assert "lga_source" not in r["measured"]
    monkeypatch.setattr(inp, "gather", lambda lat, lng, **kw: lot(lga="PENRITH"))
    assert "lga_source" not in inp.area_check(-33.75, 150.7)["measured"]


def test_no_note_when_the_live_service_answered():
    r = d.decide(lot(lga="PENRITH"), FACTS)
    assert not any("own copy of the lot boundaries" in n for n in r["notes"])


def test_both_failing_is_still_cant_tell_never_yes():
    r = d.decide(lot(lga=None), FACTS)
    assert r["lmr"]["answer"] == "cant_tell"


@pytest.mark.parametrize("name", ["BATHURST REGIONAL", "BLUE MOUNTAINS", "HAWKESBURY", "WOLLONDILLY"])
def test_the_four_excluded_councils_are_still_excluded_when_the_name_came_from_the_snapshot(name):
    r = d.decide(lot(lga=name, lga_source=SNAP), FACTS)
    assert r["lmr"]["answer"] == "no"


# ---- the live call fails fast ------------------------------------------------------------------------------------------------------

class _Timeout:
    def __init__(self):
        self.calls = []

    def post(self, url, data=None, headers=None, timeout=None):
        self.calls.append(timeout)
        raise requests.exceptions.ReadTimeout("stalled")

    get = post


def test_get_json_defaults_are_unchanged_and_the_limits_can_be_shortened(monkeypatch):
    fake = _Timeout()
    monkeypatch.setattr(inp.requests, "post", fake.post)
    monkeypatch.setattr(inp.time, "sleep", lambda s: None)
    assert inp._get_json("http://x", {}, post=True) is None
    assert fake.calls == [inp.TIMEOUT_S, inp.TIMEOUT_S]
    fake.calls.clear()
    assert inp._get_json("http://x", {}, post=True, timeout=5, attempts=1) is None
    assert fake.calls == [5]


def test_the_council_lookup_uses_one_short_try(monkeypatch):
    fake = _Timeout()
    monkeypatch.setattr(inp.requests, "post", fake.post)
    monkeypatch.setattr(inp.time, "sleep", lambda s: None)
    assert inp._lga_live(-33.75, 150.7) == (False, None)
    assert fake.calls == [inp.LGA_LIVE_TIMEOUT_S] and inp.LGA_LIVE_TIMEOUT_S < inp.TIMEOUT_S


# ---- lga_from_snapshot: only answers when sure --------------------------------------------------------------------------------------

class _Cur:
    def __init__(self, rows=None, boom=False):
        self.rows, self.boom, self.args = rows or [], boom, None

    def execute(self, sql, args=None):
        if self.boom:
            raise RuntimeError("statement timeout")
        self.sql, self.args = sql, args

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, cur):
        self.cur, self.closed = cur, False

    def cursor(self):
        return self.cur

    def close(self):
        self.closed = True


def _lookup(rows=None, boom=False):
    conn = _Conn(_Cur(rows, boom))
    return lga.lga_from_snapshot(-33.75, 150.7, connect=lambda: conn), conn


T = dt.datetime(2026, 6, 18, 3, 0, tzinfo=dt.timezone.utc)


def test_a_lot_containing_the_point_decides_with_its_date_and_the_connection_is_closed():
    got, conn = _lookup([(" PENRITH ", True, T)])
    assert got == ("PENRITH", "2026-06-18", "the lot at this point") and conn.closed
    assert conn.cur.args == (150.7, -33.75, 150.7, -33.75, lga.NEAR_DEG)   # longitude then latitude, twice, then the distance


def test_the_lot_the_point_is_in_decides_even_when_another_council_is_close():
    got, _ = _lookup([("PENRITH", True, T), ("BLUE MOUNTAINS", False, T)])
    assert got == ("PENRITH", "2026-06-18", "the lot at this point")


def test_on_a_road_with_one_council_all_round_that_council_is_returned():
    assert _lookup([("HAWKESBURY", False, T)])[0] == ("HAWKESBURY", "2026-06-18", "the lots around this point")


def test_on_a_road_between_two_councils_gives_no_answer():
    got, conn = _lookup([("PENRITH", False, T), ("BLUE MOUNTAINS", False, T)])
    assert got is None and conn.closed


def test_an_excluded_council_is_never_lost_to_a_neighbour_across_a_wide_road():
    """The point is in an excluded council's road reserve; a neighbour's lots are near but so are the excluded council's: no guess."""
    assert _lookup([("PENRITH", False, T), ("BLUE MOUNTAINS", False, T), ("BLUE MOUNTAINS", False, T)])[0] is None


def test_two_lots_of_different_councils_containing_one_point_is_not_trusted():
    assert _lookup([("PENRITH", True, T), ("BLUE MOUNTAINS", True, T)])[0] is None


def test_no_lot_nearby_gives_no_answer():
    assert _lookup([])[0] is None


def test_blank_names_are_never_skipped_over():
    assert _lookup([("", True, T), (None, True, T)])[0] is None


def test_a_containing_lot_with_no_council_name_is_not_replaced_by_a_neighbour():
    """The review's case: the lot the point is in has no council name and a neighbour's lot is near: say nothing, never the neighbour."""
    assert _lookup([(None, True, T), ("PENRITH", False, T)])[0] is None
    assert _lookup([("", True, T), ("PENRITH", False, T)])[0] is None


def test_a_nearby_lot_with_no_council_name_makes_a_road_answer_unsure():
    assert _lookup([("PENRITH", False, T), (None, False, T)])[0] is None


def test_a_database_error_gives_no_answer_and_still_closes():
    got, conn = _lookup(boom=True)
    assert got is None and conn.closed


def test_no_connection_available_gives_no_answer():
    assert lga.lga_from_snapshot(-33.75, 150.7, connect=lambda: None) is None


def test_a_connection_that_raises_gives_no_answer():
    def bad():
        raise OSError("refused")

    assert lga.lga_from_snapshot(-33.75, 150.7, connect=bad) is None


def test_without_a_database_setting_the_default_connection_gives_no_answer(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert lga.lga_from_snapshot(-33.75, 150.7) is None


def test_the_query_is_read_only_spatial_and_limited_to_a_short_distance():
    sql = lga._SQL
    assert sql.lstrip().upper().startswith("SELECT") and "ST_DWithin" in sql and "ST_Intersects" in sql and "4326" in sql
    assert "lot_search_index" in sql
    assert lga.NEAR_DEG <= 0.0015 and lga.CONNECT_TIMEOUT_S <= 5 and lga.STATEMENT_TIMEOUT_MS <= 5000



def _guess(rows=None, boom=False):
    conn = _Conn(_Cur(rows, boom))
    return lga.lga_best_guess(-33.75, 150.7, connect=lambda: conn), conn


def test_best_guess_prefers_the_containing_lot_then_the_nearest_and_lists_the_others():
    got, conn = _guess([("BLUE MOUNTAINS", False, 0.0002, T), ("PENRITH", True, 0.0, T)])
    assert got == {"council": "PENRITH", "as_of": "2026-06-18", "alternatives": ["BLUE MOUNTAINS"]} and conn.closed
    got, _ = _guess([("A", False, 0.0008, T), ("B", False, 0.0003, T)])
    assert got["council"] == "B" and got["alternatives"] == ["A"]


def test_best_guess_says_nothing_when_nothing_is_near_or_on_error():
    assert _guess([])[0] is None
    got, conn = _guess(boom=True)
    assert got is None and conn.closed
    assert lga.lga_best_guess(-33.75, 150.7, connect=lambda: None) is None


def test_the_unsure_note_does_not_invent_another_council_when_none_was_found():
    r = d.decide(lot(lga="PENRITH", lga_source={**SNAP, "unsure": True, "alternatives": []}), FACTS)
    n = next(x for x in r["notes"] if "could not be sure" in x)
    assert "no other council was found nearby" in n and "could also be" not in n



# ---- bush fire prone land: our copy first, the live map confirms --------------------------------------------------------------------

RING = [[150.0, -33.0], [150.001, -33.0], [150.001, -33.001], [150.0, -33.001], [150.0, -33.0]]
OWN_HIT = {"point": True, "lot": True, "as_of": "2026-11-18"}
OWN_CLEAR = {"point": False, "lot": False, "as_of": "2026-11-18"}
LIVE_CLEAR = {"point": False, "lot": False}
LIVE_SILENT = {"point": None, "lot": None}
BF_SRC = {"source": "snapshot", "as_of": "2026-11-18", "confirmed": False}


def _live(monkeypatch, result):
    calls = []
    monkeypatch.setattr(inp, "_layer", lambda key, lat, lng, rings, **kw: calls.append((key, kw)) or result)
    return calls


def test_a_hit_in_our_copy_is_final_and_the_live_map_is_not_asked(monkeypatch):
    calls = _live(monkeypatch, LIVE_CLEAR)
    got = inp._bushfire_resolved(-33.7, 150.7, RING, lambda *a: OWN_HIT)
    assert got == ({"point": True, "lot": True}, {**BF_SRC, "found": "hit"}) and calls == []


def test_a_clear_in_our_copy_is_checked_live_with_a_short_limit_and_live_wins(monkeypatch):
    calls = _live(monkeypatch, {"point": True, "lot": True})
    got = inp._bushfire_resolved(-33.7, 150.7, RING, lambda *a: OWN_CLEAR)
    assert got == ({"point": True, "lot": True}, None)          # our copy lacked an area the live map has: live wins
    assert calls == [("bushfire", {"timeout": inp.BUSHFIRE_LIVE_CHECK_TIMEOUT_S, "attempts": 1})]


def test_when_live_is_silent_our_clear_is_never_an_answer_it_stays_unknown(monkeypatch):
    _live(monkeypatch, LIVE_SILENT)
    result, src = inp._bushfire_resolved(-33.7, 150.7, RING, lambda *a: OWN_CLEAR)
    assert result == LIVE_SILENT and src == {**BF_SRC, "found": "clear_unconfirmed"}
    assert d.layer_state(result) == "unknown"          # the decision sees unknown, never clear


def test_a_half_answered_live_map_counts_as_silent(monkeypatch):
    _live(monkeypatch, {"point": False, "lot": None})
    result, src = inp._bushfire_resolved(-33.7, 150.7, RING, lambda *a: OWN_CLEAR)
    assert src == {**BF_SRC, "found": "clear_unconfirmed"} and result == {"point": False, "lot": None}


@pytest.mark.parametrize("own", [None, lambda *a: None, lambda *a: {"point": "yes", "as_of": "x"}, lambda *a: {"point": False}])
def test_without_a_usable_copy_the_live_map_alone_decides_as_before(monkeypatch, own):
    calls = _live(monkeypatch, LIVE_SILENT)
    assert inp._bushfire_resolved(-33.7, 150.7, RING, own) == (LIVE_SILENT, None)
    assert calls == [("bushfire", {})]                       # the old limits: no shortened wait when there is no copy to fall back on


def test_a_failing_copy_lookup_falls_back_to_live(monkeypatch):
    _live(monkeypatch, LIVE_CLEAR)

    def boom(*a):
        raise RuntimeError("db")

    assert inp._bushfire_resolved(-33.7, 150.7, RING, boom) == (LIVE_CLEAR, None)


def test_the_unconfirmed_note_says_so_and_the_answer_is_not_clear():
    r = d.decide(lot(bushfire={"point": None, "lot": None}, bushfire_source={**BF_SRC, "found": "clear_unconfirmed"}), FACTS)
    n = next(x for x in r["notes"] if "bush fire prone land map did not answer" in x)
    assert "2026-11-18" in n and "NOT treated as clear" in n and "Planning Portal" in n
    assert r["lmr"]["answer"] == "cant_tell"
    r = d.decide(lot(bushfire={"point": True, "lot": True}, bushfire_source={**BF_SRC, "found": "hit"}), FACTS)
    r = d.decide(lot(bushfire={"point": True, "lot": True}, bushfire_source={**BF_SRC, "found": "hit"}), FACTS)
    assert any("found in our own copy" in x and "live state map was not needed" in x for x in r["notes"]) and r["lmr"]["answer"] == "no"
    assert not any("bush fire" in x.lower() for x in d.decide(lot(), FACTS)["notes"])


def test_fetch_layers_keeps_the_bushfire_source_only_when_the_copy_was_used(monkeypatch, quiet_layers):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: (True, "PENRITH"))
    out = inp.fetch_layers(-33.7, 150.7, RING, None, None, lambda *a: OWN_HIT)
    assert out["bushfire"] == {"point": True, "lot": True} and out["bushfire_source"]["found"] == "hit"
    out = inp.fetch_layers(-33.7, 150.7, RING, None, None, None)
    assert "bushfire_source" not in out


# ---- bushfire_from_snapshot --------------------------------------------------------------------------------------------------------

class _CurBF:
    def __init__(self, answers, boom=False):
        self.answers, self.boom, self.sqls = list(answers), boom, []

    def execute(self, sql, args=None):
        if self.boom:
            raise RuntimeError("statement timeout")
        self.sqls.append((sql, args))

    def fetchone(self):
        return (self.answers.pop(0),)


def _bf(answers, rings=RING, boom=False, info=True, monkeypatch=None):
    conn = _Conn(_CurBF(answers, boom))
    return lga.bushfire_from_snapshot(-33.0005, 150.0005, rings, connect=lambda: conn), conn


def test_the_copy_answers_point_and_lot_with_the_refresh_date_and_closes():
    got, conn = _bf([False, True])
    assert got == {"point": False, "lot": True, "as_of": "2026-11-18"} and conn.closed
    assert conn.cur.sqls[0][1] == (150.0005, -33.0005) and conn.cur.sqls[1][1][0].startswith("POLYGON((150.0 -33.0")


def test_without_a_lot_outline_only_the_point_is_asked_and_lot_is_none():
    got, conn = _bf([True], rings=None)
    assert got == {"point": True, "lot": None, "as_of": "2026-11-18"} and len(conn.cur.sqls) == 1


def test_an_error_or_no_connection_or_no_record_of_the_copy_date_gives_none(monkeypatch):
    assert _bf([], boom=True)[0] is None
    assert lga.bushfire_from_snapshot(-33.0, 150.0, RING, connect=lambda: None) is None
    monkeypatch.setattr(lga, "_BUSHFIRE_COPY", lga._BUSHFIRE_COPY.parent / "does_not_exist.json")
    assert _bf([False, False])[0] is None


def test_the_committed_copy_record_names_the_date_and_what_the_copy_lacks():
    info = lga.bushfire_copy_info()
    assert info["refreshed_on"] >= "2026-11-18" and info["areas_missing_from_our_copy"] >= 0 and info["areas_in_our_copy_gone_from_live"] >= 0


def test_the_bushfire_queries_are_read_only_exists_checks_on_the_bushfire_layer():
    for q in (lga._SQL_BF_POINT, lga._SQL_BF_LOT):
        assert q.upper().startswith("SELECT EXISTS") and "layer_type = 'bushfire'" in q and "ST_Intersects" in q


# ---- the lot outline from our own copy ---------------------------------------------------------------------------------------------

import json as _json

RING = [[150.0, -33.0], [150.001, -33.0], [150.001, -33.001], [150.0, -33.001], [150.0, -33.0]]


def _lot(rows=None, boom=False):
    conn = _Conn(_Cur(rows, boom))
    return lga.lot_outline_from_snapshot(-33.0005, 150.0005, connect=lambda: conn), conn


def test_the_lot_outline_comes_from_our_copy_with_its_date():
    got, conn = _lot([(_json.dumps({"type": "Polygon", "coordinates": [RING]}), T)])
    assert got == (RING, "2026-06-18") and conn.closed


@pytest.mark.parametrize("rows", [[], [(_json.dumps({"type": "Point", "coordinates": [1, 2]}), T)],
                                  [(_json.dumps({"type": "Polygon", "coordinates": [RING[:3]]}), T)]])
def test_no_lot_or_a_bad_shape_gives_no_outline(rows):
    assert _lot(rows)[0] is None


def test_an_outline_lookup_error_gives_none_and_closes():
    got, conn = _lot(boom=True)
    assert got is None and conn.closed


def test_gather_uses_our_outline_first_and_skips_the_live_property_service(monkeypatch):
    monkeypatch.setattr(inp, "fetch_lot_rings", lambda *a: (_ for _ in ()).throw(AssertionError("live property service asked")))
    monkeypatch.setattr(inp, "fetch_layers", lambda *a, **k: {"lga": "PENRITH"})
    monkeypatch.setattr(inp, "load_stations", lambda: None)
    m = inp.gather(-33.0005, 150.0005, lot_fn=lambda la, lo: (RING, "2026-06-18"))
    assert m["lot_outline"] is True and m["lot_source"] == {"source": "snapshot", "as_of": "2026-06-18"}


def test_gather_falls_back_to_the_live_service_when_our_copy_has_no_outline(monkeypatch):
    monkeypatch.setattr(inp, "fetch_lot_rings", lambda *a: RING)
    monkeypatch.setattr(inp, "fetch_layers", lambda *a, **k: {"lga": "PENRITH"})
    monkeypatch.setattr(inp, "load_stations", lambda: None)
    m = inp.gather(-33.0005, 150.0005, lot_fn=lambda la, lo: None)
    assert m["lot_outline"] is True and "lot_source" not in m


def test_the_note_says_when_the_outline_came_from_our_copy():
    r = d.decide(lot(lot_source={"source": "snapshot", "as_of": "2026-06-18"}), FACTS)
    assert any("lot outline was read from our own copy" in n and "2026-06-18" in n for n in r["notes"])
    assert not any("lot outline was read" in n for n in d.decide(lot(), FACTS)["notes"])


def test_the_outline_query_needs_the_point_strictly_inside_the_lot_and_the_note_never_says_as_at_none():
    assert "ST_Contains((d).geom" in lga._SQL_LOT and "ST_Intersects((d).geom" not in lga._SQL_LOT
    r = d.decide(lot(lot_source={"source": "snapshot", "as_of": None}), FACTS)
    n = next(x for x in r["notes"] if "lot outline was read" in x)
    assert "None" not in n and "as at" not in n


def test_a_ring_with_a_missing_coordinate_is_not_an_outline():
    bad = [[150.0, -33.0], [150.001, None], [150.001, -33.001], [150.0, -33.001], [150.0, -33.0]]
    assert _lot([(_json.dumps({"type": "Polygon", "coordinates": [bad]}), T)])[0] is None
