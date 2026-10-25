"""Three DCP-monitor findings from the 2026-10-25 code-quality review (dcp-monitor-verdicts.md).

0. "All chapters are current" was printed while chapters with no document link went unchecked.
2. A broken `hub_scrapers` import became "no scraper" for every council, silently.
4. `checked + unchanged` counted every unchanged chapter twice (each `unchanged += 1` pairs a `checked += 1`).
"""
from __future__ import annotations

import importlib
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

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


def test_skipped_no_link_chapters_are_named_as_not_checked():
    note = r2_monitor.not_checked_note(_results(checked=10, skipped_no_url=3))
    assert "3 with no document link, not checked" in note


def test_all_checked_has_no_note():
    assert r2_monitor.not_checked_note(_results(checked=10)) == ""


def test_main_prints_all_current_only_without_a_note():
    src = open(r2_monitor.__file__, encoding="utf-8").read()
    assert 'infra_note = not_checked_note(results)' in src
    assert '" Some chapters were NOT checked:" + infra_note if infra_note' in src


def test_unchanged_chapters_are_counted_once():
    # 10 chapters checked, 7 of them unchanged: the total is 10, not 17.
    assert r2_monitor.chapters_checked(_results(checked=10, unchanged=7)) == 10
    src = open(r2_monitor.__file__, encoding="utf-8").read()
    assert 'results["checked"] + results["unchanged"]' not in src


def test_a_broken_hub_scrapers_import_fails_loudly(monkeypatch):
    monkeypatch.setitem(sys.modules, "hub_scrapers", None)  # makes `import hub_scrapers` raise
    with pytest.raises(ImportError):
        importlib.reload(r2_monitor)
    monkeypatch.delitem(sys.modules, "hub_scrapers")
    importlib.reload(r2_monitor)  # leave a working module for later tests
