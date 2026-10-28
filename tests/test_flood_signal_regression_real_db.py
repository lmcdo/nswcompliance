"""Real-database check for scripts/flood_signal_regression.py.

Opt-in, like tests/test_drawdown_verify_real_db.py:
    PYTEST_REAL_DB=1 pytest -m database tests/test_flood_signal_regression_real_db.py -o addopts=

Read-only. Proves the latest-per-address query returns real flood inputs that
the rule can score, and that it picks the same row on every run -- the
regression gate compares a baseline with a later run, so an unstable pick would
report changes that are not there.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
pytestmark = pytest.mark.database


@pytest.fixture(scope="module")
def reg():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_flood_signal_regression_real_db.py -o addopts=")
    import flood_signal_regression as reg
    return reg


def test_latest_rows_are_real_scorable_flood_inputs(reg):
    rows = reg.load_latest()
    assert len(rows) > 0, "no saved flood checks found"
    addresses = [a for a, _ in rows]
    assert len(addresses) == len(set(addresses)), "more than one row per address"
    assert not any(a.lower().startswith("calibration ") for a in addresses)
    for _, o in rows:
        assert "epi_flood_class" in o
        assert reg.score(o)["signal"] in reg.LEVEL


def test_latest_pick_is_stable_between_runs(reg):
    first = {a: o for a, o in reg.load_latest()}
    second = {a: o for a, o in reg.load_latest()}
    assert first == second
