"""scripts/verify_lga_capability_flags.py's DB-touching functions, verified
against the REAL database -- not conftest_mocks.py's psycopg2 stub.

tests/test_verify_lga_capability_flags.py already covers the pure decision
logic (find_drift) with no database at all. It does NOT, and cannot, prove
that check_has_dcp_data / check_has_flood_data issue SQL that actually runs
against the real schema and returns the counts this script's own
investigation found on 2026-09-10 -- a mocked cursor would happily return
whatever a test tells it to, which proves the Python is well-formed and
nothing about whether dcp_setback_controls.lga, lga_registry.parent_lga, or
spatial_overlays.lga_name are spelled the way the queries assume.

Opt-in via PYTEST_REAL_DB=1, @pytest.mark.database (deselected by default per
pytest.ini), matching the convention tests/test_lga_coverage.py and
tests/test_drawdown_verify_real_db.py already use -- the default `pytest` run
this repo uses everywhere else is completely unaffected.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_verify_lga_capability_flags_real_db.py -v

These tests pin known-true facts about the LIVE database as of 2026-09-10, not
facts about this script. If Lane Cove later gets real dcp_setback_controls
rows, or Blacktown gets a spatial_overlays flood row, the corresponding test
below should start failing -- and that failure means the underlying real-world
drift this script exists to catch has been fixed, not that the test is wrong.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    from dotenv import load_dotenv
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "verify_lga_capability_flags.py"
_spec = importlib.util.spec_from_file_location("verify_lga_capability_flags_real_db_under_test", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_verify_lga_capability_flags_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


@pytest.fixture(scope="module")
def real_cursor():
    _skip_if_no_real_db()
    from dq_db import connect
    conn = connect()
    cur = conn.cursor()
    yield cur
    conn.close()


class TestHasDcpDataAgainstRealSchema:
    def test_blacktown_has_current_setback_controls(self, real_cursor):
        """A known-good council: Blacktown has 33 current dcp_setback_controls
        rows (measured 2026-09-10). Proves the query's column names and JOIN
        actually resolve against the live schema, not just a mock's promise."""
        cnt, detail = _mod.check_has_dcp_data(real_cursor, "blacktown")
        assert cnt > 0, f"Blacktown regressed to zero: {detail}"

    def test_lane_cove_has_zero_setback_controls_today(self, real_cursor):
        """The real, pre-existing drift this script's first run found: Lane
        Cove claims hasDcpData: true in verify-lgas.ts with zero backing rows.
        If this starts failing, someone fixed the data -- update verify-lgas.ts
        and this test together, do not just delete the assertion."""
        cnt, detail = _mod.check_has_dcp_data(real_cursor, "lane-cove")
        assert cnt == 0, f"Lane Cove now has data ({detail}) -- update verify-lgas.ts's hasDcpData claim and this test"

    def test_inner_west_merger_credit_reaches_its_absorbed_councils(self, real_cursor):
        """Inner West's OWN dcp_setback_controls rows are not current (0 of
        29) -- its current controls live under ashfield/leichhardt/marrickville,
        the councils it absorbed in the 2016 merger. The query must count
        those via parent_lga, or a real, currently-served council would be
        wrongly flagged as drift the day this ships."""
        cnt, detail = _mod.check_has_dcp_data(real_cursor, "inner-west")
        assert cnt > 0, f"Inner West merger credit broke: {detail}"

    def test_the_hills_shire_slug_override_resolves(self, real_cursor):
        """the-hills-shire's lga_registry slug is 'the_hills', not
        'the_hills_shire' -- confirmed by querying lga_registry directly. A
        naive hyphen-to-underscore swap here would silently look up a slug
        that has never existed and report every Hills Shire claim as drift."""
        cnt, detail = _mod.check_has_dcp_data(real_cursor, "the-hills-shire")
        assert cnt > 0, f"The Hills Shire override broke: {detail}"


class TestHasFloodDataAgainstRealSchema:
    def test_campbelltown_has_spatial_overlays_flood_rows(self, real_cursor):
        """Campbelltown is the largest flood dataset in the table (26,054+
        rows measured 2026-09-10) -- the clearest possible proof the query's
        layer_type/lga_name filter actually matches real rows."""
        cnt, detail = _mod.check_has_flood_data(real_cursor, "Campbelltown")
        assert cnt > 0, f"Campbelltown flood data disappeared: {detail}"

    def test_blacktown_has_zero_spatial_overlays_flood_rows_today(self, real_cursor):
        """Blacktown claims hasFloodData: false in granny-flat-lgas.ts, and
        has no 'BLACKTOWN' rows in spatial_overlays' flood layer -- this is
        the exact case used to prove the check can fail (see the PR): flipping
        Blacktown's flag to true and re-running the script produced a DRIFT
        finding naming Blacktown/hasFloodData with 0 rows, then the file was
        restored and the finding disappeared."""
        cnt, detail = _mod.check_has_flood_data(real_cursor, "Blacktown")
        assert cnt == 0, f"Blacktown now has flood data ({detail}) -- the injection proof in the PR needs a different council"
