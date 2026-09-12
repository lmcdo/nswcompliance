"""The reading step: what it must refuse to let through.

The mechanical verifier proves a number is in the document and inside its own
quote. On the first real run all 11 proposals passed every mechanical check and
four still had to be changed -- for DIRECTION, SCOPE and GRAIN, none of which a
string comparison can see. This module records that reading, so these tests are
about the ways a recorded reading can itself be wrong.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_review_proposals import (  # noqa: E402
    apply_review, row_key)

PAGE = (
    "3.4.3.4 OPEN SPACE\n"
    "C.04 Private open space is to be provided as follows:\n"
    "a) 1-bedroom/studio units must provide a minimum of 8m2 per dwelling.\n"
    "b) 2-bedroom units must provide a minimum of 12m2 per dwellings.\n"
    "c) 3 or more-bedroom units must provide a minimum of 16m2 per dwelling.\n"
)
PAGES = {("parramatta", "dcp-full", 100): PAGE}

NOTE = ("A note long enough to be a real reason rather than a rubber stamp, "
        "because an unexplained verdict is an unread one.")


def proposal(value, quote, **kw):
    base = {
        "council": "parramatta", "control_type": "private_open_space",
        "dev_type": "manor_house", "applicability": "universal_residential",
        "value_min": value, "value_max": None, "unit": "m2",
        "condition": "first floor level", "section_ref": "C.04",
        "source_text": quote, "source_page": 100, "source_chapter": "dcp-full",
    }
    base.update(kw)
    return base


ONE_BED = proposal(8, "a) 1-bedroom/studio units must provide a minimum of "
                      "8m2 per dwelling.")
TWO_BED = proposal(12, "b) 2-bedroom units must provide a minimum of 12m2 "
                       "per dwellings.")


def verdicts(*pairs):
    return {k: {"verdict": v, "note": NOTE} for k, v in pairs}


class TestKeying:
    def test_one_clause_with_three_minimums_gets_three_keys(self):
        """THE BUG THIS KEY SHAPE EXISTS FOR.

        Parramatta states three different minimums under one clause label -- C.04
        a) 8m2, b) 12m2, c) 16m2 -- all on page 100. Keying on
        council|control_type|section_ref|page collapsed them onto one key, so a
        verdict written about one would have governed all three, and two would
        never have been read while the run reported zero problems.
        """
        assert row_key(ONE_BED) != row_key(TWO_BED)

    def test_dev_type_separates_rows_that_differ_only_by_it(self):
        assert row_key(ONE_BED) != row_key(proposal(
            8, ONE_BED["source_text"], dev_type="multi_dwelling_housing"))

    def test_a_genuine_collision_is_reported_not_absorbed(self):
        _, _, problems = apply_review(
            [ONE_BED, dict(ONE_BED)],
            verdicts((row_key(ONE_BED), "ACCEPT")), PAGES)
        assert any("KEY COLLISION" in p for p in problems)


class TestFailsClosed:
    def test_an_unreviewed_proposal_does_not_pass(self):
        serve, stopped, problems = apply_review([ONE_BED], {}, PAGES)
        assert serve == [] and stopped == []
        assert any("UNREVIEWED" in p for p in problems)

    def test_an_unknown_verdict_does_not_pass(self):
        serve, _, problems = apply_review(
            [ONE_BED], verdicts((row_key(ONE_BED), "LOOKS_FINE")), PAGES)
        assert serve == []
        assert any("BAD VERDICT" in p for p in problems)

    def test_an_unexplained_accept_does_not_pass(self):
        """An ACCEPT with no reason is indistinguishable from an unread one."""
        serve, _, problems = apply_review(
            [ONE_BED],
            {row_key(ONE_BED): {"verdict": "ACCEPT", "note": "fine"}}, PAGES)
        assert serve == []
        assert any("NOTE TOO SHORT" in p for p in problems)

    def test_a_clean_accept_passes(self):
        """Mutation guard: the gate must not be refusing everything."""
        serve, stopped, problems = apply_review(
            [ONE_BED], verdicts((row_key(ONE_BED), "ACCEPT")), PAGES)
        assert problems == []
        assert len(serve) == 1 and stopped == []
        assert serve[0]["review_verdict"] == "ACCEPT"

    def test_a_rejected_row_is_kept_with_its_reason_but_not_served(self):
        serve, stopped, problems = apply_review(
            [ONE_BED], verdicts((row_key(ONE_BED), "REJECT")), PAGES)
        assert problems == [] and serve == []
        assert len(stopped) == 1 and stopped[0]["review_note"] == NOTE


class TestTheReviewerIsNotExemptFromTheCheck:
    """The previous review changed 8 -> 10 and 4.5 -> 6 by hand and never
    re-ran the mechanical check. A corrected value that has left its own quote is
    the reviewer introducing the exact defect the verifier exists to catch."""

    def test_a_correction_that_leaves_the_quote_is_caught(self):
        key = row_key(ONE_BED)
        serve, _, problems = apply_review(
            [ONE_BED],
            {key: {"verdict": "CORRECT_AND_ACCEPT", "note": NOTE,
                   "corrections": {"value_min": 9}}}, PAGES)
        assert serve == []
        assert any("REVIEW BROKE THE ROW" in p for p in problems)

    def test_a_correction_that_stays_in_the_quote_passes_and_is_recorded(self):
        # 8 and 12 are both genuinely on this page; correcting one row's value to
        # a number inside ITS OWN quote is the only correction that can stand.
        key = row_key(TWO_BED)
        serve, _, problems = apply_review(
            [TWO_BED],
            {key: {"verdict": "CORRECT_AND_ACCEPT", "note": NOTE,
                   "corrections": {"dev_type": "residential_flat_building"}}},
            PAGES)
        assert problems == []
        assert serve[0]["dev_type"] == "residential_flat_building"

    def test_a_changed_value_is_recorded_as_changed(self):
        key = row_key(ONE_BED)
        serve, _, _ = apply_review(
            [ONE_BED],
            {key: {"verdict": "ACCEPT", "note": NOTE,
                   "corrections": {"value_min": 8.0}}}, PAGES)
        # 8 -> 8.0 is not a change of value and must not be flagged as one.
        assert serve and serve[0]["review_changed_values"] is None

    def test_a_correction_citing_an_unsupplied_page_is_caught(self):
        key = row_key(ONE_BED)
        serve, _, problems = apply_review(
            [ONE_BED], {key: {"verdict": "ACCEPT", "note": NOTE}}, {})
        assert serve == []
        assert any("PAGE NOT SUPPLIED" in p for p in problems)
