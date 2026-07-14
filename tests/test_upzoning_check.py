"""Upzoning-check endpoint (/pipeline/upzoning) — thin exposure of the eligibility engine.

These tests run the REAL evaluate_eligibility (standards + gates mocked) so the
endpoint's wiring is mutation-tested: dropping the heritage flag, hand-rolling
gate logic, or hardcoding the forms list all fail. Pinned here:
  - the Haberfield regression at route level (heritage suppresses LMR forms);
  - the []-disambiguation (non-residential vs standards outage — an outage must
    surface as "unavailable", never as "nothing is possible here");
  - fail modes (unresolvable address, missing address, missing lot dimensions).
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import services.housing_sepp_eligibility as hse
import services.upzoning_check as upz

# Same fake standards shape as tests/test_housing_sepp_eligibility.py GROUPED.
GROUPED = {
    "dwelling_houses":  {"requires_lmr_area": False, "applicable_zones": ["R1", "R2", "R3", "R4"], "min_lot_size": None,  "min_lot_width": None},
    "dual_occupancy":   {"requires_lmr_area": False, "applicable_zones": ["R1", "R2", "R3", "R4"], "min_lot_size": 450.0, "min_lot_width": 12.0},
    "terraces":         {"requires_lmr_area": True,  "applicable_zones": ["R1", "R2", "R3", "R4"], "min_lot_size": 500.0, "min_lot_width": 18.0},
}

GATES_LMR = {"in_lmr_area": True, "in_tod": False, "dual_occ_prohibited": False}

# Real parse_controls shape (generate_conveyancing_report.py:3999): "zone" holds
# the CODE, "zone_full" holds the portal's zone NAME with NO code embedded. The
# original fixture embedded the code in zone_full, which masked a preference-order
# bug the live verify caught (every lot mislabelled not_residential).
CONTROLS_CLEAN = {
    "zone": "R2", "zone_full": "Low Density Residential",
    "zone_epi": "Test LEP 2013", "legislation_url": "https://legislation.nsw.gov.au/test",
    "heritage_items": [], "heritage_hca": [],
}
CONTROLS_HERITAGE = {
    **CONTROLS_CLEAN,
    "heritage_items": ["Haberfield Heritage Conservation Area"],
    "heritage_hca": ["Haberfield Heritage Conservation Area"],
}


class _Dims:
    """Mirrors constraint_models.LotDimensions' consumed fields (incl. battleaxe)."""

    def __init__(self, area, frontage, lot_type="rectangular", main_lot_width=None):
        self.area_m2 = area
        self.frontage_m = frontage
        self.lot_type = lot_type
        self.battleaxe_main_lot_width_m = main_lot_width
        self.battleaxe_access_way_width_m = None
        self.battleaxe_access_way_length_m = None
        self.battleaxe_main_lot_area_m2 = None


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(upz.router)
    return TestClient(app)


@pytest.fixture
def wire(monkeypatch):
    """Wire the endpoint's externals; returns a dict tests may mutate per-case."""
    state = {
        "resolved": (1304911, -33.886142, 151.143860, None),
        "controls": CONTROLS_CLEAN,
        "dims": _Dims(700.0, 20.0),
        "gates": dict(GATES_LMR),
    }
    monkeypatch.setattr(upz, "resolve_address", lambda addr: state["resolved"])
    monkeypatch.setattr(upz, "get_raw_controls", lambda pid: [])
    monkeypatch.setattr(upz, "parse_controls", lambda raw: state["controls"])
    monkeypatch.setattr(upz, "fetch_lot_geometry", lambda pid: {"rings": [[0, 0]]})
    monkeypatch.setattr(upz, "calculate_lot_dimensions", lambda geom: state["dims"])
    monkeypatch.setattr(hse, "_fetch_standards_grouped", lambda: GROUPED)
    monkeypatch.setattr(hse, "_gate_inputs", lambda lat, lng: state["gates"])
    return state


def _forms_by_type(payload):
    return {f["development_type"]: f for f in payload["forms"]}


# --- expected use -------------------------------------------------------------

