#!/usr/bin/env python3
"""Liability language scanner for user-facing code.

Scans CHANGED LINES in user-facing files for words that could create
legal liability under Australian Consumer Law s18 or common law
negligent misstatement.

Only flags NEW text — existing reviewed code is not re-scanned.

Usage:
    # Check diff of changed files vs main (for hooks and CI)
    python scripts/liability_language_check.py --diff-base main

    # Check specific files entirely (for full audit)
    python scripts/liability_language_check.py --full file1.tsx file2.py

Exit codes:
    0 = PASSED
    1 = FAILED (flagged terms found in new user-facing text)
"""

import re
import subprocess
import sys
from pathlib import Path

# Words that imply professional assurance, recommendation, or guarantee
FLAGGED_TERMS = re.compile(
    r'\b('
    r'safe|feasible|compliant|(?<!should_)should(?!_)|recommend|suitable|'
    r'adequate|sufficient|approved|guaranteed|certified|confirmed|verified|'
    r'ensure|assure|accurate|definitive|comprehensive|reliable'
    r')\b',
    re.IGNORECASE,
)

# File patterns that contain user-facing text
USER_FACING_PATTERNS = [
    r'\.tsx$', r'\.jsx$',
    r'report.*\.py$', r'pdf.*\.py$',
    r'route\.ts$', r'route\.py$',
]

# Lines to exclude (not user-facing)
EXCLUDE_PATTERNS = [
    r'^\s*//', r'^\s*#', r'^\s*\*', r'^\s*/\*',
    r'^\s*import\s', r'^\s*from\s',
    # camelCase/snake_case identifiers containing flagged words
    r'[a-z](?:Safe|Feasible|Compliant|Sufficient|Reliable|Accurate|Verified|Confirmed|Approved|Certified)',
    r'is_(?:safe|feasible|compliant|sufficient|reliable|accurate|verified|confirmed|approved|certified)',
    r'console\.\w+\(', r'logger\.\w+\(', r'logging\.\w+\(',
    r':\s*(?:boolean|string|number|Optional)',
    r'assert\s', r'expect\(',
]


def is_user_facing_file(filepath: str) -> bool:
    return any(re.search(p, filepath) for p in USER_FACING_PATTERNS)


def is_excluded_line(line: str) -> bool:
    return any(re.search(p, line) for p in EXCLUDE_PATTERNS)


def get_diff_added_lines(base: str) -> dict[str, list[tuple[int, str]]]:
    """Get only ADDED lines from the diff vs base.

    Returns {filepath: [(line_num, line_text), ...]}
    Only includes user-facing files.
    """
    result = subprocess.run(
        ['git', 'diff', '-U0', f'{base}...HEAD'],
        capture_output=True, text=True
    )

    files: dict[str, list[tuple[int, str]]] = {}
    current_file = None
    current_line = 0

    for line in result.stdout.split('\n'):
        # New file header
        if line.startswith('+++ b/'):
            filepath = line[6:]
            current_file = filepath if is_user_facing_file(filepath) else None
            continue

        # Hunk header: @@ -old,count +new,count @@
        if line.startswith('@@') and current_file:
            match = re.search(r'\+(\d+)', line)
            if match:
                current_line = int(match.group(1))
            continue

        # Added line (not the diff header)
        if line.startswith('+') and not line.startswith('+++') and current_file:
            actual_line = line[1:]  # Strip the leading +
            if current_file not in files:
                files[current_file] = []
            files[current_file].append((current_line, actual_line))
            current_line += 1
            continue

        # Context or removed line
        if current_file and not line.startswith('-'):
            current_line += 1

    return files


def scan_lines(filepath: str, lines: list[tuple[int, str]]) -> list[dict]:
    """Scan specific lines for liability language."""
    findings = []
    for line_num, line_text in lines:
        if is_excluded_line(line_text):
            continue
        for match in FLAGGED_TERMS.finditer(line_text):
            term = match.group(1)
            findings.append({
                'file': filepath,
                'line': line_num,
                'term': term,
                'context': line_text.strip()[:120],
            })
    return findings


def scan_file_full(filepath: str) -> list[dict]:
    """Scan an entire file for liability language (for --full mode)."""
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                if is_excluded_line(line):
                    continue
                for match in FLAGGED_TERMS.finditer(line):
                    findings.append({
                        'file': filepath,
                        'line': line_num,
                        'term': match.group(1),
                        'context': line.strip()[:120],
                    })
    except (FileNotFoundError, PermissionError):
        pass
    return findings


def main():
    args = sys.argv[1:]

    if '--diff-base' in args:
        idx = args.index('--diff-base')
        base = args[idx + 1] if idx + 1 < len(args) else 'origin/main'

        diff_lines = get_diff_added_lines(base)
        if not diff_lines:
            print("No new user-facing lines to check.")
            sys.exit(0)

        all_findings = []
        for filepath, lines in diff_lines.items():
            all_findings.extend(scan_lines(filepath, lines))

        file_count = len(diff_lines)

    elif '--full' in args:
        files = [a for a in args if a != '--full']
        user_facing = [f for f in files if is_user_facing_file(f)]
        if not user_facing:
            sys.exit(0)

        all_findings = []
        for filepath in user_facing:
            all_findings.extend(scan_file_full(filepath))
        file_count = len(user_facing)

    else:
        # Default: treat args as files, scan only user-facing ones fully
        files = args
        user_facing = [f for f in files if is_user_facing_file(f)]
        if not user_facing:
            sys.exit(0)

        all_findings = []
        for filepath in user_facing:
            all_findings.extend(scan_file_full(filepath))
        file_count = len(user_facing)

    if not all_findings:
        print(f"Liability language check PASSED ({file_count} files scanned)")
        sys.exit(0)

    print(f"LIABILITY LANGUAGE CHECK: {len(all_findings)} flagged term(s) in new code")
    print(f"Scanned {file_count} user-facing files\n")

    for f in all_findings:
        print(f"  {f['file']}:{f['line']} -- \"{f['term']}\"")
        print(f"    {f['context']}")
        print()

    print("Each flagged term must be:")
    print("  (a) A direct regulatory quotation")
    print("  (b) Replaced with factual language")
    print()
    print("See docs/qa/language-audit-2026-05-18.md for guidelines.")
    sys.exit(1)


if __name__ == '__main__':
    main()
