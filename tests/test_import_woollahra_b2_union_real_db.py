"""Woollahra B2 union loader against the REAL boundaries table, read-only. DQ-146."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = pytest.mark.database
_REAL = os.environ.get("PYTEST_REAL_DB") == "1"


@pytest.fixture
def ro_cursor():
    if not _REAL:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database -o addopts= <file>")
    import dq_db
    conn = dq_db.connect()  # read-only session: a dry run that tried to write would raise
    try:
        yield conn.cursor()
    finally:
        conn.close()


@pytest.mark.parametrize("name,n", [("woollahra_b2", 11), ("krg_14b", 4)])
def test_every_member_outline_exists(ro_cursor, name, n):
    import import_woollahra_b2_union as m
    u = m.UNIONS[name]
    ro_cursor.execute("SELECT count(*) FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = ANY(%s)",
                      (u["lga"], list(u["members"])))
    assert ro_cursor.fetchone()[0] == len(u["members"]) == n
