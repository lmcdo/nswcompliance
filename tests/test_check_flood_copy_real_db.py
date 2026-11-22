"""scripts/lmr_area/check_flood_copy.py against the REAL database and the committed flood copy (opt-in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database -o addopts= ).

conftest_mocks.py stubs psycopg2 by default, so without the opt-in a mock would answer instead of the database and the comparison would mean nothing.
"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

pytestmark = [pytest.mark.skipif(os.environ.get("PYTEST_REAL_DB") != "1", reason="needs PYTEST_REAL_DB=1 and a real DATABASE_URL: psycopg2 is stubbed by default")]


@pytest.mark.database
def test_the_committed_flood_copy_agrees_with_the_database_rows_it_was_made_from(capsys):
    from scripts.lmr_area import check_flood_copy as chk

    code = chk.main(["60"])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "source INSIDE but copy says clear: 0" in out and "flips beyond the margin: 0" in out
    assert "points 60" in out


@pytest.mark.database
def test_the_check_releases_its_connection_even_when_the_comparison_fails(monkeypatch):
    import psycopg2

    from scripts.lmr_area import check_flood_copy as chk

    closed = []
    real_connect = psycopg2.connect

    class Tracked:
        """A real connection behind a thin wrapper that records close(): the driver's own connection object does not allow close to be replaced."""

        def __init__(self, conn):
            self._conn = conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def close(self):
            closed.append(True)
            self._conn.close()

    def tracking_connect(*a, **k):
        return Tracked(real_connect(*a, **k))

    monkeypatch.setattr(psycopg2, "connect", tracking_connect)
    monkeypatch.setattr(chk, "_run", lambda conn, n, rnd: (_ for _ in ()).throw(RuntimeError("comparison failed")))
    with pytest.raises(RuntimeError):
        chk.main(["10"])
    assert closed == [True]
