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

# Captured at collection time, before the autouse fixture below ever patches
# hse._fetch_standards_grouped — a test that wants the REAL function (not the
# GROUPED fixture) calls this name instead of going through the module attr.
_REAL_FETCH_STANDARDS_GROUPED = hse._fetch_standards_grouped

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


def test_dual_occupancy_missing_its_lot_row_is_not_passed(monkeypatch):
    # Cross-review 2026-09-15: dual_occupancy was exempt from the missing-lot guard, so a
    # dropped min_lot_size row made it eligible on any lot. It carries a lot standard; a
    # missing one is a data gap. Dwelling houses stay exempt (no SEPP lot minimum).
    no_dual_lot = {**GROUPED, "dual_occupancy": {**GROUPED["dual_occupancy"], "min_lot_size": None}}
    monkeypatch.setattr(hse, "_fetch_standards_grouped", lambda: no_dual_lot)
    r = _by_type(evaluate_eligibility("R2", 900, 25, -33.8, 151.1, gate_inputs=ALL_FALSE))
    assert r["dual_occupancy"].eligible is False
    assert r["dual_occupancy"].unconfirmed is True
    assert "dataset" in r["dual_occupancy"].reason
    assert r["dwelling_houses"].eligible is True


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
    def _boom(*args, **kwargs):
        raise RuntimeError("ArcGIS down")
    monkeypatch.setattr(hse, "fetch_sepp_exclusions", _boom)
    monkeypatch.setattr(hse, "fetch_tod_catchment", _boom)
    monkeypatch.setattr(hse, "fetch_town_centre_catchment", _boom)
    monkeypatch.setattr(hse, "fetch_dual_occ_prohibition", _boom)
    assert _gate_inputs(-33.8, 151.1) == {"in_lmr_area": False, "in_tod": False, "dual_occ_prohibited": False}


# in_lmr_area derivation: ANCHORED (town centre within 800m OR inside TOD)
# AND NOT excluded. Absence from the 776 exclusion map alone is NOT inclusion —
# the Bowral regression (2026-07-13): regional lots with no anchor for miles were
# reported in-area because 776 only carves out spots inside covered regions.

def _wire_gates(monkeypatch, *, excluded=False, in_tod=False, near_tc=False):
    monkeypatch.setattr(hse, "fetch_sepp_exclusions", lambda lat, lng: {"low_mid_rise": excluded})
    monkeypatch.setattr(hse, "fetch_tod_catchment", lambda lat, lng: {"in_tod": in_tod})
    monkeypatch.setattr(hse, "fetch_town_centre_catchment",
                        lambda lat, lng, distance_m=800: {"within_catchment": near_tc, "label": None})
    monkeypatch.setattr(hse, "fetch_dual_occ_prohibition", lambda lat, lng: {"prohibited": False})


def test_gate_inputs_not_excluded_alone_is_NOT_in_lmr_area(monkeypatch):
    """The Bowral regression: no anchor anywhere near -> not in the reform area,
    even though the lot is absent from the exclusion map."""
    _wire_gates(monkeypatch, excluded=False, in_tod=False, near_tc=False)
    assert _gate_inputs(-34.488, 150.430)["in_lmr_area"] is False


def test_gate_inputs_town_centre_anchor_plus_not_excluded_is_in_lmr_area(monkeypatch):
    _wire_gates(monkeypatch, excluded=False, near_tc=True)
    assert _gate_inputs(-33.8, 151.1)["in_lmr_area"] is True


def test_gate_inputs_tod_anchor_plus_not_excluded_is_in_lmr_area(monkeypatch):
    _wire_gates(monkeypatch, excluded=False, in_tod=True)
    assert _gate_inputs(-33.8, 151.1)["in_lmr_area"] is True


def test_gate_inputs_anchored_but_excluded_is_not_in_lmr_area(monkeypatch):
    _wire_gates(monkeypatch, excluded=True, near_tc=True, in_tod=True)
    assert _gate_inputs(-33.8, 151.1)["in_lmr_area"] is False


def test_gate_inputs_town_centre_query_failure_is_not_falsely_anchored(monkeypatch):
    """Anchor query dies -> that anchor term stays False; with no TOD either,
    the lot is NOT in the reform area (fail-closed, never falsely eligible)."""
    _wire_gates(monkeypatch, excluded=False, in_tod=False)
    def _boom(*args, **kwargs):
        raise RuntimeError("766 down")
    monkeypatch.setattr(hse, "fetch_town_centre_catchment", _boom)
    assert _gate_inputs(-33.8, 151.1)["in_lmr_area"] is False


# --- DQ-96: stale_since/stale_reason notice (W3, #839 — the contract already
# proven for services/cdc_screen.py, extended here where it was missing) -----

def test_fresh_standards_carry_no_stale_notice():
    """No stale_since in the grouped dict -> FormEligibility carries none."""
    r = _by_type(evaluate_eligibility("R2", None, None, -33.8, 151.1, gate_inputs=ALL_FALSE))
    assert r["dwelling_houses"].stale_since is None
    assert r["dwelling_houses"].stale_reason is None


