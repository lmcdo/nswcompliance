#!/usr/bin/env python3
# prior-art-checked: reuse not viable as a new HARNESS -- none is written here. This is a
# thin case list driving the shared scripts/falsifiability.py (#890), which is exactly the
# reuse that module was built for; before it, every session open-coded this and it failed
# twice (a plant that no-opped on CRLF, a restore that never ran).
"""Prove the controls-vs-PDF check can actually go red.

Five defects, each planted into the real file, each expected to be CAUGHT by the test
suite, each restored byte-identically. A check whose tests survive the removal of its own
logic is decoration -- this is the difference between that and a verification.

Makes no database calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from falsifiability import ProofCase, prove, pytest_runner  # noqa: E402

TARGET = REPO_ROOT / "scripts" / "validate_controls_against_source_pdf.py"

_OK_LINE = ("    ok = (not missing) and coverage >= TERM_COVERAGE_MIN "
            "and bool(wanted) and bool(terms)")

CASES = [
    ProofCase(
        label="stop requiring the numbers",
        path=TARGET,
        find=_OK_LINE,
        replace="    ok = coverage >= TERM_COVERAGE_MIN and bool(wanted) and bool(terms)",
    ),
    ProofCase(
        label="stop requiring the subject to match",
        path=TARGET,
        find=_OK_LINE,
        replace="    ok = (not missing) and bool(wanted) and bool(terms)",
    ),
    ProofCase(
        label="soften the pass mark to 50%",
        path=TARGET,
        find="DATA_MARK = 0.95",
        replace="DATA_MARK = 0.50",
    ),
    ProofCase(
        label="count 'could not check' as checkable",
        path=TARGET,
        find="COULD_NOT_CHECK = {DOC_NO_TEXT, DOC_UNAVAILABLE, NO_QUOTE, NO_TESTABLE_VALUE}",
        replace="COULD_NOT_CHECK = set()",
    ),
    ProofCase(
        label="stop stripping clause markers",
        path=TARGET,
        find='    return _CLAUSE_MARKER.sub("", text or "", count=1)',
        replace='    return text or ""',
    ),
    ProofCase(
        label="stop preferring the stored value",
        path=TARGET,
        find="    wanted = required_values(value_min, value_max)",
        replace="    wanted = []",
    ),
    ProofCase(
        label="stop folding & into and",
        path=TARGET,
        find='("&", " and ")):',
        replace='("&", " & ")):',
    ),
]


def main() -> int:
    runner = pytest_runner(["tests/test_controls_against_source_pdf.py"], cwd=REPO_ROOT)
    report = prove(CASES, runner)
    print(report.table())
    print()
    if report.ok:
        print("PROVEN: every planted defect was caught, and the file was restored clean.")
        return 0
    print("NOT PROVEN: a defect slipped past the suite, or the baseline was not green. "
          "The check cannot be relied on until this is fixed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
