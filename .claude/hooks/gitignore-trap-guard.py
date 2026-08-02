#!/usr/bin/env python
"""Warn when a newly written file sits under a whitelist-ignored directory.

WHY THIS EXISTS
---------------
`.gitignore` line 402 ignores `scripts/*` and re-includes named files with
`!scripts/foo.py`. That makes re-inclusion POSSIBLE, not automatic — a new script
is silently untracked until someone remembers the `!` line. The trap has now cost
three separate sessions, including the one that fixed its root cause (changing
`scripts/` to `scripts/*`), and each miss costs CI round-trips because the file is
absent from the checkout CI builds.

WHY `git check-ignore` AND NOT `git ls-files --error-unmatch`
------------------------------------------------------------
`ls-files --error-unmatch` is the right check at COMMIT time. At PostToolUse time
a brand-new file has simply not been `git add`ed yet, so that command fails for
EVERY new file — it would be a 100% false-positive alarm and get ignored within a
day. The condition that actually distinguishes the trap is "would git refuse to
add this?", which is `git check-ignore`. The commit-time command is printed in the
message as the follow-up, so both checks are used where each one works.

Warns, never blocks: the file is already on disk by the time PostToolUse runs, so
blocking achieves nothing except noise. Exit 0 always.

Fail-open on any internal error — a bug here must never interfere with real work.
"""
import json
import os
import subprocess
import sys

# Directories whose contents are whitelist-ignored, or where an untracked file is
# a silent failure rather than an obvious one.
WATCHED = ("scripts/", "services/", "enrichment/", "migrations/")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool = data.get("tool_name") or data.get("toolName") or ""
    if tool not in ("Write", "Edit"):
        return 0

    tool_input = data.get("tool_input") or data.get("toolInput") or {}
    path = tool_input.get("file_path") or ""
    if not path:
        return 0

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        rel = os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return 0
    if rel.startswith(".."):
        return 0
    if not rel.startswith(WATCHED):
        return 0

    try:
        # -q: exit 0 means "this path IS ignored", which is the trap.
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", rel],
            cwd=root, capture_output=True, timeout=10,
        ).returncode == 0
        if not ignored:
            return 0
        # Distinguish "already tracked" (gitignore does not apply to tracked
        # files, so this is fine) from genuinely untracked-and-ignored.
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=root, capture_output=True, timeout=10,
        ).returncode == 0
        if tracked:
            return 0
    except Exception:
        return 0

    # partition, not split()[0]: total on any input, including "" and a path with
    # no separator, so there is no index to get wrong.
    top = rel.partition("/")[0] + "/"
    print(
        f"\n⚠  GITIGNORE TRAP: {rel} is IGNORED and untracked.\n"
        f"   `{top}` is whitelist-ignored, so this file will NOT be committed and\n"
        f"   will be ABSENT from the checkout CI builds — the failure shows up as a\n"
        f"   confusing 'file not found' in CI, not as a git error here.\n\n"
        f"   Fix now, before committing:\n"
        f"     1. append to .gitignore:   !{rel}\n"
        f"     2. git add .gitignore {rel}\n"
        f"     3. confirm:                git ls-files --error-unmatch {rel}\n",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
