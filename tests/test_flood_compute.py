"""
Mutation-testing-grade tests for flood_truth.py compute + build functions.

Scope:
  _compute_flood_signal  — multi-source convergence signal
  _compute_confidence    — data availability tier
  _build_s1_gap_warning  — Sentinel-1B gap text
  _build_compound_risk_notes — compound risk descriptions
  _build_data_sources    — data source name list
"""

import pytest

from services.flood_truth import (
    _compute_flood_signal,
    _compute_confidence,
    _build_s1_gap_warning,
    _build_compound_risk_notes,
    _build_data_sources,
    _COMPOUND_RISK_DESCRIPTIONS,
)


# ============================================================================
# Helpers
# ============================================================================

def _base(**overrides) -> dict:
    """Minimal inputs dict — all sources absent/None."""
    d = {
        "data_currency": "ok",
        "epi_flood_class": None,
        "ses_in_flood_planning_area": None,
        "flood_studies": [],
        "hawkesbury_flood_level_100aep": None,
        "ems_flood_detected": None,
        "jrc_water_occurrence_pct": None,
        "dea_wofs_frequency_pct": None,
        "bom_last_major_flood_date": None,
    }
    d.update(overrides)
    return d


# ============================================================================
# _compute_flood_signal
# ============================================================================

class TestComputeFloodSignal:
    """Each test targets a unique code path to maximise mutant kills."""

    # --- Top-level short-circuits ---

    def test_query_failed_returns_unavailable(self):
        assert _compute_flood_signal(_base(data_currency="query_failed")) == "unavailable"

    def test_query_failed_overrides_all_positive_signals(self):
        """Even if every indicator is positive, query_failed wins."""
        assert _compute_flood_signal(_base(
            data_currency="query_failed",
            epi_flood_class="Flood Planning Area",
            ems_flood_detected=True,
            jrc_water_occurrence_pct=50.0,
            bom_last_major_flood_date="2022-03-01",
        )) == "unavailable"

    # --- Phase 0 false-negative fix (unavailable when EPI uncovered) ---

    def test_epi_none_str_no_ses_no_study_no_observed_returns_unavailable(self):
        """epi_flood_class="none" + no SES + no study + no observed → unavailable."""
        assert _compute_flood_signal(_base(epi_flood_class="none")) == "unavailable"

    def test_epi_none_str_with_ses_queried_returns_none(self):
        """SES queried (even False) prevents false-negative guard."""
        assert _compute_flood_signal(_base(
            epi_flood_class="none",
            ses_in_flood_planning_area=False,
        )) == "none"

    def test_epi_none_str_with_flood_study_returns_low(self):
        """Flood study raster = study_in_overlay = in_overlay → low."""
        assert _compute_flood_signal(_base(
            epi_flood_class="none",
            flood_studies=[{"design": {"1pct": 4.5}}],
        )) == "low"

    def test_epi_none_str_with_ems_detected_skips_unavailable(self):
        """EMS detection prevents false-negative guard → moderate (ems alone)."""
        assert _compute_flood_signal(_base(
            epi_flood_class="none",
            ems_flood_detected=True,
        )) == "moderate"

    def test_epi_none_str_with_bom_flood_skips_unavailable(self):
        """BOM flood date prevents false-negative guard."""
        assert _compute_flood_signal(_base(
            epi_flood_class="none",
            bom_last_major_flood_date="2022-03-01",
        )) != "unavailable"

    def test_epi_none_str_with_jrc_at_boundary_5(self):
        """effective_pct == 5.0 is NOT < 5 → skips unavailable guard → moderate (jrc_low)."""
        result = _compute_flood_signal(_base(
            epi_flood_class="none",
            jrc_water_occurrence_pct=5.0,
        ))
        assert result != "unavailable"

    def test_epi_none_str_with_jrc_at_4_point_9(self):
        """effective_pct == 4.9 IS < 5 → unavailable (Phase 0 guard)."""
        assert _compute_flood_signal(_base(
            epi_flood_class="none",
            jrc_water_occurrence_pct=4.9,
        )) == "unavailable"

    def test_epi_none_str_with_wofs_fallback_below_5(self):
        """JRC=0, WOfS=4.9 → effective_pct=4.9 < 5 → unavailable."""
        assert _compute_flood_signal(_base(
            epi_flood_class="none",
            jrc_water_occurrence_pct=0.0,
            dea_wofs_frequency_pct=4.9,
        )) == "unavailable"

    def test_epi_none_str_with_wofs_fallback_at_5(self):
        """JRC=0, WOfS=5.0 → effective_pct=5.0 → NOT unavailable."""
        result = _compute_flood_signal(_base(
            epi_flood_class="none",
            jrc_water_occurrence_pct=0.0,
            dea_wofs_frequency_pct=5.0,
        ))
        assert result != "unavailable"

    # --- Three-state boundaries for epi_flood_class ---

    def test_epi_null_means_not_in_overlay(self):
        """epi_flood_class=None → epi_in_overlay=False → does NOT trigger Phase 0."""
        assert _compute_flood_signal(_base(epi_flood_class=None)) == "none"

    def test_epi_empty_string_means_not_in_overlay(self):
        """epi_flood_class="" → epi_in_overlay=False → none."""
        assert _compute_flood_signal(_base(epi_flood_class="")) == "none"

    def test_epi_none_string_means_not_in_overlay_but_triggers_phase0(self):
        """epi_flood_class="none" → epi_in_overlay=False, epi_no_coverage=True → unavailable."""
        assert _compute_flood_signal(_base(epi_flood_class="none")) == "unavailable"

    def test_epi_flood_planning_area_means_in_overlay(self):
        """Non-null/non-"none"/non-"" string → in overlay."""
        assert _compute_flood_signal(_base(epi_flood_class="Flood Planning Area")) == "low"

    # --- JRC vs WOfS fallback ---

    def test_jrc_positive_ignores_wofs(self):
        """When jrc_pct > 0, wofs_pct is irrelevant."""
        result_jrc = _compute_flood_signal(_base(
            jrc_water_occurrence_pct=20.0,
            dea_wofs_frequency_pct=50.0,
        ))
        result_jrc_only = _compute_flood_signal(_base(
            jrc_water_occurrence_pct=20.0,
            dea_wofs_frequency_pct=0.0,
        ))
        assert result_jrc == result_jrc_only == "moderate"  # jrc_moderate

    def test_jrc_zero_falls_back_to_wofs(self):
        """jrc_pct=0 → effective_pct = wofs_pct."""
        assert _compute_flood_signal(_base(
            jrc_water_occurrence_pct=0.0,
            dea_wofs_frequency_pct=20.0,
        )) == "moderate"  # jrc_moderate via wofs fallback

    def test_jrc_none_falls_back_to_wofs(self):
        """jrc_pct=None → (None or 0.0) = 0.0 → falls back to wofs."""
        assert _compute_flood_signal(_base(
            jrc_water_occurrence_pct=None,
            dea_wofs_frequency_pct=20.0,
        )) == "moderate"

    def test_both_none_means_zero(self):
        """Both None → effective_pct = 0."""
        assert _compute_flood_signal(_base()) == "none"

    # --- Hawkesbury backward-compat ---

    def test_hawkesbury_100aep_sets_study_in_overlay(self):
        """hawkesbury_flood_level_100aep not None → study_in_overlay=True → in_overlay → low."""
        assert _compute_flood_signal(_base(
            hawkesbury_flood_level_100aep=7.5,
        )) == "low"

    def test_hawkesbury_zero_still_sets_study_in_overlay(self):
        """Even hawkesbury=0 (not None) → study_in_overlay=True."""
        assert _compute_flood_signal(_base(
            hawkesbury_flood_level_100aep=0,
        )) == "low"

    # --- Flood studies ---

    def test_flood_study_with_1pct_sets_in_overlay(self):
        assert _compute_flood_signal(_base(
            flood_studies=[{"design": {"1pct": 3.2}}],
        )) == "low"

    def test_flood_study_without_1pct_does_not_set_overlay(self):
        """design.1pct is None → study_in_overlay stays False."""
        assert _compute_flood_signal(_base(
            flood_studies=[{"design": {"1pct": None}}],
        )) == "none"

    def test_flood_study_no_design_key(self):
        """Missing design key → .get("design") returns None → no overlay."""
        assert _compute_flood_signal(_base(
            flood_studies=[{"name": "test"}],
        )) == "none"

    def test_flood_study_empty_design(self):
        """design={} → .get("1pct") returns None → no overlay."""
        assert _compute_flood_signal(_base(
            flood_studies=[{"design": {}}],
        )) == "none"

    def test_multiple_flood_studies_any_with_1pct(self):
        """Only one needs 1pct for study_in_overlay=True."""
        assert _compute_flood_signal(_base(
            flood_studies=[
                {"design": {"1pct": None}},
                {"design": {"1pct": 5.0}},
            ],
        )) == "low"

    # --- SES overlay ---

    def test_ses_true_means_in_overlay(self):
        assert _compute_flood_signal(_base(ses_in_flood_planning_area=True)) == "low"

    def test_ses_false_means_not_in_overlay_but_ses_queried(self):
        """ses=False → NOT in overlay, but ses_queried=True prevents Phase 0."""
        assert _compute_flood_signal(_base(
            epi_flood_class="none",
            ses_in_flood_planning_area=False,
        )) == "none"

    # --- ELEVATED: multiple sources agree ---

    def test_elevated_overlay_plus_ems(self):
        """in_overlay AND ems_detected → elevated."""
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            ems_flood_detected=True,
        )) == "elevated"

    def test_elevated_ems_plus_jrc_moderate(self):
        """ems AND jrc_moderate (15 <= pct < 40) → elevated."""
        assert _compute_flood_signal(_base(
            ems_flood_detected=True,
            jrc_water_occurrence_pct=15.0,
        )) == "elevated"

    def test_elevated_ems_plus_jrc_high(self):
        """ems AND jrc_high (>= 40) → elevated."""
        assert _compute_flood_signal(_base(
            ems_flood_detected=True,
            jrc_water_occurrence_pct=40.0,
        )) == "elevated"

    def test_elevated_jrc_high_alone(self):
        """jrc_high (>= 40) alone → elevated."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=40.0)) == "elevated"

    def test_elevated_overlay_jrc_moderate_bom(self):
        """in_overlay AND jrc_moderate AND bom_flood → elevated."""
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            jrc_water_occurrence_pct=15.0,
            bom_last_major_flood_date="2022-03-01",
        )) == "elevated"

    def test_elevated_ses_overlay_plus_ems(self):
        """SES overlay (not EPI) + EMS → elevated."""
        assert _compute_flood_signal(_base(
            ses_in_flood_planning_area=True,
            ems_flood_detected=True,
        )) == "elevated"

    def test_elevated_study_overlay_plus_ems(self):
        """Flood study overlay + EMS → elevated."""
        assert _compute_flood_signal(_base(
            flood_studies=[{"design": {"1pct": 3.0}}],
            ems_flood_detected=True,
        )) == "elevated"

    def test_elevated_hawkesbury_overlay_plus_ems(self):
        """Hawkesbury overlay + EMS → elevated."""
        assert _compute_flood_signal(_base(
            hawkesbury_flood_level_100aep=7.5,
            ems_flood_detected=True,
        )) == "elevated"

    # --- JRC boundary tests for elevated ---

    def test_jrc_39_point_9_not_high(self):
        """39.9 < 40 → NOT jrc_high → not elevated (alone)."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=39.9)) == "moderate"

    def test_jrc_40_point_0_is_high(self):
        """40.0 >= 40 → jrc_high → elevated."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=40.0)) == "elevated"

    def test_jrc_40_point_1_is_high(self):
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=40.1)) == "elevated"

    def test_ems_plus_jrc_14_point_9_not_elevated(self):
        """14.9 < 15 → jrc_low (not moderate) → ems alone → moderate, not elevated."""
        assert _compute_flood_signal(_base(
            ems_flood_detected=True,
            jrc_water_occurrence_pct=14.9,
        )) == "moderate"

    def test_ems_plus_jrc_15_point_0_is_elevated(self):
        """15.0 >= 15 → jrc_moderate → ems+jrc_moderate → elevated."""
        assert _compute_flood_signal(_base(
            ems_flood_detected=True,
            jrc_water_occurrence_pct=15.0,
        )) == "elevated"

    # --- MODERATE: one strong or two weaker ---

    def test_moderate_ems_alone(self):
        assert _compute_flood_signal(_base(ems_flood_detected=True)) == "moderate"

    def test_moderate_overlay_plus_jrc_low(self):
        """in_overlay AND jrc_low (0 < pct < 15) → moderate."""
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            jrc_water_occurrence_pct=5.0,
        )) == "moderate"

    def test_moderate_overlay_plus_bom(self):
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            bom_last_major_flood_date="2022-03-01",
        )) == "moderate"

    def test_moderate_jrc_moderate_alone(self):
        """jrc_moderate (15 <= pct < 40) without ems → moderate."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=15.0)) == "moderate"

    def test_moderate_jrc_low_plus_bom(self):
        assert _compute_flood_signal(_base(
            jrc_water_occurrence_pct=5.0,
            bom_last_major_flood_date="2022-03-01",
        )) == "moderate"

    # --- JRC boundary tests for moderate ---

    def test_jrc_0_not_low(self):
        """jrc=0 → effective_pct=0 → NOT jrc_low (condition is 0 < pct)."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=0.0)) == "none"

    def test_jrc_0_point_1_is_low(self):
        """0.1 > 0 and < 15 → jrc_low."""
        # By itself, jrc_low doesn't trigger moderate. Needs overlay or bom.
        # With overlay:
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            jrc_water_occurrence_pct=0.1,
        )) == "moderate"

    def test_jrc_14_point_9_is_low(self):
        """14.9 < 15 → jrc_low, not jrc_moderate."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=14.9)) != "elevated"
        # jrc_low alone doesn't trigger moderate (no overlay, no bom)
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=14.9)) == "none"

    def test_jrc_15_point_0_is_moderate(self):
        """15.0 → jrc_moderate → moderate."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=15.0)) == "moderate"

    def test_jrc_5_alone_is_none(self):
        """jrc_low=True but no other signal → falls through to none."""
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=5.0)) == "none"

    # --- LOW: overlay only ---

    def test_low_epi_overlay_only(self):
        assert _compute_flood_signal(_base(epi_flood_class="Flood Planning Area")) == "low"

    def test_low_ses_overlay_only(self):
        assert _compute_flood_signal(_base(ses_in_flood_planning_area=True)) == "low"

    def test_low_study_overlay_only(self):
        assert _compute_flood_signal(_base(
            flood_studies=[{"design": {"1pct": 2.0}}],
        )) == "low"

    def test_low_hawkesbury_overlay_only(self):
        assert _compute_flood_signal(_base(hawkesbury_flood_level_100aep=7.5)) == "low"

    # --- NONE: no indicators ---

    def test_none_all_absent(self):
        assert _compute_flood_signal(_base()) == "none"

    def test_none_ems_false_not_detected(self):
        """ems_flood_detected=False → NOT True → ems_detected=False."""
        assert _compute_flood_signal(_base(ems_flood_detected=False)) == "none"

    def test_none_jrc_zero(self):
        assert _compute_flood_signal(_base(jrc_water_occurrence_pct=0.0)) == "none"

    # --- Combinations that confirm priority ordering ---

    def test_elevated_beats_moderate(self):
        """All signals positive → elevated (not moderate or low)."""
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            ems_flood_detected=True,
            jrc_water_occurrence_pct=50.0,
            bom_last_major_flood_date="2022-03-01",
        )) == "elevated"

    def test_moderate_beats_low(self):
        """Overlay + jrc_low → moderate (not low)."""
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            jrc_water_occurrence_pct=5.0,
        )) == "moderate"

    def test_overlay_plus_jrc_moderate_no_bom_is_moderate_not_elevated(self):
        """in_overlay AND jrc_moderate WITHOUT bom → moderate (third elevated condition needs all three)."""
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            jrc_water_occurrence_pct=20.0,
        )) == "moderate"

    # --- WOfS fallback in elevated/moderate paths ---

    def test_wofs_fallback_high_triggers_elevated(self):
        """jrc=0, wofs=45 → effective=45 → jrc_high → elevated."""
        assert _compute_flood_signal(_base(
            jrc_water_occurrence_pct=0.0,
            dea_wofs_frequency_pct=45.0,
        )) == "elevated"

    def test_wofs_fallback_moderate_triggers_moderate(self):
        """jrc=0, wofs=20 → effective=20 → jrc_moderate → moderate."""
        assert _compute_flood_signal(_base(
            jrc_water_occurrence_pct=0.0,
            dea_wofs_frequency_pct=20.0,
        )) == "moderate"

    def test_wofs_fallback_low_with_overlay_triggers_moderate(self):
        """jrc=0, wofs=5 → effective=5 → jrc_low + overlay → moderate."""
        assert _compute_flood_signal(_base(
            epi_flood_class="Flood Planning Area",
            jrc_water_occurrence_pct=0.0,
            dea_wofs_frequency_pct=5.0,
        )) == "moderate"


# ============================================================================
# _compute_confidence
# ============================================================================

class TestComputeConfidence:

    def test_high_all_sources_plus_sar(self):
        """EMS + JRC + BOM + SES (=4 layers) + 1 SAR season → high."""
        assert _compute_confidence({
            "ems_flood_detected": True,
            "jrc_water_occurrence_pct": 10.0,
            "bom_gauge_name": "Hawkesbury at Windsor",
            "ses_in_flood_planning_area": True,
            "wet_seasons_checked": 1,
        }) == "high"

    def test_high_three_layers_one_season(self):
        """Exactly 3 spatial layers + 1 SAR season → high."""
        assert _compute_confidence({
            "ems_flood_detected": False,
            "jrc_water_occurrence_pct": 10.0,
            "bom_gauge_name": "Test",
            "wet_seasons_checked": 1,
        }) == "high"

    def test_high_three_layers_wofs_instead_of_jrc(self):
        """WOfS counts as jrc_available OR wofs_available."""
        assert _compute_confidence({
            "ems_flood_detected": True,
            "dea_wofs_frequency_pct": 5.0,
            "bom_gauge_name": "Test",
            "wet_seasons_checked": 2,
        }) == "high"

    def test_high_needs_three_layers_not_two(self):
        """2 spatial layers + 1 SAR → NOT high → medium."""
        assert _compute_confidence({
            "ems_flood_detected": True,
            "jrc_water_occurrence_pct": 10.0,
            "wet_seasons_checked": 1,
        }) == "medium"

    def test_high_needs_at_least_one_sar_season(self):
        """3 spatial layers + 0 SAR → NOT high → medium."""
        assert _compute_confidence({
            "ems_flood_detected": True,
            "jrc_water_occurrence_pct": 10.0,
            "bom_gauge_name": "Test",
            "wet_seasons_checked": 0,
        }) == "medium"

    def test_medium_one_spatial_layer(self):
        """1 spatial layer, no SAR → medium."""
        assert _compute_confidence({
            "ems_flood_detected": False,
        }) == "medium"

    def test_medium_one_sar_season_no_layers(self):
        """0 spatial layers + 1 SAR → medium."""
        assert _compute_confidence({
            "wet_seasons_checked": 1,
        }) == "medium"

    def test_medium_two_layers_no_sar(self):
        assert _compute_confidence({
            "ems_flood_detected": True,
            "bom_gauge_name": "Test",
        }) == "medium"

    def test_low_nothing_available(self):
        """No spatial layers, no SAR → low."""
        assert _compute_confidence({}) == "low"

    def test_low_zero_seasons_no_layers(self):
        """wet_seasons_checked=0 explicitly → low."""
        assert _compute_confidence({"wet_seasons_checked": 0}) == "low"

    def test_jrc_and_wofs_count_as_one(self):
        """Both JRC and WOfS present → still counts as 1 layer (OR)."""
        result = _compute_confidence({
            "jrc_water_occurrence_pct": 10.0,
            "dea_wofs_frequency_pct": 5.0,
            "wet_seasons_checked": 1,
        })
        # 1 spatial layer (jrc OR wofs) + 1 SAR: spatial_layers=1, so NOT >= 3 → medium
        assert result == "medium"

    def test_ems_none_vs_false(self):
        """ems=None → not available. ems=False → available (was queried)."""
        assert _compute_confidence({"ems_flood_detected": None}) == "low"
        assert _compute_confidence({"ems_flood_detected": False}) == "medium"

    def test_ses_none_vs_false(self):
        """Same pattern: ses=None → not available, ses=False → available."""
        assert _compute_confidence({"ses_in_flood_planning_area": None}) == "low"
        assert _compute_confidence({"ses_in_flood_planning_area": False}) == "medium"


# ============================================================================
# _build_s1_gap_warning
# ============================================================================

class TestBuildS1GapWarning:

    def test_with_ems_data(self):
        warning = _build_s1_gap_warning({"ems_flood_detected": True})
        assert warning.startswith("Sentinel-1B was non-operational")
        assert warning.endswith("activation data.")
        assert "Copernicus EMS" in warning
        assert "ingest" not in warning.lower()

    def test_with_ems_false_still_available(self):
        """ems_flood_detected=False → EMS was queried → same branch as True."""
        warning = _build_s1_gap_warning({"ems_flood_detected": False})
        assert warning.startswith("Sentinel-1B")
        assert warning.endswith("activation data.")

    def test_without_ems_data(self):
        warning = _build_s1_gap_warning({"ems_flood_detected": None})
        assert warning.startswith("Sentinel-1B was non-operational")
        assert warning.endswith("fill this gap.")
        assert "Sentinel-1A only" in warning
        assert "ingest_copernicus_ems.py" in warning
        # Kill mutant 1179: XX prefix on middle segment
        assert "2025. Flood detection" in warning

    def test_without_ems_key(self):
        """Missing key → .get() returns None → no EMS branch."""
        warning = _build_s1_gap_warning({})
        assert warning.startswith("Sentinel-1B")
        assert warning.endswith("fill this gap.")

    def test_both_branches_mention_sentinel_1b(self):
        w1 = _build_s1_gap_warning({"ems_flood_detected": True})
        w2 = _build_s1_gap_warning({})
        assert "Sentinel-1B" in w1
        assert "Sentinel-1B" in w2

    def test_both_mention_dec_2021(self):
        w1 = _build_s1_gap_warning({"ems_flood_detected": True})
        w2 = _build_s1_gap_warning({})
        assert "Dec 2021" in w1
        assert "Dec 2021" in w2

    def test_both_mention_mar_2025(self):
        w1 = _build_s1_gap_warning({"ems_flood_detected": True})
        w2 = _build_s1_gap_warning({})
        assert "Mar 2025" in w1
        assert "Mar 2025" in w2


# ============================================================================
# _build_compound_risk_notes
# ============================================================================

class TestBuildCompoundRiskNotes:

    def test_empty_list(self):
        assert _build_compound_risk_notes([]) == []

    def test_single_known_type(self):
        notes = _build_compound_risk_notes(["heritage"])
        assert len(notes) == 1
        assert notes[0] == _COMPOUND_RISK_DESCRIPTIONS["heritage"]

    def test_all_known_types(self):
        notes = _build_compound_risk_notes(["heritage", "riparian", "wetlands", "landslide"])
        assert len(notes) == 4
        assert notes[0] == _COMPOUND_RISK_DESCRIPTIONS["heritage"]
        assert notes[1] == _COMPOUND_RISK_DESCRIPTIONS["riparian"]
        assert notes[2] == _COMPOUND_RISK_DESCRIPTIONS["wetlands"]
        assert notes[3] == _COMPOUND_RISK_DESCRIPTIONS["landslide"]

    def test_unknown_type_ignored(self):
        notes = _build_compound_risk_notes(["bushfire"])
        assert notes == []

    def test_mixed_known_unknown(self):
        notes = _build_compound_risk_notes(["unknown", "heritage", "invalid"])
        assert len(notes) == 1
        assert "heritage" in notes[0].lower()

    def test_order_preserved(self):
        notes = _build_compound_risk_notes(["landslide", "heritage"])
        assert "landslide" in notes[0].lower()
        assert "heritage" in notes[1].lower()

    def test_heritage_exact_content(self):
        notes = _build_compound_risk_notes(["heritage"])
        assert notes[0].startswith("Property is within a heritage conservation area")
        assert notes[0].endswith("heritage controls.")

    def test_riparian_exact_content(self):
        notes = _build_compound_risk_notes(["riparian"])
        assert notes[0].startswith("Property is on or adjacent to mapped riparian land")
        assert notes[0].endswith("setback requirements.")

    def test_wetlands_exact_content(self):
        notes = _build_compound_risk_notes(["wetlands"])
        assert notes[0].startswith("Property is within or adjacent to a mapped wetland area")
        assert notes[0].endswith("neighbouring properties.")

    def test_landslide_exact_content(self):
        notes = _build_compound_risk_notes(["landslide"])
        assert notes[0].startswith("Property is within a mapped landslide-prone area")
        assert notes[0].endswith("standard flood modelling.")


# ============================================================================
# _build_data_sources
# ============================================================================

class TestBuildDataSources:

    def test_epi_always_first_planetary_never_unconditional(self):
        """FLIPPED 2026-08-03 (campaign item 4 / DQ-44): this test previously
        pinned 'Planetary Computer always last' — but no S1 query has ever
        run (sar_flood_detected is hard-nulled), so the pinned behaviour was
        a named source that was never queried. The S1 source may appear ONLY
        when a SAR result exists."""
        sources = _build_data_sources({})
        assert sources[0] == "NSW SEED EPI WFS"
        assert "Microsoft Planetary Computer S1 RTC" not in sources

    def test_s1_source_claimed_only_with_a_sar_result(self):
        sources = _build_data_sources({"sar_flood_detected": False})
        assert sources[-1] == "Microsoft Planetary Computer S1 RTC"

    def test_minimal_inputs(self):
        """No optional data → only EPI (S1 no longer falsely claimed)."""
        sources = _build_data_sources({})
        assert len(sources) == 1

    def test_ses_included(self):
        sources = _build_data_sources({"ses_in_flood_planning_area": True})
        assert any("SES" in s for s in sources)

    def test_ses_false_still_included(self):
        """ses=False is not None → source included."""
        sources = _build_data_sources({"ses_in_flood_planning_area": False})
        assert any("SES" in s for s in sources)

    def test_ses_none_excluded(self):
        sources = _build_data_sources({"ses_in_flood_planning_area": None})
        assert not any("SES" in s for s in sources)

    def test_ems_included(self):
        sources = _build_data_sources({"ems_flood_detected": True})
        assert any("EMS" in s for s in sources)

    def test_ems_false_included(self):
        sources = _build_data_sources({"ems_flood_detected": False})
        assert any("EMS" in s for s in sources)

    def test_ems_none_excluded(self):
        sources = _build_data_sources({"ems_flood_detected": None})
        assert not any("EMS" in s for s in sources)

    def test_jrc_included(self):
        sources = _build_data_sources({"jrc_water_occurrence_pct": 10.0})
        assert any("JRC" in s for s in sources)

    def test_jrc_zero_included(self):
        """jrc=0.0 is not None → included."""
        sources = _build_data_sources({"jrc_water_occurrence_pct": 0.0})
        assert any("JRC" in s for s in sources)

    def test_jrc_none_excluded(self):
        sources = _build_data_sources({"jrc_water_occurrence_pct": None})
        assert not any("JRC" in s for s in sources)

    def test_wofs_included(self):
        sources = _build_data_sources({"dea_wofs_frequency_pct": 5.0})
        assert any("DEA" in s or "WOfS" in s for s in sources)

    def test_wofs_none_excluded(self):
        sources = _build_data_sources({"dea_wofs_frequency_pct": None})
        assert not any("DEA" in s and "WOfS" in s for s in sources)

    def test_bom_included(self):
        sources = _build_data_sources({"bom_gauge_name": "Windsor"})
        assert any("BOM" in s for s in sources)

    def test_bom_none_excluded(self):
        sources = _build_data_sources({"bom_gauge_name": None})
        assert not any("BOM" in s for s in sources)

    def test_dem_included(self):
        sources = _build_data_sources({"ground_elevation_m_ahd": 15.0})
        assert any("DEM" in s for s in sources)

    def test_dem_zero_included(self):
        """Elevation 0 is valid (sea level) → not None → included."""
        sources = _build_data_sources({"ground_elevation_m_ahd": 0.0})
        assert any("DEM" in s for s in sources)

    def test_dem_none_excluded(self):
        sources = _build_data_sources({"ground_elevation_m_ahd": None})
        assert not any("DEM" in s for s in sources)

    def test_flood_study_included(self):
        sources = _build_data_sources({
            "flood_studies": [{"study_name": "Hawkesbury", "source": "SES"}],
        })
        assert "Hawkesbury — SES (flood study raster)" in sources

    def test_flood_study_missing_name(self):
        """Missing study_name defaults to 'Unknown'."""
        sources = _build_data_sources({
            "flood_studies": [{"source": "SES"}],
        })
        study_src = [s for s in sources if "flood study raster" in s]
        assert len(study_src) == 1
        assert study_src[0] == "Unknown — SES (flood study raster)"

    def test_flood_study_missing_source(self):
        """Missing source defaults to empty string."""
        sources = _build_data_sources({
            "flood_studies": [{"study_name": "Test"}],
        })
        study_src = [s for s in sources if "flood study raster" in s]
        assert len(study_src) == 1
        assert study_src[0] == "Test —  (flood study raster)"

    def test_multiple_flood_studies(self):
        sources = _build_data_sources({
            "flood_studies": [
                {"study_name": "Study A", "source": "SES"},
                {"study_name": "Study B", "source": "Council"},
            ],
        })
        study_sources = [s for s in sources if "flood study raster" in s]
        assert len(study_sources) == 2

    def test_no_flood_studies(self):
        """Empty list → no flood study sources."""
        sources = _build_data_sources({"flood_studies": []})
        assert not any("flood study raster" in s for s in sources)

    def test_compound_layers_included(self):
        sources = _build_data_sources({"compound_heritage": True})
        assert "NSW ePlanning spatial_overlays (heritage)" in sources

    def test_compound_all_four_types(self):
        sources = _build_data_sources({
            "compound_heritage": True,
            "compound_riparian": True,
            "compound_wetlands": True,
            "compound_landslide": True,
        })
        assert "NSW ePlanning spatial_overlays (heritage)" in sources
        assert "NSW ePlanning spatial_overlays (riparian)" in sources
        assert "NSW ePlanning spatial_overlays (wetlands)" in sources
        assert "NSW ePlanning spatial_overlays (landslide)" in sources

    def test_compound_none_excluded(self):
        sources = _build_data_sources({"compound_heritage": None})
        assert not any("heritage" in s for s in sources)

    def test_compound_false_included(self):
        """compound_heritage=False is not None → included."""
        sources = _build_data_sources({"compound_heritage": False})
        assert any("heritage" in s for s in sources)

    def test_all_sources_present(self):
        """All optional sources present → count is correct."""
        sources = _build_data_sources({
            "ses_in_flood_planning_area": True,
            "ems_flood_detected": True,
            "jrc_water_occurrence_pct": 10.0,
            "dea_wofs_frequency_pct": 5.0,
            "bom_gauge_name": "Test",
            "flood_studies": [{"study_name": "Test", "source": "SES"}],
            "ground_elevation_m_ahd": 15.0,
            "compound_heritage": True,
            "compound_riparian": True,
            "compound_wetlands": True,
            "compound_landslide": True,
        })
        # EPI + SES + EMS + JRC + DEA + BOM + 1 study + DEM + 4 compound = 12
        # (S1 appears only with a SAR result — FLIPPED 2026-08-03, DQ-44).
        assert len(sources) == 12
        assert "Microsoft Planetary Computer S1 RTC" not in sources

    def test_source_order(self):
        """EPI first; S1 last ONLY when a SAR result exists (FLIPPED
        2026-08-03, DQ-44 — it was unconditionally claimed before)."""
        sources = _build_data_sources({
            "ses_in_flood_planning_area": True,
            "ems_flood_detected": True,
            "jrc_water_occurrence_pct": 10.0,
            "sar_flood_detected": True,
        })
        assert sources[0] == "NSW SEED EPI WFS"
        assert sources[-1] == "Microsoft Planetary Computer S1 RTC"
