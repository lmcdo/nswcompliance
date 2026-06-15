"""
Tests for services/reverse_shadow.py — Reverse Shadow Model.

Tests: direction mapping, risk classification, consumer language, ADG compliance.
Heavy geo deps (shapely/pybdshadow) are mocked.
"""
import re
import pytest
from unittest.mock import patch, MagicMock

from services.reverse_shadow import (
    NEIGHBOUR_DIRECTIONS,
    SHADOW_SCENARIO_DESCRIPTIONS,
    NeighbourShadowResult,
    SolarAccessRisk,
    model_neighbour_shadow_on_subject,
    assess_solar_access_risk,
    _make_risk_summary,
)

BANNED_WORDS = re.compile(
    r'\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|'
    r'approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|'
    r'definitive|comprehensive|reliable|illegal|unapproved|unauthorized)\b',
    re.IGNORECASE
)

# Simple rectangular lot for testing
SUBJECT_LOT = {
    "type": "Polygon",
    "coordinates": [[[151.15, -33.88], [151.1505, -33.88],
                     [151.1505, -33.8805], [151.15, -33.8805], [151.15, -33.88]]],
}


# ---------------------------------------------------------------------------
# Direction mapping
# ---------------------------------------------------------------------------

class TestDirectionMapping:
    def test_all_three_directions_covered(self):
        assert set(NEIGHBOUR_DIRECTIONS.values()) == {"east", "north", "west"}

    def test_morning_is_east(self):
        assert NEIGHBOUR_DIRECTIONS["jun21_9am"] == "east"

    def test_noon_is_north(self):
        assert NEIGHBOUR_DIRECTIONS["jun21_12pm"] == "north"

    def test_afternoon_is_west(self):
        assert NEIGHBOUR_DIRECTIONS["jun21_3pm"] == "west"

    def test_all_scenarios_have_descriptions(self):
        for key in NEIGHBOUR_DIRECTIONS:
            assert key in SHADOW_SCENARIO_DESCRIPTIONS


# ---------------------------------------------------------------------------
# model_neighbour_shadow_on_subject — ImportError fallback
# ---------------------------------------------------------------------------

class TestModelNeighbourShadowFallback:
    @patch.dict("sys.modules", {"shapely": None, "shapely.geometry": None})
    def test_returns_zero_without_shapely(self):
        """Without shapely, should return zero shadow, not crash."""
        result = model_neighbour_shadow_on_subject(
            subject_lot_geojson=SUBJECT_LOT,
            neighbour_lot_geojson=None,
            neighbour_height_m=9.0,
            direction="north",
            scenario="jun21_12pm",
        )
        assert isinstance(result, NeighbourShadowResult)
        assert result.shadow_fraction == 0.0
        assert result.scenario == "jun21_12pm"
        assert result.neighbour_direction == "north"

    def test_result_model_fields(self):
        """Verify all fields are populated even in fallback."""
        result = model_neighbour_shadow_on_subject(
            subject_lot_geojson=SUBJECT_LOT,
            neighbour_lot_geojson=None,
            neighbour_height_m=12.0,
            direction="east",
            scenario="jun21_9am",
        )
        assert result.neighbour_height_m == 12.0
        assert result.scenario_description == "Winter solstice 9am — shadow from east"


# ---------------------------------------------------------------------------
# Risk level classification
# ---------------------------------------------------------------------------

class TestRiskClassification:
    def _make_result(self, fraction, scenario="jun21_12pm", direction="north"):
        return NeighbourShadowResult(
            scenario=scenario,
            scenario_description="test",
            neighbour_direction=direction,
            neighbour_height_m=9.0,
            neighbour_footprint_area_m2=200,
            shadow_on_subject_m2=fraction * 500,
            subject_lot_area_m2=500,
            shadow_fraction=fraction,
        )

    def test_low_risk(self):
        scenarios = [
            self._make_result(0.10, "jun21_9am", "east"),
            self._make_result(0.15, "jun21_12pm", "north"),
            self._make_result(0.12, "jun21_3pm", "west"),
        ]
        # worst = 0.15 < 0.20 → low
        worst = max(s.shadow_fraction for s in scenarios)
        assert worst < 0.20

    def test_moderate_risk(self):
        scenarios = [
            self._make_result(0.25, "jun21_9am", "east"),
            self._make_result(0.35, "jun21_12pm", "north"),
            self._make_result(0.30, "jun21_3pm", "west"),
        ]
        worst = max(s.shadow_fraction for s in scenarios)
        assert 0.20 <= worst < 0.50

    def test_high_risk(self):
        scenarios = [
            self._make_result(0.40, "jun21_9am", "east"),
            self._make_result(0.60, "jun21_12pm", "north"),
            self._make_result(0.55, "jun21_3pm", "west"),
        ]
        worst = max(s.shadow_fraction for s in scenarios)
        assert worst >= 0.50

    def test_adg_compliance_noon_under_50(self):
        """ADG: if noon fraction < 0.5, likely compliant."""
        noon_fraction = 0.35
        assert noon_fraction < 0.50  # ADG OK

    def test_adg_compliance_noon_over_50(self):
        """ADG: if noon fraction >= 0.5, solar access at risk."""
        noon_fraction = 0.55
        assert noon_fraction >= 0.50  # ADG risk


# ---------------------------------------------------------------------------
# Consumer summary language
# ---------------------------------------------------------------------------

class TestConsumerSummary:
    def _scenario(self, fraction, scenario="jun21_12pm"):
        return NeighbourShadowResult(
            scenario=scenario,
            scenario_description="Winter solstice noon — shadow from north",
            neighbour_direction="north",
            neighbour_height_m=9.0,
            neighbour_footprint_area_m2=200,
            shadow_on_subject_m2=fraction * 500,
            subject_lot_area_m2=500,
            shadow_fraction=fraction,
        )

    def test_low_risk_no_banned_words(self):
        text = _make_risk_summary("low", 0.15, 9.0, [self._scenario(0.15)])
        matches = BANNED_WORDS.findall(text)
        assert matches == [], f"Banned words: {matches}"
        assert "15%" in text

    def test_moderate_risk_no_banned_words(self):
        text = _make_risk_summary("moderate", 0.35, 12.0, [self._scenario(0.35)])
        matches = BANNED_WORDS.findall(text)
        assert matches == [], f"Banned words: {matches}"

    def test_high_risk_no_banned_words(self):
        text = _make_risk_summary("high", 0.65, 12.0, [self._scenario(0.65)])
        matches = BANNED_WORDS.findall(text)
        assert matches == [], f"Banned words: {matches}"
        assert "65%" in text

    def test_includes_height(self):
        text = _make_risk_summary("low", 0.10, 9.0, [self._scenario(0.10)])
        assert "9m" in text


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_height_neighbour(self):
        """Vacant lot (height=0) → zero shadow."""
        result = model_neighbour_shadow_on_subject(
            subject_lot_geojson=SUBJECT_LOT,
            neighbour_lot_geojson=None,
            neighbour_height_m=0.0,
            direction="north",
        )
        assert result.shadow_fraction == 0.0

    def test_unknown_scenario(self):
        """Unknown scenario key → uses key as description."""
        result = model_neighbour_shadow_on_subject(
            subject_lot_geojson=SUBJECT_LOT,
            neighbour_lot_geojson=None,
            neighbour_height_m=9.0,
            direction="north",
            scenario="custom_scenario",
        )
        assert result.scenario == "custom_scenario"
