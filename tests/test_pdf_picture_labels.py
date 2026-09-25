"""Labels printed as pictures, and the rule's OWN label.

Leichhardt part-c-s1 prints "C9" beside its control as an image; the text layer
has a tab there. 146 correct citations were refused for want of a label
(2026-09-25). And the label check itself was loose: any label printed between
the section heading and the rule counted, so C10 was "proven" as C9 -- 474 of
517 shifted labels passed. Each fix is pinned with its confusable negative.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import citation_proof as C  # noqa: E402
import pdf_picture_labels as P  # noqa: E402

BODY = "the quick council wording of this particular rule sits right here on the page"


def t(page, y, text):
    return (page, y, "t", text)


def p(page, y, mask):
    return (page, y, "p", mask)


# -- naming pictures by their order --------------------------------------------

def test_pictures_under_controls_run_c1_c2_c3():
    ev = [t(1, 10, "controls"), p(1, 20, "m1"), p(1, 30, "m2"), p(1, 40, "m3")]
    assert [n[2] for n in P.name_labels(ev)] == ["c1", "c2", "c3"]


def test_objectives_run_is_o_and_controls_restart_at_one():
    ev = [t(1, 10, "objectives"), p(1, 20, "o1"), p(1, 30, "o2"),
          t(1, 40, "controls"), p(1, 50, "m1")]
    assert [n[2] for n in P.name_labels(ev)] == ["o1", "o2", "c1"]


def test_a_section_heading_ends_the_run():
    # After "c1.4 heritage" and before its own "controls", a picture is not
    # counted -- it is named only by what its mask was called elsewhere.
    ev = [t(1, 10, "controls"), p(1, 20, "m1"), p(1, 30, "m2"),
          t(1, 40, "c1.4 heritage"), p(1, 50, "m2"), p(1, 60, "unseen")]
    assert P.name_labels(ev) == [(1, 20, "c1"), (1, 30, "c2"), (1, 50, "c2")]


def test_a_mask_with_two_names_voids_the_whole_document():
    # The same picture counted as C1 once and C2 elsewhere: the counting is
    # wrong somewhere, so nothing is named -- never a guessed label.
    ev = [t(1, 10, "controls"), p(1, 20, "m1"), p(1, 30, "m2"),
          t(2, 10, "controls"), p(2, 20, "m2")]
    assert P.name_labels(ev) == []


def test_pictures_of_another_size_are_dropped_before_counting():
    pics = [(1, 20, 72, "icon", 5.0), (1, 30, 72, "m1", 8.04), (1, 40, 72, "m2", 8.0)]
    assert [p[3] for p in P.label_sized(pics)] == ["m1", "m2"]
    assert P.label_sized([]) == []


def test_no_run_heading_names_nothing():
    assert P.name_labels([p(1, 20, "m1"), t(1, 30, BODY)]) == []


# -- placing the labels in the reading -------------------------------------------

def _raw():
    # Native order draws the footer FIRST, as Leichhardt's pages do.
    return [C.Line(1, 780.0, 300.0, "part c - 1"),
            C.Line(1, 60.0, 72.0, "controls"),
            C.Line(1, 90.8, 108.0, "first rule words"),
            C.Line(1, 120.0, 108.0, BODY)]


def test_a_label_sits_before_its_row_in_both_readings():
    pics = [(1, 40.0, 72.0, "hdr"), (1, 94.0, 72.0, "m1"), (1, 123.0, 72.0, "m2")]
    # "controls" is text; the header picture is outside a run and unnamed.
    raw = P.merge_labels(_raw(), pics, C.Line)
    native = [ln.text for ln in raw]
    assert native.index("c1") == native.index("first rule words") - 1
    assert native.index("c2") == native.index(BODY) - 1
    assert native[0] == "part c - 1", "a label must not jump ahead of the footer"
    ordered = C.ChapterLines.build(raw, page_width=595.0, keep_order=False).lines
    texts = [ln.text for ln in ordered]
    # The picture's top (94.0) is below the text's (90.8); given its own y the
    # label would sort AFTER the line it labels.
    assert texts.index("c1") == texts.index("first rule words") - 1


def test_no_pictures_leaves_the_reading_untouched():
    raw = _raw()
    assert P.merge_labels(raw, [], C.Line) is raw


# -- the rule's own label ----------------------------------------------------------

def _doc(lines):
    raw = [C.Line(1, 10.0, 70.0, "header")]
    raw += [C.Line(1, 100.0 + 20 * n, 70.0, s) for n, s in enumerate(lines)]
    return C.ChapterLines.build(raw, page_width=595.0)


def _prove(ref, ch, text=BODY):
    return C.prove_citation(f"Doc__chap__{ref}", f"# code title\n\n{text}", ch, None)


def test_the_label_printed_above_an_earlier_rule_is_not_this_rules_label():
    ch = _doc(["c1.3 alterations", "c9", "earlier rule wording only", "c10", BODY])
    assert _prove("C1_3 C10", ch)["status"] == "proven"
    r = _prove("C1_3 C9", ch)
    assert r["status"] == "not_proven" and "item_missing" in r["detail"]


def test_a_sub_heading_above_its_label_still_finds_the_label_below():
    # Stored text opens with the sub-heading, so it anchors one line ABOVE its
    # own label; "last label above" named the previous rule's (C1.3 C8 as C7).
    sub = "for alterations and additions to the side of existing dwellings"
    ch = _doc(["c1.3 alterations", "c7", "earlier rule wording only", sub, "c8", BODY])
    assert _prove("C1_3 C8", ch, text=sub + "\n\n" + BODY)["status"] == "proven"
    assert _prove("C1_3 C7", ch, text=sub + "\n\n" + BODY)["status"] == "not_proven"


def test_a_rule_whose_first_line_sits_in_its_heading_keeps_its_label():
    # Marrickville stores the rule's first line in its heading, so only line two
    # matches -- and the NEXT rule's label is nearer to it than its own.
    ch = _doc(["8.3.2.3 building setbacks", "c14", "original setbacks must be retained",
               "c15", "new construction including carports must not be built", BODY,
               "c16", "driveway-width setbacks beside the house"])
    assert _prove("8_3_2_3 C15", ch)["status"] == "proven"
    assert _prove("8_3_2_3 C16", ch)["status"] == "not_proven"


@pytest.mark.xfail(strict=True, reason=(
    "A phantom second match starts mid-C53 (its closing words recur in C54) and "
    "its span runs into C54's block. Three de-duplication rules were measured "
    "over the corpus 2026-09-25; each fixed this row and broke 8-15 others. "
    "The row is REFUSED rather than proven wrongly."))
def test_closing_words_repeated_in_the_next_rule_do_not_move_the_label():
    # Ashfield E2 2.2.13: C53 ends "at the side of the house"; C54 repeats it.
    ch = _doc(["2.2.13 garages and carports", "controls",
               "c53. new garages and carports are to be located at the back or at the side of the house.",
               "c54. where a garage or carport is at the side of the house it must be at least 1 metre back"])
    text = "New garages and carports are to be located at the back or at the side of the house."
    assert _prove("2_2_13 C53", ch, text=text)["status"] == "proven"
    assert _prove("2_2_13 C54", ch, text=text)["status"] == "not_proven"


@pytest.mark.xfail(strict=True, reason=(
    "c6.1 (a sub-item of control C6) reads as a section heading and ends C1.14's "
    "scope. Telling it from a real section C6.1 needs the printed parent C6 AND "
    "sequential numbering; not built. Leichhardt C1.14 C11, page 88."))
def test_a_nested_sub_item_is_not_a_section_heading():
    ch = _doc(["c1.14 trees", "c6 the following works do not require consent",
               "c6.1 canopy lifting to 2.5 metres", "c11", BODY])
    assert _prove("C1_14 C11", ch)["status"] == "proven"


def test_a_label_printed_after_an_unlabelled_paragraph_is_not_its_label():
    # Cross-review: a note or introduction followed a few lines later by C10
    # was proven as C10 by the "first label after" fallback (Leichhardt B3.2.7
    # note as C1; G9.3 introduction as O1).
    ch = _doc(["b3.2.7 general", "controls", BODY, "c1", "the first real control wording"])
    r = _prove("B3_2_7 C1", ch)
    assert r["status"] == "not_proven"


def _raw_doc(lines):
    """lines: (y, x, text) on page 1."""
    raw = [C.Line(1, 10.0, 70.0, "header")] + [C.Line(1, y, x, t) for y, x, t in lines]
    return C.ChapterLines.build(raw, page_width=595.0)


def test_a_label_left_of_the_rule_but_on_a_lower_row_is_not_its_label():
    ch = _raw_doc([(90.0, 71.0, "g9.6.4 basements"), (100.0, 107.0, BODY),
                   (120.0, 71.0, "c5")])
    assert _prove("G9_6_4 C5", ch)["status"] == "not_proven"


def test_a_label_on_the_rules_row_but_to_its_right_is_not_its_label():
    ch = _raw_doc([(90.0, 71.0, "g9.6.4 basements"), (100.0, 107.0, BODY),
                   (101.0, 500.0, "c5")])
    assert _prove("G9_6_4 C5", ch)["status"] == "not_proven"
