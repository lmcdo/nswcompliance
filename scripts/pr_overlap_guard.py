#!/usr/bin/env python3
"""Advisory: warn when the current branch's changed files overlap an OPEN PR.

prior-art-checked: no existing PR-overlap checker in the repo (grep
check_pr_overlap / pr.*overlap = none). The prior-art guard and dedup ratchet
check code duplication, not in-flight-PR overlap. Reuse not viable.

Why this exists: the recurring failure mode is starting NEW work that duplicates
an already-open PR (e.g. re-implementing a fix that is sitting in review). Code
guards (prior-art, jscpd) cannot see open PRs. This shells out to `gh` and warns
before push.

Non-blocking by contract: always exits 0, and fails open (silent) if git or gh
are unavailable, so it can never break a push. Wired as an advisory in
.githooks/pre-push.
"""
from __future__ import annotations

import json
import subprocess
import sys


def _sh(args: list[str]) -> str:
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except Exception:
        return ""


def compute_overlaps(
    cur_branch: str,
    changed_files,
    prs,
) -> list[tuple[int, str, list[str]]]:
    """Pure overlap logic (no I/O — unit-testable).

    Return [(pr_number, title, [overlapping files])] for PRs (excluding the
    current branch) whose files intersect changed_files.
    """
    changed = set(changed_files)
    hits: list[tuple[int, str, list[str]]] = []
    for pr in prs:
        if pr.get("headRefName") == cur_branch:
            continue  # the current branch's own PR is not a conflict
        pr_files = {f.get("path") for f in (pr.get("files") or []) if isinstance(f, dict)}
        overlap = sorted(changed & pr_files)
        if overlap:
            hits.append((pr.get("number"), pr.get("title") or "", overlap))
    return hits


def find_overlaps(base: str = "main") -> list[tuple[int, str, list[str]]]:
    """Gather git/gh state, then delegate to compute_overlaps."""
    cur = _sh(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    changed = {
        f for f in _sh(["git", "diff", "--name-only", f"origin/{base}...HEAD"]).splitlines() if f
    }
    if not changed:
        return []

    raw = _sh(["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName,files"])
    if not raw:
        return []
    try:
        prs = json.loads(raw)
    except (ValueError, TypeError):
        return []

    return compute_overlaps(cur, changed, prs)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "main"
    hits = find_overlaps(base)
    if hits:
        print("")
        print("==========================================")
        print("  PR OVERLAP ADVISORY (non-blocking)")
        print("==========================================")
        print("  Your changed files also appear in these OPEN PR(s):")
        for num, title, files in hits:
            print(f"    #{num} {title[:72]}")
            for f in files:
                print(f"        - {f}")
        print("  Confirm you are not duplicating in-flight work before opening a PR.")
        print("")
    return 0  # advisory only — never block


if __name__ == "__main__":
    sys.exit(main())
