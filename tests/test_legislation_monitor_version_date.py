"""instrument_registry.version_date must be parsed, never guessed.

The column existed and was written by NOTHING (repo-wide grep, 2026-08-16)
while current_version carried a readable date as text on 25 of 26 active
instruments. That is the currency date of every LEP and SEPP we monitor,
sitting one column away from being usable.

These tests pin the half that matters: the parser must REFUSE anything that is
not an explicit day-month-year, because a guessed currency date is worse than
an absent one. That is the rule which retired the old version-label parser, and
without a test it is a comment.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

from legislation_monitor import parse_version_date  # noqa: E402


class TestParses:
    @pytest.mark.parametrize("text,expected", [
        ("15 May 2026", date(2026, 5, 15)),
        ("8 May 2026", date(2026, 5, 8)),
        ("31 October 2025", date(2025, 10, 31)),
        ("28 November 2025", date(2025, 11, 28)),
        # Real labels are sometimes wrapped in a phrase.
        ("as amended 9 September 2022", date(2022, 9, 9)),
        ("Current version for 6 February 2026", date(2026, 2, 6)),
    ])
    def test_explicit_day_month_year(self, text, expected):
        assert parse_version_date(text) == expected

    def test_month_case_is_ignored(self):
        assert parse_version_date("15 may 2026") == date(2026, 5, 15)


class TestRefuses:
    """Each of these previously had no guard at all, because nothing parsed."""

    @pytest.mark.parametrize("text", [
        None,          # wingecarribee_lep_2010: no pco_instrument_id, the DQ-69 floor
        "",
        "   ",
        "v3",
        "Amendment 6",
        "2026",        # a bare year is a label, not a date
        "May 2026",    # month precision is not day precision
    ])
    def test_returns_none_rather_than_guessing(self, text):
        assert parse_version_date(text) is None

    def test_an_impossible_date_is_refused_not_clamped(self):
        """31 February must not become 28 February or 3 March."""
        assert parse_version_date("31 February 2026") is None

    def test_a_year_outside_the_century_pattern_is_refused(self):
        assert parse_version_date("15 May 1899") is None


def test_the_refusals_are_not_vacuous():
    """Control case.

    Every assertion above is `is None`, which a parser stubbed to
    `return None` would satisfy completely. This asserts the parser still
    parses, so that mutant dies here rather than passing the whole file.
    """
    assert parse_version_date("15 May 2026") == date(2026, 5, 15)
