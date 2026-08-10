#!/usr/bin/env python3
"""Resolve the per-branch QA report path.

prior-art-checked: reuse not viable because no path resolver exists. Four
sweeps, 2026-08-10 against origin/main b1234b4c: (1) `git grep -n "qa_report"`
over the whole tree returns 16 files, every one of which hardcodes the literal
string ``.qa_report.json`` -- there is no helper to reuse and no indirection to
extend; (2) `git grep -nE "def (resolve|report_path|branch_slug|slugify)"` over
scripts/ returns ZERO; (3) `ls scripts/qa_*` is qa_gate.py and
qa_report_template.json only; (4) `~/.claude/plans/INDEX*.md` + MEMORY.md name
``memory/project-qa-report-untracked.md``, which records the OPPOSITE fix
(untracking) and is superseded by this module -- see WHY below.

WHY THIS EXISTS
---------------
``.qa_report.json`` lived at the repo root, tracked, and every branch wrote it.
That is a guaranteed conflict: the moment one PR merges, every other open PR
touching it becomes CONFLICTING, and a conflicting PR gets **no GitHub Actions
run at all** -- nothing fails, nothing starts, and the PR page looks identical
to "still running". On 2026-08-10, 8 of 16 open PRs were dirty for this reason
alone.

This was fixed once already and silently reverted. ``fe725c58`` (#398,
2026-05-28) ran ``git rm --cached .qa_report.json`` for exactly this reason.
``eced0898`` (#434, 2026-05-31) -- a PR titled "add GEO foundation: AI crawlers,
llms.txt, topic sitemaps" -- re-added it. Nobody noticed for ten weeks, because
``.gitignore`` line 4 still lists the file and reads like proof it is untracked;
gitignore does not apply to already-tracked files.

So untracking is NOT the fix here, twice over: it did not hold, and CI treats an
absent report as ``::warning::`` + ``exit 0`` (gates.yml). An untracked report
means the gate silently stops enforcing -- the failure mode the whole
QA-railguard effort exists to prevent. The report is authored judgement; CI
cannot regenerate it, so it has to be committed. It just must not be committed
to a path another branch also writes.

Hence: one file per branch, committed, at ``.qa/reports/<slug>.json``.

WHY EVERY CONSUMER CALLS THIS
-----------------------------
Five things read the report (post-commit hook, Claude pre-commit hook, pre-push
hook, CI workflow, the gate itself) across three languages (Python, POSIX sh,
YAML). If each derived the path independently they would drift, and the drift
would present as "the gate did not run" -- silent, which is the worst failure
mode this repo has. The sh and YAML callers shell out to this module; the Python
callers import it. One definition, five callers.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

#: Directory holding the committed per-branch reports.
REPORT_DIR = ".qa/reports"

#: The pre-2026-08-10 single shared path. Still READ so that a branch cut before
#: this landed keeps passing through its gate instead of failing open, but never
#: written. Drop it once no open branch carries one.
LEGACY_PATH = ".qa_report.json"

#: Prefixes identifying "this is a QA report, not corpus state". Used by
#: doc_claims.py to keep report findings out of the baseline.
REPORT_PREFIXES = (REPORT_DIR + "/", LEGACY_PATH)

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


class BranchUnknown(RuntimeError):
    """The current branch could not be determined by any means."""


def slugify_branch(branch: str) -> str:
    """Return a flat, filename-safe slug for a git branch name.

    ``/`` becomes ``__`` rather than a directory separator, so the report
    directory stays flat. Flat matters for two reasons: pruning is a single
    glob, and git forbids the refs ``fix/foo`` and ``fix/foo/bar`` coexisting
    while a filesystem does not -- nesting would invent a file-vs-directory
    collision that the ref namespace cannot actually produce.

    Args:
        branch: A git branch name, e.g. ``fix/lot-area-mercator``.

    Returns:
        The slug, e.g. ``fix__lot-area-mercator``.

    Raises:
        ValueError: If ``branch`` is empty or slugifies to nothing.
    """
    if not branch or not branch.strip():
        raise ValueError("branch name is empty")
    slug = _UNSAFE.sub("-", branch.strip().replace("/", "__"))
    slug = slug.strip("-.")
    if not slug:
        raise ValueError(f"branch name {branch!r} slugifies to nothing")
    return slug


def _git(args: list[str], project_dir: str | Path) -> tuple[int, str]:
    """Run a git command, returning ``(returncode, stripped_stdout)``.

    Never raises for an ordinary git failure -- callers decide what a non-zero
    code means, because "git could not answer" and "git answered no" need
    different handling, and conflating them is how a gate fails open.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 1, ""
    return proc.returncode, proc.stdout.strip()


