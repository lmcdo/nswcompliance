"""Golden-fixture guard: brief satellite cards must surface what the services emit.

Regression guard for the key-mismatch class of bug (Tier 0 of
ce-brief-content-enrichment). The services return rich payloads but the brief's
_build_* functions previously read the WRONG dict keys and silently emitted
null. Fixtures below use the REAL service output keys (captured live
2026-06-22). The `*_does_not_read_legacy_keys` tests pin the fix: if anyone
reverts to the old keys, they fail.
"""
import pytest

from services.intelligence_brief import (
    _build_bushfire_detail,
    _build_flood_detail,
    _build_shadow_result,
)

# ── Bushfire: real run_bushfire output shape (bushfire_prescreen.py:557-572) ──
BUSHFIRE_RAW = {
    "outputs": {
        "is_bushfire_prone": True,
        "designation_category": "Vegetation Category 1",
        "designation_guideline": "10/50 Vegetation Clearing",
        "estimated_bal_band": "BAL-29",
        "fire_signal": "elevated",
        "compliance": {"cross_overlays": [{"type": "flood"}, {"type": "heritage"}]},
    },
    "confidence": "medium",
}


def test_bushfire_surfaces_real_fields():
    d = _build_bushfire_detail(BUSHFIRE_RAW)
    assert d is not None
    assert d.is_bushfire_prone is True
    assert d.category == "Vegetation Category 1"
    assert d.bal_estimate == "BAL-29"
    assert d.fire_signal == "elevated"
    assert d.cross_overlays == [{"type": "flood"}, {"type": "heritage"}]
    assert d.confidence == "medium"


def test_bushfire_does_not_read_legacy_rfs_key():
    # The bug was reading outputs['rfs'][...]; that must NOT populate anything.
    legacy = {"outputs": {"rfs": {"category": "X", "bal_estimate": "Y"}}, "confidence": "low"}
    d = _build_bushfire_detail(legacy)
    assert d.category is None
    assert d.bal_estimate is None


def test_bushfire_none_input():
    assert _build_bushfire_detail(None) is None


# ── Bushfire pass-through parity (PR-B): recorded Kincumber run 2026-07-16
# (20 Patanga St, propId 66652), compliance sub-object reshaped to the
# post-#756 three-state contract (referral/10-50 conditional, never blanket). ──
KINCUMBER_BUSHFIRE_RAW = {
    "outputs": {
        "is_bushfire_prone": True,
        "designation_source": "NSW Rural Fire Service Bush Fire Prone Land Map",
        "designation_category": "Vegetation Buffer",
        "designation_guideline": "v5b",
        "estimated_bal_band": "BAL-12.5",
        "bal_assessment_likely_required": True,
        "bal_formal_assessment_cost_range": "$500-$2,000",
        "bal_assessor_directory_url": (
            "https://www.rfs.nsw.gov.au/plan-and-prepare/building-in-a-bush-fire-area/find-a-practitioner"
        ),
        "fire_signal": "low",
        "data_currency": "2026-07-16",
        "compliance": {
            "state_legislation": (
                "Environmental Planning and Assessment Act 1979 s4.14; "
                "Rural Fires Act 1997; Planning for Bush Fire Protection 2019"
            ),
            "rfs_referral_required": None,
            "rfs_referral_note": (
                "Referral to the NSW Rural Fire Service applies only if the proposal "
                "matches a trigger below. Other development on bush fire prone land is "
                "assessed by the council against Planning for Bush Fire Protection."
            ),
            "rfs_referral_triggers": ["Subdivision of bushfire-prone land"],
            "cdc_pathway_available": True,
            "clearing_10_50_entitled": None,
            "clearing_10_50_exceptions": (
                "Whether the 10/50 vegetation clearing scheme applies here depends "
                "on the RFS 10/50 entitlement area map — check the address in the "
                "RFS online 10/50 tool. Entitlements do not apply within "
                "threatened species habitat or 40m of a waterway."
            ),
            "estimated_consultant_costs": (
                "$500-$2,000 (formal BAL assessment) + $2,000-$5,000 (bushfire report if required)"
            ),
            "cross_overlays": None,
            "legislation_url": (
                "https://legislation.nsw.gov.au/view/html/inforce/current/act-1979-203/part-4/div-4.8/sec-4.14"
            ),
        },
    },
    "confidence": "medium",
}


