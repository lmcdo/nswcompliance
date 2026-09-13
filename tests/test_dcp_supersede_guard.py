"""A chapter may not be replaced by a version missing most of its sections.

REAL INCIDENT, 2026-09-13. marrickville part4-s1-low-density: 215 live rules across 38
sections were switched off and replaced by 26 rules across 8, none of them a setback,
height or floor-space rule. The commit step compared nothing. See
scripts/dcp_supersede_guard.py.

Each test says what it would catch if the guard were removed or mistuned. The
confusable negatives matter as much as the refusals: an ordinary amendment drops a
few sections, and a guard that refused those would be switched off within a week.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dcp_supersede_guard as g  # noqa: E402
from dcp_supersede_guard import Snapshot, judge  # noqa: E402


def codes(prefix: str, n: int) -> frozenset:
    return frozenset(f"{prefix}.{i}" for i in range(1, n + 1))


def first(snapshot_codes: frozenset, n: int) -> frozenset:
    return frozenset(sorted(snapshot_codes)[:n])


# ---------------------------------------------------------------------------
# 1. The incident, and the threshold bounded from both sides
# ---------------------------------------------------------------------------

def test_the_incident_shape_is_refused():
    """38 sections -> 8 of them. Remove the guard and this passes silently."""
    before = Snapshot(codes("4.1", 38), 215)
    v = judge(before, Snapshot(first(before.codes, 8), 26))
    assert v.refused and v.measure == "codes"
    assert len(v.lost) == 30


def test_the_threshold_is_more_than_half_and_is_bounded_both_ways():
    """Loosen it and six-of-ten lost gets through; tighten it and half lost is refused."""
    before = Snapshot(codes("5.1", 10), 50)
    assert not judge(before, Snapshot(first(before.codes, 5), 25)).refused   # 5 of 10 lost
    assert judge(before, Snapshot(first(before.codes, 4), 20)).refused       # 6 of 10 lost


# ---------------------------------------------------------------------------
# 2. Confusable negatives -- when it must NOT refuse
# ---------------------------------------------------------------------------

def test_an_ordinary_amendment_is_allowed():
    """A council deletes three sections of twenty. That is an amendment, not a loss."""
    before = Snapshot(codes("2.25", 20), 48)
    after = Snapshot(frozenset(sorted(before.codes)[3:]), 44)
    v = judge(before, after)
    assert not v.refused and len(v.lost) == 3


def test_growth_and_a_first_extraction_are_allowed():
    assert not judge(Snapshot(frozenset(), 0), Snapshot(codes("4.2", 30), 80)).refused
    assert not judge(Snapshot(codes("4.2", 10), 40), Snapshot(codes("4.2", 25), 90)).refused


def test_a_positive_and_a_negative_together_so_a_broken_judge_cannot_pass_vacuously():
    before = Snapshot(codes("8.2", 40), 300)
    verdicts = {judge(before, Snapshot(first(before.codes, 38), 290)).refused,
                judge(before, Snapshot(first(before.codes, 10), 60)).refused}
    assert verdicts == {True, False}


# ---------------------------------------------------------------------------
# 3. The cases between
# ---------------------------------------------------------------------------

def test_a_renumbering_is_refused_and_says_how_many_codes_arrived():
    """Every served citation changes; a person should see that. The message must make
    a renumbering recognisable rather than look like a collapse."""
    before = Snapshot(codes("B", 12), 60)
    v = judge(before, Snapshot(codes("C", 12), 60))
    assert v.refused and v.gained == 12
    assert "12 new" in v.describe("waverley", "part-b")


def test_a_chapter_with_too_few_codes_is_judged_by_its_rules():
    before = Snapshot(frozenset({"1.1", "1.2"}), 30)
    assert judge(before, Snapshot(frozenset(), 3)).refused            # 27 of 30 rules gone
    assert not judge(before, Snapshot(frozenset(), 28)).refused       # 2 of 30 gone
    v = judge(Snapshot(frozenset(), 10), Snapshot(frozenset(), 0))
    assert not v.refused and v.measure == "not judged"


# ---------------------------------------------------------------------------
# 4. enforce(): reads the chapter in the same transaction, raises, names the way out
# ---------------------------------------------------------------------------

class _Cur:
    def __init__(self, headers):
        self.headers = headers
        self.sql = None
        self.params = None

    def execute(self, sql, params=None):
        self.sql, self.params = sql, params

    def fetchall(self):
        return [(h,) for h in self.headers]


def _after_the_bad_swap():
    # 8 coded headers plus 18 rows with no header at all -- 26 live rules.
    return _Cur([f"4.1.{i} Heading" for i in range(1, 9)] + [None] * 18)


def test_enforce_refuses_with_the_numbers_and_the_override_command():
    before = Snapshot(codes("4.1", 38), 215)
    cur = _after_the_bad_swap()
    with pytest.raises(g.SectionLossRefused) as exc:
        g.enforce(cur, "marrickville", "part4-s1-low-density", before)
    msg = str(exc.value)
    assert "38 sections before, 8 after" in msg
    assert "--allow-section-loss marrickville/part4-s1-low-density" in msg
    assert "is_current = TRUE" in cur.sql
    assert cur.params == ("marrickville", "part4-s1-low-density")


def test_the_override_lets_through_the_named_chapter_and_no_other():
    before = Snapshot(codes("4.1", 38), 215)
    v = g.enforce(_after_the_bad_swap(), "marrickville", "part4-s1-low-density", before,
                  allowed=frozenset({"marrickville/part4-s1-low-density"}))
    assert v.refused   # still reported as a loss -- allowed, not re-labelled clean
    with pytest.raises(g.SectionLossRefused):
        g.enforce(_after_the_bad_swap(), "marrickville", "part4-s1-low-density", before,
                  allowed=frozenset({"marrickville/part5-commercial-mixed-use"}))
