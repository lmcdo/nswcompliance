"""
Adversarial unit tests for services/shadow_detector.py.

Pure-logic functions only — no DB, no network, no shadow_model imports.

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
from services.shadow_model import Scenario


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


def test_adg_compliant_empty_scenarios_is_not_assessed():
    """THREE-STATE (fix 1): cannot assess without scenarios — None, never a
    compliance verdict. The old doctrine defaulted to True."""
    assert _adg_compliant([]) is None


def test_adg_compliant_no_noon_scenario_is_not_assessed():
    """jun21_12pm absent — can't gate on it → None (was: default True)."""
    scenarios = [
        _scenario("jun21_9am", overlaps=True, length_m=35.0),
        _scenario("jun21_3pm", overlaps=True, length_m=30.0),
    ]
    assert _adg_compliant(scenarios) is None


def test_adg_compliant_nine_and_three_overlap_but_noon_clear():
    """9am and 3pm always produce long shadows — only noon drives compliance verdict."""
    scenarios = [
        _scenario("jun21_9am", overlaps=True, length_m=35.0),
        _scenario("jun21_12pm", overlaps=False, length_m=14.0),
        _scenario("jun21_3pm", overlaps=True, length_m=30.0),
    ]
    assert _adg_compliant(scenarios) is True


def test_adg_compliant_null_overlaps_is_not_assessed():
    """overlaps_subject_lot=None: unknown ≠ confirmed overlap AND unknown ≠
    confirmed clear. The old code turned unknown into a compliance PASS
    (bool(None)=False → True); three-state returns None (fix 1)."""
    s = _scenario("jun21_12pm", overlaps=False, length_m=14.0)
    s["overlaps_subject_lot"] = None
    assert _adg_compliant([s]) is None


