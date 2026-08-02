"""Tests for the named derivation rules behind validate_control_source_values.py.

The dangerous direction here is a FALSE EXPLANATION: a rule that fires on a row
whose stored number its quote does not support turns a real defect into a silent
pass, and the row disappears from the finding list forever. So every rule is
tested twice — once on the derivation it is meant to name, and once on a case it
must REFUSE. A rule that always returned evidence would fail the refusal tests;
a rule that always returned None would fail the derivation tests. Neither
direction alone would catch a broken rule.
"""
import pytest

from services.extracted_data_integrity import (
    FAILING_STATES,
    MISSING_SOURCE_TEXT,
    NO_VALUE_STORED,
    RULE_NAMES,
    TRUNCATED_EVIDENCE,
    UNEXPLAINED,
    explain_row,
    explain_value,
    evidence_is_truncated,
    fabricated_values,
)


def rule_of(value, text, unit=None):
    return explain_value(value, text, unit)[0]


def evidence_of(value, text, unit=None):
    return explain_value(value, text, unit)[1]


class TestExactDigitMatch:
    def test_the_number_is_in_the_quote(self):
        assert rule_of(6, "Front setback minimum 6m") == "exact_digit_match"

    def test_decimal_written_the_same_way(self):
        assert rule_of(0.9, "Minimum side setback of 0.9 metres") == "exact_digit_match"

    def test_a_number_at_the_end_of_a_sentence_still_matches(self):
        # Regression: an over-tight lookahead rejected "up to 3." and silently
        # un-explained rows that were fine.
        assert rule_of(3, "Maximum: up to 3.") == "exact_digit_match"

    def test_five_is_not_found_inside_fifteen(self):
        # A substring test would call this explained. It compares numeric tokens
        # precisely so that it cannot.
        assert rule_of(5, "A setback of 15 metres applies") == UNEXPLAINED

    def test_a_clause_reference_does_not_explain_a_value(self):
        # 's4.3.6' must not let a stored 4.3 explain itself by its own citation.
        assert rule_of(4.3, "s4.3.6: Walls minimum 900mm from side boundaries") \
            != "exact_digit_match"

    def test_a_spaced_clause_label_is_also_a_citation(self):
        # The lookbehind only catches a label glued to the number ('s4.3.6'). A
        # labelled number with a space survived, so 'Clause 4.3: minimum setback
        # is 6m' explained a stored 4.3 — the citation vouching for the value it
        # is supposed to be evidence against.
        assert rule_of(4.3, "Clause 4.3: minimum setback is 6m", "m") == UNEXPLAINED
        assert rule_of(6, "Clause 4.3: minimum setback is 6m", "m") \
            == "exact_digit_match"

    @pytest.mark.parametrize("label", ["Part", "Table", "Control", "Figure",
                                       "Objective", "Section", "Schedule"])
    def test_every_citation_label_is_excluded(self, label):
        assert rule_of(7, f"{label} 7 sets out the following controls", "m") \
            == UNEXPLAINED

    def test_a_numbered_list_ordinal_does_not_explain_a_value(self):
        # Camden control 693: a front_setback of 2.0 m was "explained" by the '2'
        # of a list item, in a clause about front FENCE height. A long quote
        # listing points 1., 2., 3. will contain almost any small stored value,
        # which makes ordinals the largest false-pass channel in the check.
        text = ("1. Front fencing must have a maximum height of 1.2m above ground "
                "level.\n2. Front fences and walls are not to impede safe sight "
                "lines for traffic.")
        assert rule_of(2.0, text, "m") == UNEXPLAINED

    def test_a_real_quantity_beside_an_ordinal_still_matches(self):
        # The exclusion must remove the ordinal only — not the numbers around it,
        # or it would manufacture findings out of correct rows.
        text = "1. The minimum front setback is 6m."
        assert rule_of(6, text, "m") == "exact_digit_match"

    def test_a_table_cell_number_is_not_mistaken_for_an_ordinal(self):
        assert rule_of(6, "|  Front Setback | 6 | applies to primary frontage", "m") \
            == "exact_digit_match"

    def test_a_quantity_labelled_as_another_kind_of_thing_does_not_explain_it(self):
        # "a minimum of 3 hours of sunlight" must not explain a 3 METRE setback.
        # The number matches; the text says what it measures, and it is not this.
        assert rule_of(3, "a minimum of 3 hours of sunlight to living areas", "m") \
            == UNEXPLAINED

    def test_an_unlabelled_quantity_is_never_rejected_on_a_guess(self):
        # The guard needs BOTH sides. A number the text does not label must still
        # match — inventing findings is the mirror of inventing passes.
        assert rule_of(3, "a minimum of 3 to the boundary", "m") == "exact_digit_match"
        assert rule_of(3, "a minimum of 3 in total", None) == "exact_digit_match"

    def test_a_parking_column_is_recognised_and_rejects_a_time_quantity(self):
        # 'spaces/dwelling' used to fall outside the stored-unit map, so it was
        # treated as unknown and a quote about hours explained a parking rate.
        # 450+ rows carry a 'spaces/...' unit, so this was the largest blind spot.
        assert rule_of(3, "a minimum of 3 hours of sunlight", "spaces/dwelling") \
            == UNEXPLAINED

    def test_a_parking_column_still_accepts_counted_nouns(self):
        # 'rate' and 'count' are deliberately compatible: a spaces/dwelling value
        # is genuinely written as "2 spaces per dwelling", so a counted noun beside
        # it is the expected phrasing, not a conflict.
        assert rule_of(2, "2 spaces per dwelling are required", "spaces/dwelling") \
            == "exact_digit_match"

    def test_a_matching_unit_family_still_explains_the_value(self):
        assert rule_of(6, "a minimum front setback of 6 metres", "m") \
            == "exact_digit_match"

    def test_a_near_miss_is_not_a_match(self):
        # No rounding tolerance on exact matching: 0.899 and 0.9 are different
        # numbers and accepting one for the other would swallow a typo.
        assert rule_of(0.9, "a setback of 0.899 metres") == UNEXPLAINED


