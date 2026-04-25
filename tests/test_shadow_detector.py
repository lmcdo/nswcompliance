"""
Adversarial unit tests for services/shadow_detector.py.

Pure-logic functions only — no DB, no network, no shadow_model/sentinel2 imports.

Covers:
  _arcgis_to_geojson  — coordinate transform, edge cases
  _adg_compliant      — compliance gate, edge cases
  _worst_case         — shadow_length_m comparisons, None values
  _build_scenario_list — null shadow_map values, empty SHADOW_SCENARIOS
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# _arcgis_to_geojson, _adg_compliant, _worst_case are pure functions with no imports
from services.shadow_detector import (
    _arcgis_to_geojson,
    _adg_compliant,
    _worst_case,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scenario(key: str, overlaps: bool, length_m: float) -> dict:
    """Build a minimal scenario dict."""
    return {
        "scenario": key,
        "label": key,
        "date": "2025-06-21",
        "time_local": "12:00",
        "shadow_length_m": length_m,
        "shadow_direction_deg": 180.0,
        "overlaps_subject_lot": overlaps,
    }


# Web-Mercator (EPSG:3857) coordinate for Sydney CBD ~(151.2°, -33.87°)
# x = lng * R/180, y = ln(tan(π/4 + lat_rad/2)) * R/π
_R = 20037508.342789244
_SYDNEY_X = 151.21 * _R / 180.0
_SYDNEY_Y = math.log(math.tan(math.pi / 4.0 + math.radians(-33.87) / 2.0)) * _R / math.pi


# ---------------------------------------------------------------------------
# _arcgis_to_geojson — coordinate transform
# ---------------------------------------------------------------------------

def test_arcgis_to_geojson_known_point_approximately_correct():
    """A single-ring geometry at Sydney CBD should round-trip to ~(151.21, -33.87)."""
    geom = {"rings": [[
        [_SYDNEY_X, _SYDNEY_Y],
        [_SYDNEY_X + 1000, _SYDNEY_Y],
        [_SYDNEY_X + 1000, _SYDNEY_Y - 1000],
        [_SYDNEY_X, _SYDNEY_Y - 1000],
        [_SYDNEY_X, _SYDNEY_Y],
    ]]}
    result = _arcgis_to_geojson(geom)
    assert result["type"] == "Polygon"
    first_coord = result["coordinates"][0][0]
    assert first_coord[0] == pytest.approx(151.21, abs=0.1)
    assert first_coord[1] == pytest.approx(-33.87, abs=0.1)


def test_arcgis_to_geojson_empty_rings_returns_empty_coordinates():
    result = _arcgis_to_geojson({"rings": []})
    assert result == {"type": "Polygon", "coordinates": []}


def test_arcgis_to_geojson_missing_rings_key_returns_empty_coordinates():
    """geometry dict with no 'rings' key — .get("rings") or [] guard."""
    result = _arcgis_to_geojson({})
    assert result == {"type": "Polygon", "coordinates": []}


def test_arcgis_to_geojson_null_rings_returns_empty_not_crash():
    """geometry["rings"] = null — was iterating None before or [] fix."""
    result = _arcgis_to_geojson({"rings": None})
    assert result == {"type": "Polygon", "coordinates": []}


def test_arcgis_to_geojson_single_ring_has_correct_coord_count():
    ring = [[_SYDNEY_X + i * 1000, _SYDNEY_Y + i * 1000] for i in range(5)]
    result = _arcgis_to_geojson({"rings": [ring]})
    assert len(result["coordinates"]) == 1
    assert len(result["coordinates"][0]) == 5


def test_arcgis_to_geojson_multiple_rings_preserved():
    ring_a = [[_SYDNEY_X, _SYDNEY_Y], [_SYDNEY_X + 1000, _SYDNEY_Y], [_SYDNEY_X, _SYDNEY_Y]]
    ring_b = [[_SYDNEY_X + 2000, _SYDNEY_Y + 2000], [_SYDNEY_X + 3000, _SYDNEY_Y + 2000], [_SYDNEY_X + 2000, _SYDNEY_Y + 2000]]
    result = _arcgis_to_geojson({"rings": [ring_a, ring_b]})
    assert len(result["coordinates"]) == 2


# ---------------------------------------------------------------------------
# _adg_compliant — compliance gate
# ---------------------------------------------------------------------------

def test_adg_compliant_noon_no_overlap_is_compliant():
    scenarios = [_scenario("jun21_12pm", overlaps=False, length_m=14.0)]
    assert _adg_compliant(scenarios) is True


def test_adg_compliant_noon_overlaps_is_non_compliant():
    scenarios = [_scenario("jun21_12pm", overlaps=True, length_m=14.0)]
    assert _adg_compliant(scenarios) is False


def test_adg_compliant_empty_scenarios_defaults_to_compliant():
    """Cannot assess without scenarios — default to True (compliant)."""
    assert _adg_compliant([]) is True


def test_adg_compliant_no_noon_scenario_defaults_to_compliant():
    """jun21_12pm absent — can't gate on it, default to True."""
    scenarios = [
        _scenario("jun21_9am", overlaps=True, length_m=35.0),
        _scenario("jun21_3pm", overlaps=True, length_m=30.0),
    ]
    assert _adg_compliant(scenarios) is True


