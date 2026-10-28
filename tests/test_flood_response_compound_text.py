"""The flood response accepts the compound-risk layer labels it is given.

_query_compound_risk_layers returns the overlay's own label ("Riparian Area")
or True. The response model typed these four fields bool only, so every
address on heritage, riparian, wetland or landslide land failed FastAPI
response validation after its report had been saved: 31 of 308 checked
addresses (2026-06-13 to 2026-10-28) got a 500 instead of a flood result.
The payload below is the one production rejected on 2026-10-28 (Railway log),
with the address replaced.
"""
from __future__ import annotations

import pytest

from services.flood_truth import FloodResponse

REJECTED = {
    "address": "1 Test St, Cecil Park NSW 2178", "lat": -33.8647, "lng": 150.8378,
    "run_date": "2026-10-28",
    "outputs": {
        "epi_flood_class": "none", "epi_flood_label": "No EPI Flood Overlay",
        "ems_flood_detected": False, "ems_activations": [],
        "jrc_water_occurrence_pct": 0.0, "jrc_data_year": 2021, "dea_wofs_frequency_pct": 0.0,
        "ses_in_flood_planning_area": False, "bom_gauge_name": "Georges River at Liverpool",
        "bom_gauge_distance_km": 9.8, "bom_flood_history": [], "data_currency": "unknown",
        "flood_studies": [], "ground_elevation_m_ahd": 88.06,
        "in_100yr_flood_zone_unconsulted": [], "in_100yr_flood_zone": False,
        "compound_heritage": None, "compound_riparian": "Riparian Area",
        "compound_wetlands": None, "compound_landslide": None,
        "compound_risk_layers": ["riparian"],
        "compound_risk_notes": ["Property is on or adjacent to mapped riparian land."],
        "flood_signal": "none",
    },
    "confidence": "medium", "data_sources": ["NSW SEED EPI WFS"], "data_gaps": [],
}


def test_the_payload_production_rejected_now_validates():
    r = FloodResponse.model_validate(REJECTED)
    assert r.outputs.compound_riparian == "Riparian Area"


@pytest.mark.parametrize("field", ["compound_heritage", "compound_riparian",
                                   "compound_wetlands", "compound_landslide"])
@pytest.mark.parametrize("value", ["Some Layer Label", True, None])
def test_every_compound_field_takes_a_label_true_or_none(field, value):
    payload = {**REJECTED, "outputs": {**REJECTED["outputs"], field: value}}
    got = getattr(FloodResponse.model_validate(payload).outputs, field)
    assert got == value and type(got) is type(value)
