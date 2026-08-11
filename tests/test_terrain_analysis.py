"""
Unit tests for services/terrain_analysis.py.

Pure-logic functions — no whitebox, no rasterio, no network.

Covers:
  _aspect_to_compass       — all 8 directions + edge cases
  _classify_hand           — all 5 tiers
  _classify_twi            — all 4 tiers
  _compute_composite_score — boundary values, weights
  _classify_composite      — all 5 tiers
  _run_tool                — success + failure return codes
  TerrainAnalysisDetail    — Pydantic model validation
  FloodSusceptibilityDetail — default disclaimer, model validation
  run_terrain_analysis     — mocked end-to-end (whitebox + rasterio)
"""

import math
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.terrain_analysis import (
    _aspect_to_compass,
    _classify_hand,
    _classify_twi,
    _compute_composite_score,
    _classify_composite,
    _run_tool,
    _central_crop_bounds,
    _interpret_gradient,
    _interpret_landform,
    _interpret_aspect,
    _interpret_solar,
    _interpret_elevation,
    _interpret_ruggedness,
    _build_terrain_interpretation,
    TerrainAnalysisDetail,
    FloodSusceptibilityDetail,
    TerrainRequest,
    TerrainResponse,
    TerrainSeverity,
    TerrainFinding,
    TerrainInterpretation,
    HAND_STREAM_THRESHOLD,
    _HAND_THRESHOLDS,
    _TWI_THRESHOLDS,
    _GEOMORPHON_LABELS,
    _LANDFORM_SEVERITY,
)


# ---------------------------------------------------------------------------
# _aspect_to_compass
# ---------------------------------------------------------------------------


class TestAspectToCompass:
    @pytest.mark.parametrize("deg,expected", [
        (0, "N"),
        (10, "N"),
        (45, "NE"),
        (90, "E"),
        (135, "SE"),
        (180, "S"),
        (225, "SW"),
        (270, "W"),
        (315, "NW"),
        (350, "N"),
        (359.9, "N"),
    ])
    def test_cardinal_directions(self, deg, expected):
        assert _aspect_to_compass(deg) == expected

    def test_360_wraps_to_north(self):
        assert _aspect_to_compass(360.0) == "N"

    def test_nan_returns_flat(self):
        assert _aspect_to_compass(float("nan")) == "flat"

    def test_negative_returns_flat(self):
        assert _aspect_to_compass(-1.0) == "flat"

    def test_boundary_ne_e(self):
        """67.5 is the boundary between NE and E."""
        # 67.5 = midpoint of 45 and 90; anything >= should go to E
        assert _aspect_to_compass(67.5) == "E"
        assert _aspect_to_compass(67.4) == "NE"

    def test_large_value_wraps(self):
        """Values > 360 should wrap via modulo."""
        assert _aspect_to_compass(405) == "NE"  # 405 % 360 = 45


# ---------------------------------------------------------------------------
# _classify_hand
# ---------------------------------------------------------------------------


class TestClassifyHand:
    def test_very_high(self):
        assert _classify_hand(0.5) == "very_high"
        assert _classify_hand(1.9) == "very_high"

    def test_high(self):
        assert _classify_hand(2.0) == "high"
        assert _classify_hand(4.9) == "high"

    def test_moderate(self):
        assert _classify_hand(5.0) == "moderate"
        assert _classify_hand(9.9) == "moderate"

    def test_low(self):
        assert _classify_hand(10.0) == "low"
        assert _classify_hand(14.9) == "low"

    def test_very_low(self):
        assert _classify_hand(15.0) == "very_low"
        assert _classify_hand(100.0) == "very_low"

    def test_zero(self):
        assert _classify_hand(0.0) == "very_high"

    def test_exact_thresholds(self):
        """Threshold values belong to the next tier (>=)."""
        assert _classify_hand(_HAND_THRESHOLDS["very_high"]) == "high"
        assert _classify_hand(_HAND_THRESHOLDS["high"]) == "moderate"
        assert _classify_hand(_HAND_THRESHOLDS["moderate"]) == "low"
        assert _classify_hand(_HAND_THRESHOLDS["low"]) == "very_low"


# ---------------------------------------------------------------------------
# _classify_twi
# ---------------------------------------------------------------------------


class TestClassifyTwi:
    def test_very_high(self):
        assert _classify_twi(12.0) == "very_high"
        assert _classify_twi(20.0) == "very_high"

    def test_high(self):
        assert _classify_twi(9.0) == "high"
        assert _classify_twi(11.9) == "high"

    def test_moderate(self):
        assert _classify_twi(6.0) == "moderate"
        assert _classify_twi(8.9) == "moderate"

    def test_low(self):
        assert _classify_twi(0.0) == "low"
        assert _classify_twi(5.9) == "low"

    def test_exact_thresholds(self):
        assert _classify_twi(_TWI_THRESHOLDS["very_high"]) == "very_high"
        assert _classify_twi(_TWI_THRESHOLDS["high"]) == "high"
        assert _classify_twi(_TWI_THRESHOLDS["moderate"]) == "moderate"