def test_adg_compliant_nine_and_three_overlap_but_noon_clear():
    """9am and 3pm always produce long shadows — only noon drives compliance verdict."""
    scenarios = [
        _scenario("jun21_9am", overlaps=True, length_m=35.0),
        _scenario("jun21_12pm", overlaps=False, length_m=14.0),
        _scenario("jun21_3pm", overlaps=True, length_m=30.0),
    ]
    assert _adg_compliant(scenarios) is True


def test_adg_compliant_null_overlaps_treated_as_false():
    """overlaps_subject_lot=None (DB null) must not invert the verdict.
    bool(None) = False → not False = True → treated as compliant. Correct: unknown ≠ confirmed overlap."""
    s = _scenario("jun21_12pm", overlaps=False, length_m=14.0)
    s["overlaps_subject_lot"] = None
    assert _adg_compliant([s]) is True


# ---------------------------------------------------------------------------
# _worst_case
# ---------------------------------------------------------------------------

def test_worst_case_returns_longest_shadow_scenario():
    scenarios = [
        _scenario("jun21_9am", overlaps=False, length_m=35.0),
        _scenario("jun21_12pm", overlaps=False, length_m=14.0),
        _scenario("jun21_3pm", overlaps=False, length_m=30.0),
    ]
    assert _worst_case(scenarios) == "jun21_9am"


def test_worst_case_empty_scenarios_returns_fallback():
    assert _worst_case([]) == "jun21_9am"


def test_worst_case_all_zero_lengths_returns_first_scenario():
    """All shadows zero — any scenario is equally worst; max picks first by stability."""
    scenarios = [
        _scenario("jun21_9am", overlaps=False, length_m=0.0),
        _scenario("jun21_12pm", overlaps=False, length_m=0.0),
    ]
    # max() on equal values returns the first encountered; either is acceptable
    result = _worst_case(scenarios)
    assert result in ("jun21_9am", "jun21_12pm")


def test_worst_case_null_shadow_length_treated_as_zero():
    """shadow_length_m=None must not raise TypeError in max() comparison.
    Fixed with: s.get("shadow_length_m") or 0.0"""
    scenarios = [
        _scenario("jun21_9am", overlaps=False, length_m=35.0),
        _scenario("jun21_12pm", overlaps=False, length_m=0.0),
    ]
    scenarios[1]["shadow_length_m"] = None  # simulate null from shadow_model error path
    result = _worst_case(scenarios)
    assert result == "jun21_9am"


def test_worst_case_single_scenario_returns_it():
    scenarios = [_scenario("jun21_12pm", overlaps=True, length_m=20.0)]
    assert _worst_case(scenarios) == "jun21_12pm"


# ---------------------------------------------------------------------------
# _build_scenario_list — null shadow_map values
# ---------------------------------------------------------------------------

def test_build_scenario_list_null_shadow_map_value_does_not_crash(monkeypatch):
    """shadow_map[key] = None (not absent) — was raising TypeError on 'error' in None.
    Fixed with: shadow_map.get(key) or {}"""
    import services.shadow_detector as sd

    # Minimal SHADOW_SCENARIOS stub: one scenario
    STUB_SCENARIOS = [
        ("jun21_12pm", 6, 21, 2, "ADG noon Jun 21", "2025-06-21", "12:00", 0.0),
    ]
    monkeypatch.setattr(sd, "SHADOW_SCENARIOS", STUB_SCENARIOS)
    monkeypatch.setattr(sd, "shadow_reach_m", lambda *a, **kw: 0.0)
    monkeypatch.setattr(sd, "shadow_overlap_fraction", lambda *a, **kw: 0.0)
    monkeypatch.setattr(sd, "overlaps_lot", lambda *a, **kw: False)
    monkeypatch.setattr(sd, "shadow_on_lot_geojson", lambda *a, **kw: None)

    shadow_map = {"jun21_12pm": None}  # null value — the bug case
    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    result = sd._build_scenario_list(shadow_map, lot, 151.21, -33.87)
    assert len(result) == 1
    assert result[0]["scenario"] == "jun21_12pm"
    # Error path taken (shadow_geojson was {}) → length = 0, overlaps = False
    assert result[0]["shadow_length_m"] == 0.0
