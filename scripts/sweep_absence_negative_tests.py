#!/usr/bin/env python3
"""Tests that assert an ABSENCE produces a NEGATIVE verdict rather than unknown.

prior-art-checked: reuse not viable because nothing looks for this. Four sweeps
2026-08-08 against origin/main 858c7735: (1) `git ls-files scripts/ | grep -iE
"sweep|absence|test_"` returns check_test_baselines.py and check_dependency_skips.py,
which count tests and skips and never read an assertion; (2) `git grep -niE
"absence.?negative|assert.*absence|pins the defect"` over py/sh returns only the
flood tests this sweep was commissioned by; (3) scripts/mutation_health.py drives
mutmut and asks whether a test CAN fail, not what it asserts; (4) DQ-53 is the
can't-fail-test item and is explicitly a different class. This is the machinery
for the second class.

WHY THIS IS A DIFFERENT CLASS FROM DQ-53
----------------------------------------
DQ-53 is about tests that cannot fail. These CAN fail. They assert the wrong
thing. Every gate ran correctly, every suite was green, and six of them were
guarding a false answer on the most consequential field in a property report —
one named `test_epi_none_class_not_in_100yr`, which asserted that the EPI layer
returning NOTHING meant "not in a flood zone".

A green suite is not evidence the assertions are right.

WHAT IT FINDS, AND WHAT IT CANNOT
---------------------------------
It pairs two signals inside one test function:

  * an ABSENCE set up   — a fixture assigning None/null, an empty list or dict,
    a raise/side_effect, or a test NAME containing missing/absent/empty/none/
    unavailable/fail/error/timeout/no_data
  * a NEGATIVE asserted — `is False`, `== False`, `assert not x`, `toBe(false)`

Both in the same function is a candidate, not a verdict. Deciding whether False
is CORRECT there needs a human: "no flood study matched this point" is a true
negative, "the flood study could not be read" is not, and they look identical in
a test. Every hit is ranked, none is judged.

Ranking is by how consequential the field is if the assertion is wrong, using
the module under test. It is a triage order, not a severity claim.

READ ONLY. Prints; changes nothing.

Usage:
    python scripts/sweep_absence_negative_tests.py
    python scripts/sweep_absence_negative_tests.py --tier 1
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# What a wrong "False" costs the reader, worst first. Matched against the test
# file path and the assertion text. Tier 1 is a claim a buyer acts on directly.
_TIERS: list[tuple[int, str, tuple[str, ...]]] = [
    (1, "served hazard verdict a buyer acts on",
     ("flood", "bushfire", "coastal", "contaminat", "mine_subsid", "landslide",
      "heritage", "acid_sulfate")),
    (2, "eligibility or permissibility — drives whether they can build",
     ("eligib", "permissib", "exempt", "cdc", "housing_sepp", "upzoning",
      "development_permission", "zone")),
    (3, "other served report fields",
     ("shadow", "solar", "granny", "threat_radar", "climate", "terrain",
      "servicing", "gsp", "strata", "conveyanc", "brief", "da_outcome")),
    (4, "pipeline, extraction and internal plumbing", ()),
]

_ABSENCE_NAME_RE = re.compile(
    r"missing|absent|empty|none|null|unavailable|no_data|nodata|not_found|"
    r"fail|error|timeout|exception|raises|unreachable|offline|down|"
    r"no_match|no_result|no_rows|blank",
    re.I,
)

_NEG_JS_RE = re.compile(r"toBe\(false\)|toBeFalsy\(\)|toEqual\(false\)")
_ABS_JS_RE = re.compile(r"null|undefined|\[\]|\{\}|mockRejected|throw", re.I)


@dataclass
class Hit:
    tier: int
    path: str
    line: int
    test: str
    why_absence: str
    assertion: str


def _tier_for(path: str, text: str) -> tuple[int, str]:
    haystack = f"{path} {text}".lower()
    for tier, label, keys in _TIERS:
        if keys and any(k in haystack for k in keys):
            return tier, label
    return 4, _TIERS[-1][1]


def _py_absence_signals(fn: ast.AST) -> str | None:
    """Why this test looks like it sets up an absence."""
    reasons: list[str] = []
    name = getattr(fn, "name", "")
    if _ABSENCE_NAME_RE.search(name):
        reasons.append("name")
    for node in ast.walk(fn):
        if isinstance(node, ast.Constant) and node.value is None:
            reasons.append("None literal")
            break
    for node in ast.walk(fn):
        if isinstance(node, (ast.List, ast.Dict)) and not getattr(node, "elts", getattr(node, "keys", [1])):
            reasons.append("empty collection")
            break
    for node in ast.walk(fn):
        if isinstance(node, ast.keyword) and node.arg in ("side_effect", "return_value"):
            src = ast.unparse(node.value) if hasattr(ast, "unparse") else ""
            if "Error" in src or "Exception" in src or src == "None":
                reasons.append(f"mock {node.arg}")
                break
    return ", ".join(dict.fromkeys(reasons)) if reasons else None


def _py_negative_assertions(fn: ast.AST) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assert):
            continue
        try:
            src = ast.unparse(node.test)
        except Exception:  # noqa: BLE001
            continue
        if re.search(r"\bis False\b|== False|^not \w", src) or src.startswith("not "):
            out.append((node.lineno, src[:110]))
    return out


def sweep_python(files: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for rel in files:
        p = _ROOT / rel
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test"):
                continue
            why = _py_absence_signals(node)
            if not why:
                continue
            for lineno, src in _py_negative_assertions(node):
                tier, _ = _tier_for(rel, node.name + " " + src)
                hits.append(Hit(tier, rel, lineno, node.name, why, src))
    return hits


def sweep_typescript(files: list[str]) -> list[Hit]:
    """Line-based: TS has no stdlib parser, so the window is the enclosing it()."""
    hits: list[Hit] = []
    for rel in files:
        p = _ROOT / rel
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        current, current_line = "", 0
        for i, line in enumerate(lines, start=1):
            m = re.search(r"\b(it|test)\s*\(\s*['\"](.+?)['\"]", line)
            if m:
                current, current_line = m.group(2), i
            if not current or not _NEG_JS_RE.search(line):
                continue
            window = "\n".join(lines[max(0, current_line - 1): i + 1])
            why = []
            if _ABSENCE_NAME_RE.search(current):
                why.append("name")
            if _ABS_JS_RE.search(window):
                why.append("null/empty/throw in the case")
            if not why:
                continue
            tier, _ = _tier_for(rel, current + " " + line)
            hits.append(Hit(tier, rel, i, current[:60], ", ".join(why), line.strip()[:110]))
    return hits


def main(argv: list[str] | None = None) -> int:
    # partition, not split()[0]: a module stripped of docstrings by -OO leaves
    # __doc__ as None, and split on an empty string still indexes fine but the
    # None does not. Cheap to make total.
    ap = argparse.ArgumentParser(
        description=(__doc__ or "absence-negative sweep").partition("\n")[0]
    )
    ap.add_argument("--tier", type=int, default=None, help="show only this tier")
    args = ap.parse_args(argv)

    env_keys = subprocess.run(
        ["git", "ls-files"], cwd=str(_ROOT), capture_output=True, text=True, timeout=30
    )
    if env_keys.returncode != 0:
        print("git ls-files failed — UNKNOWABLE, not zero.")
        return 2
    tracked = env_keys.stdout.split()

    py = [f for f in tracked if f.startswith("tests/") and f.endswith(".py")]
    ts = [f for f in tracked if "__tests__" in f and f.endswith((".ts", ".tsx"))]

    hits = sweep_python(py) + sweep_typescript(ts)
    hits.sort(key=lambda h: (h.tier, h.path, h.line))

    shown = [h for h in hits if args.tier is None or h.tier == args.tier]

    print("=" * 96)
    print("TESTS THAT MAY PIN 'ABSENCE = NEGATIVE'")
    print("=" * 96)
    print(f"  python test files scanned : {len(py)}")
    print(f"  TS/TSX test files scanned : {len(ts)}")
    print(f"  candidates                : {len(hits)}")
    print()
    print("  A candidate is NOT a defect. False is the right answer when a source")
    print("  was consulted and said no. It is wrong only when the source was never")
    print("  reached. The two are indistinguishable from the test text — a human")
    print("  decides. Ranked by what a wrong False would cost the reader.")
    print()

    by_tier: dict[int, list[Hit]] = {}
    for h in hits:
        by_tier.setdefault(h.tier, []).append(h)
    for tier, label, _ in _TIERS:
        print(f"  tier {tier}  {label:<52} {len(by_tier.get(tier, [])):>4}")
    print()

    last_tier = None
    for h in shown:
        if h.tier != last_tier:
            label = next(l for t, l, _ in _TIERS if t == h.tier)
            print("=" * 96)
            print(f"TIER {h.tier} — {label}")
            print("=" * 96)
            last_tier = h.tier
        print(f"  {h.path}:{h.line}")
        print(f"      test      : {h.test}")
        print(f"      absence   : {h.why_absence}")
        print(f"      asserts   : {h.assertion}")
    print()
    print("  READ ONLY — nothing was changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
