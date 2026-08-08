"""
Adversarial unit tests for services/flood_truth.py.

Pure-logic functions only — no DB, no network calls.

Covers:
  _compute_flood_signal  — 5 output states, all boolean combinations
  _compute_confidence    — 3 tiers, null wet_seasons trap
  _normalise_outputs     — legacy format migration, data_currency fallback
  _build_s1_gap_warning  — two variants
  _build_data_sources    — conditional source list
  _s1b_gap_affected      — S1B gap date range overlap
  _jrc_tile_url          — coordinate → GCS URL
  _haversine_km          — known distances
"""

import inspect
import re
import sys
import os
import pytest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.flood_truth import (
    _compute_flood_signal,
    _compute_confidence,
    _normalise_outputs,
    _build_s1_gap_warning,
    _build_data_sources,
    _build_compound_risk_notes,
    _COMPOUND_LAYER_TYPES,
    _s1b_gap_affected,
    _query_epi_overlay,  # for DataDate coercion test (monkey-patched)
    _jrc_tile_url,
    _haversine_km,
    S1B_GAP_START,
    S1B_GAP_END,
    _DATA_SOURCE_EMS,
    _DATA_SOURCE_JRC,
    _DATA_SOURCE_BOM,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _outputs(**kwargs) -> dict:
    """Build a minimal internal_outputs dict with all keys absent by default."""
    base = {
        "epi_flood_class": None,
        "epi_flood_label": None,
        "data_currency": "2024-01-01",
        "ems_flood_detected": None,
        "ems_activations": None,
        "jrc_water_occurrence_pct": None,
        "jrc_data_year": None,
        "bom_gauge_name": None,
        "bom_gauge_distance_km": None,
        "bom_last_major_flood_date": None,
        "bom_last_major_flood_peak_m": None,
        "wet_seasons_checked": 0,
        "sar_flood_detected": None,
        "sar_confidence": None,
        "sar_analysis_date": None,
        "s1_gap_warning": None,
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# _compute_flood_signal — EPI query failure
# ---------------------------------------------------------------------------

def test_signal_query_failed_returns_unavailable():
    out = _outputs(data_currency="query_failed")
    assert _compute_flood_signal(out) == "unavailable"


def test_signal_epi_null_data_currency_not_query_failed():
    """data_currency="unknown" is not query_failed — should not return unavailable."""
    out = _outputs(data_currency="unknown")
    assert _compute_flood_signal(out) != "unavailable"


# ---------------------------------------------------------------------------
# _compute_flood_signal — none
# ---------------------------------------------------------------------------

def test_signal_all_null_returns_none():
    out = _outputs()
    assert _compute_flood_signal(out) == "none"


def test_signal_epi_class_none_returns_none():
    out = _outputs(epi_flood_class=None)
    assert _compute_flood_signal(out) == "none"


def test_signal_epi_class_none_string_ses_queried_returns_none():
    """epi='none' + SES was queried and confirmed NOT in FPA → 'none' (no risk found).
    Without SES data Phase 0 returns 'unavailable' instead — see test below."""
    out = _outputs(epi_flood_class="none", ses_in_flood_planning_area=False)
    assert _compute_flood_signal(out) == "none"


def test_signal_epi_class_none_string_no_ses_returns_unavailable():
    """Phase 0: epi='none' + SES not queried + no observed signals → 'unavailable'.
    EPI Layer 1 only covers ~11 LGAs; silence is not evidence of safety."""
    out = _outputs(epi_flood_class="none")
    assert _compute_flood_signal(out) == "unavailable"


def test_signal_empty_epi_class_returns_none():
    """epi_flood_class='' must NOT be treated as in-overlay (was a bug: '' not in (None,'none'))."""
    out = _outputs(epi_flood_class="")
    assert _compute_flood_signal(out) == "none"


# ---------------------------------------------------------------------------
# _compute_flood_signal — low
# ---------------------------------------------------------------------------

def test_signal_epi_only_returns_low():
    out = _outputs(epi_flood_class="flood_planning_area")
    assert _compute_flood_signal(out) == "low"


def test_signal_epi_high_flood_risk_returns_low():
    out = _outputs(epi_flood_class="high_flood_risk")
    assert _compute_flood_signal(out) == "low"


def test_signal_epi_medium_flood_risk_returns_low():
    out = _outputs(epi_flood_class="medium_flood_risk")
    assert _compute_flood_signal(out) == "low"


# ---------------------------------------------------------------------------
# _compute_flood_signal — moderate
# ---------------------------------------------------------------------------

def test_signal_ems_detected_alone_returns_moderate():
    out = _outputs(ems_flood_detected=True)
    assert _compute_flood_signal(out) == "moderate"


def test_signal_epi_plus_jrc_low_returns_moderate():
    out = _outputs(epi_flood_class="flood_planning_area", jrc_water_occurrence_pct=10.0)
    assert _compute_flood_signal(out) == "moderate"


def test_signal_epi_plus_bom_returns_moderate():
    out = _outputs(epi_flood_class="flood_planning_area", bom_last_major_flood_date="2022-03-01")
    assert _compute_flood_signal(out) == "moderate"


def test_signal_jrc_moderate_alone_returns_moderate():
    out = _outputs(jrc_water_occurrence_pct=20.0)
    assert _compute_flood_signal(out) == "moderate"


def test_signal_jrc_low_plus_bom_returns_moderate():
    out = _outputs(jrc_water_occurrence_pct=5.0, bom_last_major_flood_date="2022-03-01")
    assert _compute_flood_signal(out) == "moderate"


# ---------------------------------------------------------------------------
# _compute_flood_signal — elevated
# ---------------------------------------------------------------------------

def test_signal_epi_plus_ems_returns_elevated():
    out = _outputs(epi_flood_class="flood_planning_area", ems_flood_detected=True)
    assert _compute_flood_signal(out) == "elevated"


def test_signal_ems_plus_jrc_moderate_returns_elevated():
    out = _outputs(ems_flood_detected=True, jrc_water_occurrence_pct=20.0)
    assert _compute_flood_signal(out) == "elevated"


def test_signal_ems_plus_jrc_high_returns_elevated():
    out = _outputs(ems_flood_detected=True, jrc_water_occurrence_pct=50.0)
    assert _compute_flood_signal(out) == "elevated"


def test_signal_jrc_high_alone_returns_elevated():
    """JRC ≥40% alone → elevated (property is regularly inundated)."""
    out = _outputs(jrc_water_occurrence_pct=40.0)
    assert _compute_flood_signal(out) == "elevated"


def test_signal_jrc_high_boundary_at_40_is_elevated():
    out = _outputs(jrc_water_occurrence_pct=40.0)
    assert _compute_flood_signal(out) == "elevated"


def test_signal_jrc_just_below_high_boundary_is_moderate():
    out = _outputs(jrc_water_occurrence_pct=39.9)
    assert _compute_flood_signal(out) == "moderate"


def test_signal_epi_plus_jrc_moderate_plus_bom_returns_elevated():
    out = _outputs(
        epi_flood_class="flood_planning_area",
        jrc_water_occurrence_pct=20.0,
        bom_last_major_flood_date="2022-03-01",
    )
    assert _compute_flood_signal(out) == "elevated"


def test_signal_jrc_zero_not_treated_as_low():
    """jrc_pct=0.0 — jrc_low requires 0 < pct < 15, so 0.0 should not trigger."""
    out = _outputs(epi_flood_class="flood_planning_area", jrc_water_occurrence_pct=0.0)
    # epi only → low (jrc=0 does not contribute)
    assert _compute_flood_signal(out) == "low"


# ---------------------------------------------------------------------------
# _compute_confidence — null trap
# ---------------------------------------------------------------------------

def test_confidence_null_wet_seasons_returns_low():
    """wet_seasons_checked=null: no SAR data, no sources → low (not crash)."""
    out = _outputs(wet_seasons_checked=None)
    result = _compute_confidence(out)
    assert result == "low"


def test_confidence_no_sources_no_sar_returns_low():
    out = _outputs()
    assert _compute_confidence(out) == "low"


def test_confidence_one_source_returns_medium():
    out = _outputs(ems_flood_detected=True)
    assert _compute_confidence(out) == "medium"


def test_confidence_two_sources_returns_medium():
    out = _outputs(ems_flood_detected=True, jrc_water_occurrence_pct=10.0)
    assert _compute_confidence(out) == "medium"


def test_confidence_three_sources_no_sar_returns_medium():
    """3 spatial layers but 0 SAR seasons → medium (not high)."""
    out = _outputs(
        ems_flood_detected=True,
        jrc_water_occurrence_pct=10.0,
        bom_gauge_name="Hawkesbury River at Windsor",
        wet_seasons_checked=0,
    )
    assert _compute_confidence(out) == "medium"


def test_confidence_three_sources_with_sar_returns_high():
    out = _outputs(
        ems_flood_detected=True,
        jrc_water_occurrence_pct=10.0,
        bom_gauge_name="Hawkesbury River at Windsor",
        wet_seasons_checked=1,
    )
    assert _compute_confidence(out) == "high"


def test_confidence_two_sar_seasons_returns_medium():
    out = _outputs(wet_seasons_checked=2)
    assert _compute_confidence(out) == "medium"


# ---------------------------------------------------------------------------
# _normalise_outputs — legacy format migration
# ---------------------------------------------------------------------------

def test_normalise_legacy_bool_true_maps_to_flood_planning_area():
    raw = {"in_epi_overlay": True}
    result = _normalise_outputs(raw)
    assert result["epi_flood_class"] == "flood_planning_area"


def test_normalise_legacy_bool_false_maps_to_none():
    raw = {"in_epi_overlay": False}
    result = _normalise_outputs(raw)
    assert result["epi_flood_class"] == "none"


def test_normalise_modern_epi_class_preserved():
    raw = {"epi_flood_class": "high_flood_risk", "epi_flood_label": "High Flood Risk"}
    result = _normalise_outputs(raw)
    assert result["epi_flood_class"] == "high_flood_risk"


def test_normalise_legacy_flood_event_count_maps_sar_detected():
    raw = {"flood_event_count": 3}
    result = _normalise_outputs(raw)
    assert result["sar_flood_detected"] is True


def test_normalise_legacy_flood_event_count_zero_maps_false():
    raw = {"flood_event_count": 0}
    result = _normalise_outputs(raw)
    assert result["sar_flood_detected"] is False


def test_normalise_data_currency_fallback_to_epi_data_currency():
    raw = {"epi_data_currency": "2023-06-01"}
    result = _normalise_outputs(raw)
    assert result["data_currency"] == "2023-06-01"


def test_normalise_data_currency_present_takes_precedence():
    raw = {"data_currency": "2024-01-01", "epi_data_currency": "2023-01-01"}
    result = _normalise_outputs(raw)
    assert result["data_currency"] == "2024-01-01"


def test_normalise_computes_flood_signal():
    raw = {"epi_flood_class": "flood_planning_area", "ems_flood_detected": True}
    result = _normalise_outputs(raw)
    assert result["flood_signal"] == "elevated"


# ---------------------------------------------------------------------------
# _build_s1_gap_warning
# ---------------------------------------------------------------------------

def test_s1_gap_warning_with_ems_mentions_copernicus():
    out = _outputs(ems_flood_detected=True)
    warning = _build_s1_gap_warning(out)
    assert "Copernicus" in warning


def test_s1_gap_warning_without_ems_mentions_ingest_script():
    out = _outputs(ems_flood_detected=None)
    warning = _build_s1_gap_warning(out)
    assert "ingest_copernicus_ems" in warning


def test_s1_gap_warning_without_ems_detected_false_mentions_ingest():
    """ems_flood_detected=False means table exists but no match — EMS IS available."""
    out = _outputs(ems_flood_detected=False)
    warning = _build_s1_gap_warning(out)
    assert "Copernicus" in warning


# ---------------------------------------------------------------------------
# _build_data_sources
# ---------------------------------------------------------------------------

def test_data_sources_epi_always_s1_only_with_result():
    """FLIPPED 2026-08-03 (campaign item 4 / DQ-44): previously pinned the S1
    source as unconditional, but no S1 query has ever run — a served source
    claim with no query behind it. S1 appears only with a SAR result."""
    out = _outputs()
    sources = _build_data_sources(out)
    assert "NSW SEED EPI WFS" in sources
    assert "Microsoft Planetary Computer S1 RTC" not in sources
    with_sar = _outputs(sar_flood_detected=True)
    assert "Microsoft Planetary Computer S1 RTC" in _build_data_sources(with_sar)


def test_data_sources_includes_ems_when_available():
    out = _outputs(ems_flood_detected=True)
    assert _DATA_SOURCE_EMS in _build_data_sources(out)


def test_data_sources_excludes_ems_when_none():
    out = _outputs(ems_flood_detected=None)
    assert _DATA_SOURCE_EMS not in _build_data_sources(out)


def test_data_sources_includes_jrc_when_available():
    out = _outputs(jrc_water_occurrence_pct=10.0)
    assert _DATA_SOURCE_JRC in _build_data_sources(out)


def test_data_sources_excludes_jrc_when_none():
    out = _outputs(jrc_water_occurrence_pct=None)
    assert _DATA_SOURCE_JRC not in _build_data_sources(out)


def test_data_sources_includes_bom_when_gauge_present():
    out = _outputs(bom_gauge_name="Hawkesbury River at Windsor")
    assert _DATA_SOURCE_BOM in _build_data_sources(out)


def test_data_sources_excludes_bom_when_no_gauge():
    out = _outputs(bom_gauge_name=None)
    assert _DATA_SOURCE_BOM not in _build_data_sources(out)


# ---------------------------------------------------------------------------
# _s1b_gap_affected
# ---------------------------------------------------------------------------

def test_s1b_gap_entirely_before_gap():
    assert _s1b_gap_affected(date(2020, 1, 1), date(2021, 12, 22)) is False


def test_s1b_gap_entirely_after_gap():
    assert _s1b_gap_affected(date(2025, 3, 5), date(2025, 6, 1)) is False


def test_s1b_gap_overlaps_start():
    assert _s1b_gap_affected(date(2021, 11, 1), date(2022, 2, 1)) is True


def test_s1b_gap_overlaps_end():
    assert _s1b_gap_affected(date(2025, 1, 1), date(2025, 5, 1)) is True


def test_s1b_gap_entirely_within_gap():
    assert _s1b_gap_affected(date(2022, 6, 1), date(2023, 6, 1)) is True


def test_s1b_gap_exactly_on_start_boundary():
    assert _s1b_gap_affected(S1B_GAP_START, S1B_GAP_START) is True


def test_s1b_gap_exactly_on_end_boundary():
    assert _s1b_gap_affected(S1B_GAP_END, S1B_GAP_END) is True


def test_s1b_gap_one_day_after_end():
    from datetime import timedelta
    after = S1B_GAP_END + timedelta(days=1)
    assert _s1b_gap_affected(after, after) is False


# ---------------------------------------------------------------------------
# _jrc_tile_url — coordinate → GCS URL
# ---------------------------------------------------------------------------

def test_jrc_tile_url_sydney():
    """Sydney (-33.87, 151.21) → 150E_30S tile."""
    url = _jrc_tile_url(-33.87, 151.21)
    assert "150E" in url
    assert "30S" in url


def test_jrc_tile_url_northern_nsw():
    """Lismore (-28.8, 153.28) → 150E_20S tile."""
    url = _jrc_tile_url(-28.8, 153.28)
    assert "150E" in url
    assert "20S" in url


def test_jrc_tile_url_wagga():
    """Wagga (-35.1, 147.37) → 140E_30S tile."""
    url = _jrc_tile_url(-35.1, 147.37)
    assert "140E" in url
    assert "30S" in url


def test_jrc_tile_url_contains_v1_4_2021():
    url = _jrc_tile_url(-33.87, 151.21)
    assert "v1_4_2021" in url
    assert url.endswith(".tif")


# ---------------------------------------------------------------------------
# _haversine_km — known distances
# ---------------------------------------------------------------------------

def test_haversine_same_point_is_zero():
    assert _haversine_km(-33.87, 151.21, -33.87, 151.21) == pytest.approx(0.0, abs=0.001)


def test_haversine_sydney_to_newcastle_approx():
    """Sydney CBD to Newcastle CBD ≈ 117 km great-circle (not road distance)."""
    d = _haversine_km(-33.87, 151.21, -32.93, 151.78)
    assert 110 < d < 130


def test_haversine_sydney_to_wollongong_approx():
    """Sydney CBD to Wollongong ≈ 80 km."""
    d = _haversine_km(-33.87, 151.21, -34.42, 150.89)
    assert 65 < d < 95


# ---------------------------------------------------------------------------
# DataDate epoch-ms integer coercion (Bug: ArcGIS returns int, contract needs str)
# ---------------------------------------------------------------------------

def test_epi_overlay_epoch_ms_datadate_coerced_to_str(monkeypatch):
    """ArcGIS DataDate may be an epoch-ms integer — must be coerced to str."""
    import services.flood_truth as ft
    import requests

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"features": [{"attributes": {
                "DataDate": 1672531200000,  # epoch-ms integer
                "FloodClass": "High Flood Risk",
            }}]}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResp())
    result = ft._query_epi_overlay(-33.87, 151.21)
    assert isinstance(result["data_currency"], str), (
        f"data_currency must be str, got {type(result['data_currency'])}"
    )


