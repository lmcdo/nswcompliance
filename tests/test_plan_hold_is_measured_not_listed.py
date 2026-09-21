"""A council stayed held after its chapters were repaired, because the hold was a list.

`HELD_BACK` was a literal dict of five councils, four of them held for DQ-70 staleness.
Measured 2026-09-20, right after the OCR re-read of city_of_sydney/section-3 landed:
DQ-70 fell 151 -> 59, city_of_sydney, georges_river and woollahra reached ZERO stale
chapters — and all three were still skipped, because a literal does not re-measure.

Three councils blocked from a confirmation they qualified for, by a constant nobody had
reason to revisit. OC-17's plan-in-force sub-check could not fall while it stood.

The dict also said northern_beaches' monitored URL "is pinned to the 2016 file and can
never change". That stopped being true in #1139, which re-pointed it at the council's
live ePlanning export — the block held while its stated reason had already expired.

Staleness is derivable from the same columns DQ-70 reads, so it is measured now. What
stays declared is the one thing the database cannot express: Part G10 commenced on
15 September 2025 and our Northern Beaches copy predates it.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "confirm_plan_in_force.py").read_text(encoding="utf-8")


def _mod():
    import confirm_plan_in_force
    return confirm_plan_in_force


class TestStalenessIsMeasured:
    def test_the_stale_councils_are_no_longer_listed_by_name(self):
        """Each of these was held by a literal and each is now derivable. A name back in
        the dict means the hold has stopped tracking the repair again."""
        m = _mod()
        for council in ("city_of_sydney", "georges_river", "woollahra", "ku_ring_gai"):
            assert council not in m.HELD_BACK, (
                f"{council} is hardcoded again — it will stay held after its chapters "
                f"are repaired, which is the defect this replaced")

    def test_the_hold_is_read_from_the_registry_at_run_time(self):
        m = _mod()
        sql = m.STALE_CHAPTERS_SQL
        assert "content_hash <> provisions_extracted_from_hash" in sql
        assert "is_active" in sql
        assert "GROUP BY council" in sql

    def test_it_uses_the_same_columns_DQ_70_does(self):
        """If the two drift, a council can be released here while the ledger still counts
        its rows as stale -- a confirmation contradicting the measurement beside it."""
        import re

        import dq_probe_live

        # Read the BUILT query, not the file. The probe assembles its SQL from adjacent
        # string literals, so no clause appears contiguously in the source -- which is
        # exactly how this test failed on its first version.
        entry = dq_probe_live.PROBES["DQ-70"]
        sql = next(x for x in entry if isinstance(x, str) and "SELECT" in x.upper())

        # DQ-70 joins two tables so its columns carry "r." / "p." aliases; the hold
        # reads one table and does not. Strip the aliases explicitly rather than with a
        # pattern -- the pattern version silently did nothing and the test failed for a
        # reason that had nothing to do with the code under test.
        def norm(t):
            for alias in ("r.", "p.", "q.", "a.", "s.", "t.", "x."):
                t = t.replace(alias, "")
            return " ".join(t.split())

        dq70, hold = norm(sql), norm(_mod().STALE_CHAPTERS_SQL)
        for clause in ("provisions_extracted_from_hash IS NOT NULL",
                       "content_hash IS NOT NULL",
                       "content_hash <> provisions_extracted_from_hash"):
            assert clause in dq70, f"DQ-70 no longer contains {clause!r}"
            assert clause in hold, f"the hold no longer matches DQ-70 on {clause!r}"

    def test_a_stale_council_is_still_skipped(self):
        """The point is not to release everything. The derived hold must still refuse a
        council whose chapters have moved, or it would confirm a plan while serving text
        from a superseded copy."""
        assert 'elif lga in stale:' in SRC
        assert "re-read pending" in SRC

    def test_the_skip_names_the_measured_count(self):
        """The old message said ku_ring_gai had 8 stale chapters; it has 2. A number
        printed from a literal drifts silently."""
        assert "{n} chapter(s) moved since extraction" in SRC


class TestWhatStaysDeclaredStaysDeclared:
    def test_northern_beaches_is_still_held(self):
        """Its reason is a legal fact, not a hash: Part G10 commenced 15 September 2025
        and our copy predates it. Nothing in the registry says that, so nothing can
        derive it — it must stay written down."""
        m = _mod()
        assert "northern_beaches" in m.HELD_BACK
        assert "G10" in m.HELD_BACK["northern_beaches"]

    def test_its_reason_no_longer_claims_the_url_cannot_change(self):
        """It said the monitored URL 'is pinned to the 2016 file and can never change'.
        #1139 re-pointed it at the council's live ePlanning export. The block still
        holds; that justification for it does not."""
        m = _mod()
        reason = m.HELD_BACK["northern_beaches"]
        assert "can never change" not in reason
        assert "2016" not in reason

    def test_the_declared_list_stays_small(self):
        """It is the escape hatch for facts the data cannot hold. If it grows, holds are
        being hardcoded again rather than measured."""
        assert len(_mod().HELD_BACK) <= 2