def test_stale_standard_still_serves_with_a_notice(monkeypatch):
    """Founder-specified contract (W3): values keep serving; the notice rides
    along as data on the result, never a blank and never silently dropped.

    _fetch_standards_grouped's real contract carries stale_since as a raw
    datetime (isoformat'd only in _result()) — the mock must match that
    contract, not a pre-formatted string, or this test would prove nothing
    about the actual conversion path it exists to check.
    """
    import datetime as _dt

    grouped_with_stale = {
        **GROUPED,
        "dwelling_houses": {
            **GROUPED["dwelling_houses"],
            "stale_since": _dt.datetime(2026, 4, 24, 10, 54, 53, tzinfo=_dt.timezone.utc),
            "stale_reason": "State Environmental Planning Policy (Housing) 2021 version changed (24 April 2026 -> 15 May 2026)",
        },
    }
    monkeypatch.setattr(hse, "_fetch_standards_grouped", lambda: grouped_with_stale)
    r = _by_type(evaluate_eligibility("R2", None, None, -33.8, 151.1, gate_inputs=ALL_FALSE))
    assert r["dwelling_houses"].eligible is True  # screen RAN — not blanked
    assert r["dwelling_houses"].stale_since == "2026-04-24T10:54:53+00:00"
    assert "version changed" in r["dwelling_houses"].stale_reason


def test_fetch_standards_grouped_pairs_stale_date_with_its_own_reason(monkeypatch):
    """Sol #839's exact finding, replicated for this table: two rows for the
    SAME development_type with different stale_since values must return the
    LATER date paired with THAT row's own reason, never a mixed pair."""
    import datetime as _dt

    d1 = _dt.datetime(2026, 4, 24, tzinfo=_dt.timezone.utc)
    d2 = _dt.datetime(2026, 6, 8, tzinfo=_dt.timezone.utc)
    rows = [
        ("dwelling_houses", "min_lot_size", 200.0, ["R2"], False,
         "cl 3.1", "SEPP (Housing) 2021", "https://legislation.nsw.gov.au/x",
         None, d1, "amendment A"),
        ("dwelling_houses", "min_lot_width", 12.0, ["R2"], False,
         "cl 3.1(3)", "SEPP (Housing) 2021", "https://legislation.nsw.gov.au/x",
         None, d2, "amendment B"),
    ]

    class Cur:
        def execute(self, *a): pass
        def fetchall(self): return rows
        def close(self): pass

    class Conn:
        def cursor(self): return Cur()
        def close(self): pass

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setattr("psycopg2.connect", lambda *a, **k: Conn())
    out = _REAL_FETCH_STANDARDS_GROUPED()
    assert out["dwelling_houses"]["stale_since"] == d2
    assert out["dwelling_houses"]["stale_reason"] == "amendment B"


# --- secondary dwellings: answered per approval path, never by a lot minimum ---

import copy  # noqa: E402

from services.secondary_dwelling_paths import validate_rules  # noqa: E402
from tests.test_secondary_dwelling_paths import BASE_ROWS  # noqa: E402

# The old pathway-agnostic rows (ids 44 = 450 m2, 34 = 12 m) as they stand until
# migration 089 retires them: the generic gate must ignore them for this form.
_SD_WITH_OLD_ROWS = {**GROUPED, "secondary_dwelling": {
    "requires_lmr_area": False, "applicable_zones": ["R1", "R2", "R3", "R4"],  # noqa: zone-codes — fixture copy of a stored row, not a served zone list
    "min_lot_size": 450.0, "min_lot_width": 12.0}}


@pytest.fixture
def _sd_rules(monkeypatch):
    monkeypatch.setattr(hse, "_fetch_standards_grouped", lambda: _SD_WITH_OLD_ROWS)
    monkeypatch.setattr(hse, "_fetch_path_rules", lambda: validate_rules(copy.deepcopy(BASE_ROWS)).rules)


def test_secondary_dwelling_small_lot_is_not_declared_below_a_minimum(_sd_rules):
    r = _by_type(evaluate_eligibility("R2", 300, 8, -33.8, 151.1, gate_inputs=ALL_FALSE))["secondary_dwelling"]
    assert "below the minimum" not in r.reason
    # 450 m2 appears only as the DA site area for a DETACHED granny flat.
    assert "If the granny flat is detached, this lot of 300 m² is below the 450 m² site area" in r.reason
    assert "sets no single minimum lot size" in r.reason
    assert r.min_lot_size_m2 is None and r.min_lot_width_m is None
    assert r.unconfirmed is True and r.approval_paths["da"]["path"] == "da"


def test_secondary_dwelling_rules_unavailable_is_unconfirmed_never_eligible(monkeypatch):
    monkeypatch.setattr(hse, "_fetch_standards_grouped", lambda: _SD_WITH_OLD_ROWS)
    monkeypatch.setattr(hse, "_fetch_path_rules", lambda: None)
    r = _by_type(evaluate_eligibility("R2", 800, 20, -33.8, 151.1, gate_inputs=ALL_FALSE))["secondary_dwelling"]
    assert r.eligible is False and r.unconfirmed is True and r.approval_paths is None


def test_other_forms_still_use_their_lot_minimum(_sd_rules):
    r = _by_type(evaluate_eligibility("R2", 300, 8, -33.8, 151.1, gate_inputs=ALL_FALSE))["dual_occupancy"]
    assert r.eligible is False and "below the minimum 450" in r.reason
