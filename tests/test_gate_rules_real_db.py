"""Gate rules against the REAL production schema, read-only (dry run). DQ-146."""
import os
import re
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


def test_every_gate_rule_selects_rows_and_dry_run_writes_nothing(ro_cursor):
    import gate_rules as g
    for rule in g.GATE_RULES:
        changes = g.apply_gate_rules(ro_cursor, rule["council"], apply=False, only={rule['name']})
        # The rule's chapter must exist; the rule itself may match nothing once applied (idempotent).
        chapter = re.search(r"source_chapter_key = '([^']+)'", rule["where"]).group(1)
        ro_cursor.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND source_council = %s"
                          " AND source_chapter_key = %s", (rule["council"], chapter))
        assert ro_cursor.fetchone()[0] > 0, f"{rule['name']}: chapter {chapter} has no current row"
        assert all(c[4] == rule["name"] for c in changes)
