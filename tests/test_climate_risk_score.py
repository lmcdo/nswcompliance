"""Adversarial unit tests for climate_risk_score.py.

Pattern: same as test_flood_truth.py — test all pure-logic functions without
network/DB. Mock spatial overlay queries and NARCliM data.

Coverage targets:
- Normalization functions: boundary values, empty inputs, null traps
- Interaction bonus: all pair combinations, no-hazard edge case
- Score banding: boundary values (20, 40, 60, 80)
- Composite calculation: zero exposure, max exposure, partial exposure
- to_dict serialization
"""

import pytest
from unittest.mock import patch, MagicMock

# Import the module under test — handle both import paths
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.climate_risk_score import (
    _normalize_flood,
    _normalize_bushfire,
    _normalize_coastal,
    _normalize_fire_history,
    _normalize_landslide,
    _normalize_heat,
    _compute_interaction_bonus,
    _score_to_band,
    ClimateRiskResult,
    HazardScore,
    WEIGHTS,
    INTERACTION_PAIRS,
)

_RFS = "services.climate_risk_score._query_rfs_bfpl"


# ── _score_to_band ───────────────────────────────────────────────────────────

class TestScoreToBand:
    def test_low_floor(self):
        assert _score_to_band(1) == "Low"

    def test_low_ceiling(self):
        assert _score_to_band(20) == "Low"

    def test_moderate_floor(self):
        assert _score_to_band(21) == "Moderate"

    def test_moderate_ceiling(self):
        assert _score_to_band(40) == "Moderate"

    def test_high_floor(self):
        assert _score_to_band(41) == "High"

    def test_high_ceiling(self):
        assert _score_to_band(60) == "High"

    def test_very_high_floor(self):
        assert _score_to_band(61) == "Very High"

    def test_very_high_ceiling(self):
        assert _score_to_band(80) == "Very High"

    def test_extreme_floor(self):
        assert _score_to_band(81) == "Extreme"

    def test_extreme_ceiling(self):
        assert _score_to_band(100) == "Extreme"


# ── _normalize_flood ──────────────────────────────────────────────────────────

class TestNormalizeFlood:
    def test_no_flood_overlay(self):
        h = _normalize_flood({})
        assert h.present is False
        assert h.raw_score == 0.0
        assert h.weighted_score == 0.0
        assert h.confidence == "high"

    def test_flood_present(self):
        h = _normalize_flood({"flood": [{"layer_type": "flood", "value": "Flood Planning"}]})
        assert h.present is True
        assert h.raw_score == 1.0
        assert h.weighted_score == WEIGHTS["flood"]

    def test_flood_empty_list(self):
        """Empty list for flood layer = not present."""
        h = _normalize_flood({"flood": []})
        assert h.present is False
        assert h.raw_score == 0.0

    def test_flood_multiple_hits(self):
        """Multiple flood polygons — still binary (present/not)."""
        h = _normalize_flood({"flood": [{"value": "a"}, {"value": "b"}]})
        assert h.present is True
        assert h.raw_score == 1.0  # Binary, not additive

    def test_other_layers_ignored(self):
        """Other layer types in the dict should not affect flood score."""
        h = _normalize_flood({"bushfire": [{"value": "cat1"}]})
        assert h.present is False


# ── _normalize_bushfire ───────────────────────────────────────────────────────

class TestNormalizeBushfire:
    def test_not_bushfire_prone(self):
        h = _normalize_bushfire({})
        assert h.present is False
        assert h.raw_score == 0.0

    def test_bushfire_prone(self):
        h = _normalize_bushfire({"bushfire": [{"value": "Vegetation Category 1"}]})
        assert h.present is True
        assert h.raw_score == 1.0

    def test_bushfire_empty_list(self):
        h = _normalize_bushfire({"bushfire": []})
        assert h.present is False


# ── _normalize_coastal ────────────────────────────────────────────────────────

