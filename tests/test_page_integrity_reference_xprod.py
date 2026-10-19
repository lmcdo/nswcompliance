"""Tests for R (page vs hand-checked expected.json) and C7 (page vs Site Report). Fixtures only."""
from pathlib import Path

import pytest

from scripts.page_integrity import checks_reference as cr
from scripts.page_integrity import checks_xprod as cx
from scripts.page_integrity.checks_data import P_CA, P_PROP
from scripts.page_integrity.load import load

FX = Path(__file__).parent / "fixtures" / "page_integrity"
WH, CW, MA, CO = ("winston_hills_6_berrigan", "cabramatta_west_24_yvonne", "mount_annan_3_egret",
                  "concord_14_gale")


def facts(flags):
    return {f.fact for f in flags}


def fixed_page(n):
    """The stored captures are of the page BEFORE the flood fix, when floodProne was the
    constant False. These three councils publish no flood planning map, so the fixed page
    sends null; apply that so the other reference facts can be tested on their own."""
    c = load(FX / n)
    c.data(P_PROP)["constraints"]["floodProne"] = None
    return c


@pytest.mark.parametrize("n", [WH, MA, CO])
def test_r_catches_the_old_constant_flood_no(n):
    """Before the fix the page said 'flood: No' on councils with no flood map."""
    assert "reference:flood_lep_map" in facts(cr.check_reference(load(FX / n)))


# ---- R: real captures
def test_r_concord_strata_is_caught():
    assert facts(cr.check_reference(fixed_page(CO))) == {"reference:strata"}


@pytest.mark.parametrize("n", [WH, MA])
def test_r_green(n):
    assert cr.check_reference(fixed_page(n)) == []


def test_r_no_expected_file_is_not_checked():
    c = load(FX / CW)
    assert cr.check_reference(c) == [] and cr.facts_checked(c) == {}


# ---- R: planted faults on a green capture
def test_r_planted_zone():
    c = fixed_page(MA)
    c.data(P_PROP)["constraints"]["zone"] = "R3"
    assert facts(cr.check_reference(c)) == {"reference:zone"}


def test_r_planted_setback_not_in_dcp():
    c = fixed_page(MA)
    c.data(P_CA)["setback_rear_m"] = 5.0  # Camden gives 4 m or 6 m, never 5
    assert facts(cr.check_reference(c)) == {"reference:setback_rear_m"}


def test_r_planted_lot_area_beyond_tolerance():
    c = fixed_page(MA)
    c.data(P_PROP)["lotDimensions"]["area"] = 700.0
    assert facts(cr.check_reference(c)) == {"reference:lot_area_m2"}


def test_r_missing_route_is_not_a_pass():
    c = load(FX / MA)
    c.calls = [x for x in c.calls if x["path"] not in (P_PROP, P_CA)]
    assert cr.check_reference(c) == []
    assert not any(cr.facts_checked(c).values())


# ---- C7: real captures
def test_c7_concord():
    assert facts(cx.check_cross_product(load(FX / CO))) == {"lot_area", "homes", "corner"}


def test_c7_mount_annan_only_lot_area():
    assert facts(cx.check_cross_product(load(FX / MA))) == {"lot_area"}


# ---- C7: planted faults
def test_c7_green_then_planted(monkeypatch):
    c = load(FX / MA)
    sec = cx.site_report(c)
    sec["planning_controls"]["lot_dimensions"]["value"]["area_m2"] = c.data(P_PROP)["lotDimensions"]["area"]
    monkeypatch.setattr(cx, "site_report", lambda cap: sec)
    assert cx.check_cross_product(c) == []
    c.data(P_PROP)["constraints"]["maxHeight"] = 12
    assert facts(cx.check_cross_product(c)) == {"height"}


def test_c7_no_site_report_is_not_a_pass(monkeypatch):
    c = load(FX / MA)
    monkeypatch.setattr(cx, "site_report", lambda cap: None)
    assert cx.check_cross_product(c) == [] and cx.facts_checked(c) == {"site_report": False}


def test_c7_unfinished_stream_is_not_an_answer(tmp_path):
    import gzip
    import json
    import shutil
    shutil.copytree(FX / MA, tmp_path / MA)
    p = tmp_path / MA / "site_report.jsonl.gz"
    with gzip.open(p, "rt", encoding="utf-8") as f:
        evs = [json.loads(x) for x in f][:-1]  # drop 'complete'
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.writelines(json.dumps(e) + "\n" for e in evs)
    c = load(tmp_path / MA)
    assert cx.site_report(c) is None and cx.check_cross_product(c) == []


@pytest.mark.parametrize("a,b,same", [("R2: Low Density Residential", "R2", True), ("9", 9, True),
                                      ("0.5:1", 0.5, True), (False, None, None), (True, False, False)])
def test_c7_norm(a, b, same):
    na, nb = cx._norm(a), cx._norm(b)
    if same is None:
        assert nb is None
    else:
        assert (na == nb) is same
