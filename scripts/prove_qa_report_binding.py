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
from qa_report_path import git_env  # noqa: E402  (DQ-54)

REPO = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO),
        env=git_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _is_ancestor(rev: str, ref: str) -> bool | None:
    """True/False, or None when git could not answer (0=yes, 1=no, else error)."""
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", rev, ref],
        cwd=str(REPO), env=git_env(), capture_output=True, timeout=30,
    )
    return {0: True, 1: False}.get(proc.returncode)


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
            cwd=str(REPO), env=git_env(), capture_output=True, timeout=30,
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
    detail = lines[-1].strip() if lines else proc.stdout.strip()[-160:]
    # The gate prints em-dashes. Captured with errors="replace" they arrive as
    # U+FFFD, which a cp1252 console cannot print — and a proof harness that
    # dies while REPORTING its result is indistinguishable from one that failed.
    return proc.returncode, detail.encode("ascii", "replace").decode("ascii")


def main() -> int:
    # A cp1252 console is the default on Windows and this harness must be able
    # to print its own verdict on the machine it runs on.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    report = resolve(REPO)
    if report is None:
        print("No QA report resolved for this branch — nothing to prove.")
        return 2

    # `or ""` not a .get default: a report carrying "commit_hash": null would
    # otherwise yield None and build the anchor '"commit_hash": "None"', which
    # matches nothing, and the plant would fail rather than the check.
    current = json.loads(report.read_text(encoding="utf-8")).get("commit_hash") or ""
    if not current:
        print("Report has no commit_hash — nothing to prove.")
        return 2

    anchor = f'"commit_hash": "{current}"'
    sibling = _a_sibling_branch_commit()
    on_main = _git("rev-parse", "--short", "origin/main")
    full_sha = _git("rev-parse", "HEAD")

    # Preconditions. Without these the harness can report CAUGHT for the wrong
    # reason and call it proof — which it did on 2026-08-10, when a corrupted
    # local origin/main ref made `sibling` and `on_main` the SAME commit and the
    # inherited-from-main case was silently re-testing not-an-ancestor.
    if sibling == on_main:
        raise SystemExit(
            f"sibling tip and origin/main are the same commit ({sibling}). The "
            f"two red cases would test one condition twice. Run `git fetch "
            f"origin` and check refs/remotes/origin/main is not stale."
        )
    if _is_ancestor(on_main, "origin/main") is not True:
        raise SystemExit(
            f"{on_main} is not an ancestor of origin/main, so the "
            f"inherited-from-main case would not exercise that branch of the "
            f"check. Local origin/main is probably wrong."
        )
    if _is_ancestor(sibling, "HEAD") is not False:
        raise SystemExit(
            f"{sibling} IS an ancestor of HEAD, so the copied-from-another-branch "
            f"case would not exercise that branch of the check."
        )

    print(f"report      : {report.relative_to(REPO).as_posix()}")
    print(f"stamped     : {current}")
    print(f"sibling tip : {sibling}   (must be rejected)")
    print(f"origin/main : {on_main}   (must be rejected)")
    print(f"full sha    : {full_sha[:12]}..  (must be accepted)\n")

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

    # "It went red" is not the claim. "It went red FOR THIS REASON" is. A red
    # that fires on a different branch of the check would look identical in the
    # table above and would prove nothing about the branch it names.
    expected_reason = {
        "copied-from-another-branch": "not an ancestor of HEAD",
        "inherited-from-main": "already on origin/main",
        "names-no-commit": "names no commit",
    }
    wrong_reason = [
        f"{o.label}: expected {expected_reason[o.label]!r}, got {o.detail!r}"
        for o in result.outcomes
        if o.label in expected_reason and expected_reason[o.label] not in o.detail
    ]

    if result.ok and not wrong_reason:
        print("PROVEN: every planted defect was caught for the reason it was planted,")
        print("the legitimate report passed, and the file is byte-identical to where")
        print("it started.")
        return 0
    for line in wrong_reason:
        print(f"WRONG REASON — {line}")
    print("NOT PROVEN — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