def test_adg_compliant_errored_noon_is_not_assessed_never_a_pass():
    """THE fix-1 pin: an errored noon scenario must NOT become a compliance
    pass. Old chain: error → overlaps False → adg_compliant True — a crash
    served as 'meets the ADG test'. FAILS on the pre-change code."""
    s = _scenario("jun21_12pm", overlaps=False, length_m=14.0)
    s["status"] = "unavailable"
    s["overlaps_subject_lot"] = None
    s["shadow_length_m"] = None
    assert _adg_compliant([s]) is None


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
    # Scenario NamedTuple: (key, month, day, local_hour, local_minute,
    # description). No hour_utc and no direction_deg — the hand-computed UTC
    # offset and the stored bearing constant were the shadow calibration defect.
    STUB_SCENARIOS = [
        Scenario("jun21_12pm", 6, 21, 12, 0, "ADG noon Jun 21"),
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
    # Typed absence (fix 1): a null/empty shadow output is UNAVAILABLE — not a
    # measured 0.0m no-shadow claim (which is what the old code served).
    assert result[0]["status"] == "unavailable"
    assert result[0]["shadow_length_m"] is None
    assert result[0]["overlaps_subject_lot"] is None


def test_build_scenario_list_errored_scenario_is_typed_unavailable(monkeypatch):
    """THE fix-1 shape pin: an {'error': ...} scenario must serve None
    measurements and status 'unavailable' — the old code served
    shadow_length_m=0.0 and overlaps_subject_lot=False, a crash rendered as a
    numeric no-shadow claim. FAILS on the pre-change code."""
    import services.shadow_detector as sd

    # Scenario NamedTuple: (key, month, day, local_hour, local_minute,
    # description). No hour_utc and no direction_deg — the hand-computed UTC
    # offset and the stored bearing constant were the shadow calibration defect.
    STUB_SCENARIOS = [
        Scenario("jun21_12pm", 6, 21, 12, 0, "ADG noon Jun 21"),
    ]
    monkeypatch.setattr(sd, "SHADOW_SCENARIOS", STUB_SCENARIOS)

    shadow_map = {"jun21_12pm": {"error": "pybdshadow raised: bad geometry"}}
    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    result = sd._build_scenario_list(shadow_map, lot, 151.21, -33.87)
    assert result[0]["status"] == "unavailable"
    assert result[0]["shadow_length_m"] is None
    assert result[0]["shadow_overlap_fraction"] is None
    assert result[0]["overlaps_subject_lot"] is None
    assert result[0]["shadow_polygon"] is None
    assert "pybdshadow" in result[0]["error_note"]
    # And the chain must end in NOT-ASSESSED, never a compliance pass:
    assert sd._adg_compliant(result) is None


def test_build_scenario_list_computed_scenario_is_typed_computed(monkeypatch):
    import services.shadow_detector as sd

    # Scenario NamedTuple: (key, month, day, local_hour, local_minute,
    # description). No hour_utc and no direction_deg — the hand-computed UTC
    # offset and the stored bearing constant were the shadow calibration defect.
    STUB_SCENARIOS = [
        Scenario("jun21_12pm", 6, 21, 12, 0, "ADG noon Jun 21"),
    ]
    monkeypatch.setattr(sd, "SHADOW_SCENARIOS", STUB_SCENARIOS)
    monkeypatch.setattr(sd, "shadow_reach_m", lambda *a, **kw: 14.0)
    monkeypatch.setattr(sd, "shadow_overlap_fraction", lambda *a, **kw: 0.1)
    monkeypatch.setattr(sd, "overlaps_lot", lambda *a, **kw: False)
    monkeypatch.setattr(sd, "shadow_on_lot_geojson", lambda *a, **kw: None)

    shadow_map = {"jun21_12pm": {"type": "FeatureCollection", "features": []}}
    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    result = sd._build_scenario_list(shadow_map, lot, 151.21, -33.87)
    assert result[0]["status"] == "computed"
    assert result[0]["shadow_length_m"] == 14.0
    assert sd._adg_compliant(result) is True


# ---------------------------------------------------------------------------
# Reach-ceiling guard — fail closed (Sol pre-push round, 2026-08-07)
# ---------------------------------------------------------------------------

def test_build_scenario_list_ceiling_failure_fails_closed(monkeypatch):
    """An exception in the reach-ceiling computation used to be caught and
    ignored, silently disabling the physical-plausibility guard — the 1,779 m
    reach the guard exists to block would then be served as status='computed'.
    With a known height, a reach that cannot be validated is UNAVAILABLE.
    FAILS on the pre-fix code (it served the unvalidated reach as computed)."""
    import services.shadow_detector as sd

    STUB_SCENARIOS = [
        Scenario("jun21_12pm", 6, 21, 12, 0, "ADG noon Jun 21"),
    ]
    monkeypatch.setattr(sd, "SHADOW_SCENARIOS", STUB_SCENARIOS)
    # The implausible reach the ceiling guard exists to catch:
    monkeypatch.setattr(sd, "shadow_reach_m", lambda *a, **kw: 1779.5)
    monkeypatch.setattr(sd, "shadow_overlap_fraction", lambda *a, **kw: 0.9)
    monkeypatch.setattr(sd, "overlaps_lot", lambda *a, **kw: True)
    monkeypatch.setattr(sd, "shadow_on_lot_geojson", lambda *a, **kw: None)

    def _raise(*a, **kw):
        raise RuntimeError("suncalc is not installed")
    monkeypatch.setattr(sd, "sun_position", _raise)

    shadow_map = {"jun21_12pm": {"type": "FeatureCollection", "features": []}}
    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    result = sd._build_scenario_list(shadow_map, lot, 151.21, -33.87, height_m=9.0)
    assert result[0]["status"] == "unavailable"
    assert result[0]["shadow_length_m"] is None
    assert result[0]["overlaps_subject_lot"] is None
    assert "could not be validated" in result[0]["error_note"]
    # The chain must end NOT-ASSESSED, never a verdict from an unvalidated run:
    assert sd._adg_compliant(result) is None


def test_build_scenario_list_no_height_does_not_fail_closed(monkeypatch):
    """Without a known height there is no ceiling to validate against, so the
    fail-closed branch must not fire — pinned so it cannot over-reach."""
    import services.shadow_detector as sd

    STUB_SCENARIOS = [
        Scenario("jun21_12pm", 6, 21, 12, 0, "ADG noon Jun 21"),
    ]
    monkeypatch.setattr(sd, "SHADOW_SCENARIOS", STUB_SCENARIOS)
    monkeypatch.setattr(sd, "shadow_reach_m", lambda *a, **kw: 14.0)
    monkeypatch.setattr(sd, "shadow_overlap_fraction", lambda *a, **kw: 0.1)
    monkeypatch.setattr(sd, "overlaps_lot", lambda *a, **kw: False)
    monkeypatch.setattr(sd, "shadow_on_lot_geojson", lambda *a, **kw: None)

    def _raise(*a, **kw):
        raise RuntimeError("suncalc is not installed")
    monkeypatch.setattr(sd, "sun_position", _raise)

    shadow_map = {"jun21_12pm": {"type": "FeatureCollection", "features": []}}
    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    result = sd._build_scenario_list(shadow_map, lot, 151.21, -33.87, height_m=None)
    assert result[0]["status"] == "computed"
    assert result[0]["shadow_length_m"] == 14.0


# ---------------------------------------------------------------------------
# Lord Howe civil-time refusal (Sol pre-push round, 2026-08-07)
# ---------------------------------------------------------------------------

def test_lord_howe_longitude_is_refused_not_mislabelled():
    """Lord Howe Island keeps Australia/Lord_Howe (+10:30 outside daylight
    saving), so a winter scenario there would be modelled 30 minutes early
    under the Sydney wall-clock label. The route refuses east of 154.0 E — a
    geographic fact (the NSW mainland ends at Cape Byron, 153.64 E; only the
    Lord Howe group lies beyond), not an approximated civil-time boundary.
    Measured exposure 2026-08-07: 0 of 538 stored reports east of 154.0.
    FAILS on the pre-fix code (the request proceeded to the lot fetch)."""
    from fastapi import HTTPException
    import services.shadow_detector as sd

    req = sd.ShadowRequest(
        address="Lord Howe Island NSW 2898", prop_id="0",
        lat=-31.55, lng=159.08, report_id="test")
    with pytest.raises(HTTPException) as exc:
        sd.run_shadow(req)
    assert exc.value.status_code == 422
    assert "Lord Howe" in str(exc.value.detail)


def test_mainland_longitude_is_not_refused_by_the_lord_howe_gate(monkeypatch):
    """Sydney must sail past the civil-time gate and fail later (stubbed lot
    fetch) — proves the refusal does not over-reach onto the mainland."""
    from fastapi import HTTPException
    import services.shadow_detector as sd

    monkeypatch.setattr(sd, "_fetch_lot_geometry", lambda *a, **kw: None)
    req = sd.ShadowRequest(
        address="Sydney NSW", prop_id="0",
        lat=-33.87, lng=151.21, report_id="test")
    with pytest.raises(HTTPException) as exc:
        sd.run_shadow(req)
    assert "Lord Howe" not in str(exc.value.detail)


# ---------------------------------------------------------------------------
# Intersection failure must FAIL CLOSED, not become a measured zero
# (authorized-repair prerequisite, 2026-08-07)
# ---------------------------------------------------------------------------

def test_overlap_fraction_is_none_when_the_intersection_cannot_be_computed(monkeypatch):
    """GEOS raises TopologyException on self-touching or unclosed cadastral
    rings. That used to be caught and returned as 0.0, so a failed geometry op
    was served as "0% of the lot is in shadow". Across the stored corpus 7
    reports told a customer they met the ADG solar-access test on exactly that
    basis, while the recomputed truth was up to 100% of the lot in shadow.
    FAILS on the pre-fix code, which returned 0.0."""
    import services.shadow_model as sm

    def _raise(*a, **kw):
        raise sm.ShadowGeometryError("TopologyException: Ring edge missing")
    monkeypatch.setattr(sm, "_shadow_intersection", _raise)

    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    shadow = {"type": "FeatureCollection", "features": []}

    assert sm.shadow_overlap_fraction(shadow, lot) is None
    assert sm.shadow_reach_m(shadow, lot) is None
    # And the boolean must not become False — that asserts the lot is
    # unaffected on the strength of a computation that did not happen.
    assert sm.overlaps_lot(shadow, lot) is None


def test_genuine_no_overlap_is_still_zero_not_none(monkeypatch):
    """The counterpart pin: a VALID geometry whose shadow simply misses the lot
    must stay 0.0/False. Without this, the fix above could over-reach and turn
    every clear result into 'not assessed', which would be its own false claim.

    `shapely.geometry` is injected as a stub module with a fixed-area geometry,
    so this runs identically whether or not shapely is installed. Without that
    the test measures the ENVIRONMENT, not the behaviour: where shapely is
    absent, conftest_mocks' MagicMock lot sends the function down its exception
    path and returns None; where it is present, the real path returns 0.0. The
    same assertion would then pass on one interpreter and fail on the other —
    which is how this test failed the first time it ran under the gate."""
    import sys
    import types
    import services.shadow_model as sm

    class _StubLot:
        area = 100.0
        bounds = (0.0, 0.0, 1.0, 1.0)

    shapely_stub = types.ModuleType("shapely")
    geometry_stub = types.ModuleType("shapely.geometry")
    geometry_stub.shape = lambda _g: _StubLot()
    shapely_stub.geometry = geometry_stub
    monkeypatch.setitem(sys.modules, "shapely", shapely_stub)
    monkeypatch.setitem(sys.modules, "shapely.geometry", geometry_stub)
    monkeypatch.setattr(sm, "_shadow_intersection", lambda *a, **kw: None)

    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    shadow = {"type": "FeatureCollection", "features": []}

    assert sm.shadow_overlap_fraction(shadow, lot) == 0.0
    assert sm.shadow_reach_m(shadow, lot) == 0.0
    assert sm.overlaps_lot(shadow, lot) is False


def test_uncomputable_overlap_makes_the_scenario_unavailable(monkeypatch):
    """End-to-end: an unintersectable lot must not be served as status
    'computed' with null measurements — the PDF prints an em dash for a null
    reach, which reads as 'no shadow'. It must be typed-unavailable, and the
    ADG chain must end NOT-ASSESSED rather than issuing a pass."""
    import services.shadow_detector as sd
    import services.shadow_model as sm

    STUB_SCENARIOS = [Scenario("jun21_12pm", 6, 21, 12, 0, "ADG noon Jun 21")]
    monkeypatch.setattr(sd, "SHADOW_SCENARIOS", STUB_SCENARIOS)
    monkeypatch.setattr(sd, "shadow_reach_m", lambda *a, **kw: None)
    monkeypatch.setattr(sd, "shadow_overlap_fraction", lambda *a, **kw: None)
    monkeypatch.setattr(sd, "overlaps_lot", lambda *a, **kw: None)
    monkeypatch.setattr(sd, "shadow_on_lot_geojson", lambda *a, **kw: None)

    shadow_map = {"jun21_12pm": {"type": "FeatureCollection", "features": []}}
    lot = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}

    result = sd._build_scenario_list(shadow_map, lot, 151.21, -33.87, height_m=9.0)
    assert result[0]["status"] == "unavailable"
    assert result[0]["shadow_overlap_fraction"] is None
    assert result[0]["overlaps_subject_lot"] is None
    assert "could not be intersected" in result[0]["error_note"]
    assert sd._adg_compliant(result) is None
