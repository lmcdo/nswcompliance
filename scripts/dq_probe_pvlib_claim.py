#!/usr/bin/env python3
"""DQ-47 probe: pvlib credited as the shadow method while never being used.

Exit 0 = clean. Exit 1 = production code imports pvlib again.

Scoped to non-test source ON PURPOSE. tests/test_shadow_calibration.py DOES
import pvlib and should: it is the independent reference the shadow calibration
is measured against, and it is the evidence the fix holds. A repo-wide grep
would false-fail on exactly the test that proves the thing.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ["services", "src", "scripts", "enrichment"]


def _root_module(dotted: str | None) -> str:
    """First segment of a dotted module name, or "" for None/empty.

    str.partition always returns a 3-tuple, so this unpacks rather than
    subscripts. `"a.b".split(".")[0]` is safe for every input the AST can
    produce here, but the indexing pattern is the risky one in general and
    the gate is right to refuse it on sight rather than case by case.
    """
    head, _, _ = (dotted or "").partition(".")
    return head


def _imports_pvlib(path: Path) -> int | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if _root_module(a.name) == "pvlib":
                    return node.lineno
        elif isinstance(node, ast.ImportFrom):
            if _root_module(node.module) == "pvlib":
                return node.lineno
    return None


def main() -> int:
    offenders = []
    for d in SOURCE_DIRS:
        base = _ROOT / d
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "test" in path.name:
                continue
            lineno = _imports_pvlib(path)
            if lineno:
                offenders.append((path.relative_to(_ROOT).as_posix(), lineno))

    if not offenders:
        print("DQ-47 CLEAN: pvlib is not imported by any non-test module")
        return 0

    print("DQ-47 REGRESSED: production code imports pvlib.")
    for rel, lineno in offenders:
        print(f"  {rel}:{lineno}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