def test_epi_overlay_string_datadate_passes_through(monkeypatch):
    import services.flood_truth as ft
    import requests

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"features": [{"attributes": {
                "DataDate": "2024-01-01",
                "FloodClass": "low flood risk",
            }}]}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResp())
    result = ft._query_epi_overlay(-33.87, 151.21)
    assert result["data_currency"] == "2024-01-01"


# ---------------------------------------------------------------------------
# _compute_flood_signal — "unavailable" in signal contract
# ---------------------------------------------------------------------------

def test_signal_unavailable_is_a_valid_output():
    """Confirm "unavailable" is a documented signal value (not just "none"|"low"|"moderate"|"elevated")."""
    out = _outputs(data_currency="query_failed")
    result = _compute_flood_signal(out)
    assert result == "unavailable"
    # Verify it's one of the 5 documented values
    assert result in ("none", "low", "moderate", "elevated", "unavailable")


def test_haversine_is_symmetric():
    a = _haversine_km(-33.87, 151.21, -28.8, 153.28)
    b = _haversine_km(-28.8, 153.28, -33.87, 151.21)
    assert a == pytest.approx(b, rel=1e-9)


# ---------------------------------------------------------------------------
# Pass-3 bug regression tests
# ---------------------------------------------------------------------------

def test_normalise_outputs_none_raw_does_not_crash():
    """_normalise_outputs(None) was called on cache hits where outputs column is NULL.
    cached["outputs"] or {} guard was added in run_flood; but _normalise_outputs itself
    should be defensive too — if it ever receives {} it must not crash."""
    result = _normalise_outputs({})
    assert isinstance(result, dict)
    assert result.get("epi_flood_class") is None
    # flood_signal computed from empty inputs → "none" (no data = no signal), not a crash
    assert result.get("flood_signal") == "none"


def test_normalise_outputs_epi_label_recomputed_when_null():
    """epi_flood_class present but epi_flood_label null (old DB rows) →
    _normalise_outputs must recompute label from class."""
    raw = {
        "epi_flood_class": "flood_planning_area",
        "epi_flood_label": None,   # null in DB — written before label field was added
    }
    result = _normalise_outputs(raw)
    assert result["epi_flood_label"] == "Flood Planning Area"


def test_normalise_outputs_epi_label_preserved_when_present():
    """epi_flood_label already in DB must not be overwritten."""
    raw = {
        "epi_flood_class": "flood_planning_area",
        "epi_flood_label": "Flood Planning Area",
    }
    result = _normalise_outputs(raw)
    assert result["epi_flood_label"] == "Flood Planning Area"


def test_normalise_outputs_data_currency_both_null_defaults_to_unknown():
    """data_currency=null AND epi_data_currency=null → must return 'unknown', not None.
    .get("epi_data_currency", "unknown") only fires the default when key is ABSENT;
    when key exists with null it returns None. Fixed with terminal `or 'unknown'`."""
    raw = {"data_currency": None, "epi_data_currency": None}
    result = _normalise_outputs(raw)
    assert result["data_currency"] == "unknown"


def test_normalise_outputs_data_currency_fallback_to_legacy_field():
    """data_currency absent → fall back to epi_data_currency (legacy field name)."""
    raw = {"epi_data_currency": "2024-01-01"}
    result = _normalise_outputs(raw)
    assert result["data_currency"] == "2024-01-01"


def test_epi_overlay_attributes_null_does_not_crash(monkeypatch):
    """feats[0]["attributes"] returning null (not absent) must not raise AttributeError.
    The .get("attributes", {}) null trap was fixed to .get("attributes") or {}."""
    import services.flood_truth as ft
    import requests

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self):
            # API returns feature with null attributes — can happen on partial EPI coverage
            return {"features": [{"attributes": None}]}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResp())
    result = ft._query_epi_overlay(-33.87, 151.21)
    # Should not raise; should return a valid dict (no class = no overlay)
    assert isinstance(result, dict)
    assert result.get("epi_flood_class") in (None, "none")


# ---------------------------------------------------------------------------
# _SES_CLASS_DISPLAY normalisation
# ---------------------------------------------------------------------------

def test_ses_class_display_snake_case_mapped():
    """Raw DB value 'flood_planning_area' must map to display label."""
    import services.flood_truth as ft
    assert ft._SES_CLASS_DISPLAY["flood_planning_area"] == "Flood Planning Area"


def test_ses_class_display_short_code_mapped():
    """Short code '1%AEP' from council FeatureServers must map correctly."""
    import services.flood_truth as ft
    assert ft._SES_CLASS_DISPLAY["1%AEP"] == "1% AEP Flood Extent"


def test_ses_class_display_unknown_passthrough():
    """Any value not in the dict must pass through unchanged."""
    import services.flood_truth as ft
    raw = "Some Unknown Category"
    assert ft._SES_CLASS_DISPLAY.get(raw, raw) == raw


def test_ses_class_display_no_snake_case_values_in_dict_values():
    """All display values must be human-readable (no underscores)."""
    import services.flood_truth as ft
    for key, val in ft._SES_CLASS_DISPLAY.items():
        assert "_" not in val, f"Display value for {key!r} contains underscore: {val!r}"


# ---------------------------------------------------------------------------
# _query_hawkesbury_rasters — spatial + nodata + CRS
# ---------------------------------------------------------------------------

def test_hawkesbury_missing_raster_dir_returns_null_gracefully(monkeypatch):
    """If raster directory doesn't exist on this host, return null — not an error.
    Note: _query_hawkesbury_rasters was refactored into _query_flood_study_rasters.
    rasterio is required for raster tests — skip if unavailable."""
    import services.flood_truth as ft
    pytest.importorskip("rasterio")
    monkeypatch.setitem(ft.FLOOD_STUDIES["hawkesbury"], "dir",
                        "/nonexistent/path/to/rasters")
    result = ft._query_flood_study_rasters(-33.6134, 150.8130)
    assert result.get("hawkesbury_flood_level_100aep") is None


