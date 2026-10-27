"""A run that checked no chapter is not "all current" (review note on #1507, 2026-10-26).

With zero chapters checked and nothing to explain it, the monitor printed "No changes detected.
All chapters are current." and exited 0 -- a monitor that silently stopped working looked healthy.
"""
from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock

sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
if "botocore.exceptions" not in sys.modules:
    _m = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        pass

    _m.ClientError = ClientError
    sys.modules["botocore.exceptions"] = _m

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
for _k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID",
           "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_k, "test-placeholder-not-a-credential")

import r2_monitor  # noqa: E402


def _results(**kw):
    base = {"checked": 0, "unchanged": 0, "failed": 0, "skipped_no_url": 0, "changed": [],
            "transient": [], "waf_blocked": [], "rate_limited": []}
    return {**base, **kw}


def test_nothing_checked_and_nothing_explains_it_fails():
    assert r2_monitor.quiet_run_outcome(_results()) == (1, "NOTHING CHECKED")


def test_nothing_checked_because_every_site_blocked_stays_quiet_but_says_so():
    code, word = r2_monitor.quiet_run_outcome(_results(waf_blocked=[{"council": "x"}]))
    assert code == 0 and word == "NOTHING CHECKED"


def test_a_normal_quiet_run_is_still_clean():
    assert r2_monitor.quiet_run_outcome(_results(checked=40, unchanged=40)) == (0, "no changes")


def test_main_uses_it():
    src = open(r2_monitor.__file__, encoding="utf-8").read()
    assert "quiet_run_outcome(results)" in src
