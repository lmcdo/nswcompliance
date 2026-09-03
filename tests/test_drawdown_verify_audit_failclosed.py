"""DQ-91: a failed drawdown-verify audit write must fail the request, not be
silently discharged.

Before the fix, services/drawdown_verify.py::submit_drawdown_verify caught any
exception from _insert_audit, logged it, and returned status="submitted"
anyway -- so a caller (a lender, per the module's own docstring: "This is
legal evidence if construction fraud goes to court") could be told a
verification was recorded when no row was ever written. Confirmed live
2026-09-04: drawdown_verify_audits has never existed in production, so this
branch fires on every real call.

This test does not touch a database -- psycopg2 is stubbed globally by
tests/conftest_mocks.py, and _find_sentinel1_scenes / _submit_hyp3_job /
_insert_audit are patched directly so only the failure-handling contract in
submit_drawdown_verify itself is under test.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

import services.drawdown_verify as dv


def _request():
    return dv.DrawdownVerifyRequest(
        loan_id="loan-123",
        address="1 Test Street, Testville NSW 2000",
        stage_claimed="slab",
        lot_bbox=dv.LotBbox(min_lon=151.0, min_lat=-33.9, max_lon=151.01, max_lat=-33.89),
        reference_date="2026-06-01",
    )


class TestAuditWriteFailsClosed:
    def test_audit_insert_failure_raises_500_not_a_fake_success(self):
        """The core DQ-91 regression: a broken audit write must surface as an
        error, never as status="submitted"."""
        with patch.object(
            dv, "_find_sentinel1_scenes",
            return_value=("scene-before-id", "scene-after-id", "2026-05-20", "2026-06-01"),
        ), patch.object(
            dv, "_submit_hyp3_job", return_value="hyp3-job-abc123",
        ), patch.object(
            dv, "_insert_audit",
            side_effect=Exception('relation "drawdown_verify_audits" does not exist'),
        ):
            with pytest.raises(HTTPException) as exc_info:
                dv.submit_drawdown_verify(_request())

        assert exc_info.value.status_code == 500
        # The caller must be told the write is unconfirmed, not that it
        # succeeded. Wording deliberately does NOT assert "NOT recorded" --
        # Sol cross-review (2026-09-04) caught that as its own overclaim: a
        # commit can succeed before a connection drop hides the acknowledgement,
        # so "definitely absent" is not something this exception can prove
        # either. See services/drawdown_verify.py's inline comment on this string.
        assert "could not be confirmed" in exc_info.value.detail
        assert "UNCONFIRMED" in exc_info.value.detail

    def test_audit_insert_failure_response_carries_the_hyp3_job_name_for_reconciliation(self):
        """The HyP3 job was already submitted (money/quota spent) before the
        audit write is attempted, so the error the caller sees must carry
        enough to find that job by hand -- losing the job_name here means the
        submitted-but-unrecorded job becomes unreconcilable, not just unrecorded."""
        with patch.object(
            dv, "_find_sentinel1_scenes",
            return_value=("scene-before-id", "scene-after-id", "2026-05-20", "2026-06-01"),
        ), patch.object(
            dv, "_submit_hyp3_job", return_value="hyp3-job-abc123",
        ), patch.object(
            dv, "_insert_audit", side_effect=Exception("connection refused"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                dv.submit_drawdown_verify(_request())

        assert "loan-loan-123-slab-2026-06-01" in exc_info.value.detail

    def test_audit_insert_success_still_returns_submitted(self):
        """The fix must not break the working path: a successful audit write
        still returns status="submitted" with the real audit id."""
        with patch.object(
            dv, "_find_sentinel1_scenes",
            return_value=("scene-before-id", "scene-after-id", "2026-05-20", "2026-06-01"),
        ), patch.object(
            dv, "_submit_hyp3_job", return_value="hyp3-job-abc123",
        ), patch.object(
            dv, "_insert_audit", return_value="real-audit-uuid",
        ):
            result = dv.submit_drawdown_verify(_request())

        assert result.status == "submitted"
        assert result.job_id == "real-audit-uuid"

    def test_hyp3_submission_failure_is_unchanged_by_this_fix(self):
        """Not part of DQ-91, but pinned so this fix cannot be confused with a
        change to the (already-correct) HyP3-submission failure path."""
        with patch.object(
            dv, "_find_sentinel1_scenes",
            return_value=("scene-before-id", "scene-after-id", "2026-05-20", "2026-06-01"),
        ), patch.object(
            dv, "_submit_hyp3_job", side_effect=Exception("HyP3 quota exceeded"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                dv.submit_drawdown_verify(_request())

        assert exc_info.value.status_code == 500
        assert "HyP3 submission failed" in exc_info.value.detail


class TestDbConnectionCloses:
    """Adversarial pre-push review caught a second, pre-existing defect in the
    same file while this PR was already touching it: `with _db_conn() as
    conn:` only manages COMMIT/ROLLBACK on exit (psycopg2 behaviour), it does
    NOT close the connection -- so _insert_audit/_update_audit/_get_audit
    each leaked one connection against the pooler on every call, including
    the polling endpoint that can be hit repeatedly over a 1-2 hour job.
    Fixed alongside DQ-91 rather than filed separately, since it is in the
    same three functions this PR already has open."""

    def test_insert_audit_closes_connection_even_on_query_error(self):
        mock_conn = MagicMock()
        # Real psycopg2 connections return SELF from __enter__ (only exit
        # manages commit/rollback) -- the default MagicMock.__enter__ returns
        # a DIFFERENT auto-generated mock, which silently detached the old
        # `with _db_conn() as conn:` code from this exception injection and
        # made these tests fail against the pre-fix code for the wrong reason
        # (DID NOT RAISE, from never reaching the execute() call at all,
        # rather than a clean close()-not-called assertion). Pinning this
        # makes the mock behave like the real driver either way.
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("boom")
        with patch.object(dv, "_db_conn", return_value=mock_conn):
            with pytest.raises(Exception, match="boom"):
                dv._insert_audit(
                    loan_id="loan-1", address="addr", stage_claimed="slab",
                    hyp3_job_name="job", hyp3_job_id="id",
                    scene_before="a", scene_after="b",
                )
        mock_conn.close.assert_called_once()

    def test_update_audit_closes_connection_even_on_query_error(self):
        mock_conn = MagicMock()
        # Real psycopg2 connections return SELF from __enter__ (only exit
        # manages commit/rollback) -- the default MagicMock.__enter__ returns
        # a DIFFERENT auto-generated mock, which silently detached the old
        # `with _db_conn() as conn:` code from this exception injection and
        # made these tests fail against the pre-fix code for the wrong reason
        # (DID NOT RAISE, from never reaching the execute() call at all,
        # rather than a clean close()-not-called assertion). Pinning this
        # makes the mock behave like the real driver either way.
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("boom")
        with patch.object(dv, "_db_conn", return_value=mock_conn):
            with pytest.raises(Exception, match="boom"):
                dv._update_audit("audit-1", status="complete")
        mock_conn.close.assert_called_once()

    def test_get_audit_closes_connection_even_on_query_error(self):
        mock_conn = MagicMock()
        # Real psycopg2 connections return SELF from __enter__ (only exit
        # manages commit/rollback) -- the default MagicMock.__enter__ returns
        # a DIFFERENT auto-generated mock, which silently detached the old
        # `with _db_conn() as conn:` code from this exception injection and
        # made these tests fail against the pre-fix code for the wrong reason
        # (DID NOT RAISE, from never reaching the execute() call at all,
        # rather than a clean close()-not-called assertion). Pinning this
        # makes the mock behave like the real driver either way.
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("boom")
        with patch.object(dv, "_db_conn", return_value=mock_conn):
            with pytest.raises(Exception, match="boom"):
                dv._get_audit("audit-1")
        mock_conn.close.assert_called_once()

    def test_insert_audit_closes_connection_on_success(self):
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn  # match real psycopg2 semantics
        with patch.object(dv, "_db_conn", return_value=mock_conn):
            dv._insert_audit(
                loan_id="loan-1", address="addr", stage_claimed="slab",
                hyp3_job_name="job", hyp3_job_id="id",
                scene_before="a", scene_after="b",
            )
        mock_conn.close.assert_called_once()
        mock_conn.commit.assert_called_once()
