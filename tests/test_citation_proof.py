"""A citation is proven only where the council printed it, directly above the rule.

Every case below is a real row from the 2026-09-24 prototype run over nine
chapters, reduced to the lines that decided it. Each weakness the prototype hit
is pinned twice: the case that must PASS and the confusable one that must FAIL.
A checker that only ever passes, or only ever fails, cannot satisfy both.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import citation_proof as C  # noqa: E402

BODY = "the quick council wording of this particular rule sits right here on the page"


def doc(*pages, x=70.0, width=595.0):
    """pages: each a list of line strings, or (x, text) for a side-column line."""
    raw = []
    for pno, lines in enumerate(pages, 1):
        raw.append(C.Line(pno, 10.0, 70.0, f"header of page {pno}"))
        for n, t in enumerate(lines):
            lx, lt = t if isinstance(t, tuple) else (x, t)
            raw.append(C.Line(pno, 100.0 + 20 * n, lx, lt.lower()))
        raw.append(C.Line(pno, 800.0, 300.0, str(pno)))
    return C.ChapterLines.build(raw, page_width=width)


def prove(ref, ch, text=BODY, hint=None):
    return C.prove_citation(f"Doc__chap__{ref}", f"# code title here\n\n{text}", ch, hint)


# -- the plain case --------------------------------------------------------------

def test_heading_then_item_then_rule_is_proven():
    ch = doc(["e2.2.6 overland flow", "c3", BODY])
    assert prove("E2_2_6 C3", ch)["status"] == "proven"


def test_code_only_mid_sentence_is_a_cross_reference_not_proof():
    ch = doc(["development must refer to e2.2.6 for detail", "c3", BODY])
    r = prove("E2_2_6 C3", ch)
    assert r["status"] == "not_proven" and "cross_ref_only" in r["detail"]


# -- nearest heading, not "printed somewhere" -------------------------------------

def test_marrickville_neighbouring_number_is_not_the_heading_above():
    # 8.2.31.6 exists earlier in the document; the rule sits under 8.2.39.6.
    ch = doc(["8.2.31.6 other site controls", "other words"],
             ["8.2.39.6 applicable conservation controls", BODY])
    r = prove("8_2_31_6", ch)
    assert r["status"] == "not_proven" and "not_nearest" in r["detail"]


def test_leichhardt_shallower_heading_of_the_same_family_ends_the_scope():
    # G8.6.4 is printed further up; G6.14 is printed directly above the rule.
    ch = doc(["g8.6.4 building materials", "o1", "something else"],
             ["g6.14", "o1", BODY])
    assert prove("G8_6_4 O1", ch)["status"] == "not_proven"
    assert prove("G6_14 O1", ch)["status"] == "proven"


def test_numbered_list_items_inside_a_section_do_not_end_it():
    ch = doc(["2.9 contributions", "1. first point", "2. second point", BODY])
    assert prove("2_9", ch)["status"] == "proven"


def test_a_measurement_line_is_not_a_heading():
    # "5.5m" shares the section's first number, so read as a heading it would
    # close 5.1.4's scope.
    ch = doc(["5.1.4 flood controls", "5.5m minimum setback to the street", BODY])
    assert prove("5_1_4", ch)["status"] == "proven"


def test_a_margin_navigation_tab_is_not_a_heading():
    # Marrickville prints "8.5 HCA style sheets" at x=551 on every page of 8.4.
    ch = doc(["8.4.1.2 roof form", (551.0, "8.5 hca style sheets"), "c3", BODY])
    assert prove("8_4_1_2_C3", ch)["status"] == "proven"


# -- the prompt's own example -------------------------------------------------------

def test_woollahra_c4_9_is_not_rescued_by_a_cross_reference_to_c4():
    ch = doc(["refer to chapter c4 for heritage", "e2.4 flood planning", "c5", BODY])
    assert prove("C4_9 C5", ch)["status"] == "not_proven"


def test_a_bare_number_is_never_a_heading_piece():
    # Leichhardt C4.4 passed the prototype as "C4 > 4" off a numbered line.
    # Every piece here is printed at a line start; "4.1" is not.
    ch = doc(["c4 parking", "4 access", "1 visitors", "o1", BODY])
    assert prove("C4_4_1 O1", ch)["status"] == "not_proven"


# -- ref shapes that are the council's, joined by us ----------------------------------

def test_waverley_joined_headings_are_proven_piece_by_piece():
    ch = doc(["b14 advertising and signage", "14.3 sign specific controls",
              "14.3.7 murals", BODY])
    assert prove("B14_14_3_14_3_7", ch)["status"] == "proven"


def test_sydney_section_plus_numbered_control():
    ch = doc(["6.3.29 8-24 kippax street", "(1) " + BODY])
    assert prove("6_3_29_1", ch)["status"] == "proven"
    ch2 = doc(["6.3.29 8-24 kippax street", BODY])        # no "(1)" printed
    assert prove("6_3_29_1", ch2)["status"] == "not_proven"


def test_parent_token_is_not_checked_as_its_own_heading():
    ch = doc(["g6.15", "o1", "another objective"], ["c1", BODY])
    assert prove("G6 G6_15 C1", ch)["status"] == "proven"
    # ...but a first token that is NOT a parent of the second is checked.
    assert prove("G8 G6_15 C1", ch)["status"] == "not_proven"


# -- furniture ------------------------------------------------------------------------

def test_sydney_page_number_served_as_a_clause_is_refused():
    # "6.2-20" is City of Sydney's page number; row 95840 served it as a clause.
    raw = [C.Line(1, 100.0, 70.0, "figure 6.58 marriott street setbacks"),
           C.Line(1, 120.0, 70.0, BODY),
           C.Line(1, 800.0, 480.0, "6.2-20")]
    assert prove("6_2_20", C.ChapterLines.build(raw))["status"] == "not_proven"


def test_repeated_control_wording_in_the_body_is_not_page_furniture():
    # Leichhardt prints the same control under many sites; a repetition rule
    # deleted the very line being cited.
    pages = [["g6.15", "c1", BODY]] + [[f"g{n}.2", "c1", BODY] for n in (7, 8, 9)]
    ch = doc(*pages)
    assert prove("G6_15 C1", ch)["status"] == "proven"


# -- where the rule is ------------------------------------------------------------------

def test_stored_page_only_orders_the_search():
    # The AI reader restarts its page count per chunk; the hint points at the
    # wrong site's copy of the same wording.
    ch = doc(["g6.15", "c1", BODY], ["g10.5", "c1", BODY])
    assert prove("G6_15 C1", ch, hint=2)["status"] == "proven"


def test_stored_text_opening_with_its_parent_heading():
    # City of Sydney rows open with the parent site's heading and preamble; the
    # cited sub-heading is only reached from the END of the stored text.
    preamble = [f"preamble line {n} about the site and its additional height" for n in range(14)]
    ch = doc(["6.3.29 8-24 kippax street"] + preamble, ["6.3.29.1 built form", BODY])
    text = "8 24 kippax street " + " ".join(preamble) + " 6.3.29.1 built form " + BODY
    assert prove("6_3_29_1", ch, text=text)["status"] == "proven"


def test_rule_text_running_on_into_the_next_clause():
    ch = doc(["2.9 contributions", BODY, "2.10 next clause", "more words of the next clause here now"])
    run_on = BODY + " 2.10 next clause more words of the next clause here now"
    assert prove("2_9", ch, text=run_on)["status"] == "proven"


def test_side_column_heading_sorted_just_after_the_rule_line():
    raw = [C.Line(1, 101.0, 71.0, "c5"), C.Line(1, 100.0, 107.0, BODY),
           C.Line(1, 90.0, 71.0, "g9.6.4 basements")]
    assert prove("G9_6_4 C5", C.ChapterLines.build(raw))["status"] == "proven"


# -- item labels -------------------------------------------------------------------------

def test_item_in_our_format_not_the_councils_is_its_own_verdict():
    ch = doc(["e7 development on land adjoining public open space", "7. " + BODY])
    r = prove("E7 C7", ch)
    assert r["status"] == "not_proven" and "item_format" in r["detail"]


def test_item_the_council_never_printed():
    ch = doc(["ds1.1", "pc1.", BODY])
    assert prove("DS1_1 C1", ch)["status"] == "not_proven"


# -- declared, not dropped ---------------------------------------------------------------

def test_unjudgeable_and_missing_text_are_named():
    ch = doc(["2.9 contributions", BODY])
    assert prove("6", ch)["status"] == "unjudged"
    assert prove("2_9", ch, text="words that appear nowhere at all in this document ok")["status"] \
        == "text_not_found"


def test_a_section_scoped_page_number_is_not_a_heading():
    # City of Sydney prints "6.3-18" in the footer. With the footer read as the
    # heading "6.3" and a list item "4." beside the rule, 6.3.4 -- printed
    # nowhere -- would be proven.
    raw = [C.Line(1, 100.0, 70.0, "a site heading in words only"),
           C.Line(1, 120.0, 70.0, "4. " + BODY),
           C.Line(1, 800.0, 480.0, "6.3-18")]
    assert prove("6_3_4", C.ChapterLines.build(raw, page_width=595.0))["status"] == "not_proven"


def test_the_heading_above_wins_over_a_repeat_below():
    ch = doc(["g9.6.4 basements", "o1", BODY, "g9.6.4 continues over the page"])
    assert prove("G9_6_4 O1", ch)["status"] == "proven"