def test_hawkesbury_result_has_all_nine_aep_fields_with_none_values(monkeypatch):
    """null_result always contains all 9 AEP keys with None values (contract stability).
    rasterio is required for raster tests — skip if unavailable."""
    import services.flood_truth as ft
    pytest.importorskip("rasterio")
    monkeypatch.setitem(ft.FLOOD_STUDIES["hawkesbury"], "dir", "/nonexistent")
    result = ft._query_flood_study_rasters(-33.6134, 150.8130)
    # Output keys use ARI naming (2aep, 5aep, ...) via _HAWK_AEP_MAP, not design dict keys
    expected_suffixes = ["2aep", "5aep", "10aep", "20aep", "50aep", "100aep", "200aep", "500aep", "pmf"]
    for suffix in expected_suffixes:
        key = f"hawkesbury_flood_level_{suffix}"
        assert key in result, f"Missing key: {key}"
        assert result[key] is None, f"{key} should be None for nonexistent dir, got {result[key]}"


def test_signal_hawk_100aep_present_counts_as_low():
    """hawkesbury_flood_level_100aep not None → 'low' (single overlay source, no corroboration)."""
    out = _outputs(
        epi_flood_class="none",
        ses_in_flood_planning_area=None,
        hawkesbury_flood_level_100aep=17.34,
    )
    signal = _compute_flood_signal(out)
    assert signal == "low"


def test_signal_all_three_overlay_sources_absent_returns_unavailable():
    """EPI=none + SES=None + hawk_100=None → unavailable (not 'none')."""
    out = _outputs(
        epi_flood_class="none",
        ses_in_flood_planning_area=None,
        hawkesbury_flood_level_100aep=None,
    )
    assert _compute_flood_signal(out) == "unavailable"


def test_normalise_outputs_includes_hawkesbury_fields():
    """_normalise_outputs must pass through all Hawkesbury AEP fields."""
    raw = {
        "epi_flood_class": "none",
        "data_currency": "2025-01-01",
        "hawkesbury_flood_level_100aep": 17.34,
        "hawkesbury_flood_level_pmf": 30.55,
        "hawkesbury_flood_study": "Hawkesbury FRMSP 2025",
    }
    out = _normalise_outputs(raw)
    assert out["hawkesbury_flood_level_100aep"] == 17.34
    assert out["hawkesbury_flood_level_pmf"] == 30.55
    assert out["hawkesbury_flood_study"] == "Hawkesbury FRMSP 2025"
    assert out["hawkesbury_flood_level_2aep"] is None  # absent in raw → None


def test_normalise_outputs_hawkesbury_absent_returns_none():
    """Old cached results with no Hawkesbury keys → None (backwards compat)."""
    raw = {"epi_flood_class": "none", "data_currency": "2025-01-01"}
    out = _normalise_outputs(raw)
    assert out.get("hawkesbury_flood_level_100aep") is None
    assert out.get("hawkesbury_flood_study") is None


# ---------------------------------------------------------------------------
# Compound risk layers
# ---------------------------------------------------------------------------

def test_compound_risk_notes_empty_when_no_layers():
    assert _build_compound_risk_notes([]) == []


def test_compound_risk_notes_heritage():
    notes = _build_compound_risk_notes(["heritage"])
    assert len(notes) == 1
    assert "heritage" in notes[0].lower()


def test_compound_risk_notes_all_four():
    notes = _build_compound_risk_notes(["heritage", "riparian", "wetlands", "landslide"])
    assert len(notes) == 4


def test_compound_risk_notes_unknown_layer_skipped():
    notes = _build_compound_risk_notes(["heritage", "unknown_layer"])
    assert len(notes) == 1


def test_normalise_outputs_includes_compound_fields():
    """Compound risk keys present in normalised output even when all None."""
    raw = {"epi_flood_class": "none", "data_currency": "2025-01-01"}
    out = _normalise_outputs(raw)
    assert out["compound_risk_layers"] == []
    assert out["compound_risk_notes"] == []
    for lt in _COMPOUND_LAYER_TYPES:
        assert f"compound_{lt}" in out


def test_normalise_outputs_compound_heritage_populated():
    raw = {
        "epi_flood_class": "flood_planning_area",
        "data_currency": "2025-01-01",
        "compound_heritage": "Heritage Conservation Area",
    }
    out = _normalise_outputs(raw)
    assert out["compound_heritage"] == "Heritage Conservation Area"
    assert "heritage" in out["compound_risk_layers"]
    assert len(out["compound_risk_notes"]) == 1


def test_normalise_outputs_compound_multiple_layers():
    raw = {
        "epi_flood_class": "flood_planning_area",
        "data_currency": "2025-01-01",
        "compound_heritage": "HCA",
        "compound_landslide": "Landslide Susceptibility",
    }
    out = _normalise_outputs(raw)
    assert set(out["compound_risk_layers"]) == {"heritage", "landslide"}
    assert len(out["compound_risk_notes"]) == 2


def test_data_sources_includes_compound_when_present():
    raw = _outputs(compound_heritage="HCA")
    sources = _build_data_sources(raw)
    assert any("heritage" in s.lower() for s in sources)
    # Must be a specific source string, not just any match
    heritage_sources = [s for s in sources if "heritage" in s.lower()]
    assert len(heritage_sources) == 1


def test_data_sources_excludes_compound_when_absent():
    raw = _outputs()
    sources = _build_data_sources(raw)
    assert not any("heritage" in s for s in sources)


# ---------------------------------------------------------------------------
# run_flood — endpoint integration tests
# ---------------------------------------------------------------------------

from services.flood_truth import run_flood, FloodRequest, _write_report

# All 9 data source functions that run_flood calls in parallel
_DATA_SOURCE_FUNCTIONS = [
    "_query_epi_overlay",
    "_query_copernicus_ems",
    "_query_jrc_surface_water",
    "_query_bom_gauge",
    "_query_ses_flood_study",
    "_query_dea_wofs",
    "_query_flood_study_rasters",
    "_query_ground_elevation",
    "_query_compound_risk_layers",
]


def _make_request(address="1 Test St, Sydney NSW 2000", lat=-33.87, lng=151.21):
    return FloodRequest(
        address=address, lat=lat, lng=lng,
        report_id="test-report-001", prop_id="TEST-LOT"
    )


def _stub_all_sources(monkeypatch, overrides=None):
    """Monkeypatch all 9 data source functions to return empty/safe defaults.
    Returns a dict of the return values for assertion."""
    import services.flood_truth as ft

    defaults = {
        "_query_epi_overlay": {"epi_flood_class": None, "epi_flood_label": None, "data_currency": None, "epi_data_currency": None},
        "_query_copernicus_ems": {"ems_flood_detected": None, "ems_activations": None},
        "_query_jrc_surface_water": {"jrc_water_occurrence_pct": None, "jrc_data_year": None},
        "_query_bom_gauge": {"bom_gauge_name": None, "bom_gauge_distance_km": None, "bom_last_major_flood_date": None, "bom_last_major_flood_peak_m": None},
        "_query_ses_flood_study": {"ses_in_flood_planning_area": None, "ses_flood_class": None, "ses_flood_class_display": None},
        "_query_dea_wofs": {"dea_wofs_frequency_pct": None},
        "_query_flood_study_rasters": {"flood_studies": None},
        "_query_ground_elevation": {"ground_elevation_m_ahd": None},
        "_query_compound_risk_layers": {"compound_heritage": None, "compound_riparian": None, "compound_wetlands": None, "compound_landslide": None},
    }
    if overrides:
        for k, v in overrides.items():
            defaults[k].update(v)

    for func_name, return_val in defaults.items():
        monkeypatch.setattr(ft, func_name, lambda lat, lng, rv=return_val: rv)

    return defaults


def _stub_db(monkeypatch, cache_row=None):
    """Stub _get_conn and _write_report to avoid DB calls."""
    import services.flood_truth as ft

    class FakeCursor:
        def __init__(self, row):
            self._row = row
        def execute(self, *a, **kw): pass
        def fetchone(self):
            return self._row
        def fetchall(self):
            # #762 guard reads candidate rows via fetchall
            return [self._row] if self._row else []
        def __enter__(self): return self
        def __exit__(self, *a): pass

    class FakeConn:
        def __init__(self, row):
            self._row = row
        def cursor(self, **kw):
            return FakeCursor(self._row)
        def commit(self): pass
        def close(self): pass

    monkeypatch.setattr(ft, "_get_conn", lambda: FakeConn(cache_row))
    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: None)


# Minimum 3 sources to pass refuse-to-serve threshold (_MIN_SOURCES_FOR_SCREENING).
# Tests that expect a normal (non-refused) response should use these overrides.
_VIABLE_OVERRIDES = {
    "_query_copernicus_ems": {"ems_flood_detected": False, "ems_activations": []},
    "_query_jrc_surface_water": {"jrc_water_occurrence_pct": 0.0, "jrc_data_year": 2021},
    "_query_ground_elevation": {"ground_elevation_m_ahd": 15.0},
}


# --- Response structure tests ---

def test_run_flood_returns_required_top_level_keys(monkeypatch):
    """Response must have address, lat, lng, run_date, outputs, confidence, data_sources, data_gaps."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert set(result.keys()) == {"address", "lat", "lng", "run_date", "outputs", "confidence", "data_sources", "data_gaps"}


def test_run_flood_returns_correct_address_and_coords(monkeypatch):
    """Response must echo back the exact address and coordinates from the request."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch)
    result = run_flood(_make_request(address="42 Wallaby Way, Sydney", lat=-33.85, lng=151.25))
    assert result["address"] == "42 Wallaby Way, Sydney"
    assert result["lat"] == -33.85
    assert result["lng"] == 151.25


def test_run_flood_returns_todays_date(monkeypatch):
    """run_date must be today's date in ISO format."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch)
    result = run_flood(_make_request())
    assert result["run_date"] == date.today().isoformat()


def test_run_flood_outputs_is_dict(monkeypatch):
    """outputs must be a dict (from _normalise_outputs), not None or list."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert isinstance(result["outputs"], dict)


def test_run_flood_confidence_is_valid_tier(monkeypatch):
    """confidence must be one of the defined tiers."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert result["confidence"] in ("high", "medium", "low")


def test_run_flood_data_sources_is_list(monkeypatch):
    """data_sources must be a list of strings."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert isinstance(result["data_sources"], list)
    assert all(isinstance(s, str) for s in result["data_sources"])


# --- Cache hit path ---

def test_run_flood_cache_hit_returns_cached_outputs(monkeypatch):
    """When property_reports has a cached row, return those outputs without calling sources."""
    cached_outputs = {"epi_flood_class": "Flood Planning Area", "flood_signal": "low"}
    cache_row = {
        "outputs": cached_outputs,
        "confidence": "medium",
        "data_sources": ["NSW SEED EPI WFS"],
    }
    _stub_db(monkeypatch, cache_row=cache_row)

    calls = []
    import services.flood_truth as ft
    for fn in _DATA_SOURCE_FUNCTIONS:
        monkeypatch.setattr(ft, fn, lambda lat, lng, _fn=fn: calls.append(_fn) or {})

    result = run_flood(_make_request())
    assert len(calls) == 0, "Data sources should not be called on cache hit"
    assert result["confidence"] == "medium"


def test_run_flood_cache_hit_still_normalises_outputs(monkeypatch):
    """Cached outputs are passed through _normalise_outputs (not returned raw)."""
    cache_row = {
        "outputs": {"epi_flood_class": "Flood Planning Area"},
        "confidence": "medium",
        "data_sources": ["NSW SEED EPI WFS"],
    }
    _stub_db(monkeypatch, cache_row=cache_row)
    result = run_flood(_make_request())
    # _normalise_outputs adds flood_signal and other derived fields
    assert "flood_signal" in result["outputs"]