class TestNormalizeCoastal:
    def test_no_coastal_layers(self):
        h = _normalize_coastal({})
        assert h.present is False
        assert h.raw_score == 0.0

    def test_single_hazard_layer(self):
        h = _normalize_coastal({"coastal_wetlands": [{"value": "x"}]})
        assert h.present is True
        assert h.raw_score == pytest.approx(1.0 / 3.0, abs=0.01)

    def test_three_or_more_layers_caps_at_1(self):
        overlays = {
            "coastal_wetlands": [{"value": "x"}],
            "littoral_rainforest": [{"value": "x"}],
            "coastal_environment_area": [{"value": "x"}],
            "coastal_use_area": [{"value": "x"}],
        }
        h = _normalize_coastal(overlays)
        assert h.raw_score == 1.0  # Capped at 1.0

    def test_land_application_excluded(self):
        """coastal_land_application with 'Land Application' value is jurisdictional, not a hazard."""
        h = _normalize_coastal({
            "coastal_land_application": [{"value": "Land Application"}]
        })
        assert h.present is False
        assert h.raw_score == 0.0

    def test_land_application_subject_land_included(self):
        """'Subject Land' value IS a specific coastal hazard designation."""
        h = _normalize_coastal({
            "coastal_land_application": [{"value": "Subject Land"}]
        })
        assert h.present is True
        assert h.raw_score > 0.0

    def test_land_application_whitespace(self):
        """Value with trailing whitespace should still match."""
        h = _normalize_coastal({
            "coastal_land_application": [{"value": "  Subject Land  "}]
        })
        assert h.present is True

    def test_empty_value_string(self):
        """Empty string value in coastal_land_application — not 'Subject Land'."""
        h = _normalize_coastal({
            "coastal_land_application": [{"value": ""}]
        })
        assert h.present is False


# ── _normalize_fire_history ───────────────────────────────────────────────────

class TestNormalizeFireHistory:
    def test_no_fire_history(self):
        h = _normalize_fire_history({})
        assert h.present is False
        assert h.raw_score == 0.0

    def test_one_fire_event(self):
        h = _normalize_fire_history({"fire_history": [{"value": "2019"}]})
        assert h.present is True
        assert h.raw_score == pytest.approx(0.3)

    def test_two_fire_events(self):
        h = _normalize_fire_history({"fire_history": [{"value": "2019"}, {"value": "2013"}]})
        assert h.raw_score == pytest.approx(0.6)

    def test_three_fire_events_caps_at_1(self):
        h = _normalize_fire_history({"fire_history": [{"value": "a"}, {"value": "b"}, {"value": "c"}]})
        assert h.raw_score == pytest.approx(0.9)

    def test_four_fire_events_caps_at_1(self):
        h = _normalize_fire_history({"fire_history": [{"value": "a"}] * 4})
        assert h.raw_score == 1.0  # Capped at 1.0

    def test_empty_fire_history_list(self):
        h = _normalize_fire_history({"fire_history": []})
        assert h.present is False


# ── _normalize_heat ───────────────────────────────────────────────────────────

