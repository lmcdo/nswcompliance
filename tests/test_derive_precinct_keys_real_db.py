"""Woollahra neighbourhood-HCA and Paddington keying rules against the REAL production rows, read-only. DQ-146."""
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


def test_b2_rules_partition_the_chapter(ro_cursor):
    import derive_precinct_keys as dpk
    rules = [r for r in dpk.RULES if r["name"].startswith("woollahra_b2")]
    ro_cursor.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND source_council = %s"
                      " AND source_chapter_key = %s", ("woollahra", "chapter-b2-neighbourhood-hcas"))
    total = ro_cursor.fetchone()[0]
    matched = 0
    for r in rules:
        ro_cursor.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND source_council = %s"
                          f" AND ({r['where']})", ("woollahra",))
        matched += ro_cursor.fetchone()[0]
    assert total > 0 and matched == total  # every B2 row keyed exactly once