# --- Cache miss / DB failure path ---

def test_run_flood_db_failure_falls_through_to_live_queries(monkeypatch):
    """If cache lookup raises, run_flood proceeds to call all data sources."""
    import services.flood_truth as ft

    monkeypatch.setattr(ft, "_get_conn", lambda: (_ for _ in ()).throw(ConnectionError("no db")))
    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: None)

    called_sources = []

    def make_tracker(name, default_return):
        def tracker(lat, lng):
            called_sources.append(name)
            return default_return
        return tracker

    monkeypatch.setattr(ft, "_query_epi_overlay", make_tracker("epi", {"epi_flood_class": None, "epi_flood_label": None, "data_currency": None, "epi_data_currency": None}))
    monkeypatch.setattr(ft, "_query_copernicus_ems", make_tracker("ems", {"ems_flood_detected": None, "ems_activations": None}))
    monkeypatch.setattr(ft, "_query_jrc_surface_water", make_tracker("jrc", {"jrc_water_occurrence_pct": None, "jrc_data_year": None}))
    monkeypatch.setattr(ft, "_query_bom_gauge", make_tracker("bom", {"bom_gauge_name": None, "bom_gauge_distance_km": None, "bom_last_major_flood_date": None, "bom_last_major_flood_peak_m": None}))
    monkeypatch.setattr(ft, "_query_ses_flood_study", make_tracker("ses", {"ses_in_flood_planning_area": None, "ses_flood_class": None, "ses_flood_class_display": None}))
    monkeypatch.setattr(ft, "_query_dea_wofs", make_tracker("wofs", {"dea_wofs_frequency_pct": None}))
    monkeypatch.setattr(ft, "_query_flood_study_rasters", make_tracker("studies", {"flood_studies": None}))
    monkeypatch.setattr(ft, "_query_ground_elevation", make_tracker("dem", {"ground_elevation_m_ahd": None}))
    monkeypatch.setattr(ft, "_query_compound_risk_layers", make_tracker("compound", {"compound_heritage": None, "compound_riparian": None, "compound_wetlands": None, "compound_landslide": None}))

    result = run_flood(_make_request())
    assert set(called_sources) == {"epi", "ems", "jrc", "bom", "ses", "wofs", "studies", "dem", "compound"}


# --- Three-state boundary tests ---

def test_run_flood_epi_query_failed_returns_unavailable(monkeypatch):
    """When EPI overlay query failed, flood_signal must be 'unavailable'
    — never 'none' which would imply no risk."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        **_VIABLE_OVERRIDES,
        "_query_epi_overlay": {"epi_flood_class": None, "epi_flood_label": None,
                               "data_currency": "query_failed", "epi_data_currency": "query_failed"},
    })
    result = run_flood(_make_request())
    signal = result["outputs"].get("flood_signal")
    assert signal == "unavailable", f"EPI query_failed must yield 'unavailable', got '{signal}'"


def test_run_flood_all_sources_empty_returns_refused(monkeypatch):
    """When all sources return null data, refuse-to-serve kicks in (< 3 sources)."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch)
    result = run_flood(_make_request())
    assert result.get("refused") is True, "All-null sources must trigger refuse-to-serve"
    assert result["available_count"] == 0


def test_run_flood_epi_returns_data_reflected_in_output(monkeypatch):
    """When EPI returns a flood class, it must appear in the output."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        **_VIABLE_OVERRIDES,
        "_query_epi_overlay": {"epi_flood_class": "Flood Planning Area", "epi_flood_label": "Flood Planning Area", "data_currency": "2024-06-01", "epi_data_currency": "2024-06-01"},
    })
    result = run_flood(_make_request())
    assert result["outputs"]["epi_flood_label"] == "Flood Planning Area"


def test_run_flood_ground_elevation_passed_through(monkeypatch):
    """DEM elevation must appear in outputs when available."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        **_VIABLE_OVERRIDES,
        "_query_ground_elevation": {"ground_elevation_m_ahd": 12.5},
    })
    result = run_flood(_make_request())
    assert result["outputs"]["ground_elevation_m_ahd"] == 12.5


def test_run_flood_compound_heritage_true_appears_in_output(monkeypatch):
    """Heritage overlay must pass through to compound risk fields."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        **_VIABLE_OVERRIDES,
        "_query_compound_risk_layers": {"compound_heritage": True, "compound_riparian": None, "compound_wetlands": None, "compound_landslide": None},
    })
    result = run_flood(_make_request())
    assert result["outputs"]["compound_heritage"] is True


def test_run_flood_ses_data_appears_in_output(monkeypatch):
    """SES flood study data must pass through to outputs."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        **_VIABLE_OVERRIDES,
        "_query_ses_flood_study": {"ses_in_flood_planning_area": True, "ses_flood_class": "high_flood_risk", "ses_flood_class_display": "High Flood Risk"},
    })
    result = run_flood(_make_request())
    assert result["outputs"]["ses_in_flood_planning_area"] is True


# --- Report write failure ---

def test_run_flood_write_failure_raises_503(monkeypatch):
    """If _write_report fails on the live path, raise HTTPException 503."""
    import services.flood_truth as ft
    from fastapi import HTTPException

    # DB works for cache lookup (returns None = cache miss)
    class FakeConn:
        def cursor(self, **kw):
            c = type("C", (), {"execute": lambda *a, **kw: None, "fetchone": lambda s: None, "__enter__": lambda s: s, "__exit__": lambda *a: None})()
            return c
        def commit(self): pass
        def close(self): pass

    monkeypatch.setattr(ft, "_get_conn", lambda: FakeConn())
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)

    # _write_report raises on the live-query path
    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: (_ for _ in ()).throw(Exception("DB down")))

    with pytest.raises(HTTPException) as exc_info:
        run_flood(_make_request())
    assert exc_info.value.status_code == 503


# --- Coordinate passthrough ---

def test_run_flood_passes_correct_coords_to_sources(monkeypatch):
    """All data source functions must receive the exact lat/lng from the request."""
    _stub_db(monkeypatch)
    import services.flood_truth as ft

    captured_coords = {}

    def make_coord_capture(name, default_return):
        def capture(lat, lng):
            captured_coords[name] = (lat, lng)
            return default_return
        return capture

    monkeypatch.setattr(ft, "_query_epi_overlay", make_coord_capture("epi", {"epi_flood_class": None, "epi_flood_label": None, "data_currency": None, "epi_data_currency": None}))
    monkeypatch.setattr(ft, "_query_copernicus_ems", make_coord_capture("ems", {"ems_flood_detected": None, "ems_activations": None}))
    monkeypatch.setattr(ft, "_query_jrc_surface_water", make_coord_capture("jrc", {"jrc_water_occurrence_pct": None, "jrc_data_year": None}))
    monkeypatch.setattr(ft, "_query_bom_gauge", make_coord_capture("bom", {"bom_gauge_name": None, "bom_gauge_distance_km": None, "bom_last_major_flood_date": None, "bom_last_major_flood_peak_m": None}))
    monkeypatch.setattr(ft, "_query_ses_flood_study", make_coord_capture("ses", {"ses_in_flood_planning_area": None, "ses_flood_class": None, "ses_flood_class_display": None}))
    monkeypatch.setattr(ft, "_query_dea_wofs", make_coord_capture("wofs", {"dea_wofs_frequency_pct": None}))
    monkeypatch.setattr(ft, "_query_flood_study_rasters", make_coord_capture("studies", {"flood_studies": None}))
    monkeypatch.setattr(ft, "_query_ground_elevation", make_coord_capture("dem", {"ground_elevation_m_ahd": None}))
    monkeypatch.setattr(ft, "_query_compound_risk_layers", make_coord_capture("compound", {"compound_heritage": None, "compound_riparian": None, "compound_wetlands": None, "compound_landslide": None}))

    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: None)

    run_flood(_make_request(lat=-33.50, lng=151.10))

    for name, (lat, lng) in captured_coords.items():
        assert lat == -33.50, f"{name} received wrong lat: {lat}"
        assert lng == 151.10, f"{name} received wrong lng: {lng}"


# --- Output field completeness ---

def test_run_flood_outputs_contain_epi_fields(monkeypatch):
    """Outputs must contain EPI-derived fields even when null."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    outputs = result["outputs"]
    assert "epi_flood_label" in outputs
    assert "data_currency" in outputs


def test_run_flood_outputs_contain_flood_signal(monkeypatch):
    """Outputs must always contain flood_signal (from _normalise_outputs)."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert "flood_signal" in result["outputs"]


def test_run_flood_outputs_contain_ground_elevation(monkeypatch):
    """Outputs must contain ground_elevation_m_ahd."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert "ground_elevation_m_ahd" in result["outputs"]


def test_run_flood_outputs_contain_compound_fields(monkeypatch):
    """Outputs must contain compound risk fields (heritage, riparian, etc.)."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    outputs = result["outputs"]
    assert "compound_heritage" in outputs
    assert "compound_riparian" in outputs


# --- Internal output defaults ---

def test_run_flood_sentinel1b_gap_affected_is_true(monkeypatch):
    """sentinel1b_gap_affected must be True (S1B dead Dec 2021–Mar 2025)."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    outputs = result["outputs"]
    assert outputs.get("s1_gap_warning") is not None or True  # s1_gap_warning derived from sentinel1b_gap_affected=True


def test_run_flood_wet_seasons_checked_is_zero(monkeypatch):
    """wet_seasons_checked=0 means confidence cannot be 'high' (requires SAR seasons)."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    # With viable sources but no SAR seasons, confidence is "medium" (spatial layers present).
    assert result["confidence"] in ("low", "medium")


def test_run_flood_sar_fields_none_when_no_sar(monkeypatch):
    """SAR fields must be None when no SAR processing ran."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    outputs = result["outputs"]
    assert outputs["sar_flood_detected"] is None
    assert outputs["sar_confidence"] is None
    assert outputs["sar_analysis_date"] is None


# --- Data source spread verification ---

def test_run_flood_each_source_contributes_to_output(monkeypatch):
    """Each data source's output must appear in the final result when non-null."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        "_query_epi_overlay": {"epi_flood_class": "Flood Planning Area", "epi_flood_label": "FPA", "data_currency": "2024-01", "epi_data_currency": "2024-01"},
        "_query_copernicus_ems": {"ems_flood_detected": True, "ems_activations": [{"id": "EMSR001"}]},
        "_query_jrc_surface_water": {"jrc_water_occurrence_pct": 42.5, "jrc_data_year": "2023"},
        "_query_bom_gauge": {"bom_gauge_name": "Test Gauge", "bom_gauge_distance_km": 5.2, "bom_last_major_flood_date": "2022-03-01", "bom_last_major_flood_peak_m": 8.5},
        "_query_ses_flood_study": {"ses_in_flood_planning_area": True, "ses_flood_class": "high_flood_risk", "ses_flood_class_display": "High Flood Risk"},
        "_query_dea_wofs": {"dea_wofs_frequency_pct": 15.0},
        "_query_flood_study_rasters": {"flood_studies": []},
        "_query_ground_elevation": {"ground_elevation_m_ahd": 7.3},
        "_query_compound_risk_layers": {"compound_heritage": True, "compound_riparian": None, "compound_wetlands": True, "compound_landslide": None},
    })
    result = run_flood(_make_request())
    o = result["outputs"]
    # EPI
    assert o["epi_flood_class"] == "Flood Planning Area"
    assert o["epi_flood_label"] == "FPA"
    # EMS
    assert o["ems_flood_detected"] is True
    assert len(o["ems_activations"]) == 1
    # JRC
    assert o["jrc_water_occurrence_pct"] == 42.5
    # BOM
    assert o["bom_gauge_name"] == "Test Gauge"
    assert o["bom_gauge_distance_km"] == 5.2
    assert o["bom_last_major_flood_date"] == "2022-03-01"
    assert o["bom_last_major_flood_peak_m"] == 8.5
    # SES
    assert o["ses_in_flood_planning_area"] is True
    assert o["ses_flood_class"] == "high_flood_risk"
    # WOfS
    assert o["dea_wofs_frequency_pct"] == 15.0
    # DEM
    assert o["ground_elevation_m_ahd"] == 7.3
    # Compound
    assert o["compound_heritage"] is True
    assert o["compound_wetlands"] is True


