"""DQ-128: a former council's plan must not be registered under the merged council it rolled into.

The registry's council is copied into regulatory_provisions.source_council by dcp_extract_changed.py, so a
Marrickville chapter registered as 'inner_west' served 10 rules under the wrong slug. The unit tests feed
a fake cursor; the real-DB test reads lga_registry and runs only when asked for:

    PYTEST_REAL_DB=1 pytest -m database tests/test_register_orphan_chapters_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from dq_db import main_checkout  # noqa: E402

_REAL_DB = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB:
    load_dotenv(main_checkout() / ".env")

import register_orphan_chapters as roc  # noqa: E402

FORMER = [{"slug": "marrickville", "display_name": "Marrickville"},
          {"slug": "ashfield", "display_name": "Ashfield"}]


class _Cur:
    def __init__(self, rows):
        self.rows, self.sql = rows, None

    def execute(self, sql, params=None):
        self.sql, self.params = sql, params

    def fetchall(self):
        return self.rows


def test_a_former_councils_plan_under_the_parent_is_refused():
    cur = _Cur(FORMER)
    assert roc.former_council_owner(cur, "inner_west", "Marrickville DCP 2011") == "marrickville"
    assert "is_active = TRUE" in cur.sql and cur.params == ("inner_west",)


def test_the_councils_own_plan_is_not_refused():
    assert roc.former_council_owner(_Cur(FORMER), "inner_west", "Inner West DCP 2016") is None


def test_a_name_that_only_starts_with_the_same_letters_is_not_refused():
    """'Ashfield' must not claim 'Ashfieldvale DCP' -- the match is on a whole word."""
    assert roc.former_council_owner(_Cur(FORMER), "inner_west", "Ashfieldvale DCP 2001") is None


def test_missing_inputs_refuse_nothing():
    assert roc.former_council_owner(_Cur(FORMER), "", "Marrickville DCP 2011") is None
    assert roc.former_council_owner(_Cur(FORMER), "inner_west", None) is None


def test_no_inner_west_former_council_chapter_is_listed_for_registration():
    bad = [(c, k, n) for c, k, n, _l, _u in roc.NEW_CHAPTERS
           if c == "inner_west" and n.split(" ")[0] in ("Ashfield", "Leichhardt", "Marrickville")]
    assert not bad, f"re-registers DQ-128's duplicates: {bad}"


@pytest.mark.database
def test_real_registry_refuses_marrickville_under_inner_west():
    if not _REAL_DB:
        pytest.skip("Real-DB test. Run with PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_register_orphan_chapters_real_db.py -o addopts=")
    import psycopg2
    from psycopg2.extras import RealDictCursor
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        assert roc.former_council_owner(cur, "inner_west", "Marrickville DCP 2011") == "marrickville"
        assert roc.former_council_owner(cur, "inner_west", "Leichhardt DCP 2013") == "leichhardt"
        assert roc.former_council_owner(cur, "hornsby", "Hornsby DCP 2024") is None
    finally:
        conn.close()
