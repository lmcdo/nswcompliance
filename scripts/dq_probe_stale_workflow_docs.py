#!/usr/bin/env python3
"""DQ-55 probe: do docs name GitHub workflows that do not exist?

Exit 0 = clean. Exit 1 = stale references found (DQ-55 still open).

Three docs describe workflows deleted in #506 as current infrastructure, so a
reader believes scheduled DCP extraction and a satellite freshness monitor are
running. Neither is.

Scoped to the three docs that carry FALSE CURRENT-STATE claims. It deliberately
does NOT scan docs/RAILWAY_MONITORS.md, which is a "what happened to each
workflow" migration table -- naming a deleted workflow there is correct by
design. The same filename means opposite things in the two places, which is why
this probe names files rather than grepping the tree.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

DOCS = [
    "docs/DCP_MONITORING.md",
    "docs/DCP_UPDATE_GOVERNANCE.md",
    "docs/QA-DATA-PROVENANCE.md",
]


def main() -> int:
    wf_dir = _ROOT / ".github" / "workflows"
    existing = {p.name for p in wf_dir.glob("*.yml")} | {p.name for p in wf_dir.glob("*.yaml")}

    stale: list[tuple[str, int, str]] = []
    for rel in DOCS:
        path = _ROOT / rel
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name in re.findall(r"([a-z0-9][a-z0-9\-_]*\.ya?ml)", line):
                if name not in existing:
                    stale.append((rel, lineno, name))

    if not stale:
        print(f"DQ-55 CLEAN: no doc names a missing workflow (present: {sorted(existing)})")
        return 0

    print(f"DQ-55 OPEN: {len(stale)} reference(s) to workflows that do not exist.")
    print(f"  workflows that DO exist: {sorted(existing)}")
    for rel, lineno, name in stale:
        print(f"  {rel}:{lineno} -> {name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