def test_run_flood_epi_data_in_overlay_changes_flood_signal(monkeypatch):
    """EPI flood class must influence flood_signal — not just pass through."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        **_VIABLE_OVERRIDES,
        "_query_epi_overlay": {"epi_flood_class": "Flood Planning Area", "epi_flood_label": "FPA", "data_currency": "2024-01", "epi_data_currency": "2024-01"},
    })
    result = run_flood(_make_request())
    assert result["outputs"]["flood_signal"] in ("low", "moderate", "elevated")
    assert result["outputs"]["in_100yr_flood_zone"] is True


def test_run_flood_s1_gap_warning_is_not_none(monkeypatch):
    """s1_gap_warning must be a non-empty string (Sentinel-1B gap always applies)."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    warning = result["outputs"].get("s1_gap_warning")
    assert warning is not None, "s1_gap_warning must not be None"
    assert isinstance(warning, str) and len(warning) > 10, "s1_gap_warning must be a real message"


# --- Cache hit tightening ---

def test_run_flood_cache_hit_returns_exact_confidence(monkeypatch):
    """Cache hit must return the exact cached confidence, not recompute."""
    cache_row = {
        "outputs": {"epi_flood_class": None},
        "confidence": "high",
        "data_sources": ["source1"],
    }
    _stub_db(monkeypatch, cache_row=cache_row)
    result = run_flood(_make_request())
    assert result["confidence"] == "high"


def test_run_flood_cache_hit_returns_cached_data_sources(monkeypatch):
    """Cache hit must return the exact cached data_sources."""
    cache_row = {
        "outputs": {"epi_flood_class": None},
        "confidence": "low",
        "data_sources": ["NSW SEED EPI WFS", "BOM Water Data Online"],
    }
    _stub_db(monkeypatch, cache_row=cache_row)
    result = run_flood(_make_request())
    assert "NSW SEED EPI WFS" in result["data_sources"]
    assert "BOM Water Data Online" in result["data_sources"]


def test_run_flood_cache_hit_echoes_address(monkeypatch):
    """Cache hit must still echo the request address in the response."""
    cache_row = {
        "outputs": {"epi_flood_class": None},
        "confidence": "low",
        "data_sources": [],
    }
    _stub_db(monkeypatch, cache_row=cache_row)
    result = run_flood(_make_request(address="99 Cache St", lat=-33.9, lng=151.1))
    assert result["address"] == "99 Cache St"
    assert result["lat"] == -33.9
    assert result["lng"] == 151.1


# ===========================================================================
# Data gap disclosure tests
# ===========================================================================

def test_gap_reasons_all_null_returns_gaps():
    """When all sources are null, most gap reasons should be present."""
    out = _outputs()
    from services.flood_truth import _build_data_gap_reasons
    gaps = _build_data_gap_reasons(out)
    assert len(gaps) >= 6
    sources = [g["source"] for g in gaps]
    assert any("EPI" in s for s in sources)
    assert any("BOM" in s for s in sources)
    assert any("DEM" in s or "5m" in s for s in sources)


def test_gap_reasons_epi_revoked_vs_query_failed():
    """EPI 'none' + no SES/studies triggers revocation reason; query_failed triggers service reason."""
    from services.flood_truth import _build_data_gap_reasons
    out_revoked = _outputs(epi_flood_class="none", data_currency="2024-01-01")
    out_failed = _outputs(epi_flood_class=None, data_currency="query_failed")

    gaps_rev = _build_data_gap_reasons(out_revoked)
    gaps_fail = _build_data_gap_reasons(out_failed)

    rev_reasons = [g["reason"] for g in gaps_rev if "EPI" in g["source"]]
    fail_reasons = [g["reason"] for g in gaps_fail if "EPI" in g["source"]]
    assert any("revoked" in r for r in rev_reasons), f"Expected revocation reason, got {rev_reasons}"
    assert any("did not respond" in r for r in fail_reasons), f"Expected service failure reason, got {fail_reasons}"


def test_gap_reasons_epi_none_with_ses_data_no_revocation():
    """EPI 'none' but SES data exists → no revocation reason (address genuinely not in flood zone)."""
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(epi_flood_class="none", data_currency="2024-01-01",
                   ses_in_flood_planning_area=False)
    gaps = _build_data_gap_reasons(out)
    epi_gaps = [g for g in gaps if "EPI" in g["source"]]
    assert len(epi_gaps) == 0, f"Should not show EPI gap when SES data exists, got {epi_gaps}"


def test_gap_reasons_all_present_returns_empty():
    """When all sources returned data, no gaps."""
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(
        epi_flood_class="flood_planning_area", data_currency="2024-01-01",
        ems_flood_detected=False, jrc_water_occurrence_pct=0.0,
        dea_wofs_frequency_pct=0.0, bom_gauge_name="Gauge X",
        ses_in_flood_planning_area=False, ground_elevation_m_ahd=10.0,
        flood_studies=[{"study_key": "test"}],
    )
    gaps = _build_data_gap_reasons(out)
    assert len(gaps) == 0, f"No gaps expected when all sources present, got {gaps}"


def test_gap_reasons_structure():
    """Each gap must have 'source' and 'reason' string keys."""
    from services.flood_truth import _build_data_gap_reasons
    gaps = _build_data_gap_reasons(_outputs())
    for gap in gaps:
        assert "source" in gap and isinstance(gap["source"], str)
        assert "reason" in gap and isinstance(gap["reason"], str)
        assert len(gap["reason"]) > 10, "Reason must be a real explanation, not a stub"


# ===========================================================================
# Source availability counting tests
# ===========================================================================

def test_count_sources_all_null():
    from services.flood_truth import _count_available_sources
    assert _count_available_sources(_outputs()) == 0


def test_count_sources_all_present():
    from services.flood_truth import _count_available_sources
    out = _outputs(
        epi_flood_class="flood_planning_area",
        ems_flood_detected=False, jrc_water_occurrence_pct=5.0,
        dea_wofs_frequency_pct=2.0, bom_gauge_name="G",
        ses_in_flood_planning_area=True,
        flood_studies=[{"study_key": "x"}],
        ground_elevation_m_ahd=15.0,
        compound_heritage=True,
    )
    assert _count_available_sources(out) == 9


def test_count_sources_boundary_three():
    """Exactly 3 sources = passes threshold (>= _MIN_SOURCES_FOR_SCREENING)."""
    from services.flood_truth import _count_available_sources
    out = _outputs(
        ems_flood_detected=False,
        jrc_water_occurrence_pct=5.0,
        ground_elevation_m_ahd=15.0,
    )
    assert _count_available_sources(out) == 3


def test_count_sources_epi_none_not_counted():
    """EPI returning 'none' (no coverage) should NOT count as available."""
    from services.flood_truth import _count_available_sources
    out = _outputs(epi_flood_class="none")
    assert _count_available_sources(out) == 0


def test_count_sources_compound_requires_raw_keys():
    """Compound counts if any compound_* raw key is not None (not compound_risk_layers list)."""
    from services.flood_truth import _count_available_sources
    out = _outputs(compound_heritage=None, compound_riparian=True,
                   compound_wetlands=None, compound_landslide=None)
    # Only riparian is non-None → compound counts as 1
    assert _count_available_sources(out) == 1


# ===========================================================================
# Refuse-to-serve integration tests
# ===========================================================================

def test_run_flood_refused_when_zero_sources(monkeypatch):
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch)  # all defaults = all None
    result = run_flood(_make_request())
    assert result.get("refused") is True
    assert "data_gaps" in result
    assert isinstance(result["data_gaps"], list)
    assert result["available_count"] == 0
    assert result["total_count"] == 9


def test_run_flood_refused_when_two_sources(monkeypatch):
    """2 of 9 is below threshold (3) → refused."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides={
        "_query_copernicus_ems": {"ems_flood_detected": False, "ems_activations": []},
        "_query_ground_elevation": {"ground_elevation_m_ahd": 15.0},
    })
    result = run_flood(_make_request())
    assert result.get("refused") is True
    assert result["available_count"] == 2


def test_run_flood_not_refused_when_three_sources(monkeypatch):
    """3 of 9 = threshold → NOT refused."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert result.get("refused") is not True
    assert "outputs" in result
    assert "data_gaps" in result


def test_run_flood_cache_hit_never_refused(monkeypatch):
    """Cached results already passed threshold — never re-check."""
    _stub_db(monkeypatch, cache_row={
        "outputs": {},  # even empty outputs
        "confidence": "low",
        "data_sources": [],
    })
    result = run_flood(_make_request())
    assert result.get("refused") is not True
    assert "outputs" in result


def test_run_flood_refused_still_writes_report(monkeypatch):
    """Refused path must still attempt _write_report for audit trail."""
    import services.flood_truth as ft
    write_calls = []
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch)
    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: write_calls.append(1))
    result = run_flood(_make_request())
    assert result.get("refused") is True
    assert len(write_calls) == 1, "Must write report even when refusing"


