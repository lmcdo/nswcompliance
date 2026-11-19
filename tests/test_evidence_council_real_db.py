"""Real-database check of the council data for the evidence page. Opt in:
PYTEST_REAL_DB=1 DATABASE_URL=... pytest tests/test_evidence_council_real_db.py -o addopts= -m database

conftest_mocks stubs psycopg2 by default, so the flag is required; without it the test skips (never passes). Read-only."""
import os

import pytest

from services import evidence_council as ec


def _need_db():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... -o addopts= -m database; skipped, not a pass")


@pytest.mark.database
def test_penrith_controls_are_read_with_words_clause_and_page():
    _need_db()
    out = ec.council_controls("PENRITH")
    assert out["status"] == "ok", out
    assert out["council"] == "penrith"
    assert out["controls"]
    assert all(c["council_words"] and c["page"] for c in out["controls"])


@pytest.mark.database
def test_penrith_files_have_one_current_file_per_chapter_and_old_ones_have_no_date():
    _need_db()
    out = ec.council_files("PENRITH")
    assert out["status"] == "ok", out
    chapters = {f["chapter"] for f in out["files"]}
    assert len(chapters) >= 1
    for ch in chapters:
        assert sum(1 for f in out["files"] if f["chapter"] == ch and f["current"]) == 1
    assert all(f["council_file_date"] is None for f in out["files"] if not f["current"])
