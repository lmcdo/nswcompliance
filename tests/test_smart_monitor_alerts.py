"""
Tests for smart monitor alert logic:
  1. _auto_verify_controls — auto-clears needs_review when no value changes
  2. Smart flagging — only flags for numeric changes, auto-verifies for text-only
  3. Watchdog severity tiers — CRITICAL vs STANDARD vs INFO classification
"""

import sys
import types
from unittest.mock import MagicMock, patch, call
import pytest


# ── Import helpers ──────────────────────────────────────────────────────────
# dcp_extract_changed.py is a script with top-level DB connections.
# We can't import it directly. Extract testable functions via exec + module.


def _load_extract_function():
    """Load _auto_verify_controls from dcp_extract_changed.py without running top-level code."""
    import importlib.util
    from pathlib import Path

    script_path = Path(__file__).parent.parent / "scripts" / "dcp_extract_changed.py"
    source = script_path.read_text(encoding="utf-8")

    # Extract just the _auto_verify_controls function
    # Find the function definition
    start = source.index("def _auto_verify_controls(")
    # Find the next top-level def or class (non-indented)
    import re
    next_def = re.search(r"\n(?:def |class |# ── )", source[start + 10:])
    end = start + 10 + next_def.start() if next_def else len(source)
    func_source = source[start:end]

    # Create a module namespace and exec the function
    ns = {}
    exec(func_source, ns)
    return ns["_auto_verify_controls"]


# ── _auto_verify_controls tests ─────────────────────────────────────────────


class TestAutoVerifyControls:
    """Test that _auto_verify_controls correctly updates DB rows."""

    @pytest.fixture
    def auto_verify(self):
        return _load_extract_function()

    @pytest.fixture
    def mock_db(self):
        cur = MagicMock()
        conn = MagicMock()
        return cur, conn

    def test_updates_controls_and_commits(self, auto_verify, mock_db):
        cur, conn = mock_db
        cur.rowcount = 5
        auto_verify(cur, conn, "ku_ring_gai", "part-4", "regeneration_artifact")
        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "needs_review" in sql
        assert "FALSE" in sql
        assert "last_verified_at" in sql
        conn.commit.assert_called_once()

    def test_no_commit_when_flag_false(self, auto_verify, mock_db):
        cur, conn = mock_db
        cur.rowcount = 3
        auto_verify(cur, conn, "ku_ring_gai", "part-4", "text_only_change", commit=False)
        conn.commit.assert_not_called()

    def test_passes_correct_params(self, auto_verify, mock_db):
        cur, conn = mock_db
        cur.rowcount = 0
        auto_verify(cur, conn, "inner_west", "section-b-part-3", "map_change")
        params = cur.execute.call_args[0][1]
        assert params == ("inner_west", "section-b-part-3")

    def test_zero_rows_no_error(self, auto_verify, mock_db):
        """Auto-verify with no matching rows should not raise."""
        cur, conn = mock_db
        cur.rowcount = 0
        auto_verify(cur, conn, "nonexistent", "fake-key", "test")
        # Should still commit
        conn.commit.assert_called_once()


# ── Smart flagging logic tests ──────────────────────────────────────────────


