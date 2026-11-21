"""Real-database check of the compare's lot sample, and a small real compare. Opt in:
PYTEST_REAL_DB=1 PYTEST_REAL_HTTP=1 DATABASE_URL=... pytest tests/test_check_map_copy_real_db.py -o addopts= -m database

conftest_mocks stubs psycopg2 and requests by default, so both flags are required; without them the tests skip (never pass). Read-only."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "lmr_area"))
import check_map_copy as cm  # noqa: E402


def _need(http: bool = False):
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... -o addopts= -m database; skipped, not a pass")
    if http and os.environ.get("PYTEST_REAL_HTTP") != "1":
        pytest.skip("live comparison needs PYTEST_REAL_HTTP=1 (otherwise requests is a stand-in); skipped, not a pass")


@pytest.mark.database
def test_the_sample_returns_real_lots_with_closed_outlines_inside_nsw():
    _need()
    lots = cm._sample_lots(8, 20261121)
    assert len(lots) == 8
    for lot in lots:
        assert -38 < lot["lat"] < -28 and 140 < lot["lng"] < 154.5       # noqa: regulatory-number -- NSW bounds in a test, not a planning figure
        assert len(lot["rings"]) >= 4 and lot["rings"][0] == lot["rings"][-1]


@pytest.mark.database
def test_a_small_real_compare_finds_no_unflagged_difference():
    _need(http=True)
    ok, lines = cm.compare(6, 20261121)
    assert ok, lines
