#!/usr/bin/env python3
"""DQ-48 probe: a named SAR threshold/endpoint with no call site behind it.

Exit 0 = clean. Exit 1 = a constant was reintroduced.

Matches ASSIGNMENTS via the AST, not mentions. A text grep false-fails here:
services/flood_truth.py still discusses FLOOD_RATIO in a comment explaining why
it was removed, and that comment is the record, not the defect.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
TARGET = _ROOT / "services" / "flood_truth.py"
NAMES = {"FLOOD_RATIO", "PC_CATALOG", "S1_COLLECTION"}


def main() -> int:
    if not TARGET.exists():
        print(f"DQ-48 UNKNOWABLE: {TARGET} does not exist")
        return 1

    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    found = []
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name) and t.id in NAMES:
                found.append((t.id, node.lineno))

    if not found:
        print("DQ-48 CLEAN: no SAR constant is assigned in services/flood_truth.py")
        return 0

    print("DQ-48 REGRESSED: a named SAR constant is back with no detector behind it.")
    for name, lineno in found:
        print(f"  services/flood_truth.py:{lineno} -> {name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
