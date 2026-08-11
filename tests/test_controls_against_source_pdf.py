"""Falsifiability tests for the controls-vs-published-PDF check.

A check that cannot go red is not a verification -- the DQ-30 "0% drift" lesson, where
stored values were compared against the code that produced them and the metric could not
fail. These tests pin the behaviours that must hold, and `--prove` plants defects in the
core to demonstrate each one is load-bearing rather than decorative.

Module-scope import on purpose: if the module under test cannot be imported the suite is
RED, never green-by-skip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_controls_against_source_pdf import (  # noqa: E402
    required_values,
    strip_clause_marker,
    DOC_NO_TEXT,
    DOC_UNAVAILABLE,
    NO_QUOTE,
    PAGE_OUT_OF_RANGE,
    SUPPORTED_ELSEWHERE,
    SUPPORTED_ON_CITED_PAGE,
    UNSUPPORTED,
    Summary,
    classify,
    distinctive_terms,
    normalise,
    numeric_tokens,
    page_supports,
)

REAL_QUOTE = ("Seniors housing: 0.2 per unit for residents + 1 per 5 units for "
              "visitors and carers (Parking Area 1)")
REAL_PAGE = (
    "PART 2: GENERIC PROVISIONS\n6\nMarrickville Development Control Plan 2011\n"
    "Land use\nCar spaces:\nParking Area 1\nCar spaces:\nParking Area 2\n"
    "Seniors housing\n0.2 per unit for residents +\n1 per 5 units for visitors &\ncarers\n"
    "0.33 per unit for residents\n"
)


class TestNormalisation:
    def test_ampersand_becomes_and(self):
        # The stored quote says "and"; the PDF table says "&". A check that missed this
        # would report a false crisis across every table-derived control.
        assert "and" in normalise("visitors & carers")

    def test_smart_punctuation_folded(self):
        assert normalise("“front” – setback") == '"front" - setback'

    def test_newlines_inside_a_sentence_collapse(self):
        assert normalise("0.2 per unit\nfor residents") == "0.2 per unit for residents"


class TestNumericTokens:
    def test_extracts_every_number(self):
        assert numeric_tokens("0.2 per unit + 1 per 5 units") == ["0.2", "1", "5"]

    def test_equivalent_spellings_normalise(self):
        # 0.50 and .5 and 0.5 are one number to a reader.
        assert numeric_tokens("0.50") == numeric_tokens("0.5") == ["0.5"]

    def test_no_numbers_is_empty_not_error(self):
        assert numeric_tokens("no additional parking required") == []


class TestDistinctiveTerms:
    def test_drops_stopwords_and_units(self):
        terms = distinctive_terms("Minimum required rear setback of 12m")
        assert "setback" in terms and "rear" in terms
        assert "minimum" not in terms and "required" not in terms

    def test_case_folded_and_deduplicated(self):
        assert distinctive_terms("Setback setback SETBACK") == ["setback"]


class TestClauseMarkers:
    """The measured false positive: parramatta id=563 took `6` from `C.06`."""

    def test_leading_clause_marker_is_stripped(self):
        assert strip_clause_marker("C.06 On corner lots").strip() == "On corner lots"
        assert strip_clause_marker("O.01 Ensure development").strip() == "Ensure development"
        assert strip_clause_marker("A.1.2 Something").strip() == "Something"

    def test_clause_digits_never_become_control_values(self):
        # If C.06's 6 leaked in, this list would contain "6".
        assert numeric_tokens("C.06 On corner lots, the setback must be 3 metres") == ["3"]

    def test_a_real_leading_value_is_not_mistaken_for_a_marker(self):
        assert "3" in numeric_tokens("3 metres is the minimum side setback")


class TestRequiredValues:
    def test_stored_value_is_what_must_be_found(self):
        assert "4.5" in required_values(4.5, None)

    def test_metre_value_also_accepted_in_millimetres(self):
        # "900mm" in the PDF, 0.9 in the database -- the same control.
        assert "900" in required_values(0.9, None)

    def test_millimetre_value_also_accepted_in_metres(self):
        assert "0.9" in required_values(900, None)

    def test_no_stored_value_yields_nothing_rather_than_guessing(self):
        assert required_values(None, None) == []


class TestPageSupports:
    def test_real_marrickville_row_is_supported(self):
        ok, coverage, missing = page_supports(REAL_QUOTE, REAL_PAGE)
        assert ok, f"coverage={coverage} missing={missing}"
        assert missing == []

    def test_a_missing_number_is_not_supported(self):
        # THE defect this whole check exists to catch: page says 0.4, we stored 0.2.
        ok, _cov, missing = page_supports(REAL_QUOTE, REAL_PAGE.replace("0.2", "0.4"))
        assert not ok
        assert "0.2" in missing

    def test_stored_value_absent_from_page_is_not_supported(self):
        # The canada_bay class: page says one number, we serve another.
        ok, _cov, missing = page_supports(REAL_QUOTE, REAL_PAGE, value_min=9.9)
        assert not ok
        assert "9.9" in missing

    def test_stored_value_present_wins_over_noisy_quote_numbers(self):
        ok, _cov, missing = page_supports(REAL_QUOTE, REAL_PAGE, value_min=0.2)
        assert ok and missing == []

    def test_right_numbers_wrong_subject_is_not_supported(self):
        # Numbers present but the page is about something else entirely -- term coverage
        # is what stops a coincidental numeric match on a long document.
        page = "Bicycle parking 0.2 1 5 spaces for staff amenity blocks"
        ok, coverage, _ = page_supports(REAL_QUOTE, page)
        assert not ok
        assert coverage < 0.60

    def test_empty_page_is_not_supported(self):
        ok, _c, _m = page_supports(REAL_QUOTE, "")
        assert not ok

    def test_quote_with_no_numbers_or_terms_cannot_pass_vacuously(self):
        ok, _c, _m = page_supports("   ", REAL_PAGE)
        assert not ok


class TestClassify:
    PAGES = {1: "front matter", 8: "approach to parking provision rates",
             10: REAL_PAGE, 11: "other content"}

    def test_supported_on_the_page_it_cites(self):
        v = classify(1, "marrickville", "car_parking", REAL_QUOTE, 10, self.PAGES, 23)
        assert v.verdict == SUPPORTED_ON_CITED_PAGE

    def test_within_one_page_still_counts_as_cited(self):
        v = classify(1, "marrickville", "car_parking", REAL_QUOTE, 11, self.PAGES, 23)
        assert v.verdict == SUPPORTED_ON_CITED_PAGE

    def test_found_elsewhere_reports_the_real_page_and_offset(self):
        # The measured Marrickville defect: cites 8, actually on 10.
        v = classify(1, "marrickville", "car_parking", REAL_QUOTE, 8, self.PAGES, 23)
        assert v.verdict == SUPPORTED_ELSEWHERE
        assert v.found_on_page == 10
        assert v.page_delta == 2

    def test_unsupported_when_no_page_carries_it(self):
        v = classify(1, "x", "y", "Front setback 9.9m to the primary street boundary",
                     8, self.PAGES, 23)
        assert v.verdict == UNSUPPORTED

    def test_cited_page_past_end_of_document(self):
        v = classify(1, "x", "y", REAL_QUOTE, 999, self.PAGES, 23)
        assert v.verdict == PAGE_OUT_OF_RANGE

    def test_missing_document_is_not_a_pass(self):
        v = classify(1, "x", "y", REAL_QUOTE, 10, None, None)
        assert v.verdict == DOC_UNAVAILABLE

    def test_document_without_text_layer_is_not_a_pass(self):
        v = classify(1, "x", "y", REAL_QUOTE, 1, {1: "  ", 2: ""}, 2)
        assert v.verdict == DOC_NO_TEXT

    def test_row_without_a_quote_is_not_a_pass(self):
        v = classify(1, "x", "y", None, 10, self.PAGES, 23)
        assert v.verdict == NO_QUOTE


class TestSummaryMark:
    """The mark is applied in exactly one place; these pin it."""

    @staticmethod
    def _s(verdicts: list[str]) -> Summary:
        from validate_controls_against_source_pdf import RowVerdict
        return Summary([RowVerdict(i, "l", "c", 1, v) for i, v in enumerate(verdicts)])

    def test_all_supported_passes(self):
        ok, line = self._s([SUPPORTED_ON_CITED_PAGE] * 20).verdict_line()
        assert ok, line

    def test_below_95_percent_fails(self):
        ok, line = self._s([SUPPORTED_ON_CITED_PAGE] * 18 + [UNSUPPORTED] * 2).verdict_line()
        assert not ok
        assert "FAIL" in line

    def test_could_not_check_is_excluded_from_the_denominator_not_counted_as_pass(self):
        s = self._s([SUPPORTED_ON_CITED_PAGE] * 10 + [DOC_UNAVAILABLE] * 90)
        assert len(s.checkable) == 10
        assert s.data_rate == 1.0

    def test_nothing_checkable_is_not_a_pass(self):
        ok, line = self._s([DOC_UNAVAILABLE] * 5).verdict_line()
        assert not ok
        assert "not a pass" in line

    def test_citation_rate_is_separate_from_the_data_rate(self):
        s = self._s([SUPPORTED_ON_CITED_PAGE] * 5 + [SUPPORTED_ELSEWHERE] * 5)
        assert s.data_rate == 1.0          # every control is real
        assert s.citation_rate == 0.5      # half the page references are wrong


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
