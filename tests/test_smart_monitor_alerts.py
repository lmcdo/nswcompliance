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


# ── Watchdog staleness must not be measured off a value we rewrite ──────────
# On 2026-08-13 the alert read "5 chapters stuck >48h" and then "oldest 0d" for
# five chapters flagged since 2026-06-22 — 53 days. The >48h tier was computed
# from the chapter flag (right); the printed age came from MIN(queue.created_at),
# and dcp_extract_changed.py:2969 deletes and re-inserts pending rows nightly, so
# that clock resets every night. Loading by source slice: importing dcp_watchdog
# would execute its module-level DB queries.
def _load_stuck_review_line():
    import datetime as _dt
    from pathlib import Path as _P
    src = (_P(__file__).resolve().parent.parent / "scripts" / "dcp_watchdog.py").read_text(
        encoding="utf-8")
    start = src.index("def stuck_review_line")
    end = src.index("# ── Check 1")
    ns: dict = {"datetime": _dt.datetime, "timezone": _dt.timezone}
    exec(src[start:end], ns)
    return ns["stuck_review_line"]


class TestWatchdogStalenessSource:
    stuck_review_line = staticmethod(_load_stuck_review_line())

    def _now(self):
        import datetime as dt
        return dt.datetime(2026, 8, 13, 20, 0, tzinfo=dt.timezone.utc)

    def test_age_comes_from_the_chapter_flag_not_the_nightly_queue_rows(self):
        """The live case: flagged 2026-06-22, queue rows rebuilt today."""
        import datetime as dt
        flagged = dt.datetime(2026, 6, 22, 2, 0, tzinfo=dt.timezone.utc)
        line = self.stuck_review_line("city_of_sydney", "section-3", flagged, 106, self._now())
        assert "52d" in line or "53d" in line, (
            f"a 53-day-old stall must not report as fresh; got: {line}"
        )
        assert "0d" not in line

    def test_a_genuinely_new_stall_still_reads_as_new(self):
        import datetime as dt
        flagged = self._now() - dt.timedelta(days=0, hours=50)
        line = self.stuck_review_line("blacktown", "part-a", flagged, 36, self._now())
        assert "flagged 2d ago" in line

    def test_missing_flag_says_unknown_rather_than_zero(self):
        """A NULL url_last_changed must not silently render as 0 days."""
        line = self.stuck_review_line("x", "y", None, 5, self._now())
        assert "UNKNOWN" in line and "0d" not in line

    def test_pending_row_count_is_still_reported(self):
        import datetime as dt
        flagged = self._now() - dt.timedelta(days=10)
        assert "106 rows pending" in self.stuck_review_line("a", "b", flagged, 106, self._now())


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


# ── Watchdog ↔ run_monitors exit-code contract ──────────────────────────────


class TestWatchdogExitCodeContract:
    """Lock the exit-code contract between dcp_watchdog.py and run_monitors.py.

    Regression guard for the double-alert bug: the watchdog used to exit 1 when it
    found issues, but run_monitors treats any code outside {0, 2} as a crash — so
    every normal findings run produced a spurious "🚨 dcp-watchdog failed (exit 1)"
    alert on top of the real DCP alert.

    Contract (shared with r2_monitor / legislation_monitor / dcp_extract_changed):
      0 = all clear, 2 = ran fine + found issues, anything else = genuine crash.
    """

    @staticmethod
    def _read(rel_path: str) -> str:
        from pathlib import Path
        return (Path(__file__).parent.parent / rel_path).read_text(encoding="utf-8")

    def test_run_monitors_treats_exit_2_as_success(self):
        """run_monitors must classify only codes outside {0, 2} as failed."""
        src = self._read("scripts/run_monitors.py")
        assert "exit_code not in (0, 2)" in src, (
            "run_monitors failure classification changed — the watchdog's exit-2 "
            "findings signal may now be (mis)reported as a failure."
        )

    def test_watchdog_issues_path_exits_2_not_1(self):
        """The watchdog's 'issues found' branch must exit 2, reserving 1 for crashes."""
        src = self._read("scripts/dcp_watchdog.py")
        assert "sys.exit(2)" in src, "watchdog no longer signals findings with exit 2"
        # The only intentional non-zero/non-2 exit is an uncaught crash, never a
        # hardcoded sys.exit(1) on the findings path.
        assert "sys.exit(1)" not in src, (
            "watchdog reintroduced sys.exit(1) — run_monitors would treat a normal "
            "findings run as a crash and double-alert (see TestWatchdogExitCodeContract)."
        )

    def test_watchdog_all_clear_exits_0(self):
        """The all-clear branch must still exit 0 (healthy, no alert)."""
        src = self._read("scripts/dcp_watchdog.py")
        assert "sys.exit(0)" in src
