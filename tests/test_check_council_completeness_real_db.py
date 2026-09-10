"""The completeness check against the REAL driver and the REAL database.

tests/test_check_council_completeness.py tests the judgement -- compare() over
constructed numbers. It cannot catch a wrong column name, a predicate that means
something different in Postgres than it reads like in Python, or a snapshot row
that does not survive the JSONB round trip. Those need the real thing.

Opt-in, per the convention in tests/test_lga_coverage.py and
tests/test_drawdown_verify_real_db.py: conftest_mocks.py stubs psycopg2 unless
PYTEST_REAL_DB=1, so without the flag this file would be asserting against a
MagicMock. Deselected by default via @pytest.mark.database (pytest.ini).

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \\
        tests/test_check_council_completeness_real_db.py -v

WHAT IT WRITES. Only dcp_council_field_snapshot, only rows whose council is the
sentinel below, and it deletes them by id in a finally. It never writes to
regulatory_provisions or to a real council's snapshot history -- a test that
inserted a baseline for a real council would change what the next production run
compares against, which is the one thing this table must not have done to it.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Reuse rather than repeat: scripts/dq_db.py already solved "find the .env from
# inside a worktree", which has none of its own.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

#: Cannot collide with a real source_council: those are lowercase slugs with no
#: prefix, and this row is deleted by id regardless.
SENTINEL = "zz_completeness_selftest"


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_check_council_completeness_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _module():
    import check_council_completeness as ccc
    return ccc


def _connect():
    import psycopg2
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    conn = psycopg2.connect(url, connect_timeout=15)
    conn.cursor().execute("SET statement_timeout = '30s'")
    return conn


def test_the_snapshot_table_exists_with_the_columns_the_checker_writes():
    """Migration 068 must have been applied. If it has not, every production run
    degrades to the '[warn] completeness check failed' branch in
    dcp_commit_approved -- which is a warning, not a failure, so nothing would
    ever say the check had stopped working."""
    _skip_if_no_real_db()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_schema='public' AND table_name='dcp_council_field_snapshot'"""
        )
        cols = {r[0] for r in cur.fetchall()}
        assert cols >= {"id", "taken_at", "trigger_source", "council", "served", "counts"}, (
            f"dcp_council_field_snapshot is missing columns: {cols}. "
            f"Has migrations/068_council_field_snapshot.sql been applied?"
        )
    finally:
        conn.close()


def test_measure_returns_real_councils_with_the_watched_fields():
    """Every predicate in WATCHED_FIELDS has to be valid SQL against the live
    schema. A misspelled column here raises rather than returning zeros -- but
    only when something actually executes it."""
    _skip_if_no_real_db()
    ccc = _module()
    conn = _connect()
    try:
        got = ccc.measure(conn.cursor())
        assert got, "no councils measured -- the served-set filter matched nothing"
        for council, m in got.items():
            assert m["served"] > 0
            assert set(m["counts"]) == set(ccc.WATCHED_FIELDS)
            for field, n in m["counts"].items():
                assert 0 <= n <= m["served"], (
                    f"{council}/{field}: {n} populated of {m['served']} served -- "
                    f"a fill count above the denominator means the predicate is wrong"
                )
    finally:
        conn.close()


def test_scoping_to_one_council_returns_only_that_council():
    """--council is the one value that comes from outside, and it is passed as a
    bind parameter. Asserted because the surrounding SELECT interpolates column
    names, so it would be easy to 'match the style' and interpolate this too."""
    _skip_if_no_real_db()
    ccc = _module()
    conn = _connect()
    try:
        got = ccc.measure(conn.cursor(), ["ashfield"])
        assert set(got) == {"ashfield"}
    finally:
        conn.close()


def test_a_recorded_snapshot_survives_the_jsonb_round_trip():
    """counts goes out as a dict and must come back as one. If psycopg2 returned
    a string here, load_previous's isinstance check would treat every baseline as
    absent and the check would report NO_BASELINE forever -- silently passing."""
    _skip_if_no_real_db()
    ccc = _module()
    from psycopg2.extras import Json
    conn = _connect()
    ids = []
    try:
        cur = conn.cursor()
        payload = {f: i for i, f in enumerate(ccc.WATCHED_FIELDS)}
        cur.execute(
            """INSERT INTO dcp_council_field_snapshot
                   (trigger_source, council, served, counts)
               VALUES ('manual', %s, 100, %s) RETURNING id""",
            (SENTINEL, Json(payload)),
        )
        ids.append(cur.fetchone()[0])
        conn.commit()

        prev = ccc.load_previous(cur, SENTINEL)
        assert prev is not None, "a row was just inserted and load_previous did not find it"
        assert prev["served"] == 100
        assert prev["counts"] == payload
    finally:
        if ids:
            cur.execute("DELETE FROM dcp_council_field_snapshot WHERE id = ANY(%s)", (ids,))
            conn.commit()
        conn.close()


def test_a_council_recorded_and_then_absent_is_reported_as_gone():
    """The sentinel has a snapshot but no provisions, which is exactly the shape
    of a council whose rows all disappeared. run() finds it by comparing the
    recorded set against the measured set -- a council that is gone cannot be
    found by iterating what exists."""
    _skip_if_no_real_db()
    ccc = _module()
    from psycopg2.extras import Json
    conn = _connect()
    ids = []
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO dcp_council_field_snapshot
                   (trigger_source, council, served, counts)
               VALUES ('manual', %s, 500, %s) RETURNING id""",
            (SENTINEL, Json({f: 500 for f in ccc.WATCHED_FIELDS})),
        )
        ids.append(cur.fetchone()[0])
        conn.commit()

        rc = ccc.run(trigger_source="manual", councils=[SENTINEL],
                     record=False, alert=False)
        assert rc == 2, (
            "a council with a 500-row baseline and no live rows must be a finding; "
            f"run() returned {rc}"
        )
    finally:
        if ids:
            cur.execute("DELETE FROM dcp_council_field_snapshot WHERE id = ANY(%s)", (ids,))
            conn.commit()
        cur.execute("SELECT COUNT(*) FROM dcp_council_field_snapshot WHERE council = %s",
                    (SENTINEL,))
        assert cur.fetchone()[0] == 0, "sentinel rows were left behind"
        conn.close()


def test_a_clean_run_over_real_data_exits_zero():
    """The confusable negative for the test above. Without it, 'run() returned 2'
    proves only that run() returns 2, not that it discriminates."""
    _skip_if_no_real_db()
    ccc = _module()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dcp_council_field_snapshot WHERE council='ashfield'")
        if cur.fetchone()[0] == 0:
            pytest.skip("ashfield has no baseline recorded yet -- nothing to compare against")
    finally:
        conn.close()
    assert ccc.run(trigger_source="manual", councils=["ashfield"],
                   record=False, alert=False) == 0