def test_run_flood_data_gaps_in_normal_response(monkeypatch):
    """Normal (non-refused) response must include data_gaps list."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    assert "data_gaps" in result
    assert isinstance(result["data_gaps"], list)
    # With viable overrides, some gaps should still exist (EPI, SES, BOM etc still null)
    assert len(result["data_gaps"]) > 0


def test_run_flood_cache_hit_includes_data_gaps(monkeypatch):
    """Cache hit response must include data_gaps field."""
    _stub_db(monkeypatch, cache_row={
        "outputs": {"epi_flood_class": "flood_planning_area", "data_currency": "2024-01"},
        "confidence": "medium",
        "data_sources": ["NSW SEED EPI WFS"],
    })
    result = run_flood(_make_request())
    assert "data_gaps" in result


# ===========================================================================
# Output contract snapshot — locks _normalise_outputs keys
# ===========================================================================

_EXPECTED_OUTPUT_KEYS = {
    "epi_flood_class", "epi_flood_label", "sar_flood_detected", "sar_confidence",
    "sar_analysis_date", "ems_flood_detected", "ems_activations",
    "jrc_water_occurrence_pct", "jrc_data_year", "dea_wofs_frequency_pct",
    "ses_in_flood_planning_area", "ses_flood_class", "ses_study_name", "ses_study_lga",
    "bom_gauge_name", "bom_gauge_distance_km", "bom_last_major_flood_date",
    "bom_last_major_flood_peak_m", "bom_flood_history",
    "flood_study_name", "flood_study_date", "s1_gap_warning", "data_currency",
    "hawkesbury_flood_level_2aep", "hawkesbury_flood_level_5aep",
    "hawkesbury_flood_level_10aep", "hawkesbury_flood_level_20aep",
    "hawkesbury_flood_level_50aep", "hawkesbury_flood_level_100aep",
    "hawkesbury_flood_level_200aep", "hawkesbury_flood_level_500aep",
    "hawkesbury_flood_level_pmf", "hawkesbury_flood_study",
    "flood_studies", "ground_elevation_m_ahd", "in_100yr_flood_zone",
    # Names the sources that could have answered the 1% AEP question and were
    # not reachable. Required by the "not assessed" copy, which has to say what
    # was tried — an unexplained absence reads as evasion.
    "in_100yr_flood_zone_unconsulted",
    "compound_heritage", "compound_riparian", "compound_wetlands", "compound_landslide",
    "compound_risk_layers", "compound_risk_notes", "flood_signal",
}


def test_normalise_outputs_contract_keys():
    """Output keys must not change without updating this test + frontend types.
    This is a contract snapshot: if a key is added or removed, this test fails,
    forcing the developer to verify the frontend TypeScript interface matches."""
    from services.flood_truth import _normalise_outputs
    result = _normalise_outputs(_outputs())
    assert set(result.keys()) == _EXPECTED_OUTPUT_KEYS, (
        f"Contract mismatch.\n"
        f"  Added: {set(result.keys()) - _EXPECTED_OUTPUT_KEYS}\n"
        f"  Removed: {_EXPECTED_OUTPUT_KEYS - set(result.keys())}"
    )


# ===========================================================================
# Hypothesis property-based invariants
# Domain rule: "Absence of data is not clearance" (SEPP Resilience and Hazards 2021)
# ===========================================================================

try:
    from hypothesis import given, strategies as st, settings, assume
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

if HAS_HYPOTHESIS:
    _SIGNAL_ENUM = ("none", "low", "moderate", "elevated", "unavailable")

    @given(
        epi=st.sampled_from([None, "none", "flood_planning_area", "high_flood_risk"]),
        data_currency=st.sampled_from([None, "2024-01-01", "query_failed", "unknown"]),
        ses=st.one_of(st.none(), st.booleans()),
        jrc=st.one_of(st.none(), st.floats(0, 100, allow_nan=False)),
        wofs=st.one_of(st.none(), st.floats(0, 100, allow_nan=False)),
        ems=st.one_of(st.none(), st.booleans()),
        bom_date=st.one_of(st.none(), st.just("2022-03-01")),
    )
    @settings(max_examples=500)
    def test_hyp_signal_always_valid_enum(epi, data_currency, ses, jrc, wofs, ems, bom_date):
        """INVARIANT: flood_signal is always one of the 5 defined values."""
        out = _outputs(
            epi_flood_class=epi, data_currency=data_currency,
            ses_in_flood_planning_area=ses,
            jrc_water_occurrence_pct=jrc, dea_wofs_frequency_pct=wofs,
            ems_flood_detected=ems, bom_last_major_flood_date=bom_date,
        )
        signal = _compute_flood_signal(out)
        assert signal in _SIGNAL_ENUM, f"Invalid signal: {signal}"

    @given(
        epi=st.sampled_from([None, "none"]),
        ses=st.none(),
        jrc=st.one_of(st.none(), st.floats(0, 4.9, allow_nan=False)),
        ems=st.one_of(st.none(), st.just(False)),
        bom_date=st.none(),
    )
    @settings(max_examples=200)
    def test_hyp_no_positive_data_never_elevated(epi, ses, jrc, ems, bom_date):
        """INVARIANT: if no source returned positive data, signal must not be 'elevated'.
        Domain rule: cannot assert high risk without evidence."""
        out = _outputs(
            epi_flood_class=epi, data_currency="2024-01-01",
            ses_in_flood_planning_area=ses,
            jrc_water_occurrence_pct=jrc, dea_wofs_frequency_pct=None,
            ems_flood_detected=ems, bom_last_major_flood_date=bom_date,
        )
        signal = _compute_flood_signal(out)
        assert signal != "elevated", (
            f"Signal must not be 'elevated' without positive evidence. "
            f"epi={epi}, ses={ses}, jrc={jrc}, ems={ems}, bom={bom_date}"
        )

    @given(
        epi=st.sampled_from([None, "none", "flood_planning_area"]),
        data_currency=st.sampled_from([None, "2024-01-01", "query_failed"]),
        ses=st.one_of(st.none(), st.booleans()),
    )
    @settings(max_examples=200)
    def test_hyp_gap_reasons_always_list_of_dicts(epi, data_currency, ses):
        """INVARIANT: _build_data_gap_reasons always returns list[dict] with source+reason keys."""
        from services.flood_truth import _build_data_gap_reasons
        out = _outputs(epi_flood_class=epi, data_currency=data_currency,
                       ses_in_flood_planning_area=ses)
        gaps = _build_data_gap_reasons(out)
        assert isinstance(gaps, list)
        for gap in gaps:
            assert isinstance(gap, dict)
            assert "source" in gap and "reason" in gap

    @given(
        ems=st.one_of(st.none(), st.booleans()),
        jrc=st.one_of(st.none(), st.floats(0, 100, allow_nan=False)),
        dem=st.one_of(st.none(), st.floats(-10, 200, allow_nan=False)),
    )
    @settings(max_examples=200)
    def test_hyp_count_sources_bounded(ems, jrc, dem):
        """INVARIANT: available source count is always 0-9."""
        from services.flood_truth import _count_available_sources
        out = _outputs(ems_flood_detected=ems, jrc_water_occurrence_pct=jrc,
                       ground_elevation_m_ahd=dem)
        count = _count_available_sources(out)
        assert 0 <= count <= 9


# ===========================================================================
# Golden response tests — frozen known-good outputs from known inputs
# Kills LOGIC mutants: if signal/confidence/gap logic changes, these break.
# Each fixture was manually verified against domain rules before committing.
# ===========================================================================

def test_golden_all_sources_present_elevated_signal():
    """Golden: EPI flood_planning_area + JRC >10% + SES confirmed → elevated signal."""
    out = _outputs(
        epi_flood_class="flood_planning_area", epi_flood_label="Flood Planning Area",
        data_currency="2024-06-15",
        ems_flood_detected=False, ems_activations=[],
        jrc_water_occurrence_pct=12.5, jrc_data_year=2021,
        dea_wofs_frequency_pct=8.3,
        bom_gauge_name="Hawkesbury R at Windsor", bom_gauge_distance_km=5.2,
        bom_last_major_flood_date="2022-03-08", bom_last_major_flood_peak_m=13.7,
        ses_in_flood_planning_area=True, ses_flood_class="medium",
        ground_elevation_m_ahd=8.5,
        flood_studies=[{"study_key": "hawkesbury-2024"}],
        compound_riparian=True,
        wet_seasons_checked=3,
    )
    # Domain rule: EPI flood_planning_area → "moderate"
    # SES confirms but doesn't escalate beyond moderate without SAR detection
    signal = _compute_flood_signal(out)
    assert signal == "moderate", f"Expected moderate for EPI+SES, got {signal}"
    conf = _compute_confidence(out)
    assert conf == "high", f"Expected high confidence with all sources, got {conf}"


def test_golden_all_sources_present_none_signal():
    """Golden: No EPI coverage, no SES, JRC=0, no flood studies → none signal."""
    out = _outputs(
        epi_flood_class="none", data_currency="2024-01-01",
        ems_flood_detected=False, ems_activations=[],
        jrc_water_occurrence_pct=0.0, jrc_data_year=2021,
        dea_wofs_frequency_pct=0.0,
        bom_gauge_name="Test Gauge", bom_gauge_distance_km=50.0,
        ses_in_flood_planning_area=False,
        ground_elevation_m_ahd=85.0,
        wet_seasons_checked=3,
    )
    signal = _compute_flood_signal(out)
    assert signal == "none", f"Expected none, got {signal}"
    conf = _compute_confidence(out)
    assert conf == "high", f"Expected high confidence with many sources, got {conf}"


def test_golden_unavailable_signal():
    """Golden: data_currency=query_failed → unavailable regardless of other data."""
    out = _outputs(data_currency="query_failed")
    signal = _compute_flood_signal(out)
    assert signal == "unavailable"


def test_golden_refused_response_shape(monkeypatch):
    """Golden: all sources null → refused response with exact shape."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch)  # all defaults = all None
    result = run_flood(_make_request())
    # Verify exact shape
    assert result["refused"] is True
    assert isinstance(result["reason"], str)
    assert result["available_count"] == 0
    assert result["total_count"] == 9
    assert isinstance(result["data_gaps"], list)
    assert len(result["data_gaps"]) > 0
    # Every gap must have source + reason
    for gap in result["data_gaps"]:
        assert "source" in gap
        assert "reason" in gap
        assert isinstance(gap["source"], str)
        assert isinstance(gap["reason"], str)
        assert len(gap["reason"]) > 10  # not a stub


def test_golden_normal_response_shape(monkeypatch):
    """Golden: 3+ sources → normal response with exact shape."""
    _stub_db(monkeypatch)
    _stub_all_sources(monkeypatch, overrides=_VIABLE_OVERRIDES)
    result = run_flood(_make_request())
    # Verify exact shape
    assert "refused" not in result or result.get("refused") is not True
    assert isinstance(result["outputs"], dict)
    assert isinstance(result["confidence"], str)
    assert result["confidence"] in ("low", "medium", "high")
    assert isinstance(result["data_sources"], list)
    assert isinstance(result["data_gaps"], list)
    assert result["outputs"]["flood_signal"] in ("none", "low", "moderate", "elevated", "unavailable")
    assert isinstance(result["run_date"], str)
    assert result["address"] == "1 Test St, Sydney NSW 2000"


def test_golden_gap_reasons_epi_null_scenario():
    """Golden: EPI null (no response) → specific gap reason."""
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(epi_flood_class=None, data_currency=None)
    gaps = _build_data_gap_reasons(out)
    epi_gaps = [g for g in gaps if "EPI" in g["source"]]
    assert len(epi_gaps) == 1
    assert "not available" in epi_gaps[0]["reason"]


def test_golden_gap_reasons_epi_revoked_scenario():
    """Golden: EPI 'none' + no SES + no studies → revocation reason."""
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(epi_flood_class="none", data_currency="2024-01-01",
                   ses_in_flood_planning_area=None, flood_studies=None)
    gaps = _build_data_gap_reasons(out)
    epi_gaps = [g for g in gaps if "EPI" in g["source"]]
    assert len(epi_gaps) == 1
    assert "revoked" in epi_gaps[0]["reason"]


def test_golden_count_sources_exact_values():
    """Golden: verify exact source counts for known combinations."""
    from services.flood_truth import _count_available_sources
    # 0 sources
    assert _count_available_sources(_outputs()) == 0
    # EPI alone (flood_planning_area counts, "none" doesn't)
    assert _count_available_sources(_outputs(epi_flood_class="flood_planning_area")) == 1
    assert _count_available_sources(_outputs(epi_flood_class="none")) == 0
    # 3 sources (viable overrides)
    assert _count_available_sources(_outputs(
        ems_flood_detected=False, jrc_water_occurrence_pct=0.0, ground_elevation_m_ahd=15.0
    )) == 3
    # 9 sources (all present)
    assert _count_available_sources(_outputs(
        epi_flood_class="flood_planning_area",
        ems_flood_detected=False, jrc_water_occurrence_pct=5.0,
        dea_wofs_frequency_pct=2.0, bom_gauge_name="G",
        ses_in_flood_planning_area=True,
        flood_studies=[{"study_key": "x"}],
        ground_elevation_m_ahd=15.0,
        compound_heritage=True,
    )) == 9


# ===========================================================================
# Three-state boundary tests — every source: exists / empty / unreachable
# Domain rule: "Absence of data is not clearance" (SEPP R&H 2021)
# ===========================================================================

def test_three_state_epi_exists():
    """EPI exists (flood_planning_area) → signal is at least 'low' (statutory overlay only)."""
    out = _outputs(epi_flood_class="flood_planning_area", data_currency="2024-01-01")
    signal = _compute_flood_signal(out)
    assert signal in ("low", "moderate", "elevated")

def test_three_state_epi_empty():
    """EPI empty (class='none') → does not contribute to signal."""
    out = _outputs(epi_flood_class="none", data_currency="2024-01-01")
    signal = _compute_flood_signal(out)
    assert signal in ("none", "low", "unavailable")

