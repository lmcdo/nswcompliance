"""DQ-91 connection-leak fix, verified against the REAL psycopg2 driver and
the REAL production database -- not conftest_mocks.py's MagicMock stub.

Every other test for this fix (tests/test_drawdown_verify_audit_failclosed.py)
stops at a mock boundary: `_db_conn` is patched to return a MagicMock, so
"conn.close() was called" only proves the mock recorded a call, not that a
real database connection was actually released. That gap was pointed out
directly in session (2026-09-04) after the mock's __enter__ semantics had
already caused three of four leak-fix tests to fail against the pre-fix code
for the WRONG mechanical reason once -- a second, sharper instance of the
same "mock doesn't behave like the real thing" risk.

This file closes that gap the way the project's own convention already
supports (see tests/test_lga_coverage.py, tests/conftest_mocks.py) rather than
inventing a new one: opt-in via PYTEST_REAL_DB=1, @pytest.mark.database
(deselected by default per pytest.ini), so the default `pytest` run this repo
uses everywhere else is completely unaffected.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_drawdown_verify_real_db.py -v

Deliberately does NOT touch drawdown_verify_audits with a write -- the table
does not exist in production (that is DQ-91's root cause, still open pending
migration approval), and this file must not be the thing that first creates
data in it. Every test here is read-only or expects the query to fail because
the table is absent, and asserts nothing is left open regardless.

What this file does NOT and importantly SHOULD NOT do: call the real HyP3 API.
_submit_hyp3_job talks to a paid third-party InSAR processing service (ASF
Earthdata credentials, real compute cost, 1-2 hour turnaround per job) -- that
is a fundamentally different class of "real" than a database round-trip, and
does not belong in an automated test suite. It needs a manual, deliberate,
credentialed run outside pytest if it is ever verified end-to-end. Flagging
that explicitly here rather than silently having no coverage for it.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

# prior-art-checked: reuse, not reinvention -- scripts/dq_db.py already solved
# "find the right .env from inside a worktree" (a naive load_dotenv('.env')
# silently falls through to localhost defaults from a worktree, which has no
# .env of its own -- documented in dq_db.py's own docstring as a mistake made
# once before that helper existed). Reusing its main_checkout() rather than
# repeating the git-common-dir lookup a third time in this repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

import services.drawdown_verify as dv  # noqa: E402  (after dotenv/marker setup)


def _skip_if_no_real_db():
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_drawdown_verify_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


class TestRealConnectionLifecycle:
    def test_db_conn_returns_a_real_psycopg2_connection_and_close_actually_closes_it(self):
        """The most basic proof there is: open one, use it, close it, then
        prove it is REALLY closed by trying to use it again."""
        _skip_if_no_real_db()
        import psycopg2

        conn = dv._db_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 AS one")
            row = cur.fetchone()
            assert row["one"] == 1  # RealDictCursor -- dict-like row, not a tuple
        finally:
            conn.close()

        # The real, load-bearing assertion: a closed psycopg2 connection
        # raises on further use. A MagicMock would happily return another
        # MagicMock here and this would tell us nothing.
        with pytest.raises(psycopg2.InterfaceError):
            conn.cursor()

    def test_get_audit_closes_the_real_connection_even_though_the_table_is_missing(self):
        """Uses the ACTUAL DQ-91 root cause (drawdown_verify_audits does not
        exist in production) as the natural failure trigger -- no mock stands
        in for the failure, the failure is real. Proves _get_audit's
        finally: conn.close() fires against a genuine connection on a genuine
        error, and that the connection this test itself opened is truly
        closed afterward -- not merely recorded-as-closed by a mock."""
        _skip_if_no_real_db()
        import psycopg2

        # psycopg2.extensions.connection is a C-extension type -- its
        # attributes (including .close) are read-only, so it cannot be
        # monkeypatched directly (confirmed by actually trying it: raises
        # "attribute 'close' is read-only"). A thin observation proxy that
        # delegates everything except .close is the real-object equivalent of
        # what the mock was doing, without replacing any real behaviour.
        real_conn = dv._db_conn()

        class _CloseTrackingProxy:
            def __init__(self, conn):
                self._conn = conn
                self.close_called = False

            def close(self):
                self.close_called = True
                self._conn.close()

            def __enter__(self):
                # Matches real psycopg2: `with conn:` returns conn itself,
                # not a different object -- this is the exact mismatch that
                # made three of four MagicMock-based leak tests fail against
                # the pre-fix code for the wrong reason earlier this session.
                return self

            def __exit__(self, *exc_info):
                return self._conn.__exit__(*exc_info)

            def __getattr__(self, name):
                return getattr(self._conn, name)

        proxy = _CloseTrackingProxy(real_conn)

        from unittest.mock import patch
        with patch.object(dv, "_db_conn", return_value=proxy):
            with pytest.raises(psycopg2.errors.UndefinedTable):
                dv._get_audit(str(uuid.uuid4()))

        assert proxy.close_called, (
            "finally: conn.close() did not fire on the real connection when "
            "the real query genuinely failed"
        )
        # The real proof: the underlying psycopg2 connection this test itself
        # opened is genuinely closed, not merely recorded-as-closed.
        assert real_conn.closed != 0
        with pytest.raises(psycopg2.InterfaceError):
            real_conn.cursor()

    def test_drawdown_verify_audits_still_does_not_exist(self):
        """Pinned so this file fails loudly (not silently stops testing
        anything meaningful) the moment someone runs migration 033 and this
        test file's premise -- 'the table is absent, so its absence is what
        proves the finally: block fires on a genuine error' -- stops holding.
        When this goes red, update DQ-91's declared status and rewrite (not
        delete) the two tests above to insert-then-delete a real throwaway
        row instead."""
        _skip_if_no_real_db()
        conn = dv._db_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT count(*) AS cnt FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='drawdown_verify_audits'"
            )
            count = cur.fetchone()["cnt"]  # RealDictCursor -- dict-like row
        finally:
            conn.close()
        assert count == 0, (
            "drawdown_verify_audits now exists -- DQ-91's root cause is "
            "fixed. Update .claude/dq_checks.json (declared: fixed) and "
            "rewrite the two tests above to use a real insert+delete."
        )