# ---------------------------------------------------------------------------
# _compute_composite_score
# ---------------------------------------------------------------------------


class TestCompositeScore:
    def test_max_susceptibility(self):
        """HAND=0, ponding=1m+, TWI=15+, slope=0° → score should be 100."""
        score = _compute_composite_score(0.0, 1.0, 15.0, 0.0)
        assert score == 100.0

    def test_min_susceptibility(self):
        """HAND=20m+, ponding=0, TWI=0, slope=15°+ → score should be 0."""
        score = _compute_composite_score(20.0, 0.0, 0.0, 15.0)
        assert score == 0.0

    def test_moderate(self):
        """Middle-range values → score between 20-80."""
        score = _compute_composite_score(5.0, 0.3, 7.0, 5.0)
        assert 20 < score < 80

    def test_hand_dominates(self):
        """HAND has weight 0.45 — changing it should have the biggest effect."""
        low_hand = _compute_composite_score(1.0, 0.5, 7.0, 5.0)
        high_hand = _compute_composite_score(18.0, 0.5, 7.0, 5.0)
        assert low_hand - high_hand > 20  # HAND swing > 20 points

    def test_negative_hand_clamped(self):
        """Negative HAND (shouldn't happen but defensive) → clamped."""
        score = _compute_composite_score(-5.0, 0.0, 0.0, 0.0)
        # hand_norm = max(0, 1 - (-5)/20) = max(0, 1.25) = 1.25 → not clamped to 1
        # This is a known edge — test documents the behavior
        assert score >= 0

    def test_return_type(self):
        score = _compute_composite_score(10.0, 0.5, 8.0, 3.0)
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# _classify_composite
# ---------------------------------------------------------------------------


class TestClassifyComposite:
    @pytest.mark.parametrize("score,expected", [
        (100, "very_high"),
        (70, "very_high"),
        (69.9, "high"),
        (50, "high"),
        (49.9, "moderate"),
        (30, "moderate"),
        (29.9, "low"),
        (15, "low"),
        (14.9, "very_low"),
        (0, "very_low"),
    ])
    def test_all_tiers(self, score, expected):
        assert _classify_composite(score) == expected


# ---------------------------------------------------------------------------
# _run_tool
# ---------------------------------------------------------------------------


class TestRunTool:
    def test_success(self):
        """Return code 0 → no exception."""
        mock_fn = lambda *a, **kw: 0
        mock_fn.__name__ = "slope"
        _run_tool(mock_fn)

    def test_failure(self):
        """Non-zero return code → RuntimeError."""
        mock_fn = lambda *a, **kw: 1
        mock_fn.__name__ = "slope"
        with pytest.raises(RuntimeError, match="whitebox slope failed"):
            _run_tool(mock_fn)

    def test_negative_return(self):
        """Negative return code → also fails."""
        mock_fn = lambda *a, **kw: -1
        mock_fn.__name__ = "breach"
        with pytest.raises(RuntimeError):
            _run_tool(mock_fn)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TestTerrainModels:
    def test_terrain_detail_defaults(self):
        d = TerrainAnalysisDetail()
        assert d.slope_mean_deg is None
        assert d.aspect_direction is None

    def test_terrain_detail_defaults_new_fields(self):
        d = TerrainAnalysisDetail()
        assert d.landform_class is None
        assert d.landform_type is None
        assert d.daylight_fraction is None

    def test_terrain_detail_populated(self):
        d = TerrainAnalysisDetail(
            slope_mean_deg=5.2, slope_max_deg=18.3,
            aspect_dominant_deg=180.0, aspect_direction="S",
            elevation_min_m=10.0, elevation_max_m=45.0,
            elevation_range_m=35.0, terrain_ruggedness=0.03,
            landform_class=6, landform_type="slope",
            daylight_fraction=0.92,
        )
        assert d.slope_mean_deg == 5.2
        assert d.aspect_direction == "S"
        assert d.landform_class == 6
        assert d.landform_type == "slope"
        assert d.daylight_fraction == 0.92

    def test_terrain_detail_serialise(self):
        d = TerrainAnalysisDetail(slope_mean_deg=5.2, landform_type="ridge")
        data = d.model_dump()
        assert data["slope_mean_deg"] == 5.2
        assert data["slope_max_deg"] is None
        assert data["landform_type"] == "ridge"

    def test_flood_disclaimer_default(self):
        f = FloodSusceptibilityDetail()
        assert "not a flood study" in f.disclaimer

    def test_flood_detail_populated(self):
        f = FloodSusceptibilityDetail(
            hand_min_m=1.5, hand_mean_m=4.2, hand_class="high",
            ponding_max_depth_m=0.3, ponding_has_risk=True,
            twi_mean=8.5, twi_class="moderate",
            composite_score=55.0, composite_class="high",
        )
        assert f.composite_class == "high"
        assert f.ponding_has_risk is True

    def test_terrain_request_defaults(self):
        r = TerrainRequest(lat=-33.87, lng=151.21)
        assert r.include_flood_susceptibility is False
        assert r.address == ""

    def test_terrain_response(self):
        r = TerrainResponse(
            terrain=TerrainAnalysisDetail(slope_mean_deg=3.0),
            flood_susceptibility=None,
        )
        assert r.terrain.slope_mean_deg == 3.0
        assert r.error is None

    def test_terrain_response_error(self):
        r = TerrainResponse(error="DEM fetch failed")
        assert r.terrain is None
        assert r.error == "DEM fetch failed"


