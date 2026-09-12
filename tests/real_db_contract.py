"""Shared helper for the DCP scripts' real-layer tests.

WHAT A REAL-LAYER TEST IS FOR HERE
----------------------------------
Every one of these scripts reads production and reports a number. None of them
writes anything a user sees, except dcp_restore_section_codes, which writes only
under --apply. So the risk is not corruption -- it is a script that goes on
printing a number after the schema underneath it has moved, and the number stops
meaning what its caller thinks.

That is not hypothetical in this repo. DQ-97's probe read green for a day on
2026-09-10 because its population had been drained rather than repaired, and
`former_council` / `source_ref` are named in CLAUDE.md as columns several scripts
still assume exist on regulatory_provisions and which do not.

So each test asserts the same two things against the live database:

  1. every column the script names still EXISTS on the table it reads;
  2. the script's own scoping predicate still selects a non-empty set, or the
     test says plainly that it selects nothing -- which is a finding, not a pass.

Deselected by default and marked `database`. The PYTEST_REAL_DB opt-in matters:
conftest_mocks stubs psycopg2, so without it every assertion here would run
against a MagicMock and pass for the wrong reason.

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dcp_chapter_measure_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def database_url() -> str:
    from scripts.check_council_completeness import _load_env
    _load_env()
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("no DATABASE_URL")
    return url


def connect():
    import psycopg2
    conn = psycopg2.connect(database_url(), connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout='60s'")
    return conn, cur


def columns_of(table: str) -> set[str]:
    conn, cur = connect()
    try:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s", (table,))
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


def assert_columns_exist(table: str, needed: set[str]) -> None:
    """The script names these columns. If one is gone, the script raises at
    runtime in a cron job nobody is watching -- which is how a measurement
    silently stops being taken."""
    present = columns_of(table)
    assert present, "table " + table + " does not exist at all"
    missing = sorted(needed - present)
    assert not missing, (
        table + " no longer has " + str(missing) + " -- a script reads them. "
        "CLAUDE.md already records this failure once: former_council and "
        "source_ref were assumed on regulatory_provisions and do not exist.")


def count_where(table: str, predicate: str, params: tuple = ()) -> int:
    conn, cur = connect()
    try:
        cur.execute("SELECT count(*) FROM " + table + " WHERE " + predicate,
                    params)
        return cur.fetchone()[0]
    finally:
        conn.close()
