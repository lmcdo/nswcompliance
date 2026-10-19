"""Tests for scripts/page_integrity/checks_data.py: 3 real captures + synthetic edge cases."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.page_integrity import checks_data as cd
from scripts.page_integrity.load import Capture, load

FX = Path(__file__).parent / "fixtures" / "page_integrity"
WH, CW, MA = "winston_hills_6_berrigan", "cabramatta_west_24_yvonne", "mount_annan_3_egret"


@pytest.fixture(scope="module")
def caps():
    return {n: load(FX / n) for n in (WH, CW, MA)}


def facts(flags):
    return {f.fact for f in flags}


# ---- fixtures: C1
def test_c1_winston_red(caps):
    f = cd.same_fact_agrees(caps[WH])
    assert len(f) > 0 and {"front_setback", "side_setback"} <= facts(f)
    assert "rear_setback" not in facts(f)  # rear DCP row has no figure
    assert not (facts(f) & {"zone", "lot_area", "fsr", "height"})


@pytest.mark.parametrize("n", [CW, MA])
def test_c1_green(caps, n):
    assert cd.same_fact_agrees(caps[n]) == []


# ---- fixtures: C3
def test_c3_winston_red(caps):
    assert facts(cd.honest_absence(caps[WH])) == {"setbacks_absent"}


@pytest.mark.parametrize("n", [CW, MA])
def test_c3_green(caps, n):
    assert cd.honest_absence(caps[n]) == []


# ---- fixtures: C4
def test_c4_winston_red(caps):
    f = cd.row_fits_lot(caps[WH])
    dt = [x for x in f if x.fact == "row_dev_type"]
    assert len(dt) == 2 and all("p.92" in x.detail for x in dt)
    assert len([x for x in f if x.fact == "corner_lot"]) == 1


def test_c4_cabramatta_red(caps):
    f = cd.row_fits_lot(caps[CW])
    assert facts(f) == {"side_setback_conditional"}
    assert "4.0 m" in f[0].detail or "side setback 4.0 m" in f[0].detail
    assert "gives 0.9 m" in f[0].detail


def test_c4_mount_annan_red(caps):
    f = cd.row_fits_lot(caps[MA])
    assert facts(f) == {"rear_setback_conditional"}
    assert "rear setback 6.0 m" in f[0].detail and "gives 4.0 m" in f[0].detail


# ---- mutation: a no-op check would fail the red-fixture assertions above
@pytest.mark.parametrize("fn,n,fact", [
    ("same_fact_agrees", WH, "front_setback"),
    ("honest_absence", WH, "setbacks_absent"),
    ("row_fits_lot", CW, "side_setback_conditional"),
    ("row_fits_lot", MA, "rear_setback_conditional"),
    ("row_fits_lot", WH, "corner_lot"),
    ("row_fits_lot", WH, "row_dev_type"),
])
def test_mutation_noop_is_detected(caps, monkeypatch, fn, n, fact):
    flags = getattr(cd, fn)(caps[n])
    assert len(flags) > 0 and fact in facts(flags)
    monkeypatch.setattr(cd, fn, lambda cap: [])
    assert fact not in facts(getattr(cd, fn)(caps[n]))  # i.e. the red assertion above would fail


def test_facts_checked_real(caps):
    fc = cd.facts_checked(caps[WH])
    assert fc["setback_front"] and fc["lot_area"] and fc["zone"] and fc["council_key"]


# ---- synthetic
def mk(*calls):
    out = []
    for path, j, q, b in calls:
        out.append({"method": "GET", "path": path, "query": q or {}, "request_body": b, "status": 200,
                    "json": {"success": True, "data": j}})
    return Capture(folder=Path("."), meta={}, calls=out)


def sc(rows, dev="dwelling_house", council="x"):
    return (cd.P_SC, {"categories": [{"category": "Setbacks", "controls": rows}]},
            {"council": council, "dev_type": dev}, None)


def row(t, v, cond=None, page=1, **kw):
    return {"control_type": t, "value_min": v, "condition": cond, "pdf_page": page, **kw}


ALL = (cd.same_fact_agrees, cd.honest_absence, cd.row_fits_lot)


@pytest.mark.parametrize("fn", ALL)
def test_empty_capture_no_flag_no_crash(fn):
    assert fn(mk()) == []


def test_empty_capture_facts_checked_all_false():
    assert not any(cd.facts_checked(mk()).values())


def test_missing_ca_route_is_not_a_flag_nor_a_pass():
    cap = mk(sc([row("front_setback", 6)]))
    assert cd.same_fact_agrees(cap) == []
    assert cd.facts_checked(cap)["setback_front"] is False


def test_none_values_and_junk_json():
    cap = mk((cd.P_CA, {"setback_front_m": None}, None, {"lot_area_m2": None, "zone": None}),
             (cd.P_SC, {"categories": [{"controls": [row("front_setback", None), "junk"]}]}, {}, None),
             (cd.P_PROP, {"constraints": None, "lotDimensions": None, "cornerLot": None}, None, None))
    for fn in ALL:
        assert fn(cap) == []


def test_string_numbers_agree():
    cap = mk((cd.P_CA, {"setback_front_m": "6", "setback_side_m": None, "setback_rear_m": None}, None,
              {"lot_area_m2": "688.05"}),
             sc([row("front_setback", "6.0")]),
             (cd.P_CAP, {}, None, {"lotSize": 688.05}))
    assert cd.same_fact_agrees(cap) == []


def test_lot_area_mismatch_and_tolerance():
    def base(a):
        return mk((cd.P_PROP, {"lotDimensions": {"area": 600}}, None, None),
                  (cd.P_CAP, {}, None, {"lotSize": a}))
    assert cd.same_fact_agrees(base(600.005)) == []
    assert facts(cd.same_fact_agrees(base(650))) == {"lot_area"}


def test_zone_leading_token():
    cap = mk((cd.P_PROP, {"constraints": {"zone": "R2: Low Density"}}, None, None),
             (cd.P_CA, {}, None, {"zone": "R2"}), (cd.P_PROV, {}, {"zone": "R3"}, None))  # noqa: zone-codes (deliberate mismatch fixture)
    assert facts(cd.same_fact_agrees(cap)) == {"zone"}
    cap2 = mk((cd.P_PROP, {"constraints": {"zone": "R2: Low Density"}}, None, None),
              (cd.P_CA, {}, None, {"zone": "r2"}))
    assert cd.same_fact_agrees(cap2) == []


def test_fsr_height_mismatch():
    cap = mk((cd.P_PROP, {"constraints": {"maxFsr": 0.5, "maxHeight": 9}}, None, None),
             (cd.P_CA, {}, None, {"maxFsr": None, "maxHeight": 10}))
    assert facts(cd.same_fact_agrees(cap)) == {"fsr", "height"}


def test_ca_value_not_in_dcp():
    cap = mk((cd.P_CA, {"setback_front_m": 5, "setback_side_m": None, "setback_rear_m": None}, None, None),
             sc([row("front_setback", 6)]))
    assert facts(cd.same_fact_agrees(cap)) == {"front_setback"}


def test_council_key_mismatch_normalised():
    ok = mk((cd.P_CA, {}, None, {"formerCouncil": "city_of_parramatta", "lga": "CITY OF PARRAMATTA"}),
            (cd.P_SC, {"categories": []}, {"council": "City of Parramatta"}, None))
    assert cd.honest_absence(ok) == []
    bad = mk((cd.P_CA, {}, None, {"formerCouncil": "parramatta"}),
             (cd.P_PROV, {}, {"former_council": "city_of_parramatta"}, None))
    f = cd.honest_absence(bad)
    assert facts(f) == {"council_key"} and "parramatta" in f[0].detail


def test_c3_all_none_setbacks_with_rows():
    cap = mk((cd.P_CA, {"setback_front_m": None, "setback_side_m": None, "setback_rear_m": None, "gaps": []},
              None, None),
             sc([row("side_setback", 0.9)]))
    assert facts(cd.honest_absence(cap)) == {"setbacks_absent"}


def test_c4_dev_type_matching_own_type_not_flagged():
    assert cd.row_fits_lot(mk(sc([row("front_setback", 3, "terraces only")], dev="terrace"))) == []
    assert facts(cd.row_fits_lot(mk(sc([row("front_setback", 3, "dual occupancy")])))) == {"row_dev_type"}


def test_c4b_no_flag_when_chosen_has_unconditional_row():
    cap = mk((cd.P_CA, {"setback_rear_m": 6, "setback_front_m": None, "setback_side_m": None}, None, None),
             sc([row("rear_setback", 6), row("rear_setback", 4, "Single storey")]))
    assert cd.row_fits_lot(cap) == []


def test_c4c_applies_only_if_and_unknown_corner():
    def prop(v):
        return (cd.P_PROP, {"cornerLot": v}, None, None)
    ok = sc([row("secondary_street_setback", 3, "corner lot; applies only if corner")])
    assert cd.row_fits_lot(mk(prop({"isCornerLot": False}), ok)) == []
    plain = sc([row("secondary_street_setback", 3, "corner lot")])
    assert cd.row_fits_lot(mk(prop(None), plain)) == []
    assert facts(cd.row_fits_lot(mk(prop({"isCornerLot": False}), plain))) == {"corner_lot"}


# ---- listed setbacks (A3): a side whose rows disagree is LISTED, not picked
def _listed(front_opts, side=0.9):
    return {"setback_front_m": None, "setback_side_m": side, "setback_rear_m": None,
            "setback_front_options": [{"value_m": v} for v in front_opts],
            "setback_rear_options": [], "setback_side_options": [], "gaps": []}


def test_c1_listed_side_matching_dcp_tab_is_green():
    cap = mk((cd.P_CA, _listed([6.0, 10.0]), None, None),
             sc([row("front_setback", 6), row("front_setback", 10, "state road"), row("side_setback", 0.9)]))
    assert "front_setback" not in facts(cd.same_fact_agrees(cap))


def test_c1_listed_side_missing_a_dcp_value_is_red():
    cap = mk((cd.P_CA, _listed([6.0]), None, None),
             sc([row("front_setback", 6), row("front_setback", 10, "state road"), row("side_setback", 0.9)]))
    assert "front_setback" in facts(cd.same_fact_agrees(cap))


def test_c1_listed_side_inventing_a_value_is_red():
    cap = mk((cd.P_CA, _listed([6.0, 10.0, 12.0]), None, None),
             sc([row("front_setback", 6), row("front_setback", 10, "state road"), row("side_setback", 0.9)]))
    assert "front_setback" in facts(cd.same_fact_agrees(cap))


def test_c3_all_sides_listed_is_not_absent():
    ca = _listed([6.0, 10.0], side=None)
    ca["setback_side_options"] = [{"value_m": 0.9}, {"value_m": 1.5}]
    cap = mk((cd.P_CA, ca, None, None),
             sc([row("front_setback", 6), row("front_setback", 10), row("side_setback", 0.9), row("side_setback", 1.5)]))
    assert "setbacks_absent" not in facts(cd.honest_absence(cap))


# ---- corner rows: marked on the page = shown honestly; failed road check = not measured
def _corner_cap(rendered_dcp="", error=None):
    cl = {"isCornerLot": False, "confidence": 0 if error else 1}
    if error:
        cl["error"] = error
    cap = mk((cd.P_PROP, {"cornerLot": cl}, None, None),
             sc([row("secondary_street_setback", 3.0, "secondary street or corner allotment")]))
    cap.rendered = {"dcp": rendered_dcp}
    return cap


def test_c4_corner_row_unmarked_is_red():
    assert "corner_lot" in facts(cd.row_fits_lot(_corner_cap()))


def test_c4_corner_row_marked_on_page_is_green():
    cap = _corner_cap("Secondary street setback 3.0 m\nApplies only to corner lots — this lot is not on a corner.")
    assert "corner_lot" not in facts(cd.row_fits_lot(cap))


def test_c4_failed_road_check_is_not_a_measured_no():
    cap = _corner_cap(error="Failed to query road data: This operation was aborted")
    assert "corner_lot" not in facts(cd.row_fits_lot(cap))


def test_c4_row_naming_a_type_it_excludes_is_not_for_that_type():
    cap = mk(sc([row("rear_setback", 6.0, "single street frontage; excludes outbuildings and secondary dwellings. "
                                          "NOT yet stored: secondary dwelling 3.0m (C11)")]))
    assert "row_dev_type" not in facts(cd.row_fits_lot(cap))


def test_c4_row_for_another_type_still_red():
    cap = mk(sc([row("deep_soil_min", 30.0, "terraces; 50% at rear")]))
    assert "row_dev_type" in facts(cd.row_fits_lot(cap))
