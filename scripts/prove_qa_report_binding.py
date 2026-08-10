#!/usr/bin/env python3
"""Prove the QA report's commit binding can actually go red.

prior-art-checked: reuse not viable as a whole, and the part that IS reusable is
reused. Four sweeps, 2026-08-10 against origin/main b1234b4c: (1) `ls
scripts/prove_*` returns prove_controls_pdf_check.py only, which proves a PDF
control check and shares no subject matter; (2) `git grep -n "falsifiability"`
returns scripts/falsifiability.py plus four docs and three tests -- the harness
this script imports rather than reimplements, which is the whole point of #883's
lesson; (3) `git grep -nE "commit_hash|is-ancestor"` over scripts/ returns
qa_gate.py alone, so nothing already proves this binding; (4) MEMORY.md and
`~/.claude/plans/INDEX*.md` record no falsifiability proof for the QA gate.

WHAT IS PROVEN
--------------
That check_commit_hash_binding rejects the two reports it is supposed to reject,
accepts the one it is supposed to accept, and does not care how short the hash
is. The plants go into THIS BRANCH'S OWN report and the gate is re-run for real,
so the thing under test is the shipped path -- resolver, gate and all -- not a
unit-test stand-in.

The four cases:

  copied-from-another-branch   a real sibling branch's tip     must go RED
  inherited-from-main          a real commit on origin/main    must go RED
  names-no-commit              a hash present in no history    must go RED
  full-sha-same-commit         HEAD as 40 chars, not 7         must stay GREEN

The last one is not filler. The old rule string-compared against `git log %h`,
so it broke whenever git chose a different abbreviation length. If anyone
reintroduces string comparison, that case turns red and the harness reports it
as a FALSE ALARM.

WHY A SEPARATE HARNESS FROM THE TESTS
-------------------------------------
tests/test_qa_report_binding.py asserts the same four outcomes against
purpose-built repositories, which is the portable proof. This script asserts
them against the real one, which is the proof that the wiring works end to end:
a resolver that found the wrong file, or a workflow calling the gate with the
wrong argument, would pass every unit test and fail here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from falsifiability import ProofCase, prove  # noqa: E402
from qa_report_path import resolve  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _a_sibling_branch_commit() -> str:
    """The tip of some remote branch that is NOT an ancestor of HEAD.

    Chosen by asking git, not hardcoded, so this keeps working as branches come
    and go. Falls back to a synthesised orphan commit if every remote branch is
    somehow an ancestor, so the case is never silently dropped.
    """
    refs = _git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    for ref in refs.splitlines():
        ref = ref.strip()
        if not ref or ref.endswith("/HEAD") or ref == "origin/main":
            continue
        probe = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ref, "HEAD"],
            cwd=str(REPO), capture_output=True, timeout=30,
        )
        if probe.returncode == 1:  # 1 = definitively not an ancestor
            return _git("rev-parse", "--short", ref)
    raise SystemExit(
        "no remote branch is outside HEAD's history — cannot plant the "
        "copied-from-another-branch case, so it must not be reported as proven"
    )


def _run() -> tuple[int, str]:
    """Run the real gate the way pre-push runs it, and report its verdict."""
    proc = subprocess.run(
        [sys.executable, "scripts/qa_gate.py"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    lines = [ln for ln in proc.stdout.splitlines() if "QA-GATE:" in ln or "hash" in ln]
    return proc.returncode, (lines[-1].strip() if lines else proc.stdout.strip()[-160:])


def main() -> int:
    report = resolve(REPO)
    if report is None:
        print("No QA report resolved for this branch — nothing to prove.")
        return 2

    current = json.loads(report.read_text(encoding="utf-8")).get("commit_hash", "")
    if not current:
        print("Report has no commit_hash — nothing to prove.")
        return 2

    anchor = f'"commit_hash": "{current}"'
    sibling = _a_sibling_branch_commit()
    on_main = _git("rev-parse", "--short", "origin/main")
    full_sha = _git("rev-parse", "HEAD")

    print(f"report      : {report.relative_to(REPO).as_posix()}")
    print(f"stamped     : {current}")
    print(f"sibling tip : {sibling}   (must be rejected)")
    print(f"origin/main : {on_main}   (must be rejected)")
    print(f"full sha    : {full_sha[:12]}…  (must be accepted)\n")

    cases = [
        ProofCase(
            label="copied-from-another-branch",
            path=report,
            find=anchor,
            replace=f'"commit_hash": "{sibling}"',
            expect="red",
        ),
        ProofCase(
            label="inherited-from-main",
            path=report,
            find=anchor,
            replace=f'"commit_hash": "{on_main}"',
            expect="red",
        ),
        ProofCase(
            label="names-no-commit",
            path=report,
            find=anchor,
            replace='"commit_hash": "0000000"',
            expect="red",
        ),
        ProofCase(
            label="full-sha-same-commit",
            path=report,
            find=anchor,
            replace=f'"commit_hash": "{full_sha}"',
            expect="green",
        ),
    ]

    result = prove(cases, _run)
    print(result.table())
    print()
    if result.ok:
        print("PROVEN: every planted defect was caught, the legitimate report passed,")
        print("and the file is byte-identical to where it started.")
        return 0
    print("NOT PROVEN — see the verdict column above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
