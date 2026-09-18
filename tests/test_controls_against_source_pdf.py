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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.extracted_data_integrity import TRUNCATION_LIMIT  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_controls_against_source_pdf import (  # noqa: E402
    required_values,
    strip_clause_marker,
    strip_provenance,
    DOC_NO_TEXT,
    DOC_UNAVAILABLE,
    NO_QUOTE,
    PAGE_OUT_OF_RANGE,
    SUPPORTED_ELSEWHERE,
    SUPPORTED_ON_CITED_PAGE,
    TERM_COVERAGE_MIN,
    UNSUPPORTED,
    Summary,
    classify,
    derivation_is_on_page,
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


class TestOurCitationIsNotTheCouncilsText:
    """`source_text` carries a provenance wrapper the council's page never contains.

    Measured on the 2026-09-18 run: 40 of 67 unsupported rows ended in one. It fails the
    check twice over -- the year becomes a number demanded of the page, and the citation's
    words dilute term coverage below the bar.
    """

    def test_a_trailing_citation_is_removed(self):
        assert strip_provenance("Secondary dwelling: 24m2 min width 4m "
                                "(Penrith DCP 2014 Part D2)") == \
            "Secondary dwelling: 24m2 min width 4m"

    def test_a_leading_plan_preamble_is_removed(self):
        assert strip_provenance("Ashfield DCP 2016 A-Part8 Table 2: Flats - 1 per 10 "
                                "flats") == "Flats - 1 per 10 flats"

    def test_a_parenthetical_the_COUNCIL_wrote_survives(self):
        """The negative that keeps this honest: drop this and two neighbouring table rows
        ("<800m from a station" vs ">800m") stop being distinguishable."""
        quote = "1 visitor space per 7 dwellings (sites <800m from railway station)"
        assert strip_provenance(quote) == quote

    def test_a_year_inside_our_citation_is_not_demanded_of_the_page(self):
        # leichhardt 1086 was reported unsupported for want of "2013" -- the DCP's year.
        assert "2013" not in numeric_tokens(
            strip_provenance("Leichhardt DCP 2013 Part C Section 3: soft landscape areas "
                             "must be included at the front and rear"))

    def test_an_ordinary_sentence_with_a_colon_keeps_its_subject(self):
        quote = "Seniors housing: 0.2 per unit for residents"
        assert strip_provenance(quote) == quote

    def test_a_citation_word_the_page_DOES_carry_still_counts(self):
        """Deleting the citation outright fixed 11 rows and broke 11 on the 2026-09-18
        runs: "(Table C-B)" is frequently a real column header on the cited page, so a
        rule that removes it from the quote throws away a word that was matching. Our
        words stop being REQUIRED; they never stop counting."""
        page = ("Table C-B Parking rates near transport\n"
                "0.9 spaces per 2-bedroom apartment where within 400m of a station")
        ok, coverage, _missing = page_supports(
            "0.9 spaces per 2-bedroom apartment near transport (Table C-B)", page,
            value_min=0.9, unit="spaces/dwelling")
        assert ok
        assert coverage == 1.0

    def test_our_citation_stops_costing_coverage(self):
        """penrith 1117 against its real page 40 text. Stripping the citation lifts this
        row from 50% coverage to 67%: the stored 24 is found, "secondary" and "dwelling"
        match, and the ONE word still missing is `width`, which the council wrote as
        "more than 4m wide".

        So the row is right and the check still cannot pass it. That residue is a
        word-form difference, not a value defect, and it is left visible rather than
        papered over with a stemmer -- which would loosen every other comparison in this
        file to fix a single row a human reads in five seconds.
        """
        page = ("1) The secondary dwelling must have more than 24m2 of usable private "
                "open space.\n2) The private open space area must be more than 4m wide.")
        quote = "Secondary dwelling: 24m2 min width 4m (Penrith DCP 2014 Part D2)"
        ok, coverage, missing = page_supports(quote, page, value_min=24, unit="m2")
        assert missing == []                       # the VALUE is on the page
        assert 0.60 < coverage < TERM_COVERAGE_MIN  # one word short, and it is "width"
        assert not ok
        bare, _cov_bare, _m = page_supports(quote.replace(" min width 4m", ""), page,
                                            value_min=24, unit="m2")
        assert bare                                # without that word, it passes


class TestDerivedValuesAreSupportedByTheRateOnThePage:
    """A council writes the rate; we store the quotient. Both must still be checkable.

    Every page here is the real wording from the page the row cites, read on 2026-09-18
    during the first full run -- which marked all of them unsupported because 0.143 is
    nowhere on a page that says "1 space per 7 dwellings".

    The negatives are the point: the rule must not become "a derivable value passes".
    """

    HORNSBY_PAGE = ("Sites < 800m from Railway Station Sites > 800m from Railway Station\n"
                    "0-2 Bedrooms 1 space/dwelling\n"
                    "Visitors (see Note***) 1 space per 7 dwellings 1 space per 5 dwellings")
    HORNSBY_QUOTE = "1 visitor space per 7 dwellings (sites <800m from railway station)"

    def test_a_rate_written_as_one_per_seven_supports_the_stored_quotient(self):
        ok, _cov, missing = page_supports(self.HORNSBY_QUOTE, self.HORNSBY_PAGE,
                                          value_min=0.143,
                                          unit="visitor_spaces/dwelling")
        assert ok and missing == []

    def test_the_same_quotient_is_unsupported_where_that_rate_is_not_written(self):
        """The confusable negative: 0.143 is derivable from the QUOTE on any page."""
        page = ("Sites > 800m from Railway Station\n"
                "Visitors (see Note***) 1 space per 5 dwellings")
        ok, _cov, missing = page_supports(self.HORNSBY_QUOTE, page, value_min=0.143,
                                          unit="visitor_spaces/dwelling")
        assert not ok and missing == ["0.143", "143"]

    def test_a_value_the_quote_contradicts_stays_unsupported(self):
        """waverley 635: stored 15%, quote says 50%. No rule explains it, so it fails."""
        page = "50% of the landscaped area must be deep soil zone."
        ok, _cov, missing = page_supports("50% of the landscaped area must be deep soil "
                                          "zone.", page, value_min=15, unit="%")
        assert not ok and "15" in missing

    def test_an_area_from_its_dimensions_is_supported(self):
        """marrickville 1113: 4m x 4m stored as 16 m2, and 16 is nowhere on the page."""
        page = ("A detached secondary dwelling must be provided with private open space "
                "of at least 4m x 4m accessible from a living area.")
        quote = "Secondary dwelling: minimum private open space 4m x 4m"
        assert "16" not in page
        ok, _cov, _missing = page_supports(quote, page, value_min=16, unit="m2")
        assert ok

    def test_an_abbreviated_quote_still_fails_on_WORDING_not_on_its_value(self):
        """The residue this change does NOT fix, pinned so it is not mistaken for a
        value defect: the quote says "POS", the page says "private open space", so term
        coverage falls under the bar even though 4m x 4m -> 16 is explained and present.
        Widening the term test is a separate decision with its own false-positive cost."""
        page = ("A detached secondary dwelling must be provided with private open space "
                "of at least 4m x 4m accessible from a living area.")
        ok, coverage, missing = page_supports("Secondary dwelling: min 4m x 4m POS", page,
                                              value_min=16, unit="m2")
        assert not ok
        assert missing == []          # the VALUE is accounted for
        assert coverage < 0.70        # the WORDS are what fell short

    def test_built_to_the_boundary_supports_a_nil_setback(self):
        """penrith 50: 'may be built to the rear boundary' stored as 0m, and 0 is not
        a number the page contains."""
        page = ("e) Where located above a garage facing a rear laneway, the building may "
                "be built to the rear boundary.")
        ok, _cov, _missing = page_supports(
            "Where located above a garage facing a rear laneway, the building may be "
            "built to the rear boundary.", page, value_min=0.0, unit="m")
        assert ok

    def test_a_derivation_does_not_rescue_a_page_about_something_else(self):
        """Term coverage still governs: the rate is on the page, the subject is not."""
        page = "Child care centres: 1 space per 7 children plus 1 space per 2 staff."
        ok, _cov, _missing = page_supports(self.HORNSBY_QUOTE, page, value_min=0.143,
                                           unit="visitor_spaces/dwelling")
        assert not ok

    def test_derivation_is_on_page_names_the_rule_it_used(self):
        rule = derivation_is_on_page(self.HORNSBY_QUOTE,
                                     set(numeric_tokens(self.HORNSBY_PAGE)),
                                     0.143, None, "visitor_spaces/dwelling")
        assert rule == "ratio_or_rate"

    def test_derivation_is_on_page_returns_none_when_no_rule_explains_the_value(self):
        assert derivation_is_on_page("50% of the landscaped area must be deep soil zone.",
                                     {"50"}, 15, None, "%") is None

    def test_a_rate_read_out_of_a_SEVERED_quote_does_not_support_anything(self):
        """A quote at the extractor's hard cut is not evidence either way (cumberland
        28/30: one row falsely flagged and one falsely passed, from the same cut). The
        rate rule still fires on the surviving fragment, so only the state guard rejects
        it -- without that guard a truncated quote would silently license the value."""
        quote = "1 visitor space per 7 dwellings for residential flat buildings, "
        quote = (quote * 10)[:TRUNCATION_LIMIT]
        assert len(quote) == TRUNCATION_LIMIT
        assert derivation_is_on_page(quote, {"1", "7"}, 0.143, None,
                                     "visitor_spaces/dwelling") is None
        ok, _cov, missing = page_supports(quote, "1 visitor space per 7 dwellings for "
                                                 "residential flat buildings",
                                          value_min=0.143,
                                          unit="visitor_spaces/dwelling")
        assert not ok and missing == ["0.143", "143"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
