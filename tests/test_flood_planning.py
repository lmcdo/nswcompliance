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
        if sql.startswith("SET LOCAL"):
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
    s = fp.flood_planning_status(-29.04, 153.25, conn_with(
        [], [("RICHMOND VALLEY",)], [("BALLINA",), ("TWEED",)]))
    assert s["value"] is None
    assert s["reason"] == "we do not hold this council's flood planning map"


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
