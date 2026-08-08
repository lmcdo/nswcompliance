"""Tests for scripts/measure_control_quote_gap.py.

The point of this script is that a WRONG number here would relaunch the false
"the chapter wasn't loaded" explanation it exists to retract, so each pure
function is tested at both ends: the case that must score high AND the case that
must score low. A function that always returned the same band would pass neither.
"""
import importlib.util
import os
import sys

import pytest

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scripts", "measure_control_quote_gap.py")
_spec = importlib.util.spec_from_file_location("measure_control_quote_gap", _PATH)
mcqg = importlib.util.module_from_spec(_spec)
sys.modules["measure_control_quote_gap"] = mcqg
_spec.loader.exec_module(mcqg)


class TestQuotedClause:
    def test_strips_the_trailing_document_citation(self):
        # The extractors append this; it is not in the provision, so leaving it on
        # would fail matches for the wrong reason and overstate the ceiling.
        assert mcqg.quoted_clause(
            "Minimum 35% of site area as landscaped area (Ashfield DCP 2016 DS18.5)"
        ) == "minimum 35% of site area as landscaped area"

    def test_keeps_a_parenthetical_that_is_part_of_the_rule(self):
        text = "Side setback 900mm (excluding eaves)"
        assert mcqg.quoted_clause(text) == "side setback 900mm (excluding eaves)"

    def test_none_and_empty_do_not_raise(self):
        assert mcqg.quoted_clause(None) == ""
        assert mcqg.quoted_clause("   ") == ""


class TestLongestRunFraction:
    def test_identical_text_scores_one(self):
        q = "the minimum side setback is 900mm"
        assert mcqg.longest_run_fraction(q, mcqg.words(q)) == 1.0

    def test_disjoint_text_scores_zero(self):
        assert mcqg.longest_run_fraction(
            "the minimum side setback is 900mm",
            mcqg.words("bicycle parking shall be provided in a communal area"),
        ) == 0.0

    def test_a_quote_embedded_in_a_longer_provision_still_scores_one(self):
        # The real recovery case: the sentence IS in the corpus, the substring
        # match failed only on punctuation elsewhere in the provision.
        q = "the minimum side setback is 900mm"
        provision = mcqg.words(
            "objectives of this control are as follows the minimum side setback "
            "is 900mm measured from the boundary")
        assert mcqg.longest_run_fraction(q, provision) == 1.0

    def test_shared_words_out_of_order_do_not_score_high(self):
        # This is the failure the discarded set-overlap metric had: every word of
        # the quote is present, but no contiguous run is, so it must NOT read as
        # verbatim.
        q = "setback minimum side 900mm dwelling"
        provision = mcqg.words(
            "dwelling a b c 900mm d e f side g h i minimum j k l setback")
        assert mcqg.longest_run_fraction(q, provision) < 0.4

    def test_empty_inputs_score_zero_rather_than_dividing_by_zero(self):
        assert mcqg.longest_run_fraction("", mcqg.words("anything")) == 0.0
        assert mcqg.longest_run_fraction("anything", []) == 0.0


class TestBandFor:
    @pytest.mark.parametrize("fraction,expected", [
        (1.0, "verbatim_present_substring_failed_on_punctuation"),
        (0.8, "verbatim_present_substring_failed_on_punctuation"),
        (0.79, "partly_verbatim"),
        (0.4, "partly_verbatim"),
        (0.39, "fragmentary"),
        (0.2, "fragmentary"),
        (0.19, "not_present_in_any_recognisable_form"),
        (0.0, "not_present_in_any_recognisable_form"),
    ])
    def test_boundaries(self, fraction, expected):
        assert mcqg.band_for(fraction) == expected

    def test_every_band_is_reachable(self):
        # A banding function that collapsed to one label would still pass any
        # single-case test; this asserts all four are distinct and produced.
        produced = {mcqg.band_for(f) for f in (1.0, 0.6, 0.3, 0.05)}
        assert len(produced) == 4


class TestChapterTokens:
    def test_control_key_and_document_id_reduce_to_a_comparable_set(self):
        key = mcqg.chapter_tokens("chapter-f-dev-category")
        doc = mcqg.chapter_tokens("Inner_West_Ashfield_DCP_2016__chapter_f_dev_category")
        # Subset, not equality: the document id carries the council name too.
        assert key <= doc

    def test_a_different_chapter_is_not_a_subset(self):
        key = mcqg.chapter_tokens("chapter-b-public-domain")
        doc = mcqg.chapter_tokens("Inner_West_Ashfield_DCP_2016__chapter_f_dev_category")
        assert not key <= doc

    def test_year_and_instrument_noise_is_stripped(self):
        assert mcqg.chapter_tokens("woollahra-dcp-2015-chapter-b3") == {
            "woollahra", "chapter", "b3"}

    def test_empty_key_yields_an_empty_set_not_a_false_match(self):
        # An empty set is a subset of everything, so the caller must treat it as
        # "untestable" rather than "ingested". Guarding the value here documents
        # why measure() branches on `not key_tokens` FIRST.
        assert mcqg.chapter_tokens(None) == set()
        assert mcqg.chapter_tokens("") == set()
        assert set() <= mcqg.chapter_tokens("anything")
