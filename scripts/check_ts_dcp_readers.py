#!/usr/bin/env python3
# prior-art-checked: no existing check enforces the TS-reader consolidation
# (the campaign doc §4 item 5 names this exact grep as the falsifiable check).
# Pure source scan — no DB, no network.
"""Falsifiable check: frontend readers of dcp_setback_controls.

Campaign item 5, observation mode. `FROM dcp_setback_controls` in
frontend-nextjs must resolve ONLY to:
  - the internal review routes (the human write-path UI, excluded by design),
  - the coverage metadata route (direct SQL retained WITH the standard
    guards, measured no-change),
  - test files that PIN the absence of inline SQL (they name the table in
    assertions/prose).
Every value-serving route sources rows via lib/dcp-controls-client
(/pipeline/dcp-controls -> conveyancing_db.fetch_dcp_setbacks — the ONE
guarded implementation).

Exit codes: 0 = ran and recorded; 2 = could not measure. The count of
UNEXPECTED readers is reported, not enforced (blocking is earned).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(REPO_ROOT, "frontend-nextjs")

ALLOWED = {
    "app/api/internal/setback-review/route.ts",
    "app/api/internal/setback-review/[id]/route.ts",
    "app/api/dcp/coverage/route.ts",
}
ALLOWED_PREFIXES = ("__tests__/",)

# The is_current = TRUE / needs_review guards live in conveyancing_db.
# fetch_dcp_setbacks — the point of this check is that NO frontend file
# queries the table (and therefore no frontend file needs those predicates).
PATTERN = re.compile(r"FROM\s+dcp_setback_controls", re.I)
# Comments legitimately NAME the table (provenance notes in lib/coverage.ts,
# docstrings). The check is about what a file EXECUTES, so comments are
# stripped before matching — same doctrine as the parking-rates source test.
_COMMENTS = re.compile(r"/\*[\s\S]*?\*/|(^|\s)//[^\n]*", re.M)


def main() -> int:  # pragma: no cover - CLI entry point
    if not os.path.isdir(FRONTEND):
        print("ERROR: frontend-nextjs not found — nothing was measured, "
              "which is not a pass. Exiting 2.", file=sys.stderr)
        return 2

    readers: list[str] = []
    for dirpath, dirnames, filenames in os.walk(FRONTEND):
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".next")]
        for name in filenames:
            if not name.endswith((".ts", ".tsx")):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8") as f:
                    src = _COMMENTS.sub(" ", f.read())
                if PATTERN.search(src):
                    rel = os.path.relpath(path, FRONTEND).replace("\\", "/")
                    readers.append(rel)
            except OSError:
                continue

    if not readers:
        print("ERROR: zero files reference the table — the scan is wrong "
              "(the internal review routes always do). Exiting 2.",
              file=sys.stderr)
        return 2

    unexpected = [r for r in readers
                  if r not in ALLOWED
                  and not r.startswith(ALLOWED_PREFIXES)]
    report = {
        "check": "ts_dcp_readers",
        "mode": "observation",
        "run_date": date.today().isoformat(),
        "readers_total": len(readers),
        "allowed": sorted(r for r in readers if r not in unexpected),
        "unexpected_inline_readers": sorted(unexpected),
        "target": "unexpected_inline_readers == [] (campaign item 5); NOT "
                  "enforced — observation mode until false-positive "
                  "behaviour is known",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
