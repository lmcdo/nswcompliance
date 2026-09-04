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

UPDATE 2026-09-04: migrations/033_drawdown_verify_audits.sql was run against
production (explicit user authorization) after this file was first written --
verified live: 19 columns, 3 indexes, matching the migration exactly. The
table-absence tests below were pinned to fail the moment that happened, and
they did (confirmed: test_get_audit_closes_the_real_connection_even_though_
the_table_is_missing failed because the query it expected to error no longer
does; test_drawdown_verify_audits_still_does_not_exist failed on its own
`assert count == 0`). Rewritten per their own instructions: the DQ-91 root
cause for THIS table is fixed, proven by a genuine insert -> read-back ->
delete round trip through the real _insert_audit/_get_audit functions (run
manually first outside pytest to confirm before writing it up as a test:
audit_id 37373b9d-0974-48a4-807a-83bd44c422d3, inserted, read back with
matching fields, deleted, confirmed gone). The 3 OTHER tables DQ-91 also
tracks (basix_provisions, sepp_provisions, special_provisions_registry) were
NOT touched -- their liveness was only partially checked this session (ruled
out as registered routers in compliance_api_server.py; not fully re-verified
beyond that), so DQ-91 stays declared 'open' (probe count 4 -> 3, not 0).

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

# Sol cross-review (2026-09-04, caught on the pre-push run that shipped the
# rest of this file): loading .env unconditionally at collection time meant
# every plain `pytest` run -- not just an opt-in real-DB run -- pulled
# production DATABASE_URL into the process environment, even though this
# module's tests are deselected by default. psycopg2 stays stubbed in that
# case (conftest_mocks.py gates on PYTEST_REAL_DB, not on DATABASE_URL being
# present), so nothing in THIS file could act on the leaked credential -- but
# an unrelated test elsewhere that checks os.environ["DATABASE_URL"] directly
# (rather than going through the stub) could, and that risk is not worth
# carrying for a module whose tests never run without the flag anyway. Gate
# the load on the flag itself, checked with no dotenv/pytest machinery
# involved, so the credential is never in-process unless explicitly asked for.
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

import services.drawdown_verify as dv  # noqa: E402  (after dotenv/marker setup)


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
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

    def test_get_audit_closes_the_real_connection_even_on_a_genuine_query_error(self):
        """The table now exists, so the natural failure trigger changed: an
        invalid UUID string sent to a UUID-typed column raises a genuine
        psycopg2.errors.InvalidTextRepresentation from the real driver. Same
        proof as before (finally: conn.close() fires on a real connection on
        a real error), different real error to trigger it with."""
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
            with pytest.raises(psycopg2.errors.InvalidTextRepresentation):
                dv._get_audit("not-a-valid-uuid")

        assert proxy.close_called, (
            "finally: conn.close() did not fire on the real connection when "
            "the real query genuinely failed"
        )
        # The real proof: the underlying psycopg2 connection this test itself
        # opened is genuinely closed, not merely recorded-as-closed.
        assert real_conn.closed != 0
        with pytest.raises(psycopg2.InterfaceError):
            real_conn.cursor()

    def test_drawdown_verify_audits_exists_with_the_expected_schema(self):
        """Replaces the old absence-watchdog now that migration 033 has run
        (explicit user authorization, 2026-09-04). Confirms the live schema
        matches the migration, not just that a table with this name exists."""
        _skip_if_no_real_db()
        conn = dv._db_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='drawdown_verify_audits' "
                "ORDER BY ordinal_position"
            )
            columns = [r["column_name"] for r in cur.fetchall()]
        finally:
            conn.close()
        expected = {
            "id", "loan_id", "address", "stage_claimed", "hyp3_job_name",
            "hyp3_job_id", "scene_before", "scene_after", "status",
            "confidence", "coherence_delta", "coherence_before",
            "coherence_after", "evidence_date_before", "evidence_date_after",
            "manual_review", "geotiff_r2_key", "error_message",
            "created_at", "updated_at",
        }
        assert set(columns) == expected, (
            f"Live schema drifted from migrations/033_drawdown_verify_audits.sql "
            f"-- got {sorted(columns)}"
        )

    def test_insert_read_delete_round_trip_through_the_real_functions(self):
        """The strongest proof available: not just 'the table exists' or
        'close() gets called' but the full path a real caller depends on --
        _insert_audit really writes a row, _get_audit really reads it back
        with the right values, and cleanup really removes it. Run manually
        once outside pytest first to confirm before writing this up
        (audit_id 37373b9d-0974-48a4-807a-83bd44c422d3, 2026-09-04) -- this
        test reproduces that run under the suite so it is re-checked, not a
        one-off claim."""
        _skip_if_no_real_db()
        marker = f"TEST-DQ91-{uuid.uuid4()}"
        audit_id = dv._insert_audit(
            loan_id=marker,
            address="TEST ADDRESS -- not a real property",
            stage_claimed="slab",
            hyp3_job_name="test-job-name",
            hyp3_job_id="test-job-id",
            scene_before="test-scene-before",
            scene_after="test-scene-after",
        )
        try:
            row = dv._get_audit(audit_id)
            assert row is not None, "insert claimed to succeed but the row cannot be read back"
            assert row["loan_id"] == marker
            assert row["status"] == "submitted"
        finally:
            # This table is documented as legal evidence -- no test rows left
            # behind regardless of whether the assertions above passed.
            conn = dv._db_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM drawdown_verify_audits WHERE id = %s", (audit_id,))
                conn.commit()
                deleted = cur.rowcount
            finally:
                conn.close()
            assert deleted == 1, f"expected to delete exactly 1 test row, deleted {deleted}"

        assert dv._get_audit(audit_id) is None, "cleanup failed -- test row still present"


