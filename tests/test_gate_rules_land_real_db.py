"""gate_rules_land against the REAL production schema, read-only (dry run)."""
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


def test_every_entry_reads_the_real_schema_and_a_dry_run_writes_nothing(ro_cursor):
    import gate_rules_land as g
    changes = g.apply_land_limits(ro_cursor, None, apply=False)
    assert all(c[4] == "land_limits" and c[1] in ("v2_marker", "v2_applicable_zones", "v2_dcp_layer") for c in changes)
    # Every listed zone must exist in its council's LEP table (the same check the writer raises on).
    for e in g.entries():
        if e["kind"] == "zones":
            assert g._zones_ok(ro_cursor, e["council"], e["zones"]), e
