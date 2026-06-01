"""
Mutation-testing-grade tests for _normalise_outputs and _write_report
in services/flood_truth.py.

Target: kill mutmut mutants on lines 1227-1355.
Pattern: assert exact values, not just key presence.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from services.flood_truth import (
    _normalise_outputs,
    _write_report,
    _EPI_CLASS_LABELS,
    _COMPOUND_LAYER_TYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_raw(**overrides):
    """Return a minimal raw dict that exercises the default path."""
    base = {
        "epi_flood_class": "none",
        "epi_flood_label": "No EPI Flood Overlay",
        "sar_flood_detected": False,
        "sar_confidence": None,
        "sar_analysis_date": None,
        "ems_flood_detected": None,
        "ems_activations": None,
        "jrc_water_occurrence_pct": None,
        "jrc_data_year": None,
        "dea_wofs_frequency_pct": None,
        "ses_in_flood_planning_area": None,
        "ses_flood_class": None,
        "ses_study_name": None,
        "ses_study_lga": None,
        "bom_gauge_name": None,
        "bom_gauge_distance_km": None,
        "bom_last_major_flood_date": None,
        "bom_last_major_flood_peak_m": None,
        "bom_flood_history": None,
        "flood_study_name": None,
        "flood_study_date": None,
        "s1_gap_warning": None,
        "data_currency": None,
        "epi_data_currency": None,
        "flood_studies": [],
        "ground_elevation_m_ahd": None,
        "compound_heritage": None,
        "compound_riparian": None,
        "compound_wetlands": None,
        "compound_landslide": None,
    }
    base.update(overrides)
    return base


# ===========================================================================
# _normalise_outputs — EPI backward-compat
# ===========================================================================

class TestEpiBackwardCompat:
    """EPI old bool format → epi_flood_class + epi_flood_label."""

    def test_old_bool_true_maps_to_flood_planning_area(self):
        raw = _minimal_raw(epi_flood_class=None, epi_flood_label=None, in_epi_overlay=True)
        result = _normalise_outputs(raw)
        assert result["epi_flood_class"] == "flood_planning_area"
        assert result["epi_flood_label"] == "Flood Planning Area"

    def test_old_bool_false_maps_to_none(self):
        raw = _minimal_raw(epi_flood_class=None, epi_flood_label=None, in_epi_overlay=False)
        result = _normalise_outputs(raw)
        assert result["epi_flood_class"] == "none"
        assert result["epi_flood_label"] == "No EPI Flood Overlay"

    def test_old_bool_not_used_when_epi_class_present(self):
        raw = _minimal_raw(epi_flood_class="high_flood_risk", epi_flood_label="High Flood Risk", in_epi_overlay=False)
        result = _normalise_outputs(raw)
        assert result["epi_flood_class"] == "high_flood_risk"
        assert result["epi_flood_label"] == "High Flood Risk"

    def test_non_bool_in_epi_overlay_ignored(self):
        """Only isinstance(bool) triggers backward compat."""
        raw = _minimal_raw(epi_flood_class=None, epi_flood_label=None, in_epi_overlay="yes")
        result = _normalise_outputs(raw)
        assert result["epi_flood_class"] is None
        assert result["epi_flood_label"] is None


class TestEpiLabelRecomputation:
    """epi_class present but epi_label null → recompute from _EPI_CLASS_LABELS."""

    def test_label_recomputed_when_null(self):
        raw = _minimal_raw(epi_flood_class="medium_flood_risk", epi_flood_label=None)
        result = _normalise_outputs(raw)
        assert result["epi_flood_label"] == "Medium Flood Risk"

    def test_label_recomputed_when_empty_string(self):
        """Empty string is falsy, should trigger recomputation."""
        raw = _minimal_raw(epi_flood_class="low_flood_risk", epi_flood_label="")
        result = _normalise_outputs(raw)
        assert result["epi_flood_label"] == "Low Flood Risk"

    def test_all_epi_classes_produce_correct_labels(self):
        for cls, expected_label in _EPI_CLASS_LABELS.items():
            raw = _minimal_raw(epi_flood_class=cls, epi_flood_label=None)
            result = _normalise_outputs(raw)
            assert result["epi_flood_label"] == expected_label, f"Failed for class {cls}"

    def test_label_preserved_when_already_set(self):
        raw = _minimal_raw(epi_flood_class="high_flood_risk", epi_flood_label="Custom Label")
        result = _normalise_outputs(raw)
        assert result["epi_flood_label"] == "Custom Label"


# ===========================================================================
# _normalise_outputs — SAR backward-compat
# ===========================================================================

class TestSarBackwardCompat:
    """flood_event_count → sar_flood_detected derivation."""

    def test_flood_event_count_positive_sets_detected_true(self):
        raw = _minimal_raw(sar_flood_detected=None, flood_event_count=3)
        result = _normalise_outputs(raw)
        assert result["sar_flood_detected"] is True

    def test_flood_event_count_zero_sets_detected_false(self):
        raw = _minimal_raw(sar_flood_detected=None, flood_event_count=0)
        result = _normalise_outputs(raw)
        assert result["sar_flood_detected"] is False

    def test_sar_detected_not_overridden_when_set(self):
        raw = _minimal_raw(sar_flood_detected=True, flood_event_count=0)
        result = _normalise_outputs(raw)
        assert result["sar_flood_detected"] is True

    def test_sar_detected_stays_none_when_no_event_count(self):
        raw = _minimal_raw(sar_flood_detected=None, flood_event_count=None)
        result = _normalise_outputs(raw)
        assert result["sar_flood_detected"] is None


# ===========================================================================
# _normalise_outputs — output key completeness and values
# ===========================================================================

class TestOutputKeyValues:
    """Assert exact values for all passthrough keys."""

    def test_sar_fields(self):
        raw = _minimal_raw(
            sar_confidence="high",
            sar_analysis_date="2026-01-15",
        )
        result = _normalise_outputs(raw)
        assert result["sar_confidence"] == "high"
        assert result["sar_analysis_date"] == "2026-01-15"

    def test_ems_fields(self):
        activations = [{"id": "EMSR001", "date": "2022-03-01"}]
        raw = _minimal_raw(ems_flood_detected=True, ems_activations=activations)
        result = _normalise_outputs(raw)
        assert result["ems_flood_detected"] is True
        assert result["ems_activations"] == activations

    def test_jrc_fields(self):
        raw = _minimal_raw(jrc_water_occurrence_pct=12.5, jrc_data_year=2021)
        result = _normalise_outputs(raw)
        assert result["jrc_water_occurrence_pct"] == 12.5
        assert result["jrc_data_year"] == 2021

    def test_dea_wofs_field(self):
        raw = _minimal_raw(dea_wofs_frequency_pct=3.7)
        result = _normalise_outputs(raw)
        assert result["dea_wofs_frequency_pct"] == 3.7

    def test_ses_fields(self):
        raw = _minimal_raw(
            ses_in_flood_planning_area=True,
            ses_flood_class="1% AEP",
            ses_study_name="Hawkesbury-Nepean",
            ses_study_lga="Hawkesbury",
        )
        result = _normalise_outputs(raw)
        assert result["ses_in_flood_planning_area"] is True
        assert result["ses_flood_class"] == "1% AEP"
        assert result["ses_study_name"] == "Hawkesbury-Nepean"
        assert result["ses_study_lga"] == "Hawkesbury"

    def test_bom_fields(self):
        raw = _minimal_raw(
            bom_gauge_name="Wilsons River at Lismore",
            bom_gauge_distance_km=2.3,
            bom_last_major_flood_date="2022-02-28",
            bom_last_major_flood_peak_m=14.4,
            bom_flood_history=[{"date": "2022-02-28", "peak_m": 14.4}],
        )
        result = _normalise_outputs(raw)
        assert result["bom_gauge_name"] == "Wilsons River at Lismore"
        assert result["bom_gauge_distance_km"] == 2.3
        assert result["bom_last_major_flood_date"] == "2022-02-28"
        assert result["bom_last_major_flood_peak_m"] == 14.4
        assert result["bom_flood_history"] == [{"date": "2022-02-28", "peak_m": 14.4}]

    def test_bom_flood_history_defaults_to_empty_list(self):
        raw = _minimal_raw(bom_flood_history=None)
        result = _normalise_outputs(raw)
        assert result["bom_flood_history"] == []

    def test_flood_study_name_and_date(self):
        raw = _minimal_raw(flood_study_name="Test Study", flood_study_date="2023-06-01")
        result = _normalise_outputs(raw)
        assert result["flood_study_name"] == "Test Study"
        assert result["flood_study_date"] == "2023-06-01"

    def test_s1_gap_warning(self):
        raw = _minimal_raw(s1_gap_warning="S1B gap affects this period")
        result = _normalise_outputs(raw)
        assert result["s1_gap_warning"] == "S1B gap affects this period"


# ===========================================================================
# _normalise_outputs — data_currency fallback chain
# ===========================================================================

class TestDataCurrency:
    """data_currency → epi_data_currency → 'unknown'."""

    def test_data_currency_used_when_present(self):
        raw = _minimal_raw(data_currency="2026-01-01")
        result = _normalise_outputs(raw)
        assert result["data_currency"] == "2026-01-01"

    def test_epi_data_currency_fallback(self):
        raw = _minimal_raw(data_currency=None, epi_data_currency="2025-12-01")
        result = _normalise_outputs(raw)
        assert result["data_currency"] == "2025-12-01"

    def test_unknown_fallback(self):
        raw = _minimal_raw(data_currency=None, epi_data_currency=None)
        result = _normalise_outputs(raw)
        assert result["data_currency"] == "unknown"

    def test_empty_string_data_currency_falls_through(self):
        """Empty string is falsy → falls to epi_data_currency."""
        raw = _minimal_raw(data_currency="", epi_data_currency="2025-06-01")
        result = _normalise_outputs(raw)
        assert result["data_currency"] == "2025-06-01"

    def test_empty_both_falls_to_unknown(self):
        raw = _minimal_raw(data_currency="", epi_data_currency="")
        result = _normalise_outputs(raw)
        assert result["data_currency"] == "unknown"


# ===========================================================================
# _normalise_outputs — Hawkesbury AEP flood level fields
# ===========================================================================

class TestHawkesburyAep:
    """9 AEP keys + study name."""

    AEP_KEYS = ("2aep", "5aep", "10aep", "20aep", "50aep", "100aep", "200aep", "500aep", "pmf")

    def test_all_aep_keys_present_when_set(self):
        raw_extra = {f"hawkesbury_flood_level_{k}": float(i + 5) for i, k in enumerate(self.AEP_KEYS)}
        raw_extra["hawkesbury_flood_study"] = "FRMSP 2025"
        raw = _minimal_raw(**raw_extra)
        result = _normalise_outputs(raw)
        for i, k in enumerate(self.AEP_KEYS):
            assert result[f"hawkesbury_flood_level_{k}"] == float(i + 5)
        assert result["hawkesbury_flood_study"] == "FRMSP 2025"

    def test_all_aep_keys_none_when_missing(self):
        raw = _minimal_raw()
        result = _normalise_outputs(raw)
        for k in self.AEP_KEYS:
            assert result[f"hawkesbury_flood_level_{k}"] is None
        assert result["hawkesbury_flood_study"] is None

    def test_specific_100aep_value(self):
        raw = _minimal_raw(**{"hawkesbury_flood_level_100aep": 17.3})
        result = _normalise_outputs(raw)
        assert result["hawkesbury_flood_level_100aep"] == 17.3


# ===========================================================================
# _normalise_outputs — flood_studies passthrough and depth computation
# ===========================================================================

class TestFloodStudies:
    """flood_studies list passthrough + depth derivation."""

    def test_flood_studies_passthrough(self):
        studies = [{"study_name": "Camden 2020", "source": "council", "design": {}}]
        raw = _minimal_raw(flood_studies=studies)
        result = _normalise_outputs(raw)
        assert result["flood_studies"] == studies

    def test_flood_studies_defaults_to_empty_list(self):
        raw = _minimal_raw(flood_studies=None)
        result = _normalise_outputs(raw)
        assert result["flood_studies"] == []

    def test_depth_computed_from_level_and_ground_elev(self):
        studies = [
            {
                "study_name": "Test",
                "design": {
                    "1pct": {"level_m_ahd": 15.0, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["design"]["1pct"]["depth_m"] == 5.0

    def test_depth_clamped_to_zero_when_negative(self):
        """level_m_ahd < ground_elevation → depth = 0.0."""
        studies = [
            {
                "study_name": "Test",
                "design": {
                    "1pct": {"level_m_ahd": 8.0, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["design"]["1pct"]["depth_m"] == 0.0

    def test_depth_rounded_to_2dp(self):
        studies = [
            {
                "study_name": "Test",
                "design": {
                    "1pct": {"level_m_ahd": 10.333, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["design"]["1pct"]["depth_m"] == 0.33

    def test_depth_not_overwritten_when_already_set(self):
        studies = [
            {
                "study_name": "Test",
                "design": {
                    "1pct": {"level_m_ahd": 15.0, "depth_m": 3.5},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["design"]["1pct"]["depth_m"] == 3.5

    def test_depth_not_computed_when_no_ground_elev(self):
        studies = [
            {
                "study_name": "Test",
                "design": {
                    "1pct": {"level_m_ahd": 15.0, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=None)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["design"]["1pct"]["depth_m"] is None

    def test_depth_not_computed_when_no_level(self):
        studies = [
            {
                "study_name": "Test",
                "design": {
                    "1pct": {"level_m_ahd": None, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["design"]["1pct"]["depth_m"] is None

    def test_historical_depth_computed(self):
        studies = [
            {
                "study_name": "Test",
                "historical": {
                    "2022": {"level_m_ahd": 12.0, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["historical"]["2022"]["depth_m"] == 2.0

    def test_historical_depth_clamped(self):
        studies = [
            {
                "study_name": "Test",
                "historical": {
                    "2022": {"level_m_ahd": 9.0, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["historical"]["2022"]["depth_m"] == 0.0

    def test_multiple_design_aeps(self):
        studies = [
            {
                "study_name": "Multi",
                "design": {
                    "1pct": {"level_m_ahd": 15.0, "depth_m": None},
                    "5pct": {"level_m_ahd": 13.0, "depth_m": None},
                },
            }
        ]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"][0]["design"]["1pct"]["depth_m"] == 5.0
        assert result["flood_studies"][0]["design"]["5pct"]["depth_m"] == 3.0

    def test_no_design_key_no_crash(self):
        """Study with no 'design' key should not crash."""
        studies = [{"study_name": "Basic"}]
        raw = _minimal_raw(flood_studies=studies, ground_elevation_m_ahd=10.0)
        result = _normalise_outputs(raw)
        assert result["flood_studies"] == [{"study_name": "Basic"}]


# ===========================================================================
# _normalise_outputs — in_100yr_flood_zone derivation
# ===========================================================================

class TestIn100yrFloodZone:
    """Multiple sources can set in_100yr_flood_zone to True."""

    def test_false_when_no_indicators(self):
        raw = _minimal_raw(epi_flood_class="none")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is False

    def test_true_from_epi_class(self):
        raw = _minimal_raw(epi_flood_class="flood_planning_area", epi_flood_label="Flood Planning Area")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is True

    def test_true_from_epi_high_risk(self):
        raw = _minimal_raw(epi_flood_class="high_flood_risk", epi_flood_label="High Flood Risk")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is True

    def test_false_from_epi_empty_string(self):
        """Empty string epi_class is in the exclusion list."""
        raw = _minimal_raw(epi_flood_class="")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is False

    def test_true_from_ses_1pct(self):
        raw = _minimal_raw(ses_flood_class="1% AEP Flood Extent")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is True

    def test_true_from_ses_1aep(self):
        raw = _minimal_raw(ses_flood_class="1AEP Flood Level")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is True

    def test_true_from_ses_100(self):
        raw = _minimal_raw(ses_flood_class="100 Year Flood")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is True

    def test_false_from_ses_5pct(self):
        raw = _minimal_raw(ses_flood_class="5% AEP")
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is False

    def test_true_from_flood_study_1pct(self):
        studies = [{"study_name": "Test", "design": {"1pct": {"level_m_ahd": 12.0}}}]
        raw = _minimal_raw(flood_studies=studies)
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is True

    def test_false_from_flood_study_5pct_only(self):
        studies = [{"study_name": "Test", "design": {"5pct": {"level_m_ahd": 12.0}}}]
        raw = _minimal_raw(flood_studies=studies)
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is False

    def test_true_from_hawkesbury_100aep(self):
        raw = _minimal_raw(**{"hawkesbury_flood_level_100aep": 17.3})
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is True

    def test_false_from_hawkesbury_200aep_only(self):
        """200aep alone does not trigger in_100yr."""
        raw = _minimal_raw(**{"hawkesbury_flood_level_200aep": 20.0})
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is False

    def test_epi_none_class_not_in_100yr(self):
        raw = _minimal_raw(epi_flood_class=None)
        result = _normalise_outputs(raw)
        assert result["in_100yr_flood_zone"] is False


# ===========================================================================
# _normalise_outputs — compound risk layers
# ===========================================================================

class TestCompoundRiskLayers:
    """compound_* keys, compound_risk_layers list, compound_risk_notes."""

    def test_all_compound_keys_present(self):
        raw = _minimal_raw()
        result = _normalise_outputs(raw)
        for lt in _COMPOUND_LAYER_TYPES:
            assert f"compound_{lt}" in result

    def test_compound_none_values(self):
        raw = _minimal_raw()
        result = _normalise_outputs(raw)
        assert result["compound_risk_layers"] == []
        assert result["compound_risk_notes"] == []

    def test_compound_heritage_set(self):
        raw = _minimal_raw(compound_heritage=True)
        result = _normalise_outputs(raw)
        assert result["compound_heritage"] is True
        assert "heritage" in result["compound_risk_layers"]
        assert len(result["compound_risk_notes"]) == 1
        assert "heritage" in result["compound_risk_notes"][0].lower()

    def test_compound_riparian_set(self):
        raw = _minimal_raw(compound_riparian=True)
        result = _normalise_outputs(raw)
        assert result["compound_riparian"] is True
        assert "riparian" in result["compound_risk_layers"]

    def test_compound_multiple(self):
        raw = _minimal_raw(compound_heritage=True, compound_landslide=True)
        result = _normalise_outputs(raw)
        assert result["compound_risk_layers"] == ["heritage", "landslide"]
        assert len(result["compound_risk_notes"]) == 2

    def test_compound_order_matches_layer_types(self):
        """Order in compound_risk_layers should match _COMPOUND_LAYER_TYPES order."""
        raw = _minimal_raw(compound_landslide=True, compound_heritage=True, compound_wetlands=True)
        result = _normalise_outputs(raw)
        assert result["compound_risk_layers"] == ["heritage", "wetlands", "landslide"]

    def test_compound_false_not_included(self):
        """False is not None — it IS included in compound_risk_layers."""
        raw = _minimal_raw(compound_heritage=False)
        result = _normalise_outputs(raw)
        assert result["compound_heritage"] is False
        assert "heritage" in result["compound_risk_layers"]


# ===========================================================================
# _normalise_outputs — flood_signal
# ===========================================================================

class TestFloodSignal:
    """flood_signal is computed via _compute_flood_signal."""

    def test_signal_none_for_no_indicators(self):
        """No flood indicators and ses queried → 'none'."""
        raw = _minimal_raw(epi_flood_class="none", ses_in_flood_planning_area=False)
        result = _normalise_outputs(raw)
        assert result["flood_signal"] == "none"

    def test_signal_low_for_epi_only(self):
        raw = _minimal_raw(
            epi_flood_class="flood_planning_area",
            epi_flood_label="Flood Planning Area",
            ses_in_flood_planning_area=False,
        )
        result = _normalise_outputs(raw)
        assert result["flood_signal"] == "low"

    def test_signal_elevated_for_epi_plus_ems(self):
        raw = _minimal_raw(
            epi_flood_class="flood_planning_area",
            epi_flood_label="Flood Planning Area",
            ems_flood_detected=True,
            ses_in_flood_planning_area=False,
        )
        result = _normalise_outputs(raw)
        assert result["flood_signal"] == "elevated"

    def test_signal_unavailable_when_query_failed(self):
        raw = _minimal_raw(data_currency="query_failed")
        result = _normalise_outputs(raw)
        assert result["flood_signal"] == "unavailable"

    def test_signal_unavailable_no_coverage(self):
        """epi=none, no SES, no study, no EMS, no BOM, low JRC → unavailable."""
        raw = _minimal_raw(epi_flood_class="none")
        result = _normalise_outputs(raw)
        assert result["flood_signal"] == "unavailable"

    def test_signal_moderate_for_ems_only(self):
        raw = _minimal_raw(
            epi_flood_class="none",
            ems_flood_detected=True,
            ses_in_flood_planning_area=False,
        )
        result = _normalise_outputs(raw)
        assert result["flood_signal"] == "moderate"


# ===========================================================================
# _normalise_outputs — ground_elevation passthrough
# ===========================================================================

class TestGroundElevation:
    def test_ground_elevation_passthrough(self):
        raw = _minimal_raw(ground_elevation_m_ahd=42.5)
        result = _normalise_outputs(raw)
        assert result["ground_elevation_m_ahd"] == 42.5

    def test_ground_elevation_none(self):
        raw = _minimal_raw(ground_elevation_m_ahd=None)
        result = _normalise_outputs(raw)
        assert result["ground_elevation_m_ahd"] is None


# ===========================================================================
# _write_report
# ===========================================================================

class TestWriteReport:
    """Test _write_report SQL parameter ordering and resource management."""

    @patch("services.flood_truth._get_conn")
    @patch("services.flood_truth._compute_confidence", return_value="medium")
    @patch("services.flood_truth._build_data_sources", return_value=["NSW SEED EPI WFS"])
    def test_sql_params_ordering(self, mock_sources, mock_conf, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        _write_report(
            report_id="rpt-123",
            address="1 Test St",
            lat=-33.8,
            lng=151.2,
            prop_id="LOT123",
            inputs={"radius_km": 5},
            internal_outputs={"epi_flood_class": "none"},
        )

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params[0] == "rpt-123"      # report_id
        assert params[1] == "1 Test St"     # address
        assert params[2] == -33.8           # lat
        assert params[3] == 151.2           # lng
        assert params[4] == "LOT123"        # prop_id
        assert params[5] == date.today()    # run_date
        # params[6] = Json(inputs), params[7] = Json(outputs)
        assert params[8] == "medium"        # confidence
        assert params[9] == ["NSW SEED EPI WFS"]  # data_sources

    @patch("services.flood_truth._get_conn")
    @patch("services.flood_truth._compute_confidence", return_value="low")
    @patch("services.flood_truth._build_data_sources", return_value=[])
    def test_conn_close_called(self, mock_sources, mock_conf, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        _write_report("id", "addr", -33.0, 151.0, "prop", {}, {})

        mock_conn.close.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("services.flood_truth._get_conn")
    @patch("services.flood_truth._compute_confidence", return_value="low")
    @patch("services.flood_truth._build_data_sources", return_value=[])
    def test_conn_close_on_error(self, mock_sources, mock_conf, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        with pytest.raises(Exception, match="DB error"):
            _write_report("id", "addr", -33.0, 151.0, "prop", {}, {})

        mock_conn.close.assert_called_once()

    @patch("services.flood_truth._get_conn")
    @patch("services.flood_truth._compute_confidence", return_value="high")
    @patch("services.flood_truth._build_data_sources", return_value=["src"])
    def test_confidence_and_sources_from_internal_outputs(self, mock_sources, mock_conf, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        internal = {"epi_flood_class": "high_flood_risk"}
        _write_report("id", "addr", -33.0, 151.0, "prop", {}, internal)

        mock_conf.assert_called_once_with(internal)
        mock_sources.assert_called_once_with(internal)
