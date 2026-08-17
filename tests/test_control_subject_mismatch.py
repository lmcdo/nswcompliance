"""A control's number must be about the thing its control_type names.

THE FIXTURES ARE REAL ROWS, and the pairs matter more than the singles. The
first version of this rule flagged "a foreign word appears near the number",
which caught the Fairfield driveway AND the four Marrickville setbacks whose
conditions merely mention a driveway. Those four are correct. So the driveway
sentences appear here on BOTH sides — as a mismatch and as a non-mismatch —
because a rule that cannot tell them apart is the rule we already rejected.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

from check_control_subject_mismatch import (  # noqa: E402
    locate_value,
    subject_mismatch,
)

# Real source_text values, copied from the rows they belong to.
DRIVEWAY_IS_THE_SUBJECT = (
    "a) Coloured concrete that is textured or patterned must be used and "
    "finished with a non-slip surface or coating b) All driveways are to be "
    "set a minimum of 0.5m from any side boundary and incorporate a soft soil "
    "zone for turf/landscaping."
)
DRIVEWAY_IS_THE_CONDITION_4 = (
    "C11 ii. Minimum side setback: a. Must be 4 metres where there is no "
    "driveway along the side boundary"
)
DRIVEWAY_IS_THE_CONDITION_7 = (
    "C11 ii. b. Must be 7 metres where a driveway is proposed along that side "
    "boundary"
)
SITE_FRONTAGE = (
    "P39 Duplex development will not be supported in streets and sites subject "
    "to Building Appearance and Streetscape Provisions under Section 4.5. P40 "
    "Duplex development requires a minimum site frontage of 15 metres. P41 "
    "Duplex development will not be supported on battleaxe lots."
)
FRONT_FENCING = (
    "1. Front fencing must have a maximum height of 1.2m above ground level "
    "(existing) and must be open style incorporating pickets, slats, palings "
    "or the like or lattice style panels with a minimum aperture of 25mm. 2. "
    "Front fences and walls are not to impede safe sight lines for traffic."
)
FACADE_SEPARATION = (
    "f. provide a minimum of 12m between front facades within the development "
    "so that the layout does not create gun-barrel vistas."
)
BIN_HARDSTAND = (
    "a. be provided within 10m of the kerb; b. be setback at least 3 metres "
    "from the front boundary; c. be suitably screened or otherwise not visible "
    "from the street; d. be a hardstand which is graded and drained "
    "appropriately to prevent pollution; e. be designed as per Council's Waste "
    "Management Guideline; f. enable a collect and return service."
)
PLAIN_SETBACK = (
    "Front Setback (primary frontage) Minimum 6m Dwelling house shall align "
    "with the street"
)


class TestCatchesAMisfiledSubject:
    def test_a_driveway_setback_served_as_the_houses_side_setback(self):
        """0.5 m, and the real ground-level side setback in the same slot is
        0.9 m — this one is SMALLER, so a reader is under-set-back."""
        why = subject_mismatch(DRIVEWAY_IS_THE_SUBJECT, 0.5)
        assert why is not None and "driveway" in why

    def test_a_lot_width_served_as_a_front_setback(self):
        why = subject_mismatch(SITE_FRONTAGE, 15.0)
        assert why is not None and "frontage" in why

    def test_a_fence_height_served_as_a_front_setback(self):
        assert subject_mismatch(FRONT_FENCING, 1.2) is not None

    def test_a_facade_separation_served_as_a_boundary_setback(self):
        """The foreign noun is AFTER the number here, which the first
        positional cut missed entirely."""
        why = subject_mismatch(FACADE_SEPARATION, 12.0)
        assert why is not None and "facades" in why

    def test_a_bin_hardstand_setback_served_as_a_dwelling_setback(self):
        """The giveaway words sit in sibling list items, far from the number,
        so only the whole-quote rule reaches this one."""
        why = subject_mismatch(BIN_HARDSTAND, 3.0)
        assert why is not None and "waste-storage" in why


class TestDoesNotFlagAConditionThatMerelyMentionsOne:
    """THE FALSE POSITIVES THE FIRST VERSION PRODUCED — all four were SERVED
    and all four were correct."""

    @pytest.mark.parametrize("text,val", [
        (DRIVEWAY_IS_THE_CONDITION_4, 4.0),
        (DRIVEWAY_IS_THE_CONDITION_7, 7.0),
    ])
    def test_driveway_after_a_conditional_word_is_not_the_subject(self, text, val):
        assert subject_mismatch(text, val) is None

    def test_an_ordinary_setback_is_not_flagged(self):
        assert subject_mismatch(PLAIN_SETBACK, 6.0) is None


class TestSaysNothingRatherThanGuessing:
    def test_a_number_absent_from_its_quote_is_not_checkable(self):
        """Not the same as fine — a different state, counted separately."""
        assert locate_value(PLAIN_SETBACK, 99.0) is None
        assert subject_mismatch(PLAIN_SETBACK, 99.0) is None

    def test_no_value(self):
        assert subject_mismatch(PLAIN_SETBACK, None) is None

    def test_no_text(self):
        assert subject_mismatch(None, 6.0) is None

    def test_a_non_numeric_value(self):
        assert subject_mismatch(PLAIN_SETBACK, "not a number") is None


class TestValueFormsFoundInTheQuote:
    def test_millimetres_in_the_text_for_a_metre_value(self):
        assert locate_value("side setback of 900mm for houses", 0.9) is not None

    def test_an_integer_value_written_without_a_decimal(self):
        assert locate_value("shall not exceed two (2) storeys", 2) is not None


class TestTheWindowStopsAtTheSentence:
    """Raised by adversarial review. A window measured in characters runs past
    the full stop, and the noun in the NEXT sentence governs the NEXT number."""

    def test_a_driveway_in_the_following_sentence_is_not_the_subject(self):
        text = ("Minimum dwelling side setback 3m. Driveways must be 1m from "
                "the side boundary")
        assert subject_mismatch(text, 3.0) is None

    def test_but_that_driveway_still_governs_its_own_number(self):
        """CONTROL for the control: the guard must not have made the rule
        blind, only precise. 1 m IS the driveway's number."""
        text = ("Minimum dwelling side setback 3m. Driveways must be 1m from "
                "the side boundary")
        assert subject_mismatch(text, 1.0) is not None

    def test_a_fence_in_the_preceding_sentence_is_not_the_subject(self):
        text = ("Front fencing must not exceed 1.2m. The dwelling must be set "
                "back 6m from the front boundary")
        assert subject_mismatch(text, 6.0) is None

    def test_the_facade_case_has_no_sentence_break_and_still_flags(self):
        assert subject_mismatch(FACADE_SEPARATION, 12.0) is not None


class TestOneStrayWasteWordIsNotAWasteControl:
    """Raised by adversarial review: a genuine setback clause that merely
    cross-references the waste guideline must not be condemned by one word."""

    def test_a_single_mention_does_not_condemn_the_quote(self):
        text = ("Minimum front setback 6m. Refer also to the Waste Management "
                "Guideline for servicing.")
        assert subject_mismatch(text, 6.0) is None

    def test_the_real_bin_list_carries_several_and_still_flags(self):
        why = subject_mismatch(BIN_HARDSTAND, 3.0)
        assert why is not None and "waste-storage" in why


def test_the_rule_can_say_yes_and_no():
    """Control case.

    Most assertions here are `is None`, which a function stubbed to
    `return None` satisfies completely — and that stub would report 0
    mismatches over the whole table forever, the comfortable-green failure
    this check exists to prevent. Pin both directions in one place, on the
    same foreign noun, so the difference is the RULE and not the vocabulary.
    """
    assert subject_mismatch(DRIVEWAY_IS_THE_SUBJECT, 0.5) is not None
    assert subject_mismatch(DRIVEWAY_IS_THE_CONDITION_4, 4.0) is None
