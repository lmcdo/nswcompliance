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


def test_paragraphs_sharing_a_number_are_joined_never_suffixed():
    # City of Sydney 3.15: unnumbered paragraphs under one heading. "3.15_2" is
    # printed nowhere; the rule is one rule under 3.15.
    got, ext = R.merge_codes([{"code": "3.15", "text": "first paragraph"},
                              {"code": "3.15", "text": "second paragraph"}], taken=set())
    assert [(p["code"], p["text"]) for p in got] == [("3.15", "first paragraph" + chr(10) * 2 + "second paragraph")]
    assert ext == {}


def test_a_code_held_by_a_rule_not_reread_extends_that_rule():
    got, ext = R.merge_codes([{"code": "4.1 C2", "text": "new words"}], taken={"4_1 C2"})
    assert got == [] and ext == {"4_1 C2": "new words"}


def test_an_exact_repeat_is_dropped_and_blank_codes_skipped():
    got, _ = R.merge_codes([{"code": "A", "text": "t"}, {"code": "A", "text": "t"},
                            {"code": "", "text": "u"}], taken=set())
    assert [p["code"] for p in got] == ["A"]


def test_section_in_force_is_the_last_numbered_heading_before_the_page():
    raw = [C.Line(1, 10, 70, "header"), C.Line(1, 100, 70, "3.2 torrens title"),
           C.Line(2, 100, 70, "3.3 strata subdivision"), C.Line(2, 200, 70, "c13 some rule words here"),
           C.Line(3, 100, 70, "c14 the next rule")]
    ch = C.ChapterLines.build(raw, page_width=595.0)
    assert R.section_in_force(ch, 3) == "3.3"
    assert R.section_in_force(ch, 1) is None


def test_a_new_dotted_code_matching_a_stored_ref_tail_is_recognised():
    _got, ext = R.merge_codes([{"code": "4.1 C2", "text": "new"}], taken={"4_1 C2"})
    assert "4_1 C2" in ext


def test_a_page_whose_rules_came_back_is_not_missing():
    lines = [f"development on site {i} must keep the landscaped setback clear" for i in range(6)]
    assert R.page_missing(lines, [{"code": "C1", "text": " ".join(lines)}]) is False


def test_a_page_of_rules_that_came_back_empty_is_missing():
    lines = [f"development on site {i} must keep the maximum landscaped setback clear" for i in range(6)]
    assert R.page_missing(lines, [{"code": "C1", "text": "something else entirely here"}]) is True


def test_a_page_with_citations_the_page_does_not_print_scores_low():
    raw = [C.Line(1, 10, 70, "header"), C.Line(1, 100, 70, "3.3 strata subdivision"),
           C.Line(1, 120, 70, "c13"), C.Line(1, 140, 100, "the strata boundary must relate to the occupancies here")]
    rd = C.both_orders(raw, 595.0)
    good = [{"code": "3.3 C13", "text": "the strata boundary must relate to the occupancies here"}]
    bad = [{"code": "3.2 C14", "text": "the strata boundary must relate to the occupancies here"}]
    assert R.proven_share(good, rd, "Doc__x", 1) == 1.0
    assert R.proven_share(bad, rd, "Doc__x", 1) == 0.0
    assert R.proven_share([], rd, "Doc__x", 1) == 1.0


def test_a_rule_running_over_several_pages_is_placed_on_all_of_them():
    body = ["development must keep the landscaped setback clear of all structures always",
            "and the maximum building height is measured from existing ground level here",
            "while car parking must not dominate the street frontage of the site at all"]
    raw = [C.Line(1, 10, 70, "header")] + [C.Line(p, 100, 70, body[p - 1]) for p in (1, 2, 3)]
    ch = C.ChapterLines.build(raw, page_width=595.0)
    assert R.located_pages(ch, "# 3.1 title\n\n" + " ".join(body)) == {1, 2, 3}


# -- the small question: only the printed number for known wording -------------------

RULE = "the strata subdivision boundary must relate appropriately to the separate occupancies"


def _ctx(ref="Doc__x__3_2 C14"):
    raw = [C.Line(1, 10, 70, "header"), C.Line(1, 100, 70, "3.3 strata subdivision"),
           C.Line(1, 120, 70, "c13"), C.Line(1, 140, 100, RULE)]
    rd = C.both_orders(raw, 595.0)
    text = f"# 3.2 C14 torrens\n\n{RULE}"
    return {"council": "c", "chapter": "x", "document_id": "Doc__x", "readings": rd,
            "live": [(ref, text, "Doc__x")], "placed": [(ref, text, {1})],
            "page_lines": {1: ["header", "3.3 strata subdivision", "c13", RULE]}}


def test_parse_labels_reads_numbered_answers_and_survives_junk():
    got = R.parse_labels('{"labels": [{"i": 1, "code": "3.3 C13", "title": "Strata"}, {"i": "x"}]}')
    assert got == {1: {"code": "3.3 C13", "title": "Strata"}}
    assert R.parse_labels("not json") == {} and R.parse_labels("[]") == {}


def test_body_of_drops_only_our_heading_line():
    assert R.body_of("# 3.2 C14 torrens\n\nthe words") == "the words"
    assert R.body_of("plain words") == "plain words"


def test_a_page_whose_rules_sit_on_it_alone_gets_the_small_question():
    plan = R.plan_pages(_ctx(), 10)
    assert plan["read"] == set() and list(plan["label"]) == [1]


def test_a_corrected_number_is_used_only_when_it_proves():
    ctx = _ctx()
    plan = {"read": set(), "gaps": set(), "label": {1: [("Doc__x__3_2 C14", "")]}}
    ok = R.build_change(ctx, plan, [], {"Doc__x__3_2 C14": {"code": "3.3 C13", "title": "strata"}})
    assert [x["ref_number"] for x in ok["added"]] == ["Doc__x__3_3 C13"]
    assert [x["ref_number"] for x in ok["removed"]] == ["Doc__x__3_2 C14"]
    wrong = R.build_change(ctx, plan, [], {"Doc__x__3_2 C14": {"code": "3.4 C99", "title": ""}})
    assert wrong["added"] == [] and wrong["removed"] == []


def test_a_paragraph_joining_a_kept_rule_changes_that_rule_not_adds_a_second():
    ctx = _ctx(ref="Doc__x__3_3 C13")
    ctx["placed"] = [("Doc__x__3_3 C13", ctx["live"][0][1], {2})]   # kept: page 2 not re-read
    plan = {"read": {1}, "gaps": set(), "label": {}}
    change = R.build_change(ctx, plan, [(1, [{"code": "3.3 C13", "text": "more words for it"}])], {})
    assert change["added"] == []
    assert [c["ref_number"] for c in change["changed"]] == ["Doc__x__3_3 C13"]
    assert change["changed"][0]["new_text"].endswith("more words for it")