def test_bushfire_carries_compliance_passthrough_fields():
    d = _build_bushfire_detail(KINCUMBER_BUSHFIRE_RAW)
    assert d is not None
    assert d.designation_source == "NSW Rural Fire Service Bush Fire Prone Land Map"
    assert d.bal_assessment_likely_required is True
    assert d.bal_formal_assessment_cost_range == "$500-$2,000"
    assert d.bal_assessor_directory_url.startswith("https://www.rfs.nsw.gov.au/")
    assert d.data_currency == "2026-07-16"
    # Three-state conditionals (post-#756): None = depends on the proposal/map.
    assert d.rfs_referral_required is None
    assert "matches a trigger below" in d.rfs_referral_note
    assert d.clearing_10_50_entitled is None
    assert "RFS 10/50 entitlement area map" in d.clearing_10_50_exceptions
    assert d.estimated_consultant_costs.startswith("$500-$2,000")
    assert d.state_legislation.startswith("Environmental Planning and Assessment Act 1979")
    assert d.legislation_url.startswith("https://legislation.nsw.gov.au/")


def test_bushfire_new_fields_default_none_on_sparse_output():
    # Three-state preserved: an output without the guidance fields stays None
    # everywhere, never a fabricated False/"".
    d = _build_bushfire_detail({"outputs": {"is_bushfire_prone": False}})
    assert d.designation_source is None
    assert d.bal_assessment_likely_required is None
    assert d.bal_formal_assessment_cost_range is None
    assert d.bal_assessor_directory_url is None
    assert d.rfs_referral_note is None
    assert d.clearing_10_50_entitled is None
    assert d.clearing_10_50_exceptions is None
    assert d.estimated_consultant_costs is None
    assert d.state_legislation is None
    assert d.legislation_url is None


# ── Flood: real run_flood normalised output (flood_truth.py:1387-1411) ──
FLOOD_RAW = {
    "outputs": {
        "epi_flood_class": "flood_planning_area",
        "epi_flood_label": "Flood Planning Area",
        "jrc_water_occurrence_pct": 12.5,
        "dea_wofs_frequency_pct": 3.2,
        "bom_gauge_distance_km": 1.4,
        "flood_studies": [{"name": "Example FRMSP"}],
    },
    "confidence": "high",
}


def test_flood_surfaces_real_fields():
    d = _build_flood_detail(FLOOD_RAW)
    assert d is not None
    assert d.epi_flood is True
    assert d.epi_flood_label == "Flood Planning Area"
    assert d.jrc_occurrence_pct == 12.5
    assert d.wofs_frequency_pct == 3.2
    assert d.bom_gauge_distance_km == 1.4


def test_flood_class_none_means_checked_not_flood():
    d = _build_flood_detail({"outputs": {"epi_flood_class": "none"}})
    assert d.epi_flood is False  # checked, genuinely not in a flood class


def test_flood_missing_class_is_unknown_not_false():
    # No class returned = not assessed; must be None, never a misleading False.
    d = _build_flood_detail({"outputs": {}})
    assert d.epi_flood is None


def test_flood_does_not_read_legacy_keys():
    legacy = {"outputs": {"jrc_occurrence_pct": 99.0, "wofs_frequency_pct": 88.0}}
    d = _build_flood_detail(legacy)
    assert d.jrc_occurrence_pct is None  # must read jrc_water_occurrence_pct
    assert d.wofs_frequency_pct is None  # must read dea_wofs_frequency_pct


