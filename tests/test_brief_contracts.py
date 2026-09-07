"""S2 typed boundary — service->brief contract tests.

The brief consumes service outputs through typed contract models (not loose dict
.get), so a renamed/dropped service key is a typed/test failure instead of a
silent null in the card (the jrc_occurrence_pct vs jrc_water_occurrence_pct class).

Increments: flood, bushfire, shadow service outputs.
"""
from services.intelligence_brief import (
    FloodServiceOutput,
    BushfireServiceOutput,
    ShadowServiceOutput,
    _build_flood_detail,
    _build_bushfire_detail,
    _build_shadow_result,
)


# The keys the flood service (flood_truth.run_flood) is documented to emit in
# `outputs`. If the service renames one, the golden/drift check (S3) re-captures
# real output and this set diverges -> caught. Here we lock the brief's contract
# to exactly this expected set so it can't silently drift.
EXPECTED_FLOOD_KEYS = {
    "flood_signal",
    "epi_flood_class",
    "epi_flood_label",
    "ems_flood_detected",
    "ems_activations",
    "sar_flood_detected",
    "sar_confidence",
    "sar_analysis_date",
    "ses_in_flood_planning_area",
    "ses_flood_class",
    "ses_study_name",
    "jrc_water_occurrence_pct",
    "jrc_data_year",
    "dea_wofs_frequency_pct",
    "bom_gauge_name",
    "bom_gauge_distance_km",
    "bom_last_major_flood_date",
    "bom_last_major_flood_peak_m",
    "bom_flood_history",
    "in_100yr_flood_zone",
    "in_100yr_flood_zone_unconsulted",
    "ground_elevation_m_ahd",
    "s1_gap_warning",
    "flood_studies",
}


def test_flood_contract_fields_are_the_expected_service_keys():
    assert set(FloodServiceOutput.model_fields) == EXPECTED_FLOOD_KEYS


def test_flood_contract_parses_real_shaped_output():
    raw = {
        "confidence": "estimated",
        "outputs": {
            "epi_flood_class": "1% AEP",
            "epi_flood_label": "Flood planning area",
            "jrc_water_occurrence_pct": 0.0,
            "dea_wofs_frequency_pct": 0.0,
            "bom_gauge_distance_km": 20.5,
            "flood_studies": [],
            # extra keys the service also emits — must be ignored, not break parsing
            "jrc_data_year": 2021,
            "refused": False,
        },
    }
    fd = _build_flood_detail(raw)
    assert fd is not None
    assert fd.epi_flood is True            # class present and != "none"
    assert fd.jrc_occurrence_pct == 0.0    # genuine zero preserved (not null)
    assert fd.wofs_frequency_pct == 0.0
    assert fd.bom_gauge_distance_km == 20.5
    assert fd.confidence == "estimated"


def test_flood_genuine_empty_values_preserved():
    # All-None outputs (a real "nothing detected") must round-trip as None, not error.
    raw = {"outputs": {k: None for k in EXPECTED_FLOOD_KEYS}}
    fd = _build_flood_detail(raw)
    assert fd is not None
    assert fd.epi_flood is None
    assert fd.jrc_occurrence_pct is None


def test_flood_old_renamed_key_does_not_populate():
    # If a service regressed to the OLD name `jrc_occurrence_pct`, the contract's
    # `jrc_water_occurrence_pct` stays None -> the card field is null. This is the
    # exact #589 bug; the contract + the drift check (S3) surface it.
    raw = {"outputs": {"jrc_occurrence_pct": 42.0}}  # wrong/old name
    fd = _build_flood_detail(raw)
    assert fd is not None
    assert fd.jrc_occurrence_pct is None  # the correct key was absent


# --- Increment 2: bushfire -------------------------------------------------

EXPECTED_BUSHFIRE_KEYS = {
    "is_bushfire_prone",
    "designation_category",
    "designation_source",
    "estimated_bal_band",
    "designation_guideline",
    "fire_signal",
    "bal_assessment_likely_required",
    "bal_formal_assessment_cost_range",
    "bal_assessor_directory_url",
    "data_currency",
    "compliance",
}


def test_bushfire_contract_fields_are_the_expected_service_keys():
    assert set(BushfireServiceOutput.model_fields) == EXPECTED_BUSHFIRE_KEYS


def test_bushfire_contract_parses_real_shaped_output():
    raw = {
        "confidence": "authoritative",
        "outputs": {
            "is_bushfire_prone": True,
            "designation_category": "Vegetation Category 1",
            "estimated_bal_band": "BAL-29",
            "designation_guideline": "Forest",
            "fire_signal": "elevated",
            "compliance": {"cross_overlays": [{"type": "flood", "value": "Flood planning area"}], "extra": 1},
            "extra_service_key": "ignored",
        },
    }
    bd = _build_bushfire_detail(raw)
    assert bd is not None
    assert bd.is_bushfire_prone is True
    assert bd.category == "Vegetation Category 1"
    assert bd.bal_estimate == "BAL-29"
    assert bd.cross_overlays == [{"type": "flood", "value": "Flood planning area"}]
    assert bd.confidence == "authoritative"


def test_bushfire_genuine_empty_preserved():
    bd = _build_bushfire_detail({"outputs": {}})
    assert bd is not None
    assert bd.is_bushfire_prone is None
    assert bd.cross_overlays is None


# --- Increment 3: shadow ---------------------------------------------------

EXPECTED_SHADOW_KEYS = {
    "height_m", "height_source", "adg_compliant", "worst_case_scenario", "scenarios",
    # Run-level passthrough: envelope confidence (merged in by get_shadow_risk).
    # The three construction_change_* keys were REMOVED 2026-08-07 (§4h) with the
    # adjacent-lot check itself — 0 readings in 538 attempts, and unable to
    # resolve a single lot at 20 m SWIR.
    "confidence",
}


def test_shadow_contract_fields_are_the_expected_service_keys():
    assert set(ShadowServiceOutput.model_fields) == EXPECTED_SHADOW_KEYS


def test_shadow_contract_parses_real_shaped_output():
    raw = {
        "height_m": 9.0,
        "height_source": "LEP control",
        "adg_compliant": True,
        "worst_case_scenario": "Jun 21 9:00 AM",
        "scenarios": [
            {
                "label": "Jun 21 (winter solstice)",
                "time_local": "9:00 AM",
                "shadow_length_m": 21.7,
                "shadow_overlap_fraction": 0.153,
                "shadow_direction_deg": 222.0,
                "overlaps_subject_lot": True,
                "extra_key": "ignored",
            }
        ],
    }
    sr = _build_shadow_result(raw)
    assert sr is not None
    assert sr.height_m == 9.0
    assert sr.adg_compliant is True
    assert len(sr.scenarios) == 1
    sc = sr.scenarios[0]
    assert sc.date_label == "Jun 21 (winter solstice)"
    assert sc.time_label == "9:00 AM"
    assert round(sc.overlap_pct, 1) == 15.3  # 0.153 fraction -> percent
    assert sc.shadow_direction_deg == 222.0


def test_shadow_genuine_empty_preserved():
    sr = _build_shadow_result({"scenarios": []})
    assert sr is not None
    assert sr.height_m is None
    assert sr.scenarios == []
