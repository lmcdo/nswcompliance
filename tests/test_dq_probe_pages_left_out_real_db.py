"""DQ-112 probe against the real database: every served chapter is checked once.

A join that drops a chapter (no active registry PDF) would hide its gaps; one
that duplicates it would double-count. Opt-in, like every real-DB test here:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dq_probe_pages_left_out_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1",
                       reason="real-DB test: set PYTEST_REAL_DB=1 and DATABASE_URL"),
]


@pytest.fixture(scope="module")
def conn():
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    c = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    yield c
    c.close()


def test_every_served_chapter_is_listed_once_with_a_pdf(conn):
    import dq_probe_pages_left_out as p
    cur = conn.cursor()
    cur.execute(p.CHAPTERS_SQL, {"council": None})
    rows = cur.fetchall()
    keys = [(r[0], r[1]) for r in rows]
    assert len(keys) == len(set(keys)), "a chapter joined more than one active PDF"
    assert all(r[2] for r in rows)
    cur.execute("SELECT count(DISTINCT (source_council, source_chapter_key)) FROM regulatory_provisions "
                "WHERE is_current AND source_council IS NOT NULL AND source_chapter_key IS NOT NULL")
    assert len(keys) == cur.fetchone()[0], "a served chapter has no active registry PDF and is never checked"


def test_the_chapter_text_query_reads_only_that_chapter(conn):
    import dq_probe_pages_left_out as p
    cur = conn.cursor()
    cur.execute(p.CHAPTERS_SQL, {"council": "woollahra"})
    council, chapter, _ = cur.fetchone()
    cur.execute(p.TEXT_SQL, (council, chapter))
    got = len(cur.fetchall())
    cur.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND source_council=%s "
                "AND source_chapter_key=%s", (council, chapter))
    assert got == cur.fetchone()[0] > 0