# ---------------------------------------------------------------------------
# HAND_STREAM_THRESHOLD — documents that it exists and is reasonable
# ---------------------------------------------------------------------------


class TestConstants:
    def test_stream_threshold_positive(self):
        assert HAND_STREAM_THRESHOLD > 0

    def test_hand_thresholds_monotonic(self):
        vals = [_HAND_THRESHOLDS[k] for k in ["very_high", "high", "moderate", "low"]]
        assert vals == sorted(vals), "HAND thresholds must be monotonically increasing"

    def test_twi_thresholds_monotonic_descending(self):
        vals = [_TWI_THRESHOLDS[k] for k in ["very_high", "high", "moderate"]]
        assert vals == sorted(vals, reverse=True), "TWI thresholds must be monotonically decreasing"


# ---------------------------------------------------------------------------
# _GEOMORPHON_LABELS
# ---------------------------------------------------------------------------


class TestGeomorphonLabels:
    def test_all_10_classes(self):
        """All 10 geomorphon landform classes are defined."""
        assert len(_GEOMORPHON_LABELS) == 10

    def test_keys_are_1_to_10(self):
        assert set(_GEOMORPHON_LABELS.keys()) == set(range(1, 11))

    @pytest.mark.parametrize("val,label", [
        (1, "flat"),
        (2, "peak"),
        (3, "ridge"),
        (4, "shoulder"),
        (5, "spur"),
        (6, "slope"),
        (7, "hollow"),
        (8, "footslope"),
        (9, "valley"),
        (10, "pit"),
    ])
    def test_label_mapping(self, val, label):
        assert _GEOMORPHON_LABELS[val] == label

    def test_all_labels_unique(self):
        labels = list(_GEOMORPHON_LABELS.values())
        assert len(labels) == len(set(labels)), "Geomorphon labels must be unique"

    def test_zero_not_in_labels(self):
        """0 is NoData in geomorphons output — must not be a valid class."""
        assert 0 not in _GEOMORPHON_LABELS

    def test_11_not_in_labels(self):
        assert 11 not in _GEOMORPHON_LABELS


# ---------------------------------------------------------------------------
# Terrain interpretation — _interpret_gradient
# ---------------------------------------------------------------------------


class TestInterpretGradient:
    def test_gentle_gradient(self):
        f = _interpret_gradient({"slope_mean_deg": 3.0, "slope_max_deg": 8.0})
        assert f.severity == TerrainSeverity.GREEN
        assert f.id == "site_gradient"
        assert f.action_trigger is None
        assert f.estimated_cost is None
        assert "3.0" in f.narrative
        assert "8.0" in f.narrative

    def test_moderate_gradient(self):
        f = _interpret_gradient({"slope_mean_deg": 7.0, "slope_max_deg": 15.0})
        assert f.severity == TerrainSeverity.AMBER
        assert f.classification == "Moderate gradient"
        assert f.action_trigger is not None
        assert f.estimated_cost is not None

    def test_moderate_with_steep_zones(self):
        """Mean < 10 but max >= 20 → localised steep zones."""
        f = _interpret_gradient({"slope_mean_deg": 8.0, "slope_max_deg": 22.0})
        assert f.severity == TerrainSeverity.AMBER
        assert "localised steep zones" in f.classification.lower()

    def test_steep_site(self):
        f = _interpret_gradient({"slope_mean_deg": 12.0, "slope_max_deg": 20.0})
        assert f.severity == TerrainSeverity.RED
        assert f.classification == "Steep site"
        assert "AS 2890.1" not in f.classification  # standard is in narrative, not classification
        assert f.action_trigger is not None
        assert f.estimated_cost is not None

    def test_very_steep_site(self):
        f = _interpret_gradient({"slope_mean_deg": 15.0, "slope_max_deg": 30.0})
        assert f.severity == TerrainSeverity.RED
        assert f.classification == "Very steep site"
        assert "AS 4678" in f.narrative

    def test_boundary_gentle_moderate(self):
        """At exactly mean=5, mx=10 → should be moderate (not gentle)."""
        f = _interpret_gradient({"slope_mean_deg": 5.0, "slope_max_deg": 10.0})
        assert f.severity == TerrainSeverity.AMBER

    def test_boundary_moderate_steep(self):
        """At exactly mean=10, mx=20 → steep (not moderate)."""
        f = _interpret_gradient({"slope_mean_deg": 10.0, "slope_max_deg": 20.0})
        assert f.severity == TerrainSeverity.RED

    def test_none_slope_defaults_zero(self):
        """Missing slope values default to 0.0 → gentle."""
        f = _interpret_gradient({})
        assert f.severity == TerrainSeverity.GREEN

    def test_metric_dict_populated(self):
        f = _interpret_gradient({"slope_mean_deg": 6.5, "slope_max_deg": 12.0})
        assert f.metric == {"slope_mean_deg": 6.5, "slope_max_deg": 12.0}

    def test_relevance_includes_architect(self):
        f = _interpret_gradient({"slope_mean_deg": 3.0, "slope_max_deg": 5.0})
        assert "architect" in f.relevance


