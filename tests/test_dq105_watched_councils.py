"""DQ-105's one exception: no config, but nothing falling through.

The check counts COUNCILS with no applicability config, deliberately not rows —
its own docstring argues that counting rows would let a council read 0 "because
its prose happened to match" and drift on re-extraction with nothing decided.
That argument holds and the count is still per-council.

It does not, however, justify demanding a config that cannot be written
truthfully, and cumberland is that case. Measured 2026-09-24: 29 served rows, 0
falling through. Its DCP Part B is FIVE separate sub-parts sharing ONE
document_id, each with its own "1.1 Land to which this Part applies" naming a
different scope — "all residential development types except for single dwelling
house development", "low rise dual occupancy", "residential flat building
development", "boarding house", and dwelling house plus secondary dwelling — and
their section codes COLLIDE, every sub-part having a 1.1 and a 2.4. Neither key
the tagger uses can separate them, so one entry would mis-scope four of the five.

So it is WATCHED: printed, not counted. This file exists because an exception
nobody polices becomes an amnesty. The property that makes it safe is that it
is computed, not listed — no council is named in the probe's logic, and the
moment a watched council has one row fall through it is counted again.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dq_probe_unchecked_rows import probe_105  # noqa: E402


class FakeCursor:
    """Yields the four columns probe_105 selects, in order."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_a, **_k):
        return None

    def fetchall(self):
        return self._rows


def _row(council, source, doc="Unconfigured_Council_Plan__nothing_matches_this"):
    #: `doc` deliberately resolves to no config, which is the state under test.
    return (council, doc, "# 2.4 Some control text", source)


def _run(rows):
    count, detail = probe_105(FakeCursor(rows))
    return count, {k[0]: k[1] for k in detail}


class TestACouncilWithRowsFallingThroughIsCounted:
    def test_it_counts(self):
        count, detail = _run([_row("newcouncil", "no_config"),
                              _row("newcouncil", "no_config")])
        assert count == 1
        assert "newcouncil" in detail
        assert "2 applying to every development type" in detail["newcouncil"]

    def test_one_single_falling_row_is_enough(self):
        """The ratchet. A council that is watched today is counted the moment
        one row starts falling through -- no edit to the probe required."""
        count, _ = _run([_row("c", "text_regex")] * 40 + [_row("c", "no_config")])
        assert count == 1


class TestACouncilWithNothingFallingThroughIsWatchedNotCounted:
    def test_it_does_not_count(self):
        count, detail = _run([_row("cumberland", "text_regex") for _ in range(29)])
        assert count == 0
        assert "cumberland" in detail, "a watched council must still be visible"

    def test_it_says_why_it_is_watched(self):
        """A silent exclusion is how an exception becomes an amnesty. Whoever
        reads the report has to be told this council was seen and skipped."""
        _, detail = _run([_row("cumberland", "text_regex")])
        assert "watched" in detail["cumberland"]
        assert "document_id" in detail["cumberland"]

    def test_the_exception_names_no_council_in_its_logic(self):
        """It is computed from the rows, not from a hardcoded allowlist. A list
        would go stale silently and would excuse the next council by accident."""
        src = (ROOT / "scripts" / "dq_probe_unchecked_rows.py").read_text(
            encoding="utf-8")
        body = src[src.index("def probe_105"):]
        body = body[:body.index("\nPROBES = ")]
        code = "\n".join(ln for ln in body.splitlines()
                         if not ln.lstrip().startswith("#"))
        assert '"cumberland"' not in code and "'cumberland'" not in code, (
            "a council name appears in probe_105's executable logic; the "
            "exception must be derived from fallthrough == 0, not listed")

    def test_any_council_with_zero_fallthrough_is_watched_not_just_cumberland(self):
        count, detail = _run([_row("somewhere_else", "config_all")])
        assert count == 0
        assert "watched" in detail["somewhere_else"]


class TestAConfiguredCouncilIsNeither:
    def test_a_resolving_document_is_not_reported_at_all(self):
        """Waverley keys on a section code read out of the provision TEXT. It
        was falsely reported as unconfigured once already, by a version of this
        probe that passed an empty string for the text."""
        rows = [("waverley", "Waverley_DCP_2012__part_e_site_specific",
                 "# E1 Some control", "config_all")]
        count, detail = _run(rows)
        assert count == 0
        assert "waverley" not in detail

    def test_the_probe_still_returns_a_count_that_can_rise(self):
        """Guards against the whole thing being neutered into always-zero."""
        count, _ = _run([_row("a", "no_config"), _row("b", "no_config")])
        assert count == 2
