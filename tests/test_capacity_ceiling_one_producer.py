"""The yield box and the Site Report get the capacity range from ONE producer (_capacity_ceiling).

Page check C2, 2026-10-19: the assessment yield box passed no ceiling, so 15 of 19 pages showed
one house while the LEP table on the same page permitted a dual occupancy or denser.
"""
import asyncio

import pytest

from services import constraint_arithmetic as ca
from services import intelligence_brief as ib


def _req(**kw):
    base = dict(lot_area_m2=688.05, dev_type="dwelling_house", zone="R2", lga="city_of_parramatta",
                lep_height_str="9", lep_fsr_str="0.5", frontage_m=22.4, depth_m=39.7,
                lat=-33.7765, lng=150.9856, lga_name="CITY OF PARRAMATTA", heritage=False)
    base.update(kw)
    return ca.ConstraintArithmeticFullRequest(**base)


@pytest.fixture
def offline(monkeypatch):
    """No DB, no ArcGIS: stub the data fetchers the endpoint calls."""
    monkeypatch.setattr(ca, "_fetch_constraint_data_from_db", lambda **k: ([], [], []))
    monkeypatch.setattr(ca, "_fetch_dcp_coverage", lambda *a, **k: None)
    monkeypatch.setattr(ib, "_fetch_heritage_postgis", lambda lat, lng, wkt: {"has_heritage": False})
    calls = []

    def fake_ceiling(zone, lga, lat, lng, area, heritage, width_range=None, results=None):
        calls.append(dict(zone=zone, lga=lga, heritage=heritage, width=width_range))
        return "dwelling_house", "dual_occupancy", False, None

    monkeypatch.setattr(ib, "_capacity_ceiling", fake_ceiling)
    return calls


def test_endpoint_sets_the_ceiling(offline):
    r = asyncio.run(ca.constraint_arithmetic_full(_req()))
    assert r.max_permitted_form == "dual_occupancy"
    assert offline[0]["lga"] == "CITY OF PARRAMATTA"  # current LGA, not the DCP slug
    assert not any("not checked" in g for g in r.gaps)


@pytest.mark.parametrize("missing,word", [({"lat": None}, "location"), ({"zone": None}, "zone"),
                                          ({"lga_name": None}, "LGA")])
def test_missing_input_says_not_checked(offline, missing, word):
    r = asyncio.run(ca.constraint_arithmetic_full(_req(**missing)))
    assert r is None or r.max_permitted_form is None
    if r is not None:
        assert any(g.startswith("Highest permitted housing form not checked") and word in g for g in r.gaps)
    assert offline == []


def test_lookup_failure_says_not_checked(offline, monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("arcgis")

    monkeypatch.setattr(ib, "_capacity_ceiling", boom)
    r = asyncio.run(ca.constraint_arithmetic_full(_req()))
    assert r.max_permitted_form is None
    assert "Highest permitted housing form not checked: the lookup failed." in r.gaps


def test_heritage_from_postgis_reaches_the_producer(offline, monkeypatch):
    monkeypatch.setattr(ib, "_fetch_heritage_postgis", lambda lat, lng, wkt: {"has_heritage": True})
    asyncio.run(ca.constraint_arithmetic_full(_req(heritage=False)))
    assert offline[0]["heritage"] is True


def test_width_range_passed_only_when_both_ends(offline):
    asyncio.run(ca.constraint_arithmetic_full(_req(width_min_m=13.3, width_max_m=22.4)))
    asyncio.run(ca.constraint_arithmetic_full(_req(width_min_m=13.3)))
    assert offline[0]["width"] == (13.3, 22.4) and offline[1]["width"] is None


def test_capacity_ceiling_composes_the_three_steps(monkeypatch):
    seen = {}
    monkeypatch.setattr(ib, "_eligibility_excluded_forms", lambda lat, lng: {"dual_occupancy"})

    def uplift(zone, lat, lng, area, w, heritage, results=None, lot_width_range=None):
        seen["uplift"] = (heritage, results, lot_width_range)
        return "manor_house", {"source_clause": "cl 1"}

    def forms(zone, lga, excluded_forms=None, uplift_form=None, return_source=False):
        seen["forms"] = (lga, excluded_forms, uplift_form)
        return "dwelling_house", "manor_house", True

    monkeypatch.setattr(ib, "_lmr_uplift_form", uplift)
    monkeypatch.setattr(ib, "_realistic_forms", forms)
    out = ib._capacity_ceiling("R2", "Parramatta", -33.7, 150.9, 600.0, True,
                               width_range=(12.0, 15.0), results=["r"])
    assert out == ("dwelling_house", "manor_house", True, {"source_clause": "cl 1"})
    assert seen["uplift"] == (True, ["r"], (12.0, 15.0))
    assert seen["forms"] == ("Parramatta", {"dual_occupancy"}, "manor_house")
