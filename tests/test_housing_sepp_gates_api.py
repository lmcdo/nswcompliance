"""Tests for services/housing_sepp_gates_api.py: each gate is True / False / None, and None is never folded to False."""
import importlib
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import services.housing_sepp_gates_api as g

NOT_EXCLUDED = {"low_mid_rise": False}
EXCLUDED = {"low_mid_rise": True}
NEAR = {"within_catchment": True, "label": "Northmead Village"}
NOT_NEAR = {"within_catchment": False}
TOD = {"in_tod": True}
NOT_TOD = {"in_tod": False}
DUAL_OK = {"prohibited": False}


def patch(monkeypatch, excl=NOT_EXCLUDED, tod=NOT_TOD, tc=NOT_NEAR, dop=DUAL_OK):
    for name, val in (
        ("fetch_sepp_exclusions", excl),
        ("fetch_tod_catchment", tod),
        ("fetch_town_centre_catchment", tc),
        ("fetch_dual_occ_prohibition", dop),
    ):
        if isinstance(val, Exception):
            def boom(*a, _e=val):
                raise _e
            monkeypatch.setattr(g, name, boom)
        else:
            monkeypatch.setattr(g, name, lambda *a, _v=val: _v)


def test_near_town_centre_and_not_excluded_is_in_area(monkeypatch):
    patch(monkeypatch, tc=NEAR)
    r = g.lmr_gates(-33.8, 151.0)
    assert r["in_lmr_area"] is True
    assert r["near_town_centre"] is True
    assert r["town_centre"] == "Northmead Village"


def test_in_tod_is_in_area(monkeypatch):
    patch(monkeypatch, tod=TOD)
    assert g.lmr_gates(-33.8, 151.0)["in_lmr_area"] is True


def test_neither_is_not_in_area(monkeypatch):
    patch(monkeypatch)
    r = g.lmr_gates(-33.8, 151.0)
    assert r["in_lmr_area"] is False
    assert r["in_tod"] is False and r["near_town_centre"] is False


def test_excluded_is_not_in_area_even_if_near(monkeypatch):
    patch(monkeypatch, tc=NEAR, excl=EXCLUDED)
    r = g.lmr_gates(-33.8, 151.0)
    assert r["in_lmr_area"] is False
    assert r["lmr_excluded"] is True


def test_town_centre_unanswered_and_not_tod_is_unknown_never_false(monkeypatch):
    patch(monkeypatch, tc=None)
    r = g.lmr_gates(-33.8, 151.0)
    assert r["near_town_centre"] is None
    assert r["in_lmr_area"] is None


def test_exclusions_unanswered_and_near_is_unknown(monkeypatch):
    patch(monkeypatch, tc=NEAR, excl=None)
    r = g.lmr_gates(-33.8, 151.0)
    assert r["lmr_excluded"] is None
    assert r["in_lmr_area"] is None


def test_exclusion_payload_without_the_flag_is_unknown(monkeypatch):
    patch(monkeypatch, tc=NEAR, excl={})
    assert g.lmr_gates(-33.8, 151.0)["in_lmr_area"] is None


def test_no_anchor_is_false_even_if_exclusions_unanswered(monkeypatch):
    patch(monkeypatch, excl=None)
    assert g.lmr_gates(-33.8, 151.0)["in_lmr_area"] is False


def test_a_raising_fetcher_gives_none_for_that_field_only(monkeypatch):
    patch(monkeypatch, tc=NEAR, tod=RuntimeError("layer down"))
    r = g.lmr_gates(-33.8, 151.0)
    assert r["in_tod"] is None
    assert r["near_town_centre"] is True
    assert r["lmr_excluded"] is False
    assert r["in_lmr_area"] is True


def test_dual_occupancy_gate_is_passed_through(monkeypatch):
    patch(monkeypatch, dop={"prohibited": True})
    assert g.lmr_gates(-33.8, 151.0)["dual_occ_prohibited"] is True
    patch(monkeypatch, dop=None)
    assert g.lmr_gates(-33.8, 151.0)["dual_occ_prohibited"] is None


def client():
    app = FastAPI()
    app.include_router(g.router)
    return TestClient(app)


def test_endpoint_rejects_a_point_outside_nsw(monkeypatch):
    patch(monkeypatch)
    assert client().get("/pipeline/housing-sepp/gates", params={"lat": 51.5, "lng": -0.12}).status_code == 422


def test_endpoint_rejects_swapped_coordinates(monkeypatch):
    patch(monkeypatch)
    assert client().get("/pipeline/housing-sepp/gates", params={"lat": 151.0, "lng": -33.8}).status_code == 422


def test_endpoint_returns_json_for_a_valid_point(monkeypatch):
    patch(monkeypatch, tc=NEAR)
    r = client().get("/pipeline/housing-sepp/gates", params={"lat": -33.8, "lng": 151.0})
    assert r.status_code == 200
    body = r.json()
    assert body["in_lmr_area"] is True
    assert set(body) == {"in_lmr_area", "in_tod", "near_town_centre", "town_centre", "lmr_excluded",
                         "dual_occ_prohibited", "source"}


@pytest.mark.integration
def test_live_berrigan_st_winston_hills_is_not_in_a_low_and_mid_rise_area(monkeypatch):
    """Real HTTP to the NSW Planning Portal layers. Skips (never passes) when any layer is unreachable."""
    stub = sys.modules.pop("requests", None)  # conftest_mocks stubs requests; portal_constraints imported the stub
    try:
        try:
            real_requests = importlib.import_module("requests")
        except ImportError:
            pytest.skip("real requests module not installed")
        import services.portal_constraints as pc
        monkeypatch.setattr(pc, "requests", real_requests)
        r = g.lmr_gates(-33.77766669616996, 150.9970337411538)
        if any(r[k] is None for k in ("in_lmr_area", "near_town_centre", "in_tod", "lmr_excluded")):
            pytest.skip(f"a planning layer did not answer: {r}")
        assert r["in_lmr_area"] is False
        assert r["near_town_centre"] is False
    finally:
        if stub is not None:
            sys.modules["requests"] = stub
