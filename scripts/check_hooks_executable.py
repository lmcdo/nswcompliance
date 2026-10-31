#!/usr/bin/env python3
# prior-art-checked: no existing script reads git index file modes; grep for
# '100755' / 'chmod' across scripts/ and .github/ on origin/main 1dc64af6
# returned nothing.
"""Fail if any git hook is not executable in the git index.

WHY
---
Git silently skips a hook that is not executable ("hook was ignored because
it's not set as executable"). All four files in .githooks/ were committed as
mode 100644, so on every Linux/macOS clone -- including every cloud session --
commits and pushes ran with no local checks at all. Windows ignores the mode,
which is why nobody noticed. Measured 2026-10-31 with
`git ls-tree origin/main .githooks/`.

The mode lives in the index, so this reads `git ls-files -s`, not the
filesystem.
"""
from __future__ import annotations

import subprocess
import sys

HOOK_DIR = ".githooks/"


def non_executable(ls_files_output: str) -> list[str]:
    """Return hook paths whose index mode is not 100755.

    Args:
        ls_files_output: Output of `git ls-files -s -- .githooks`.

    Returns:
        Paths that git would refuse to run.
    """
    bad = []
    for line in ls_files_output.splitlines():
        meta, _, path = line.partition("\t")
        if not path.startswith(HOOK_DIR):
            continue
        fields = meta.strip().split()
        if not fields or fields[0] != "100755":
            bad.append(path)
    return bad


def main() -> int:
    out = subprocess.run(
        ["git", "ls-files", "-s", "--", HOOK_DIR],
        capture_output=True, text=True, check=True,
    ).stdout
    if not out.strip():
        print(f"UNKNOWN: no files tracked under {HOOK_DIR}")
        return 1
    bad = non_executable(out)
    if bad:
        print("Git hooks not executable (git will skip them on Linux/macOS):")
        for p in bad:
            print(f"  {p}")
        print("Fix: git update-index --chmod=+x " + " ".join(bad))
        return 1
    print(f"OK: all hooks under {HOOK_DIR} are 100755")
    return 0


if __name__ == "__main__":
    sys.exit(main())
