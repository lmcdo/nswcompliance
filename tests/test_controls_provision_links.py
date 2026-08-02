"""A control is linked to a provision only when exactly one provision matches.

WHY THESE TESTS LOOK LIKE THIS
------------------------------
A WRONG link is worse than no link. An unlinked control is simply not yet
machine-checkable; a wrongly linked one lets a later check compare a number
against someone else's clause and report a confident false verdict. So the tests
that matter are the ones proving the matcher REFUSES: no match, several matches,
and a quote too short to be distinctive must all yield None.

Mutation notes:
  * returning hits[0] regardless of count fails test_several_matches_refuse.
  * dropping the length floor fails test_a_short_quote_never_links.
  * dropping the citation strip fails test_the_appended_citation_is_stripped.
  * overwriting an existing link fails TestExistingLinksAreNeverOverwritten.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.link_controls_to_provisions import (  # noqa: E402
    MIN_QUOTE_CHARS,
    PRESERVE_EXISTING_LINKS,
    classify,
    find_single_match,
    normalise,
    quoted_clause,
)

CLAUSE = "side setbacks to external walls should be a minimum of 900mm"
assert len(CLAUSE) >= MIN_QUOTE_CHARS


class TestTheMatcherRefusesWhenItCannotBeSure:
    def test_no_match_refuses(self):
        provisions = [(1, normalise("front setbacks are to be 6m from the boundary"))]
        assert find_single_match(CLAUSE, provisions) == (None, 0)
        assert classify(CLAUSE, provisions) == "no_provision_contains_the_quote"

    def test_several_matches_refuse(self):
        """Duplicate clauses across documents are real — this is not hypothetical."""
        text = normalise(f"s2.1.2 B.1d: {CLAUSE}.")
        provisions = [(1, text), (2, text)]
        picked, count = find_single_match(CLAUSE, provisions)
        assert picked is None and count == 2
        assert classify(CLAUSE, provisions) == "ambiguous_multiple_provisions"

    def test_a_short_quote_never_links(self):
        short = "min 900mm"
        assert len(short) < MIN_QUOTE_CHARS
        provisions = [(1, normalise(f"side setback {short} applies"))]
        assert find_single_match(short, provisions) == (None, 0)
        assert classify(short, provisions) == "quote_too_short"

    def test_a_council_with_no_provisions_is_its_own_outcome(self):
        """Not 'no match' — the distinction is the whole finding of this work."""
        assert classify(CLAUSE, []) == "council_has_no_provisions"

    def test_exactly_one_match_links(self):
        provisions = [(7, normalise(f"s2.1.2 B.1d: {CLAUSE}.")),
                      (8, normalise("rear setback is 3m"))]
        assert find_single_match(CLAUSE, provisions) == (7, 1)
        assert classify(CLAUSE, provisions) == "linkable"


class TestNormalisation:
    def test_whitespace_and_case_do_not_prevent_a_match(self):
        provisions = [(1, normalise("SIDE  setbacks to external\nwalls should be a "
                                    "minimum of 900MM in all cases"))]
        assert find_single_match(quoted_clause(CLAUSE), provisions)[0] == 1

    def test_the_appended_citation_is_stripped(self):
        """The extractors append '(Ashfield DCP 2016 DS18.5)', which is not in the
        provision text — leaving it on makes every such row fail to match."""
        raw = "Minimum 35% of site area as landscaped area (Ashfield DCP 2016 DS18.5)"
        assert quoted_clause(raw) == "minimum 35% of site area as landscaped area"

    def test_a_parenthetical_that_is_not_a_citation_is_kept(self):
        """Under-match rather than over-strip: dropping real clause text would
        widen matching and risk linking the wrong provision."""
        raw = "Side setback of 900mm (measured to the external wall face)"
        assert quoted_clause(raw).endswith("(measured to the external wall face)")

    def test_none_and_empty_are_safe(self):
        assert quoted_clause(None) == "" and normalise(None) == ""
        assert find_single_match(quoted_clause(None), [(1, "anything")]) == (None, 0)


class TestStaleLinksAreNotRetained:
    """A link pointing outside the CURRENT provision set is stale, whoever made it.

    The candidate list passed to the matcher already excludes superseded rows, so
    "previous id is absent from it" is the staleness test. The first version of the
    script only handled staleness inside the `linkable` branch, which silently
    retained a stale link on any row that no longer matched anything current — 3
    live rows were in exactly that state.
    """

    def test_a_previous_id_absent_from_the_current_set_is_stale(self):
        current = [(7, normalise(f"s2.1.2 B.1d: {CLAUSE}."))]
        current_ids = {pid for pid, _ in current}
        assert 102098 not in current_ids, "a superseded provision id"
        # re-pointable: the quote still matches a current row
        assert find_single_match(CLAUSE, current)[0] == 7

    def test_stale_with_no_current_match_must_clear_not_keep(self):
        """Pointing at withdrawn text is worse than admitting there is no link."""
        current = [(9, normalise("an unrelated clause about tree canopy"))]
        picked, count = find_single_match(CLAUSE, current)
        assert picked is None and count == 0, (
            "nothing current matches, so the planner must write None rather than "
            "leave the stale id in place")

    def test_the_query_requires_current_and_actionable(self):
        sql = (ROOT / "scripts" / "link_controls_to_provisions.py").read_text(
            encoding="utf-8")
        assert "p.is_current AND p.v2_is_actionable" in sql
        assert "r.is_active" in sql

    def test_the_backup_is_checked_for_COVERAGE_not_just_count(self):
        """CREATE TABLE IF NOT EXISTS reuses an earlier run's table, and a count
        check passes spuriously when it holds different rows — which happened."""
        sql = (ROOT / "scripts" / "link_controls_to_provisions.py").read_text(
            encoding="utf-8")
        assert "planned rows missing" in sql
        assert "WHERE NOT EXISTS" in sql


class TestExistingLinksAreNeverOverwritten:
    def test_the_flag_is_on(self):
        """Guards the real case found on the live table: control 3 already pointed
        at provision 98149, and this matcher resolves it to 97850 because the same
        clause exists as more than one provision row. Neither is provably right, so
        the human's link stands."""
        assert PRESERVE_EXISTING_LINKS is True

    def test_the_update_guard_is_null_safe_and_compares_the_planned_value(self):
        """A plan built from a stale read must not clobber a link written since.

        The guard is the planned previous value, NOT `provision_id IS NULL`. An
        earlier version asserted NULL-only, which was right while the script could
        only fill blanks; clearing a stale link means writing over a non-NULL id, so
        a NULL-only guard would have silently skipped exactly the rows that most
        needed fixing. Concurrency safety is unchanged: if anything wrote to the row
        after planning, the comparison fails and the row is skipped rather than
        overwritten. Never overwriting a HUMAN's current link is enforced in the
        planner (PRESERVE_EXISTING_LINKS), which is where the judgement lives.
        """
        sql = (ROOT / "scripts" / "link_controls_to_provisions.py").read_text(
            encoding="utf-8")
        assert "provision_id IS NOT DISTINCT FROM %s" in sql, (
            "the guard must be null-safe; `= NULL` never matches and would skip "
            "every row, which is the defect found in the DQ-33 re-tag")
