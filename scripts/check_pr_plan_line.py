"""CI: a PR that changes a pipeline file must say which approved plan it implements.

prior-art-checked: plan none (owner-approved guardrail, 2026-11-03); the file list is the
plan-line-gate hook's own, kept equal by tests/test_plan_line_gate_ci.py.

The PR body needs a line `Plan: <plan file>.md -- <section>` or `Plan: none`. The owner
reads it before saying "merge"; this only makes sure it is there to read.
    python scripts/check_pr_plan_line.py --base <sha>      # body from $GITHUB_EVENT_PATH
Exit 0 = no pipeline file changed, or the line is there; 1 = missing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

PIPELINE = (
    "scripts/dcp_extract_changed.py", "scripts/ai_extractor.py", "scripts/dcp_commit_approved.py",
    "scripts/r2_monitor.py", "scripts/add_new_chapter.py", "scripts/council_quote.py",
    "scripts/council_quote_db.py", "scripts/dcp_page_repair.py", "scripts/pipeline_run.py",
    "migrations/",
)
PLAN = re.compile(r"^\s*\**Plan:\**\s*(none\b.*|\S+\.md\s+--\s+\S.*)$", re.I | re.M)   # file AND section, or none


def pipeline_changes(files: list[str]) -> list[str]:
    return [f for f in files if any(f == p or f.startswith(p) for p in PIPELINE)]


def has_plan_line(body: str | None) -> bool:
    return bool(PLAN.search(body or ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "x").strip().splitlines()[0])
    ap.add_argument("--base", required=True)
    a = ap.parse_args(argv)
    files = subprocess.run(["git", "diff", "--name-only", f"{a.base}..HEAD"], capture_output=True,
                           text=True, check=True).stdout.split()
    changed = pipeline_changes(files)
    if not changed:
        print("plan line: no pipeline file changed")
        return 0
    body = ""
    ev = os.environ.get("GITHUB_EVENT_PATH")
    if ev and os.path.exists(ev):
        body = (json.load(open(ev, encoding="utf-8")).get("pull_request") or {}).get("body") or ""
    if has_plan_line(body):
        print(f"plan line: present for {len(changed)} pipeline file(s)")
        return 0
    print(f"::error::This PR changes pipeline file(s) {changed} but its description has no "
          "`Plan: <plan file>.md -- <section>` or `Plan: none` line. Add it, then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
