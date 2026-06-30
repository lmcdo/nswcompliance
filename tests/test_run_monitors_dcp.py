"""Tests for the DCP monitor dispatch table in scripts/run_monitors.py.

Guards the wiring of the scheduled re-extract-all detector cadence:
- dcp-extract-all must run `dcp_extract_changed.py --all --review`
- it must be DISTINCT from the reactive dcp-extract (which has no --all)
- both must be --review (extract-to-queue, never a provision commit)
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

run_monitors = importlib.import_module("run_monitors")
MONITORS = run_monitors.MONITORS


class TestDcpExtractAllWiring:
    def test_dcp_extract_all_is_registered(self):
        assert "dcp-extract-all" in MONITORS

    def test_dcp_extract_all_runs_all_review(self):
        cmd = MONITORS["dcp-extract-all"]["cmd"]
        assert cmd == ["python", "scripts/dcp_extract_changed.py", "--all", "--review"]

    def test_reactive_extract_has_no_all_flag(self):
        # The reactive byte-change path must stay byte-change-only.
        assert "--all" not in MONITORS["dcp-extract"]["cmd"]

    def test_all_and_reactive_are_distinct_commands(self):
        assert MONITORS["dcp-extract-all"]["cmd"] != MONITORS["dcp-extract"]["cmd"]

    def test_both_extract_paths_are_review_only(self):
        # --review = enqueue to dcp_review_queue, NO provision commit. Neither
        # extract path may carry --commit (only dcp-commit does, behind the human gate).
        for name in ("dcp-extract", "dcp-extract-all"):
            cmd = MONITORS[name]["cmd"]
            assert "--review" in cmd
            assert "--commit" not in cmd

    def test_dcp_commit_is_the_only_committer(self):
        assert "--commit" in MONITORS["dcp-commit"]["cmd"]
