#!/usr/bin/env python3
"""Delete QA reports whose branch no longer exists on the remote.

prior-art-checked: reuse not viable because nothing prunes anything. Four
sweeps, 2026-08-10 against origin/main b1234b4c: (1) `git grep -nE "def
(prune|reap|gc_|cleanup)"` over scripts/ returns ZERO; (2) `ls scripts/ | grep
-iE "prune|clean|reap|stale"` returns ZERO; (3) `git grep -n "ls-remote"` over
the whole tree returns ZERO -- nothing anywhere asks the remote which branches
are alive; (4) MEMORY.md and `~/.claude/plans/INDEX*.md` describe no cleanup
job. The nearest neighbours are check_test_quarantine.py and
check_pr_gates.py, both of which assert a condition and neither of which
removes a file.

WHY THIS EXISTS
---------------
A per-branch QA report is committed on its branch, so a squash merge lands it
on main and it stays there forever. Nothing else deletes it: the branch is gone,
the PR is closed, and the file that described that PR's judgement is now inert
weight in the tree. One per merged PR accumulates without limit.

They are harmless individually -- a few KB, and they never conflict, which is
the entire point of the per-branch scheme -- so this is housekeeping, not a
gate. It is deliberately NOT wired into CI: an automated delete driven by a
transient `git ls-remote` failure is a worse outcome than a directory with a
few hundred stale files in it.

FAIL-CLOSED ON DELETION
-----------------------
The remote branch list is the only evidence that a report is orphaned. If
`git ls-remote` fails, times out, or returns nothing, this script deletes
NOTHING and says so. An empty branch list means "the question was not answered",
never "no branch is alive" -- reading it the second way would delete every
report in the repository in one run.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_report_path import REPORT_DIR, slugify_branch  # noqa: E402


class RemoteUnavailable(RuntimeError):
    """The remote branch list could not be obtained, so nothing may be deleted."""


def live_branch_slugs(project_dir: Path, remote: str = "origin") -> set[str]:
    """Return the slug of every branch that currently exists on the remote.

    Raises:
        RemoteUnavailable: If the remote could not be queried, or answered with
            no branches at all. Both are treated as "unknown", never as "empty".
    """
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--heads", remote],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        raise RemoteUnavailable(f"git ls-remote could not run: {exc}") from exc

    if proc.returncode != 0:
        raise RemoteUnavailable(
            f"git ls-remote exited {proc.returncode}: {proc.stderr.strip()[:200]}"
        )

    slugs: set[str] = set()
    for line in proc.stdout.splitlines():
        _, _, ref = line.partition("\t")
        ref = ref.strip()
        if not ref.startswith("refs/heads/"):
            continue
        branch = ref[len("refs/heads/") :]
        try:
            slugs.add(slugify_branch(branch))
        except ValueError:
            continue

    if not slugs:
        raise RemoteUnavailable(
            "git ls-remote returned no branches. Treating that as 'unknown', "
            "not 'none alive' — deleting on it would remove every report."
        )
    return slugs


def find_orphans(project_dir: Path, live: set[str]) -> list[Path]:
    """Reports in the tree whose slug matches no live remote branch."""
    reports_dir = project_dir / REPORT_DIR
    if not reports_dir.is_dir():
        return []
    return sorted(
        path
        for path in reports_dir.glob("*.json")
        if path.stem not in live
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Delete QA reports whose branch is gone from the remote.",
    )
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--remote", default="origin")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete. Without it this only lists what it would delete.",
    )
    args = parser.parse_args(argv)
    project_dir = Path(args.project_dir).resolve()

    try:
        live = live_branch_slugs(project_dir, args.remote)
    except RemoteUnavailable as exc:
        print(f"REFUSING TO PRUNE: {exc}", file=sys.stderr)
        return 2

    orphans = find_orphans(project_dir, live)
    if not orphans:
        print(f"Nothing to prune. {len(live)} live branch(es) on {args.remote}.")
        return 0

    verb = "Deleting" if args.apply else "Would delete"
    print(f"{verb} {len(orphans)} orphaned report(s) ({len(live)} live branches):")
    for path in orphans:
        print(f"  {path.relative_to(project_dir).as_posix()}")
        if args.apply:
            path.unlink()

    if args.apply:
        print(f"\nDeleted {len(orphans)}. Commit them: git add -A {REPORT_DIR}")
    else:
        print("\nDry run. Re-run with --apply to delete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