class TestNormalizeHeat:
    def test_no_narclim_data(self):
        h = _normalize_heat({})
        assert h.present is False
        assert h.raw_score == 0.0
        assert h.confidence == "low"

    def test_zero_delta(self):
        h = _normalize_heat({"hot_days_delta_2090": 0.0, "hot_days_baseline": 10, "hot_days_late_century_high": 10})
        assert h.present is False
        assert h.raw_score == 0.0

    def test_moderate_delta(self):
        h = _normalize_heat({"hot_days_delta_2090": 20.0, "hot_days_baseline": 10, "hot_days_late_century_high": 30})
        assert h.present is True
        assert h.raw_score == pytest.approx(20.0 / 45.0, abs=0.01)

    def test_max_delta(self):
        h = _normalize_heat({"hot_days_delta_2090": 45.0, "hot_days_baseline": 10, "hot_days_late_century_high": 55})
        assert h.raw_score == 1.0

    def test_exceeds_max_caps_at_1(self):
        h = _normalize_heat({"hot_days_delta_2090": 60.0, "hot_days_baseline": 5, "hot_days_late_century_high": 65})
        assert h.raw_score == 1.0  # Capped

    def test_negative_delta(self):
        """Negative delta (cooling) should clamp to 0."""
        h = _normalize_heat({"hot_days_delta_2090": -5.0, "hot_days_baseline": 15, "hot_days_late_century_high": 10})
        assert h.raw_score == 0.0

    def test_delta_none_explicitly(self):
        h = _normalize_heat({"hot_days_delta_2090": None})
        assert h.present is False
        assert h.confidence == "low"

    def test_confidence_is_medium(self):
        """NARCliM projections are model-dependent — confidence is medium, not high."""
        h = _normalize_heat({"hot_days_delta_2090": 20.0, "hot_days_baseline": 10, "hot_days_late_century_high": 30})
        assert h.confidence == "medium"


# ── _compute_interaction_bonus ────────────────────────────────────────────────

class TestInteractionBonus:
    def _make_hazard(self, name: str, present: bool) -> HazardScore:
        return HazardScore(
            hazard=name, raw_score=1.0 if present else 0.0,
            weight=0.2, weighted_score=0.2 if present else 0.0,
            present=present, detail="", confidence="high", data_source=""
        )

    def test_no_hazards_present(self):
        hazards = [self._make_hazard(h, False) for h in ["flood", "bushfire", "coastal", "fire_history", "heat"]]
        assert _compute_interaction_bonus(hazards) == 0.0

    def test_bushfire_and_fire_history(self):
        hazards = [
            self._make_hazard("bushfire", True),
            self._make_hazard("fire_history", True),
            self._make_hazard("flood", False),
            self._make_hazard("coastal", False),
            self._make_hazard("heat", False),
        ]
        assert _compute_interaction_bonus(hazards) == 0.05

    def test_all_hazards_present(self):
        hazards = [self._make_hazard(h, True) for h in ["flood", "bushfire", "coastal", "fire_history", "heat"]]
        bonus = _compute_interaction_bonus(hazards)
        # All 4 pairs should fire: bushfire+fire_history(0.05) + flood+coastal(0.05)
        # + bushfire+heat(0.05) + flood+heat(0.03) = 0.18
        assert bonus == pytest.approx(0.18)

    def test_single_hazard_no_bonus(self):
        hazards = [
            self._make_hazard("flood", True),
            self._make_hazard("bushfire", False),
            self._make_hazard("coastal", False),
            self._make_hazard("fire_history", False),
            self._make_hazard("heat", False),
        ]
        assert _compute_interaction_bonus(hazards) == 0.0

    def test_flood_and_coastal(self):
        hazards = [
            self._make_hazard("flood", True),
            self._make_hazard("coastal", True),
            self._make_hazard("bushfire", False),
            self._make_hazard("fire_history", False),
            self._make_hazard("heat", False),
        ]
        assert _compute_interaction_bonus(hazards) == 0.05


# ── ClimateRiskResult.to_dict ─────────────────────────────────────────────────

