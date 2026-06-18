"""GATE-1 part 2 — derive dev_type from the LEP Land Use Table.

The engine hardcoded dev_type='dwelling_house'. It now reads the densest
PERMITTED residential form for the zone + LGA from lep_land_use_table, so R3/R4
get their denser permitted yield while R2 (which does not permit RFB) stays a
dwelling house. Fail-safe to dwelling_house on any error or no coverage.
"""
import pytest

import services.intelligence_brief as ib
from services.intelligence_brief import _densest_permitted_dev_type, _fetch_permitted_dev_type


# --- the density policy (pure) ----------------------------------------------

@pytest.mark.parametrize("permitted,expected", [
    ({"residential_flat_buildings", "dwelling_houses"}, "residential_flat_building"),
    ({"shop_top_housing", "dwelling_houses"}, "shop_top_housing"),
    ({"multi_dwelling_housing", "attached_dwellings", "dwelling_houses"}, "multi_dwelling_housing"),
    ({"attached_dwellings", "dwelling_houses"}, "attached_dwelling"),
    ({"dual_occupancies", "dwelling_houses"}, "dual_occupancy"),
    ({"semi_detached_dwellings", "dwelling_houses"}, "dual_occupancy"),
    ({"dwelling_houses", "secondary_dwellings"}, "dwelling_house"),
    # Inner West R2 reality: no RFB / multi / dual-occ permitted -> dwelling_house
    ({"dwelling_houses", "secondary_dwellings", "semi_detached_dwellings", "seniors_housing"}, "dual_occupancy"),
    # nothing residential permitted -> conservative default
    ({"roads", "group_homes", "neighbourhood_shops"}, "dwelling_house"),
    (set(), "dwelling_house"),
])
def test_densest_permitted_dev_type(permitted, expected):
    assert _densest_permitted_dev_type(permitted) == expected


# --- the DB fetcher ---------------------------------------------------------

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    def execute(self, *a, **k):
        return None
    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
    def cursor(self):
        return _FakeCursor(self._rows)
    def close(self):
        return None


def test_fetch_returns_densest_permitted(monkeypatch):
    monkeypatch.setattr(ib, "_get_db_conn",
                        lambda: _FakeConn([("residential_flat_buildings",), ("dwelling_houses",)]))
    assert _fetch_permitted_dev_type("R4", "Inner West") == "residential_flat_building"


def test_fetch_r2_with_only_houses(monkeypatch):
    monkeypatch.setattr(ib, "_get_db_conn",
                        lambda: _FakeConn([("dwelling_houses",), ("secondary_dwellings",)]))
    assert _fetch_permitted_dev_type("R2", "Inner West") == "dwelling_house"


def test_fetch_missing_inputs_returns_dwelling_house():
    assert _fetch_permitted_dev_type(None, "Inner West") == "dwelling_house"
    assert _fetch_permitted_dev_type("R4", None) == "dwelling_house"


def test_fetch_db_error_is_failsafe(monkeypatch):
    def _boom():
        raise RuntimeError("DB down")
    monkeypatch.setattr(ib, "_get_db_conn", _boom)
    assert _fetch_permitted_dev_type("R4", "Inner West") == "dwelling_house"
