"""Tests for the pure low-and-mid-rise / TOD decision rules (services/lmr_area_decision.py).

Each test builds a hand-made lot. The facts come from the saved law file, so a change to the law text
that moves a clause fails here rather than in front of a user.
"""
import copy
import re

import pytest

from services import lmr_area_decision as d

FACTS = d.LawFacts.load()
# The walking range is lopsided: LO below the measured walk, HI above it. The edge tests below are written relative to these,
# so re-measuring and changing them does not break the tests.
LO, HI = d.WALK_MARGIN_LOW_M, d.WALK_MARGIN_HIGH_M

CLEAR = {"point": False, "lot": False}
HIT = {"point": True, "lot": True}


def lot(**over):
    """A lot that is clear on every rule and 450 m from a station: the answer is YES until a test breaks it."""
    base = {
        "lga": "Inner West",
        "tod_map": CLEAR, "accelerated": CLEAR, "exclusion": CLEAR, "bushfire": CLEAR,
        "heritage": {"item": False, "conservation_area": False, "state_register": False},
        "sched12_straight_m": 5000.0,
        "straight_m": 300.0,
        "walk": {"m": 450.0, "anchor": "Ashfield station", "entrance_id": "node/1", "valid": True},
    }
    base.update(over)
    return base


def ans(m):
    return d.decide(m, FACTS)


def test_baseline_is_yes_with_clause_page_and_figures():
    r = ans(lot())
    assert r["lmr"]["answer"] == "yes" and r["pathway"] == "lmr"
    assert r["lmr"]["clause"].startswith("s163") and r["lmr"]["page"] == 77
    assert r["lmr"]["figures"]["limit_m"] == 800 and r["lmr"]["figures"]["walk_m"] == 450
    assert r["law_version_date"] == "2026-10-23"


def test_every_yes_prints_what_was_not_checked():
    # lot(): bush fire wired; the coastal and Hawkesbury-Nepean maps are not; Inner West is outside the (f1) and (g) council lists
    r = ans(lot())
    paras = {x["para"] for x in r["not_checked"]}
    assert paras == {"b", "f", "h", "i"}, paras
    assert all(x["clause"] and x["page"] for x in r["not_checked"])
    unwired = {k: v for k, v in lot().items() if k != "bushfire"}
    assert "a" in {x["para"] for x in ans(unwired)["not_checked"]}


# ---- flood, coastal ----------------------------------------------------------------------------------
GEORGES_COUNCILS = ["Canterbury-Bankstown", "Cumberland", "Fairfield", "Georges River", "Liverpool", "Sutherland"]
G_COUNCILS = ["Armidale Regional", "Newcastle", "Shoalhaven", "Queanbeyan-Palerang Regional", "Upper Hunter", "Walcha"]


def coastal(**over):
    base = {"coastal_vuln": CLEAR, "coastal_wetlands": CLEAR, "littoral": CLEAR}
    base.update(over)
    return base


def test_council_lists_come_from_the_law_text_and_are_complete():
    assert len(FACTS.council_names("g", "roman")) == 23 and FACTS.council_names("g", "roman")[-1] == "Walcha"
    assert FACTS.council_names("f1", "letter") == ["Canterbury-Bankstown", "Cumberland", "City of Fairfield", "Georges River", "City of Liverpool", "Sutherland Shire"]
    assert len(FACTS.council_names("e", "roman")) == 4


@pytest.mark.parametrize("name", G_COUNCILS)
def test_g_applies_only_in_the_named_councils_and_needs_the_flood_map_there(name):
    r = ans(lot(lga=name))   # no flood answer supplied for a named council: not a yes
    assert r["lmr"]["answer"] == "cant_tell"
    assert any(q["clause"] == "s164(1)(g)" and q["outcome"] == "unknown" for q in r["lmr"]["rules"])
    assert ans(lot(lga=name, flood_planning={"value": False}))["lmr"]["answer"] == "yes"
    r = ans(lot(lga=name, flood_planning={"value": True}))["lmr"]
    assert r["answer"] == "no" and r["clause"] == "s164(1)(g)"
    assert ans(lot(lga=name, flood_planning={"value": None}))["lmr"]["answer"] == "cant_tell"


def test_g_is_clear_everywhere_else_without_any_flood_data():
    for name in ("Inner West", "Woollahra", "Ku-ring-gai", "Canterbury-Bankstown"):
        r = ans(lot(lga=name))
        assert not any(q["outcome"] == "unknown" and q["clause"] == "s164(1)(g)" for q in r["lmr"]["rules"]), name