class TestPercentagePhrasing:
    def test_a_percentage_stored_as_a_fraction(self):
        assert rule_of(0.35, "Minimum 35% of the site as landscaped area", "%") \
            == "percentage_phrasing"

    def test_a_percentage_does_not_explain_a_length(self):
        # Without a unit gate, "Minimum 35% landscaped area" explained a 0.35
        # METRE setback — the arithmetic works and the meaning does not.
        assert rule_of(0.35, "Minimum 35% landscaped area", "m") == UNEXPLAINED

    def test_a_percentage_stored_as_written_takes_the_exact_rule_first(self):
        # Ordering matters: this is a literal match, not a conversion, and the
        # reported state should say so.
        assert rule_of(35, "Minimum 35% of the site") == "exact_digit_match"

    def test_a_bare_number_is_never_read_as_a_percentage(self):
        # Without the literal '%', dividing 3500 by 100 to reach 35 would be an
        # arithmetic coincidence presented as provenance.
        assert rule_of(35, "A floor area of 3500 square metres") == UNEXPLAINED

    def test_a_quoted_percentage_is_never_multiplied_up(self):
        # The rule once accepted pct * 100 as well, so a quoted 35% explained a
        # stored 3500. Nobody stores a percentage that way; that direction existed
        # only to manufacture matches.
        assert rule_of(3500, "Minimum 35% landscaped area") == UNEXPLAINED


