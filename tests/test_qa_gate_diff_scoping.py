"""Tests for the diff-scoping logic added to scripts/qa_gate.py.

Verifies the gate only RELAXES when it is certain a flagged line is pre-existing,
and never weakens when it cannot determine the changed lines.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from qa_gate import filter_to_changed_lines, changed_line_numbers  # noqa: E402


def _clean_env() -> dict:
    """GIT_* stripped -- a hook exporting GIT_DIR would make git operate on
    the real repository instead of the tmpdir. See test_qa_gate_claimed_files.py."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, env=_clean_env(), capture_output=True,
        text=True, check=False,
    )


@pytest.fixture
def real_repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    # Sol cross-review (2026-09-05): tests in this file create a SEPARATE
    # "main" branch at a specific commit to give changed_line_numbers() a
    # base to diff against (see test_a_non_utf8_byte_in_the_diff_does_not_
    # crash). If the environment's own init.defaultBranch is already "main"
    # (common -- newer git defaults to it), that later `git branch main
    # HEAD` fails (branch already exists), HEAD and "main" stay the SAME
    # ref, and a same-branch diff comes back silently empty -- the wrong
    # failure, for the wrong reason. `-b work` fixes the starting branch
    # name explicitly so "main" is always available to create fresh,
    # regardless of any environment's git config.
    _git(r, "init", "-q", "-b", "work")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "T")
    top = _git(r, "rev-parse", "--show-toplevel").stdout.strip()
    assert Path(top).resolve() == r.resolve()
    return r


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

    def test_hook_exported_git_dir_does_not_leak(self, tmp_path, monkeypatch):
        # Git hooks export GIT_DIR (absolute when pushing from a worktree).
        # cwd must still decide the repo: a non-repo dir yields {} even when
        # GIT_DIR points at a real repository.
        import os
        repo_git_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".git")
        monkeypatch.setenv("GIT_DIR", repo_git_dir)
        assert changed_line_numbers(["x.py"], str(tmp_path)) == {}

    def test_a_non_utf8_byte_in_the_diff_does_not_crash(self, real_repo):
        """Found live on CI, 2026-09-05: a file deleted by
        fix/fabricated-compliance-fallback carried a pre-existing non-UTF-8
        byte (services/sepp_quantitative_extractor.py, from long before that
        session -- likely a Latin-1 'm²'). `_git()`'s `text=True` decode
        defaulted to strict UTF-8 on Linux CI and raised UnicodeDecodeError,
        crashing the whole gate. Windows tolerated the SAME byte silently
        because its platform-default encoding (cp1252 here) is more
        permissive -- proven below by decoding the raw diff bytes strictly
        as UTF-8 ourselves; without that separate proof, this test would
        pass against the pre-fix code on this machine for the wrong reason
        and never actually exercise the crash the fix addresses. Even with
        that proof, this test alone CANNOT force-fail on Windows -- calling
        through to a real subprocess never crashes here regardless of the
        fix, since Windows' own decode never raises either. See the
        deterministic sibling test below, which mocks subprocess.run
        directly and does force-fail identically on every platform."""
        bad = real_repo / "bad.py"
        bad.write_bytes(b"# area is 10\xb2 sqm\ndef f():\n    return 1\n")
        _git(real_repo, "add", "-A")
        _git(real_repo, "commit", "-q", "-m", "add file with a non-utf8 byte")
        # A NEW branch pointing at the current commit, not a rename of the
        # checked-out one -- `branch -m` would relabel the very branch HEAD
        # follows, so "main" and HEAD would still be the same ref after the
        # next commit and `git diff main HEAD` would show nothing at all.
        # Asserted, not just run: if this ever fails silently (e.g. "main"
        # already existed for some reason the real_repo fixture's `-b work`
        # did not anticipate), every assertion below would fail for the
        # WRONG reason -- a same-branch, always-empty diff -- rather than
        # this one, clear reason.
        branch_result = _git(real_repo, "branch", "main", "HEAD")
        assert branch_result.returncode == 0, (
            f"could not create 'main' at HEAD: {branch_result.stderr}"
        )
        bad.write_bytes(b"# area is 20\xb2 sqm\ndef f():\n    return 2\n")
        _git(real_repo, "add", "-A")
        _git(real_repo, "commit", "-q", "-m", "edit the file with the bad byte")

        # Prove the byte is genuinely invalid UTF-8 in this exact diff output
        # -- independent of what this machine's platform-default text
        # encoding happens to tolerate. This is what actually crashed on
        # Linux CI's strict-UTF-8 default.
        raw = subprocess.run(
            ["git", "diff", "--unified=0", "main", "HEAD", "--", "bad.py"],
            cwd=real_repo, env=_clean_env(), capture_output=True, check=False,
        ).stdout
        with pytest.raises(UnicodeDecodeError):
            raw.decode("utf-8")

        result = changed_line_numbers(["bad.py"], str(real_repo))
        assert result != {}, (
            "a real, resolvable diff came back as the full-scan fallback -- "
            "the crash was swallowed into a false 'could not determine', "
            "not actually fixed"
        )
        assert result.get("bad.py") == {1, 3}, (
            "the changed lines (the comment with the bad byte, and the "
            "return statement) should still be reported correctly even "
            "with the invalid byte replaced during decoding"
        )

    def test_the_nested_git_helper_decodes_explicitly_not_by_platform_default(
        self, monkeypatch
    ):
        """The test above cannot force-fail on every machine: Windows'
        platform-default text encoding (cp1252 here) happens to tolerate
        byte 0xb2, so calling through to a REAL subprocess never crashes
        here regardless of whether the fix is present -- only Linux's
        strict-UTF-8 default does, which is what CI actually runs on. This
        test instead asserts the fix's literal presence -- encoding='utf-8',
        errors='replace' passed to subprocess.run -- which fails identically
        on every platform if either kwarg is ever removed, closing the gap
        the test above cannot."""
        import qa_gate

        seen: dict = {}

        def fake_run(*args, **kwargs):
            seen.update(kwargs)
            raise subprocess.SubprocessError("stop before actually running git")

        monkeypatch.setattr(qa_gate.subprocess, "run", fake_run)
        # changed_line_numbers swallows SubprocessError from its nested _git
        # and returns {} (its own documented "could not determine" fallback)
        # -- the interesting assertion is what fake_run was CALLED with, not
        # this function's return value.
        changed_line_numbers(["x.py"], ".")
        assert seen.get("encoding") == "utf-8", (
            "the nested _git() inside changed_line_numbers no longer passes "
            "encoding='utf-8' to subprocess.run -- this is the exact "
            "regression that crashed CI on a pre-existing non-UTF-8 byte"
        )
        assert seen.get("errors") == "replace", (
            "the nested _git() inside changed_line_numbers no longer passes "
            "errors='replace' to subprocess.run"
        )
