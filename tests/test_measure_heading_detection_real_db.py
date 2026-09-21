"""The heading-detection measurement reads the live registry; prove that read works.

scripts/measure_heading_detection.py compares the incumbent regex against a
typography reader, scored on each document's own embedded PDF outline. To do that it
resolves chapters to their R2 paths from dcp_chapter_registry.

That query is the script's only database contact and it is READ-ONLY, but "read-only"
is not "cannot be wrong": a renamed column or a changed is_active convention would
make the measurement silently score nothing and report a clean split, which is the
failure mode the whole script exists to avoid in the extractor.

Skips without PYTEST_REAL_DB=1, because tests/conftest_mocks.py stubs psycopg2 by
default and a mocked cursor would return a MagicMock that passes every assertion
below while proving nothing.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.database

REAL_DB = os.getenv("PYTEST_REAL_DB") == "1" and bool(os.getenv("DATABASE_URL"))
requires_db = pytest.mark.skipif(
    not REAL_DB,
    reason="needs PYTEST_REAL_DB=1 and DATABASE_URL; a stubbed psycopg2 would return "
           "a MagicMock and pass this without touching anything")


@requires_db
def test_the_registry_query_returns_usable_chapters():
    """The columns the script selects must exist and mean what it assumes."""
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT chapter_key, r2_current_path FROM dcp_chapter_registry
                WHERE council = %s AND is_active AND r2_current_path IS NOT NULL
                ORDER BY chapter_key LIMIT 3""", ("woollahra",))
        rows = cur.fetchall()
    finally:
        conn.close()

    assert rows, ("no active woollahra chapter has an r2_current_path -- the "
                  "measurement would report 'nothing measured' and look like a "
                  "clean result")
    for chapter_key, r2_path in rows:
        assert isinstance(chapter_key, str) and chapter_key
        assert isinstance(r2_path, str) and r2_path.endswith(".pdf"), (
            f"r2_current_path {r2_path!r} is not a PDF path; the script would "
            f"download it and fitz would fail on every chapter")


@requires_db
def test_a_council_with_no_rows_is_distinguishable_from_a_broken_query():
    """The script prints 'nothing measured' when it finds no chapters. That must mean
    the council has none, not that the query silently matched nothing for another
    reason -- wollongong and newcastle genuinely hold zero DCP chapters."""
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM dcp_chapter_registry WHERE council = %s",
                    ("wollongong",))
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM dcp_chapter_registry WHERE council = %s",
                    ("woollahra",))
        known_good = cur.fetchone()[0]
    finally:
        conn.close()

    assert known_good > 0, "the table itself is unreadable, not just one council"
    assert total == 0, (
        "wollongong now has registry chapters; this test's premise has changed and "
        "the 'nothing measured' path needs re-checking against a council that is "
        "genuinely empty")