# ── Flood pass-through parity (PR-B): recorded Kincumber run 2026-07-16
# (20 Patanga St, propId 66652, deployed Railway) — the run whose signal
# ("moderate", EMS-detected) the brief's card previously rendered as clear. ──
KINCUMBER_FLOOD_RAW = {
    "outputs": {
        "flood_signal": "moderate",
        "epi_flood_class": "none",
        "epi_flood_label": "No EPI Flood Overlay",
        "ems_flood_detected": True,
        "ems_activations": [{
            "activation_id": "EMSR567",
            "event_name": "NSW/QLD Floods Feb–Mar 2022 — La Niña (Copernicus EMSR567)",
            "event_date": "2022-02-26",
            "flood_type": "observed",
        }],
        "sar_flood_detected": None,
        "sar_confidence": None,
        "sar_analysis_date": None,
        "ses_in_flood_planning_area": False,
        "ses_flood_class": None,
        "ses_study_name": None,
        "jrc_water_occurrence_pct": 0.0,
        "jrc_data_year": 2021,
        "dea_wofs_frequency_pct": 0.52,
        "bom_gauge_name": "Hawkesbury River at Windsor",
        "bom_gauge_distance_km": 56.3,
        "bom_last_major_flood_date": None,
        "bom_last_major_flood_peak_m": None,
        "bom_flood_history": [],
        "in_100yr_flood_zone": False,
        "ground_elevation_m_ahd": None,
        "s1_gap_warning": (
            "Sentinel-1B was non-operational Dec 2021 – Mar 2025. 2022 La Niña "
            "flood events sourced from Copernicus EMS activation data."
        ),
        "flood_studies": [],
    },
    "confidence": "medium",
}


def test_flood_carries_signal_and_ems_fields():
    """The Kincumber defect: flood_signal + EMS detection must survive the
    contract layer instead of being discarded into an effectively-clear card."""
    d = _build_flood_detail(KINCUMBER_FLOOD_RAW)
    assert d is not None
    assert d.flood_signal == "moderate"
    assert d.ems_flood_detected is True
    assert d.ems_activations == KINCUMBER_FLOOD_RAW["outputs"]["ems_activations"]
    assert d.ems_activations[0]["activation_id"] == "EMSR567"
    assert d.s1_gap_warning.startswith("Sentinel-1B was non-operational")
    assert d.bom_gauge_name == "Hawkesbury River at Windsor"
    assert d.bom_gauge_distance_km == 56.3
    assert d.in_100yr_flood_zone is False
    assert d.ses_in_flood_planning_area is False
    assert d.jrc_data_year == 2021
    assert d.wofs_frequency_pct == 0.52
    # SAR not run on this pass (S1 gap) — stays None, never a fabricated False.
    assert d.sar_flood_detected is None
    assert d.confidence == "medium"


def test_flood_new_fields_default_none_on_sparse_output():
    # Three-state preserved: nothing in the payload -> None everywhere.
    d = _build_flood_detail({"outputs": {}})
    assert d.flood_signal is None
    assert d.ems_flood_detected is None
    assert d.ems_activations is None
    assert d.ses_in_flood_planning_area is None
    assert d.bom_gauge_name is None
    assert d.in_100yr_flood_zone is None
    assert d.ground_elevation_m_ahd is None
    assert d.s1_gap_warning is None
    assert d.jrc_data_year is None


def test_flood_ems_false_is_checked_clear_not_none():
    d = _build_flood_detail({"outputs": {"ems_flood_detected": False, "ems_activations": []}})
    assert d.ems_flood_detected is False  # checked, no mapped extent here
    assert d.ems_activations == []


