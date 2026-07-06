"""Backend Housing-SEPP eligibility engine (consolidation P2) — the single source of truth.

Ports the frontend gate logic but computes inLMRArea (776) and the TOD catchment (752/759)
authoritatively. These tests pin the per-form gates (zone, LMR-area, lot size, lot width,
TOD, dual-occ prohibition), the conservative defaults (unconfirmed lot / failed gate ->
ineligible, never falsely eligible), and the fail-safe gate-input fetcher.
"""
import pytest

import services.housing_sepp_eligibility as hse
from services.housing_sepp_eligibility import (
    evaluate_eligibility,
    normalize_zone,
    _gate_inputs,
)

# Fake housing_sepp_standards (mirrors the real shape).
GROUPED = {
    "dwelling_houses":      {"requires_lmr_area": False, "applicable_zones": ["R1", "R2", "R3", "R4"], "min_lot_size": None,  "min_lot_width": None},
    "dual_occupancy":       {"requires_lmr_area": False, "applicable_zones": ["R1", "R2", "R3", "R4"], "min_lot_size": 450.0, "min_lot_width": 12.0},
    "terraces":             {"requires_lmr_area": True,  "applicable_zones": ["R1", "R2", "R3", "R4"], "min_lot_size": 500.0, "min_lot_width": 18.0},
    "residential_flat_r1r2": {"requires_lmr_area": True, "applicable_zones": ["R1", "R2"],             "min_lot_size": 500.0, "min_lot_width": 12.0},
    "residential_flat_r3r4_inner": {"requires_lmr_area": True, "applicable_zones": ["R3", "R4"],       "min_lot_size": None,  "min_lot_width": None},
    # Known dataset gap: manor_house has no min_lot_size and requires_lmr_area=False.
    "manor_house":          {"requires_lmr_area": False, "applicable_zones": ["R1", "R2", "R3", "R4"], "min_lot_size": None, "min_lot_width": None},
}

ALL_FALSE = {"in_lmr_area": False, "in_tod": False, "dual_occ_prohibited": False}


@pytest.fixture(autouse=True)
def _mock_standards(monkeypatch):
    monkeypatch.setattr(hse, "_fetch_standards_grouped", lambda: GROUPED)


def _by_type(results):
    return {r.development_type: r for r in results}


# --- zone normalisation -----------------------------------------------------

def test_normalize_zone():
    assert normalize_zone("R2 Low Density Residential") == "R2"
    assert normalize_zone(" r3 ") == "R3"
    assert normalize_zone(None) == ""
    assert normalize_zone("") == ""


def test_non_residential_zone_returns_empty():
    assert evaluate_eligibility("B4 Mixed Use", 800, 20, -33.8, 151.1, gate_inputs=ALL_FALSE) == []


# --- the gates --------------------------------------------------------------

def test_dwelling_house_is_eligible_with_no_lot_data_and_no_gates():
    r = _by_type(evaluate_eligibility("R2", None, None, -33.8, 151.1, gate_inputs=ALL_FALSE))
    assert r["dwelling_houses"].eligible is True


def test_lmr_form_ineligible_when_not_in_lmr_area():
    r = _by_type(evaluate_eligibility("R2", 600, 20, -33.8, 151.1, gate_inputs=ALL_FALSE))
    assert r["terraces"].eligible is False
    assert "Low and Mid-Rise" in r["terraces"].reason


def test_lmr_form_eligible_when_in_area_and_lot_ok():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 600, 20, -33.8, 151.1, gate_inputs=gates))
    assert r["terraces"].eligible is True
    assert "subject to a development application" in r["terraces"].reason


def test_lot_too_small_is_ineligible():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 400, 20, -33.8, 151.1, gate_inputs=gates))
    assert r["terraces"].eligible is False
    assert "below the minimum" in r["terraces"].reason


def test_unconfirmed_lot_is_conservatively_ineligible():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", None, None, -33.8, 151.1, gate_inputs=gates))
    assert r["terraces"].eligible is False
    assert "unconfirmed" in r["terraces"].reason


