"""The stuck-chapter alarm must survive a stuck chapter.

Check 1 selects FOUR columns from dcp_chapter_registry; three of its consumers unpacked
three. Every run with a stuck chapter died on `ValueError: too many values to unpack
(expected 3)` — observed in Railway's dcp-watchdog logs from 2026-09-16, exit code 1, while
36 chapters sat stuck and a review queue went two days stale with nothing raised. The alarm
built to catch exactly that was the thing that was broken.

A second failure rode along: `critical` was rebuilt as 3-tuples while `stuck` holds
4-tuples, so `non_critical = [x for x in stuck if x not in critical]` never matched and a
chapter stuck past 48 hours was filed as merely standard.

These tests are source-shape and arithmetic only — no database, no clock, no import of the
module (which connects at import time).

prior-art-checked: tests/test_dcp_watchdog_blocked.py covers the THREE-STATE wording of the
alert and extracts its pure helpers the same way; it asserts nothing about tuple arity and
would not have caught this — it passes today while the script cannot run.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts" / "dcp_watchdog.py").read_text(encoding="utf-8")


def _check_one_column_count() -> int:
    """How many columns Check 1 actually selects, read from the source."""
    m = re.search(r"#\s*──+\s*Check 1.*?SELECT\s+(.*?)\s+FROM\s+dcp_chapter_registry",
                  SRC, re.DOTALL)
    assert m, "Check 1's SELECT could not be located in dcp_watchdog.py"
    return len([c for c in m.group(1).split(",") if c.strip()])


def _unpack_arities(variable: str) -> list[tuple[int, str]]:
    """(arity, line) for every `for a, b, c in <variable>` over the rows of that query."""
    out = []
    for line in SRC.splitlines():
        m = re.search(rf"for\s+([A-Za-z_,\s]+?)\s+in\s+{variable}\b", line)
        if m:
            out.append((len([n for n in m.group(1).split(",") if n.strip()]), line.strip()))
    return out


class TestEveryReaderMatchesTheQuery:
    def test_check_one_selects_four_columns(self):
        assert _check_one_column_count() == 4

    @pytest.mark.parametrize("variable", ["stuck", "non_critical"])
    def test_no_consumer_unpacks_the_wrong_number(self, variable):
        """The bug, stated as a rule: a reader of these rows either binds the WHOLE row
        (one name) or unpacks ALL of its columns. A count in between — three names for a
        four-column row — is the crash, and it is the only thing rejected here. Both
        variables hold rows of the same query."""
        expected = _check_one_column_count()
        wrong = [(n, line) for n, line in _unpack_arities(variable)
                 if n not in (1, expected)]
        assert not wrong, (
            f"{variable}: expected 1 name (whole row) or {expected} (full unpack), found "
            + "; ".join(f"{n} in `{line}`" for n, line in wrong))

    def test_there_is_at_least_one_reader_to_check(self):
        """Guards the guard: if the loops are renamed away, the tests above pass vacuously."""
        assert _unpack_arities("stuck"), "no `for ... in stuck` loop found — test is vacuous"


class TestCriticalSplitUsesWholeRows:
    """The second defect: comparing rebuilt tuples against whole rows silently downgrades
    every critical chapter. Run the real lines from the source, not a copy of them."""

    def _run_split(self, stuck, now):
        crit_line = next(l for l in SRC.splitlines() if l.strip().startswith("critical = ["))
        non_line = next(l for l in SRC.splitlines() if l.strip().startswith("non_critical = ["))
        ns = {"stuck": stuck, "now": now}
        exec(compile(crit_line.strip() + "\n" + non_line.strip(),  # noqa: S102
                     "dcp_watchdog_split", "exec"), ns)
        return ns["critical"], ns["non_critical"]

    def test_a_chapter_stuck_over_48h_is_critical_and_not_also_standard(self):
        now = datetime(2026, 9, 18, tzinfo=timezone.utc)
        rows = [
            ("ku_ring_gai", "section-a-part-8-mixed-use", now - timedelta(hours=72), 1),
            ("woollahra", "chapter-b3-general-development", now - timedelta(hours=30), 2_973_719),
        ]
        critical, non_critical = self._run_split(rows, now)
        assert critical == [rows[0]]
        assert non_critical == [rows[1]]

    def test_the_two_lists_never_overlap(self):
        """The observed symptom: with rebuilt tuples, `x not in critical` was always true,
        so a 72h chapter appeared in BOTH lists and the critical alert lost its meaning."""
        now = datetime(2026, 9, 18, tzinfo=timezone.utc)
        rows = [("c", f"k{i}", now - timedelta(hours=h), 10) for i, h in enumerate((72, 96, 26))]
        critical, non_critical = self._run_split(rows, now)
        assert not set(critical) & set(non_critical)
        assert len(critical) + len(non_critical) == len(rows)

    def test_nothing_is_critical_when_everything_is_fresh(self):
        now = datetime(2026, 9, 18, tzinfo=timezone.utc)
        rows = [("c", "k", now - timedelta(hours=26), 10)]
        critical, non_critical = self._run_split(rows, now)
        assert critical == []
        assert non_critical == rows
