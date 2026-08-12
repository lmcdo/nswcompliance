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

    # Optional "requires": a path that must exist for this check to mean
    # anything. Without it, a check whose ENVIRONMENT is missing exits non-zero
    # and gets read as "the defect is present" -- CI's python job has no
    # frontend-nextjs/node_modules, so DQ-32's jest guard reported RED on a fix
    # that was in fact working, and would have blocked the merge that shipped
    # it. That is the same collapse that turned main red on 2026-08-12 (#939):
    # could-not-look is not the same as found-something.
    need = spec.get("requires")
    if need and not (_ROOT / need).exists():
        return "UNKNOWN", (
            f"{need} is absent, so this check could not run here and the row is "
            f"UNVERIFIED rather than failing. It is not evidence either way."
        )

    try:
        # Optional "cwd" on a check spec, relative to the repo root. Some
        # defects live in a subproject and their check will not run from here:
        # jest resolves its babel config from the working directory, so
        # --rootDir frontend-nextjs parses but then fails on every file. The
        # obvious workaround, `npm --prefix`, is worse -- subprocess without a
        # shell cannot resolve `npm` on Windows, where this repo's runners are,
        # so the check reports UNRUNNABLE rather than passing or failing.
        proc = subprocess.run(
            cmd, cwd=_ROOT / spec["cwd"] if spec.get("cwd") else _ROOT,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=_TIMEOUT,
        )
    except FileNotFoundError:
        return "ERROR", f"cannot run {cmd[0]!r}"
    except subprocess.TimeoutExpired:
        return "ERROR", f"timed out after {_TIMEOUT}s"

    if verbose and proc.stdout:
        print(proc.stdout.rstrip())

    # Exit 2 means the probe could not look -- dq_probe_live.py returns it when
    # the database is unreachable. That is UNKNOWN, and UNKNOWN is neither a
    # pass nor a fail. Folding it into `passed = returncode == 0` reported
    # "declared FIXED but the check FAILS" for probes that never ran, which put
    # a false regression alarm on main: CI has no DATABASE_URL, so every
    # DB-backed row went red the moment one was declared fixed.
    #
    # It does NOT fail the run. A gate that is permanently red wherever the
    # database is absent gets switched off, and then nothing is checked at all.
    # It is reported loudly instead, and counted separately from "no check
    # written" so an unreachable database can never be mistaken for coverage.
    if proc.returncode == 2:
        return "UNKNOWN", (
            "the probe could not reach its source, so this row is UNVERIFIED "
            "rather than clean. " + (proc.stdout or "").strip().splitlines()[-1]
            if (proc.stdout or "").strip() else
            "the probe could not reach its source, so this row is UNVERIFIED "
            "rather than clean."
        )

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


#: Rows whose declared state means "still costing something".
_UNRESOLVED = {"open", "partial", "backlog"}


def _report() -> int:
    """The status of every defect, GENERATED rather than typed.

    This exists because the prose summaries around this ledger kept being
    wrong in ways the ledger itself was not: a status is only as good as the
    last person who retyped it. Everything below is produced by running the
    checks, and every number a probe prints carries the query behind it, so a
    reader can re-run any figure instead of trusting it. If this report is
    wrong, the command that produced it is wrong, and that is fixable.
    """
    checks = load_checks()
    ids = ledger_ids()

    unresolved = [i for i in ids if checks.get(i, {}).get("declared") in _UNRESOLVED]
    resolved = len(ids) - len(unresolved)

    print("=" * 72)
    print("DEFECT STATUS - generated by scripts/dq_check.py --report")
    print("=" * 72)
    print(f"{len(ids)} rows in the ledger: {resolved} resolved, "
          f"{len(unresolved)} unresolved.")
    print()
    print("UNRESOLVED, with what a check can currently say about each:")
    print()

    verified = unverified = 0
    for dq in unresolved:
        spec = checks[dq]
        declared = spec.get("declared")
        if not spec.get("check"):
            unverified += 1
            print(f"  {dq}  [{declared}]  NOT VERIFIED")
            print(f"      {spec.get('why_no_check', 'no reason recorded')}")
            print()
            continue

        verified += 1
        verdict, _ = run_one(dq, spec)
        print(f"  {dq}  [{declared}]  checked -> {verdict}")
        try:
            proc = subprocess.run(
                spec["check"], cwd=_ROOT, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=_TIMEOUT,
            )
            for line in (proc.stdout or "").splitlines():
                if line.strip():
                    print(f"      {line}")
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"      could not re-run for detail: {exc}")
        print()

    print("-" * 72)
    print(f"Of {len(unresolved)} unresolved defects: {verified} have a check that "
          f"was just run, {unverified} have NONE.")
    if unverified:
        print("An unverified row is not a clean row. It means nobody has written")
        print("something that could tell you, and the count above is the honest gap.")
    print("-" * 72)
    return 0


