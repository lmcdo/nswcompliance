"""Outreach documents must be visible to git.

WHY THIS EXISTS
---------------
`.gitignore` carries `docs/*` with a short allow-list of exceptions. One of
them is `!docs/*.md`, which re-includes markdown at the TOP level of `docs/`
only. `docs/outreach/` is a subdirectory, and once `docs/*` excludes a
directory git never descends into it, so nothing inside could be added — with
no error, no warning, and no entry in `git status`.

PR #982, titled "A one-page brief for students testing the tool", merged
exactly one file: its own 46-line QA report. The 109-line brief it was named
after was written to `docs/outreach/student-brief.md`, silently ignored, and
survived only as an untracked file on one machine. The QA report even listed
the brief under `files`, and the gate passed anyway, because
`check_diff_coverage` only looks for changed files missing from the report and
never for files the report claims that are missing from the change.

WHAT THIS PINS
--------------
The rule, not the file. An already-tracked file stays tracked no matter what
`.gitignore` says, so asserting the brief is tracked would NOT catch someone
deleting the negation — the next new document would vanish exactly as before.
`git check-ignore` answers for a path that need not exist, so the test asks
about a hypothetical future document instead, which is the thing that breaks.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIEF = Path("docs/outreach/student-brief.md")


def _git_env() -> dict[str, str]:
    """The repo's own scrubbed git environment.

    Reused rather than reimplemented: git hooks export GIT_DIR and
    GIT_INDEX_FILE, and those OVERRIDE cwd, so a test that shells out to git
    from inside pre-push would otherwise read the wrong repository.
    """
    spec = importlib.util.spec_from_file_location(
        "qa_report_path_for_outreach_test", REPO_ROOT / "scripts" / "qa_report_path.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.git_env()


def _check_ignore(relpath: str) -> bool:
    """True if git ignores `relpath`.

    Uses -q deliberately. With -v, git exits 0 when the winning rule is a
    NEGATION, so a re-included path reads as "ignored" to any caller checking
    the exit code.
    """
    result = subprocess.run(
        ["git", "check-ignore", "-q", relpath],
        cwd=REPO_ROOT,
        env=_git_env(),
        capture_output=True,
    )
    return result.returncode == 0


def _tracked(relpath: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relpath],
        cwd=REPO_ROOT,
        env=_git_env(),
        capture_output=True,
    )
    return result.returncode == 0


def test_a_new_outreach_document_would_not_be_ignored():
    """The regression that actually bites: the NEXT document, not this one."""
    assert not _check_ignore("docs/outreach/some-future-brief.md"), (
        "docs/outreach/ is gitignored again. A document written there will be "
        "invisible to git — no error, no git status entry — exactly as the "
        "student brief was lost in PR #982. Restore the '!docs/outreach/' and "
        "'!docs/outreach/**' negations in .gitignore."
    )


def test_the_docs_star_rule_still_applies_elsewhere():
    """Control case: the fix must re-include one directory, not defeat the rule.

    Without this, a change that simply deleted `docs/*` would make the test
    above pass while dragging every ignored PDF and scratch file into the repo.
    """
    assert _check_ignore("docs/some-other-subdir/scratch.md"), (
        "docs/* no longer ignores unlisted subdirectories. The outreach fix was "
        "meant to re-include ONE directory, not disable the rule."
    )


def test_every_outreach_document_on_disk_is_tracked():
    """The general form: nothing sitting in docs/outreach/ may be invisible.

    Naming one file per test does not scale and, worse, only protects the
    documents someone remembered to name. This walks what is actually there,
    so a handout dropped in the folder and forgotten fails the build instead of
    quietly living on one machine — which is exactly how the brief was lost.
    """
    outreach = REPO_ROOT / "docs" / "outreach"
    if not outreach.is_dir():
        pytest.fail("docs/outreach/ is missing entirely")

    on_disk = sorted(p for p in outreach.rglob("*.md"))
    assert on_disk, "docs/outreach/ holds no markdown — the brief should be here"

    untracked = [
        p for p in on_disk
        if not _tracked(p.relative_to(REPO_ROOT).as_posix())
    ]
    assert not untracked, (
        "Untracked outreach document(s): "
        + ", ".join(p.relative_to(REPO_ROOT).as_posix() for p in untracked)
        + ". These exist on this machine only and vanish with the worktree. "
        "Either `git add` them or delete them."
    )


def test_student_brief_is_tracked():
    assert _tracked(str(BRIEF).replace("\\", "/")), (
        f"{BRIEF} is not tracked by git. It is the handout the student launch "
        "depends on; untracked, it exists on one machine and disappears with "
        "the worktree."
    )


def test_student_brief_has_content():
    """A tracked but empty file would satisfy the check above and help nobody."""
    path = REPO_ROOT / BRIEF
    if not path.exists():
        pytest.fail(f"{BRIEF} is missing from the working tree")
    text = path.read_text(encoding="utf-8")
    assert len(text.splitlines()) > 50, (
        f"{BRIEF} is {len(text.splitlines())} lines — the brief is ~109. "
        "A truncated handout is worse than none, because it still gets sent."
    )
    # The two findings the launch plan calls worth the whole exercise. If the
    # brief stops asking for them, the feedback widget's cohort copy — which
    # names the same two — is no longer backed by anything.
    assert "This control is missing." in text
    assert "This number is wrong." in text