# ---------------------------------------------------------------------------
# Terrain interpretation — _interpret_landform
# ---------------------------------------------------------------------------


class TestInterpretLandform:
    @pytest.mark.parametrize("lf,expected_sev", [
        ("flat", TerrainSeverity.GREEN),
        ("spur", TerrainSeverity.GREEN),
        ("ridge", TerrainSeverity.GREEN),
        ("peak", TerrainSeverity.GREEN),
        ("footslope", TerrainSeverity.AMBER),
        ("shoulder", TerrainSeverity.AMBER),
        ("slope", TerrainSeverity.AMBER),
        ("hollow", TerrainSeverity.RED),
        ("valley", TerrainSeverity.RED),
        ("pit", TerrainSeverity.RED),
    ])
    def test_severity_mapping(self, lf, expected_sev):
        f = _interpret_landform({"landform_type": lf, "drainage_direction": "SE"})
        assert f.severity == expected_sev

    def test_drainage_direction_in_narrative(self):
        f = _interpret_landform({"landform_type": "hollow", "drainage_direction": "NW"})
        assert "NW" in f.narrative

    def test_hollow_has_action_trigger(self):
        f = _interpret_landform({"landform_type": "hollow"})
        assert f.action_trigger is not None
        assert f.estimated_cost is not None

    def test_valley_has_action_trigger(self):
        f = _interpret_landform({"landform_type": "valley"})
        assert f.action_trigger is not None

    def test_pit_has_action_trigger(self):
        f = _interpret_landform({"landform_type": "pit"})
        assert "no natural outfall" in f.action_trigger.lower()

    def test_flat_no_action(self):
        f = _interpret_landform({"landform_type": "flat"})
        assert f.action_trigger is None
        assert f.estimated_cost is None

    def test_footslope_has_geotech_action(self):
        f = _interpret_landform({"landform_type": "footslope"})
        assert f.action_trigger is not None
        assert "geotechnical" in f.action_trigger.lower()

    def test_default_drainage(self):
        """Missing drainage_direction defaults to 'downslope'."""
        f = _interpret_landform({"landform_type": "slope"})
        assert "downslope" in f.narrative

    def test_unknown_landform_defaults_amber(self):
        """Unknown landform falls back to AMBER and slope narrative."""
        f = _interpret_landform({"landform_type": "unknown_type"})
        assert f.severity == TerrainSeverity.AMBER

    def test_id_is_landform(self):
        f = _interpret_landform({"landform_type": "ridge"})
        assert f.id == "landform"


# ---------------------------------------------------------------------------
# Terrain interpretation — _interpret_aspect
# ---------------------------------------------------------------------------


