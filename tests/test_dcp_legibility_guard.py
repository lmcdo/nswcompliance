"""A chapter can keep every section and every rule and still be ruined.

city_of_sydney/section-3-general-provisions holds 92 of DQ-70's remaining stale rows, so
committing it looks like the fix. Measured on the live queue 2026-09-19, it is the
opposite: clause 3.2.3 is served clean today — 1,357 tokens, single-letter ratio 0.021 —
and the approved replacement is a two-column page read straight across at 2,202 tokens and
ratio 0.225. Across the chapter, 0 live rules match the signature and 1 queued rule does.

None of the existing gates could see it. count_drop compares row counts, the section-loss
guard compares section codes, and regeneration_artifact, map_change and restructure all
look at structure. The rule survives every one of them with its words destroyed.

The signature is DQ-78's, reused rather than reinvented, so the gate, the data-quality
ledger and the page a planner reads all mean one thing by "scrambled".
"""
from __future__ import annotations

import pytest

from scripts import dcp_supersede_guard as g
from scripts.dcp_supersede_guard import Snapshot


def snap(rows=40, refs=(), ratios=None):
    """refs at a default 0.30, or ratios={ref: ratio} for the score cases."""
    rules = {r: (r, 0.30) for r in refs}
    for r, v in (ratios or {}).items():
        rules[r] = (r, v)
    return Snapshot(codes=frozenset(f"3.{i}" for i in range(1, 9)), rows=rows,
                    scrambled_rules=rules)


class TestTheSignatureIsDQ78s:
    def test_the_thresholds_are_the_ledgers(self):
        """Not re-chosen here. DQ-78 read them off the served distribution: >=0.50 matched
        34 rows, >=0.30 83, >=0.20 128, >=0.10 663, and the token floor separates a
        scrambled page from a short unit split like 's o o m m', which is DQ-77's."""
        assert g.SCRAMBLE_MIN_TOKENS == 100
        assert g.SCRAMBLE_MIN_RATIO == 0.20

    def test_the_query_counts_single_letter_tokens(self):
        cur = _Cur([], scrambled=[])
        g.snapshot(cur, "city_of_sydney", "section-3-general-provisions")
        sql = next(c[0] for c in cur.calls if "singles" in c[0])
        assert "regexp_split_to_array" in sql
        assert "'^[A-Za-z]$'" in sql
        assert "singles::numeric / n >=" in sql

    def test_it_does_NOT_filter_on_v2_is_actionable(self):
        """Load-bearing, and the reason to pin it by name: rows this worker inserts get
        v2_is_actionable NULL — the classifier decides later — so DQ-78's own actionable
        filter would exclude every newly written row. The AFTER count could never rise
        above BEFORE, and the guard would be permanently dead while appearing to run."""
        cur = _Cur([], scrambled=[])
        g.snapshot(cur, "city_of_sydney", "section-3")
        sql = next(c[0] for c in cur.calls if "singles" in c[0])
        assert "v2_is_actionable" not in sql, (
            "the scramble query filters on v2_is_actionable, so it cannot see the rows "
            "this commit just inserted and the guard can never fire")
        assert "is_current = TRUE" in sql


