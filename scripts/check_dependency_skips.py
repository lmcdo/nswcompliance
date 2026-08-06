#!/usr/bin/env python3
"""Ratchet on tests that do not run because an import is missing.

prior-art-checked: reuse not viable because the surfaced matches are all
compliance HTTP routes that share only the word "check"; the ratchet siblings
this actually belongs beside are scripts/check_test_baselines.py (test COUNTS
never drop) and scripts/brief_field_coverage_ratchet.py, and neither can host
this — they ratchet numbers that a skipped test still contributes to. Skips are
precisely what those two cannot see.

WHY THIS EXISTS
main was red from 2026-08-03 to 2026-08-06: four tests in test_dcp_as_at.py
needed PyMuPDF, requirements-test.txt did not install it, and `pytest -x`
stopped the run at the first one — so ~1,800 tests did not execute for three
days without anyone noticing. Adding the dependency fixes those four. It does
not fix the class.

Auditing the rest of the suite for the same cause turned up the quieter half:
23 tests that never run in ANY environment because a missing import turns them
into a skip, and a skip is green. A test that cannot run is not a passing test,
and the only thing separating the loud version of this failure from the silent
one is whether the missing import happens to sit inside a `pytest.importorskip`.

This makes the silent version countable. tests/conftest.py writes every
dependency-driven skip to .pytest-skips.json; this script compares the count
against dependency-skip-baseline.json and fails when it rises. The existing 23
are baselined, not blessed: the baseline may only shrink, and shrinking it is
how the coverage gets recovered.

Deliberately NOT counted: env-gated skips ("set RUN_LIVE_GEMINI=1"), which are
a choice rather than a missing dependency. Folding those in would make the
number measure intent instead of coverage.

Exit codes:
    0  count <= baseline (and prints the current census)
    1  count > baseline, or a new dependency appeared
    2  the skip report is missing — treated as a failure, never as a pass,
       because "no report" and "no skips" must not look the same
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / ".pytest-skips.json"
BASELINE = ROOT / "dependency-skip-baseline.json"


def main() -> int:
    if not REPORT.exists():
        print(f"DEPENDENCY-SKIP RATCHET: FAILED — {REPORT.name} not found.")
        print("  The pytest run must complete for the census to be written.")
        print("  A missing report is not an empty one; refusing to pass.")
        return 2

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    # `or`, not a .get default: these files are hand-edited, and an
    # explicit null would sail past a default and crash the comparison.
    skips = report.get("skips") or []
    count = report.get("count")
    if count is None:
        count = len(skips)

    by_dep: dict[str, list[str]] = {}
    for s in skips:
        by_dep.setdefault(s["dependency"], []).append(s["test"])

    if not BASELINE.exists():
        print(f"DEPENDENCY-SKIP RATCHET: no baseline — writing {BASELINE.name} at {count}")
        BASELINE.write_text(json.dumps(
            {"count": count, "dependencies": {k: len(v) for k, v in sorted(by_dep.items())}},
            indent=1) + "\n", encoding="utf-8")
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    limit = baseline.get("count") or 0
    known = baseline.get("dependencies") or {}

    print(f"DEPENDENCY-SKIP CENSUS: {count} test(s) skipped for a missing import "
          f"(baseline {limit})")
    for dep in sorted(by_dep):
        was = known.get(dep)
        mark = "" if was == len(by_dep[dep]) else f"  <- was {was if was is not None else 'NEW'}"
        print(f"  {dep:<28} {len(by_dep[dep]):>3}{mark}")

    new_deps = sorted(set(by_dep) - set(known))
    if new_deps:
        print()
        print("DEPENDENCY-SKIP RATCHET: FAILED — a NEW dependency is now skipping tests:")
        for dep in new_deps:
            for t in by_dep[dep]:
                print(f"  {dep}: {t}")
        print("  Install it in requirements-test.txt so the tests run, or, if it")
        print("  genuinely cannot be a CI dependency, say why here and raise the")
        print("  baseline in the same commit — deliberately, in review.")
        return 1

    if count > limit:
        print()
        print(f"DEPENDENCY-SKIP RATCHET: FAILED — {count} skips against a baseline of {limit}.")
        print("  More tests stopped running than last time.")
        return 1

    if count < limit:
        print()
        print(f"Baseline is loose by {limit - count}. Lower `count` in "
              f"{BASELINE.name} to {count} to lock the gain in.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