def test_lot_too_narrow_is_ineligible():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 600, 15, -33.8, 151.1, gate_inputs=gates))  # 15 < 18m terrace width
    assert r["terraces"].eligible is False
    assert "width" in r["terraces"].reason.lower()


def test_all_residential_flats_require_tod_catchment():
    in_lmr = {**ALL_FALSE, "in_lmr_area": True}
    # R3/R4 flats need TOD
    r = _by_type(evaluate_eligibility("R3", 800, 20, -33.8, 151.1, gate_inputs=in_lmr))
    assert r["residential_flat_r3r4_inner"].eligible is False
    assert "Transport Oriented Development" in r["residential_flat_r3r4_inner"].reason
    r2 = _by_type(evaluate_eligibility("R3", 800, 20, -33.8, 151.1, gate_inputs={**in_lmr, "in_tod": True}))
    assert r2["residential_flat_r3r4_inner"].eligible is True
    # R1/R2 flats are ALSO mid-rise -> also need TOD (not eligible statewide just by LMR area)
    r3 = _by_type(evaluate_eligibility("R2", 700, 20, -33.8, 151.1, gate_inputs=in_lmr))
    assert r3["residential_flat_r1r2"].eligible is False
    r4 = _by_type(evaluate_eligibility("R2", 700, 20, -33.8, 151.1, gate_inputs={**in_lmr, "in_tod": True}))
    assert r4["residential_flat_r1r2"].eligible is True


def test_dual_occ_prohibition_blocks_dual_occ():
    gates = {**ALL_FALSE, "dual_occ_prohibited": True}
    r = _by_type(evaluate_eligibility("R2", 600, 20, -33.8, 151.1, gate_inputs=gates))
    assert r["dual_occupancy"].eligible is False
    assert "prohibited" in r["dual_occupancy"].reason
    r2 = _by_type(evaluate_eligibility("R2", 600, 20, -33.8, 151.1, gate_inputs=ALL_FALSE))
    assert r2["dual_occupancy"].eligible is True


def test_zone_filter_drops_inapplicable_forms():
    # residential_flat_r1r2 applies to R1/R2 only — absent for an R3 lot.
    r = _by_type(evaluate_eligibility("R3", 800, 20, -33.8, 151.1, gate_inputs={**ALL_FALSE, "in_lmr_area": True}))
    assert "residential_flat_r1r2" not in r


def test_heritage_suppresses_lmr_forms_but_not_base_forms():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 700, 20, -33.8, 151.1, heritage=True, gate_inputs=gates))
    assert r["terraces"].eligible is False  # LMR form suppressed on heritage
    assert "heritage" in r["terraces"].reason.lower()
    assert r["residential_flat_r1r2"].eligible is False
    assert r["dual_occupancy"].eligible is True  # base form unaffected by heritage


def test_form_missing_lot_standard_is_conservatively_ineligible():
    # manor_house has no min_lot_size in the dataset -> must NOT pass by default.
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 380, 9, -33.8, 151.1, gate_inputs=gates))
    assert r["manor_house"].eligible is False
    assert "dataset" in r["manor_house"].reason
    # on a generous lot it is still conservatively ineligible (no lot standard to confirm)
    r2 = _by_type(evaluate_eligibility("R2", 900, 25, -33.8, 151.1, gate_inputs=gates))
    assert r2["manor_house"].eligible is False


# --- unconfirmed: a data gap must not read as a failed standard ---------------
# (Bowral regression: an irregular 4,096 m² lot has no measurable frontage, so
# every width-gated form failed — the UI showed "Not eligible" for a lot that
# passed every measurable standard. The outcome stays conservative; the flag
# lets the UI say "Unconfirmed" instead.)

def test_missing_width_is_unconfirmed_but_still_conservatively_ineligible():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 4096, None, -33.8, 151.1, gate_inputs=gates))
    assert r["terraces"].eligible is False
    assert r["terraces"].unconfirmed is True
    assert "unconfirmed" in r["terraces"].reason


def test_width_below_minimum_is_a_failed_standard_not_unconfirmed():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 600, 15, -33.8, 151.1, gate_inputs=gates))
    assert r["terraces"].eligible is False
    assert r["terraces"].unconfirmed is False