class TestUnitConversion:
    def test_millimetres_stored_as_metres(self):
        assert rule_of(0.9, "Minimum side setback is 900mm", "m") == "unit_conversion"

    def test_centimetres_stored_as_metres(self):
        assert rule_of(0.45, "a 45 cm projection is permitted", "m") == "unit_conversion"

    def test_the_evidence_names_the_conversion(self):
        assert "900mm" in evidence_of(0.9, "setback is 900mm", "m")

    def test_a_bare_number_is_not_treated_as_millimetres(self):
        assert rule_of(0.9, "control 900 applies to this lot", "m") == UNEXPLAINED

    def test_it_does_not_convert_into_an_area_column(self):
        # 'm2' was allowed alongside 'm', so a quoted 900mm explained a 0.9 SQUARE
        # metre value — a different kind of thing.
        assert rule_of(0.9, "a setback of 900mm applies", "m2") == UNEXPLAINED

    def test_it_does_not_convert_into_an_unlabelled_column(self):
        # A conversion is a claim about what the number measures; 49 rows carry no
        # unit, and assuming metres for them would be that claim made up.
        assert rule_of(0.9, "a setback of 900mm applies", None) == UNEXPLAINED

    def test_it_converts_in_one_direction_only(self):
        # Dividing BY the factor was also accepted once, so a quoted "0.9mm"
        # explained a stored 900 m. Nothing is quoted in millimetres and stored
        # in kilometres.
        assert rule_of(900, "minimum setback 0.9mm", "m") == UNEXPLAINED

    def test_it_does_not_fire_on_a_parking_rate(self):
        # Converting a value whose column says 'spaces/dwelling' into metres is
        # nonsense; the rule refuses rather than producing a tidy wrong answer.
        assert rule_of(0.9, "900mm setback", "spaces/dwelling") != "unit_conversion"


class TestRatioOrRate:
    def test_one_space_per_four_dwellings(self):
        assert rule_of(0.25, "1 visitor space per 4 dwellings") == "ratio_or_rate"

    def test_one_third_rounded_as_stored(self):
        assert rule_of(0.333, "1 space per 3 dwellings") == "ratio_or_rate"

    def test_for_every_is_the_same_rate(self):
        assert rule_of(0.25, "1 space for every 4 dwellings") == "ratio_or_rate"

    def test_per_every_is_the_same_rate(self):
        assert rule_of(0.2, "1 space per every 5 dwellings, or part thereof") \
            == "ratio_or_rate"

    def test_a_numerator_far_from_its_per_is_still_found(self):
        assert rule_of(0.333, "One (1) external additional visitor car parking space "
                              "shall be provided for every three (3) units") \
            == "ratio_or_rate"

    def test_a_leading_clause_reference_does_not_hijack_the_numerator(self):
        # Regression: a single leftmost-first regex locked onto 9.2 from 'DS9.2'
        # and the row lost the explanation it genuinely had.
        assert rule_of(0.25, "DS9.2 Parking for visitors is provided at the rate of "
                             "1 space for every 4 dwellings") == "ratio_or_rate"

    def test_a_rate_that_does_not_produce_the_stored_value_is_unexplained(self):
        # The text says 0.4. Storing 0.2 must NOT be explained by inventing a
        # different numerator.
        assert rule_of(0.2, "2 visitor spaces per 5 dwellings") == UNEXPLAINED

    def test_a_parking_rate_does_not_explain_a_setback(self):
        # A row whose source_text was attached to the wrong control: the quote is
        # a parking rate, the column is metres. 0.25 is derivable from the text
        # and means nothing about a setback.
        assert rule_of(0.25, "1 visitor space per 4 dwellings", "m") == UNEXPLAINED

    def test_a_number_across_a_sentence_break_is_not_a_numerator(self):
        assert rule_of(0.5, "A total of 2 storeys. Parking per 4 dwellings applies") \
            == UNEXPLAINED

    def test_a_decimal_numerator_survives_the_sentence_break_cut(self):
        # Cutting the lead-in on a bare "." split decimals: "0.5 spaces per 4
        # dwellings" left "5 spaces" and produced 5/4, so a stored 1.25 passed
        # against a quote stating 0.125.
        assert rule_of(1.25, "0.5 spaces per 4 dwellings", "spaces/dwelling") \
            == UNEXPLAINED
        assert rule_of(0.125, "0.5 spaces per 4 dwellings", "spaces/dwelling") \
            == "ratio_or_rate"

    def test_a_rate_is_not_assembled_from_two_unrelated_clauses(self):
        # Offering every number in the lead-in as a numerator let 6/4 explain a
        # stored 1.5 here, when the rate the text states is 0.25. Only the number
        # immediately before the 'per' can be its numerator.
        assert rule_of(1.5, "Minimum setback 6m and provide 1 space per 4 dwellings") \
            == UNEXPLAINED

    def test_a_rate_five_times_too_large_is_not_within_tolerance(self):
        # Sol finding, verified: a flat 0.005 absolute tolerance swallowed this.
        # 1/1000 is 0.001; a stored 0.005 is five times that and must not pass.
        assert rule_of(0.005, "1 space per 1000 dwellings") == UNEXPLAINED

    def test_two_decimal_rounding_is_accepted(self):
        # The table stores 2/3 as 0.67 and 1/3 as both 0.33 and 0.333, so the
        # tolerance comes from the stored value's own precision. A flat tolerance
        # tight enough for the case above rejected both of these real rows.
        assert rule_of(0.67, "2 spaces per 3 self-contained units") == "ratio_or_rate"
        assert rule_of(0.33, "Minimum 1 space per 3 dwellings") == "ratio_or_rate"

    def test_three_decimal_rounding_is_also_accepted(self):
        assert rule_of(0.333, "1 space per 3 dwellings") == "ratio_or_rate"
        assert rule_of(0.091, "visitor min 1 per 11 dwellings") == "ratio_or_rate"

    def test_a_whole_number_cannot_absorb_a_large_absolute_gap(self):
        # Half of the last decimal place of a whole number is 0.5, which alone
        # would let a derived 5.6 explain a stored 6. The relative bound stops it.
        assert rule_of(6, "28 spaces per 5 dwellings") == UNEXPLAINED

    def test_a_whole_number_must_match_its_derivation_exactly(self):
        # 24/25 is 0.96. Rounding that up to a stored 1 is a judgement someone
        # made, not a derivation the text states. All five whole-number derived
        # rows in the live table are exact products, so requiring exactness here
        # costs nothing.
        assert rule_of(1, "24 spaces per 25 dwellings", "spaces/dwelling") \
            == UNEXPLAINED
        assert rule_of(9, "3m x 3m private open space", "m2") \
            == "area_from_dimensions"