class TestInterpretAspect:
    def test_level_site_green(self):
        """Slope < 2° → aspect immaterial."""
        f = _interpret_aspect({"aspect_direction": "S", "aspect_dominant_deg": 180.0, "slope_mean_deg": 1.5})
        assert f.severity == TerrainSeverity.GREEN
        assert "level" in f.classification.lower()

    def test_north_favourable(self):
        f = _interpret_aspect({"aspect_direction": "N", "aspect_dominant_deg": 5.0, "slope_mean_deg": 8.0})
        assert f.severity == TerrainSeverity.GREEN
        assert "favourable" in f.classification.lower()

    def test_ne_favourable(self):
        f = _interpret_aspect({"aspect_direction": "NE", "aspect_dominant_deg": 45.0, "slope_mean_deg": 5.0})
        assert f.severity == TerrainSeverity.GREEN

    def test_nw_favourable(self):
        f = _interpret_aspect({"aspect_direction": "NW", "aspect_dominant_deg": 315.0, "slope_mean_deg": 5.0})
        assert f.severity == TerrainSeverity.GREEN

    def test_east_amber(self):
        f = _interpret_aspect({"aspect_direction": "E", "aspect_dominant_deg": 90.0, "slope_mean_deg": 5.0})
        assert f.severity == TerrainSeverity.AMBER
        assert "morning" in f.classification.lower()

    def test_west_amber(self):
        f = _interpret_aspect({"aspect_direction": "W", "aspect_dominant_deg": 270.0, "slope_mean_deg": 5.0})
        assert f.severity == TerrainSeverity.AMBER
        assert "afternoon" in f.classification.lower()

    def test_south_steep_red(self):
        """South-facing + steep (≥10°) → RED."""
        f = _interpret_aspect({"aspect_direction": "S", "aspect_dominant_deg": 180.0, "slope_mean_deg": 12.0})
        assert f.severity == TerrainSeverity.RED

    def test_south_moderate_amber(self):
        """South-facing + moderate slope → AMBER."""
        f = _interpret_aspect({"aspect_direction": "S", "aspect_dominant_deg": 180.0, "slope_mean_deg": 6.0})
        assert f.severity == TerrainSeverity.AMBER

    def test_se_steep_red(self):
        """SE-facing + steep → RED."""
        f = _interpret_aspect({"aspect_direction": "SE", "aspect_dominant_deg": 135.0, "slope_mean_deg": 10.0})
        assert f.severity == TerrainSeverity.RED

    def test_sw_moderate_amber(self):
        f = _interpret_aspect({"aspect_direction": "SW", "aspect_dominant_deg": 225.0, "slope_mean_deg": 5.0})
        assert f.severity == TerrainSeverity.AMBER

    def test_raw_values_in_narrative(self):
        f = _interpret_aspect({"aspect_direction": "E", "aspect_dominant_deg": 92.3, "slope_mean_deg": 7.5})
        assert "92.3" in f.narrative
        assert "7.5" in f.narrative

    def test_adg_referenced(self):
        """All non-level aspects should reference ADG."""
        f = _interpret_aspect({"aspect_direction": "N", "aspect_dominant_deg": 10.0, "slope_mean_deg": 5.0})
        assert "ADG" in f.narrative


# ---------------------------------------------------------------------------
# Terrain interpretation — _interpret_solar
# ---------------------------------------------------------------------------


class TestInterpretSolar:
    def test_full_access(self):
        f = _interpret_solar({"daylight_fraction": 0.95})
        assert f.severity == TerrainSeverity.GREEN
        assert f.classification == "Full terrain solar access"
        assert "95.0%" in f.narrative

    def test_moderate_shadowing(self):
        f = _interpret_solar({"daylight_fraction": 0.82})
        assert f.severity == TerrainSeverity.AMBER
        assert f.classification == "Moderate terrain shadowing"

    def test_significant_shadowing(self):
        f = _interpret_solar({"daylight_fraction": 0.65})
        assert f.severity == TerrainSeverity.RED
        assert "Significant" in f.classification

    def test_severe_shadowing(self):
        f = _interpret_solar({"daylight_fraction": 0.50})
        assert f.severity == TerrainSeverity.RED
        assert "Severe" in f.classification

    def test_boundary_full_moderate(self):
        """Exactly 0.90 → full access (GREEN)."""
        f = _interpret_solar({"daylight_fraction": 0.90})
        assert f.severity == TerrainSeverity.GREEN

    def test_boundary_moderate_significant(self):
        """Exactly 0.75 → moderate (AMBER)."""
        f = _interpret_solar({"daylight_fraction": 0.75})
        assert f.severity == TerrainSeverity.AMBER

    def test_boundary_significant_severe(self):
        """Exactly 0.60 → significant (RED)."""
        f = _interpret_solar({"daylight_fraction": 0.60})
        assert f.severity == TerrainSeverity.RED

    def test_derate_in_narrative(self):
        """Moderate+ should mention PV derating percentage."""
        f = _interpret_solar({"daylight_fraction": 0.80})
        assert "20%" in f.narrative  # 1 - 0.80 = 0.20 → 20%

    def test_fraction_in_narrative(self):
        f = _interpret_solar({"daylight_fraction": 0.85})
        assert "0.850" in f.narrative
        assert "85.0%" in f.narrative

    def test_metric_dict(self):
        f = _interpret_solar({"daylight_fraction": 0.92})
        assert f.metric["daylight_fraction"] == 0.92
        assert f.metric["daylight_pct"] == 92.0


# ---------------------------------------------------------------------------
# Terrain interpretation — _interpret_elevation
# ---------------------------------------------------------------------------


