"""DQ-101 "Page Proof" — the fidelity gate certifies corrupt text as `grounded`.

The gate already exists and already runs automatically: `scripts/dcp_fidelity_gate.py`
grades every pending review-queue row against its chapter PDF, and
`dcp_supersede_guard.enforce_fidelity` refuses a commit that carries no verdict. Nothing
about the WIRING is missing. What is missing is that the grader throws the evidence away
before it scores.

Measured live on 2026-09-22, same extraction run, same chapter
(canterbury_bankstown/chapter-7-5-canterbury-local-centre):

    extractor  : schema_fail — 12 of 49 provisions with serious artifacts
    fidelity   : 39 grounded, 3 ok, 3 flagged

Twelve provisions carrying serious artifacts, and the gate called essentially all of them
grounded. That is not a sampling accident; it follows from three properties of the grader:

1. `_content_words` is `[a-z]{4,}` — only words of FOUR OR MORE letters are scored. A
   scrambled map label is single letters (`S T R E E T`), so the corruption is discarded
   before the ratio is computed and cannot lower it. DQ-78's rows are invisible BY
   CONSTRUCTION.
2. Words are compared as a SET, so order is never checked. Two-column interleave is the
   right words in the wrong order and scores 100%. This is the same blindness recorded in
   `feedback-two-column-interleave-hides-from-the-scramble-ratio`: correct words, wrong
   order, scores 0.055 on the scramble ratio and reads as "clean".
3. Membership is `w in page_text` — a SUBSTRING test. `"50"` and `"00"` are both substrings
   of `"5000"`, so a LaTeX-split number passes against a page that states the real value.

Every assertion below is written against text taken from production on 2026-09-22, not
invented. The four `TestTheGateMustRefuse` cases FAIL before the fix — that is the point:
a gate whose zero has never been shown to move is not evidence of anything
(`memory/project-defect-repair-calibration-2026-08`: a page-match probe read 0 everywhere
because it dropped short words and digits).

The `TestTheGateMustStillAccept` cases are the confusable negatives. They are not padding.
Demanding a stored number appear literally on its page once marked 116 CORRECT rows wrong
(2026-09-18), and an exact-substring check on citations fixed 11 rows and broke 11. A fix
that flags these has not tightened the gate, it has broken it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

fg = pytest.importorskip("dcp_fidelity_gate")


# --------------------------------------------------------------------------------------
# Fixtures. Page text is what the council's PDF says; row text is what we stored.
# --------------------------------------------------------------------------------------

#: A real Codes SEPP clause, as the legislation states it.
TANK_PAGE = (
    "3.5 Ancillary development\n"
    "A fuel tank installed on the land must not have a capacity of more than 5000 L "
    "and must be located behind the building line of the dwelling house. "
    "A gas tank must not have a capacity of more than 1000 L. "
    "The tank must be screened from the street and must not be located within the "
    "front setback of the allotment."
)

#: What we actually serve. The reader emitted LaTeX and SPLIT both numbers.
#: '50 00' is not 5000 and '1 000' is not 1000 -- but '50', '00', '1' and '000' are each
#: substrings of the page's own numbers, so the numeric check finds them all.
TANK_ROW_SPLIT_NUMBERS = (
    "A fuel tank installed on the land must not have a capacity of more than "
    "{ \\cdot } 50 00 L and must be located behind the building line of the dwelling "
    "house. A gas tank must not have a capacity of more than 1 {} 000 L. "
    "The tank must be screened from the street and must not be located within the "
    "front setback of the allotment."
)

#: A City of Sydney locality page: ordinary prose, plus a figure whose street labels are
#: drawn one glyph at a time.
LOCALITY_PAGE = (
    "6.2.12 Darlinghurst Road locality\n"
    "Development at 18-32A Darlinghurst Road is to provide publicly accessible open "
    "space at ground level. Buildings are to address the street frontage and maintain "
    "the existing pattern of subdivision. Figure 5.244 Danks Street South Land "
    "Amalgamation."
)

#: The stored row: the same prose with the map's street labels swept into it. Every
#: injected token is a SINGLE LETTER, which `[a-z]{4,}` discards before scoring.
LOCALITY_ROW_MAP_INTERLEAVE = (
    "Development at 18-32A Darlinghurst Road is to provide publicly accessible open "
    "space at ground level. T E E T R E O T T S T T S T R E T R E E T R RI TI S S S "
    "A P O M B A E P Buildings are to address the street frontage and maintain the "
    "existing pattern of subdivision."
)

#: A Ku-ring-gai cover page. `UURRBBAA83NN P PRREEC8C5ININCCTT` is "URBAN PRECINCT" with
#: every glyph doubled AND the page numbers 83/85 injected mid-word, which is why the
#: existing undoubling guard cannot restore it (verified 2026-09-22: it returns
#: ' 83NN P PRREEC8C5ININCCTT').
PRECINCT_PAGE = (
    "14K.1 Urban Precinct\n"
    "The site at 45-47 Tennyson Avenue and 105 Eastern Road Turramurra is identified "
    "as an urban precinct. Development is to respond to the existing streetscape "
    "character and provide deep soil landscaping along the eastern boundary."
)

PRECINCT_ROW_DOUBLED = (
    "The site at 45-47 Tennyson Avenue and 105 Eastern Road Turramurra is identified "
    "as an urban precinct. UURRBBAA83NN P PRREEC8C5ININCCTT AANNDD S SITITEESS "
    "Development is to respond to the existing streetscape character and provide "
    "deep soil landscaping along the eastern boundary."
)


def pages(text: str, anchor: int = 3) -> dict:
    """One chapter whose anchor page holds `text`, with plausible neighbours.

    Neighbours matter: `_page_window` widens to page +-1, so a single-page dict would
    make the anchor unambiguous in a way a real chapter never is.
    """
    return {
        anchor - 1: "Part 3 Residential development. This part applies to land in Zone R2.",
        anchor: text,
        anchor + 1: "Objectives. To ensure development is compatible with the locality.",
    }


# DQ-101 WAS diagnosed here and is now FIXED (2026-09-22, same day).
#
# These three cases shipped as xfail(strict=True) while the defect was open, so that
# fixing the grader would fail the test FOR PASSING (XPASS) and force the marker off
# rather than leave a stale claim behind. That is exactly what happened: adding the
# reverse checks to ground_row turned all three XPASS(strict), and the markers were
# removed in the same change. A plain skip would have hidden the fix as well as the bug.
#
# What the grader now also asks, having only ever asked "are the row's words on the page":
#   * unsourced-token ratio, counting SHORT tokens -- catches scrambled figure labels,
#     which are single letters and were discarded by [a-z]{4,} before scoring
#   * word-pair adjacency -- catches column interleave, the right words in the wrong order
#   * whole-token number match -- catches "50 00" against a page that says "5000"

class TestTheGateMustRefuse:
    """Each of these is real corruption that the gate currently certifies as grounded."""

    def test_a_split_number_is_not_the_number_on_the_page(self):
        """'50 00 L' against a page that says '5000 L'.

        A planner reads a 5,000 L limit as 50 L or 00 L depending on where they stop.
        The numeric check passes only because '50' and '00' are substrings of '5000'.
        """
        got = fg.ground_row(TANK_ROW_SPLIT_NUMBERS, "sepp__3_5", pages(TANK_PAGE))
        assert got["status"] == "flagged", (
            "a fuel-tank capacity stored as '50 00 L' was certified against a page "
            f"stating '5000 L' (detail={got['detail']!r})")

    def test_map_labels_swept_into_prose_are_refused(self):
        """The injected tokens are single letters, so `[a-z]{4,}` never sees them."""
        got = fg.ground_row(LOCALITY_ROW_MAP_INTERLEAVE, "sydney__6_2_12",
                            pages(LOCALITY_PAGE))
        assert got["status"] == "flagged", (
            "a provision carrying 'T E E T R E O T T S' scrambled off a map figure was "
            f"certified as grounded (detail={got['detail']!r})")

    def test_doubled_glyphs_with_injected_page_numbers_are_refused(self):
        got = fg.ground_row(PRECINCT_ROW_DOUBLED, "krg__14k_1", pages(PRECINCT_PAGE))
        assert got["status"] == "flagged", (
            "a provision carrying 'UURRBBAA83NN P PRREEC8C5ININCCTT' was certified as "
            f"grounded (detail={got['detail']!r})")

    def test_the_right_words_in_the_wrong_order_are_refused(self):
        """Two-column interleave. Set membership scores this 100%.

        Reversing the words keeps the multiset identical, so any bag-of-words check is
        blind to it by construction. This is the fault class the repo already knows
        scores 0.055 = 'clean' on the scramble ratio.
        """
        scrambled = " ".join(reversed(TANK_PAGE.split()))
        got = fg.ground_row(scrambled, "sepp__3_5", pages(TANK_PAGE))
        assert got["status"] == "flagged", (
            "text whose words are the page's own, in reverse order, was certified as "
            f"grounded (detail={got['detail']!r})")


class TestTheGateMustStillAccept:
    """Confusable negatives. A fix that trips these has broken the gate, not tightened it.

    Both cost real rows when they were got wrong before: demanding a literal number on the
    page marked 116 correct rows wrong, and tightening citation matching fixed 11 rows and
    broke 11.
    """

    def test_the_same_text_rewrapped_is_still_grounded(self):
        """A PDF re-export changes line breaks and spacing, not meaning."""
        rewrapped = "\n".join(TANK_PAGE.replace("\n", " ").split(". "))
        got = fg.ground_row(rewrapped, "sepp__3_5", pages(TANK_PAGE))
        assert got["status"] == "grounded", (
            f"re-wrapping the very same sentences flagged the row (detail={got['detail']!r})")

    def test_a_clause_continuing_onto_the_next_page_is_still_grounded(self):
        """The clause opens on the anchor page and finishes on the next one."""
        p = pages(TANK_PAGE)
        p[4] = ("and must not be located within the front setback of the allotment or "
                "within 900 mm of a side boundary.")
        row = (TANK_PAGE.split("\n", 1)[1] +
               " and must not be located within 900 mm of a side boundary.")
        got = fg.ground_row(row, "sepp__3_5", p)
        assert got["status"] == "grounded", (
            f"a clause straddling a page break was flagged (detail={got['detail']!r})")

    def test_the_new_checks_add_nothing_to_a_thousands_separated_page(self):
        """The page prints "1,500 m2"; the row stores "1500 m2".

        The EXISTING number check flags this, deliberately. Commit cc3f15f0 (Sol
        cross-review, HIGH 0.97) made a thousands-separated value a different number
        because "500" was matching inside "1,500" and grounding a 500 m² minimum lot size
        against a chapter stating 1,500. That decision is not this change's to reverse —
        the first version of this test asserted the opposite and was wrong.

        What DQ-101's three checks must not do is pile on a second, different-sounding
        complaint about the same formatting. `_tokens` strips the separator before
        tokenising precisely so they stay quiet here: a row carrying the page's own words
        in the page's own order has no unsourced tokens and no broken pairs, whatever the
        commas do. A mutation removing that normalisation is caught by this test.
        """
        page = (
            "4.2 Lot requirements\n"
            "The minimum lot size for a dual occupancy is 1,500 m2 and the maximum gross "
            "floor area is 12,000 m2 where the site adjoins a classified road."
        )
        row = (
            "The minimum lot size for a dual occupancy is 1500 m2 and the maximum gross "
            "floor area is 12000 m2 where the site adjoins a classified road."
        )
        src = " ".join(pages(page).values())
        assert fg._unsourced_ratio(row, src) == 0.0, (
            "the separator made the row's own numbers look absent from its own page")
        assert fg._adjacency_ratio(row, src) == 1.0, (
            "the separator broke word-pair matching on text that is word-for-word the page")
        assert fg._split_numbers(row, src, set()) == [], (
            "a separated page number was reported as a reader-split number")

    def test_the_rows_own_section_code_is_not_demanded_of_the_page(self):
        """`code_nums` exists so a ref like `3_5` is not hunted for as a control value."""
        got = fg.ground_row(TANK_PAGE.split("\n", 1)[1], "sepp__99_99", pages(TANK_PAGE))
        assert got["status"] == "grounded", (
            f"the row's own section code was demanded of the page (detail={got['detail']!r})")
