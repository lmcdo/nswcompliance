"""Tests for the diff-scoping logic added to scripts/qa_gate.py.

Verifies the gate only RELAXES when it is certain a flagged line is pre-existing,
and never weakens when it cannot determine the changed lines.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from qa_gate import filter_to_changed_lines, changed_line_numbers  # noqa: E402


class TestFilterToChangedLines:
    def test_keeps_finding_on_a_changed_line(self):
        errs = ["DB guard: scripts/x.py:10 references 'foo' but none of ..."]
        assert filter_to_changed_lines(errs, {"scripts/x.py": {10, 11}}) == errs

    def test_drops_finding_on_an_unchanged_line(self):
        errs = ["Python adversarial: scripts/x.py:99 uses .get(k, [])"]
        assert filter_to_changed_lines(errs, {"scripts/x.py": {10, 11}}) == []

    def test_empty_changed_keeps_everything_fallback(self):
        # git couldn't determine the diff -> never weaken: keep all
        errs = ["DB guard: scripts/x.py:99 references 'foo'"]
        assert filter_to_changed_lines(errs, {}) == errs

    def test_file_absent_from_changed_map_is_kept(self):
        errs = ["DB guard: scripts/y.py:5 references 'foo'"]
        assert filter_to_changed_lines(errs, {"scripts/x.py": {5}}) == errs

    def test_error_without_a_file_line_is_kept(self):
        errs = ["Section 3: need >= 1 functions documented, got 0"]
        assert filter_to_changed_lines(errs, {"scripts/x.py": {5}}) == errs

    def test_mixed_changed_and_pre_existing(self):
        errs = [
            "DB guard: a.py:10 changed-line-finding",
            "DB guard: a.py:50 pre-existing-finding",
            "A note with no path:line at all",
        ]
        out = filter_to_changed_lines(errs, {"a.py": {10}})
        assert "DB guard: a.py:10 changed-line-finding" in out
        assert "DB guard: a.py:50 pre-existing-finding" not in out
        assert "A note with no path:line at all" in out

    def test_path_suffix_match(self):
        # error path may be relative while changed key is repo-relative (or vice versa)
        errs = ["Silent failure: frontend/app/route.ts:7 empty catch"]
        assert filter_to_changed_lines(errs, {"app/route.ts": {7}}) == errs
        assert filter_to_changed_lines(errs, {"app/route.ts": {8}}) == []


class TestChangedLineNumbers:
    def test_returns_empty_when_no_git_base(self, tmp_path):
        # An empty dir is not a git repo -> merge-base fails -> {} (full-scan fallback)
        assert changed_line_numbers(["x.py"], str(tmp_path)) == {}
