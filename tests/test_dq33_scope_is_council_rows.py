"""DQ-33 counted rows no repair could ever reach, so it could never reach zero.

The ratchet subtracts a floor of 1,278 — the residue the 2026-08-01 retag deliberately
left — from every served row reading `no_config`. But that population is not the one the
retag worked on. `scripts/retag_applicability_slug_docids.py` selects
`WHERE source_council = ANY(%s)`, so it only ever touched rows WITH a council, while the
check also counted 4,887 statewide LEP and SEPP rows. Those have no council whose config
could resolve them: for a statewide instrument `no_config` is the permanent honest answer,
not a defect. The check therefore reported 5,595 and could not fall below 4,887 no matter
what anyone fixed.

A ratchet that cannot reach zero measures nothing, and a number that large hid the 708
council rows that ARE the defect.

Two failures this file exists to catch, because they are opposite and both plausible:
widening it back to every served row, and narrowing it so far that it reads zero. A
narrowing that produces zero is deleting a check, not fixing one — the test that this
change is a correction is that the number still moves.

Pure: reads the probe's own SQL. The real-DB counts that justify it are recorded in the
commit and in the probe's explanation, measured 2026-09-19.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "dq_probe_live.py").read_text(encoding="utf-8")


def _dq33_block() -> str:
    m = re.search(r'"DQ-33":\s*\((.*?)\n    \),\n', SRC, re.S)
    assert m, "the DQ-33 entry could not be located in dq_probe_live.py"
    return m.group(1)


def _dq33_sql() -> str:
    block = _dq33_block()
    m = re.search(r'"(SELECT GREATEST[^"]*(?:"\s*\n\s*"[^"]*)*)"', block, re.S)
    assert m, f"the DQ-33 query could not be located:\n{block[:400]}"
    return " ".join(re.sub(r'"\s*\n\s*"', "", m.group(1)).split())


class TestItAsksOnlyWhereTheAnswerCanChange:
    def test_the_query_is_scoped_to_rows_that_have_a_council(self):
        """Without this it counts 4,887 statewide rows whose no_config is permanent."""
        assert "source_council IS NOT NULL" in _dq33_sql(), _dq33_sql()

    def test_it_still_reads_the_field_it_is_about(self):
        """Guards the guard: scoping must not quietly change WHAT is measured."""
        sql = _dq33_sql()
        assert "v2_dev_type_source = 'no_config'" in sql
        assert "is_current" in sql and "v2_is_actionable" in sql

    def test_the_floor_is_unchanged(self):
        """1,278 is the residue the retag deliberately left, and it sits entirely inside
        the council population — which is exactly why subtracting it from the council-
        scoped count is correct rather than double-counting. Moving the floor to make a
        number look better is the failure this ledger exists to catch."""
        assert "GREATEST(count(*) - 1278, 0)" in _dq33_sql()

    def test_the_scope_matches_the_repair_it_ratchets(self):
        """Read from the repair, not assumed: if that script ever starts touching rows
        without a council, this scope is wrong and the two must move together."""
        retag = (ROOT / "scripts" / "retag_applicability_slug_docids.py").read_text(
            encoding="utf-8")
        assert "WHERE source_council = ANY(%s)" in retag, (
            "the retag no longer scopes itself to councils, so DQ-33's council-only "
            "scope no longer matches the population its floor was measured on")


class TestItCannotBeQuietlyEmptied:
    def test_the_explanation_says_what_was_excluded_and_why(self):
        """A scope change that is not written down reads as a check going green."""
        block = _dq33_block()
        assert "4,887" in block, "the excluded population is not named in the probe text"
        assert "statewide" in block or "LEP/SEPP" in block
        assert "retag only touched those" in block or "only ever touched" in block

    def test_it_is_not_scoped_to_a_single_council_or_document(self):
        """The opposite failure to over-counting: a filter narrow enough to read zero
        would delete the check while looking like a fix."""
        sql = _dq33_sql()
        for over in ("source_council =", "source_council IN", "document_id =",
                     "source_chapter_key ="):
            assert over not in sql, f"DQ-33 is narrowed to a specific {over.split()[0]}"

    def test_the_separate_untagged_gap_is_still_declared(self):
        """10,103 served rows have a NULL v2_dev_type_source and were never tagged at
        all. They are out of scope here and must stay named, or this scoping reads as
        having covered them."""
        assert "10,103" in _dq33_block()


@pytest.mark.database
class TestAgainstTheRealDatabase:
    """The counts the scoping rests on. Opt-in, as this repo does it:

        PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database \\
            tests/test_dq33_scope_is_council_rows.py -o addopts=
    """

    @staticmethod
    def _rows():
        import os
        if os.environ.get("PYTEST_REAL_DB") != "1":
            pytest.skip("needs PYTEST_REAL_DB=1 and a live DATABASE_URL")
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv(ROOT.parents[2] / ".env")
        url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
        if not url:
            pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL available")
        conn = psycopg2.connect(url, connect_timeout=20)
        try:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '60s'")
                cur.execute("""
                    SELECT count(*) FILTER (WHERE source_council IS NOT NULL),
                           count(*) FILTER (WHERE source_council IS NULL)
                    FROM regulatory_provisions
                    WHERE is_current AND v2_is_actionable
                      AND v2_dev_type_source = 'no_config'
                """)
                return cur.fetchone()
        finally:
            conn.close()

    def test_the_statewide_rows_really_are_the_bulk_of_what_was_counted(self):
        council, statewide = self._rows()
        assert statewide > council, (
            f"the premise of this change is that statewide rows dominated the count; "
            f"measured council={council}, statewide={statewide}")

    def test_the_scoped_check_is_NOT_zero(self):
        """The whole test of whether this is a correction or a whitewash. If scoping
        takes it to zero, the check has been deleted and should be argued for on those
        terms instead."""
        council, _ = self._rows()
        assert council > 1278, (
            f"scoped to councils the check now reads 0 ({council} <= the 1,278 floor). "
            f"That is not a fix — re-open the scoping decision.")
