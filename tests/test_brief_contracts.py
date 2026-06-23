"""S2 typed boundary — service->brief contract tests.

The brief consumes service outputs through typed contract models (not loose dict
.get), so a renamed/dropped service key is a typed/test failure instead of a
silent null in the card (the jrc_occurrence_pct vs jrc_water_occurrence_pct class).

Increment 1: the flood service output.
"""
from services.intelligence_brief import FloodServiceOutput, _build_flood_detail


# The keys the flood service (flood_truth.run_flood) is documented to emit in
# `outputs`. If the service renames one, the golden/drift check (S3) re-captures
# real output and this set diverges -> caught. Here we lock the brief's contract
# to exactly this expected set so it can't silently drift.
EXPECTED_FLOOD_KEYS = {
    "epi_flood_class",
    "epi_flood_label",
    "jrc_water_occurrence_pct",
    "dea_wofs_frequency_pct",
    "bom_gauge_distance_km",
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