def test_missing_area_is_unconfirmed_but_area_below_minimum_is_not():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", None, 20, -33.8, 151.1, gate_inputs=gates))
    assert r["terraces"].eligible is False
    assert r["terraces"].unconfirmed is True
    r2 = _by_type(evaluate_eligibility("R2", 400, 20, -33.8, 151.1, gate_inputs=gates))
    assert r2["terraces"].eligible is False
    assert r2["terraces"].unconfirmed is False


def test_missing_lot_standard_is_unconfirmed():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 900, 25, -33.8, 151.1, gate_inputs=gates))
    assert r["manor_house"].eligible is False
    assert r["manor_house"].unconfirmed is True


def test_eligible_and_genuine_gate_failures_are_never_unconfirmed():
    gates = {**ALL_FALSE, "in_lmr_area": True}
    r = _by_type(evaluate_eligibility("R2", 600, 20, -33.8, 151.1, gate_inputs=gates))
    assert r["terraces"].eligible is True and r["terraces"].unconfirmed is False
    # not-in-LMR-area is a gate outcome, not a measurement gap
    r2 = _by_type(evaluate_eligibility("R2", 600, 20, -33.8, 151.1, gate_inputs=ALL_FALSE))
    assert r2["terraces"].eligible is False and r2["terraces"].unconfirmed is False
    # TOD absence likewise
    r3 = _by_type(evaluate_eligibility("R3", 800, 20, -33.8, 151.1, gate_inputs=gates))
    assert r3["residential_flat_r3r4_inner"].unconfirmed is False


def test_rfb_r3r4_without_min_lot_is_NOT_caught_by_the_gap_guard():
    # r3r4 RFB legitimately has no min_lot (TOD-gated, not a data gap) -> stays eligible in TOD.
    gates = {**ALL_FALSE, "in_lmr_area": True, "in_tod": True}
    r = _by_type(evaluate_eligibility("R3", 800, 20, -33.8, 151.1, gate_inputs=gates))
    assert r["residential_flat_r3r4_inner"].eligible is True


def test_standards_fetch_failure_returns_empty(monkeypatch):
    def _boom():
        raise RuntimeError("DB down")
    monkeypatch.setattr(hse, "_fetch_standards_grouped", _boom)
    assert evaluate_eligibility("R2", 600, 20, -33.8, 151.1, gate_inputs=ALL_FALSE) == []


# --- _gate_inputs fail-safety ------------------------------------------------

def test_gate_inputs_missing_coords_all_false():
    assert _gate_inputs(None, 151.1) == {"in_lmr_area": False, "in_tod": False, "dual_occ_prohibited": False}


def test_gate_inputs_failsafe_on_query_errors(monkeypatch):
    def _boom(lat, lng):
        raise RuntimeError("ArcGIS down")
    monkeypatch.setattr(hse, "fetch_sepp_exclusions", _boom)
    monkeypatch.setattr(hse, "fetch_tod_catchment", _boom)
    monkeypatch.setattr(hse, "fetch_dual_occ_prohibition", _boom)
    assert _gate_inputs(-33.8, 151.1) == {"in_lmr_area": False, "in_tod": False, "dual_occ_prohibited": False}


def test_gate_inputs_in_lmr_area_only_when_not_excluded(monkeypatch):
    monkeypatch.setattr(hse, "fetch_sepp_exclusions", lambda lat, lng: {"low_mid_rise": False})
    monkeypatch.setattr(hse, "fetch_tod_catchment", lambda lat, lng: {"in_tod": False})
    monkeypatch.setattr(hse, "fetch_dual_occ_prohibition", lambda lat, lng: {"prohibited": False})
    assert _gate_inputs(-33.8, 151.1)["in_lmr_area"] is True
    # excluded -> not in LMR area
    monkeypatch.setattr(hse, "fetch_sepp_exclusions", lambda lat, lng: {"low_mid_rise": True})
    assert _gate_inputs(-33.8, 151.1)["in_lmr_area"] is False
