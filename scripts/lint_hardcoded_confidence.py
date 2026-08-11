#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no committed lint targets
# confidence literals. The SHAPE (repo scan, per-line findings, noqa
# suppression, categorised counts) follows scripts/lint_hardcoded_zone_codes.py
# / lint_bracket_access.py deliberately; the target regex and the
# enclosing-function heuristic are new.
"""OBSERVATION-MODE lint: literal "high"/"medium"/"low" confidence assignments.

Output-grounding campaign item 2 (§7 revised order). A displayed confidence
badge is a representation; a hardcoded literal is a representation nobody
computed. This script REPORTS where confidence values are assigned as string
literals outside a *confidence-computing* function (name contains
"confidence", e.g. `_compute_confidence`), so the eventual gate can be sized
against an OBSERVED false-positive rate.

DELIBERATELY NOT WIRED: not in pre-push, not in CI, and it always exits 0.
Blocking status must be EARNED — per the campaign's Sol review (§7 finding 6),
gates start in observation mode, measure legitimate-failure categories, then
block the paid channel only. Do not wire this without that measurement.

What counts as a hit: `confidence = "high"`, `confidence="medium"` (kwarg),
`"confidence": "low"` (dict/JSON), `confidence: 'high'` (TS object literal) —
including ternary/branched forms (a branch over real conditions is still a
literal at the assignment site; whether that is acceptable is exactly what the
observation phase measures).

Categories reported separately (all counted, none hidden):
  computed  — inside a function whose name contains "confidence" (the house
              pattern: conveyancing/flood _compute_confidence, granny_flat)
  test      — under tests/ or *.test.* / __tests__ (fixtures need literals)
  prod      — everything else: the number the future gate would act on

Suppress per-line with:  # noqa: confidence-literal  /  // noqa: confidence-literal

Known-absent field (do NOT "fix" via this lint): services/threat_radar.py has
no confidence field at all — nothing to lint there; adding one is design work
that waits for the absence census (docs/qa/absence-semantics-census-2026-08.md).

Exit 0 always (observation mode).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent

CONFIDENCE_LITERAL_RE = re.compile(
    r"""(?:\bconfidence\w*\s*[=:]\s*|["']confidence["']\s*:\s*)"""
    r"""(?:f?["'](high|medium|low)["'])""",
    re.IGNORECASE,
)
SUPPRESS_RE = re.compile(r"#\s*noqa:\s*confidence-literal|//\s*noqa:\s*confidence-literal")
PY_DEF_RE = re.compile(r"^(\s*)def\s+(\w+)\s*\(")
TS_FN_RE = re.compile(r"^(\s*)(?:function\s+(\w+)|(?:const|let)\s+(\w+)\s*=)")
COMMENT_RE = re.compile(r"^\s*(#|//|\*|/\*)")

SCAN_DIRS = ("services", "scripts", "enrichment", "src", "frontend-nextjs")
SKIP_PARTS = {"node_modules", ".next", "__pycache__", ".git", "venv", "venv_linux"}
EXTS = {".py", ".ts", ".tsx"}


def _is_test_path(path: Path) -> bool:
    s = str(path).replace("\\", "/")
    return ("/tests/" in s or "/__tests__/" in s or ".test." in path.name
            or path.name.startswith("test_") or path.name.startswith("conftest"))


def _enclosing_function(lines: list[str], idx: int, is_py: bool) -> str:
    """Name of the nearest enclosing function above lines[idx] (best-effort:
    nearest def/function at strictly lower indent; '' if none found)."""
    target_indent = len(lines[idx]) - len(lines[idx].lstrip())
    pattern = PY_DEF_RE if is_py else TS_FN_RE
    for j in range(idx - 1, -1, -1):
        m = pattern.match(lines[j])
        if m:
            indent = len(m.group(1))
            if indent < target_indent or target_indent == 0:
                return (m.group(2) or (m.group(3) if m.lastindex and m.lastindex >= 3 else "")) or ""
    return ""


def scan() -> list[dict]:
    findings = []
    for base in SCAN_DIRS:
        root = REPO / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in EXTS:
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "confidence" not in text and "Confidence" not in text:
                continue
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if COMMENT_RE.match(line) or SUPPRESS_RE.search(line):
                    continue
                m = CONFIDENCE_LITERAL_RE.search(line)
                if not m:
                    continue
                is_py = path.suffix == ".py"
                fn = _enclosing_function(lines, i, is_py)
                if _is_test_path(path):
                    category = "test"
                elif "confidence" in fn.lower():
                    category = "computed"
                else:
                    category = "prod"
                findings.append({
                    "file": str(path.relative_to(REPO)).replace("\\", "/"),
                    "line": i + 1,
                    "literal": m.group(1).lower(),
                    "function": fn or "(module level)",
                    "category": category,
                    "text": line.strip()[:110],
                })
    return findings


def main() -> int:
    findings = scan()
    by_cat: dict[str, list[dict]] = {"prod": [], "computed": [], "test": []}
    for f in findings:
        by_cat[f["category"]].append(f)

    print("=== confidence-literal lint — OBSERVATION MODE (never blocks) ===")
    print(f"  total literal assignments : {len(findings)}")
    print(f"  prod (outside compute fn) : {len(by_cat['prod'])}  <- the number a future gate would act on")
    print(f"  inside confidence-named fn: {len(by_cat['computed'])}")
    print(f"  test fixtures             : {len(by_cat['test'])}")

    print("\n--- prod hits, by file ---")
    by_file: dict[str, list[dict]] = {}
    for f in by_cat["prod"]:
        by_file.setdefault(f["file"], []).append(f)
    for file in sorted(by_file):
        print(f"  {file}  ({len(by_file[file])})")
        for f in by_file[file]:
            print(f"    :{f['line']:<5} [{f['literal']}] in {f['function']}: {f['text']}")

    if by_cat["computed"]:
        print("\n--- inside confidence-computing functions (house pattern, listed for completeness) ---")
        for f in by_cat["computed"]:
            print(f"  {f['file']}:{f['line']} [{f['literal']}] in {f['function']}")

    print("\nObservation mode: exit 0 regardless of findings. Blocking must be "
          "earned with an observed false-positive rate (campaign §7 finding 6).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