class TestImpliedSingleUnitRate:
    def test_an_unwritten_numerator_of_one(self):
        assert rule_of(0.25, "An additional car parking space for every 4 dwellings") \
            == "implied_single_unit_rate"

    def test_it_refuses_when_a_numerator_was_written(self):
        # This is the rule's whole risk: '2 spaces per 5' stored as 0.2 must stay
        # a finding, not become 1/5.
        assert rule_of(0.2, "2 spaces per 5 dwellings") == UNEXPLAINED

    def test_the_implied_one_must_actually_be_written_as_something(self):
        # "An additional car parking SPACE for every 4 dwellings" says one space.
        # "Visitor parking must be considered for every 4 dwellings" states no
        # quantity at all, and deriving 1/4 from it invents the numerator.
        assert rule_of(0.25, "Visitor parking must be considered for every 4 "
                             "dwellings", "spaces/dwelling") == UNEXPLAINED


class TestFractionLiteral:
    def test_a_fraction_written_as_a_fraction(self):
        assert rule_of(0.333, "Leichhardt DCP Table C4: 1 bed min 1/3") \
            == "fraction_literal"

    def test_an_awkward_fraction_within_rounding(self):
        assert rule_of(0.091, "visitor min 1/11, max 0.125/dwelling") \
            == "fraction_literal"

    def test_an_unrelated_fraction_does_not_explain_a_different_value(self):
        assert rule_of(0.75, "visitor min 1/11 per dwelling") == UNEXPLAINED

    def test_a_fraction_does_not_explain_a_setback(self):
        # Same class as the rate rules: a landscaping fraction must not vouch for
        # a value stored in metres on a row with the wrong source_text attached.
        assert rule_of(0.333, "At least 1/3 of the landscaped area must be deep "
                              "soil", "m") == UNEXPLAINED


