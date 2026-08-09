#!/usr/bin/env python3
# prior-art-checked: reuse not viable because the two existing ratchets guard
# different things and neither can see an uncollected file. Four sweeps,
# 2026-08-09 against origin/main af7982a8:
#   * scripts/check_dependency_skips.py + dependency-skip-baseline.json --
#     guards tests that SKIP for a missing library. A quarantined file never
#     runs at all, so it produces no skip and is invisible to that check.
#   * scripts/validate_schema_contract.py + schema_contract_baseline.json --
#     the shrink-only BASELINE PATTERN is copied from here deliberately, but it
#     checks SQL identifiers, not test collection.
#   * scripts/brief_field_coverage_ratchet.py -- locks model fields.
#   * No script anywhere reads tests/conftest.py's collect_ignore; grep for
#     'collect_ignore' outside conftest returns nothing.
"""Shrink-only ratchet for quarantined test files.

WHY
---
On 2026-05-23, one commit -- the very commit that turned CI and the pre-push
hook ON -- quarantined 16 test files so the new gates could go green. That is
the honest price of switching enforcement on. The problem is what happened
next: nothing.

The exemption was invisible. The files sit in `collect_ignore` in
tests/conftest.py, so pytest never collects them. They produce no "skipped"
line, they are absent from every count, and `pytest -m stale` returns ZERO
tests -- so even someone deliberately hunting for them finds nothing. A list in
a Python file that nothing reads and nothing reports is not technical debt, it
is a hiding place.

Re-measured 2026-08-09 against the live database: FIVE of the sixteen passed
with no changes whatsoever -- 35 working tests switched off for no current
reason. Two more had been broken BY the quarantining itself: inserting
`pytestmark = pytest.mark.stale` at the top of the file pushed
`from __future__ import annotations` below other statements, which is a
SyntaxError. One of those two is test_lga_coverage.py, the gate that enforces
"do not enable an LGA before its data is ready" -- and 13 councils with zero
provisions are live.

WHAT THIS DOES
--------------
Turns an invisible permanent exemption into a number that can only go down.

  * A file quarantined but NOT in the baseline  -> FAIL. New debt is refused.
  * A baseline file that now PASSES             -> FAIL. Fixed means deleted
                                                   from the baseline, not left
                                                   as standing amnesty.
  * A baseline file still failing               -> reported, allowed.

The second rule is the one that matters. Without it a baseline becomes exactly
what collect_ignore already was: somewhere entries go to be forgotten.

USAGE
    python scripts/check_test_quarantine.py           # report + exit code
    python scripts/check_test_quarantine.py --list    # just show the list
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFTEST = REPO / "tests" / "conftest.py"
BASELINE = REPO / "tests" / "quarantine-baseline.json"


def quarantined_test_files() -> list[str]:
    """Read collect_ignore from tests/conftest.py without importing it.

    Parsed with ast rather than imported, because importing conftest pulls in
    the mock-injection side effects and would be a silly dependency for a
    linter. Only entries that look like test files are considered -- the list
    also holds non-test utility scripts, which are correctly excluded and are
    not debt.
    """
    tree = ast.parse(CONFTEST.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "collect_ignore":
                    if isinstance(node.value, ast.List):
                        vals = [
                            e.value for e in node.value.elts
                            if isinstance(e, ast.Constant) and isinstance(e.value, str)
                        ]
                        return sorted(v for v in vals if v.startswith("test_"))
    return []


def load_baseline() -> dict[str, dict]:
    if not BASELINE.exists():
        return {}
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    # `or []` rather than a .get default: "entries": null is present-but-empty
    # and the default would not apply, so iteration would raise and the whole
    # gate would error out instead of reporting every file as new debt. Failing
    # open on a malformed baseline is the wrong direction for a check like this.
    return {e["file"]: e for e in (data.get("entries") or [])}


def run_one(path: str) -> tuple[bool, str]:
    """Run a single quarantined file. Returns (passes_cleanly, summary).

    `-o addopts=` clears the ini's default deselection so the marker cannot
    hide the result from the very check meant to see it.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/{path}", "-q", "--no-header",
         "-p", "no:cacheprovider", "-o", "addopts="],
        capture_output=True, text=True, cwd=REPO, timeout=300,
    )
    out = (proc.stdout or "").strip().splitlines()
    summary = ""
    for line in reversed(out):
        if re.search(r"\d+ (passed|failed|error|skipped)|no tests ran", line):
            summary = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
            break
    # "Passes cleanly" deliberately EXCLUDES a file that collects but whose
    # every test skips. A test that always skips protects nothing, so promoting
    # it out of quarantine would be the same self-deception in a new costume.
    clean = (
        "passed" in summary
        and "failed" not in summary
        and "error" not in summary
        and proc.returncode == 0
    )
    return clean, summary or "(no recognisable pytest summary)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="print the list and stop")
    args = ap.parse_args()

    quarantined = quarantined_test_files()
    baseline = load_baseline()

    print(f"=== quarantined test files: {len(quarantined)} ===")
    if args.list:
        for f in quarantined:
            b = baseline.get(f, {})
            print(f"  {b.get('status','UNLISTED'):12} {f:40} {b.get('error','')[:60]}")
        return 0

    errors: list[str] = []

    # Rule 1 -- no new debt.
    for f in quarantined:
        if f not in baseline:
            errors.append(
                f"NEW quarantine, not in the baseline: {f}\n"
                f"    A test file was excluded from collection without recording why. "
                f"Add an entry to tests/quarantine-baseline.json with its measured "
                f"error, or fix the test."
            )

    # Rule 2 -- fixed means deleted, not forgiven.
    fixed_now: list[str] = []
    still_failing: list[tuple[str, str]] = []
    for f in quarantined:
        if f not in baseline:
            continue
        clean, summary = run_one(f)
        if clean:
            fixed_now.append(f"{f} -- now {summary}")
        else:
            still_failing.append((f, summary))

    for f in fixed_now:
        errors.append(
            f"BASELINE ENTRY NOW PASSES: {f}\n"
            f"    Remove it from tests/conftest.py collect_ignore AND from "
            f"tests/quarantine-baseline.json. A passing test left in quarantine is "
            f"exactly the amnesty this file exists to prevent."
        )

    # Rule 3 -- an entry for a file no longer quarantined is stale bookkeeping.
    for f in baseline:
        if f not in quarantined:
            errors.append(
                f"STALE BASELINE ENTRY: {f} is listed but is no longer in "
                f"collect_ignore. Delete the entry."
            )

    print()
    for f, summary in still_failing:
        b = baseline[f]
        print(f"  {b['status']:12} {f:40} {summary}")

    print()
    print(f"  still quarantined : {len(still_failing)}")
    print(f"  newly passing     : {len(fixed_now)}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nPASSED: quarantine list matches the baseline and none of it has "
          "started passing.")
    print("        This is not a clean bill of health -- it means the debt has "
          "not GROWN. It is still debt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