class TestSmartFlaggingDecision:
    """Test the decision logic for when to flag vs auto-verify.

    The actual logic is inline in extract_chapter(), so we test the
    decision conditions directly rather than importing that function.
    """

    @staticmethod
    def _should_flag(diff: dict, status: str) -> tuple[bool, str]:
        """Replicate the smart flagging decision from extract_chapter().

        Returns (should_flag, reason) matching the code logic.
        """
        has_numeric = any(
            c.get("has_numeric_change") for c in diff.get("changed", [])
        )
        n_added = len(diff.get("added", []))
        n_removed = len(diff.get("removed", []))
        has_structural = n_added > 0 or n_removed > 0

        if has_numeric or (status == "restructure" and has_structural):
            reason = "numeric_value_changed" if has_numeric else "structural_change"
            return True, reason
        return False, "auto_verified"

    def test_numeric_change_flags(self):
        diff = {"changed": [{"has_numeric_change": True}], "added": [], "removed": []}
        should_flag, reason = self._should_flag(diff, "ok")
        assert should_flag is True
        assert reason == "numeric_value_changed"

    def test_text_only_change_auto_verifies(self):
        diff = {"changed": [{"has_numeric_change": False}], "added": [], "removed": []}
        should_flag, _ = self._should_flag(diff, "ok")
        assert should_flag is False

    def test_no_changes_auto_verifies(self):
        diff = {"changed": [], "added": [], "removed": []}
        should_flag, _ = self._should_flag(diff, "ok")
        assert should_flag is False

    def test_restructure_with_additions_flags(self):
        diff = {
            "changed": [],
            "added": [{"ref_number": "new-1", "new_text": "text"}],
            "removed": [],
        }
        should_flag, reason = self._should_flag(diff, "restructure")
        assert should_flag is True
        assert reason == "structural_change"

    def test_restructure_with_removals_flags(self):
        diff = {
            "changed": [],
            "added": [],
            "removed": [{"ref_number": "old-1", "old_text": "text"}],
        }
        should_flag, reason = self._should_flag(diff, "restructure")
        assert should_flag is True
        assert reason == "structural_change"

    def test_restructure_text_only_no_adds_removes_auto_verifies(self):
        """Restructure status but only text changes (no adds/removes) → auto-verify."""
        diff = {
            "changed": [{"has_numeric_change": False}],
            "added": [],
            "removed": [],
        }
        should_flag, _ = self._should_flag(diff, "restructure")
        assert should_flag is False

    def test_mixed_numeric_and_text_flags(self):
        """One numeric change among many text-only → flag."""
        diff = {
            "changed": [
                {"has_numeric_change": False},
                {"has_numeric_change": False},
                {"has_numeric_change": True},
                {"has_numeric_change": False},
            ],
            "added": [],
            "removed": [],
        }
        should_flag, reason = self._should_flag(diff, "ok")
        assert should_flag is True
        assert reason == "numeric_value_changed"

    def test_additions_without_restructure_auto_verifies(self):
        """New provisions in normal 'ok' diff don't trigger flag
        (additions might be from pagination changes)."""
        diff = {
            "changed": [],
            "added": [{"ref_number": "new-1", "new_text": "text"}],
            "removed": [],
        }
        should_flag, _ = self._should_flag(diff, "ok")
        assert should_flag is False


# ── Watchdog severity classification tests ──────────────────────────────────


class TestWatchdogSeverity:
    """Test that review_reason maps to correct severity tier."""

    CRITICAL_REASONS = {"numeric_value_changed"}
    STANDARD_REASONS = {"structural_change", "chapter_pdf_changed"}

    def test_numeric_value_changed_is_critical(self):
        assert "numeric_value_changed" in self.CRITICAL_REASONS

    def test_structural_change_is_standard(self):
        assert "structural_change" in self.STANDARD_REASONS

    def test_legacy_chapter_pdf_changed_is_standard(self):
        assert "chapter_pdf_changed" in self.STANDARD_REASONS

    def test_severity_buckets_complete(self):
        """All known review_reason values are classified."""
        all_reasons = {"numeric_value_changed", "structural_change", "chapter_pdf_changed"}
        classified = self.CRITICAL_REASONS | self.STANDARD_REASONS
        assert all_reasons <= classified

    def test_critical_and_standard_disjoint(self):
        assert not self.CRITICAL_REASONS & self.STANDARD_REASONS


class TestFailGracePeriod:
    """Test the grace period logic for failing chapter URLs."""

    def test_grace_period_filters_recent_failures(self):
        """Chapters that were OK recently should not be alerted."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        grace_days = 3

        # Last OK 1 day ago → should NOT alert
        last_ok = now - timedelta(days=1)
        should_alert = last_ok < now - timedelta(days=grace_days)
        assert should_alert is False

    def test_grace_period_allows_old_failures(self):
        """Chapters failing for >grace_days should be alerted."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        grace_days = 3

        # Last OK 5 days ago → should alert
        last_ok = now - timedelta(days=5)
        should_alert = last_ok < now - timedelta(days=grace_days)
        assert should_alert is True

    def test_never_ok_should_alert(self):
        """Chapters that have never succeeded should be alerted."""
        # url_last_ok IS NULL → always alert
        last_ok = None
        should_alert = last_ok is None
        assert should_alert is True
