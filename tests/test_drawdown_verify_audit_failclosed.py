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
from unittest.mock import patch

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
        # The caller must be told the request was NOT recorded, not that it was.
        assert "NOT been recorded" in exc_info.value.detail

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
