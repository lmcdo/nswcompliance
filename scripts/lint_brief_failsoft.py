#!/usr/bin/env python3
"""Fail-soft lint for the Intelligence Brief and conveyancing PDF pipeline.

prior-art-checked: new static-analysis gate; no existing lint covers the
`_df.value or {default}` fail-soft anti-pattern. Distinct from the bracket-access
lint and the prior-art guard.

Rule 1 (brief): ``<name>_df.value or {default}`` / ``or [default]`` discards a
DataField's NOT_AVAILABLE failure signal, so a FAILED fetch gets re-stamped as a
confident AUTHORITATIVE negative (the strata/overlay false-negative bug). The
sanctioned replacement is ``_unwrap_or_default(df, default)``, which returns
``(value, failed)`` so the caller can emit NOT_AVAILABLE on failure.

Rule 2 (conveyancing): inside an ``except`` block, a ``return``/assignment that
yields a user-visible benign value — a string containing "Clear"/"None
identified", or a bare empty ``[]``/``{}``/``""`` — re-stamps a FAILED fetch as
a confident negative in a legal due-diligence PDF (the Bowral bushfire/coverage
defect class). Failure paths must yield a value the renderer shows as
"Not assessed"/omitted, or carry an annotation.

Each match must be one of:
  - resolved so the failure signal survives (no match remains), OR
  - annotated ``# failsoft-ok: <reason>``   -> verified safe degrade (passes), OR
  - annotated ``# failsoft-todo: <WO-ref>`` -> known bug, tracked (warns, non-blocking).
Any un-annotated match FAILS the lint.

Usage: python scripts/lint_brief_failsoft.py [file ...]   (defaults to all targets)
Exit 0 = clean/tracked, 1 = un-annotated anti-pattern found.
"""
from __future__ import annotations

import re
import sys

# `<ident>_df.value or <masking-default>`: a dict `{`, list `[`, or computed
# default `func(...)` — each looks like a genuine empty result and discards the
# NOT_AVAILABLE signal. Scalar defaults (`or None`/`or 0`/`or False`) are allowed.
PATTERN = re.compile(r"\b\w*_df\.value\s+or\s+(?:[\{\[]|\w+\()")
BRIEF_TARGETS = ["services/intelligence_brief.py"]

# Conveyancing scope (rule 2): except-block fallbacks that surface as benign.
CONVEYANCING_TARGETS = [
    "scripts/generate_conveyancing_report.py",
    "services/conveyancing.py",
]
# A return/assignment inside an except block yielding: a string literal that
# contains "Clear"/"None identified", or a bare empty list/dict/string.
_BENIGN_LITERAL = re.compile(
    r"""(?:return|=)\s*(?:
          (?:\[\]|\{\}|""|'')\s*(?:$|\#)          # bare empty default
        | [fr]*["'][^"']*(?:Clear|None\ identified)[^"']*["']   # benign wording
    )""",
    re.VERBOSE,
)
_EXCEPT_RE = re.compile(r"^(\s*)except\b")

DEFAULT_TARGETS = BRIEF_TARGETS + CONVEYANCING_TARGETS


def _scan_except_fallbacks(path: str, lines: list[str]) -> tuple[list[str], list[str]]:
    """Rule 2: benign user-visible defaults produced inside except blocks."""
    errors: list[str] = []
    warnings: list[str] = []
    except_indent: int | None = None
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        m = _EXCEPT_RE.match(line)
        if m:
            except_indent = len(m.group(1))
            continue
        if except_indent is not None and indent <= except_indent:
            except_indent = None  # left the except block
        if except_indent is None:
            continue
        if not _BENIGN_LITERAL.search(line):
            continue
        if "failsoft-ok" in line:
            continue
        if "failsoft-todo" in line:
            warnings.append(f"{path}:{i}: tracked fail-soft (todo) -- {stripped[:120]}")
            continue
        errors.append(f"{path}:{i}: except-block fallback yields a benign user-visible "
                      f"value ('Clear'/empty) -- a failed fetch must render as "
                      f"'Not assessed'/omitted, not as a confident negative. "
                      f"Fix the fallback or annotate `# failsoft-ok: <reason>` / "
                      f"`# failsoft-todo: <WO>`.\n"
                      f"    {stripped[:120]}")
    return errors, warnings


def scan(path: str) -> tuple[list[str], list[str]]:
    """Return (blocking_errors, tracked_warnings) for one file."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return errors, warnings
    norm = path.replace("\\", "/")
    if any(norm.endswith(t) for t in CONVEYANCING_TARGETS):
        e2, w2 = _scan_except_fallbacks(path, lines)
        errors += e2
        warnings += w2
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
