#!/usr/bin/env python3
"""Lint: detect unsafe bracket access on untrusted dicts in staged Python diffs.

Only checks NEW lines (+ lines in git diff) in staged .py files under services/.
This avoids flagging the 300+ existing bracket accesses while catching new ones.

Flags:  response["key"]  ->  use .get("key") or .get("key", default)
Suppress per-line with:  # noqa: bracket-access

Exit 0 = clean, exit 1 = violations found.
"""

import re
import subprocess
import sys


BRACKET_RE = re.compile(
    r'\b([a-z_][a-z0-9_]*)\["([a-zA-Z_][a-zA-Z0-9_]*)"\]'
)

# Variables that are always safe (we built the dict, or it's a typed row)
SAFE_VARS = {
    "by_dev_type", "ov_by_type", "result", "self", "os", "sys", "env",
    "row",         # psycopg2 DictRow from our own SELECT
    "s",           # short alias for DB row in list comprehensions
    "r",           # short alias for DB row
    "rec",         # record from DB
    "controls",    # controls dict is built by us from API, keys are known
    "config",      # config dicts
    "CONFIG",
    "settings",
    "kwargs",
    "params",
    "headers",
    "mapping",
    "lookup",
    "cache",
}

SAFE_KEY_RE = re.compile(r'^__\w+__$')

SKIP_LINE_RE = re.compile(
    r'^\s*(import |from |class |def |#|.*# noqa: bracket-access)'
)


def get_staged_diff_lines() -> list[tuple[str, int, str]]:
    """Return (filepath, lineno, line_text) for new lines in staged services/*.py."""
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--cached", "-U0", "--diff-filter=ACM",
             "--", "services/*.py"],
            text=True, encoding="utf-8",
        )
    except subprocess.CalledProcessError:
        return []

    results = []
    current_file = None
    current_line = 0

    for line in diff.splitlines():
        # Track which file we're in
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        # Track line numbers from @@ hunk headers
        if line.startswith("@@"):
            # Format: @@ -old,count +new,count @@
            m = re.search(r'\+(\d+)', line)
            if m:
                current_line = int(m.group(1))
            continue

        # Only care about added lines (not removed)
        if line.startswith("+") and not line.startswith("+++"):
            if current_file:
                results.append((current_file, current_line, line[1:]))  # strip leading +
            current_line += 1
        elif not line.startswith("-"):
            # Context line — increment line counter
            current_line += 1

    return results


def check_line(filepath: str, lineno: int, line: str) -> list[str]:
    """Check a single line for bracket access violations."""
    if SKIP_LINE_RE.match(line):
        return []

    violations = []
    for match in BRACKET_RE.finditer(line):
        var_name = match.group(1)
        key_name = match.group(2)

        if var_name in SAFE_VARS:
            continue
        if SAFE_KEY_RE.match(key_name):
            continue

        # Skip assignment targets: dict["key"] = value
        after = line[match.end():].lstrip()
        if after.startswith("=") and not after.startswith("=="):
            continue

        violations.append(
            f"  {filepath}:{lineno}: {var_name}[\"{key_name}\"] "
            f"-- use .get(\"{key_name}\") or .get(\"{key_name}\", default) "
            f"or add  # noqa: bracket-access"
        )

    return violations


def main() -> int:
    # --all mode: scan entire files (for one-off audit)
    if "--all" in sys.argv:
        import glob
        files = glob.glob("services/**/*.py", recursive=True)
        all_violations = []
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(lines, 1):
                all_violations.extend(check_line(filepath, lineno, line))

        if all_violations:
            print(f"WARNING: Bracket access lint: {len(all_violations)} "
                  f"unsafe dict access(es) found across all files")
            for v in all_violations:
                print(v)
            return 1
        return 0

    # Default: staged diff mode (for pre-commit hook)
    diff_lines = get_staged_diff_lines()
    if not diff_lines:
        return 0

    all_violations = []
    for filepath, lineno, line in diff_lines:
        all_violations.extend(check_line(filepath, lineno, line))

    if all_violations:
        print(f"WARNING: Bracket access lint: {len(all_violations)} NEW "
              f"unsafe dict access(es) in staged changes")
        print("  Use .get() for dicts from external APIs, DB rows, or user input.")
        print()
        for v in all_violations:
            print(v)
        print()
        print("  Suppress false positives with:  # noqa: bracket-access")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