class TestOnlyAddedDamageIsRefused:
    def test_a_clean_chapter_turning_scrambled_is_refused(self):
        with pytest.raises(g.LegibilityRefused) as exc:
            g.enforce_legibility(
                _Cur(["3.2.3 Active frontages"], scrambled=["Sydney__3_2_3"]),
                "city_of_sydney", "section-3-general-provisions", snap())
        msg = str(exc.value)
        assert "1 rule(s) are newly scrambled" in msg
        assert "0 scrambled before, 1 after" in msg
        assert "Sydney__3_2_3" in msg, "the refusal must name a row a person can open"

    def test_an_already_garbled_chapter_that_stays_the_same_is_allowed(self):
        """Confusable negative. Holding a chapter hostage to a defect it arrived with
        would block the very re-read that fixes it."""
        cur = _Cur(["3.2.3 x"], scrambled=["a", "b", "c"])
        assert g.enforce_legibility(cur, "c", "k", snap(refs=["a", "b", "c"])) == []

    def test_a_commit_that_UNSCRAMBLES_rows_is_allowed(self):
        """The direction matters: fewer scrambled rules is the repair landing, and a
        symmetric 'any change' test would refuse it."""
        cur = _Cur(["3.2.3 x"], scrambled=["a"])
        assert g.enforce_legibility(cur, "c", "k", snap(refs=["a", "b", "c", "d"])) == []

    def test_a_first_extraction_with_garble_is_still_refused(self):
        """Nothing to lose is not nothing to damage: a chapter going from no rules to
        scrambled rules is publishing gibberish for the first time."""
        with pytest.raises(g.LegibilityRefused):
            g.enforce_legibility(_Cur([], scrambled=["x"]), "c", "k",
                                 Snapshot(frozenset(), 0, {}))

    def test_a_repair_and_a_new_break_do_NOT_cancel_out(self):
        """The real city_of_sydney commit, measured by driving it against production and
        rolling back: it deletes the junk row '2012' (a map caption whose ref is a year)
        and scrambles clause 3.2.3, which is served clean today. The TOTAL is 1 before and
        1 after, so a guard comparing counts reports no change and publishes the damage.
        Comparing which rules are scrambled cannot be cancelled that way."""
        before = snap(refs=["Sydney_DCP_2012__section_3_general_provisions__2012"])
        cur = _Cur(["3.2.3 x"], scrambled=["Sydney_DCP_2012__section_3_general_provisions__3_2_3"])
        with pytest.raises(g.LegibilityRefused) as exc:
            g.enforce_legibility(cur, "city_of_sydney", "section-3-general-provisions", before)
        msg = str(exc.value)
        assert "3_2_3" in msg
        assert "1 scrambled before, 1 after" in msg, (
            "the message must show the totals that did not move, so the next reader sees "
            "why a count would have missed it")

    def test_an_ALREADY_scrambled_rule_made_much_worse_is_refused(self):
        """Listing which rules are scrambled cannot see this: the ref is in both sets, so
        the difference is empty and 0.21 replaced by 0.90 commits. 155 live rules are
        scrambled today across 8 chapters, the worst fifteen between 0.62 and 0.91, so it
        is the next thing that would have gone wrong."""
        before = snap(ratios={"krg__2_1": 0.21})
        cur = _Cur(["2.1 x"], scrambled=[("krg__2_1", "krg__2_1", 0.90)])
        with pytest.raises(g.LegibilityRefused) as exc:
            g.enforce_legibility(cur, "ku_ring_gai", "section-a-part-2-site-analysis", before)
        assert "0.21 -> 0.90" in str(exc.value), str(exc.value)

    def test_a_scrambled_rule_that_wobbles_is_NOT_refused(self):
        """Confusable negative, and the reason for a margin rather than any-increase: a
        sentence added to a 2,000-token rule moves the ratio by under 0.01, and refusing
        that would wedge the chapter against the repair that fixes it."""
        before = snap(ratios={"krg__2_1": 0.61})
        cur = _Cur(["2.1 x"], scrambled=[("krg__2_1", "krg__2_1", 0.63)])
        assert g.enforce_legibility(cur, "c", "k", before) == []

    def test_the_margin_is_a_fifth_of_the_rise_it_was_built_for(self):
        assert g.SCRAMBLE_WORSE_MARGIN == 0.05
        assert g.SCRAMBLE_WORSE_MARGIN < (0.225 - 0.021) / 4

    def test_the_identity_is_not_ref_number_alone(self):
        """ref_number is nullable and not unique — five refs carry two current provisions
        each. Keying on it alone would collapse two rows into one, hide damage to the
        second, and crash sorting a NULL against a string while building the refusal."""
        cur = _Cur([], scrambled=[])
        g.snapshot(cur, "c", "k")
        sql = next(c[0] for c in cur.calls if "singles" in c[0])
        assert "COALESCE(ref_number, '') || '|' || COALESCE(section_header, '')" in sql
        assert "MAX(singles::numeric / n)" in sql, (
            "two rows sharing an identity must keep the WORSE ratio, which errs toward "
            "refusing rather than toward publishing")

    def test_judge_is_pure_and_never_negative(self):
        assert [d[0] for d in g.judge_legibility(snap(), snap(refs=["a","b","c"]))] == ["a","b","c"]
        assert g.judge_legibility(snap(refs=["a", "b", "c"]), snap()) == []
        assert g.judge_legibility(snap(refs=["a", "b"]), snap(refs=["a", "b"])) == []