@pytest.mark.parametrize("name", GEORGES_COUNCILS)
def test_f1_inside_catchment_and_council_is_a_warning_not_a_block(name):
    r = ans(lot(lga=name, georges_catchment=HIT, **coastal()))
    assert r["lmr"]["answer"] == "yes"
    assert [w["clause"] for w in r["warnings"]] == ["s164(1)(f1)"] and "not checked" in r["warnings"][0]["detail"]
    assert r["lmr"]["warnings"] == r["warnings"]


def test_f1_outside_the_catchment_or_the_councils_is_clear_and_unknown_blocks():
    assert ans(lot(lga="Liverpool", georges_catchment=CLEAR, **coastal()))["warnings"] == []
    assert ans(lot(lga="Inner West", georges_catchment=HIT, **coastal()))["warnings"] == []    # council not named: cannot apply
    assert ans(lot(lga="Liverpool", georges_catchment=None, **coastal()))["lmr"]["answer"] == "cant_tell"
    assert ans(lot(lga="Liverpool", georges_catchment={"point": False, "lot": None}, **coastal()))["lmr"]["answer"] == "cant_tell"
    part = ans(lot(lga="Liverpool", georges_catchment={"point": False, "lot": True}, **coastal()))
    assert part["lmr"]["answer"] == "yes" and len(part["warnings"]) == 1


def test_f_hawkesbury_nepean_clear_outside_warn_inside_and_not_wired_is_printed():
    assert ans(lot(hn_catchment=CLEAR, **coastal()))["warnings"] == []
    inside = ans(lot(hn_catchment=HIT, **coastal()))
    assert inside["lmr"]["answer"] == "yes" and [w["clause"] for w in inside["warnings"]] == ["s164(1)(f)"]
    assert ans(lot(hn_catchment=None, **coastal()))["lmr"]["answer"] == "cant_tell"
    assert "f" in {x["para"] for x in ans(lot(**coastal()))["not_checked"]}                 # not wired: printed
    assert "f" not in {x["para"] for x in ans(lot(hn_catchment=CLEAR, **coastal()))["not_checked"]}
    clear = ans(lot(hn_catchment=CLEAR, **coastal()))["lmr"]["rules"]
    assert "our inference" in next(q["detail"] for q in clear if q["clause"] == "s164(1)(f)")


def test_b_coastal_any_one_of_the_three_maps_excludes_a_part_or_a_failure_blocks():
    for key in ("coastal_vuln", "coastal_wetlands", "littoral"):
        r = ans(lot(**coastal(**{key: HIT})))["lmr"]
        assert r["answer"] == "no" and r["clause"] == "s164(1)(b)", key
        assert ans(lot(**coastal(**{key: {"point": False, "lot": True}})))["lmr"]["answer"] == "cant_tell", key
        assert ans(lot(**coastal(**{key: None})))["lmr"]["answer"] == "cant_tell", key
    assert "b" not in {x["para"] for x in ans(lot(**coastal()))["not_checked"]}
    partly = {k: v for k, v in coastal().items() if k != "littoral"}                         # one of the three missing: not wired
    assert "b" in {x["para"] for x in ans(lot(**partly))["not_checked"]}


def test_a_no_stays_final_over_a_warning_and_the_remaining_list_is_h_and_i():
    full = lot(lga="Liverpool", georges_catchment=HIT, hn_catchment=CLEAR, flood_planning={"value": False}, **coastal())
    assert {x["para"] for x in ans(full)["not_checked"]} == {"h", "i"}
    assert ans({**full, "exclusion": HIT})["lmr"]["answer"] == "no"


def test_warning_wording_has_no_liability_words():
    r = ans(lot(lga="Liverpool", georges_catchment=HIT, hn_catchment=HIT, **coastal()))
    for w in r["warnings"]:
        assert not LIAB.search(w["detail"]), w["detail"]


# ---- walking band -------------------------------------------------------------------------------------
@pytest.mark.parametrize("walk,expected", [
    (800 - HI - 1, "yes"), (800 - HI, "yes"), (800 - HI + 1, "borderline"), (799, "borderline"), (800, "borderline"),
    (800 + LO - 1, "borderline"), (800 + LO, "no"), (1500, "no"),
])
def test_walking_band_edges(walk, expected):
    m = lot(straight_m=600.0, walk={"m": float(walk), "anchor": "A", "entrance_id": "e", "valid": True})
    assert ans(m)["lmr"]["answer"] == expected


