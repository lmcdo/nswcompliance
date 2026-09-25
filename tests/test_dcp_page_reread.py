"""Re-reading only some pages must never wipe a rule that was not re-read."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import citation_proof as C  # noqa: E402
import dcp_page_reread as R  # noqa: E402


def test_a_page_whose_rule_shares_a_number_elsewhere_pulls_that_page_in():
    # Publishing replaces by ref: re-reading page 3 alone would wipe D18 on page 9.
    rows = [("Doc__D18", {3}), ("Doc__D18", {9}), ("Doc__D19", {4})]
    pages, spread = R.close_over_refs({3}, rows)
    assert pages == {3, 9} and spread == []


def test_an_unrelated_page_is_not_pulled_in():
    pages, _ = R.close_over_refs({3}, [("Doc__A", {3}), ("Doc__B", {4})])
    assert pages == {3}


def test_a_number_spread_over_too_many_pages_is_refused():
    rows = [("Doc__X", {p}) for p in range(1, 12)]
    _pages, spread = R.close_over_refs({1}, rows)
    assert spread == ["Doc__X"]


def test_a_rule_cut_by_a_page_break_is_joined():
    got = R.join_page_breaks([(5, [{"code": "C1", "text": "a"}, {"code": "C2", "text": "first half"}]),  # noqa: zone-codes (DCP control labels, not zones)
                              (6, [{"code": "C2", "text": "second half"}, {"code": "C3", "text": "c"}])])  # noqa: zone-codes
    assert [(p["code"], p["text"], p["page"]) for p in got] == [
        ("C1", "a", 5), ("C2", "first half second half", 5), ("C3", "c", 6)]  # noqa: zone-codes


def test_the_same_code_on_non_adjacent_pages_is_not_joined():
    got = R.join_page_breaks([(5, [{"code": "C2", "text": "x"}]), (8, [{"code": "C2", "text": "y"}])])
    assert len(got) == 2


def test_a_code_held_by_a_rule_not_reread_gets_a_suffix_not_a_clash():
    got = R.unique_codes([{"code": "4_1 C2", "text": "new"}], taken={"4_1 C2"})
    assert got[0]["code"] == "4_1 C2_2"


def test_an_exact_repeat_is_dropped_and_blank_codes_skipped():
    got = R.unique_codes([{"code": "A", "text": "t"}, {"code": "A", "text": "t"},
                          {"code": "", "text": "u"}], taken=set())
    assert [p["code"] for p in got] == ["A"]


def test_section_in_force_is_the_last_numbered_heading_before_the_page():
    raw = [C.Line(1, 10, 70, "header"), C.Line(1, 100, 70, "3.2 torrens title"),
           C.Line(2, 100, 70, "3.3 strata subdivision"), C.Line(2, 200, 70, "c13 some rule words here"),
           C.Line(3, 100, 70, "c14 the next rule")]
    ch = C.ChapterLines.build(raw, page_width=595.0)
    assert R.section_in_force(ch, 3) == "3.3"
    assert R.section_in_force(ch, 1) is None


def test_a_new_dotted_code_clashing_with_a_stored_ref_tail_is_suffixed():
    # The model returns "4.1 C2"; the rule not re-read is stored as "..__4_1 C2".
    got = R.unique_codes([{"code": "4.1 C2", "text": "new"}], taken={"4_1 C2"})
    assert got[0]["code"] == "4.1 C2_2"
