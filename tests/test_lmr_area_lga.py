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

def test_live_answer_is_used_and_the_fallback_is_never_called(monkeypatch):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: (True, "PENRITH"))
    called = []
    assert inp._lga_resolved(-33.75, 150.7, lambda *a: called.append(a) or ("HORNSBY", "2026-06-18")) == ("PENRITH", None)
    assert called == []


def test_a_live_answer_of_no_council_is_never_overridden_by_the_fallback(monkeypatch):
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: ANSWERED_NONE)
    called = []
    assert inp._lga_resolved(-33.75, 150.7, lambda *a: called.append(a) or ("PENRITH", "2026-06-18")) == (None, None)
    assert called == []


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
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: NO_ANSWER)
    out = inp.fetch_layers(-33.75, 150.7, None, lambda *a: ("PENRITH", "2026-06-18"))
    assert out["lga"] == "PENRITH" and out["lga_source"] == SNAP
    monkeypatch.setattr(inp, "_lga_live", lambda lat, lng: (True, "HORNSBY"))
    out = inp.fetch_layers(-33.75, 150.7, None, lambda *a: ("PENRITH", "2026-06-18"))
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
    """The review feared a TypeError: area_check forwards its keywords, so the fallback must reach fetch_layers unchanged."""
    seen = {}
    monkeypatch.setattr(inp, "fetch_lot_rings", lambda lat, lng: None)
    monkeypatch.setattr(inp, "fetch_layers", lambda lat, lng, rings, lga_fallback=None: seen.update(fb=lga_fallback) or lot())
    marker = lambda *a: ("PENRITH", "2026-06-18")  # noqa: E731
    inp.area_check(-33.75, 150.7, lga_fallback=marker)
    assert seen["fb"] is marker


def test_the_api_route_passes_the_snapshot_lookup_as_the_fallback(monkeypatch):
    from services import housing_sepp_gates_api as api

    seen = {}
    monkeypatch.setattr(inp, "area_check", lambda lat, lng, **kw: seen.update(kw) or {"ok": True})
    assert api.housing_sepp_area_check(-33.75, 150.7) == {"ok": True}
    assert seen["lga_fallback"] is lga.lga_from_snapshot and "flood_fn" in seen


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