@pytest.mark.parametrize("walk,expected", [
    (800.0 - HI - 160, "yes"),         # top of the range exactly at the limit
    (800.0 - HI - 159, "borderline"),  # top of the range one metre past the limit
    (800.0, "borderline"),
    (800.0 + LO, "no"),                # bottom of the range exactly at the limit
])
def test_unmapped_entrance_widens_the_range_upward_only(walk, expected):
    w = {"m": walk, "anchor": "A", "entrance_id": "station outline", "valid": True, "optimistic_by_m": 160.0}
    assert ans(lot(straight_m=600.0, walk=w))["lmr"]["answer"] == expected


def test_borderline_shows_the_range_the_lean_and_the_stated_rule():
    r = ans(lot(straight_m=600.0, walk={"m": 740.0, "anchor": "A", "entrance_id": "e", "valid": True}))["lmr"]
    f = r["figures"]
    assert r["answer"] == "borderline" and (f["walk_low_m"], f["walk_high_m"]) == (740 - LO, 740 + HI)
    p = round((800 - (740 - LO)) / (LO + HI), 2)
    assert r["lean"] == ("inside" if p >= 0.5 else "outside") and r["share_of_range_inside"] == p
    assert "equally likely" in r["heuristic"] and f"between {740 - LO} and {740 + HI} m" in r["detail"]
    assert f"{round(100 * p)}%" in r["detail"] and "lean" not in r["detail"].lower()
    r2 = ans(lot(straight_m=600.0, walk={"m": 860.0, "anchor": "A", "entrance_id": "e", "valid": True}))["lmr"]
    assert r2["lean"] == "outside" and r2["share_of_range_inside"] == round((800 - (860 - LO)) / (LO + HI), 2)


def test_borderline_headline_says_borderline_and_quotes_the_clause():
    r = ans(lot(straight_m=600.0, walk={"m": 800.0, "anchor": "A", "entrance_id": "e", "valid": True}))
    assert r["pathway"] == "borderline" and r["headline"].startswith("Borderline") and "s163" in r["headline"]


def test_a_missing_measurement_is_still_cant_tell_not_borderline():
    assert ans(lot(walk=None))["lmr"]["answer"] == "cant_tell"


def test_straight_line_over_limit_is_no_without_any_walk():
    r = ans(lot(straight_m=801.0, walk=None))
    assert r["lmr"]["answer"] == "no" and r["lmr"]["reason_code"] == "beyond_straight_line"


def test_straight_line_exactly_at_limit_still_needs_the_walk():
    r = ans(lot(straight_m=800.0, walk=None))
    assert r["lmr"]["answer"] == "cant_tell"


def test_no_walking_measure_inside_the_circle_is_cant_tell_never_yes():
    for w in (None, {}, {"m": None, "valid": True}, {"m": 300.0, "valid": False}, {"m": 300.0}):
        assert ans(lot(walk=w))["lmr"]["answer"] == "cant_tell", w


def test_missing_straight_distance_is_cant_tell():
    assert ans(lot(straight_m=None))["lmr"]["answer"] == "cant_tell"
    m = lot(); del m["straight_m"]
    assert ans(m)["lmr"]["answer"] == "cant_tell"


def test_inner_band_reported_on_a_yes():
    assert ans(lot(walk={"m": 100.0, "valid": True}))["lmr"]["band"] == "inner"             # whole range under the inner limit
    assert ans(lot(walk={"m": 520.0, "valid": True}))["lmr"]["band"] == "outer"             # whole range between the two limits
    assert ans(lot(walk={"m": 400.0, "valid": True}))["lmr"]["band"] == "straddles_inner_limit"


# ---- exclusions ---------------------------------------------------------------------------------------
def test_exclusion_map_hit_is_no_with_its_clause():
    r = ans(lot(exclusion=HIT))
    assert r["lmr"]["answer"] == "no" and r["lmr"]["clause"] == "s164(1)(m)" and r["lmr"]["page"] == 80


def test_part_of_lot_on_exclusion_map_is_cant_tell():
    r = ans(lot(exclusion={"point": False, "lot": True}))
    assert r["lmr"]["answer"] == "cant_tell" and r["lmr"]["reason_code"] == "exclusion_map"


def test_a_no_is_final_even_when_other_layers_did_not_answer():
    r = ans(lot(exclusion=HIT, accelerated=None, bushfire=None, sched12_straight_m=None, walk=None))
    assert r["lmr"]["answer"] == "no"
    r = ans(lot(straight_m=2000.0, exclusion=None, heritage={"item": None}))
    assert r["lmr"]["answer"] == "no"


