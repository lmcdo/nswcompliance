#!/usr/bin/env python3
"""Lint: hand-typed planning figures in served code. Shrink-only ratchet.

prior-art-checked: reuse not viable because scripts/lint_hardcoded_zone_codes.py
matches zone-code LISTS only; no check existed for numeric figures. This file
copies its baseline shape (per-file counts, rise fails, fall is announced).

Every regulatory figure must be served from the database with its quote of the
law (CLAUDE.md "Regulatory Data -- Never Hardcode"). That rule was written down
and never enforced for numbers. Found 2026-10-10: a typed "450 m2 minimum" on
six granny-flat surfaces and a typed SEPP table citing clauses not in force.

A hit is a string literal holding a number with a planning unit (m2, m, %,
spaces, storeys) next to a planning word (setback, height, lot, frontage, floor,
FSR, parking, site area, coverage, SEPP/LEP/DCP, clause, minimum, maximum, open
space). Heuristic: it catches the shapes that actually leaked; a bare number
in a list is not caught, which is why the target is the database, not this.

    python scripts/lint_hardcoded_regulatory_numbers.py --baseline           # CI: fail on any rise
    python scripts/lint_hardcoded_regulatory_numbers.py --baseline --update  # lower it after a fix
    python scripts/lint_hardcoded_regulatory_numbers.py --list               # every hit

Suppress a genuine non-regulatory figure (an engineering assumption, a UI
example) on its line with:  # noqa: regulatory-number -- <reason>
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOTS = ("frontend-nextjs/app", "frontend-nextjs/components", "frontend-nextjs/lib", "services")
SKIP = ("__tests__", "node_modules", "/tests/", ".test.", "/test_", "/archive/", "__pycache__")
SUFFIXES = (".ts", ".tsx", ".py")
BASELINE = os.path.join(".claude", "regulatory_number_baseline.json")

LITERAL = re.compile(
    r"""(['"`][^'"`\n]*?\b\d+(?:\.\d+)?\s?(?:m²|m2|sqm|square metres|metres|m\b|%|spaces?|storeys?)[^'"`\n]*['"`])""")
PLANNING = re.compile(
    r"setback|height|lot|frontage|floor|FSR|parking|site area|coverage|storey|SEPP|LEP|DCP|"
    r"cl\.|clause|minimum|maximum|open space", re.I)
SUPPRESS = "noqa: regulatory-number"


def hits_in_text(text: str) -> list[str]:
    """Every hand-typed planning figure in one file's text."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("//", "#", "*")) or SUPPRESS in line:
            continue
        # The planning word is looked for on the whole LINE, not only inside the
        # literal: a table row like { label: 'Max. floor area', value: '60 m2' }
        # splits them across two strings (the typed SEPP table did exactly this).
        if PLANNING.search(line):
            out += LITERAL.findall(line)
    return out


def scan(root: Path = Path(".")) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for top in ROOTS:
        for f in (root / top).rglob("*"):
            rel = f.relative_to(root).as_posix()
            if f.suffix not in SUFFIXES or any(s in "/" + rel for s in SKIP):
                continue
            hits = hits_in_text(f.read_text(encoding="utf-8", errors="replace"))
            if hits:
                found[rel] = hits
    return found


def compare(baseline: dict[str, int], current: dict[str, int]) -> tuple[list[str], list[str]]:
    """(rises, falls) per file. A file absent from the baseline counts from 0."""
    rises = [f"{f}: {baseline.get(f, 0)} -> {n}" for f, n in sorted(current.items()) if n > baseline.get(f, 0)]
    falls = [f"{f}: {n} -> {current.get(f, 0)}" for f, n in sorted(baseline.items()) if current.get(f, 0) < n]
    return rises, falls


def main(argv: list[str]) -> int:
    found = scan()
    current = {f: len(h) for f, h in found.items()}
    total = sum(current.values())
    if "--list" in argv:
        for f, hits in sorted(found.items()):
            for h in hits:
                print(f"{f}: {h}")
        print(f"{total} hand-typed planning figure(s) in {len(found)} file(s)")
        return 0
    if "--update" in argv:
        with open(BASELINE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"total": total, "per_file": dict(sorted(current.items()))}, fh, indent=2)
            fh.write("\n")
        print(f"Regulatory-number baseline updated: {total} across {len(current)} files.")
        return 0
    try:
        with open(BASELINE, encoding="utf-8") as fh:
            baseline = json.load(fh)["per_file"]
    except (OSError, ValueError, KeyError):
        print(f"Regulatory-number baseline: cannot read {BASELINE} -- refusing to pass.")
        return 1
    rises, falls = compare(baseline, current)
    if rises:
        print("Regulatory-number baseline: FAILED -- a hand-typed planning figure was added.")
        print("  Serve it from the database with its quote of the law, or mark a genuine")
        print(f"  non-regulatory value with '# {SUPPRESS} -- <reason>'.")
        for r in rises:
            print(f"  {r}")
        return 1
    if falls:
        print("Regulatory-number baseline: IMPROVED -- lower it and commit "
              "(python scripts/lint_hardcoded_regulatory_numbers.py --baseline --update)")
        for f in falls:
            print(f"  {f}")
    print(f"Regulatory-number baseline: OK -- {total} figure(s), none increased.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
