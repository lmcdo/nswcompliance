"""Planted-fault tests: each check C1-C6 is started GREEN on a real capture, ONE fault is planted,
and the check must go RED with the expected fact. Each fails if the check were `lambda cap: []`.
C6 planted faults live in test_page_integrity_checks_text.py (test_c6_fsr_mutation,
test_c6_footprint_text_over_100) and are not duplicated here."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.page_integrity import checks_data as cd
from scripts.page_integrity import checks_text as ct
from scripts.page_integrity.load import load

FX = Path(__file__).parent / "fixtures" / "page_integrity"
CW, MA = "cabramatta_west_24_yvonne", "mount_annan_3_egret"


def facts(flags):
    return {f.fact for f in flags}


def _cats(c):
    return c.data(cd.P_SC)["categories"]


def _ca(c):
    return c.last(cd.P_CA)["json"]["data"]


def _drop_rows(c, pred):
    for cat in _cats(c):
        cat["controls"] = [x for x in cat["controls"] if not pred(x)]


def _plant_row(c, **row):
    _cats(c)[0]["controls"].append({"control_type": "front_setback", "value_min": 5.0, **row})


# ---- C1
def test_c1_setback_planted():
    c = load(FX / CW)
    assert cd.same_fact_agrees(c) == []
    for x in cd._controls(c):
        if x["control_type"] == "front_setback":
            x["value_min"] = 7.7  # DCP tab no longer holds the 4.5 the arithmetic used
    assert "front_setback" in facts(cd.same_fact_agrees(c))


def test_c1_lot_area_planted():
    c = load(FX / MA)
    assert cd.same_fact_agrees(c) == []
    c.last(cd.P_CA)["request_body"]["lot_area_m2"] += 50  # one route only
    assert "lot_area" in facts(cd.same_fact_agrees(c))


# ---- C2
def test_c2_red_after_green():
    c = load(FX / CW)
    _ca(c)["max_permitted_form"] = "dual_occupancy"
    assert ct.check_engines_agree(c) == []
    _ca(c)["max_permitted_form"] = None  # yield box loses its multi-form answer
    assert facts(ct.check_engines_agree(c)) == {"engines-agree"}


def test_c2_less_dense_form_while_denser_permitted():
    c = load(FX / CW)
    _ca(c)["max_permitted_form"] = "dual_occupancy"
    assert ct.check_engines_agree(c) == []
    _ca(c)["max_permitted_form"] = "dwelling_house"
    assert facts(ct.check_engines_agree(c)) == {"engines-agree"}


# ---- C3
def test_c3_setbacks_blanked():
    c = load(FX / CW)
    assert cd.honest_absence(c) == []
    for k in cd.SETBACKS:
        _ca(c)[f"setback_{k}_m"] = None
    assert facts(cd.honest_absence(c)) == {"setbacks_absent"}


def test_c3_gap_text_without_values_blanked():
    c = load(FX / MA)
    assert cd.honest_absence(c) == []
    for k in cd.SETBACKS:
        _ca(c)[f"setback_{k}_m"] = None
    _ca(c)["gaps"] = ["No DCP setback controls found"]
    assert facts(cd.honest_absence(c)) == {"setbacks_absent"}


# ---- C4 (real fault removed first, then ONE fault planted)
def _c4_green_cw():
    c = load(FX / CW)
    assert facts(cd.row_fits_lot(c)) == {"side_setback_conditional"}
    _drop_rows(c, lambda x: x["control_type"] == "side_setback" and "Upper floor" in str(x.get("condition")))
    assert cd.row_fits_lot(c) == []
    return c


def test_c4_corner_lot_row_on_non_corner_lot():
    c = _c4_green_cw()
    assert cd._prop(c)["cornerLot"]["isCornerLot"] is False
    _plant_row(c, condition="Corner lots: secondary street frontage 3 m")
    assert facts(cd.row_fits_lot(c)) == {"corner_lot"}


def test_c4_row_for_other_dwelling_type():
    c = _c4_green_cw()
    _plant_row(c, condition="Terrace housing: 2 m")
    assert facts(cd.row_fits_lot(c)) == {"row_dev_type"}


# ---- C5
def _strip_asofright(c):
    for k, t in c.rendered.items():
        c.rendered[k] = "\n".join(ln for ln in t.splitlines() if not ct._ASOFRIGHT.search(ln))


def test_c5_as_of_right_planted():
    c = load(FX / CW)
    _strip_asofright(c)
    assert {"as-of-right", "contradiction"}.isdisjoint(facts(ct.check_words_on_page(c)))
    c.rendered["planning"] += "\nA dual occupancy is as-of-right on this lot.\n"
    assert "as-of-right" in facts(ct.check_words_on_page(c))


# ---- C6: see test_page_integrity_checks_text.py::test_c6_fsr_mutation / test_c6_footprint_text_over_100


# ---- emptied source call: unexamined is False, never a pass, never a false flag
def _remove_ca(c):
    c.calls[:] = [x for x in c.calls if x["path"] != cd.P_CA]


def _assert_unexamined(c):
    assert cd.same_fact_agrees(c) == [] and cd.honest_absence(c) == []
    fc = cd.facts_checked(c)
    assert not any(fc[f"setback_{k}"] for k in cd.SETBACKS) and fc["absence_setbacks"] is False
    assert ct.check_engines_agree(c) == [] and ct.facts_checked(c)["engines-agree"] is False


@pytest.mark.parametrize("n", [CW, MA])
def test_removed_constraint_arithmetic_is_not_a_pass(n):
    c = load(FX / n)
    assert cd.same_fact_agrees(c) == [] and all(cd.facts_checked(c)[f"setback_{k}"] for k in cd.SETBACKS)
    _remove_ca(c)
    _assert_unexamined(c)


@pytest.mark.parametrize("n", [CW, MA])
def test_emptied_constraint_arithmetic_json_is_not_a_pass(n):
    c = load(FX / n)
    c.last(cd.P_CA)["json"] = {}
    _assert_unexamined(c)