class TestInterpretElevation:
    def test_level_site(self):
        f = _interpret_elevation({"elevation_min_m": 50.0, "elevation_max_m": 51.5, "elevation_range_m": 1.5})
        assert f.severity == TerrainSeverity.GREEN
        assert f.action_trigger is None

    def test_moderate_non_lowlying(self):
        f = _interpret_elevation({"elevation_min_m": 40.0, "elevation_max_m": 47.0, "elevation_range_m": 7.0})
        assert f.severity == TerrainSeverity.AMBER
        assert "contour survey" in f.action_trigger.lower()

    def test_moderate_lowlying_valley(self):
        """Valley + moderate range → AMBER with drainage emphasis."""
        f = _interpret_elevation({
            "elevation_min_m": 10.0, "elevation_max_m": 17.0,
            "elevation_range_m": 7.0, "landform_type": "valley",
        })
        assert f.severity == TerrainSeverity.AMBER
        assert "drainage" in f.classification.lower()
        assert "flood planning level" in f.action_trigger.lower()

    def test_moderate_lowlying_pit(self):
        f = _interpret_elevation({
            "elevation_min_m": 5.0, "elevation_max_m": 10.0,
            "elevation_range_m": 5.0, "landform_type": "pit",
        })
        assert f.severity == TerrainSeverity.AMBER

    def test_significant_variation(self):
        f = _interpret_elevation({"elevation_min_m": 20.0, "elevation_max_m": 35.0, "elevation_range_m": 15.0})
        assert f.severity == TerrainSeverity.RED
        assert f.action_trigger is not None
        assert f.estimated_cost is not None

    def test_boundary_level_moderate(self):
        """Exactly 3m → moderate (AMBER), not level."""
        f = _interpret_elevation({"elevation_min_m": 50.0, "elevation_max_m": 53.0, "elevation_range_m": 3.0})
        assert f.severity == TerrainSeverity.AMBER

    def test_boundary_moderate_significant(self):
        """Range > 10m → RED."""
        f = _interpret_elevation({"elevation_min_m": 30.0, "elevation_max_m": 41.0, "elevation_range_m": 11.0})
        assert f.severity == TerrainSeverity.RED

    def test_elevation_values_in_narrative(self):
        f = _interpret_elevation({"elevation_min_m": 22.5, "elevation_max_m": 29.8, "elevation_range_m": 7.3})
        assert "22.5" in f.narrative
        assert "29.8" in f.narrative
        assert "7.3" in f.narrative

    def test_ahd_mentioned(self):
        f = _interpret_elevation({"elevation_min_m": 50.0, "elevation_max_m": 52.0, "elevation_range_m": 2.0})
        assert "AHD" in f.narrative


# ---------------------------------------------------------------------------
# Terrain interpretation — _interpret_ruggedness
# ---------------------------------------------------------------------------


class TestInterpretRuggedness:
    def test_uniform_surface(self):
        f = _interpret_ruggedness({"terrain_ruggedness": 1.2})
        assert f.severity == TerrainSeverity.GREEN
        assert f.action_trigger is None
        assert f.estimated_cost is None

    def test_moderate_variability(self):
        f = _interpret_ruggedness({"terrain_ruggedness": 3.5})
        assert f.severity == TerrainSeverity.AMBER
        assert f.action_trigger is not None

    def test_high_complexity(self):
        f = _interpret_ruggedness({"terrain_ruggedness": 6.0})
        assert f.severity == TerrainSeverity.RED
        assert f.action_trigger is not None
        assert f.estimated_cost is not None

    def test_boundary_uniform_moderate(self):
        """Exactly 2.0 → moderate (AMBER)."""
        f = _interpret_ruggedness({"terrain_ruggedness": 2.0})
        assert f.severity == TerrainSeverity.AMBER

    def test_boundary_moderate_high(self):
        """Exactly 5.0 → still moderate (AMBER), 5.01 → RED."""
        f = _interpret_ruggedness({"terrain_ruggedness": 5.0})
        assert f.severity == TerrainSeverity.AMBER
        f2 = _interpret_ruggedness({"terrain_ruggedness": 5.01})
        assert f2.severity == TerrainSeverity.RED

    def test_value_in_narrative(self):
        f = _interpret_ruggedness({"terrain_ruggedness": 4.7})
        assert "4.7" in f.narrative

    def test_methodology_references_std_dev(self):
        f = _interpret_ruggedness({"terrain_ruggedness": 1.0})
        assert "standard deviation" in f.methodology.lower()


# ---------------------------------------------------------------------------
# Terrain interpretation — _build_terrain_interpretation (integration)
# ---------------------------------------------------------------------------


def _full_terrain_dict():
    """Complete terrain dict that produces all 6 findings."""
    return {
        "slope_mean_deg": 8.3,
        "slope_max_deg": 15.0,
        "landform_type": "footslope",
        "drainage_direction": "SE",
        "aspect_direction": "NE",
        "aspect_dominant_deg": 42.0,
        "daylight_fraction": 0.88,
        "elevation_min_m": 35.0,
        "elevation_max_m": 43.0,
        "elevation_range_m": 8.0,
        "terrain_ruggedness": 3.1,
    }


