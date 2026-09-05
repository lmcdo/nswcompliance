"""DQ-96's _fetch_standards_grouped() change, verified against the REAL
psycopg2 driver and the REAL production database -- not conftest_mocks.py's
MagicMock stub, and not tests/test_housing_sepp_eligibility.py's hand-built
Cur/Conn fakes.

Required by the generic real-DB/HTTP test gate (feat/generic-real-db-
verification-requirement, #1041): a changed function that touches psycopg2
must have a test that exercises it against the real driver, or the gate
blocks the push. This branch's change extended _fetch_standards_grouped()'s
SELECT to add two new columns (stale_since, stale_reason) to
housing_sepp_standards -- the fake-cursor tests in
test_housing_sepp_eligibility.py prove the GROUPING logic (latest-wins,
paired reason) but, being fakes, cannot catch a real SQL error (a typo'd
column name, a type mismatch) against the live schema. This file closes
that specific gap.

Opt-in via PYTEST_REAL_DB=1, @pytest.mark.database (deselected by default
per pytest.ini), matching this repo's own established convention (see
tests/test_drawdown_verify_real_db.py, tests/test_lga_coverage.py) rather
than inventing a new one.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_housing_sepp_eligibility_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# prior-art-checked: reuse, not reinvention -- same main_checkout() lookup
# tests/test_drawdown_verify_real_db.py already established for finding the
# right .env from inside a worktree (a naive load_dotenv('.env') silently
# falls through to localhost defaults from a worktree, which has no .env of
# its own).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

# Same ordering discipline as test_drawdown_verify_real_db.py (Sol #839-
# adjacent finding on that file): only load .env -- and thus only put a real
# DATABASE_URL in-process -- when the real-DB run was explicitly requested.
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

import services.housing_sepp_eligibility as hse  # noqa: E402


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_housing_sepp_eligibility_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


class TestFetchStandardsGroupedAgainstRealSchema:
    def test_query_is_valid_against_the_live_schema_and_returns_the_new_columns(self):
        """The load-bearing proof: the real SELECT (11 columns, including the
        2 this branch added) executes against production without a SQL
        error, and every group in the returned dict carries stale_since/
        stale_reason keys -- present even when their value is None, which is
        the correct state for all 45 rows today (verified live 2026-09-05,
        DQ-96: 0 rows currently have stale_since set)."""
        _skip_if_no_real_db()
        grouped = hse._fetch_standards_grouped()
        assert grouped, "housing_sepp_standards returned no rows at all -- table empty or unreachable"
        for dev_type, g in grouped.items():
            assert "stale_since" in g, f"{dev_type} group missing stale_since key"
            assert "stale_reason" in g, f"{dev_type} group missing stale_reason key"
            # Live state as of 2026-09-05 (DQ-96): no row has been stamped
            # yet, so every group should read None -- if this ever flips to
            # a real value, that is real production data, not a bug.
            # _fetch_standards_grouped's own contract keeps this as a raw
            # datetime (isoformat happens later, in _result() -- see the
            # datetime-vs-string bug this same branch caught and fixed).
            if g["stale_since"] is not None:
                import datetime as _dt
                assert isinstance(g["stale_since"], _dt.datetime), (
                    "_fetch_standards_grouped must return a raw datetime here "
                    "(isoformat conversion happens in _result(), not here) -- "
                    f"got {type(g['stale_since'])}"
                )
