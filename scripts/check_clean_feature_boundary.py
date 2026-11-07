#!/usr/bin/env python3
# prior-art-checked: four sweeps 2026-11-07 on origin/main eaa9964d. (1) DB content: N/A, pure source
# scan. (2) Frontend: __tests__/lib/no-control-chars-in-source.test.ts has a walk() skeleton only;
# scripts/check_ts_dcp_readers.py forbids one table (dcp_setback_controls) in unexpected files, in
# observation mode, with an allow-list shape (the inverse of this check). (3) Python: no lint_*.py
# forbids council reads in a named file set. (4) Plans: ce-lmr-tod-clean-state-law-PLAN-2026-11-07.md
# sections 2d/2f record that nothing forbids regulatory_provisions, its views or council filters.
"""Boundary check: the low-and-mid-rise / TOD feature files must not read council-plan data.

The feature answers from state law and live state map layers only. A file listed in
`.claude/clean_feature_files.json` therefore must NOT touch:
  R1  the views of the rules table (they include council rows),
  R2  any council-plan table or reader (names that start with the plan code and an underscore),
  R3  the council-mixed API routes,
  R4  a council filter on the rules table (a filter is a read of council rows), or
  R5  the rules table itself unless the SAME QUERY pins it to state-law rows (`source_council IS NULL`
      within the next 400 characters, up to the next semicolon or backtick).
A listed file that does not exist is a failure, so a rename cannot silently drop coverage.
Comments are stripped before matching (they may name what a file avoids); docstrings are NOT stripped,
because SQL often lives in triple-quoted strings. Pure source scan: no database, no network.

Exit codes: 0 = clean, 1 = violation or missing file, 2 = manifest unreadable.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / ".claude" / "clean_feature_files.json"

# Comment stripping keeps newlines so reported line numbers match the file.
_BLOCK = re.compile(r"/\*[\s\S]*?\*/")
_SLASH = re.compile(r"(^|\s)//[^\n]*")
_HASH = re.compile(r"(^|\s)#[^\n]*")

_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("R1-view", re.compile(r"regulatory_provisions_(canonical|clean)", re.I), "a view that includes council rows"),
    ("R2-council-table", re.compile(r"(?<![A-Za-z0-9])dcp_[A-Za-z0-9_]*", re.I), "a council-plan table or reader"),
    ("R3-mixed-route", re.compile(r"api/dcp/|provisions/for-property|structured-controls", re.I), "a council-mixed route"),
    (
        "R4-council-filter",
        re.compile(r"source_council\s*(=|\bIN\b|\bANY\b|\bIS\s+NOT\s+NULL\b)|former_council", re.I),
        "a council filter on the rules table",
    ),
]
_TABLE = re.compile(r"regulatory_provisions(?![A-Za-z0-9_])", re.I)
_PINNED = re.compile(r"source_council\s+IS\s+NULL", re.I)
_PIN_WINDOW = 400  # characters after the table name in which the same query must pin state-law rows


def _blank(m: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


def strip_comments(text: str, suffix: str) -> str:
    """Blank out comments, keeping every newline so line numbers stay true."""
    if suffix == ".py":
        return _HASH.sub(_blank, text)
    return _SLASH.sub(_blank, _BLOCK.sub(_blank, text))


def find_violations(text: str, suffix: str = ".py") -> list[tuple[int, str, str]]:
    """Return (line, rule, what) for every breach in `text`. Empty list = clean."""
    code = strip_comments(text, suffix)
    found: list[tuple[int, str, str]] = []
    for rule, pattern, what in _RULES:
        for m in pattern.finditer(code):
            found.append((code.count("\n", 0, m.start()) + 1, rule, what))
    for table in _TABLE.finditer(code):
        # Per query, not per file: one pinned query must not hide a second unpinned one.
        window = code[table.start() : table.start() + _PIN_WINDOW]
        end = re.search(r";|`", window)
        if not _PINNED.search(window[: end.start()] if end else window):
            found.append(
                (
                    code.count("\n", 0, table.start()) + 1,
                    "R5-unpinned-table",
                    "the rules table is read without pinning to state-law rows",
                )
            )
    return sorted(found)


def listed_files(manifest: Path = MANIFEST) -> list[str]:
    return list(json.loads(manifest.read_text(encoding="utf-8"))["files"])


def check_manifest(manifest: Path = MANIFEST, root: Path = REPO_ROOT) -> list[str]:
    """Return one message per problem. Empty list = every listed file exists and is clean."""
    files = listed_files(manifest)
    if not files:
        return ["manifest lists no files: an empty list would pass silently"]
    problems: list[str] = []
    for rel in files:
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel}: listed but missing")
            continue
        for line, rule, what in find_violations(path.read_text(encoding="utf-8"), path.suffix):
            problems.append(f"{rel}:{line}: {rule}: {what}")
    return problems


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        files = listed_files()
        problems = check_manifest()
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot read manifest {MANIFEST}: {exc}")
        return 2
    if "--list" in argv:
        print("\n".join(files))
    for p in problems:
        print(p)
    print(f"clean-feature boundary: {len(problems)} problem(s) across {len(files)} listed file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