class TestAreaFromDimensions:
    def test_dimensions_stored_as_their_product(self):
        assert rule_of(9, "3m x 3m private open space", "m2") == "area_from_dimensions"

    def test_the_product_must_actually_equal_the_stored_value(self):
        assert rule_of(12, "3m x 3m private open space", "m2") == UNEXPLAINED

    def test_it_refuses_when_the_stored_unit_is_not_an_area(self):
        # Sol finding, verified: without the unit gate, '9' in a spaces/dwelling
        # column is explained by a 3m x 3m parking bay — an area the row is not
        # measuring.
        assert rule_of(9, "Provide a 3m x 3m parking area", "spaces/dwelling") \
            == UNEXPLAINED


class TestWrittenNumeral:
    def test_a_spelled_out_number(self):
        assert rule_of(1, "provided with a minimum of one car parking space") \
            == "written_numeral"

    def test_nil(self):
        assert rule_of(0, "Nil parking space required for secondary dwellings") \
            in ("written_numeral", "explicit_nil_requirement")

    def test_a_written_numeral_that_is_not_the_stored_value(self):
        assert rule_of(4, "a minimum of three hours of sunlight") == UNEXPLAINED

    def test_a_numeral_that_is_not_counting_anything_does_not_explain_a_value(self):
        # Sol finding, verified: 'one' is an ordinary English word. Without
        # requiring it to count something, an objective's number explains a
        # setback the clause contradicts.
        assert rule_of(1, "Objective one: provide a minimum 6m front setback", "m") \
            == UNEXPLAINED

    def test_a_word_between_the_numeral_and_its_noun_does_not_defeat_the_guard(self):
        # "three full hours" put 'full' where the unit scan looked, so the
        # conflict went undetected and a 3 METRE setback was explained by a
        # sunlight requirement. The guard reads the noun the rule matched.
        assert rule_of(3, "a minimum of three full hours of sunlight", "m") \
            == UNEXPLAINED

    def test_a_numeral_counting_something_still_explains_it(self):
        assert rule_of(1, "provided with a minimum of one single garage") \
            == "written_numeral"
        assert rule_of(3, "a minimum of three hours of direct sunlight", "hours") \
            == "written_numeral"


class TestExplicitNilRequirement:
    def test_no_additional_parking_is_required(self):
        assert rule_of(0, "Secondary dwellings: no additional parking is required") \
            == "explicit_nil_requirement"

    def test_a_map_being_silent_is_not_a_control_of_zero(self):
        # City of Sydney: 'where no front setback is shown on the map' says the map
        # is silent, NOT that the setback is zero. Explaining a stored 0 from this
        # would invent a control out of a sentence about cartography.
        assert rule_of(0, "Front setbacks are to be consistent with the Building "
                          "setbacks map. Where no front setback is shown on the map, "
                          "the setback is to match adjoining development.") \
            == UNEXPLAINED


class TestBuiltToBoundary:
    def test_built_to_the_rear_boundary_is_a_setback_of_zero(self):
        assert rule_of(0.0, "Where located above a garage facing a rear laneway, the "
                            "building may be built to the rear boundary.", "m") \
            == "built_to_boundary_zero"

    def test_it_does_not_explain_a_non_zero_setback(self):
        assert rule_of(3.0, "the building may be built to the rear boundary", "m") \
            == UNEXPLAINED


