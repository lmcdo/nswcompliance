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

# r2_monitor reads its R2/DB config at import time. These pure-logic tests never
# make a call with it, but without the vars the module raises KeyError on import.
# CI happens to supply the real secrets and the main checkout happens to have a
# .env, so this file used to pass by accident and fail in a worktree. setdefault
# (not assignment) keeps any real value, and python-dotenv does not override.
for _var in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID",
             "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_var, f"test-{_var.lower()}")

from r2_monitor import (  # noqa: E402
    run_exit_code,
    diff_urls,
    UNLISTED_CONFIRM_FAILURES,
    TransientFetchError,
    WAFBlockError,
)


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


def _stored(key, council_url, check_failures=0):
    return {"chapter_key": key, "council_url": council_url,
            "check_failures": check_failures}


class TestUnlistedIsNotRemoved:
    """Absence from a hub page is not evidence a document was removed.

    canterbury_bankstown, measured 2026-10-01: its hub page exposes 14 links (none
    of them DCP chapters — those sit behind a SharePoint/Azure api/publish endpoint
    the page never lists), while the registry holds 54 non-inert chapters. 51 of
    those hashed cleanly in the same 02:00 UTC run with check_failures = 0; 3 were
    genuinely gone on a decommissioned host at check_failures = 5. The old code
    called all 54 "Removed from hub", every sweep.
    """

    def test_live_url_absent_from_hub_is_unlisted_not_removed(self):
        diff = diff_urls(
            discovered=[],
            stored=[_stored("ch-a", "https://x/a.pdf", check_failures=0)],
            hub_expected_count=None,
        )
        assert diff.unlisted == ["ch-a"]
        assert diff.removed == []

    def test_dead_url_absent_from_hub_is_removed(self):
        diff = diff_urls(
            discovered=[],
            stored=[_stored("ch-a", "https://x/a.pdf",
                            check_failures=UNLISTED_CONFIRM_FAILURES)],
            hub_expected_count=None,
        )
        assert diff.removed == ["ch-a"]
        assert diff.unlisted == []

    def test_threshold_is_load_bearing_just_below_does_not_alert(self):
        """Mutation guard: a `>= 0` or a dropped threshold would alert here."""
        diff = diff_urls(
            discovered=[],
            stored=[_stored("ch-a", "https://x/a.pdf",
                            check_failures=UNLISTED_CONFIRM_FAILURES - 1)],
            hub_expected_count=None,
        )
        assert diff.removed == []
        assert diff.unlisted == ["ch-a"]

    def test_null_check_failures_is_treated_as_zero(self):
        diff = diff_urls(
            discovered=[],
            stored=[_stored("ch-a", "https://x/a.pdf", check_failures=None)],
            hub_expected_count=None,
        )
        assert diff.removed == []
        assert diff.unlisted == ["ch-a"]

    def test_the_canterbury_bankstown_shape(self):
        """51 live + 3 dead, none on the hub: 3 alerts, not 54."""
        stored = ([_stored(f"live-{i}", f"https://x/{i}.pdf", 0) for i in range(51)]
                  + [_stored(f"dead-{i}", f"https://gone/{i}.pdf", 5) for i in range(3)])
        diff = diff_urls(discovered=[], stored=stored, hub_expected_count=None)
        assert len(diff.removed) == 3
        assert len(diff.unlisted) == 51
        assert all(k.startswith("dead-") for k in diff.removed)

    def test_a_matched_chapter_is_neither(self):
        diff = diff_urls(
            discovered=[{"chapter_key": "ch-a", "url": "https://x/a.pdf", "label": "A"}],
            stored=[_stored("ch-a", "https://x/a.pdf", check_failures=9)],
            hub_expected_count=None,
        )
        assert diff.removed == [] and diff.unlisted == []
        assert diff.url_same == ["ch-a"]


# ── verified_at is stamped only when the council was actually checked ─────────
# 2026-10-15: eight councils (bayside, burwood, camden, canada_bay, fairfield, ryde,
# the_hills, the_hills_shire) had only hub-only chapters -- no council_url, every one
# skipped -- and were stamped verified because "zero failures" was the whole test.
from r2_monitor import _council_verified  # noqa: E402


def test_no_checkable_chapter_is_not_verified():
    assert _council_verified(checkable=0, checked=0, changed=0, failed=0) is False


def test_a_skipped_chapter_blocks_the_stamp():
    # a chapter still 429 after its retry is skipped without counting as failed
    assert _council_verified(checkable=3, checked=2, changed=0, failed=0) is False


def test_every_chapter_checked_and_unchanged_is_verified():
    assert _council_verified(checkable=3, checked=3, changed=0, failed=0) is True


def test_a_change_or_a_failure_blocks_the_stamp():
    assert _council_verified(checkable=3, checked=3, changed=1, failed=0) is False
    assert _council_verified(checkable=3, checked=2, changed=0, failed=1) is False


def test_every_check_path_counts_toward_the_council():
    """A new unchanged/changed path that bumps results["checked"] but not
    council_checked would block every stamp for that council -- or, if someone
    'fixes' that by loosening _council_verified, bring the false stamps back."""
    import re
    src = open(os.path.join(os.path.dirname(__file__), "..", "scripts", "r2_monitor.py"),
               encoding="utf-8").read()
    body = src[src.index("def run_monitor("):]
    body = body[:body.index("\ndef ", 1)]
    lines = body.splitlines()
    bumps = [i for i, l in enumerate(lines) if re.search(r'results\["checked"\] \+= 1', l)]
    assert bumps, "no results['checked'] increments found -- has the counter changed?"
    unpaired = [lines[i].strip() for i in bumps if "council_checked += 1" not in lines[i + 1]]
    assert not unpaired, f"{len(unpaired)} check path(s) not counted in council_checked"
    assert "_council_verified(council_checkable, council_checked" in body
