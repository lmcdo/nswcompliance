"""Real-database check of migration 126 and the backfill's insert. Opt in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database

conftest_mocks stubs psycopg2 by default, so a database test would otherwise get a MagicMock. Everything here runs inside ONE transaction that is
ALWAYS rolled back (the migration itself is applied inside it), so nothing persists whether or not migration 126 is already live.
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import backfill_dcp_source_versions as bf  # noqa: E402

MIGRATION = REPO / "migrations" / "126_dcp_source_versions.sql"
OUTER = re.compile(r"^[ \t]*(BEGIN|COMMIT);[ \t]*\r?$", re.M)
T0 = datetime(2026, 2, 28, 3, 0, 0, tzinfo=timezone.utc)

def _connect():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database")
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    conn.autocommit = False
    return conn


def _row(key="source-pdfs/dcps/zz_test/v1.0-baseline/zz-chapter.pdf", at=T0):
    return ("zz_test", "zz-chapter", "v1.0-baseline", key, "stored", 10, "abc123", None, at, "r2_listing_backfill")


@pytest.mark.database
@pytest.mark.integration
def test_migration_backfill_guards_and_trigger_in_a_rolled_back_transaction():
    import psycopg2

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = '30000'")
        cur.execute(OUTER.sub("", MIGRATION.read_text(encoding="utf-8")))

        # 1. The backfill insert is idempotent.
        bf.insert_rows(cur, [_row()])
        bf.insert_rows(cur, [_row()])
        cur.execute("SELECT count(*) FROM dcp_source_versions WHERE council = 'zz_test'")
        assert cur.fetchone()[0] == 1

        # 2. The ledger cannot be edited or emptied.
        for stmt in ("DELETE FROM dcp_source_versions WHERE council = 'zz_test'",
                     "UPDATE dcp_source_versions SET size_bytes = 1 WHERE council = 'zz_test'",
                     "TRUNCATE dcp_source_versions"):
            cur.execute("SAVEPOINT s")
            with pytest.raises(psycopg2.Error):
                cur.execute(stmt)
            cur.execute("ROLLBACK TO SAVEPOINT s")

        # 3. dcp_source_as_at returns the file held at a moment, and nothing before the first record.
        bf.insert_rows(cur, [_row(key="source-pdfs/dcps/zz_test/v1.1-2026-03-02/zz-chapter.pdf", at=T0 + timedelta(days=2))])
        held = ["stored", "received"]
        cur.execute("SELECT r2_key FROM dcp_source_as_at('zz_test', 'zz-chapter', %s, %s)", (T0 + timedelta(days=1), held))
        assert cur.fetchone()[0].endswith("v1.0-baseline/zz-chapter.pdf")
        cur.execute("SELECT r2_key FROM dcp_source_as_at('zz_test', 'zz-chapter', %s, %s)", (T0 + timedelta(days=3), held))
        assert cur.fetchone()[0].endswith("v1.1-2026-03-02/zz-chapter.pdf")
        cur.execute("SELECT count(*) FROM dcp_source_as_at('zz_test', 'zz-chapter', %s, %s)", (T0 - timedelta(days=1), held))
        assert cur.fetchone()[0] == 0
        # 'served' asks a different question: the stored-only rows above are not live events, so nothing is returned.
        cur.execute("SELECT count(*) FROM dcp_source_as_at('zz_test', 'zz-chapter', %s, %s)", (T0 + timedelta(days=3), ["live"]))
        assert cur.fetchone()[0] == 0

        # 4. The registry trigger logs a received file (staged path set) for any writer.
        cur.execute("SELECT id FROM dcp_chapter_registry ORDER BY id LIMIT 1")
        reg_id = cur.fetchone()[0]
        test_key = "source-pdfs/dcps/zz_test/v9.9-test/zz-trigger.pdf"
        cur.execute("UPDATE dcp_chapter_registry SET staged_r2_path = %s, staged_version_label = 'v9.9-test', staged_at = now() WHERE id = %s",
                    (test_key, reg_id))
        cur.execute("SELECT event, source FROM dcp_source_versions WHERE r2_key = %s", (test_key,))
        assert cur.fetchall() == [("received", "registry_trigger")]

        # 5. A failure inside the logging step must not block the registry write (it becomes a warning).
        cur.execute("ALTER TABLE dcp_source_versions ADD CONSTRAINT zz_block_all CHECK (false) NOT VALID")
        blocked_key = "source-pdfs/dcps/zz_test/v9.9-test/zz-blocked.pdf"
        cur.execute("UPDATE dcp_chapter_registry SET staged_r2_path = %s WHERE id = %s", (blocked_key, reg_id))
        cur.execute("SELECT staged_r2_path FROM dcp_chapter_registry WHERE id = %s", (reg_id,))
        assert cur.fetchone()[0] == blocked_key
        cur.execute("SELECT count(*) FROM dcp_source_versions WHERE r2_key = %s", (blocked_key,))
        assert cur.fetchone()[0] == 0
    finally:
        conn.rollback()
        conn.close()
