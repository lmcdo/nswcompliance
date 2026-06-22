"""Golden-fixture guard: brief satellite cards must surface what the services emit.

Regression guard for the key-mismatch class of bug (Tier 0 of
ce-brief-content-enrichment). The services return rich payloads but the brief's
_build_* functions previously read the WRONG dict keys and silently emitted
null. Fixtures below use the REAL service output keys (captured live
2026-06-22). The `*_does_not_read_legacy_keys` tests pin the fix: if anyone
reverts to the old keys, they fail.
"""
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
        "compliance": {"cross_overlays": {"flood": False, "heritage": True}},
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
    assert d.cross_overlays == {"flood": False, "heritage": True}
    assert d.confidence == "medium"


def test_bushfire_does_not_read_legacy_rfs_key():
    # The bug was reading outputs['rfs'][...]; that must NOT populate anything.
    legacy = {"outputs": {"rfs": {"category": "X", "bal_estimate": "Y"}}, "confidence": "low"}
    d = _build_bushfire_detail(legacy)
    assert d.category is None
    assert d.bal_estimate is None


def test_bushfire_none_input():
    assert _build_bushfire_detail(None) is None


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
