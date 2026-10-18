"""dcp_area_link_guard against the live database, read-only: the live chapter's own links are re-linkable.

prior-art-checked: real-layer twin of test_dcp_area_link_guard.py, same fixture as test_build_site_boundaries_real_db.
"""
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
    conn = dq_db.connect()
    try:
        yield conn.cursor()
    finally:
        conn.close()


def test_a_rule_keyed_live_chapter_passes_its_own_guard(ro_cursor):
    """Marrickville Precinct 8: every live rule is keyed by the doc_regex rule, so live -> live is kept in full."""
    import dcp_area_link_guard as g
    before = g.linked_count(ro_cursor, "marrickville", "part9-p08-enmore-north")
    after = g.relinkable_count(ro_cursor, "marrickville", "part9-p08-enmore-north")
    assert before.area >= 5
    assert g.judge(before.area, after.area) and g.judge(before.zone, after.zone)
