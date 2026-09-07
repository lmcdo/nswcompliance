"""S3 contract drift check — the live tripwire on the S2 typed boundary.

Validates that a service output's keys still match the brief's S2 contract.
A renamed/dropped key (the #589 class) shows up as DRIFT here instead of as a
silent null in the card on a real run.
"""
from services.intelligence_brief import (
    FloodServiceOutput,
    BushfireServiceOutput,
    ShadowServiceOutput,
    _build_flood_detail,
)
from brief_contract_drift import check_drift, check_outputs

import logging


# A realistic, on-contract flood output (all contract keys present).
_FLOOD_OK = {
    "flood_signal": "low",
    "epi_flood_class": "1% AEP",
    "epi_flood_label": "Flood planning area",
    "ems_flood_detected": False,
    "ems_activations": [],
    "sar_flood_detected": None,
    "sar_confidence": None,
    "sar_analysis_date": None,
    "ses_in_flood_planning_area": False,
    "ses_flood_class": None,
    "ses_study_name": None,
    "jrc_water_occurrence_pct": 0.0,
    "jrc_data_year": 2021,
    "dea_wofs_frequency_pct": 0.0,
    "bom_gauge_name": "Example gauge",
    "bom_gauge_distance_km": 20.5,
    "bom_last_major_flood_date": None,
    "bom_last_major_flood_peak_m": None,
    "bom_flood_history": [],
    "in_100yr_flood_zone": True,
    "in_100yr_flood_zone_unconsulted": [],
    "ground_elevation_m_ahd": None,
    "s1_gap_warning": None,
    "flood_studies": [],
    "data_currency": "unknown",   # extra service key — informational, not drift
}


def test_no_drift_when_all_contract_keys_present():
    f = check_drift(FloodServiceOutput, _FLOOD_OK)
    assert f["drift"] is False
    assert f["missing"] == []
    assert "data_currency" in f["extra"]  # new key surfaced, but not drift


def test_drift_when_a_contract_key_is_renamed():
    # The #589 bug: service emits jrc_occurrence_pct, contract expects jrc_water_occurrence_pct.
    renamed = {**_FLOOD_OK}
    del renamed["jrc_water_occurrence_pct"]
    renamed["jrc_occurrence_pct"] = 0.0   # old/wrong name
    f = check_drift(FloodServiceOutput, renamed)
    assert f["drift"] is True
    assert "jrc_water_occurrence_pct" in f["missing"]
    assert "jrc_occurrence_pct" in f["extra"]


def test_drift_when_a_contract_key_is_dropped():
    dropped = {k: v for k, v in _FLOOD_OK.items() if k != "bom_gauge_distance_km"}
    f = check_drift(FloodServiceOutput, dropped)
    assert f["drift"] is True
    assert "bom_gauge_distance_km" in f["missing"]


def test_empty_output_is_full_drift():
    f = check_drift(FloodServiceOutput, {})
    assert f["drift"] is True
    assert set(f["missing"]) == set(FloodServiceOutput.model_fields)


def test_check_outputs_flags_one_service_among_many():
    captured = {
        "flood": {"outputs": _FLOOD_OK},
        "bushfire": {"outputs": {k: None for k in BushfireServiceOutput.model_fields}},
        "shadow": {k: None for k in ShadowServiceOutput.model_fields},  # no outputs wrapper
    }
    findings, has_drift = check_outputs(captured)
    assert has_drift is False  # all keys present (values None is fine — that's genuine empty)

    # Now break flood
    captured["flood"]["outputs"] = {"jrc_occurrence_pct": 0.0}
    findings, has_drift = check_outputs(captured)
    assert has_drift is True
    flood = next(f for f in findings if f["service"] == "FloodServiceOutput")
    assert "jrc_water_occurrence_pct" in flood["missing"]


def test_shadow_uses_no_outputs_wrapper():
    captured = {"shadow": {k: None for k in ShadowServiceOutput.model_fields}}
    _, has_drift = check_outputs(captured)
    assert has_drift is False


# --- inline tripwire: the brief logs CONTRACT-DRIFT on a real drifted output --

def test_build_flood_logs_drift_warning(caplog):
    raw = {"outputs": {"jrc_occurrence_pct": 0.0}}  # old/renamed key -> drift
    with caplog.at_level(logging.WARNING):
        fd = _build_flood_detail(raw)
    assert fd is not None  # behaviour unchanged — still builds (fail-soft to None)
    assert any("CONTRACT-DRIFT" in r.getMessage() for r in caplog.records)


def test_build_flood_no_warning_on_good_output(caplog):
    raw = {"outputs": _FLOOD_OK}
    with caplog.at_level(logging.WARNING):
        _build_flood_detail(raw)
    assert not any("CONTRACT-DRIFT" in r.getMessage() for r in caplog.records)