class TestClimateRiskResultSerialization:
    def test_to_dict_structure(self):
        result = ClimateRiskResult(
            score=42,
            band="High",
            lat=-33.87,
            lng=151.21,
            hazards=[
                HazardScore(
                    hazard="flood", raw_score=1.0, weight=0.2,
                    weighted_score=0.2, present=True, detail="Flood: Yes",
                    confidence="high", data_source="NSW Planning Portal"
                )
            ],
            interaction_bonus=0.0,
        )
        d = result.to_dict()
        assert d["lat"] == -33.87
        assert d["lng"] == 151.21
        assert len(d["hazards"]) == 1
        assert d["hazards"][0]["hazard"] == "flood"
        assert d["hazards"][0]["present"] is True
        assert "methodology_version" in d
        assert "disclaimer" in d
        # The composite still computes on the object — it is the model.
        assert result.score == 42
        assert result.band == "High"
        assert result.hazards[0].weighted_score == 0.2

    def test_to_dict_omits_the_unvalidatable_composite(self):
        """The composite model must not cross the serialisation boundary.

        It cannot be validated against any available reference and #699 bars it
        from every customer surface, yet it reached the API response because
        ``climate_risk_pipeline`` spreads ``**to_dict()``. This test is the pin:
        if it fails, someone has re-opened that leak.

        Falsifiable: re-adding any one of these keys to ``to_dict`` fails here.
        """
        result = ClimateRiskResult(
            score=42, band="High", lat=-33.87, lng=151.21,
            hazards=[
                HazardScore(
                    hazard="flood", raw_score=1.0, weight=0.2,
                    weighted_score=0.2, present=True, detail="Flood: Yes",
                    confidence="high", data_source="NSW Planning Portal",
                    confidence_reason="spatial overlay hit",
                )
            ],
            interaction_bonus=0.05,
        )
        d = result.to_dict()

        for banned in ("score", "band", "interaction_bonus"):
            assert banned not in d, f"{banned} must not be serialised"
        for banned in ("raw_score", "weight", "weighted_score"):
            assert banned not in d["hazards"][0], (
                f"per-hazard {banned} must not be serialised — weight and "
                f"weighted_score make the composite reconstructible"
            )

        # What a consumer legitimately gets: the factual per-hazard exposure.
        assert set(d["hazards"][0]) == {
            "hazard", "present", "detail", "confidence",
            "confidence_reason", "data_source", "available",
        }

    def test_to_dict_empty_hazards(self):
        result = ClimateRiskResult(score=1, band="Low", lat=0, lng=0)
        d = result.to_dict()
        assert d["hazards"] == []


# ── Composite score integration (no network) ─────────────────────────────────

