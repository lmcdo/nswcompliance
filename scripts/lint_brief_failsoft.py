#!/usr/bin/env python3
"""Fail-soft lint for the Intelligence Brief (the S1 enforceable hook).

prior-art-checked: new static-analysis gate; no existing lint covers the
`_df.value or {default}` fail-soft anti-pattern. Distinct from the bracket-access
lint and the prior-art guard.

Blocks the silent-false-negative class: ``<name>_df.value or {default}`` /
``or [default]`` discards a DataField's NOT_AVAILABLE failure signal, so a FAILED
fetch gets re-stamped as a confident AUTHORITATIVE negative (the strata/overlay
false-negative bug). The sanctioned replacement is ``_unwrap_or_default(df, default)``,
which returns ``(value, failed)`` so the caller can emit NOT_AVAILABLE on failure.

Each match must be one of:
  - resolved via ``_unwrap_or_default`` (no raw ``.value or`` remains), OR
  - annotated ``# failsoft-ok: <reason>``   -> verified safe degrade (passes), OR
  - annotated ``# failsoft-todo: <WO-ref>`` -> known bug, tracked (warns, non-blocking).
Any un-annotated match FAILS the lint.

Usage: python scripts/lint_brief_failsoft.py [file ...]   (defaults to the brief)
Exit 0 = clean/tracked, 1 = un-annotated anti-pattern found.
"""
from __future__ import annotations

import re
import sys

# `<ident>_df.value or <masking-default>`: a dict `{`, list `[`, or computed
# default `func(...)` — each looks like a genuine empty result and discards the
# NOT_AVAILABLE signal. Scalar defaults (`or None`/`or 0`/`or False`) are allowed.
PATTERN = re.compile(r"\b\w*_df\.value\s+or\s+(?:[\{\[]|\w+\()")
DEFAULT_TARGETS = ["services/intelligence_brief.py"]


def scan(path: str) -> tuple[list[str], list[str]]:
    """Return (blocking_errors, tracked_warnings) for one file."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return errors, warnings
    for i, line in enumerate(lines, 1):
        if not PATTERN.search(line):
            continue
        if "failsoft-ok" in line:
            continue
        if "failsoft-todo" in line:
            warnings.append(f"{path}:{i}: tracked fail-soft (todo) -- {line.strip()[:120]}")
            continue
        errors.append(f"{path}:{i}: un-annotated `_df.value or <default>` -- "
                      f"discards the NOT_AVAILABLE signal (silent false-negative). "
                      f"Use _unwrap_or_default(df, default) and emit NOT_AVAILABLE on `failed`, "
                      f"or annotate `# failsoft-ok: <reason>` / `# failsoft-todo: <WO>`.\n"
                      f"    {line.strip()[:120]}")
    return errors, warnings


def main(argv: list[str]) -> int:
    targets = argv[1:] or DEFAULT_TARGETS
    all_errors: list[str] = []
    all_warnings: list[str] = []
    for path in targets:
        e, w = scan(path)
        all_errors += e
        all_warnings += w
    for w in all_warnings:
        print(f"FAILSOFT-LINT (tracked): {w}")
    if all_errors:
        print("\nFAILSOFT-LINT: FAILED -- fail-soft anti-pattern(s) found:\n")
        for e in all_errors:
            print(f"  - {e}\n")
        return 1
    print(f"FAILSOFT-LINT: PASSED ({len(all_warnings)} tracked todo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