class TestRealHttpLayer:
    """The one gap named directly in session (2026-09-04): every test above,
    and every mocked test in test_drawdown_verify_audit_failclosed.py, calls
    submit_drawdown_verify() as a plain Python function. Neither ever sent a
    real HTTP request through FastAPI's real routing/exception-handling stack
    and read back a real status code and a real JSON body. Calling the
    function directly and checking a status code on the exception it raises
    is NOT the same claim as "the API returns this" -- FastAPI's own
    exception handlers, response serialization, and routing sit between the
    function and an actual client, and none of that was ever exercised.

    prior-art-checked: TestClient + app.include_router is the exact pattern
    tests/test_upzoning_check.py already uses for a different router --
    reused verbatim, not reinvented.

    Only the two genuinely-external, paid third-party calls are mocked
    (Sentinel-1 scene search, HyP3 job submission) -- everything else,
    including the database, is real. The migration ran this session
    (explicit user authorization); this is the first test to prove the
    complete real request -> real response -> real database round trip."""

    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        app.include_router(dv.router)
        return TestClient(app)

    def test_real_http_request_on_audit_failure_returns_a_real_500_with_the_exact_expected_body(self):
        """The claim under test, stated precisely: a real POST to
        /pipeline/drawdown-verify, whose audit insert fails, must come back
        through real FastAPI routing and exception handling as a real 500
        with the exact wording this session's fix wrote -- not just that
        calling the Python function directly raises something with a
        matching attribute, which is a narrower claim than "the API returns
        this" and is already covered separately in
        tests/test_drawdown_verify_audit_failclosed.py.

        No real database constraint is reachable through the public request
        shape without altering schema (stage_claimed's CHECK mirrors
        pydantic's own validator; the id is server-generated so no duplicate
        key is producible; loan_id/address carry no uniqueness). So the
        insert failure itself is simulated here -- it is proven real and
        working in the two tests above (real connection, real error, real
        close). What this test adds that those do not: the real HTTP
        request/response contract around that failure -- status code, JSON
        body, exact wording -- which nothing else in this session exercised.
        """
        _skip_if_no_real_db()
        from unittest.mock import patch

        with patch.object(
            dv, "_find_sentinel1_scenes",
            return_value=("scene-before-id", "scene-after-id", "2026-05-20", "2026-06-01"),
        ), patch.object(
            dv, "_submit_hyp3_job", return_value="hyp3-job-abc123",
        ), patch.object(
            dv, "_insert_audit",
            side_effect=Exception("simulated real-world insert failure for this test"),
        ):
            client = self._client()
            response = client.post(
                "/pipeline/drawdown-verify",
                json={
                    "loan_id": "TEST-DQ91-HTTP-LAYER",
                    "address": "TEST ADDRESS -- not a real property",
                    "stage_claimed": "slab",
                    "lot_bbox": {
                        "min_lon": 151.0, "min_lat": -33.9,
                        "max_lon": 151.01, "max_lat": -33.89,
                    },
                    "reference_date": "2026-06-01",
                },
            )

        assert response.status_code == 500
        body = response.json()
        assert "could not be confirmed" in body["detail"]
        assert "UNCONFIRMED" in body["detail"]

    def test_real_http_request_on_success_actually_writes_a_readable_row_and_cleans_up(self):
        """The complete real claim: POST through real FastAPI routing, real
        pydantic validation, a REAL database write (the migration is live),
        and the response's job_id is a real UUID that reads back a real row
        with the fields the request actually sent -- not asserted against a
        mock's memory of being called, against the database itself."""
        _skip_if_no_real_db()
        from unittest.mock import patch

        marker = f"TEST-DQ91-HTTP-{uuid.uuid4()}"
        with patch.object(
            dv, "_find_sentinel1_scenes",
            return_value=("scene-before-id", "scene-after-id", "2026-05-20", "2026-06-01"),
        ), patch.object(
            dv, "_submit_hyp3_job", return_value="hyp3-job-http-test",
        ):
            client = self._client()
            response = client.post(
                "/pipeline/drawdown-verify",
                json={
                    "loan_id": marker,
                    "address": "TEST ADDRESS -- not a real property",
                    "stage_claimed": "slab",
                    "lot_bbox": {
                        "min_lon": 151.0, "min_lat": -33.9,
                        "max_lon": 151.01, "max_lat": -33.89,
                    },
                    "reference_date": "2026-06-01",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "submitted"
        job_id = body["job_id"]

        try:
            # Not re-asserting against the mock -- reading the REAL row the
            # REAL request wrote, straight from the database.
            row = dv._get_audit(job_id)
            assert row is not None, "the API returned 200 but no row exists for the job_id it gave back"
            assert row["loan_id"] == marker
            assert row["status"] == "submitted"
        finally:
            conn = dv._db_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM drawdown_verify_audits WHERE id = %s", (job_id,))
                conn.commit()
            finally:
                conn.close()
