"""Rule (f) of s164(1): the Hawkesbury-Nepean Probable Maximum Flood decided from our copy of the 2024 flood study's own extent (services/lmr_area_decision.py)."""
import pytest

from services import lmr_area_decision as d
from tests.test_lmr_area_decision import CLEAR, FACTS, HIT, ans, coastal, lot


# ---- (f) Hawkesbury-Nepean: the flood study's own extent --------------------------------------------------
def _pmf(**over):
    base = {"inside": False, "edge_m": 500.0, "nearest_m": 500.0, "within_box": True, "used_outline": True, "as_of": "2026-11-22"}
    base.update(over)
    return base


def _f_rule(m):
    rs = [r for r in d._lmr_rules(m, FACTS) if r["rule"] == "pmf_hawkesbury_nepean"]
    assert len(rs) <= 1
    return rs[0] if rs else None


def _fm(catchment=CLEAR, pmf=None, **extra):
    m = lot(hn_catchment=catchment, **coastal(), **extra)
    if pmf is not None:
        m["flood_study"] = {"pmf": pmf}
    return m


def test_f_flood_study_inside_is_a_warning_and_wins_over_a_clear_catchment():
    r = _f_rule(_fm(CLEAR, _pmf(inside=True, edge_m=300.0, nearest_m=0.0)))
    assert r["outcome"] == "warn" and r["figures"]["flood_state"] == "inside"
    assert "Probable Maximum Flood" in r["detail"] and "2024" in r["detail"] and "not proven to equal that figure" in r["detail"]
    assert "excluded" not in r["detail"] and "excludes" not in r["outcome"]
    assert r["figures"]["margin_m"] == d.FLOOD_EDGE_M and r["figures"]["copy_as_of"] == "2026-11-22" and r["figures"]["inside"] is True
    assert r["clause"] == "s164(1)(f)"


def test_f_flood_study_inside_keeps_the_answer_yes_with_one_warning():
    r = ans(_fm(CLEAR, _pmf(inside=True, edge_m=300.0, nearest_m=0.0)))
    assert r["lmr"]["answer"] == "yes" and [w["clause"] for w in r["warnings"]] == ["s164(1)(f)"]


@pytest.mark.parametrize("edge,state,outcome", [
    (60.0, "edge", "warn"), (0.0, "edge", "warn"), (d.FLOOD_EDGE_M, "edge", "warn"),
    (d.FLOOD_EDGE_M + 0.1, "outside", "clear"), (5000.0, "outside", "clear"),
])
def test_f_flood_study_margin_boundary_is_inclusive(edge, state, outcome):
    r = _f_rule(_fm(CLEAR, _pmf(inside=False, edge_m=edge, nearest_m=edge)))
    assert r["outcome"] == outcome and r["figures"]["flood_state"] == state and r["figures"]["edge_m"] == edge
    if state == "edge":
        assert f"{edge:g} m from the edge" in r["detail"] and "cannot say which side" in r["detail"]
    else:
        assert f"the nearest flood area is {d._distance_words(edge)} away" in r["detail"]


def test_f_flood_study_margin_is_100_metres():
    assert d.FLOOD_EDGE_M == 100.0


def test_f_flood_study_no_flood_area_within_the_search_distance_is_clear_and_says_so():
    r = _f_rule(_fm(CLEAR, _pmf(inside=False, edge_m=None, nearest_m=None)))
    assert r["outcome"] == "clear" and "no flood area is within the search distance" in r["detail"] and r["figures"]["flood_state"] == "outside"


def test_f_flood_study_outside_the_box_and_catchment_clear_keeps_the_older_rule():
    r = _f_rule(_fm(CLEAR, _pmf(within_box=False, inside=False, edge_m=40.0)))
    assert r["outcome"] == "clear" and "our inference" in r["detail"] and "flood_state" not in r["figures"]


def test_f_flood_study_outside_the_box_and_catchment_hit_keeps_the_older_warning():
    r = _f_rule(_fm(HIT, _pmf(within_box=False, inside=False)))
    assert r["outcome"] == "warn" and "flood extent was not checked" in r["detail"] and r["figures"] == {}