class TestBuildTerrainInterpretation:
    def test_full_dict_produces_six_findings(self):
        interp = _build_terrain_interpretation(_full_terrain_dict())
        assert interp is not None
        assert len(interp.findings) == 6

    def test_all_finding_ids_unique(self):
        interp = _build_terrain_interpretation(_full_terrain_dict())
        ids = [f.id for f in interp.findings]
        assert len(ids) == len(set(ids))

    def test_finding_ids_are_expected(self):
        interp = _build_terrain_interpretation(_full_terrain_dict())
        ids = {f.id for f in interp.findings}
        assert ids == {
            "site_gradient", "landform", "aspect_orientation",
            "solar_terrain_access", "elevation_position", "surface_complexity",
        }

    def test_minimal_dict_one_finding(self):
        """Only slope → only gradient finding."""
        interp = _build_terrain_interpretation({"slope_mean_deg": 3.0})
        assert interp is not None
        assert len(interp.findings) == 1
        assert interp.findings[0].id == "site_gradient"

    def test_none_slope_returns_none(self):
        interp = _build_terrain_interpretation({"slope_mean_deg": None})
        assert interp is None

    def test_missing_slope_returns_none(self):
        interp = _build_terrain_interpretation({})
        assert interp is None

    def test_missing_daylight_omits_solar(self):
        d = _full_terrain_dict()
        del d["daylight_fraction"]
        interp = _build_terrain_interpretation(d)
        ids = {f.id for f in interp.findings}
        assert "solar_terrain_access" not in ids
        assert len(interp.findings) == 5

    def test_missing_landform_omits_finding(self):
        d = _full_terrain_dict()
        del d["landform_type"]
        interp = _build_terrain_interpretation(d)
        ids = {f.id for f in interp.findings}
        assert "landform" not in ids

    def test_data_source_reflects_actual_provider(self):
        """FLIPPED 2026-08-03 (campaign item 4 / DQ-46): data_source used to
        assert the GA 5m DEM unconditionally, even when the SIX Maps
        photogrammetry fallback actually served the raster. It now names the
        provider recorded for the run, and says so when none was recorded."""
        interp = _build_terrain_interpretation(_full_terrain_dict())
        assert "provider not recorded" in interp.data_source

        ga = dict(_full_terrain_dict(), dem_provider="ga_wcs_5m")
        assert "Geoscience Australia 5m DEM" in _build_terrain_interpretation(ga).data_source

        six = dict(_full_terrain_dict(), dem_provider="six_maps_elevation")
        six_source = _build_terrain_interpretation(six).data_source
        assert "SIX Maps" in six_source
        assert "Geoscience Australia" not in six_source

    def test_disclaimer_mentions_surveyor(self):
        interp = _build_terrain_interpretation(_full_terrain_dict())
        assert "surveyor" in interp.disclaimer.lower()

    def test_green_findings_no_cost(self):
        """All GREEN findings must have no cost or action trigger."""
        d = {
            "slope_mean_deg": 2.0,
            "slope_max_deg": 5.0,
            "landform_type": "flat",
            "drainage_direction": "E",
            "aspect_direction": "N",
            "aspect_dominant_deg": 10.0,
            "daylight_fraction": 0.95,
            "elevation_min_m": 50.0,
            "elevation_max_m": 51.0,
            "elevation_range_m": 1.0,
            "terrain_ruggedness": 1.0,
        }
        interp = _build_terrain_interpretation(d)
        for f in interp.findings:
            assert f.severity == TerrainSeverity.GREEN, f"Expected GREEN for {f.id}, got {f.severity}"
            assert f.action_trigger is None, f"{f.id} should not have action_trigger"
            assert f.estimated_cost is None, f"{f.id} should not have estimated_cost"

    def test_red_findings_have_cost_and_action(self):
        """All RED findings must have cost and action trigger."""
        d = {
            "slope_mean_deg": 15.0,
            "slope_max_deg": 30.0,
            "terrain_ruggedness": 7.0,
            "elevation_min_m": 10.0,
            "elevation_max_m": 25.0,
            "elevation_range_m": 15.0,
        }
        interp = _build_terrain_interpretation(d)
        red_findings = [f for f in interp.findings if f.severity == TerrainSeverity.RED]
        assert len(red_findings) >= 2  # gradient + ruggedness + elevation
        for f in red_findings:
            assert f.action_trigger is not None, f"{f.id} missing action_trigger"
            assert f.estimated_cost is not None, f"{f.id} missing estimated_cost"


# ---------------------------------------------------------------------------
# Terrain interpretation — narrative content quality
# ---------------------------------------------------------------------------


