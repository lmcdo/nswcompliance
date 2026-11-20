"""Real-database check of the per-version quote verdicts. Opt in:
PYTEST_REAL_DB=1 DATABASE_URL=... pytest tests/test_dcp_quote_version_check_real_db.py -o addopts= -m database

conftest_mocks stubs psycopg2 by default, so the flag is required; without it the test skips (never passes). Read-only."""
import os

import pytest


def _conn():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... -o addopts= -m database; skipped, not a pass")
    import psycopg2

    c = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20,
                         options="-c default_transaction_read_only=on -c statement_timeout=30000")
    return c


@pytest.mark.database
def test_every_stored_verdict_is_a_known_word_and_belongs_to_a_stored_file():
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT count(*), count(*) FILTER (WHERE verdict NOT IN ('verbatim','wrong_page','not_found','no_source')) "
                "FROM dcp_quote_version_check")
    total, bad = cur.fetchone()
    assert total > 0 and bad == 0
    cur.execute("SELECT count(*) FROM dcp_quote_version_check v WHERE NOT EXISTS "
                "(SELECT 1 FROM dcp_source_versions s WHERE s.r2_key = v.r2_key AND s.event = 'stored')")
    assert cur.fetchone()[0] == 0
    c.close()


@pytest.mark.database
def test_penrith_front_setback_wording_change_is_recorded_for_the_older_file():
    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT v.verdict FROM dcp_quote_version_check v JOIN dcp_setback_controls s ON s.id = v.control_id "
                "WHERE v.council = 'penrith' AND s.control_type = 'front_setback' AND v.version_label LIKE 'v1.1%'")
    assert [r[0] for r in cur.fetchall()] == ["not_found"]
    c.close()
