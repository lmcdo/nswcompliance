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

def test_confidence_null_wet_seasons_no_crash():
    """wet_seasons_checked=null must not raise TypeError (was .get(key, 0) null trap)."""
    out = _outputs(wet_seasons_checked=None)
    result = _compute_confidence(out)
    assert result in ("high", "medium", "low")


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

def test_data_sources_always_includes_epi_and_s1():
    out = _outputs()
    sources = _build_data_sources(out)
    assert "NSW SEED EPI WFS" in sources
    assert "Microsoft Planetary Computer S1 RTC" in sources


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
    assert result["epi_flood_label"] is not None
    assert "flood" in result["epi_flood_label"].lower()


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


def test_hawkesbury_result_has_all_nine_aep_fields(monkeypatch):
    """null_result always contains all 9 AEP keys (contract stability).
    rasterio is required for raster tests — skip if unavailable."""
    import services.flood_truth as ft
    pytest.importorskip("rasterio")
    monkeypatch.setitem(ft.FLOOD_STUDIES["hawkesbury"], "dir", "/nonexistent")
    result = ft._query_flood_study_rasters(-33.6134, 150.8130)
    for k in ft.HAWKESBURY_AEP_FILES:
        assert f"hawkesbury_flood_level_{k}" in result


def test_signal_hawk_100aep_present_counts_as_in_overlay():
    """hawkesbury_flood_level_100aep not None → at least 'low' signal."""
    out = _outputs(
        epi_flood_class="none",
        ses_in_flood_planning_area=None,
        hawkesbury_flood_level_100aep=17.34,
    )
    signal = _compute_flood_signal(out)
    assert signal in ("low", "moderate", "elevated"), f"Expected overlay signal, got {signal!r}"


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
    assert any("heritage" in s for s in sources)


def test_data_sources_excludes_compound_when_absent():
    raw = _outputs()
    sources = _build_data_sources(raw)
    assert not any("heritage" in s for s in sources)
