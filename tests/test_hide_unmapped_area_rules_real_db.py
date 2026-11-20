"""hide_unmapped_area_rules selectors against the REAL production schema, read-only."""
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


def test_every_selector_runs_against_the_real_table_and_ids_stay_inside_their_chapter(ro_cursor):
    import hide_unmapped_area_rules as h
    for sel in h.selectors():
        where, params = h.where_for(sel)
        ro_cursor.execute("SELECT count(*) FROM regulatory_provisions WHERE " + where, params)
        n = ro_cursor.fetchone()[0]
        assert n >= 0
        if sel.get("ids") and sel.get("no_chapter"):
            # the ids of a no-chapter entry must all be rows with no chapter (NULL), never another chapter's rows
            ro_cursor.execute("SELECT count(*) FROM regulatory_provisions WHERE id = ANY(%s) AND source_chapter_key IS NOT NULL",
                              (sel["ids"],))
            assert ro_cursor.fetchone()[0] == 0