def test_clean_r2_lot_returns_engine_results(client, wire):
    resp = client.post("/pipeline/upzoning", json={"address": "1 Example St"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["zone"] == "R2"
    assert data["heritage"]["flag"] is False
    assert data["gates"] == GATES_LMR
    forms = _forms_by_type(data)
    assert forms["dual_occupancy"]["eligible"] is True
    assert forms["terraces"]["eligible"] is True
    # Engine wording must flow through verbatim — no rewrite at the route layer.
    assert "subject to a development application" in forms["dual_occupancy"]["reason"]


def test_heritage_lot_suppresses_lmr_forms_but_not_base_forms(client, wire):
    """The Haberfield regression, end-to-end: heritage MUST reach the engine."""
    wire["controls"] = CONTROLS_HERITAGE
    data = client.post("/pipeline/upzoning", json={"address": "1 Ramsay St"}).json()
    assert data["heritage"]["flag"] is True
    forms = _forms_by_type(data)
    assert forms["terraces"]["eligible"] is False
    assert "heritage" in forms["terraces"]["reason"].lower()
    assert forms["dual_occupancy"]["eligible"] is True  # base form unaffected


def test_dual_occ_prohibition_gate_flows_through(client, wire):
    wire["gates"] = {**GATES_LMR, "dual_occ_prohibited": True}
    forms = _forms_by_type(client.post("/pipeline/upzoning", json={"address": "x"}).json())
    assert forms["dual_occupancy"]["eligible"] is False
    assert "prohibited" in forms["dual_occupancy"]["reason"]


# --- edge cases ----------------------------------------------------------------

def test_missing_lot_dimensions_yields_unconfirmed_not_eligible(client, wire):
    wire["dims"] = None  # geometry unavailable → area/width None
    data = client.post("/pipeline/upzoning", json={"address": "x"}).json()
    assert data["lot_area_m2"] is None and data["lot_width_m"] is None
    forms = _forms_by_type(data)
    assert forms["dual_occupancy"]["eligible"] is False
    assert forms["dual_occupancy"]["unconfirmed"] is True


def test_battleaxe_lot_uses_head_width_for_eligibility(client, wire):
    """Bowral-class regression at route level: a flag lot with a 16 m handle and
    a 70 m head must feed the HEAD width into the engine — width-gated forms
    resolve on their merits instead of collapsing to 'unconfirmed'."""
    wire["dims"] = _Dims(4189.0, None, lot_type="battleaxe", main_lot_width=70.09)
    data = client.post("/pipeline/upzoning", json={"address": "x"}).json()
    assert data["lot_width_m"] == pytest.approx(70.09)
    assert data["lot_type"] == "battleaxe"
    forms = _forms_by_type(data)
    # 4,189 m² x 70 m head passes dual-occ (450 m² / 12 m) and terrace width (18 m)
    assert forms["dual_occupancy"]["eligible"] is True
    assert forms["terraces"]["eligible"] is True  # in-LMR fixture gates


def test_non_residential_zone_is_labelled_not_unavailable(client, wire):
    wire["controls"] = {**CONTROLS_CLEAN, "zone": "B4", "zone_full": "Mixed Use"}
    data = client.post("/pipeline/upzoning", json={"address": "x"}).json()
    assert data["status"] == "not_residential"
    assert data["forms"] == []


def test_zone_code_comes_from_the_zone_field_not_the_name(client, wire):
    """Live-verify regression (2026-07-13): zone_full is the portal's NAME with no
    code ("High Density Residential"); normalising it yields "HIGH" and mislabels
    a real R4 lot not_residential. The code must come from the "zone" field."""
    wire["controls"] = {**CONTROLS_CLEAN, "zone": "R4", "zone_full": "High Density Residential"}
    data = client.post("/pipeline/upzoning", json={"address": "x"}).json()
    assert data["zone"] == "R4"
    assert data["status"] == "ok"
    assert data["zone_full"] == "High Density Residential"


# --- failure cases ---------------------------------------------------------------

def test_standards_outage_reports_unavailable_not_empty_success(client, wire, monkeypatch):
    """A data outage must be visible — never rendered as 'nothing possible'."""
    def _boom():
        raise RuntimeError("standards DB down")
    monkeypatch.setattr(hse, "_fetch_standards_grouped", _boom)
    data = client.post("/pipeline/upzoning", json={"address": "x"}).json()
    assert data["status"] == "unavailable"
    assert data["forms"] == []


def test_unresolvable_address_is_422(client, wire, monkeypatch):
    def _fail(addr):
        raise RuntimeError("geocoder down")
    monkeypatch.setattr(upz, "resolve_address", _fail)
    assert client.post("/pipeline/upzoning", json={"address": "nowhere"}).status_code == 422


def test_resolved_without_coordinates_is_422(client, wire):
    wire["resolved"] = (123, None, None, None)
    assert client.post("/pipeline/upzoning", json={"address": "x"}).status_code == 422


def test_blank_address_is_400(client, wire):
    assert client.post("/pipeline/upzoning", json={"address": "   "}).status_code == 400


# --- lga_name derivation (feeds the LEP land-use panel; must be match-based) ----

def test_lga_name_derived_from_lep_epi_name(client, wire):
    wire["controls"] = {**CONTROLS_CLEAN, "zone_epi": "Wingecarribee Local Environmental Plan 2010"}
    data = client.post("/pipeline/upzoning", json={"address": "x"}).json()
    assert data["lga_name"] == "Wingecarribee"


def test_lga_name_none_for_non_lep_instrument(client, wire):
    """A non-LEP EPI title must yield None (panel absent), never leak the whole
    title as an LGA name into the permissibility lookup."""
    wire["controls"] = {**CONTROLS_CLEAN, "zone_epi": "Sydney Region Growth Centres SEPP 2006"}
    data = client.post("/pipeline/upzoning", json={"address": "x"}).json()
    assert data["lga_name"] is None
