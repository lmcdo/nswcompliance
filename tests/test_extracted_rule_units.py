"""A stored length must equal the number and unit in the text it came from.

WHY THE RULE IS ARITHMETIC AND NOT VOCABULARY. The first version of this check
compared the stored UNIT against the unit written in the text, and flagged 29
rows of which every one was correct — "350mm wide" stored as 0.35 with unit "m"
IS the conversion. A flag list where most entries are fine trains you to ignore
it, which is how a real mismatch survives inside it.

So both sides are converted to metres and compared. A conversion agrees. The
#968 misread — two patterns listed `m` before `mm`, so "600 mm" recorded 600
METRES — is out by exactly the unit factor and cannot agree.

`inconsistency` is pure so the thing that decides whether the build goes red can
be tested without a database.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

from check_extracted_rule_units import inconsistency  # noqa: E402


class TestCatchesTheMisread:
    def test_the_600mm_case_that_started_this(self):
        """"600 mm" recorded as 600 metres — 1000x, in a value used for sums."""
        got = inconsistency("setback of 600 mm", 600.0, "m")
        assert got is not None
        stored_m, expected_m = got
        assert stored_m == 600.0 and expected_m == 0.6

    def test_centimetres_misread_as_metres(self):
        assert inconsistency("150 cm high", 150.0, "m") is not None

    def test_a_wrong_value_in_the_right_unit_is_still_caught(self):
        """The check is against the TEXT, not just the unit label."""
        assert inconsistency("4.5 m setback", 6.0, "m") is not None


class TestAcceptsLegitimateDerivation:
    def test_a_conversion_is_not_a_mismatch(self):
        """THE FALSE POSITIVE THE FIRST VERSION PRODUCED, 29 times."""
        assert inconsistency("350mm wide", 0.35, "m") is None

    @pytest.mark.parametrize("raw,val", [
        ("900mm wide", 0.9), ("25mm ", 0.025), ("150mm ", 0.15),
        ("100mm wide", 0.1), ("800mm long", 0.8),
    ])
    def test_real_rows_from_the_table_are_accepted(self, raw, val):
        assert inconsistency(raw, val, "m") is None

    def test_same_unit_same_number_agrees(self):
        assert inconsistency("15 m wide", 15.0, "m") is None


class TestSaysNothingRatherThanGuessing:
    def test_no_value_is_not_a_finding(self):
        assert inconsistency("minimum height of 950mm", None, "m") is None

    def test_no_text_is_not_a_finding(self):
        assert inconsistency("", 0.9, "m") is None

    def test_a_non_length_unit_is_out_of_scope(self):
        """Areas and rates are a different question; claiming on them here
        would be inventing coverage this check does not have."""
        assert inconsistency("35 m2 of landscaping", 35.0, "m2") is None
        assert inconsistency("1 space per 4 dwellings", 0.25, "spaces") is None

    def test_text_with_no_length_at_all(self):
        assert inconsistency("must be landscaped", 1.0, "m") is None


class TestTextCarryingMoreThanOneLength:
    """Raised by adversarial review of the first version, which took only the
    FIRST length in the text and would have reported a mismatch against a
    stored value that plainly appears in it."""

    def test_the_second_length_in_the_text_is_accepted(self):
        assert inconsistency("3 m wide with a 600 mm setback", 0.6, "m") is None

    def test_the_first_length_in_the_text_is_still_accepted(self):
        assert inconsistency("3 m wide with a 600 mm setback", 3.0, "m") is None

    def test_a_value_matching_NEITHER_is_still_caught(self):
        """CONTROL. Widening to 'any length in the text' must not widen to
        'anything at all' — otherwise the check stops being able to fail."""
        got = inconsistency("3 m wide with a 600 mm setback", 600.0, "m")
        assert got is not None

    def test_three_lengths_the_last_one_matches(self):
        assert inconsistency("1.5 m, 2 m or 900 mm", 0.9, "m") is None


def test_the_rule_can_say_yes_and_no():
    """Control case.

    Most assertions above are `is None`, which a function stubbed to
    `return None` satisfies completely — and that stub would report 0
    inconsistencies over the whole table forever, which is exactly the
    comfortable-green failure this check exists to prevent. So pin both
    directions in one place.
    """
    assert inconsistency("600 mm", 600.0, "m") is not None
    assert inconsistency("600 mm", 0.6, "m") is None