class TestCompositeScoreCalculation:
    """Test the full composite calculation with mocked data queries."""

    def test_zero_exposure_property(self):
        """Property with no hazard exposure should score near minimum."""
        from services.climate_risk_score import climate_risk_score
        with patch("services.climate_risk_score._query_spatial_overlays") as mock_overlays, \
             patch("services.climate_risk_score.query_narclim_summary") as mock_narclim:
            mock_overlays.return_value = {}
            mock_narclim.return_value = {"hot_days_delta_2090": 0.0, "hot_days_baseline": 5, "hot_days_late_century_high": 5}
            result = climate_risk_score(-33.87, 151.21)
            assert result.score == 1  # Clamped minimum
            assert result.band == "Low"

    def test_max_exposure_property(self):
        """Property with all hazards at maximum should score near 100."""
        from services.climate_risk_score import climate_risk_score
        with patch("services.climate_risk_score._query_spatial_overlays") as mock_overlays, \
             patch("services.climate_risk_score.query_narclim_summary") as mock_narclim:
            mock_overlays.return_value = {
                "flood": [{"value": "x"}],
                "bushfire": [{"value": "x"}],
                "coastal_wetlands": [{"value": "x"}],
                "littoral_rainforest": [{"value": "x"}],
                "coastal_environment_area": [{"value": "x"}],
                "fire_history": [{"value": "a"}] * 4,
            }
            mock_narclim.return_value = {"hot_days_delta_2090": 45.0, "hot_days_baseline": 5, "hot_days_late_century_high": 50}
            result = climate_risk_score(-33.87, 151.21)
            # All 5 hazards at max (1.0 × 0.2 × 5 = 1.0) + interactions (0.18)
            # = 1.18 × 100 = 118, clamped to 100
            assert result.score == 100
            assert result.band == "Extreme"

    def test_narclim_unavailable_graceful(self):
        """NARCliM failure should not crash — heat excluded from denominator."""
        from services.climate_risk_score import climate_risk_score
        with patch("services.climate_risk_score._query_spatial_overlays") as mock_overlays, \
             patch("services.climate_risk_score.query_narclim_summary") as mock_narclim:
            mock_overlays.return_value = {"flood": [{"value": "x"}]}
            mock_narclim.side_effect = FileNotFoundError("NetCDF not found")
            result = climate_risk_score(-33.87, 151.21)
            heat = next(h for h in result.hazards if h.hazard == "heat")
            assert heat.raw_score == 0.0
            assert heat.present is False
            assert heat.available is False
            # Flood alone with 5 available hazards: 0.167 / 0.833 ≈ 0.2 × 100 = 20
            assert result.score == 20

    def test_deterministic(self):
        """Same inputs must produce same output."""
        from services.climate_risk_score import climate_risk_score
        with patch("services.climate_risk_score._query_spatial_overlays") as mock_overlays, \
             patch("services.climate_risk_score.query_narclim_summary") as mock_narclim:
            mock_overlays.return_value = {"bushfire": [{"value": "x"}]}
            mock_narclim.return_value = {"hot_days_delta_2090": 20.0, "hot_days_baseline": 10, "hot_days_late_century_high": 30}
            r1 = climate_risk_score(-33.87, 151.21)
            r2 = climate_risk_score(-33.87, 151.21)
            assert r1.score == r2.score
            assert r1.band == r2.band

    def test_hawkesbury_multi_hazard_high_score(self):
        """Hawkesbury-type multi-hazard property with flood + bushfire + fire history + heat.

        With 6-hazard model (weights ~0.167):
        flood(1.0×0.167) + bushfire(1.0×0.167) + fire_history(0.6×0.167) + heat(38/45×0.167)
        + interactions = ~71 → Very High
        """
        from services.climate_risk_score import climate_risk_score
        with patch("services.climate_risk_score._query_spatial_overlays") as mock_overlays, \
             patch("services.climate_risk_score.query_narclim_summary") as mock_narclim:
            mock_overlays.return_value = {
                "flood": [{"value": "Flood Planning"}],
                "bushfire": [{"value": "Vegetation Category 1"}],
                "fire_history": [{"value": "2019"}, {"value": "2013"}],
            }
            mock_narclim.return_value = {
                "hot_days_delta_2090": 38.0,
                "hot_days_baseline": 14,
                "hot_days_late_century_high": 52,
            }
            result = climate_risk_score(-33.55, 150.75)
            assert result.score >= 65
            assert result.band in ("High", "Very High", "Extreme")


# ── Bug fix: bushfire RFS fallback ──────────────────────────────────────────

class TestBushfireRFSFallback:
    """Bug 1: spatial_overlays historically bbox-limited to Greater Sydney.
    Properties outside metro got false negatives. Fix: fall back to RFS live API."""

    def test_fallback_when_overlays_empty(self):
        """No bushfire in spatial_overlays + RFS says prone → present=True."""
        with patch("services.climate_risk_score._query_rfs_bfpl") as mock_rfs:
            mock_rfs.return_value = {
                "is_bushfire_prone": True,
                "designation_category": "Vegetation Category 1",
            }
            h = _normalize_bushfire({}, lat=-33.5, lng=150.0)
            assert h.present is True
            assert h.raw_score == 1.0
            assert "live API fallback" in h.data_source
            assert h.confidence == "medium"  # Lower than PostGIS (live API = single query)

    def test_no_fallback_when_overlays_have_data(self):
        """Bushfire present in spatial_overlays → no RFS call needed."""
        with patch("services.climate_risk_score._query_rfs_bfpl") as mock_rfs:
            h = _normalize_bushfire({"bushfire": [{"value": "Cat 1"}]}, lat=-33.5, lng=150.0)
            mock_rfs.assert_not_called()
            assert h.present is True
            assert h.confidence == "high"

    def test_fallback_rfs_says_not_prone(self):
        """RFS says not prone → present=False (genuine no-risk, not data gap)."""
        with patch("services.climate_risk_score._query_rfs_bfpl") as mock_rfs:
            mock_rfs.return_value = {"is_bushfire_prone": False}
            h = _normalize_bushfire({}, lat=-33.5, lng=150.0)
            assert h.present is False
            assert h.raw_score == 0.0

    def test_fallback_rfs_failure_graceful(self):
        """RFS API failure → present=False (fail-open, not crash)."""
        with patch("services.climate_risk_score._query_rfs_bfpl") as mock_rfs:
            mock_rfs.side_effect = ConnectionError("timeout")
            h = _normalize_bushfire({}, lat=-33.5, lng=150.0)
            assert h.present is False
            assert h.raw_score == 0.0

    def test_no_fallback_without_coords(self):
        """No lat/lng → no fallback attempt."""
        with patch("services.climate_risk_score._query_rfs_bfpl") as mock_rfs:
            h = _normalize_bushfire({})
            mock_rfs.assert_not_called()
            assert h.present is False