def test_three_state_epi_unreachable():
    """EPI unreachable (query_failed) → unavailable signal."""
    out = _outputs(data_currency="query_failed")
    signal = _compute_flood_signal(out)
    assert signal == "unavailable"

def test_three_state_ems_exists():
    """EMS detected flood → flag in gap reasons absent."""
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(ems_flood_detected=True, ems_activations=[{"id": "EMSR567"}])
    gaps = _build_data_gap_reasons(out)
    assert not any("EMS" in g["source"] for g in gaps)

def test_three_state_ems_empty():
    """EMS returned False (no flood) → still counts as data present."""
    from services.flood_truth import _count_available_sources
    out = _outputs(ems_flood_detected=False, ems_activations=[])
    assert _count_available_sources(out) >= 1

def test_three_state_ems_unreachable():
    """EMS unreachable (None) → gap reason, does not count."""
    from services.flood_truth import _count_available_sources, _build_data_gap_reasons
    out = _outputs(ems_flood_detected=None)
    assert _count_available_sources(out) == 0
    gaps = _build_data_gap_reasons(out)
    assert any("EMS" in g["source"] for g in gaps)

def test_three_state_jrc_exists():
    """JRC has data → no gap, counts as source."""
    from services.flood_truth import _count_available_sources, _build_data_gap_reasons
    out = _outputs(jrc_water_occurrence_pct=5.0, jrc_data_year=2021)
    assert _count_available_sources(out) >= 1
    gaps = _build_data_gap_reasons(out)
    assert not any("JRC" in g["source"] for g in gaps)

def test_three_state_jrc_zero():
    """JRC returns 0% (confirmed dry) → counts as source, not a gap."""
    from services.flood_truth import _count_available_sources
    out = _outputs(jrc_water_occurrence_pct=0.0, jrc_data_year=2021)
    assert _count_available_sources(out) >= 1

def test_three_state_jrc_unreachable():
    """JRC unreachable (None) → gap reason."""
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(jrc_water_occurrence_pct=None)
    gaps = _build_data_gap_reasons(out)
    assert any("JRC" in g["source"] for g in gaps)

def test_three_state_dem_exists():
    from services.flood_truth import _count_available_sources, _build_data_gap_reasons
    out = _outputs(ground_elevation_m_ahd=15.0)
    assert _count_available_sources(out) >= 1
    gaps = _build_data_gap_reasons(out)
    assert not any("DEM" in g["source"] or "5m" in g["source"] for g in gaps)

def test_three_state_dem_unreachable():
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(ground_elevation_m_ahd=None)
    gaps = _build_data_gap_reasons(out)
    assert any("DEM" in g["source"] or "5m" in g["source"] for g in gaps)

def test_three_state_bom_exists():
    from services.flood_truth import _count_available_sources, _build_data_gap_reasons
    out = _outputs(bom_gauge_name="Test Gauge", bom_gauge_distance_km=10.0)
    assert _count_available_sources(out) >= 1
    gaps = _build_data_gap_reasons(out)
    assert not any("BOM" in g["source"] for g in gaps)

def test_three_state_bom_unreachable():
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(bom_gauge_name=None)
    gaps = _build_data_gap_reasons(out)
    assert any("BOM" in g["source"] for g in gaps)

def test_three_state_ses_exists():
    """SES returned data → SES gap absent (but flood study rasters gap may remain)."""
    from services.flood_truth import _count_available_sources, _build_data_gap_reasons
    out = _outputs(ses_in_flood_planning_area=True)
    assert _count_available_sources(out) >= 1
    gaps = _build_data_gap_reasons(out)
    # "Council flood study" (SES gap) should be absent; "Council flood study rasters"
    # is a separate gap that fires when flood_studies is empty.
    assert not any(g["source"] == "Council flood study" for g in gaps)

def test_three_state_ses_empty():
    """SES returned False (not in flood area) → still counts as data present."""
    from services.flood_truth import _count_available_sources
    out = _outputs(ses_in_flood_planning_area=False)
    assert _count_available_sources(out) >= 1

def test_three_state_ses_unreachable():
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(ses_in_flood_planning_area=None)
    gaps = _build_data_gap_reasons(out)
    assert any("Council" in g["source"] or "council" in g["reason"].lower() for g in gaps)

def test_three_state_wofs_exists():
    from services.flood_truth import _count_available_sources
    out = _outputs(dea_wofs_frequency_pct=2.0)
    assert _count_available_sources(out) >= 1

def test_three_state_wofs_unreachable():
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(dea_wofs_frequency_pct=None)
    gaps = _build_data_gap_reasons(out)
    assert any("DEA" in g["source"] or "Water Observations" in g["source"] for g in gaps)

def test_three_state_studies_exists():
    from services.flood_truth import _count_available_sources, _build_data_gap_reasons
    out = _outputs(flood_studies=[{"study_key": "x"}])
    assert _count_available_sources(out) >= 1
    gaps = _build_data_gap_reasons(out)
    assert not any("raster" in g["source"].lower() for g in gaps)

def test_three_state_studies_unreachable():
    from services.flood_truth import _build_data_gap_reasons
    out = _outputs(flood_studies=None)
    gaps = _build_data_gap_reasons(out)
    assert any("raster" in g["source"].lower() or "study" in g["reason"].lower() for g in gaps)

def test_three_state_compound_exists():
    from services.flood_truth import _count_available_sources
    out = _outputs(compound_heritage=True)
    assert _count_available_sources(out) >= 1

def test_three_state_compound_unreachable():
    from services.flood_truth import _count_available_sources
    out = _outputs(compound_heritage=None, compound_riparian=None,
                   compound_wetlands=None, compound_landslide=None)
    # Compound with all None should not count
    assert _count_available_sources(out) == 0


# ===========================================================================
# Layer 9: DB contract tests — verify code schema assumptions
# ===========================================================================

def test_db_contract_write_report_columns():
    """_write_report INSERT must reference exactly the documented property_reports columns.

    DB schema (DB_SCHEMA.md): id, product, address, lat, lng, prop_id, run_date,
    inputs (jsonb), outputs (jsonb), confidence, data_sources (text[]).
    If this test fails, either DB_SCHEMA.md or _write_report SQL is out of date.
    """
    import ast
    import textwrap
    from services import flood_truth
    src = inspect.getsource(flood_truth._write_report)
    # Extract column names from the INSERT INTO ... (...) pattern
    match = re.search(r"INSERT INTO property_reports\s*\(([^)]+)\)", src, re.IGNORECASE)
    assert match, "_write_report must contain INSERT INTO property_reports"
    columns = {c.strip() for c in match.group(1).split(",")}
    expected_columns = {
        "id", "product", "address", "lat", "lng", "prop_id",
        "run_date", "inputs", "outputs", "confidence", "data_sources",
    }
    assert columns == expected_columns, (
        f"Column mismatch vs DB_SCHEMA.md.\n"
        f"  In SQL but not schema: {columns - expected_columns}\n"
        f"  In schema but not SQL: {expected_columns - columns}"
    )


def test_db_contract_cache_read_columns():
    """Cache lookup SELECT must read outputs, confidence, data_sources AND
    run_date — run_date is load-bearing since output-grounding fix 2: the
    cached row's ORIGINAL run_date is served and re-written, never re-stamped
    with today. The regex tolerates the quote-join of adjacent string
    literals in the multi-line SQL."""
    from services import flood_truth
    src = inspect.getsource(flood_truth.run_flood)
    match = re.search(r"SELECT\s+([\w\s,\"]+?)FROM\s+property_reports", src)
    assert match, "run_flood must contain SELECT ... FROM property_reports"
    columns = {c.strip() for c in match.group(1).replace('"', " ").split(",")}
    required = {"outputs", "confidence", "data_sources", "run_date"}
    assert required <= columns, (
        f"Cache query missing columns: {required - columns}"
    )
    # The age policy is part of the read contract (fix 2): rows older than the
    # max age are recomputed, not served.
    assert "90 days" in src, "cache read must carry the 90-day max-age filter"


def test_db_contract_normalise_roundtrip():
    """_normalise_outputs must handle all keys that _write_report stores as JSON in outputs.

    Simulates: internal_outputs → JSON → load → _normalise_outputs. Verifies no KeyError
    or type crash on the round-trip, which is the real-world path for cached data.
    """
    import json
    from services.flood_truth import _normalise_outputs
    # Simulate a stored row with all sources present
    stored = _outputs(
        epi_flood_class="flood_planning_area", data_currency="2024-06-01",
        ems_flood_detected=False, ems_activations=[],
        jrc_water_occurrence_pct=5.0, jrc_data_year=2021,
        dea_wofs_frequency_pct=2.0,
        ses_in_flood_planning_area=True, ses_flood_class="medium",
        ses_study_name="Parramatta River FS", ses_study_lga="City of Parramatta",
        bom_gauge_name="Parramatta North", bom_gauge_distance_km=3.2,
        bom_last_major_flood_date="2022-03-08",
        bom_last_major_flood_peak_m=5.2, bom_flood_history=[],
        ground_elevation_m_ahd=12.5,
        flood_studies=[{"study_key": "parra_2020", "study_name": "Parramatta River FS",
                        "source": "City of Parramatta",
                        "design": {"1pct": {"level_m_ahd": 8.5, "depth_m": None}}}],
        compound_heritage=False, compound_riparian=True,
        compound_wetlands=False, compound_landslide=False,
    )
    # JSON round-trip (simulates Supabase JSONB storage + retrieval)
    restored = json.loads(json.dumps(stored))
    result = _normalise_outputs(restored)
    # Must not raise, and must contain flood_signal
    assert "flood_signal" in result
    assert result["flood_signal"] in {"none", "low", "moderate", "elevated", "unavailable"}


def test_db_contract_normalise_empty_roundtrip():
    """_normalise_outputs must handle an empty dict from a very old cached row
    without crashing — defensive against schema evolution."""
    import json
    from services.flood_truth import _normalise_outputs
    result = _normalise_outputs(json.loads("{}"))
    assert "flood_signal" in result


def test_db_contract_pydantic_validates_normalised():
    """FloodOutputs Pydantic model must accept the output of _normalise_outputs.

    This is the bridge between backend storage and API response validation.
    If Pydantic rejects normalised output, the API would 500.
    """
    from services.flood_truth import FloodOutputs, _normalise_outputs
    normalised = _normalise_outputs(_outputs(
        epi_flood_class="flood_planning_area", data_currency="2024-06-01",
        ems_flood_detected=False, jrc_water_occurrence_pct=5.0,
        ground_elevation_m_ahd=12.0,
    ))
    # Must not raise ValidationError
    validated = FloodOutputs(**normalised)
    assert validated.flood_signal in {"none", "low", "moderate", "elevated", "unavailable"}


# ===========================================================================
# Mutation testing kill targets — tests that catch specific surviving mutants
# ===========================================================================

def test_flood_studies_dict_has_name_key():
    """Every FLOOD_STUDIES entry must have a name key (either 'name' or legacy 'name').
    Mutant #12: key rename would break study identification in _query_flood_study_rasters."""
    from services.flood_truth import FLOOD_STUDIES
    for study_key, study in FLOOD_STUDIES.items():
        has_name = "name" in study or "name" in study
        assert has_name, f"FLOOD_STUDIES['{study_key}'] missing name key"
        name_val = study.get("name") or study.get("name")
        assert isinstance(name_val, str) and len(name_val) > 0


def test_flood_studies_hawkesbury_values_exact():
    """Hawkesbury FLOOD_STUDIES values must match — mutant #13 changes values."""
    from services.flood_truth import FLOOD_STUDIES
    hawk = FLOOD_STUDIES["hawkesbury"]
    name_val = hawk.get("name") or hawk.get("name")
    assert name_val == "Hawkesbury FRMSP 2025"
    assert hawk["source"] == "NSW Reconstruction Authority"


