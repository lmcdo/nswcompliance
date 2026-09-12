"""The three page-map checks, each forced to FAIL as well as to pass.

Standing rule (memory/feedback-detect-a-guard-by-forcing-its-failure): every
detector needs a confusable negative, and every check must be shown to be capable
of failing. The check this replaces -- ai_extractor.coverage_gap -- passed its own
tests for two and a half months while being structurally unable to fire.

The waverley numbers below are measured, not invented:
  PDF is 448 pages; the map describes 473
  F1-F5 map to 460-473 and extract nothing
  22 of 33 ranges sit on the wrong pages
  54 of 263 checkable rows contradict their own page header
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_page_map_gate import (  # noqa: E402
    FAIL, PASS, UNKNOWN, PageMapUnusable, assert_map_usable,
    check_ranges_match_headers, check_ranges_within_pdf,
    check_rows_match_page_headers, page_part_codes, ratchet,
)

# A trimmed stand-in for COUNCIL_PAGE_RANGES['waverley'], carrying the shape that
# matters: parts that fit, and the F-block that points past the end of the PDF.
WAVERLEY_LIKE = [
    ("B1", "Waste", 12, 23),
    ("B15", "Public Domain", 136, 146),
    ("F1", "Shared Residential Accommodation", 460, 461),
    ("F5", "Horticulture", 473, 473),
]
WAVERLEY_PDF_PAGES = 448


class TestCheck1RangesWithinPdf:
    """Arithmetic. The only check here that blocks, because it cannot be wrong."""

    def test_waverley_f_block_past_the_end_fails(self):
        res = check_ranges_within_pdf(WAVERLEY_LIKE, WAVERLEY_PDF_PAGES)
        assert res["status"] == FAIL
        assert {v["code"] for v in res["violations"]} == {"F1", "F5"}

    def test_a_map_that_fits_passes(self):
        fits = [("B1", "Waste", 12, 23), ("B15", "Public Domain", 136, 146)]
        assert check_ranges_within_pdf(fits, WAVERLEY_PDF_PAGES)["status"] == PASS

    def test_a_range_starting_past_the_end_is_caught_not_just_ending_past_it(self):
        # ku_ring_gai 9c_16 is 34-35 of a 34-page PDF: the END is past, the start
        # is not. A check that only looked at `b` would miss a start-past case,
        # so both bounds are asserted.
        assert check_ranges_within_pdf(
            [("x", "t", 35, 40)], 34)["status"] == FAIL
        assert check_ranges_within_pdf(
            [("9c_16", "t", 34, 35)], 34)["status"] == FAIL

    def test_boundary_last_page_is_allowed(self):
        # Off-by-one in the safe direction would reject every map's final range.
        assert check_ranges_within_pdf([("x", "t", 30, 34)], 34)["status"] == PASS

    def test_unknown_page_count_is_UNKNOWN_never_PASS(self):
        for bad in (None, 0, -1):
            assert check_ranges_within_pdf(WAVERLEY_LIKE, bad)["status"] == UNKNOWN


class TestCheck2RangesMatchHeaders:
    # A 40-page document whose pages 1-30 carry a running header: 75% coverage,
    # comfortably over HEADER_MIN_PAGE_COVERAGE. Below that floor the check
    # correctly returns UNKNOWN, and a fixture that trips it is asserting
    # nothing about FAIL -- which is how the first draft of these tests passed
    # while testing the wrong branch.
    PDF_PAGES = 40

    def _headers(self, spec):
        """{page: code} from [(code, start, end), ...]."""
        out = {}
        for code, a, b in spec:
            for p in range(a, b + 1):
                out[p] = code
        return out

    def test_a_shifted_range_is_caught(self):
        # The map says B9 is on pages 15-16; the pages themselves say B14. This is
        # waverley's real shape -- B9-B13's ranges land on B14's pages.
        page_part = self._headers([("B14", 1, 30)])
        res = check_ranges_match_headers(
            [("B9", "Safety", 15, 16)], page_part, self.PDF_PAGES)
        assert res["status"] == FAIL
        assert res["violations"][0]["pages_say"] == "B14"

    def test_a_correct_range_passes(self):
        page_part = self._headers([("B9", 1, 30)])
        res = check_ranges_match_headers(
            [("B9", "Safety", 15, 16)], page_part, self.PDF_PAGES)
        assert res["status"] == PASS

    def test_a_single_stray_header_does_not_condemn_a_correct_range(self):
        # Majority vote, not any-disagreement. A figure page or a continuation
        # can carry the neighbouring part's header.
        page_part = self._headers([("B9", 1, 30)])
        page_part[18] = "B10"
        res = check_ranges_match_headers(
            [("B9", "Safety", 1, 30)], page_part, self.PDF_PAGES)
        assert res["status"] == PASS

    def test_too_few_pages_with_headers_is_UNKNOWN_never_PASS(self):
        # This is the property that matters. Most councils carry no part code in
        # the running header at all, and reporting those as clean is exactly the
        # failure being repaired.
        sparse = {1: "B1", 2: "B1"}
        res = check_ranges_match_headers(
            [("B9", "Safety", 15, 16)], sparse, self.PDF_PAGES)
        assert res["status"] == UNKNOWN
        assert "carry a part header" in res["reason"]


class TestCheck3RowsMatchPageHeaders:
    def test_mislabelled_rows_are_caught(self):
        # The defect no code-presence check can see: the row is coded B9 and sits
        # on a page that says B14. waverley: 54 of 263.
        page_part = {p: "B14" for p in range(1, 41)}   # 40 of 60 pages = 67%
        rows = [(20, "B9 Safety and Security"), (21, "B9 Safety objectives"),
                (22, "B10 Public Art"), (23, "B11 Design Excellence")]
        rows += [(24 + i, "B14 Signage control " + str(i)) for i in range(16)]
        res = check_rows_match_page_headers(rows, page_part, 60)
        assert res["status"] == FAIL
        assert res["rows_disagree"] == 4
        assert res["examples"][0]["page_says"] == "B14"

    def test_consistent_rows_pass(self):
        page_part = {p: "B14" for p in range(1, 41)}   # 40 of 60 pages = 67%
        rows = [(1 + i, "B14 Signage " + str(i)) for i in range(20)]
        assert check_rows_match_page_headers(rows, page_part, 60)["status"] == PASS

    def test_total_disagreement_is_a_VOCABULARY_MISMATCH_not_a_finding(self):
        # The trap that once read woollahra as 95% broken: "C5" in
        # "E2.2.4 C5 Control 5" is Control 5, not part C5. When essentially every
        # row disagrees, the two sides are not the same kind of code.
        page_part = {p: "B14" for p in range(1, 41)}   # 40 of 60 pages = 67%
        rows = [(1 + i, "C" + str(i + 1) + " Control text") for i in range(20)]
        res = check_rows_match_page_headers(rows, page_part, 60)
        assert res["status"] == UNKNOWN
        assert "vocabulary mismatch" in res["reason"]

    def test_too_few_checkable_rows_is_UNKNOWN_never_PASS(self):
        page_part = {p: "B14" for p in range(1, 41)}   # 40 of 60 pages = 67%
        res = check_rows_match_page_headers(
            [(1, "B14 Signage")], page_part, 60)
        assert res["status"] == UNKNOWN

    def test_null_section_headers_do_not_raise(self):
        # 36 of 12,124 live rows carry a NULL section_header (measured 2026-09-12).
        page_part = {p: "B14" for p in range(1, 41)}   # 40 of 60 pages = 67%
        rows = [(1, None), (2, ""), (3, "B14 Signage")]
        res = check_rows_match_page_headers(rows, page_part, 60)
        assert res["status"] == UNKNOWN  # only one checkable row
        assert res["rows_checked"] == 1


class TestPageHeaderExtraction:
    def test_a_bare_part_code_line_is_read_as_the_header(self):
        pages = ["B15\nPublic Domain\nsome body text", "B15\nmore text"]
        assert page_part_codes(pages) == {1: "B15", 2: "B15"}

    def test_prose_is_not_read_as_a_header(self):
        pages = ["The design of development must respond to the setting."]
        assert page_part_codes(pages) == {}

    def test_a_code_below_the_scanned_lines_is_not_picked_up(self):
        # Only the top few lines are the running header; a code deep in the body
        # is a provision reference, not a page label.
        pages = ["line\nline\nline\nline\nB15"]
        assert page_part_codes(pages) == {}


class TestFailClosedHook:
    """assert_map_usable is what actually stops a stale map being applied."""

    def test_it_raises_on_waverley(self):
        with pytest.raises(PageMapUnusable) as exc:
            assert_map_usable("waverley", None, WAVERLEY_LIKE, WAVERLEY_PDF_PAGES)
        assert "extract NOTHING" in str(exc.value)
        assert "F1 460-461" in str(exc.value)

    def test_it_allows_a_map_that_fits(self):
        assert_map_usable("ashfield", "chapter-a-miscellaneous",
                          [("A-Part1", "Site Analysis", 4, 7)], 126)

    def test_an_unknown_page_count_raises_rather_than_waving_through(self):
        # The whole point of fail-closed. pdf_pages is always known at the call
        # site, so None means something upstream changed -- a stop, not a pass.
        with pytest.raises(PageMapUnusable):
            assert_map_usable("waverley", None, WAVERLEY_LIKE, None)

    def test_it_does_not_raise_on_checks_2_and_3(self):
        # Only check 1 blocks. A map sitting on the wrong pages is reported and
        # ratcheted, not raised -- checks 2 and 3 need a running header that most
        # councils do not carry, and blocking on UNKNOWN there would take the
        # corpus dark.
        assert_map_usable("x", "y", [("B9", "Safety", 1, 2)], 500)


class TestRatchet:
    BASE = {"per_map": {"waverley": {"check1_violations": 5,
                                     "check2_violations": 22,
                                     "check3_rows_disagree": 54}}}

    def test_a_rise_is_a_regression(self):
        now = {"waverley": {"check1_violations": 6, "check2_violations": 22,
                            "check3_rows_disagree": 54}}
        reg, imp, nb, nm = ratchet(now, self.BASE)
        assert len(reg) == 1 and reg[0]["key"] == "check1_violations"
        assert not imp and not nb

    def test_a_fall_is_an_improvement_and_does_not_fail(self):
        now = {"waverley": {"check1_violations": 0, "check2_violations": 0,
                            "check3_rows_disagree": 0}}
        reg, imp, nb, nm = ratchet(now, self.BASE)
        assert not reg and len(imp) == 3

    def test_holding_at_the_baseline_neither_fails_nor_improves(self):
        now = {"waverley": dict(self.BASE["per_map"]["waverley"])}
        reg, imp, nb, nm = ratchet(now, self.BASE)
        assert not reg and not imp and not nb

    def test_an_unknown_map_is_NO_BASELINE_not_a_pass(self):
        # Three states, never two. A new map with nothing to compare against must
        # not read as fine.
        now = {"newcouncil": {"check1_violations": 3, "check2_violations": 0,
                              "check3_rows_disagree": 0}}
        reg, imp, nb, nm = ratchet(now, self.BASE)
        assert not reg and not imp
        assert len(nb) == 3
        assert all(r["map"] == "newcouncil" for r in nb)

    def test_an_empty_baseline_reports_NO_BASELINE_for_everything(self):
        now = {"waverley": {"check1_violations": 5, "check2_violations": 22,
                            "check3_rows_disagree": 54}}
        reg, imp, nb, nm = ratchet(now, {})
        assert not reg and len(nb) == 3

    def test_a_check_that_DID_NOT_RUN_is_not_an_improvement(self):
        # THE FAIL-OPEN THIS CAUGHT. --from-ledger can only run check 1, so
        # check 2 and 3 are absent from `counts`. An earlier draft emitted 0 for
        # them, and the ratchet reported waverley 22 -> 0 and 54 -> 0 as RATCHET
        # DOWN (good) -- an unknown scoring as a fix, which is exactly the defect
        # this gate exists to stop.
        now = {"waverley": {"check1_violations": 5}}      # 2 and 3 did not run
        reg, imp, nb, nm = ratchet(now, self.BASE)
        assert not imp, "a check that did not run was reported as an improvement"
        assert not reg
        assert {r["key"] for r in nm} == {"check2_violations",
                                          "check3_rows_disagree"}
        # and the baseline it could not verify is surfaced, not silently dropped
        assert all(r["was"] for r in nm)

    def test_a_check_that_did_not_run_still_fails_on_the_ones_that_did(self):
        now = {"waverley": {"check1_violations": 9}}      # worse, 2/3 absent
        reg, imp, nb, nm = ratchet(now, self.BASE)
        assert len(reg) == 1 and reg[0]["key"] == "check1_violations"
