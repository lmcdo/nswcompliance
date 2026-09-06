"""Fidelity gate grading (2026-09) — DQ-97 follow-up.

Contract under test (anchored to a real false-flag found live: city_of_sydney
section-2-locality-statements, provision 2_1_2, page 11 — text visibly runs
across a page break per its own footer stamps '2.1-4' / '2.1-5'):
  - a confident page match grounds against a +-1 page window, not just the
    single anchor page, so text that legitimately straddles a page break is
    not falsely flagged as unmatched
  - a genuinely wrong/hallucinated number is still flagged even against the
    wider window (the fix must not weaken the numeric check into a rubber
    stamp — NUMERIC changes stay human-gated by design)
  - an ambiguous (non-confident) page match still falls back to the whole
    chapter, unchanged by this fix
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# dcp_fidelity_gate does bare `import dcp_extract_changed` / `import verify_extraction_fidelity`,
# relying on scripts/ being on sys.path (true when run as `python scripts/dcp_fidelity_gate.py`,
# not when loaded via importlib from tests/) -- so scripts/ must be added explicitly here too.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(os.path.dirname(__file__), "..", "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gate = _load("dcp_fidelity_gate")
_best_page = _gate._best_page
_page_window = _gate._page_window
ground_row = _gate.ground_row


class TestPageWindow:
    def test_includes_neighbours_when_present(self):
        pages = {10: "alpha", 11: "beta", 12: "gamma"}
        assert _page_window(11, pages) == "alpha beta gamma"

    def test_missing_neighbour_is_skipped_not_blank(self):
        pages = {11: "beta", 12: "gamma"}
        assert _page_window(11, pages) == "beta gamma"

    def test_single_page_chapter(self):
        pages = {1: "only page"}
        assert _page_window(1, pages) == "only page"


class TestGroundRowPageStraddle:
    """Reproduces the real defect: a provision whose distinctive words are
    split across two consecutive pages must ground as fine, not flagged."""

    # Most of the provision's distinctive vocabulary sits on page 11 (enough to win
    # the confident match on its own), but the clause finishes on page 12 — the
    # '2.1-4' -> '2.1-5' continuation pattern from the live case.
    PAGE_11 = ("locality statement heritage conservation landscape setting "
               "streetscape character precinct boundary")
    PAGE_12 = "continues alignment reference below determination unrelated other clause text"
    STRADDLING_TEXT = ("locality statement heritage conservation landscape setting streetscape "
                        "character precinct boundary continues alignment reference below determination")

    def test_straddling_text_grounds_when_confident(self):
        pages = {11: self.PAGE_11, 12: self.PAGE_12}
        result = ground_row(self.STRADDLING_TEXT, "cos__2_1_2", pages)
        assert result["status"] == "grounded"
        assert result["verified_page"] == 11

    def test_same_text_would_have_falsely_flagged_on_single_page(self):
        """Proves the old behaviour was the bug, not a coincidence of this fixture:
        grounding against page 11 alone drops below the 75% word-match threshold."""
        import verify_extraction_fidelity as vf
        prov_words = set(vf._content_words(self.STRADDLING_TEXT))
        single_page_ratio = sum(1 for w in prov_words if w in self.PAGE_11) / len(prov_words)
        assert single_page_ratio < 0.75  # old code would have flagged this

    def test_content_confined_to_one_page_still_grounds(self):
        pages = {5: "car parking rate is one space per dwelling for this precinct",
                  6: "unrelated clause about tree preservation orders"}
        result = ground_row("car parking rate is one space per dwelling for this precinct",
                             "x__5_1", pages)
        assert result["status"] == "grounded"


class TestGroundRowStillCatchesRealErrors:
    def test_hallucinated_number_flags_even_with_wider_window(self):
        pages = {
            11: "front setback is 4.5 metres from the primary road boundary",
            12: "side setback is 1.2 metres for a single storey dwelling",
        }
        # AI wrote 9.9m -- nowhere in the anchor page OR its neighbours.
        text = "front setback is 9.9 metres from the primary road boundary"
        result = ground_row(text, "x__2_1", pages)
        assert result["status"] == "flagged"
        assert "9.9" in result["detail"]

    def test_unrelated_text_flags_not_grounded(self):
        pages = {1: "flood planning level provisions for the low-lying precinct"}
        result = ground_row("bicycle parking requirements for commercial premises",
                             "x__9_9", pages)
        assert result["status"] == "flagged"


class TestNonConfidentFallbackUnchanged:
    def test_ambiguous_match_uses_whole_chapter_not_a_window(self):
        """When no single page wins clearly, the fix must not change the
        existing whole-chapter fallback (used for repeated/short/boilerplate
        clauses that appear near-identically on many pages)."""
        pages = {1: "objective clause", 2: "objective clause", 3: "objective clause"}
        page, confident = _best_page({"objective", "clause"}, pages)
        assert confident is False
        result = ground_row("objective clause", "x__1_1", pages)
        assert result["verified_page"] is None
        assert result["status"] == "grounded"


class TestCitationNumbers:
    """2026-09-07: live queue rows showed 'numbers not in source' false-flagging
    numbers that were never regulatory values at all -- table captions we stamp
    ourselves, and page/figure/clause cross-references the AI faithfully
    transcribed. Fixtures below are the real flagged rows (ashfield/blacktown,
    council DB), trimmed to the minimum reproducing snippet."""

    _citation_numbers = staticmethod(_gate._citation_numbers)

    def test_table_caption_excludes_both_index_and_page(self):
        text = "some clause text\n\n**Table 3** (Page 63)\n\n<table>...</table>"
        nums = self._citation_numbers(text)
        assert "3" in nums and "63" in nums

    def test_page_citation_in_prose(self):
        # ashfield D-Part6/DS3.17: "Comprehensive Inner West DCP 2016 page 123"
        text = "see Figures 8-11 (maps).\nComprehensive Inner West DCP 2016 page 123\n\nFigure 10"
        nums = self._citation_numbers(text)
        assert "123" in nums

    def test_figure_range_expands_to_every_endpoint(self):
        text = "see Figures 8-11 (maps) for the relevant elevations."
        nums = self._citation_numbers(text)
        assert {"8", "9", "10", "11"} <= nums
        # KNOWN TRADEOFF, not a guarded case: if a genuine value elsewhere in the
        # SAME row's text happens to share a digit-string with a figure range cited
        # in that row (e.g. a real "10 m" height alongside "see Figures 8-11"), this
        # exclusion is set-based, not proximity-aware, and would wrongly exempt it
        # too. Accepted for the same reason the pre-existing whole-chapter fallback
        # is: a large, measured cut in false positives against a narrow, specific
        # coincidence, not a silent hole in the common case.

    def test_figure_range_guards_against_absurd_span(self):
        text = "see Figures 3-99999 for details."
        nums = self._citation_numbers(text)
        # "3" is separately caught by the single-figure citation pattern ("Figures 3")
        # -- correct on its own terms, since it IS a real figure being cited. The guard
        # under test is narrower: the RANGE must not expand to 99,996 excluded numbers.
        assert "99999" not in nums
        assert "50000" not in nums

    def test_clause_citation_ds_and_pc_codes(self):
        # ashfield D-Part1/PC2: "pursuant to clauses PC2 and DS 2.6"
        text = "12 m Street Wall Height pursuant to clauses PC2 and DS 2.6"
        nums = self._citation_numbers(text)
        assert "2" in nums and "2.6" in nums

    def test_plain_measurement_not_swept_up_as_a_citation(self):
        """Guard against the exclusion swallowing genuine values: a setback
        figure with no 'page'/'Figure'/'Table'/'DS'/'PC' nearby must survive."""
        text = "the minimum rear setback is 4.5 metres from the boundary"
        nums = self._citation_numbers(text)
        assert "4.5" not in nums

    def test_footer_stamp_excludes_both_parts(self):
        # ku_ring_gai section-b-part-14d/14d_9: "Ku-ring-gai Development Control
        # Plan\n14D\nGORDON LOCAL CENTRE\np 14-135" -- a section-scoped running
        # footer, distinct format from the generic "page N" citation.
        text = "Ku-ring-gai Development Control Plan\n14D\nGORDON LOCAL CENTRE\np 14-135\n\nURBAN"
        nums = self._citation_numbers(text)
        assert "14" in nums and "135" in nums

    def test_property_number_excludes_the_address_not_the_setback(self):
        # ku_ring_gai section-b-part-14d/14d_9, verbatim: the real value (3m) must
        # survive; only the address number (810) is excluded.
        text = ("3 metre setback to Radford Place applying to property no.810 "
                "Pacific Highway for wider footpaths.")
        nums = self._citation_numbers(text)
        assert "810" in nums
        assert "3" not in nums

    def test_property_number_requires_no_prefix_not_bare_digits(self):
        """Guard: a bare setback number with no 'no.'/'no ' prefix anywhere near
        it must never be caught by this pattern."""
        text = "side setback of 900mm applies to all boundaries"
        nums = self._citation_numbers(text)
        assert "900" not in nums


class TestPageWindowFollowsTableCaptions:
    """2026-09-07: blacktown 10_4_3_1 is three stitched tables from real pages
    61/62/63 (each stamped by dcp_extract_changed.py's own caption); _best_page's
    word-overlap heuristic anchored on 61, and a bare +-1 window (60-62) missed 63
    even though the row's OWN caption already states it. Using that caption is
    exact, not another heuristic widening."""

    def test_window_extends_to_a_captioned_page_outside_neighbours(self):
        pages = {60: "unrelated", 61: "table one content", 62: "table two content",
                  63: "225mm above finished ground"}
        text = "flood controls\n\n**Table 1** (Page 61)\n\n**Table 3** (Page 63)"
        window = _page_window(61, pages, text)
        assert "225mm" in window

    def test_no_captions_falls_back_to_plain_neighbours(self):
        pages = {10: "a", 11: "b", 12: "c", 20: "should not appear"}
        assert _page_window(11, pages, "no captions here") == "a b c"

    def test_end_to_end_real_shape_grounds_the_flood_row(self):
        """Reproduces the actual defect (verified live against the real Blacktown
        10_4_3_1 PDF, which now grounds too): a row whose real values (200mm, 225mm)
        sit on a caption-named page the +-1 window alone would miss. Page text is
        lowercase throughout -- matching _page_text_for_chapter's own _norm(), which
        always lowercases; grounding is case-sensitive, so a mixed-case fixture here
        would falsely fail regardless of the fix."""
        part_a = ("flood related development controls f1 f2 f3 garage floor level "
                  "natural ground level annual exceedance probability flood level")
        part_b = "f9 the height difference minus 200 mm 225mm above finished ground"
        pages = {
            60: "unrelated preceding page content about setbacks driveways street "
                "frontage landscaping fencing",
            61: part_a,
            62: "unrelated filler page landscaping requirements fencing controls "
                "parking allocation bicycle",
            63: part_b,
        }
        text = ("# 10.4.3.1 land use by vulnerability to flooding\n\n" + part_a + "\n\n"
                "**Table 1** (Page 61)\n\n**Table 3** (Page 63)\n\n" + part_b)
        result = ground_row(text, "blacktown__10_4_3_1", pages)
        assert result["status"] == "grounded"
        assert result["verified_page"] == 61


class TestHeadingExclusionRequiresRealHeading:
    """2026-09-07 regression: the first heading-exclusion draft used text.splitlines()[0]
    unconditionally, so a single-line row with NO separate heading line had its own
    (and only) content line treated as "the heading" and fully exempted from checking --
    a genuinely wrong number in a heading-less row would have silently passed. Real
    rows are always built as "# {heading}\\n\\n{content}" (dcp_extract_changed.py), so
    requiring the first line to start with '#' is both correct and the guard against
    this collapsing back in."""

    def test_single_line_row_without_heading_marker_is_still_checked(self):
        pages = {1: "front setback is 4.5 metres from the primary road boundary"}
        # No leading '#' -- this must NOT be treated as a heading line.
        text = "front setback is 9.9 metres from the primary road boundary"
        result = ground_row(text, "x__1_1", pages)
        assert result["status"] == "flagged"
        assert "9.9" in result["detail"]

    def test_real_heading_line_numbers_are_still_excluded(self):
        # Lowercase page text -- matches _page_text_for_chapter's _norm(), which always
        # lowercases; a running header repeating the precinct name is what let the real
        # Ashfield D-Part12 rows ground on word-match alone (only the numbers were flagged).
        pages = {1: "d-part12 55-63 smith street summer hill the design controls "
                    "for this precinct address building form"}
        text = ("# D-Part12 55-63 Smith Street Summer Hill\n\n"
                 "the design controls for this precinct address building form")
        result = ground_row(text, "x__12_1", pages)
        assert result["status"] == "grounded"