# ── Shadow: real run_shadow scenario shape (shadow_detector.py:275-286) ──
SHADOW_RAW = {
    "height_m": 9.5,
    "height_source": "LEP",
    "adg_compliant": True,
    "worst_case_scenario": "Jun 21 9:00 AM",
    "scenarios": [{
        "label": "Jun 21 (winter solstice)",
        "time_local": "9:00 AM",
        "shadow_length_m": 18.3,
        "shadow_overlap_fraction": 0.42,
        "shadow_direction_deg": 225.0,
        "overlaps_subject_lot": True,
    }],
}


def test_shadow_surfaces_real_scenario_fields():
    r = _build_shadow_result(SHADOW_RAW)
    assert r is not None and len(r.scenarios) == 1
    s = r.scenarios[0]
    assert s.date_label == "Jun 21 (winter solstice)"
    assert s.time_label == "9:00 AM"
    assert s.shadow_length_m == 18.3
    assert s.overlap_pct == 42.0  # fraction 0.42 -> 42%
    assert s.shadow_direction_deg == 225.0
    assert s.overlaps_subject_lot is True
    assert r.height_m == 9.5


def test_shadow_does_not_read_legacy_keys():
    legacy = {"scenarios": [{"date_label": "X", "time_label": "Y", "overlap_pct": 50}]}
    s = _build_shadow_result(legacy).scenarios[0]
    assert s.date_label == ""  # must read 'label'
    assert s.time_label == ""  # must read 'time_local'


def test_shadow_none_input():
    assert _build_shadow_result(None) is None


# ── Shadow pass-through parity (PR-B): recorded Kincumber run 2026-07-16 —
# default 9 m height (no LEP height mapped), run confidence "low", Sentinel-2
# change detection timed out, 5 scenarios. Geometry keys deliberately absent
# (the brief renders a table, not a map). ──
KINCUMBER_SHADOW_RAW = {
    "height_m": 9.0,
    "height_source": "default",
    "adg_compliant": True,
    "worst_case_scenario": "jun21_3pm",
    "confidence": "low",
    "scenarios": [
        {"label": "ADG worst case 9am Jun 21", "time_local": "09:00",
         "shadow_length_m": 19.0, "shadow_overlap_fraction": 0.095,
         "shadow_direction_deg": 222.6, "overlaps_subject_lot": False},
        {"label": "ADG worst case noon Jun 21", "time_local": "12:00",
         "shadow_length_m": 13.8, "shadow_overlap_fraction": 0.063,
         "shadow_direction_deg": 179.2, "overlaps_subject_lot": False},
        {"label": "ADG worst case 3pm Jun 21", "time_local": "15:00",
         "shadow_length_m": 19.7, "shadow_overlap_fraction": 0.112,
         "shadow_direction_deg": 136.3, "overlaps_subject_lot": False},
        {"label": "Spring equinox noon", "time_local": "12:00",
         "shadow_length_m": 6.1, "shadow_overlap_fraction": 0.013,
         "shadow_direction_deg": 175.0, "overlaps_subject_lot": False},
        {"label": "Summer solstice noon", "time_local": "12:00",
         "shadow_length_m": 1.6, "shadow_overlap_fraction": 0.001,
         "shadow_direction_deg": 183.0, "overlaps_subject_lot": False},
    ],
}


def test_shadow_carries_confidence():
    """The construction_change_* assertions were REMOVED 2026-08-07 (§4h) with
    the adjacent-lot check. They were correct against the old doctrine; the
    fields no longer exist on the contract, so keeping them would test a
    feature the product does not have."""
    r = _build_shadow_result(KINCUMBER_SHADOW_RAW)
    assert r is not None
    assert r.confidence == "low"
    assert r.height_source == "default"
    assert len(r.scenarios) == 5
    labels = [s.date_label for s in r.scenarios]
    assert labels[0] == "ADG worst case 9am Jun 21"
    assert labels[-1] == "Summer solstice noon"
    assert r.scenarios[2].overlap_pct == pytest.approx(11.2)


def test_shadow_new_fields_default_none_on_sparse_output():
    r = _build_shadow_result({"scenarios": []})
    assert r.confidence is None
