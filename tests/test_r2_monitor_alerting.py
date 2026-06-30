"""Tests for the DCP-monitor alerting contract (scripts/r2_monitor.py).

The cry-wolf bug: transient (timeout/429) and WAF (403) infra failures used to
count as real failures and page a human (exit 1). They are now bucketed
separately and excluded from the exit-1 decision; only real content/parse/DB
errors page, and only confirmed content changes trigger extraction (exit 2).
"""
import os
import sys
import types
from unittest.mock import MagicMock

# Stub heavy AWS deps so the pure helpers import without boto3 installed.
sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
if "botocore.exceptions" not in sys.modules:
    _m = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        pass

    _m.ClientError = ClientError
    sys.modules["botocore.exceptions"] = _m

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from r2_monitor import run_exit_code, TransientFetchError, WAFBlockError  # noqa: E402


class TestRunExitCode:
    def test_clean_run_is_zero(self):
        assert run_exit_code(n_changed=0, n_real_failed=0) == 0

    def test_changes_only_is_two(self):
        assert run_exit_code(n_changed=3, n_real_failed=0) == 2

    def test_real_failure_no_change_is_one(self):
        assert run_exit_code(n_changed=0, n_real_failed=2) == 1

    def test_real_failure_with_change_still_pages(self):
        # a real data error always pages, even alongside changes
        assert run_exit_code(n_changed=3, n_real_failed=1) == 1

    def test_transient_and_waf_excluded_means_clean(self):
        # Contract: transient/WAF are bucketed separately and never reach
        # n_real_failed — so a run that ONLY had infra failures is exit 0, not 1.
        # (Represented here by n_real_failed=0 because the caller excludes them.)
        assert run_exit_code(n_changed=0, n_real_failed=0) == 0


class TestExceptionTypes:
    def test_transient_is_distinct_exception(self):
        assert issubclass(TransientFetchError, Exception)
        assert not issubclass(TransientFetchError, WAFBlockError)

    def test_waf_is_distinct_exception(self):
        assert issubclass(WAFBlockError, Exception)