class TestExplainValueEdges:
    def test_a_missing_value_is_not_a_pass(self):
        # 83 real rows record a rule with no number. They must be their own state:
        # counting them as explained would inflate the pass rate by 8%.
        assert rule_of(None, "any text") == NO_VALUE_STORED

    def test_a_number_with_no_quote_at_all_is_a_failure_not_a_skip(self):
        # Sol finding, verified: this used to return NO_VALUE_STORED, so a served
        # number with nothing behind it would pass as "nothing to check". No row
        # is in this state today (0 of 1,069) — which is precisely why it needs
        # one, or the check waves through the first row that appears in it.
        assert explain_value(5, "")[0] == MISSING_SOURCE_TEXT
        assert explain_value(5, None)[0] == MISSING_SOURCE_TEXT
        assert explain_value(5, "   ")[0] == MISSING_SOURCE_TEXT

    def test_missing_source_text_is_a_failing_state(self):
        assert MISSING_SOURCE_TEXT in FAILING_STATES
        assert NO_VALUE_STORED not in FAILING_STATES

    def test_a_non_numeric_value_is_not_checked(self):
        assert rule_of("see clause", "some text") == NO_VALUE_STORED

    def test_nan_and_infinity_are_findings_not_matches(self):
        # Postgres numeric accepts NaN, and every comparison against NaN is False
        # — so the exact rule's "skip if not equal" test was itself False and a
        # NaN row fell through into an explained verdict.
        assert rule_of(float("nan"), "minimum setback 6m", "m") == UNEXPLAINED
        assert rule_of(float("inf"), "minimum setback 6m", "m") == UNEXPLAINED

    def test_every_explained_row_carries_evidence(self):
        # An explanation without the substring it used is a shrug with a name on
        # it, and could never be audited.
        for value, text, unit in [
            (6, "minimum 6m", "m"),
            (0.9, "900mm setback", "m"),
            (0.25, "1 space per 4 dwellings", "spaces/dwelling"),
            (9, "3m x 3m", "m2"),
            (1, "one car space", "spaces/dwelling"),
        ]:
            name, evidence = explain_value(value, text, unit)
            assert name != UNEXPLAINED
            assert evidence, f"{name} explained {value} without evidence"


class TestExplainRow:
    def test_both_ends_of_a_range_must_be_explained(self):
        row = {"value_min": 3, "value_max": 8, "source_text": "a minimum of 3 metres",
               "unit": "m"}
        # 8 is nowhere in the quote, so the row is unexplained even though min is.
        assert explain_row(row, value_fields=["value_min", "value_max"],
                           source_field="source_text",
                           unit_field="unit")["state"] == UNEXPLAINED

    def test_the_row_state_is_the_most_derived_rule_it_needed(self):
        row = {"value_min": 0.9, "value_max": 3, "unit": "m",
               "source_text": "minimum 900mm side and 3m rear boundary setback"}
        # max=3 is exact, min=0.9 needed a conversion. Reporting 'exact' would
        # overstate how directly this row is supported.
        assert explain_row(row, value_fields=["value_min", "value_max"],
                           source_field="source_text",
                           unit_field="unit")["state"] == "unit_conversion"

    def test_a_row_with_no_values_is_its_own_state(self):
        row = {"value_min": None, "value_max": None, "unit": None,
               "source_text": "the control is qualitative"}
        assert explain_row(row, value_fields=["value_min", "value_max"],
                           source_field="source_text",
                           unit_field="unit")["state"] == NO_VALUE_STORED

    def test_a_number_with_no_quote_makes_the_whole_row_fail(self):
        row = {"value_min": 5, "value_max": None, "unit": "m", "source_text": ""}
        assert explain_row(row, value_fields=["value_min", "value_max"],
                           source_field="source_text",
                           unit_field="unit")["state"] == MISSING_SOURCE_TEXT

    def test_an_exact_match_against_a_single_quantity_is_uniquely_attributable(self):
        row = {"value_min": 6, "value_max": None, "unit": "m",
               "source_text": "The minimum front setback is 6m."}
        result = explain_row(row, value_fields=["value_min", "value_max"],
                            source_field="source_text", unit_field="unit")
        assert result["uniquely_attributable"] is True
        assert result["quote_quantity_count"] == 1

    def test_an_exact_match_among_several_quantities_is_flagged_as_not_pinned(self):
        # Sol finding, verified and measured: 571 of 839 exact matches (68.1%) are
        # in this state. The stored value appears in its source, but so do others,
        # so 'exact_digit_match' must not read as stronger evidence than it is.
        row = {"value_min": 6, "value_max": None, "unit": "m",
               "source_text": "Maximum building height 6m; minimum front setback 4m."}
        result = explain_row(row, value_fields=["value_min", "value_max"],
                            source_field="source_text", unit_field="unit")
        assert result["state"] == "exact_digit_match"
        assert result["uniquely_attributable"] is False
        assert result["quote_quantity_count"] == 2

    def test_per_field_results_are_reported_not_just_the_state(self):
        row = {"value_min": 0.9, "value_max": None, "unit": "m",
               "source_text": "minimum 900mm"}
        result = explain_row(row, value_fields=["value_min", "value_max"],
                            source_field="source_text", unit_field="unit")
        assert result["fields"]["value_min"]["rule"] == "unit_conversion"
        assert result["fields"]["value_max"]["rule"] == NO_VALUE_STORED


