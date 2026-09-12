"""The verifier's vocabulary allowlists, checked against the live constraint.

WHY THIS EXISTS
---------------
`dcp_verify_extracted_controls` rejects a proposed control whose `control_type`
or `applicability` is outside the vocabulary, so a bad value is caught while it
is still a JSON row rather than at INSERT -- by which point a human has already
spent the review the gate exists to protect.

Those allowlists are copies. A copy drifts. The failure is the quiet one: the DB
gains a control type, the verifier does not, and every proposal of that new type
is rejected with a message that reads as if the model got it wrong.

Marked `database` and deselected by default, so it runs against the real
constraint or not at all:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_control_vocabulary_matches_db.py -o addopts=

The opt-in matters: conftest_mocks stubs psycopg2 by default, so without it this
would compare an allowlist against a MagicMock and pass for the wrong reason.
"""
from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.database


def _check_constraint_values(name: str) -> set[str]:
    from scripts.check_council_completeness import _load_env
    _load_env()
    import psycopg2
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("no DATABASE_URL")
    conn = psycopg2.connect(url, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout='30s'")
        cur.execute(
            "SELECT pg_get_constraintdef(con.oid) FROM pg_constraint con "
            "JOIN pg_class c ON c.oid = con.conrelid "
            "WHERE c.relname = 'dcp_setback_controls' AND con.conname = %s",
            (name,))
        row = cur.fetchone()
    finally:
        conn.close()
    assert row, "constraint " + name + " is gone from dcp_setback_controls"
    return set(re.findall(r"'([a-z0-9_]+)'::text", row[0]))


def test_control_type_allowlist_matches_the_live_constraint():
    from scripts.dcp_verify_extracted_controls import VALID_CONTROL_TYPES
    live = _check_constraint_values("control_type_canonical")
    assert set(VALID_CONTROL_TYPES) == live, (
        "verifier allowlist has drifted from the DB.\n"
        "  only in DB:       " + str(sorted(live - set(VALID_CONTROL_TYPES))) +
        "\n  only in verifier: " + str(sorted(set(VALID_CONTROL_TYPES) - live)))


def test_applicability_allowlist_matches_the_live_constraint():
    from scripts.dcp_verify_extracted_controls import VALID_APPLICABILITY
    live = _check_constraint_values(
        "dcp_setback_controls_applicability_check")
    assert set(VALID_APPLICABILITY) == live, (
        "verifier allowlist has drifted from the DB.\n"
        "  only in DB:       " + str(sorted(live - set(VALID_APPLICABILITY))) +
        "\n  only in verifier: " + str(sorted(set(VALID_APPLICABILITY) - live)))


def test_dev_type_allowlist_covers_every_value_in_use():
    """dev_type has no CHECK constraint, so the table itself is the vocabulary.

    One-directional on purpose: the allowlist may hold a type no row uses yet,
    but a type already IN the table and missing from the allowlist would have
    every new proposal of that shape rejected for no stated reason.
    """
    from scripts.check_council_completeness import _load_env
    from scripts.dcp_verify_extracted_controls import VALID_DEV_TYPES
    _load_env()
    import psycopg2
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("no DATABASE_URL")
    conn = psycopg2.connect(url, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout='30s'")
        cur.execute("SELECT DISTINCT dev_type FROM dcp_setback_controls "
                    "WHERE is_current AND dev_type IS NOT NULL")
        in_use = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()
    assert in_use <= set(VALID_DEV_TYPES), (
        "dev_type values in the table that the verifier would reject: " +
        str(sorted(in_use - set(VALID_DEV_TYPES))))