# Scripts that are deliberately not invoked by CI or a hook. Each needs a
# reason, and the reason has to be a mechanism, not an intention.
_UNWIRED_OK = {
    "check_pr_gates.py": "run by hand immediately before `gh pr merge`; wiring it "
                         "into CI is circular - it asks whether CI passed.",
    "check_served_output.py": "needs a running dev server AND currently fails on the "
                              "live #928 defect. Wire it in the PR that closes #928.",
    "dq_db.py": "library, not a check: connection helper imported by the probes.",
    "dq_probe_live.py": "invoked through .claude/dq_checks.json by this file.",
    "check_registry.py": "loads .env from beside itself, so it cannot find credentials "
                         "from a worktree, and CI has no DATABASE_URL either. Port it to "
                         "dq_db.connect() the way verify_coverage_stats.py was, then wire.",
    "verify_controls_monitoring.py": "same defect: builds its own connection and falls "
                                     "back to localhost:5432. Port to dq_db.connect() "
                                     "before wiring, or it fails on 'role does not exist'.",
    "verify_extraction_fidelity.py": "needs the council source PDFs on disk; it proves a "
                                     "provision is grounded in its own PDF. Belongs to the "
                                     "extraction run, not to every pull request.",
    "verify_inserted_provisions.py": "one-shot tool for a specific SEPP Housing insert "
                                     "that has already happened. Kept for the record.",
    "verify_precinct_boundaries.py": "operational: its own docstring says run it before "
                                     "and after an import. There is no import in CI.",
}


def unwired_checks() -> list[str]:
    """Scripts that look like checks but nothing runs.

    The recurring failure this exists to stop: a check gets written, reviewed
    and merged, and is then invoked by nothing. It happened to campaign items
    2-5 (#874/#876, orphaned for nine days), and the same shape produced #927
    (a QA gate reading a file git would never carry) and #931 (a defect ledger
    that was prose). Three instances, one cause: an artifact that describes
    reality but is not executed decays silently.

    This lives INSIDE dq_check.py on purpose. A separate check_the_checks.py
    would need its own wiring and start the regress the fix is meant to end.
    dq_check.py already runs in gates.yml, and this scan INCLUDES ITSELF: drop
    it from CI and either it still runs and fails, or gates.yml changed, which
    is visible in the diff. Above that, main-red-alarm.yml fires from outside
    the repo when main's HEAD has no successful run. Three levels, then it
    stops.
    """
    root = Path(__file__).resolve().parent.parent
    scripts = root / "scripts"
    if not scripts.is_dir():
        return []

    # Every place a check can legitimately be invoked from. The earlier
    # hand-sweep read gates.yml and pre-push only, missed .githooks/pre-commit,
    # and so reported lint_bracket_access.py and lint_brief_failsoft.py as
    # orphaned when both run on every commit. Read the whole surface.
    haystack = []
    for d, pat in ((root / ".github" / "workflows", "*.yml"),
                   (root / ".githooks", "*"),
                   (root / ".claude", "dq_checks.json")):
        if d.is_dir():
            for f in sorted(d.glob(pat)):
                if f.is_file():
                    haystack.append(f.read_text(encoding="utf-8", errors="replace"))
    # A check invoked by another check is wired, transitively.
    for f in sorted(scripts.glob("*.py")):
        haystack.append(f.read_text(encoding="utf-8", errors="replace"))
    blob = "\n".join(haystack)

    out = []
    for f in sorted(scripts.glob("*.py")):
        n = f.name
        if not n.startswith(("check_", "lint_", "verify_", "dq_")):
            continue
        if n in _UNWIRED_OK:
            continue
        # Its own file is in the blob, so require a mention from somewhere else.
        others = blob.replace(f.read_text(encoding="utf-8", errors="replace"), "")
        # Match the stem as well as the filename: gates.yml invokes several of
        # these from a shell loop that appends the extension ("scripts/$s.py"),
        # so the literal "foo.py" never appears even though foo IS wired.
        if n not in others and f.stem not in others:
            out.append(n)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--id", help="run a single DQ id")
    ap.add_argument("--coverage", action="store_true",
                    help="only check every ledger row is accounted for")
    ap.add_argument("--list", action="store_true",
                    help="show which rows have a check")
    ap.add_argument("--report", action="store_true",
                    help="print the defect status report, generated not typed")
    args = ap.parse_args()

    if args.report:
        return _report()

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

    # --- a check nothing invokes is not a check ---
    stranded = unwired_checks()
    if stranded:
        print("DQ-CHECK: FAILED - checks exist that nothing runs.")
        for n in stranded:
            print(f"  scripts/{n}: not referenced by any workflow, hook, "
                  f"dq_checks.json entry, or other script")
        print("  Wire it into .github/workflows/gates.yml or .githooks/, or add it")
        print("  to _UNWIRED_OK in this file with a reason that is a MECHANISM.")
        print("  Origin: campaign items 2-5 shipped in #874/#876 and were invoked by")
        print("  nothing for nine days, so they could never earn blocking status.")
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

    reds, no_check, errors, unknown = [], [], [], []
    for dq in targets:
        verdict, detail = run_one(dq, checks[dq], verbose=bool(args.id))
        if verdict == "UNKNOWN":
            unknown.append(dq)
            print(f"  UNKNOWN   {dq}: {detail}")
        elif verdict == "RED":
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
          f"{len(reds)} red, {len(unknown)} unverifiable here, "
          f"{len(errors)} unrunnable, {len(no_check)} with no check written.")
    if unknown:
        print(f"  could not be verified in THIS environment: {', '.join(unknown)}")
        print("  Not clean, not failing — the probe could not reach its source "
              "(no DATABASE_URL in CI). Run locally to verify these.")

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