def test_f_flood_study_extent_wins_over_the_catchment_both_ways():
    inside_but_catchment_clear = _f_rule(_fm(CLEAR, _pmf(inside=True, nearest_m=0.0)))
    assert inside_but_catchment_clear["outcome"] == "warn"
    outside_but_catchment_hit = _f_rule(_fm(HIT, _pmf(inside=False, edge_m=900.0, nearest_m=900.0)))
    assert outside_but_catchment_hit["outcome"] == "clear" and "flood extent was not checked" not in outside_but_catchment_hit["detail"]


def test_f_flood_study_decides_even_when_the_catchment_map_did_not_answer():
    assert _f_rule(_fm(None, _pmf(inside=False, edge_m=900.0, nearest_m=900.0)))["outcome"] == "clear"


@pytest.mark.parametrize("fs", [None, {}, {"aep500": _pmf(inside=True)}, {"pmf": None}, {"pmf": "inside"}, {"pmf": ["x"]}, {"pmf": 3}, "pmf", ["pmf"]])
@pytest.mark.parametrize("catchment,outcome,text", [(CLEAR, "clear", "our inference"), (HIT, "warn", "flood extent was not checked"), (None, "unknown", "did not answer")])
def test_f_no_usable_flood_study_gives_exactly_the_older_behaviour(fs, catchment, outcome, text):
    m = _fm(catchment)
    if fs is not None:
        m["flood_study"] = fs
    r = _f_rule(m)
    assert r["outcome"] == outcome and text in r["detail"] and r["figures"] == {}


def test_f_the_rule_is_absent_without_a_catchment_map_or_a_flood_extent():
    m = lot(**coastal())
    assert _f_rule(m) is None
    m["flood_study"] = {"pmf": _pmf(within_box=False)}
    assert _f_rule(m) is None


def test_f_decide_reports_flood_study_and_pipeline_in_measured_and_adds_the_copy_note():
    fs = {"pmf": _pmf(inside=False, edge_m=900.0, nearest_m=900.0)}
    pl = {"hit": False, "names": [], "nearest_m": 4321}
    r = ans(_fm(CLEAR, None, flood_study=fs, pipeline=pl))
    assert r["measured"]["flood_study"] == fs and r["measured"]["pipeline"] == pl
    note = [n for n in r["notes"] if "Hawkesbury-Nepean River Flood Study" in n]
    assert len(note) == 1 and "2026-11-22" in note[0] and "never as clear" in note[0] and "May 2024" in note[0]


def test_f_decide_has_no_flood_note_or_measured_entry_when_the_study_did_not_decide():
    r = ans(_fm(CLEAR))
    assert "flood_study" not in r["measured"] and "pipeline" not in r["measured"]
    assert not [n for n in r["notes"] if "Hawkesbury-Nepean River Flood Study" in n]
    outside = ans(_fm(CLEAR, None, flood_study={"pmf": _pmf(within_box=False)}))
    assert not [n for n in outside["notes"] if "Hawkesbury-Nepean River Flood Study" in n] and "flood_study" in outside["measured"]


@pytest.mark.parametrize("metres,words", [(0, "0 m"), (60, "60 m"), (99.6, "99.6 m"), (100.4, "100.4 m"), (999.4, "999.4 m"), (1000, "1.0 km"), (9855.7, "9.9 km"), (23916, "23.9 km")])
def test_distance_words_use_metres_under_a_kilometre_and_kilometres_above(metres, words):
    assert d._distance_words(metres) == words


def test_the_flood_rule_alone_passes_its_figures_on_in_the_public_rule_list():
    """The evidence page needs the distances; every other rule keeps the shape it always had (no 'figures' key)."""
    out = d.decide(_fm(CLEAR, _pmf(inside=False, edge_m=9855.7, nearest_m=9855.7)))
    rules = out["lmr"]["rules"]
    flood = [r for r in rules if r["rule"] == "pmf_hawkesbury_nepean"]
    assert len(flood) == 1 and flood[0]["figures"]["nearest_m"] == 9855.7 and flood[0]["figures"]["flood_state"] == "outside"
    assert all("figures" not in r for r in rules if r["rule"] != "pmf_hawkesbury_nepean")