class TestTruncatedEvidence:
    """A severed quote is not evidence either way.

    23 rows carry a source_text of exactly 400 characters, every one ending
    mid-word. Both failure directions were observed in one council: cumberland 30
    (rear 8m, CORRECT) was falsely FLAGGED because 'Minimum 8m' fell outside the
    cut, and cumberland 28 (front 6m, served) falsely PASSED because 'Minimum 6m'
    happened to fall inside it. Which way a truncated row lands is luck.
    """

    def test_a_quote_cut_at_the_limit_mid_word_is_truncated(self):
        assert evidence_is_truncated("x" * 399 + "a")

    def test_a_quote_at_the_limit_is_truncated_even_ending_in_punctuation(self):
        # A cut can land immediately AFTER punctuation, so a terminal '.' at
        # the cap separates nothing: at exactly the extractor limit a complete
        # quote is indistinguishable from a severed one, and evidence that
        # cannot be told from severed evidence is not evidence. (The prior
        # punctuation exemption let exactly this shape be judged on a cut
        # quote.)
        assert evidence_is_truncated("x" * 399 + ".")

    def test_a_short_quote_is_never_truncated(self):
        assert not evidence_is_truncated("Front setback minimum 6m.")
        assert not evidence_is_truncated(None)
        assert not evidence_is_truncated("")

    def test_truncation_beats_a_rule_that_would_otherwise_fire(self):
        # The whole point: cumberland 28 stores 6.0 and its severed quote DOES
        # contain '6m', so exact_digit_match would fire. It must not — the number
        # surviving the cut is luck, not verification.
        quote = ("|  Setbacks  |   |\n|  Front Setback (primary frontage) | "
                 "Minimum 6m\nDwelling house shall align with the street")
        quote = quote + "x" * (400 - len(quote) - 1) + "r"
        assert len(quote) == 400
        row = {"value_min": 6.0, "value_max": None, "unit": "m",
               "source_text": quote}
        result = explain_row(row, value_fields=["value_min", "value_max"],
                             source_field="source_text", unit_field="unit")
        assert result["state"] == TRUNCATED_EVIDENCE

    def test_truncated_evidence_is_a_failing_state(self):
        assert TRUNCATED_EVIDENCE in FAILING_STATES

    def test_a_row_with_no_value_is_still_no_value_stored(self):
        # Ordering: nothing to check outranks can't-check-it. Otherwise 83 rows
        # that legitimately hold no number would be reported as unverifiable.
        row = {"value_min": None, "value_max": None, "unit": None,
               "source_text": "x" * 399 + "a"}
        result = explain_row(row, value_fields=["value_min", "value_max"],
                             source_field="source_text", unit_field="unit")
        assert result["state"] == NO_VALUE_STORED