# ── Bug fix: unavailable hazard exclusion from denominator ──────────────────

class TestUnavailableHazardExclusion:
    """Bug 2: missing hazard scored as 0 instead of excluded from weighted sum.
    A property with all hazards present should score the same whether or not
    NARCliM data is available for heat."""

    def test_heat_unavailable_does_not_drag_score(self):
        """Single hazard present, heat unavailable → score reflects only available hazards."""
        from services.climate_risk_score import climate_risk_score
        with patch("services.climate_risk_score._query_spatial_overlays") as mock_overlays, \
             patch("services.climate_risk_score.query_narclim_summary") as mock_narclim:
            # Only flood present
            mock_overlays.return_value = {"flood": [{"value": "x"}]}
            # Heat unavailable
            mock_narclim.side_effect = ValueError("no data")
            result = climate_risk_score(-33.87, 151.21)
            # 5 available hazards, 1 present. Flood=0.167, total=0.833
            # Rescaled: 0.167/0.833 ≈ 0.2004 × 100 = 20
            assert result.score == 20

    def test_heat_available_zero_risk_not_excluded(self):
        """Heat available but delta=0 → still counted in denominator (it's real data)."""
        from services.climate_risk_score import climate_risk_score
        with patch("services.climate_risk_score._query_spatial_overlays") as mock_overlays, \
             patch("services.climate_risk_score.query_narclim_summary") as mock_narclim:
            mock_overlays.return_value = {"flood": [{"value": "x"}]}
            mock_narclim.return_value = {"hot_days_delta_2090": 0.0, "hot_days_baseline": 5, "hot_days_late_century_high": 5}
            result = climate_risk_score(-33.87, 151.21)
            heat = next(h for h in result.hazards if h.hazard == "heat")
            assert heat.available is True
            # 6 available hazards, flood=0.167, total=~1.0
            # Rescaled: 0.167/1.0 = 0.167 × 100 = 17
            assert result.score == 17

    def test_available_field_in_to_dict(self):
        """The available field should appear in serialized output."""
        result = ClimateRiskResult(
            score=42, band="High", lat=-33.87, lng=151.21,
            hazards=[
                HazardScore(
                    hazard="heat", raw_score=0.0, weight=0.167,
                    weighted_score=0.0, present=False, detail="unavailable",
                    confidence="low", data_source="NARCliM", available=False,
                )
            ],
        )
        d = result.to_dict()
        assert d["hazards"][0]["available"] is False


# ── Output-grounding item 1: confidence must carry a named reason ────────────

