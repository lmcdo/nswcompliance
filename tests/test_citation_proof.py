"""A citation is proven only where the council printed it, directly above the rule.

Every case below is a real row from the 2026-09-24 prototype run over nine
chapters, reduced to the lines that decided it. Each weakness the prototype hit
is pinned twice: the case that must PASS and the confusable one that must FAIL.
A checker that only ever passes, or only ever fails, cannot satisfy both.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

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
    # The council's "7." printed right where the rule starts IS its C7 (2026-09-25,
    # Warringah): the number beside the words is exact. A "7." further up the
    # section is not the rule's own and stays item_format.
    ch = doc(["e7 development on land adjoining public open space", "7. " + BODY])
    assert prove("E7 C7", ch)["status"] == "proven"
    ch = doc(["e7 development on land adjoining public open space", "7. other rule words here",
              "and more of them", "then more", "still more", "and the last", BODY])
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
    raw = [C.Line(1, 20.0, 480.0, "6.3-18"),                 # page number, top margin
           C.Line(1, 100.0, 70.0, "a site heading in words only"),
           C.Line(1, 120.0, 70.0, "4. " + BODY),
           C.Line(1, 800.0, 70.0, "footer words")]
    assert prove("6_3_4", C.ChapterLines.build(raw, page_width=595.0))["status"] == "not_proven"


def test_the_heading_above_wins_over_a_repeat_below():
    ch = doc(["g9.6.4 basements", "o1", BODY, "g9.6.4 continues over the page"])
    assert prove("G9_6_4 O1", ch)["status"] == "proven"


def test_campbelltown_lettered_control_is_an_item_format_verdict():
    # Campbelltown prints "b)"; the reader stored "C2" for the same control.
    ch = doc(["3.7.2.10 multi dwelling housing and waste", "a) first control", "b) " + BODY])
    r = prove("3_7_2_10 C2", ch)
    assert r["status"] == "not_proven" and "item_format" in r["detail"]
    # ...and a letter that is NOT the matching position is not excused.
    ch2 = doc(["3.7.2.10 multi dwelling housing and waste", "a) first control", "d) " + BODY])
    assert "item_format" not in (prove("3_7_2_10 C2", ch2)["detail"] or "")


def test_leichhardt_control_label_sharing_the_section_letter_does_not_close_it():
    ch = doc(["c2.2.4.1 sub-area controls", "c10 an earlier control", "c11", BODY])
    assert prove("C2_2_4_1 C11", ch)["status"] == "proven"
    # ...a DOTTED code in that letter still does.
    ch2 = doc(["c2.2.4.1 sub-area controls", "c2.2.4.2 another sub-area", "c11", BODY])
    assert prove("C2_2_4_1 C11", ch2)["status"] == "not_proven"


def test_two_column_page_in_reading_order():
    # Narrow columns: no line holds six words, so the wording is only found
    # across line breaks. Sorted top-to-bottom, the right column's lines
    # interleave the left column's and it is never found intact.
    left = ["e. structures such", "as paths, letter", "boxes and electricity", "kiosks may be", "located in setbacks."]
    right = ["note one here", "note two here", "note three here", "note four here", "note five here"]
    raw = [C.Line(1, 100.0, 60.0, "3.3.5 setbacks")]
    raw += [C.Line(1, 120.0 + 20 * i, 60.0, t) for i, t in enumerate(left)]
    raw += [C.Line(1, 120.0 + 20 * i, 320.0, t) for i, t in enumerate(right)]
    text = "# t\n\ne. Structures such as paths, letter boxes and electricity kiosks may be located"
    kept = C.ChapterLines.build(raw, page_width=595.0, keep_order=True)
    assert C.prove_citation("D__c__3_3_5", text, kept)["status"] == "proven"
    interleaved = C.ChapterLines.build(raw, page_width=595.0)
    assert C.prove_citation("D__c__3_3_5", text, interleaved)["status"] == "text_not_found"


def test_either_reading_order_can_prove_but_both_must_fail():
    # Heading column sorts first top-to-bottom, but last in reading order.
    raw = [C.Line(1, 120.0, 320.0, "c3."), C.Line(1, 140.0, 320.0, BODY),
           C.Line(1, 100.0, 50.0, "5.4.3 energy efficiency")]
    readings = C.both_orders(raw, 842.0)
    assert C.prove_citation("D__c__5_4_3 C3", "# t\n\n" + BODY, readings[0])["status"] != "proven"
    assert C.prove_citation_any("D__c__5_4_3 C3", "# t\n\n" + BODY, readings)["status"] == "proven"
    assert C.prove_citation_any("D__c__5_4_4 C3", "# t\n\n" + BODY, readings)["status"] == "not_proven"


def test_landscape_page_running_header_is_furniture():
    pages = []
    for p in (1, 2, 3):
        # Landscape page, 595 tall: the header sits at its foot, which is
        # mid-page by the measure of an 842-tall portrait page.
        pages += [C.Line(p, 60.0, 51.0, f"5.4.{p} heading {p}"), C.Line(p, 80.0, 51.0, "c1."),
                  C.Line(p, 100.0, 51.0, f"rule words number {p} " + BODY),
                  C.Line(p, 560.0, 597.0, "chapter 7.6 belmore and lakemba precinct"),
                  C.Line(p, 575.0, 400.0, f"footer text {p}")]
    pages += [C.Line(4, 800.0, 70.0, "a tall portrait page line")]      # document-wide bottom 800
    ch = C.ChapterLines.build(pages, page_width=842.0)
    assert all("chapter 7.6" not in ln.text for ln in ch.lines)


def test_running_header_proves_a_parent_but_is_never_the_heading():
    # Woollahra: "e6 | sustainability" in every page header, sections "1.1".
    raw = []
    for p in (1, 2, 3):
        raw += [C.Line(p, 35.0, 70.0, "e6 | sustainability"),
                C.Line(p, 100.0, 70.0, f"1.{p} topic {p}"),
                C.Line(p, 120.0, 70.0, f"page {p} words " + BODY),
                C.Line(p, 775.0, 70.0, "2 december 2024")]
    ch = C.ChapterLines.build(raw, page_width=595.0)
    assert prove("E6_1_2", ch, text=f"page 2 words {BODY}")["status"] == "proven"
    # ...but the header cannot stand in for the section heading itself: "E6"
    # alone for a rule printed under 1.2 is true but coarse, never proven.
    assert prove("E6", ch, text=f"page 2 words {BODY}")["status"] == "imprecise"


def test_collapsed_parent_is_imprecise_not_proven():
    # Marrickville's collapsed-parent defect: 2.25 cited for a rule under 2.25.3.4.
    ch = doc(["2.25 stormwater", "2.25.3 detention", "2.25.3.4 osd sizing", "c11", BODY])
    assert prove("2_25_C11", ch)["status"] == "imprecise"
    assert prove("2_25_3_4_C11", ch)["status"] == "proven"


def test_chapter_named_only_in_the_running_header_is_imprecise():
    raw = []
    for p in (1, 2, 3):
        raw += [C.Line(p, 35.0, 70.0, "e2 | stormwater and flood risk management"),
                C.Line(p, 100.0, 70.0, f"e2.{p}.1 topic {p}"), C.Line(p, 110.0, 70.0, "c6"),
                C.Line(p, 120.0, 70.0, f"page {p} words " + BODY),
                C.Line(p, 775.0, 70.0, "2 december 2024")]
    ch = C.ChapterLines.build(raw, page_width=595.0)
    assert prove("E2 C6", ch, text=f"page 2 words {BODY}")["status"] == "imprecise"


def test_collapsed_parent_without_an_item_label_is_imprecise_too():
    ch = doc(["2.25 stormwater", "2.25.3 detention", "2.25.3.4 osd sizing", BODY])
    assert prove("2_25", ch)["status"] == "imprecise"
    assert prove("2_25_3_4", ch)["status"] == "proven"


def test_bare_number_is_judged_only_after_a_heading_word():
    # Leichhardt Appendix B: "Section 11 - Corner Hotels". The old reader filed
    # these rules under the prompt's example "C4.9"; the new one reads "11 C1".
    ch = doc(["section 11 – corner hotels", "c1 " + BODY])
    assert prove("11 C1", ch)["status"] == "proven"
    ch2 = doc(["section 11 – corner hotels", "section 12 – warehouses", "c1 " + BODY])
    assert prove("11 C1", ch2)["status"] == "not_proven"
    ch3 = doc(["11 corner hotels", "c1 " + BODY])        # no heading word: not judged
    assert prove("11 C1", ch3)["status"] == "unjudged"


def test_a_numbered_list_item_is_not_section_n():
    # "11." is item eleven of a list inside Section 12, not Section 11.
    ch = doc(["section 11 – corner hotels", "c1 other words"],
             ["section 12 – warehouses", "11. an eleventh list item", "c1 " + BODY])
    assert prove("11 C1", ch)["status"] == "not_proven"
    assert prove("12 C1", ch)["status"] == "proven"


def test_the_next_sections_heading_below_the_rule_proves_nothing():
    # Cross-review 2026-09-24: 2.2 printed just BELOW a rule under 2.1 proved a
    # row citing 2.2, through the side-column allowance.
    ch = doc(["2.1 first section", "c1 " + BODY, "2.2 second section", "c1 other words"])
    assert prove("2_2 C1", ch)["status"] == "not_proven"
    assert prove("2_1 C1", ch)["status"] == "proven"


def test_one_shared_phrase_does_not_decide_where_a_rule_sits():
    # Cross-review 2026-09-24: a generic opening repeated under 4.2 anchored a
    # rule whose substance is printed only under 7.1.
    generic = "development must be designed to ensure"
    rule = generic + " that stormwater is detained on site and released slowly to the street drainage system"
    ch = doc(["4.2 heading four two", "c1 " + generic + " privacy is kept for neighbours"],
             ["7.1 heading seven one", "c1 " + rule])
    assert prove("4_2 C1", ch, text=rule)["status"] == "not_proven"
    assert prove("7_1 C1", ch, text=rule)["status"] == "proven"


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN LIMITATION, 2026-09-24: when the stored text only half matches the "
    "page, two places tie on coverage and proof under EITHER is accepted. Needs "
    "a choose-the-best-anchor rule, not any-anchor. Kept as a failing test so it "
    "cannot be forgotten; strict, so fixing it turns this red until unmarked."))
def test_closing_words_repeated_after_the_next_heading_do_not_move_the_rule():
    # The stored rule ends differently from the page, and its closing words
    # appear only further on, under the NEXT heading. Searched loosely, the end
    # of the rule jumped there and proved a row citing that next section.
    body = "planting along the eastern boundary is to be retained and maintained"
    tail = "as shown on the approved landscape plan"
    filler = " ".join(f"filler{n}" for n in range(30))
    ch = doc(["2.1 landscaping", "c1 " + body + " per the council plan", filler,
              "2.2 fencing", "c1 fences are to match " + tail])
    stored = body + " " + tail
    assert prove("2_2 C1", ch, text=stored)["status"] != "proven"
    assert prove("2_1 C1", ch, text=stored)["status"] == "proven"


def test_a_year_or_standard_number_is_not_a_heading():
    # "1924.2-81 (playground equipment ..." proved "1924.2 C10" in leichhardt C1.
    for text in ("1924.2-81 (playground equipment for parks", "1997 amendments", "4.1-2 storeys"):
        assert C.CODE_AT_START.match(text) is None, text
    for text, code in (("4.1 c2 setbacks", "4.1"), ("c10 fences", "c10"), ("8.2.3 heights", "8.2.3")):
        assert C.CODE_AT_START.match(text).group(1) == code


def test_a_bare_label_is_not_proven_as_a_section():
    # Marrickville/Leichhardt rows cited only "C12": the label line proved itself.
    body = "the quick council wording of this particular rule sits right here on the page"
    raw = [C.Line(1, 100.0 + 20 * n, 70.0, t) for n, t in enumerate(
        ["2.9.1 controls", "c11 something else entirely here", "c12", body])]
    rd = C.both_orders(raw, 595.0)
    assert C.prove_citation_any("D__C12", "# C12 x\n\n" + body, rd)["status"] != "proven"
    raw = [C.Line(1, 100.0 + 20 * n, 70.0, t) for n, t in enumerate(["b6 waste", body])]
    rd = C.both_orders(raw, 595.0)
    assert C.prove_citation_any("D__B6", "# B6 x\n\n" + body, rd)["status"] == "proven"


def test_a_council_number_label_beside_the_rule_proves_our_letter_label():
    # Warringah prints "14." where we store "G2 C14". Only the number beside the rule counts.
    body = "the quick council wording of this particular rule sits right here on the page"
    lines = ["g2 building setbacks", "requirements", "13. all buildings are set back eight metres",
             "14. " + body]
    rd = C.both_orders([C.Line(1, 100.0 + 20 * n, 70.0, t) for n, t in enumerate(lines)], 595.0)
    assert C.prove_citation_any("D__G2 C14", "# G2 C14 x\n\n" + body, rd)["status"] == "proven"
    assert C.prove_citation_any("D__G2 C13", "# G2 C13 x\n\n" + body, rd)["status"] != "proven"
    assert C.prove_citation_any("D__G2 C15", "# G2 C15 x\n\n" + body, rd)["status"] != "proven"


def test_a_rule_sentence_after_a_code_is_not_a_heading_title():
    """_OBLIGATION held literal backspace characters where \b belongs, so it never matched and
    "C80 Development must improve ..." counted as a heading "C80" with a title (2026-09-26)."""
    L = [C.Line(page=1, y=0.0, x=0.0, text="c80 development must improve amenity"),
         C.Line(page=1, y=0.0, x=0.0, text="c3 fences and walls"),
         C.Line(page=1, y=0.0, x=0.0, text="c4 mayfield precinct")]   # "may" inside a word
    assert not C._titled(L, 0, "c80")
    assert C._titled(L, 1, "c3")
    assert C._titled(L, 2, "c4")
    assert "\x08" not in C._OBLIGATION.pattern


def test_the_repeated_ref_marker_does_not_eat_the_clause_number():
    """#1197 suffixes a repeated ref `~2`. Its PR says split_ref "ignores the suffix",
    which holds only for `7_4 (a)~2`: the item marker separates them, so `~2` becomes
    a token of its own. Attached straight to digits it ate the last component --
    `3_15_5_2~2` split into `3 15 5 2~2`, `2~2` failed _CONT, and `3.15.5.2` was
    judged as `3.15.5`. Measured 2026-10-02: five City of Sydney rows were held as
    "citation not proven" while page 106 prints "3.15.5.2 Monitoring and Review".
    A marked ref and its unmarked twin must read the same clause number.
    """
    for marked, plain in (("3_15_5_2~2", "3_15_5_2"),
                          ("3_1_1~4", "3_1_1"),
                          ("3_15~6", "3_15"),
                          ("7_4 (a)~2", "7_4 (a)")):
        got = [C.render(g) for g in C.split_ref(f"Doc__chap__{marked}")[0]]
        want = [C.render(g) for g in C.split_ref(f"Doc__chap__{plain}")[0]]
        assert got == want, f"{marked} read as {got}, its twin {plain} as {want}"
    # and the number itself, not just agreement with the twin
    assert [C.render(g) for g in C.split_ref("Doc__chap__3_15_5_2~2")[0]] == ["3.15.5.2"]
    assert C.split_ref("Doc__chap__3_15~6")[2] is None   # was "bare integer section"
    # #1197's own guard: section 3.16 is stored 3_16 and must not be mistaken for a marker
    assert [C.render(g) for g in C.split_ref("x__3_16")[0]] == ["3.16"]