class TestTheWayPastItIsNamed:
    def test_the_refusal_says_what_to_run(self):
        with pytest.raises(g.LegibilityRefused) as exc:
            g.enforce_legibility(_Cur([], scrambled=["x"]), "city_of_sydney",
                                 "section-3-general-provisions", snap())
        assert "--allow-garble city_of_sydney/section-3-general-provisions" in str(exc.value)
        assert "Fix the extraction rather than committing it" in str(exc.value)

    def test_the_override_lets_through_the_named_chapter_and_no_other(self):
        allowed = frozenset({"city_of_sydney/section-3-general-provisions"})
        assert g.enforce_legibility(_Cur([], scrambled=["x"]), "city_of_sydney",
                                    "section-3-general-provisions", snap(),
                                    allowed) == [("x", None, 0.30)]
        with pytest.raises(g.LegibilityRefused):
            g.enforce_legibility(_Cur([], scrambled=["x"]), "ku_ring_gai",
                                 "section-a-part-6-multi-dwelling", snap(),
                                 allowed)

    def test_it_is_a_separate_override_from_section_loss(self):
        """An override should permit exactly what it names. Deciding a chapter may shed
        sections is not deciding to publish text a two-column read has scrambled."""
        src = (g.__file__ and open(g.__file__, encoding="utf-8").read())
        assert "--allow-garble" in src and "--allow-section-loss" in src
        assert g.LegibilityRefused is not g.SectionLossRefused
        assert not issubclass(g.LegibilityRefused, g.SectionLossRefused)


class TestTheCommitWorkerActuallyCallsIt:
    """A guard nobody calls is a comment. #1123's lesson: merged, and run by nothing."""

    import pathlib
    SRC = (pathlib.Path(__file__).resolve().parents[1]
           / "scripts" / "dcp_commit_approved.py").read_text(encoding="utf-8")

    def test_it_runs_on_the_commit_path(self):
        assert "enforce_legibility(cur, council, chapter_key, before, allowed_garble)" in self.SRC

    def test_it_runs_after_the_write_and_before_the_commit(self):
        """Judged on the outcome, not a prediction of it — and inside the uncommitted
        transaction, so a refusal rolls back and the approval survives."""
        write = self.SRC.index("commit_reviewed_from_queue(")
        guard = self.SRC.index("enforce_legibility(cur,")
        commit = self.SRC.index("conn.commit()", write)
        assert write < guard < commit

    def test_the_flag_exists_and_is_repeatable(self):
        assert '"--allow-garble", action="append"' in self.SRC
        assert "allowed_garble = frozenset(args.allow_garble)" in self.SRC


class _Cur:
    """snapshot() issues two queries: the section headers, then the scrambled refs."""

    def __init__(self, headers, scrambled=()):
        self.headers = list(headers)
        self.scrambled = list(scrambled)
        self.sql = None
        self.calls = []

    def execute(self, sql, params=None):
        self.sql = sql
        self.calls.append((sql, params))

    def fetchall(self):
        if "singles" in (self.sql or ""):
            # (identity, shown ref, ratio) — a bare string means the default 0.30
            return [(r, r, 0.30) if isinstance(r, str) else r for r in self.scrambled]
        return [(h,) for h in self.headers]