class TestFabricationGate:
    """The gate that blocks a value whose own note admits it was assumed.

    All 28 such rows in the live table are already is_current=FALSE, so this
    passes today. It exists to stop the 29th being SERVED — which is why every
    test here drives the served/not-served distinction, not just the marker.
    """

    MARKERS = ["condition", "review_reason", "source_text"]

    def _assumed_row(self, **over):
        row = {"id": 1, "value_min": 24, "value_max": None,
               "source_text": "DCP s2.8 Private Open Space exists",
               "condition": "Assumed standard NSW POS min - verify against DCP",
               "review_reason": None, "is_current": True}
        row.update(over)
        return row

    def test_it_fires_on_a_value_whose_note_says_assumed(self):
        assert fabricated_values([self._assumed_row()], value_field="value_min",
                                 marker_fields=self.MARKERS)

    def test_it_does_not_fire_on_a_row_that_cites_a_real_clause(self):
        row = self._assumed_row(condition="Read from Table 1 page B8")
        assert not fabricated_values([row], value_field="value_min",
                                     marker_fields=self.MARKERS)

    def test_a_null_value_with_an_honest_note_is_clean(self):
        # This is the FIXED state the doctrine asks for: the rule exists, the
        # value is unknown, and the row says so. It must not be flagged, or the
        # gate would punish the correct response to its own finding.
        row = self._assumed_row(value_min=None, value_max=None)
        assert not fabricated_values([row], value_field="value_min",
                                     marker_fields=self.MARKERS)

    def test_the_marker_reads_review_reason_and_source_text_too(self):
        # A writer confesses wherever there is room. Reading only `condition`
        # would miss it.
        for field in ("review_reason", "source_text"):
            row = self._assumed_row(condition=None,
                                    **{field: "standard NSW pattern assumed"})
            assert fabricated_values([row], value_field="value_min",
                                     marker_fields=self.MARKERS), field

    def test_a_max_only_row_is_still_caught(self):
        # The gate checks value_min AND value_max; a row carrying only an upper
        # bound is just as fabricated.
        row = self._assumed_row(value_min=None, value_max=24)
        assert not fabricated_values([row], value_field="value_min",
                                     marker_fields=self.MARKERS)
        assert fabricated_values([row], value_field="value_max",
                                 marker_fields=self.MARKERS)


class TestStatesAreExhaustive:
    @pytest.mark.parametrize("value,text,unit", [
        (6, "minimum 6m", "m"),
        (0.35, "35% landscaped", "%"),
        (0.9, "900mm", "m"),
        (0.333, "min 1/3", "spaces/dwelling"),
        (0.25, "1 space per 4 dwellings", "spaces/dwelling"),
        (0.25, "a space for every 4 dwellings", "spaces/dwelling"),
        (9, "3m x 3m", "m2"),
        (3, "three hours", "hours"),
        (0, "no additional parking is required", "spaces/dwelling"),
        (0.0, "may be built to the rear boundary", "m"),
        (5.5, "no numbers here at all", "m"),
        (None, "anything", None),
    ])
    def test_every_input_lands_in_a_known_state(self, value, text, unit):
        assert rule_of(value, text, unit) in (*RULE_NAMES, UNEXPLAINED, NO_VALUE_STORED)

    def test_every_named_rule_is_reachable(self):
        # A rule that no input can reach is dead code presenting as coverage.
        reached = {
            rule_of(6, "minimum 6m", "m"),
            rule_of(0.35, "35% landscaped", "%"),
            rule_of(0.9, "900mm", "m"),
            rule_of(0.333, "min 1/3", "spaces/dwelling"),
            rule_of(0.25, "1 space per 4 dwellings", "spaces/dwelling"),
            rule_of(0.25, "a space for every 4 dwellings", "spaces/dwelling"),
            rule_of(9, "3m x 3m", "m2"),
            rule_of(3, "three hours", "hours"),
            rule_of(0, "no additional parking is required", "spaces/dwelling"),
            rule_of(0.0, "may be built to the rear boundary", "m"),
        }
        assert reached == set(RULE_NAMES), f"unreachable: {set(RULE_NAMES) - reached}"