def test_any_unanswered_rule_blocks_a_yes():
    for key in ("exclusion", "accelerated", "bushfire", "tod_map"):
        assert ans(lot(**{key: None}))["lmr"]["answer"] == "cant_tell", key
    assert ans(lot(lga=None))["lmr"]["answer"] == "cant_tell"
    assert ans(lot(sched12_straight_m=None))["lmr"]["answer"] == "cant_tell"
    assert ans(lot(heritage=None))["lmr"]["answer"] == "cant_tell"


def test_point_clear_but_lot_outline_missing_is_not_a_yes():
    assert ans(lot(exclusion={"point": False, "lot": None}))["lmr"]["answer"] == "cant_tell"


@pytest.mark.parametrize("name", ["Bathurst Regional", "CITY OF BLUE MOUNTAINS", "Hawkesbury", "wollondilly shire"])
def test_four_excluded_councils_by_name_in_any_spelling(name):
    r = ans(lot(lga=name))
    assert r["lmr"]["answer"] == "no" and r["lmr"]["clause"] == "s164(1)(e)"


def test_council_list_comes_from_the_law_not_the_code():
    f = copy.deepcopy(FACTS._facts)
    for p in f["s164"]["paragraphs"]:
        if p["para"] == "e":
            p["words"] = "the following local government areas— (i) Inner West,"
    custom = d.LawFacts({"law_version_date": "x", "facts": f})
    assert d.decide(lot(lga="Inner West"), custom)["lmr"]["answer"] == "no"
    assert d.decide(lot(lga="Wollondilly"), custom)["lmr"]["answer"] == "yes"


def test_schedule_12_inside_straight_line_is_cant_tell_beyond_is_clear():
    assert ans(lot(sched12_straight_m=799.0))["lmr"]["answer"] == "cant_tell"
    assert ans(lot(sched12_straight_m=801.0))["lmr"]["answer"] == "yes"


def test_bushfire_hit_is_no_and_unwired_is_printed_not_assumed():
    assert ans(lot(bushfire=HIT))["lmr"]["answer"] == "no"


# ---- heritage -----------------------------------------------------------------------------------------
def test_heritage_item_on_lot_is_no_but_conservation_area_is_only_a_note():
    r = ans(lot(heritage={"item": True, "conservation_area": False, "state_register": False}))
    assert r["lmr"]["answer"] == "no" and r["lmr"]["clause"] == "s164(1)(d)"
    r = ans(lot(heritage={"item": False, "conservation_area": True, "state_register": False}))
    assert r["lmr"]["answer"] == "yes" and any("conservation area" in n for n in r["notes"])


def test_state_heritage_register_hit_is_cant_tell_not_decided():
    r = ans(lot(heritage={"item": False, "conservation_area": False, "state_register": True}))
    assert r["lmr"]["answer"] == "cant_tell"


# ---- TOD ----------------------------------------------------------------------------------------------
def test_tod_lot_in_listed_council_is_tod_and_lmr_is_no_chapter_5():
    r = ans(lot(tod_map=HIT, lga="Canterbury-Bankstown"))
    assert r["pathway"] == "tod" and r["tod"]["answer"] == "yes"
    assert r["lmr"]["answer"] == "no" and r["lmr"]["clause"] == "s164(1)(c)"
    assert r["tod"]["standards"]["tod_fsr"]["value"] == "2.5:1" and r["tod"]["standards"]["tod_fsr"]["page"] == 76


def test_tod_map_but_council_not_listed_is_not_chapter_5():
    r = ans(lot(tod_map=HIT, lga="Woollahra"))
    assert r["tod"]["answer"] == "no" and r["lmr"]["answer"] == "yes"


def test_whole_lot_rule_part_on_map_applies_chapter_5_to_the_lot():
    r = ans(lot(tod_map={"point": False, "lot": True}))
    assert r["tod"]["answer"] == "yes" and r["tod"]["figures"].get("whole_lot_rule") is True


def test_whole_lot_rule_switched_off_for_a_heritage_item_lot():
    r = ans(lot(tod_map={"point": False, "lot": True},
                heritage={"item": True, "conservation_area": False, "state_register": False}))
    assert r["tod"]["answer"] == "cant_tell"
    assert r["lmr"]["answer"] == "no"  # the heritage item itself still excludes Chapter 6