class TestConfidenceCarriesReason:
    """A displayed confidence badge is a representation. Every reachable
    normalizer path must attach a non-empty confidence_reason, and the bushfire
    no-data path must never claim a confident "No".

    The pre-2026-08-03 code emitted confidence="high" with detail "Bushfire
    Prone Land: No" when the overlay was empty AND the RFS live fallback
    RAISED — a verdict about data the check never received (the DQ-36 class),
    on a safety-adjacent claim. These tests FAIL on that code:
    confidence_reason did not exist, and the RFS-failure path returned "high".
    """

    LAT, LNG = -33.6, 150.7

    def _all_path_hazards(self):
        """One HazardScore per reachable path across the failure matrix."""
        hazards = [
            _normalize_flood({}),
            _normalize_flood({"flood": [{"value": "FPA"}]}),
            _normalize_coastal({}),
            _normalize_coastal({"coastal_wetlands": [{}]}),
            _normalize_landslide({}),
            _normalize_landslide({"landslide": [{}]}),
            _normalize_fire_history({}),
            _normalize_fire_history({"fire_history": [{}]}),
            _normalize_heat({}),                              # unavailable
            _normalize_heat({"hot_days_delta_2090": 10.0}),   # available
            _normalize_bushfire({"bushfire": [{}]}),          # overlay hit
            _normalize_bushfire({}),                          # no coords → skipped
        ]
        with patch(_RFS, return_value={"is_bushfire_prone": True}):
            hazards.append(_normalize_bushfire({}, lat=self.LAT, lng=self.LNG))
        with patch(_RFS, return_value={"is_bushfire_prone": False}):
            hazards.append(_normalize_bushfire({}, lat=self.LAT, lng=self.LNG))
        with patch(_RFS, side_effect=RuntimeError("RFS down")):
            hazards.append(_normalize_bushfire({}, lat=self.LAT, lng=self.LNG))
        return hazards

    def test_every_path_names_its_reason(self):
        for h in self._all_path_hazards():
            assert h.confidence in ("low", "medium", "high"), h.hazard
            assert (h.confidence_reason or "").strip(), (
                f"{h.hazard}: confidence {h.confidence!r} served without a "
                f"named reason (detail={h.detail!r})"
            )

    def test_no_path_emits_high_without_reason(self):
        offenders = [
            h for h in self._all_path_hazards()
            if h.confidence == "high" and not (h.confidence_reason or "").strip()
        ]
        assert offenders == [], [h.hazard for h in offenders]

    def test_bushfire_rfs_failure_is_not_a_confident_no(self):
        """THE item-1 path: overlay empty + fallback raises. Old code: "No" at
        "high". New contract: unavailable, low, reason names the failure, and
        the detail says could-not-be-determined — never "No"."""
        with patch(_RFS, side_effect=RuntimeError("RFS down")):
            h = _normalize_bushfire({}, lat=self.LAT, lng=self.LNG)
        assert h.confidence != "high"
        assert h.confidence == "low"
        assert h.available is False          # excluded from composite denominator
        assert h.present is False
        assert h.raw_score == 0.0
        assert "could not be determined" in h.detail
        assert h.detail != "Bushfire Prone Land: No"
        assert "failed" in h.confidence_reason

    def test_bushfire_no_coords_is_unavailable_not_confident(self):
        h = _normalize_bushfire({})
        assert h.confidence == "low"
        assert h.available is False
        assert "could not run" in h.confidence_reason

    def test_bushfire_live_clear_is_confident_with_agreement_reason(self):
        with patch(_RFS, return_value={"is_bushfire_prone": False}):
            h = _normalize_bushfire({}, lat=self.LAT, lng=self.LNG)
        assert h.confidence == "high"
        assert h.available is True
        assert h.present is False
        assert "agrees" in h.confidence_reason

    def test_bushfire_live_prone_stays_medium(self):
        with patch(_RFS, return_value={"is_bushfire_prone": True}):
            h = _normalize_bushfire({}, lat=self.LAT, lng=self.LNG)
        assert h.confidence == "medium"
        assert h.present is True
        assert h.raw_score == 1.0

    def test_confidence_reason_serialised_in_to_dict(self):
        result = ClimateRiskResult(
            score=1, band="Low", lat=self.LAT, lng=self.LNG,
            hazards=[_normalize_flood({})],
        )
        d = result.to_dict()
        assert d["hazards"][0]["confidence_reason"].strip()