def current_branch(project_dir: str | Path = ".") -> str | None:
    """Return the branch this working tree is on, or None if undeterminable.

    Resolution order, most explicit first:

    1. ``QA_REPORT_BRANCH`` -- test hook and escape hatch.
    2. ``GITHUB_HEAD_REF`` -- on a ``pull_request`` event GitHub checks out a
       detached merge commit, so git itself cannot name the branch. This is the
       ONLY thing that works there; omitting it would make CI fall through to
       the legacy path and check the wrong file without saying so.
    3. ``git symbolic-ref --short HEAD`` -- works in linked worktrees, and fails
       non-zero on a detached HEAD rather than inventing an answer. Preferred
       over ``rev-parse --abbrev-ref HEAD``, whose ``HEAD`` sentinel is easy to
       mistake for a branch literally named HEAD.

    Args:
        project_dir: Repository root.

    Returns:
        The branch name, or None on a detached HEAD with no env override.
    """
    for var in ("QA_REPORT_BRANCH", "GITHUB_HEAD_REF"):
        value = os.environ.get(var, "").strip()
        if value:
            return value
    code, out = _git(["symbolic-ref", "--short", "HEAD"], project_dir)
    if code == 0 and out:
        return out
    return None


def target_path(project_dir: str | Path = ".", branch: str | None = None) -> Path:
    """Return where THIS branch's report belongs, whether or not it exists.

    Args:
        project_dir: Repository root.
        branch: Override the detected branch.

    Returns:
        Absolute path to ``<project_dir>/.qa/reports/<slug>.json``.

    Raises:
        BranchUnknown: If no branch could be determined.
        ValueError: If the branch name slugifies to nothing.
    """
    branch = branch or current_branch(project_dir)
    if not branch:
        raise BranchUnknown(
            "cannot determine the current branch (detached HEAD with no "
            "GITHUB_HEAD_REF). Set QA_REPORT_BRANCH or pass the path explicitly."
        )
    return Path(project_dir).resolve() / REPORT_DIR / f"{slugify_branch(branch)}.json"


def _discovered(project_dir: str | Path) -> Path | None:
    """The single report this branch adds or changes relative to origin/main.

    A last resort for a detached HEAD outside GitHub Actions. Returns None
    unless there is exactly one candidate -- two candidates is ambiguous, and
    picking one would bind the gate to an arbitrary file.
    """
    code, out = _git(
        ["diff", "--name-only", "origin/main...HEAD", "--", REPORT_DIR],
        project_dir,
    )
    if code != 0 or not out:
        return None
    names = [n for n in out.splitlines() if n.strip()]
    if len(names) != 1:
        return None
    candidate = Path(project_dir).resolve() / names[0]
    return candidate if candidate.is_file() else None


def resolve(project_dir: str | Path = ".", explicit: str | None = None) -> Path | None:
    """Return the report path that EXISTS for this branch, or None.

    Args:
        project_dir: Repository root.
        explicit: A caller-supplied path, honoured ahead of everything else.

    Returns:
        The existing report path, or None if this branch has no report.
    """
    root = Path(project_dir).resolve()

    for candidate_str in (explicit, os.environ.get("QA_REPORT_PATH", "").strip()):
        if candidate_str:
            candidate = Path(candidate_str)
            if not candidate.is_absolute():
                candidate = root / candidate
            return candidate if candidate.is_file() else None

    try:
        branch_target: Path | None = target_path(root)
    except (BranchUnknown, ValueError):
        branch_target = None
    if branch_target is not None and branch_target.is_file():
        return branch_target

    found = _discovered(root)
    if found is not None:
        return found

    legacy = root / LEGACY_PATH
    return legacy if legacy.is_file() else None


def migrate(project_dir: str | Path = ".") -> tuple[Path | None, str]:
    """Move a legacy root report to this branch's per-branch path.

    Args:
        project_dir: Repository root.

    Returns:
        ``(new_path, message)``. ``new_path`` is None when nothing was moved.
    """
    root = Path(project_dir).resolve()
    legacy = root / LEGACY_PATH
    try:
        dest = target_path(root)
    except (BranchUnknown, ValueError) as exc:
        return None, f"cannot migrate: {exc}"

    if dest.is_file():
        return dest, f"already migrated: {dest.relative_to(root).as_posix()}"
    if not legacy.is_file():
        return None, f"nothing to migrate: no {LEGACY_PATH} in {root}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(legacy.read_bytes())
    legacy.unlink()
    return dest, (
        f"moved {LEGACY_PATH} -> {dest.relative_to(root).as_posix()} "
        f"-- now `git add` it and `git rm --cached {LEGACY_PATH}` if it was tracked"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve the per-branch QA report path.",
    )
    parser.add_argument("--project-dir", default=".")
    parser.add_argument(
        "--target",
        action="store_true",
        help="print where the report BELONGS even if absent (for creating it)",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="move a legacy root .qa_report.json to the per-branch path",
    )
    parser.add_argument(
        "--relative",
        action="store_true",
        help="print a repo-relative path instead of an absolute one",
    )
    args = parser.parse_args(argv)
    root = Path(args.project_dir).resolve()

    if args.migrate:
        path, message = migrate(root)
        print(message)
        return 0 if path is not None else 1

    try:
        path = target_path(root) if args.target else resolve(root)
    except (BranchUnknown, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if path is None:
        return 1  # absent: callers branch on the exit code, stdout stays empty
    if args.relative:
        try:
            print(path.relative_to(root).as_posix())
            return 0
        except ValueError:
            pass
    print(path.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