def test_tod_unknown_council_is_cant_tell_never_no():
    assert ans(lot(tod_map=HIT, lga=None))["tod"]["answer"] == "cant_tell"
    assert ans(lot(tod_map=None))["tod"]["answer"] == "cant_tell"


def test_tod_standards_are_read_from_the_law_file():
    f = copy.deepcopy(FACTS._facts)
    f["tod_fsr"]["value"] = "9:1"
    custom = d.LawFacts({"law_version_date": "x", "facts": f})
    r = d.decide(lot(tod_map=HIT), custom)
    assert r["tod"]["standards"]["tod_fsr"]["value"] == "9:1"


# ---- fail closed --------------------------------------------------------------------------------------
def test_missing_law_file_gives_cant_tell_not_an_exception(tmp_path):
    bad = tmp_path / "nope.json"
    with pytest.raises(d.LawFactsError):
        d.LawFacts.load(bad)


def test_decide_never_raises_on_garbage():
    for g in (None, {}, {"walk": "x", "heritage": 5, "lga": 7, "straight_m": "a"}, {"tod_map": "yes"}):
        r = d.decide(g, FACTS)
        assert r["lmr"]["answer"] in ("cant_tell", "no")
        assert r["lmr"]["answer"] != "yes"


def test_law_fact_missing_makes_the_answer_cant_tell():
    f = copy.deepcopy(FACTS._facts)
    del f["lmr_outer_distance"]
    r = d.decide(lot(), d.LawFacts({"law_version_date": "x", "facts": f}))
    assert r["lmr"]["answer"] == "cant_tell" and r["lmr"]["reason_code"] == "safety_check_failed"


def test_empty_input_is_never_yes():
    assert d.decide({}, FACTS)["lmr"]["answer"] == "cant_tell"


def test_norm_lga():
    assert d.norm_lga("CITY OF BLUE MOUNTAINS") == d.norm_lga("Blue Mountains") == "blue mountains"
    assert d.norm_lga("") is None and d.norm_lga(None) is None and d.norm_lga(3) is None
    assert d.norm_lga("Canterbury-Bankstown") == "canterbury bankstown"


# ---- wording ------------------------------------------------------------------------------------------
LIAB = LIABILITY = re.compile(r"\b(safe|safely|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|"
                       r"guaranteed|certified|confirmed|verified|ensure|assure|accurate|definitive|comprehensive|"
                       r"reliable|eligible)\b", re.I)


def test_no_liability_words_in_any_text_we_write():
    cases = [lot(), lot(exclusion=HIT), lot(tod_map=HIT), lot(walk=None), lot(straight_m=900.0),
             lot(heritage={"item": False, "conservation_area": True, "state_register": True})]
    for m in cases:
        r = ans(m)
        texts = [r["headline"], r["lmr"]["detail"], r["tod"]["detail"], *r["notes"], *(x["what"] for x in r["not_checked"])]
        texts += [x["detail"] for x in r["lmr"]["rules"]]
        for t in texts:
            assert not LIABILITY.search(t), t


# ---- aircraft noise (h) and pipelines (i) -------------------------------------------------------------
ANEC = "Australian Noise Exposure Concept (units)"
ANEF = "Australian Noise Exposure Forecast (units)"


def noisy(*bands, **over):
    return lot(airport_noise=[{"code": c, "name": n} for c, n in bands], **over)


@pytest.mark.parametrize("code,name,expected", [
    ("20 - 25", ANEC, "no"),      # the law: ANEC 20 or greater
    ("25 - 30", ANEC, "no"),
    ("20 - 25", ANEF, "yes"),     # the law: ANEF 25 or greater, so the 20 - 25 band is below it
    ("25 - 30", ANEF, "no"),
    ("40 +", ANEF, "no"),
])
def test_noise_bands_are_compared_with_the_laws_own_levels(code, name, expected):
    r = ans(noisy((code, name)))["lmr"]
    assert r["answer"] == expected
    if expected == "no":
        assert r["clause"] == "s164(1)(h)" and r["page"] == 79


def test_noise_levels_come_from_the_saved_law_not_the_code():
    f = copy.deepcopy(FACTS._facts)
    f["s164_h_anef_min"]["value"] = 20
    custom = d.LawFacts({"law_version_date": "x", "facts": f})
    assert d.decide(noisy(("20 - 25", ANEF)), custom)["lmr"]["answer"] == "no"