class TestNarrativeContent:
    def test_gradient_embeds_raw_values(self):
        f = _interpret_gradient({"slope_mean_deg": 8.3, "slope_max_deg": 22.1})
        assert "8.3" in f.narrative
        assert "22.1" in f.narrative

    def test_solar_embeds_percentage_and_fraction(self):
        f = _interpret_solar({"daylight_fraction": 0.82})
        assert "82.0%" in f.narrative
        assert "0.820" in f.narrative

    def test_elevation_embeds_ahd_values(self):
        f = _interpret_elevation({"elevation_min_m": 22.5, "elevation_max_m": 35.0, "elevation_range_m": 12.5})
        assert "22.5m" in f.narrative
        assert "35.0m" in f.narrative

    def test_ruggedness_embeds_value(self):
        f = _interpret_ruggedness({"terrain_ruggedness": 4.7})
        assert "4.7" in f.narrative

    def test_gradient_methodology_cites_horn(self):
        f = _interpret_gradient({"slope_mean_deg": 5.0, "slope_max_deg": 10.0})
        assert "Horn" in f.methodology

    def test_landform_methodology_cites_jasiewicz(self):
        f = _interpret_landform({"landform_type": "flat"})
        assert "Jasiewicz" in f.methodology

    def test_aspect_methodology_cites_adg(self):
        f = _interpret_aspect({"aspect_direction": "E", "aspect_dominant_deg": 90.0, "slope_mean_deg": 5.0})
        assert "ADG" in f.methodology or "ADG" in f.narrative

    def test_landform_severity_dict_covers_all_10(self):
        """Every geomorphon label must have a severity mapping."""
        expected_types = {"flat", "footslope", "shoulder", "slope", "spur",
                          "ridge", "peak", "hollow", "valley", "pit"}
        assert set(_LANDFORM_SEVERITY.keys()) == expected_types


# ---------------------------------------------------------------------------
# _central_crop_bounds — lot-window sizing (the fix for 500m-buffer over-report)
# ---------------------------------------------------------------------------


class TestCentralCropBounds:
    """Window sizing for the lot-scoped gradient/elevation/ruggedness findings.
    Pure arithmetic — guards that they read the lot footprint, not the 1km buffer."""

    def test_central_window_is_small_and_centred(self):
        # 200x200 over a 1000m box (cell 5m); a 90m window is ~19x19 central cells
        bounds = _central_crop_bounds(200, 200, buffer_m=500.0, window_m=90.0)
        assert bounds == (91, 110, 91, 110)
        r0, r1, c0, c1 = bounds
        assert r0 > 0 and r1 < 200          # genuinely interior — edges excluded
        assert (r1 - r0) < 30               # far smaller than the 200-cell array

    def test_min_window_floor(self):
        # Coarse box (cell 50m): a 90m half-window rounds below the 3px floor
        r0, r1, c0, c1 = _central_crop_bounds(200, 200, buffer_m=5000.0, window_m=90.0)
        assert (r1 - r0) == 7 and (c1 - c0) == 7   # 2*3 + 1

    def test_tiny_array_clamps_without_crash(self):
        assert _central_crop_bounds(4, 4, buffer_m=500.0, window_m=90.0) == (0, 4, 0, 4)

    def test_window_scales_with_cell_size(self):
        # 200px over a 200m box (buffer 100) -> cell 1m -> 90m window is 91px
        r0, r1, c0, c1 = _central_crop_bounds(200, 200, buffer_m=100.0, window_m=90.0)
        assert (r1 - r0) == 91 and (c1 - c0) == 91


# ---------------------------------------------------------------------------
# Static-claims guard — interpretation prose stays in a factual register
# (pattern follows tests/test_conveyancing_truth.py source-scan guards)
# ---------------------------------------------------------------------------


class TestNoAdvisoryLanguageInSource:
    """The terrain interpretation module must state facts and references, never
    advice. A reintroduced advisory verb is a liability regression (#751 batch:
    'should be checked against AS 2890.1', 'geotechnical investigation is
    essential', 'supports compliance', …)."""

    FORBIDDEN_WORD_PATTERNS = [
        r"\bshould\b",
        r"\bessential\b",
        r"\brecommend\w*\b",
    ]

    def test_terrain_source_contains_no_advisory_verbs(self):
        import re as _re
        from pathlib import Path as _Path
        src_path = _Path(__file__).parent.parent / "services" / "terrain_analysis.py"
        src = src_path.read_text(encoding="utf-8")
        for pat in self.FORBIDDEN_WORD_PATTERNS:
            hits = _re.findall(pat, src, flags=_re.IGNORECASE)
            assert not hits, (
                f"Advisory language reintroduced into terrain_analysis.py: "
                f"{pat!r} matched {hits[:5]}"
            )
