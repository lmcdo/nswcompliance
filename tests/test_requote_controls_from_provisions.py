"""A control's quote is replaced only by the council's own words from a CURRENT rule, holding the control's number, never shared across values."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import requote_controls_from_provisions as r  # noqa: E402

RULE = {"id": 1, "page": 12, "text": "# 3.2 Setbacks\nA minimum 6m rear setback applies.\nSide setbacks to external walls should be a minimum of 900mm.\nMaximum 15 metres in height."}


def ctl(cid=10, vmin=None, vmax=None, text="", ct="rear_setback", dt="dwelling_house"):
    return {"id": cid, "control_type": ct, "dev_type": dt, "value_min": vmin, "value_max": vmax, "unit": "m", "condition": None, "source_text": text,
            "pdf_page": 1, "provision_id": None}


def test_an_exact_quote_holding_the_number_is_proven():
    assert r.prove("A minimum 6m rear setback applies.", RULE["text"], ctl(vmin=6)) == (True, "proven")


def test_whitespace_differences_are_ignored_but_words_are_not():
    assert r.prove("A  minimum 6m   rear setback applies.", RULE["text"], ctl(vmin=6))[0] is True
    assert r.prove("A minimum 5m rear setback applies.", RULE["text"], ctl(vmin=5))[0] is False


def test_a_number_that_is_only_inside_a_bigger_number_is_not_the_number():
    """5 must not be satisfied by the 15 in 'Maximum 15 metres in height'."""
    ok, why = r.prove("Maximum 15 metres in height.", RULE["text"], ctl(vmax=5, ct="max_height"))
    assert ok is False and "number" in why


def test_a_quote_that_does_not_hold_the_control_number_is_refused():
    ok, why = r.prove("Side setbacks to external walls should be a minimum of 900mm.", RULE["text"], ctl(vmin=1.5))
    assert ok is False and "number" in why


def test_an_objective_is_not_a_control():
    t = "To support the plan 2022-2032 minimum 29% LGA canopy target."
    ok, why = r.prove(t, t, ctl(vmin=29, ct="tree_canopy_min"))
    assert ok is False and "objective" in why


def test_an_empty_too_short_or_too_long_quote_is_refused():
    for q in (None, "", "6m", "x" * 401):
        assert r.prove(q, RULE["text"], ctl(vmin=6))[0] is False


def test_the_same_quote_for_controls_of_different_values_is_ambiguous_but_not_for_the_same_value():
    a = {"quote": "Maximum 0 0.4 0.7 1.2", "ctl": ctl(1, vmin=0)}
    b = {"quote": "Maximum 0 0.4 0.7 1.2", "ctl": ctl(2, vmin=0.4)}
    c = {"quote": "Maximum 0 0.4 0.7 1.2", "ctl": ctl(3, vmin=0)}
    assert r.ambiguous({1: a, 2: b}) == {1, 2}
    assert r.ambiguous({1: a, 3: c}) == set()


def test_plan_uses_a_reader_answer_and_drops_one_that_is_not_in_the_rule():
    good = {"control_id": 10, "provision_id": 1, "quote": "A minimum 6m rear setback applies."}
    forged = {"control_id": 11, "provision_id": 1, "quote": "A minimum 7m rear setback applies."}
    planned, rej = r.plan([ctl(10, vmin=6), ctl(11, vmin=7)], [RULE], {10: good, 11: forged})
    assert set(planned) == {10} and planned[10]["by"] == "reader" and planned[10]["page"] == 12
    assert "substring" in rej[11]


def test_a_readers_none_stands_the_program_does_not_overrule_it():
    planned, rej = r.plan([ctl(10, vmin=6)], [RULE], {10: {"control_id": 10, "provision_id": None, "quote": None}})
    assert planned == {} and rej[10] == "reader gave none"


def test_a_provision_the_reader_names_that_is_not_a_current_rule_of_the_council_is_not_used():
    answer = {"control_id": 10, "provision_id": 999, "quote": "A minimum 6m rear setback applies."}
    planned, rej = r.plan([ctl(10, vmin=6)], [RULE], {10: answer})
    assert planned == {} and rej[10] == "reader gave none"


def test_the_program_proposes_only_when_the_best_unit_clearly_wins():
    prov = {"id": 2, "page": 3, "text": "A minimum 6m rear setback applies to dwelling houses.\nA minimum 6m rear setback applies to dwelling houses in zone R3."}
    planned, rej = r.plan([ctl(10, vmin=6, text="rear setback 6m dwelling houses")], [prov], {})
    assert 10 not in planned          # two near-identical candidates: no clear winner, so it asks a reader
    planned, rej = r.plan([ctl(10, vmin=6, text="minimum rear setback 6m")], [RULE], {})
    assert planned[10]["by"] == "program" and "6m rear setback" in planned[10]["quote"]


def test_a_control_with_no_number_gets_no_program_proposal():
    planned, rej = r.plan([ctl(10, text="rear setback")], [RULE], {})
    assert planned == {} and rej[10] == "no proposal"


def test_release_only_frees_holds_the_quote_check_wrote():
    assert r.HOLD_REASON.match("quote not word-for-word in source PDF (whole-PDF check 2026-10-29)")
    assert r.HOLD_REASON.match("chapter_pdf_changed")
    assert not r.HOLD_REASON.match("Spot check 2026-09-13 (Claude, at the owner's request): STAYS HIDDEN")
    assert not r.HOLD_REASON.match("")