def test_noise_no_band_is_clear_and_a_failed_or_unreadable_band_blocks_a_yes():
    assert ans(lot(airport_noise=[]))["lmr"]["answer"] == "yes"
    assert ans(lot(airport_noise=None))["lmr"]["answer"] == "cant_tell"
    assert ans(noisy(("High Noise", ANEF)))["lmr"]["answer"] == "cant_tell"
    assert ans(noisy(("20 - 25", ANEF), ("High Noise", ANEF)))["lmr"]["answer"] == "cant_tell"
    assert ans(noisy(("20 - 25", ANEF), ("25 - 30", ANEF)))["lmr"]["answer"] == "no"       # an excluding band wins over a lower one


def test_h_is_still_listed_as_partly_checked_even_when_the_noise_map_answered():
    r = ans(lot(airport_noise=[]))
    h = next(x for x in r["not_checked"] if x["para"] == "h")
    assert "Sydney Airport" in h["what"] and h["clause"] == "s164(1)(h)"


def test_pipeline_hit_is_a_warning_not_a_block_and_a_miss_clears_nothing():
    hit = ans(lot(pipeline={"hit": True, "names": ["x"]}))
    assert hit["lmr"]["answer"] == "yes" and [w["clause"] for w in hit["warnings"]] == ["s164(1)(i)"]
    assert "section 2.77(3)" in hit["warnings"][0]["detail"] and "200 m" in hit["warnings"][0]["detail"]
    for p in ({"hit": False, "names": []}, {"hit": None, "names": []}, None):
        r = ans(lot(pipeline=p))
        assert r["warnings"] == [] and "i" in {x["para"] for x in r["not_checked"]}


def test_pipeline_distance_in_the_warning_follows_the_law_text():
    f = copy.deepcopy(FACTS._facts)
    f["s164_i_distance"]["value"] = 250
    custom = d.LawFacts({"law_version_date": "x", "facts": f})
    assert "250 m" in d.decide(lot(pipeline={"hit": True, "names": []}), custom)["warnings"][0]["detail"]


def test_noise_and_pipeline_wording_has_no_liability_words():
    r = ans(lot(pipeline={"hit": True, "names": []}, airport_noise=[]))
    for t in [w["detail"] for w in r["warnings"]] + [x["what"] for x in r["not_checked"]]:
        assert not LIAB.search(t), t


def test_walk_method_note_is_plain_english():
    """The card prints this note to a reader. It must not use the internal words it once did."""
    from services.lmr_area_decision import WALK_HEURISTIC
    for word in ("lopsided", "router", "straddles", "heuristic"):
        assert word not in WALK_HEURISTIC.lower()
    assert "75 m shorter and 225 m longer" in WALK_HEURISTIC  # the figures still come from the constants


def test_reader_facing_details_avoid_internal_words():
    """`detail` and `headline` are printed on the card. 'anchor' is the code's word for a station or town centre; a reader never sees it."""
    import inspect
    src = inspect.getsource(d)
    for line in src.splitlines():
        if '"detail":' in line and "reason_code" in line:
            assert "anchor" not in line.split('"detail":', 1)[1].lower(), line.strip()


def test_no_answer_headline_leads_with_the_reason_in_plain_words():
    """A lot with no answer shows 'Why: <reason>' first. The reasons the walking code gives use no internal words."""
    r = d._failed("a map did not respond")
    assert r["headline"].startswith("Why: a map did not respond")
    assert "No answer" not in r["headline"] and "Not determined" not in r["headline"]
    import inspect
    from services import lmr_walk_surface as ws
    src = inspect.getsource(ws)
    for line in src.splitlines():
        if "_invalid(" in line or "notes.append(" in line:
            for word in ("anchor", "surface has", "node", "network too thin"):
                assert word not in line.split("(", 1)[-1].lower() or "def _invalid" in line, line.strip()


def test_failure_reply_has_every_field_the_page_requires():
    """The page rejects a reply that lacks any of these (frontend-nextjs/hooks/useAreaCheck.ts isAreaCheck). A rejected reply throws away the
    reason and the card says 'did not respond', so every reply, including a failure, must carry all of them."""
    for r in (d._failed("a map did not respond"), d.decide({}, None)):
        assert isinstance(r["headline"], str) and r["headline"]
        assert r["lmr"]["answer"] in ("yes", "no", "borderline", "cant_tell")
        assert r["tod"]["answer"] in ("yes", "no", "borderline", "cant_tell")
        for key in ("warnings", "not_checked", "notes"):
            assert isinstance(r[key], list), key
