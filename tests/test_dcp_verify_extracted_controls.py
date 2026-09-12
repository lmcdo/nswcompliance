"""The pre-insert guardrail for generated control rows.

Every test here is a way a plausible-looking regulatory number can be wrong. The
accept case is one test; the rest are refusals, because the cost of a wrong
setback served as fact is not symmetric with the cost of missing one.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_verify_extracted_controls import (  # noqa: E402
    ACCEPT, REJECT, check, normalise, numbers_in,
)

PAGE = (
    "5.2 Setbacks\n"
    "C1 The minimum front setback to a primary road is 6.5m.\n"
    "C2 The minimum building setback to a secondary road is 1.5m.\n"
    "C3 The rear setback must be no less than 3.0 metres.\n"
)


def proposal(**kw):
    base = {
        "council": "bayside", "control_type": "secondary_street_setback",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "secondary road", "section_ref": "5.2 C2",
        "source_text": "The minimum building setback to a secondary road is 1.5m.",
        "source_page": 12, "source_chapter": "part-b-residential",
    }
    base.update(kw)
    return base


class TestAccepts:
    def test_a_quote_that_is_really_there_with_its_own_number(self):
        verdict, reasons = check(proposal(), PAGE)
        assert verdict == ACCEPT, reasons

    def test_typography_does_not_cause_a_false_rejection(self):
        # pdfplumber and a retyped quote differ on dashes, quotes and spacing.
        # Rejecting a correct quote for that would train everyone to ignore this.
        verdict, _ = check(
            proposal(source_text="The  minimum building setback to a "
                                 "secondary road is 1.5m."), PAGE)
        assert verdict == ACCEPT


class TestRefuses:
    def test_a_number_that_is_on_the_page_but_NOT_in_its_own_quote(self):
        # THE CENTRAL CASE. 6.5 is genuinely on this page -- it is the FRONT
        # setback. Pairing it with the secondary-road quote is exactly how a
        # wrong control gets served with real-looking provenance, and "the number
        # is on the page" accepts it.
        verdict, reasons = check(proposal(value_min=6.5), PAGE)
        assert verdict == REJECT
        assert any("does not appear in its own quote" in r for r in reasons)

    def test_a_quote_that_is_not_on_the_cited_page(self):
        verdict, reasons = check(
            proposal(source_text="The minimum secondary setback is 1.5m in all "
                                 "residential zones."), PAGE)
        assert verdict == REJECT
        assert any("verbatim" in r for r in reasons)

    def test_a_missing_quote_or_reference(self):
        for field in ("source_text", "section_ref", "condition", "unit"):
            verdict, reasons = check(proposal(**{field: ""}), PAGE)
            assert verdict == REJECT, field
            assert any(field in r for r in reasons)

    def test_a_quote_too_short_to_be_evidence(self):
        verdict, reasons = check(proposal(source_text="is 1.5m"), PAGE)
        assert verdict == REJECT
        assert any("too short" in r for r in reasons)

    def test_an_implausible_setback_is_refused_even_if_quoted(self):
        # A clause number or a year sitting next to a unit. 2015 appears in its
        # own quote and is still not a setback.
        page = PAGE + "C4 This plan was amended in 2015 m.\n"
        verdict, reasons = check(
            proposal(value_min=2015,
                     source_text="This plan was amended in 2015 m."), page)
        assert verdict == REJECT
        assert any("plausible" in r for r in reasons)

    def test_a_non_numeric_value(self):
        verdict, reasons = check(proposal(value_min="three point five"), PAGE)
        assert verdict == REJECT

    def test_value_max_is_checked_as_well_as_value_min(self):
        verdict, reasons = check(proposal(value_max=9.9), PAGE)
        assert verdict == REJECT
        assert any("value_max" in r for r in reasons)


class TestHelpers:
    def test_number_normalisation_makes_3_50_equal_3_5(self):
        assert numbers_in("3.50 and 3.5 and 3") == {"3.5", "3"}

    def test_normalise_folds_typography_not_content(self):
        assert normalise("a\u2013b  c") == normalise("a-b c")
        assert normalise("1.5m") != normalise("15m")


class TestMutationResistance:
    def test_the_verifier_does_not_accept_everything(self):
        assert check(proposal(value_min=6.5), PAGE)[0] == REJECT

    def test_the_verifier_does_not_reject_everything(self):
        assert check(proposal(), PAGE)[0] == ACCEPT


class TestAmbiguousQuotes:
    """One quote supporting two different answers is the limit of a per-row test."""

    def _p(self, vmin, ref, quote):
        return proposal(value_min=vmin, section_ref=ref, source_text=quote)

    def test_two_values_from_one_quote_are_surfaced(self):
        from scripts.dcp_verify_extracted_controls import ambiguous_quotes
        # The real hornsby Pound Road case: an interleaved table cell that
        # genuinely contains both 4 and 7.5, quoted identically for both rows.
        q = ("Primary and 4m, plus Secondary Road any ground floor commercial "
             "premises should be setback behind a colonnade that has a minimum "
             "depth of 3.5m (i.e. min setback of 7.5m to the road boundary)")
        out = ambiguous_quotes([self._p(4, "podium", q), self._p(7.5, "colonnade", q)])
        assert len(out) == 1
        assert {str(g["value_min"]) for g in list(out.values())[0]} == {"4", "7.5"}

    def test_the_same_value_quoted_twice_is_NOT_ambiguous(self):
        from scripts.dcp_verify_extracted_controls import ambiguous_quotes
        # Wingecarribee states the identical clause in all three town plans.
        # That is repetition, not ambiguity, and must not be flagged.
        q = "On corner lots a 3m setback applies to the secondary frontage."
        assert ambiguous_quotes([self._p(3, "bowral", q), self._p(3, "mittagong", q)]) == {}

    def test_distinct_quotes_are_never_ambiguous(self):
        from scripts.dcp_verify_extracted_controls import ambiguous_quotes
        assert ambiguous_quotes([
            self._p(3, "a", "A 3m setback applies to the secondary frontage here."),
            self._p(6, "b", "A 6m setback applies to the secondary frontage there."),
        ]) == {}
