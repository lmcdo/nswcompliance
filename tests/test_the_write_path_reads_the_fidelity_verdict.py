"""dcp_fidelity_gate graded every queued row against the council's own PDF, and the
commit worker never read the answer.

Measured 2026-09-20: `grep -n fidelity scripts/dcp_commit_approved.py` returned NOTHING.
A row the gate had checked against the source page and found wanting committed exactly
like a 'grounded' one. The only check in the system that compares our output with the
council's document could not stop a single write.

The legibility guard could not cover for it. Its signature is the fraction of words that
are a single letter, which sees GLYPH interleave and is blind to PHRASE interleave. On
northern_beaches/warringah-dcp-2011-full -- 232 of 250 text pages two-column -- the worst
ratio in 124 rows was 0.055 against a 0.20 threshold, i.e. "clean", while "C3 Parking
Facilities" continued into "G7 - Evergreen Introduction".

This guard is ABSOLUTE rather than before/after, and that is forced rather than chosen:
fidelity_status is a column on dcp_review_queue and regulatory_provisions has no
equivalent, so the rows being replaced carry no verdict to compare against. Verified by
reading information_schema.columns for both tables.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

GUARD_SRC = (ROOT / "scripts" / "dcp_supersede_guard.py").read_text(encoding="utf-8")
COMMIT_SRC = (ROOT / "scripts" / "dcp_commit_approved.py").read_text(encoding="utf-8")


def _guard():
    import dcp_supersede_guard
    return dcp_supersede_guard


class FakeCursor:
    """Returns one canned result set, and records the parameters it was asked for."""

    def __init__(self, rows):
        self._rows = rows
        self.params = None
        self.sql = None

    def execute(self, sql, params=None):
        self.sql, self.params = sql, params

    def fetchall(self):
        return self._rows


def rows(good=0, bad=0, status="failed", reason="section_collapsed"):
    return ([(f"ok{i}", "grounded", "") for i in range(good)]
            + [(f"bad{i}", status, reason) for i in range(bad)])


class TestTheVerdictIsActuallyConsulted:
    def test_the_commit_worker_imports_and_calls_the_fidelity_guard(self):
        """The defect was absence, not a wrong threshold. Pin the wiring itself."""
        assert "enforce_fidelity" in COMMIT_SRC, (
            "the commit worker has stopped reading fidelity_status again -- which is "
            "the entire defect this guards")
        assert re.search(r"enforce_fidelity\(\s*cur,\s*council,\s*chapter_key",
                         COMMIT_SRC), "imported but never called is the same as absent"

    def test_the_batch_it_grades_is_resolved_before_the_dry_run_branch(self):
        """The dry-run branch ends in `continue`. If batch_ts were resolved inside it,
        the commit path would read either an undefined name or the PREVIOUS chapter's
        timestamp -- scoping this guard to another chapter's run, so it would grade
        nothing and pass silently. That is worse than not running at all, because the
        log still shows the guard ran.

        It is also resolved exactly ONCE: a second lookup is a second query for an
        answer already in hand, and adding one desynchronised four existing tests that
        drive this worker with a scripted cursor."""
        call = re.search(r"enforce_fidelity\(([^)]*)\)", COMMIT_SRC).group(1)
        assert "batch_ts" in call
        assign = COMMIT_SRC.index("batch_ts, _ = latest_approved_batch")
        assert assign < COMMIT_SRC.index("if dry_run:"), (
            "batch_ts is resolved inside a branch that does not reach the commit path")
        assert COMMIT_SRC.count("batch_ts, _ = latest_approved_batch") == 1, (
            "the batch is being looked up more than once per chapter")

    def test_a_clean_batch_commits(self):
        g = self._reload()
        cur = FakeCursor(rows(good=100))
        graded, bad, _ = g.enforce_fidelity(cur, "c", "ch", "ts")
        assert (graded, bad) == (100, 0)

    def test_a_batch_that_mostly_fails_is_refused(self):
        g = self._reload()
        cur = FakeCursor(rows(good=90, bad=34))  # 27%
        with pytest.raises(g.FidelityRefused) as e:
            g.enforce_fidelity(cur, "northern_beaches", "warringah-dcp-2011-full", "ts")
        assert "27.4%" in str(e.value) or "27" in str(e.value)
        assert "--allow-fidelity" in str(e.value), "a refusal must say how to override"

    def test_the_named_override_lets_exactly_that_chapter_through(self):
        g = self._reload()
        cur = FakeCursor(rows(good=90, bad=34))
        g.enforce_fidelity(cur, "c", "ch", "ts", allowed=frozenset({"c/ch"}))
        cur2 = FakeCursor(rows(good=90, bad=34))
        with pytest.raises(g.FidelityRefused):
            g.enforce_fidelity(cur2, "c", "other", "ts", allowed=frozenset({"c/ch"}))

    @staticmethod
    def _reload():
        return _guard()


class TestTheThresholdSitsInTheGapItWasReadFrom:
    """Both distributions measured 2026-09-20 have their widest gap between ~4.3% and
    ~6.1%. A threshold that drifts out of that gap stops separating the runs that were
    fine from the ones that were not."""

    def test_the_bar_is_inside_the_measured_gap(self):
        g = _guard()
        assert 0.043 < g.FIDELITY_MAX_BAD_RATIO < 0.061, (
            "the bar has left the gap the distribution actually shows; re-measure "
            "before moving it")

    @pytest.mark.parametrize("bad,graded,refused", [
        (2, 46, False),    # canterbury_bankstown 09-18->09-20, 4.3% -- a real run that was fine
        (3, 49, True),     # 6.1% -- the bottom of the bad cluster
        (11, 124, True),   # northern_beaches 09-20, 8.9%
        (16, 53, True),    # woollahra paddington, 30.2%
        (1, 223, False),   # woollahra b3-general, 0.4%
    ])
    def test_it_splits_the_real_runs_the_way_the_measurement_did(self, bad, graded, refused):
        assert _guard().judge_fidelity(graded, bad) is refused

    def test_a_tiny_batch_is_not_judged(self):
        """One bad row in 10 is 10% and means nothing. The floor is why."""
        g = _guard()
        assert g.judge_fidelity(10, 5) is False
        assert g.judge_fidelity(g.FIDELITY_MIN_GRADED, 5) is True

    def test_exactly_at_the_bar_is_allowed_not_refused(self):
        """`>` not `>=`: the bar is the top of the allowed band, and an off-by-one here
        would refuse a run the measurement says is normal."""
        g = _guard()
        assert g.judge_fidelity(100, 5) is False
        assert g.judge_fidelity(100, 6) is True


class TestWhatCountsAsPassing:
    def test_an_ungraded_row_is_not_counted_as_a_failure(self):
        """NULL means the gate never looked at THAT row -- classify_provision skips
        boilerplate on purpose. Such a row must not inflate the bad count, or the
        guard would fire hardest on chapters full of administrative text."""
        g = _guard()
        cur = FakeCursor(rows(good=90) + [("skipped1", None, ""), ("skipped2", None, "")])
        graded, bad, _ = g.enforce_fidelity(cur, "c", "ch", "ts")
        assert graded == 90, "ungraded rows must not count toward the denominator"
        assert bad == 0, "an ungraded row is not a failed one"

    def test_a_batch_with_NO_verdict_at_all_is_refused(self):
        """The whole batch ungraded is different from one row skipped: it means the
        gate did not run. AI_EXTRACTION is opt-out, and the entire safety argument for
        an LLM reading the document is that its output is proven against the source
        before it is served. No proof, no commit."""
        g = _guard()
        cur = FakeCursor([(f"r{i}", None, "") for i in range(40)])
        with pytest.raises(g.FidelityRefused) as e:
            g.enforce_fidelity(cur, "c", "ch", "ts")
        assert "NOT ONE carries" in str(e.value)
        assert "--allow-fidelity" in str(e.value)

    def test_an_empty_batch_is_not_refused(self):
        """Confusable negative. Nothing approved is not the same as nothing checked,
        and refusing it would fail every chapter with no pending work."""
        g = _guard()
        graded, bad, _ = g.enforce_fidelity(FakeCursor([]), "c", "ch", "ts")
        assert (graded, bad) == (0, 0)

    def test_grounded_and_ok_both_pass(self):
        g = _guard()
        assert set(g.FIDELITY_PASSING) == {"grounded", "ok"}

    def test_grounded_is_not_treated_as_a_failure(self):
        """'grounded' is the BEST outcome -- verified against the source page. An
        approval script written in this same session used `IS DISTINCT FROM 'ok'` and
        turned 81 verified rows into failures."""
        g = _guard()
        cur = FakeCursor([(f"r{i}", "grounded", "") for i in range(100)])
        _graded, bad, _ = g.enforce_fidelity(cur, "c", "ch", "ts")
        assert bad == 0

    def test_the_query_is_scoped_to_one_run_and_to_approved_rows(self):
        """A chapter's queue holds every run it has ever had. Unscoped, this would mix a
        fresh batch with the superseded ones beside it -- northern_beaches alone carries
        six batches."""
        g = _guard()
        cur = FakeCursor(rows(good=5))
        g.fidelity_snapshot(cur, "nb", "warringah", "2026-09-20")
        assert "created_at = %s" in cur.sql
        assert "status = 'approved'" in cur.sql
        assert cur.params == ("nb", "warringah", "2026-09-20")


class TestTheRefusalTellsYouWhatToDoWithIt:
    def test_it_warns_that_section_collapsed_is_usually_re_splitting(self):
        """Measured on northern_beaches: 8 of 11 'failures' were section_collapsed, and
        the chapter's TOTAL text moved -1.7% (537,845 -> 528,636 chars) while its rules
        went 49 -> 113. Nothing was lost; a per-row size heuristic cannot see that. A
        refusal that does not say so invites a blind --allow-fidelity."""
        g = _guard()
        cur = FakeCursor(rows(good=90, bad=34, reason="section_collapsed"))
        with pytest.raises(g.FidelityRefused) as e:
            g.enforce_fidelity(cur, "c", "ch", "ts")
        msg = str(e.value)
        assert "TOTAL text" in msg and "finer" in msg.lower()

    def test_it_names_the_offending_rows(self):
        g = _guard()
        cur = FakeCursor(rows(good=90, bad=34))
        with pytest.raises(g.FidelityRefused) as e:
            g.enforce_fidelity(cur, "c", "ch", "ts")
        assert "bad0" in str(e.value), "a refusal nobody can act on is a blocked pipeline"


class TestASmallBatchIsNotAnnouncedAsHavingPassed:
    """Raised by the pre-push review, 2026-09-21, against this same change.

    Below the row floor the ratio is noise, so the guard does not refuse. It used to say
    so as "under the 5% bar, allowed" -- which for 9 failures in 10 rows reads as
    "90.0% did not pass -- under the 5% bar", a false statement in a log a person acts
    on. Not refusing and having passed are different facts."""

    def test_it_does_not_claim_a_small_batch_came_in_under_the_bar(self, capsys):
        g = _guard()
        cur = FakeCursor(rows(good=1, bad=9))
        g.enforce_fidelity(cur, "c", "ch", "ts")
        out = capsys.readouterr().out
        assert "under the" not in out, (
            "a batch below the floor was never measured against the bar")
        assert "NOT judged" in out

    def test_it_names_the_failures_rather_than_summarising_them_away(self, capsys):
        """The whole point of not refusing is that a person decides instead. They need
        to be told which rows, or the abstention hides the problem."""
        g = _guard()
        cur = FakeCursor(rows(good=1, bad=9))
        g.enforce_fidelity(cur, "c", "ch", "ts")
        out = capsys.readouterr().out
        assert "bad0" in out and "9 did NOT pass" in out

    def test_a_clean_small_batch_says_nothing_alarming(self, capsys):
        g = _guard()
        cur = FakeCursor(rows(good=10))
        g.enforce_fidelity(cur, "c", "ch", "ts")
        out = capsys.readouterr().out
        assert "did NOT pass" not in out
        assert "NOT judged" in out

    def test_the_full_size_wording_is_unchanged(self, capsys):
        """The confusable negative: at or above the floor, "under the bar" is true and
        must still be said."""
        g = _guard()
        cur = FakeCursor(rows(good=118, bad=2))
        g.enforce_fidelity(cur, "c", "ch", "ts")
        assert "under the 5% bar" in capsys.readouterr().out
