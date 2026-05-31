"""
Adversarial unit tests for services/solar_yield.py.

Tests _parse_solar_response and _clip_panels_to_lot with hostile inputs:
  - all null numeric fields
  - missing keys
  - empty arrays
  - zero values that are falsy (azimuthDegrees=0.0 = north-facing)
  - solarPotential absent
  - fewer sunshineQuantiles than expected
  - coverage_available=False
  - panels outside lot / inside lot / mixed
  - malformed panel entries
  - null yearlyEnergyDcKwh per panel
  - maxArrayPanelsCount null
  - invalid lot polygon

No DB, no network calls — all tests are pure unit tests.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.solar_yield import (
    _parse_solar_response,
    _clip_panels_to_lot,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A simple square lot in Sydney CBD (~100m × 100m)
_LOT_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [151.200, -33.870],
        [151.201, -33.870],
        [151.201, -33.871],
        [151.200, -33.871],
        [151.200, -33.870],
    ]],
}

_PANEL_INSIDE = {
    "center": {"latitude": -33.8705, "longitude": 151.2005},
    "segmentIndex": 0,
    "yearlyEnergyDcKwh": 400.0,
}
_PANEL_OUTSIDE = {
    "center": {"latitude": -33.800, "longitude": 151.100},
    "segmentIndex": 0,
    "yearlyEnergyDcKwh": 400.0,
}

_NORMAL_SEGMENT = {
    "stats": {
        "areaMeters2": 50.0,
        "sunshineQuantiles": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100],
    },
    "pitchDegrees": 15.0,
    "azimuthDegrees": 0.0,  # north-facing
}

_NORMAL_SP = {
    "maxArrayPanelsCount": 10,
    "maxArrayAreaMeters2": 20.0,
    "maxSunshineHoursPerYear": 1600.0,
    "wholeRoofStats": {"areaMeters2": 80.0},
    "roofSegmentStats": [_NORMAL_SEGMENT],
    "solarPanels": [_PANEL_INSIDE],
    "solarPanelConfigs": [{"panelsCount": 10, "yearlyEnergyDcKwh": 4000.0}],
}

_NORMAL_RESPONSE = {"solarPotential": _NORMAL_SP, "imageryDate": {"year": 2024, "month": 3}}


def _make_response(**overrides) -> dict:
    """Build a response dict with optional solarPotential overrides."""
    import copy
    resp = copy.deepcopy(_NORMAL_RESPONSE)
    if overrides:
        resp["solarPotential"].update(overrides)
    return resp


# ---------------------------------------------------------------------------
# _parse_solar_response — coverage sentinel
# ---------------------------------------------------------------------------

def test_coverage_available_false_returns_zero_output():
    out = _parse_solar_response({"coverage_available": False})
    assert out.coverage_available is False
    assert out.max_panels == 0
    assert out.annual_kwh_estimate == 0.0
    assert out.roof_area_m2 == 0.0


def test_missing_solar_potential_returns_no_coverage():
    out = _parse_solar_response({"imageryDate": {"year": 2024, "month": 1}})
    assert out.coverage_available is False


def test_explicit_null_solar_potential_returns_no_coverage():
    out = _parse_solar_response({"solarPotential": None})
    assert out.coverage_available is False


# ---------------------------------------------------------------------------
# _parse_solar_response — null / missing numeric fields
# ---------------------------------------------------------------------------

def test_all_null_numeric_fields_no_crash():
    """Null values on every numeric field must not raise — all should become 0."""
    raw = {
        "solarPotential": {
            "maxArrayPanelsCount": None,
            "maxArrayAreaMeters2": None,
            "maxSunshineHoursPerYear": None,
            "wholeRoofStats": {"areaMeters2": None},
            "roofSegmentStats": [],
            "solarPanels": [],
            "solarPanelConfigs": [],
        },
        "imageryDate": {"year": None, "month": None},
    }
    out = _parse_solar_response(raw)
    assert out.max_panels == 0
    assert out.max_panel_area_m2 == 0.0
    assert out.roof_area_m2 == 0.0
    assert out.sunshine_hours_per_year == 0.0
    assert out.annual_kwh_estimate == 0.0
    assert out.imagery_date == "unknown"
    assert out.coverage_available is True


def test_missing_whole_roof_stats_no_crash():
    raw = _make_response(wholeRoofStats=None)
    out = _parse_solar_response(raw)
    assert out.roof_area_m2 == 0.0


def test_empty_solar_panel_configs_annual_kwh_zero():
    raw = _make_response(solarPanelConfigs=None)
    out = _parse_solar_response(raw)
    assert out.annual_kwh_estimate == 0.0


def test_null_solar_panel_configs_annual_kwh_zero():
    raw = _make_response(solarPanelConfigs=[])
    out = _parse_solar_response(raw)
    assert out.annual_kwh_estimate == 0.0


# ---------------------------------------------------------------------------
# _parse_solar_response — imagery date edge cases
# ---------------------------------------------------------------------------

def test_imagery_date_missing_fields_gives_unknown():
    raw = _make_response()
    raw["imageryDate"] = {}
    out = _parse_solar_response(raw)
    assert out.imagery_date == "unknown"


def test_imagery_date_year_only_gives_unknown():
    raw = _make_response()
    raw["imageryDate"] = {"year": 2024}
    out = _parse_solar_response(raw)
    assert out.imagery_date == "unknown"


def test_imagery_date_valid():
    raw = _make_response()
    raw["imageryDate"] = {"year": 2023, "month": 6}
    out = _parse_solar_response(raw)
    assert out.imagery_date == "2023-06"


def test_imagery_date_single_digit_month_zero_padded():
    raw = _make_response()
    raw["imageryDate"] = {"year": 2023, "month": 1}
    out = _parse_solar_response(raw)
    assert out.imagery_date == "2023-01"


# ---------------------------------------------------------------------------
# _parse_solar_response — segment scoring: azimuth edge cases
# ---------------------------------------------------------------------------

def test_north_facing_azimuth_zero_scores_highest():
    """azimuthDegrees=0.0 is north-facing in Southern Hemisphere — must score BEST not worst.

    Previously broken: `seg.get("azimuthDegrees") or 180.0` evaluated 0.0 as falsy,
    treating north-facing as south-facing and inverting the tiebreaker.
    """
    # 11-value quantiles: index 5 (median) = 600 for both — equal sunshine → tiebreaker decides
    _quantiles = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100]
    north_seg = {
        "stats": {"areaMeters2": 50.0, "sunshineQuantiles": _quantiles},
        "pitchDegrees": 15.0,
        "azimuthDegrees": 0.0,   # north: 0.0 is falsy — was incorrectly treated as south
    }
    south_seg = {
        "stats": {"areaMeters2": 50.0, "sunshineQuantiles": _quantiles},
        "pitchDegrees": 15.0,
        "azimuthDegrees": 180.0,  # south
    }
    raw = _make_response(roofSegmentStats=[south_seg, north_seg])
    out = _parse_solar_response(raw)
    # north_seg should win the tiebreak: score = 600*(1+0.05*1.0)=630 vs south 600*(1+0.05*0)=600
    assert out.best_azimuth_deg == 0.0


def test_null_azimuth_defaults_to_south_not_north():
    """azimuthDegrees=None means unknown — should default to south (no bonus), not north."""
    _quantiles = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100]
    null_az_seg = {
        "stats": {"areaMeters2": 50.0, "sunshineQuantiles": _quantiles},
        "pitchDegrees": 10.0,
        "azimuthDegrees": None,
    }
    north_seg = {
        "stats": {"areaMeters2": 50.0, "sunshineQuantiles": _quantiles},
        "pitchDegrees": 15.0,
        "azimuthDegrees": 0.0,
    }
    raw = _make_response(roofSegmentStats=[null_az_seg, north_seg])
    out = _parse_solar_response(raw)
    # north_seg should win tiebreak: null → 180° (no bonus), north → 0° (full bonus)
    assert out.best_azimuth_deg == 0.0


def test_fewer_than_6_sunshine_quantiles_uses_zero():
    """sunshineQuantiles with <6 values — index 5 access must not crash."""
    seg = {
        "stats": {"areaMeters2": 50.0, "sunshineQuantiles": [100, 200, 300]},
        "pitchDegrees": 15.0,
        "azimuthDegrees": 0.0,
    }
    raw = _make_response(roofSegmentStats=[seg])
    out = _parse_solar_response(raw)
    # Should not raise; median sunshine defaults to 0 so output is still valid
    assert out.coverage_available is True


def test_empty_segments_no_crash():
    raw = _make_response(roofSegmentStats=[])
    out = _parse_solar_response(raw)
    assert out.best_pitch_deg == 0.0
    # Default azimuth 180.0 (south-facing) when no segments — consistent with scorer
    assert out.best_azimuth_deg == 180.0


def test_null_segments_no_crash():
    raw = _make_response(roofSegmentStats=None)
    out = _parse_solar_response(raw)
    assert out.coverage_available is True
    assert out.best_pitch_deg == 0.0


# ---------------------------------------------------------------------------
# _parse_solar_response — commercial scale threshold
# ---------------------------------------------------------------------------

def test_commercial_scale_roof_area_above_500():
    raw = _make_response(wholeRoofStats={"areaMeters2": 501.0})
    out = _parse_solar_response(raw)
    assert out.is_commercial_scale is True


def test_commercial_scale_roof_area_at_500():
    """500 m² is the boundary — should be commercial (>= 500)."""
    raw = _make_response(wholeRoofStats={"areaMeters2": 500.0})
    out = _parse_solar_response(raw)
    assert out.is_commercial_scale is True


def test_not_commercial_scale_roof_area_below_500():
    raw = _make_response(wholeRoofStats={"areaMeters2": 499.9})
    out = _parse_solar_response(raw)
    assert out.is_commercial_scale is False


# ---------------------------------------------------------------------------
# _parse_solar_response — happy path
# ---------------------------------------------------------------------------

def test_happy_path_returns_correct_values():
    out = _parse_solar_response(_NORMAL_RESPONSE)
    assert out.coverage_available is True
    assert out.max_panels == 10
    assert out.max_panel_area_m2 == 20.0
    assert out.roof_area_m2 == 80.0
    assert out.sunshine_hours_per_year == 1600.0
    assert out.annual_kwh_estimate == 4000.0
    assert out.best_azimuth_deg == 0.0   # north-facing
    assert out.imagery_date == "2024-03"
    assert out.is_heritage is False      # always False here; set by caller
    assert out.is_commercial_scale is False


# ---------------------------------------------------------------------------
# _clip_panels_to_lot — requires shapely
# ---------------------------------------------------------------------------

_has_shapely = False
try:
    import shapely  # noqa: F401
    _has_shapely = True
except ImportError:
    pass

_skip_no_shapely = pytest.mark.skipif(not _has_shapely, reason="shapely not installed")


@_skip_no_shapely
def test_all_panels_inside_lot_preserves_count():
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [_PANEL_INSIDE, _PANEL_INSIDE]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    assert result["maxArrayPanelsCount"] == 2
    assert result["_lot_clipped"] is True


@_skip_no_shapely
def test_all_panels_outside_lot_returns_zero():
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [_PANEL_OUTSIDE, _PANEL_OUTSIDE]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    assert result["maxArrayPanelsCount"] == 0
    assert result["_lot_annual_kwh"] == 0.0
    assert result["_lot_clipped"] is True


@_skip_no_shapely
def test_mixed_panels_counts_only_inside():
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [_PANEL_INSIDE, _PANEL_OUTSIDE, _PANEL_INSIDE]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    assert result["maxArrayPanelsCount"] == 2


@_skip_no_shapely
def test_null_yearly_energy_per_panel_no_crash():
    """yearlyEnergyDcKwh=None on a panel must not raise — should count as 0."""
    panel_null_kwh = {
        "center": {"latitude": -33.8705, "longitude": 151.2005},
        "segmentIndex": 0,
        "yearlyEnergyDcKwh": None,
    }
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [panel_null_kwh]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    assert result["_lot_annual_kwh"] == 0.0


@_skip_no_shapely
def test_malformed_panel_missing_center_skipped():
    """Panel without center key should be skipped, not crash."""
    bad_panel = {"segmentIndex": 0, "yearlyEnergyDcKwh": 400.0}
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [bad_panel, _PANEL_INSIDE]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    # Bad panel skipped, good panel counted
    assert result["maxArrayPanelsCount"] == 1


@_skip_no_shapely
def test_null_max_array_panels_count_no_crash():
    """maxArrayPanelsCount=null in the response must not cause TypeError."""
    sp = dict(_NORMAL_SP)
    sp["maxArrayPanelsCount"] = None
    sp["solarPanels"] = [_PANEL_INSIDE]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    # Should not raise; falls back to len(panels)
    assert result["maxArrayPanelsCount"] == 1


@_skip_no_shapely
def test_empty_panels_list_returns_sp_unchanged():
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = []
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    # No panels to clip — sp returned unchanged (no _lot_clipped flag)
    assert "_lot_clipped" not in result


@_skip_no_shapely
def test_invalid_lot_polygon_returns_sp_unchanged():
    sp = dict(_NORMAL_SP)
    bad_polygon = {"type": "Polygon", "coordinates": "not_a_list"}
    result = _clip_panels_to_lot(sp, bad_polygon)
    assert "_lot_clipped" not in result


@_skip_no_shapely
def test_kwh_sum_correct_for_inside_panels():
    panel_a = {**_PANEL_INSIDE, "yearlyEnergyDcKwh": 300.0}
    panel_b = {**_PANEL_INSIDE, "yearlyEnergyDcKwh": 250.0}
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [panel_a, panel_b]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    assert result["_lot_annual_kwh"] == 550.0


@_skip_no_shapely
def test_zero_total_area_uses_per_panel_fallback():
    """maxArrayAreaMeters2=0 should not produce 0-area panels — uses 2.0m² fallback."""
    sp = dict(_NORMAL_SP)
    sp["maxArrayAreaMeters2"] = 0.0
    sp["solarPanels"] = [_PANEL_INSIDE]
    result = _clip_panels_to_lot(sp, _LOT_POLYGON)
    # 1 panel × 2.0m² fallback
    assert result["maxArrayAreaMeters2"] == 2.0


# ---------------------------------------------------------------------------
# Round-trip: _parse_solar_response with lot clipping
# ---------------------------------------------------------------------------

@_skip_no_shapely
def test_parse_with_lot_clipping_uses_lot_kwh():
    """When lot_polygon_wgs84 is provided and panels are inside, annual_kwh comes from per-panel sum."""
    panel = {**_PANEL_INSIDE, "yearlyEnergyDcKwh": 500.0}
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [panel]
    raw = {"solarPotential": sp, "imageryDate": {"year": 2024, "month": 6}}
    out = _parse_solar_response(raw, lot_polygon_wgs84=_LOT_POLYGON)
    assert out.annual_kwh_estimate == 500.0


@_skip_no_shapely
def test_parse_with_lot_clipping_no_panels_in_lot():
    """All panels outside lot → annual_kwh=0, coverage_available still True."""
    sp = dict(_NORMAL_SP)
    sp["solarPanels"] = [_PANEL_OUTSIDE]
    raw = {"solarPotential": sp, "imageryDate": {"year": 2024, "month": 6}}
    out = _parse_solar_response(raw, lot_polygon_wgs84=_LOT_POLYGON)
    assert out.annual_kwh_estimate == 0.0
    assert out.max_panels == 0
    assert out.coverage_available is True  # Google has data; lot just has no panels
