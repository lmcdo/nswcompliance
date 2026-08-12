#!/usr/bin/env python3
"""Run the data-quality ledger's checks, and refuse a status that has rotted.

prior-art-checked: reuse not viable because nothing reads the ledger
programmatically. Four sweeps, 2026-08-12 against origin/main 2c809a93:
(1) not a data source, so the DB sweep is N/A -- this reads a markdown file and
shells out to probes; (2) frontend -- grep for DATA_QUALITY_TRACKER|dq_check|
DQ-[0-9] over frontend-nextjs/{app,lib,components} returns three files, and all
three are "// DQ-30:" style CODE COMMENTS citing a defect, not readers of the
ledger; the guard's suggested reuse targets (canibuildit/check,
permissibility/check, subdivision-check) are NSW planning compliance endpoints
and share only the word "check"; (3) python -- no dq_* runner exists in
scripts/, and the four files that mention the ledger (doc_claims.py,
lint_hardcoded_zone_codes.py, measure_control_type_mismatch.py,
validate_toc_join.py) each MEASURE one defect, none enumerates rows or enforces
a status; (4) plans + MEMORY.md name .claude/DATA_QUALITY_TRACKER.md as the
ledger but record no runner. The SHAPE is deliberately reused from
scripts/check_test_quarantine.py, which already ratchets in both directions;
confirmed none of check_test_quarantine.py, check_test_baselines.py or
check_dependency_skips.py touches the ledger, so there is nothing to extend.

WHY THIS EXISTS
---------------
.claude/DATA_QUALITY_TRACKER.md says its purpose is to "track data quality
issues systematically across Claude sessions". It cannot, on its own: a status
written by hand is a claim about the past, and this repo has three receipts that
such claims decay silently.

* #398 untracked the QA report; .gitignore made it invisible for TEN WEEKS.
* DQ-54 was logged 2026-08-08 naming "three call sites". There were NINE.
* On 2026-08-12 the tracker still read "DQ-54: Open -- report-only" hours after
  it had been fixed and merged, and its header said "Last Updated: 2026-08-08".

So the ledger keeps the narrative and this keeps the part that can be executed.

THE RATCHET RUNS BOTH WAYS
--------------------------
    declared "fixed" + check FAILS  -> RED. A regression, or a fix that never was.
    declared "open"  + check PASSES -> RED. Silently fixed; the ledger is now
                                       lying in the direction nobody checks.

The second direction is the one that matters. A stale "open" row is invisible
forever -- nobody re-tests a defect they believe is still broken -- and it is
exactly how DQ-54 sat "open" while merged.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not invent checks. "check": null is an honest recorded gap, and the
count of nulls prints on every run so the gap stays visible rather than being
mistaken for coverage. A check that cannot fail is what produced DQ-30's "0%
drift" verification, which passed while 241 rows stayed broken -- worse than no
check at all.

Usage::

    python scripts/dq_check.py                # run everything, ratchet enforced
    python scripts/dq_check.py --id DQ-55     # one row, verbose
    python scripts/dq_check.py --coverage     # only: is every row accounted for?
    python scripts/dq_check.py --list         # what has a check and what does not
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LEDGER = _ROOT / ".claude" / "DATA_QUALITY_TRACKER.md"
_CHECKS = _ROOT / ".claude" / "dq_checks.json"

#: Only these two declared states carry an enforceable expectation. "partial",
#: "backlog", "accepted" and friends are genuinely ambiguous -- a partial fix
#: can legitimately pass or fail its check -- and inventing an expectation for
#: them would manufacture exactly the false precision this file exists to remove.
_ENFORCED = {"fixed": 0, "open": 1}

_TIMEOUT = 900


def load_checks() -> dict:
    with _CHECKS.open(encoding="utf-8") as f:
        return json.load(f)["checks"]


def ledger_ids() -> list[str]:
    """Every DQ id the markdown ledger declares, in file order."""
    text = _LEDGER.read_text(encoding="utf-8")
    seen, out = set(), []
    for m in re.finditer(r"^\|\s*(DQ-\d+[a-z]?):", text, re.M):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


#: The ledger marks status with an emoji. Loose vocabulary, so this only asserts
#: the GROSS disagreements -- a row the markdown calls open while the JSON calls
#: it fixed, or the reverse. Without this the two files drift and the executable
#: half silently stops describing the narrative half, which is the same
#: two-sources-of-truth failure the whole ledger already has with reality.
_MD_OPEN = ("\U0001f534",)                      # red circle
_MD_DONE = ("✅", "\U0001f7e2")             # white check, green circle


def markdown_status(dq_id: str, text: str) -> str | None:
    """'open', 'done' or None (ambiguous) as the MARKDOWN row declares it."""
    m = re.search(rf"^\|\s*{re.escape(dq_id)}:.*$", text, re.M)
    if not m:
        return None
    row = m.group(0)
    # Only the status cell, which is the second-to-last pipe-delimited field.
    cells = [c.strip() for c in row.split("|")]
    cell = cells[-3] if len(cells) >= 3 else row
    if any(e in cell for e in _MD_OPEN):
        return "open"
    if any(e in cell for e in _MD_DONE):
        return "done"
    return None


def status_disagreements(checks: dict, ids: list[str]) -> list[str]:
    """Rows where dq_checks.json and the markdown ledger contradict each other."""
    text = _LEDGER.read_text(encoding="utf-8")
    out = []
    for dq in ids:
        declared = checks.get(dq, {}).get("declared")
        md = markdown_status(dq, text)
        if md is None or declared is None:
            continue
        if declared == "fixed" and md == "open":
            out.append(f"{dq}: dq_checks.json says FIXED, the ledger row still shows OPEN")
        elif declared == "open" and md == "done":
            out.append(f"{dq}: dq_checks.json says OPEN, the ledger row shows DONE")
    return out


def run_one(dq_id: str, spec: dict, verbose: bool = False) -> tuple[str, str]:
    """Return (verdict, detail). Verdict is one of OK / RED / NO-CHECK / ERROR."""
    cmd = spec.get("check")
    declared = spec.get("declared", "unknown")

    if not cmd:
        return "NO-CHECK", spec.get("why_no_check", "no reason recorded")

    try:
        proc = subprocess.run(
            cmd, cwd=_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=_TIMEOUT,
        )
    except FileNotFoundError:
        return "ERROR", f"cannot run {cmd[0]!r}"
    except subprocess.TimeoutExpired:
        return "ERROR", f"timed out after {_TIMEOUT}s"

    if verbose and proc.stdout:
        print(proc.stdout.rstrip())

    passed = proc.returncode == 0
    if declared not in _ENFORCED:
        return "OK", f"declared {declared!r} (not enforced); check {'passed' if passed else 'failed'}"

    expected_pass = _ENFORCED[declared] == 0
    if passed == expected_pass:
        return "OK", f"declared {declared!r} and the check agrees"

    if declared == "fixed":
        return "RED", (
            "declared FIXED but the check FAILS - a regression, or a fix that "
            "never held. " + (spec.get("red_when") or "")
        )
    return "RED", (
        "declared OPEN but the check PASSES - it appears to be fixed and the "
        "ledger never caught up. Verify, then set declared to 'fixed'."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--id", help="run a single DQ id")
    ap.add_argument("--coverage", action="store_true",
                    help="only check every ledger row is accounted for")
    ap.add_argument("--list", action="store_true",
                    help="show which rows have a check")
    args = ap.parse_args()

    checks = load_checks()
    ids = ledger_ids()

    # --- coverage: the ledger cannot grow rows nobody has to think about ---
    missing = [i for i in ids if i not in checks]
    orphan = [i for i in checks if i not in ids and not i.startswith("_")]

    if args.list:
        for dq in ids:
            spec = checks.get(dq, {})
            mark = "check" if spec.get("check") else "  -  "
            print(f"  {dq:<8} {spec.get('declared','?'):<15} {mark}")
        withc = sum(1 for s in checks.values() if s.get("check"))
        print(f"\n{withc} of {len(ids)} rows have an executable check.")
        return 0

    if missing or orphan:
        print("DQ-CHECK: FAILED - the ledger and the check file disagree.")
        for i in missing:
            print(f"  {i}: in DATA_QUALITY_TRACKER.md but absent from dq_checks.json")
            print("     Add an entry. Use check: null with a why_no_check if you "
                  "cannot write one yet.")
        for i in orphan:
            print(f"  {i}: in dq_checks.json but not in the ledger")
        return 1

    disagree = status_disagreements(checks, ids)
    if disagree:
        print("DQ-CHECK: FAILED - the ledger and the check file declare different statuses.")
        for line in disagree:
            print(f"  {line}")
        print("  Fix the row that is wrong. Two sources of truth is how DQ-54 sat")
        print("  'Open -- report-only' for hours after it was merged.")
        return 1

    if args.coverage:
        print(f"DQ-CHECK: coverage OK - all {len(ids)} ledger rows are accounted "
              "for and agree with the ledger's own statuses.")
        return 0

    targets = [args.id] if args.id else ids
    if args.id and args.id not in checks:
        print(f"DQ-CHECK: {args.id} is not in dq_checks.json")
        return 1

    reds, no_check, errors = [], [], []
    for dq in targets:
        verdict, detail = run_one(dq, checks[dq], verbose=bool(args.id))
        if verdict == "RED":
            reds.append((dq, detail))
            print(f"  RED       {dq}: {detail}")
        elif verdict == "NO-CHECK":
            no_check.append(dq)
        elif verdict == "ERROR":
            errors.append((dq, detail))
            print(f"  ERROR     {dq}: {detail}")
        elif args.id:
            print(f"  OK        {dq}: {detail}")

    total = len(targets)
    ran = total - len(no_check)
    print()
    print(f"DQ-CHECK: {ran} check(s) run across {total} row(s); "
          f"{len(reds)} red, {len(errors)} unrunnable, "
          f"{len(no_check)} with no check written.")

    if no_check and not args.id:
        print(f"  no check yet: {', '.join(no_check)}")
        print("  That is a recorded gap, not coverage. See why_no_check in "
              ".claude/dq_checks.json.")

    if reds or errors:
        print("\nDQ-CHECK: FAILED")
        return 1
    print("DQ-CHECK: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
