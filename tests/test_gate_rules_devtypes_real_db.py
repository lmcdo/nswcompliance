"""gate_rules_devtypes against the REAL production schema, read-only (dry run)."""
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
    import gate_rules_devtypes as g
    changes = g.apply_dev_type_limits(ro_cursor, None, apply=False)
    # After the 2026-11-20 apply nothing is left to narrow; a publish that resets rows to ALL makes this go above 0.
    assert all(c[4] == "dev_type_limits" and c[2] == ["ALL"] for c in changes)
    ro_cursor.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND v2_dev_type_source = 'config_all'"
                      " AND v2_applicable_dev_types && ARRAY['signage','commercial_premises','industrial_development']"
                      " AND NOT v2_applicable_dev_types = ARRAY['ALL']")
    assert ro_cursor.fetchone()[0] + len(changes) >= 1833