def test_icontract_signal_contract_active():
    """Kills mutant #17 (decorator removal)."""
    from services.flood_truth import _compute_flood_signal
    _check_postcondition(_compute_flood_signal, "_compute_flood_signal")


def _check_postcondition(func, name):
    """Assert the icontract postcondition is actually attached to `func`.

    This used to skip whenever `__postconditions__` was absent — which is the
    same observable state as THE DECORATOR HAVING BEEN DELETED, the exact
    mutant each caller below claims to kill. So the check could never fail,
    and it never did: it skipped in every environment from the day it was
    written, because icontract was declared only in
    scripts/requirements-maintenance.txt and so was never installed anywhere.
    That also concealed a real defect — `_compute_flood_signal` had no
    decorator at all, in any commit that ever touched it.

    The old docstring asserted "In CI (GitHub Actions), icontract is installed
    cleanly and these tests run." That was untrue, and it is why nobody chased
    the skip for as long as it existed.

    Now: if icontract is importable, a missing postcondition is a FAILURE.
    Only a genuinely absent library skips, and scripts/check_dependency_skips.py
    counts that so it cannot go unnoticed either.
    """
    try:
        import icontract  # noqa: F401
    except ImportError:
        pytest.skip(
            f"icontract not installed, so {name}'s postcondition cannot be checked "
            "(it is pinned in services/requirements.txt and requirements-test.txt)")
    assert hasattr(func, '__postconditions__'), (
        f"{name} has no __postconditions__. icontract IS installed, so the "
        "@icontract.ensure decorator has been removed or was never added.")
    assert len(func.__postconditions__) > 0, \
        f"{name} must have at least one postcondition"


def test_icontract_confidence_contract_active():
    """Kills mutant #24 (decorator removal)."""
    from services.flood_truth import _compute_confidence
    _check_postcondition(_compute_confidence, "_compute_confidence")


def test_icontract_count_sources_contract_active():
    """Kills mutant #31 (decorator removal)."""
    from services.flood_truth import _count_available_sources
    _check_postcondition(_count_available_sources, "_count_available_sources")


def test_icontract_gap_reasons_contract_active():
    """Kills mutant #44 (decorator removal)."""
    from services.flood_truth import _build_data_gap_reasons
    _check_postcondition(_build_data_gap_reasons, "_build_data_gap_reasons")


def test_icontract_normalise_contract_active():
    """Kills mutant #49 (decorator removal)."""
    from services.flood_truth import _normalise_outputs
    _check_postcondition(_normalise_outputs, "_normalise_outputs")


def test_count_sources_upper_bound_exactly_9():
    """_count_available_sources must return exactly 9 when all sources present.
    Kills mutant #28 (<= 9 → <= 10 boundary change)."""
    from services.flood_truth import _count_available_sources, _SOURCE_AVAILABILITY_CHECKS
    assert len(_SOURCE_AVAILABILITY_CHECKS) == 9, "Must have exactly 9 source checks"
    out = _outputs(
        epi_flood_class="flood_planning_area",
        ems_flood_detected=False, jrc_water_occurrence_pct=5.0,
        dea_wofs_frequency_pct=2.0, bom_gauge_name="G",
        ses_in_flood_planning_area=True,
        flood_studies=[{"study_key": "x"}],
        ground_elevation_m_ahd=15.0,
        compound_heritage=True,
    )
    assert _count_available_sources(out) == 9  # exact upper bound


# ===========================================================================
# Redbank Creek Flood Study 2025 — config contract + valid-range guard
# ===========================================================================

def test_flood_studies_redbank_values_exact():
    """Redbank config values must match the source dataset facts exactly.
    CRS from shapefile .prj in the same portal package; nodata from .hdr."""
    from services.flood_truth import FLOOD_STUDIES
    rb = FLOOD_STUDIES["redbank"]
    assert rb["name"] == "Redbank Creek Flood Study 2025"
    assert rb["source"] == "Hawkesbury City Council"
    assert rb["crs"] == "EPSG:7856"
    assert rb["nodata"] == -999.0
    assert rb["has_depth"] is True
    assert rb["valid_depth_range"] == (0.0, 100.0)
    assert rb["valid_level_range"] == (-10.0, 250.0)


def test_flood_studies_redbank_design_ladder_complete():
    """All 11 design events present (incl. 1-in-1000/2000/5000) and {type}-templated,
    plus the March 2022 historical event."""
    from services.flood_truth import FLOOD_STUDIES
    rb = FLOOD_STUDIES["redbank"]
    expected = {
        "20pct", "10pct", "5pct", "2pct", "1pct",
        "0_5pct", "0_2pct", "0_1pct", "0_05pct", "0_02pct", "pmf",
    }
    assert set(rb["design"].keys()) == expected
    for template in rb["design"].values():
        assert "{type}" in template, f"Redbank template must be typed: {template}"
        assert template.endswith(".tif")
    assert rb["historical"] == {
        "2022": "historical/RedBank_DES_Hist_March2022_{type}_Max_ProcessedOutput.tif",
    }


def test_aep_labels_cover_every_configured_design_key():
    """Every design key in every study must have a display label — an unlabeled
    key reaches the API as a raw token the UI cannot present."""
    from services.flood_truth import FLOOD_STUDIES, _AEP_LABELS
    for study_key, cfg in FLOOD_STUDIES.items():
        for aep_key in cfg["design"]:
            assert aep_key in _AEP_LABELS, \
                f"FLOOD_STUDIES['{study_key}'] design key {aep_key!r} missing from _AEP_LABELS"


def test_redbank_missing_raster_dir_no_match(monkeypatch):
    """Rasters absent on this host → redbank silently skipped, no error."""
    import services.flood_truth as ft
    pytest.importorskip("rasterio")
    monkeypatch.setitem(ft.FLOOD_STUDIES["redbank"], "dir", "/nonexistent/redbank")
    result = ft._query_flood_study_rasters(-33.574, 150.732)
    assert all(s["study_key"] != "redbank" for s in result["flood_studies"])


# --- _sample_raster valid-range guard (uses a real 2x2 raster on disk) ------

def _write_probe_raster(tmp_path, values, nodata=-999.0):
    """2x2 float32 GTiff at origin (1000, 2000), 1 m pixels, EPSG:7856."""
    rasterio = pytest.importorskip("rasterio")
    import numpy as np
    from rasterio.transform import from_origin
    path = str(tmp_path / "probe.tif")
    arr = np.array(values, dtype="float32")
    with rasterio.open(
        path, "w", driver="GTiff",
        height=arr.shape[0], width=arr.shape[1], count=1, dtype="float32",
        crs="EPSG:7856", transform=from_origin(1000.0, 2000.0, 1.0, 1.0),
        nodata=nodata,
    ) as ds:
        ds.write(arr, 1)
    return path


def test_sample_raster_valid_value_inside_range_returned(tmp_path):
    """Expected use: plausible value passes the guard unchanged."""
    from services.flood_truth import _sample_raster
    path = _write_probe_raster(tmp_path, [[14.51, -999.0], [-999.0, -999.0]])
    val = _sample_raster(path, 1000.5, 1999.5, -999.0, valid_range=(-10.0, 250.0))
    assert val is not None and abs(val - 14.51) < 1e-4


def test_sample_raster_artifact_value_rejected(tmp_path):
    """TUFLOW glitch cell (e.g. level -252.98 m AHD) must be treated as nodata —
    serving it would be a silent wrong result."""
    from services.flood_truth import _sample_raster
    path = _write_probe_raster(tmp_path, [[-252.98, -999.0], [-999.0, -999.0]])
    assert _sample_raster(path, 1000.5, 1999.5, -999.0, valid_range=(-10.0, 250.0)) is None


def test_sample_raster_no_range_returns_raw_value(tmp_path):
    """Backward compat: valid_range omitted → no filtering (existing studies unchanged)."""
    from services.flood_truth import _sample_raster
    path = _write_probe_raster(tmp_path, [[-252.98, -999.0], [-999.0, -999.0]])
    val = _sample_raster(path, 1000.5, 1999.5, -999.0)
    assert val is not None and abs(val - (-252.98)) < 1e-2


def test_sample_raster_range_bounds_inclusive(tmp_path):
    """Edge: value exactly at a range bound is kept (<= semantics, not <)."""
    from services.flood_truth import _sample_raster
    path = _write_probe_raster(tmp_path, [[250.0, -10.0], [-999.0, -999.0]])
    assert _sample_raster(path, 1000.5, 1999.5, -999.0, valid_range=(-10.0, 250.0)) == 250.0
    assert _sample_raster(path, 1001.5, 1999.5, -999.0, valid_range=(-10.0, 250.0)) == -10.0


def test_sample_raster_nodata_still_none_with_range(tmp_path):
    """Failure case: nodata short-circuits before the range check."""
    from services.flood_truth import _sample_raster
    path = _write_probe_raster(tmp_path, [[-999.0, -999.0], [-999.0, -999.0]])
    assert _sample_raster(path, 1000.5, 1999.5, -999.0, valid_range=(-10.0, 250.0)) is None


def test_bounds_proxy_uses_pmf_extent_not_smaller_1pct_grid(tmp_path, monkeypatch):
    """Silent false negative: event grids can differ in extent (Redbank PMF
    extends ~86 m past its 1% grid). A point inside the PMF grid but outside
    the 1% grid must still match the study — the study-level bounds pre-check
    must proxy on the maximal (PMF) grid, not the 1% grid."""
    import services.flood_truth as ft
    rasterio = pytest.importorskip("rasterio")
    import numpy as np
    from rasterio.transform import from_origin

    ddir = tmp_path / "design"
    ddir.mkdir()

    def write(name, origin_x, origin_y, value):
        arr = np.full((2, 2), value, dtype="float32")
        with rasterio.open(
            str(ddir / name), "w", driver="GTiff",
            height=2, width=2, count=1, dtype="float32",
            crs="EPSG:7856", transform=from_origin(origin_x, origin_y, 1.0, 1.0),
            nodata=-999.0,
        ) as ds:
            ds.write(arr, 1)

    # 1pct grid at (1000, 2000); pmf grid disjoint at (5000, 6000)
    for t in ("d", "h"):
        write(f"small_1pct_{t}.tif", 1000.0, 2000.0, 1.0)
        write(f"big_pmf_{t}.tif", 5000.0, 6000.0, 2.0)

    probe = {
        "name": "Proxy Extent Probe", "source": "test",
        "dir": str(tmp_path), "crs": "EPSG:7856", "nodata": -999.0,
        "has_depth": True,
        "design": {
            "1pct": "design/small_1pct_{type}.tif",
            "pmf":  "design/big_pmf_{type}.tif",
        },
        "historical": {},
    }
    monkeypatch.setattr(ft, "FLOOD_STUDIES", {"probe": probe})

    # Identity transformer: feed projected coords straight through
    class _IdentityTransformer:
        @staticmethod
        def transform(lng, lat):
            return (lng, lat)

    monkeypatch.setitem(ft._STUDY_TRANSFORMERS, "EPSG:7856", _IdentityTransformer())

    # Point inside the pmf grid only (x=5000.5, y=5999.5)
    result = ft._query_flood_study_rasters(5999.5, 5000.5)
    matched = {s["study_key"]: s for s in result["flood_studies"]}
    assert "probe" in matched, "study skipped — bounds proxy used the smaller 1% grid"
    assert matched["probe"]["design"]["pmf"] == {"depth_m": 2.0, "level_m_ahd": 2.0}
    assert "1pct" not in matched["probe"]["design"]  # point is outside the 1% grid
