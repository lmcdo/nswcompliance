#!/usr/bin/env python3
"""Refuse to merge a pull request that nothing has checked.

prior-art-checked: reuse not viable because nothing checks a PR's CI state
before merge. Four sweeps, 2026-08-10 against 8ff73b52:
  (1) `git ls-files scripts/ | grep -iE "pr_|merge|gate|ci"` -> pr_overlap_guard.py
      (warns that your files overlap an OPEN PR — an authorship aid, reads no CI
      state) and qa_gate.py (validates the QA report JSON, never touches GitHub).
  (2) `.githooks/pre-push` runs the local suite BEFORE a PR exists, so it cannot
      know whether the PR's own run happened. Different moment, different fact.
  (3) `.github/workflows/main-red-alarm.yml` asserts main's HEAD has a successful
      run — but AFTER the merge. It is the safety net, not the gate.
  (4) Branch protection is the real answer and is unavailable: the API returns
      403 "Upgrade to GitHub Pro or make this repository public".

WHY THIS EXISTS
---------------
A pull request whose mergeable state is CONFLICTING gets NO GitHub Actions run
at all. `pull_request` workflows execute against the MERGE commit, and when the
branch conflicts that commit cannot be built, so no run is ever created. Not
failed — never started. The PR page shows an empty check list, which is
indistinguishable from "the checks have not finished yet".

Measured, not assumed (2026-08-10):
  * PR #907 sat CONFLICTING for 40+ minutes with zero runs. Rebasing cleared the
    conflict; a run appeared 20 seconds later and all five jobs passed.
  * PR #902 had the same shape. Its run appeared minutes after its rebase, and
    was created 10 seconds AFTER it had already been merged. It passed, which
    was luck rather than judgement.

WHAT IT DOES AND DOES NOT PROMISE
---------------------------------
It answers one question: has the `gates` workflow run against THIS PR's current
head commit, and did it pass? Anything else is a refusal.

It cannot prevent a merge — only branch protection can, and that needs a paid
plan. What it can do is make the unchecked state loud at the moment it matters,
instead of leaving an empty list that reads as "not yet".

Three states, deliberately distinct, because "no run" and "a failed run" are
different problems with different fixes:
  READY       a gates run exists for the head sha and concluded success
  NOT-RUN     no gates run exists for the head sha (usually: the PR conflicts)
  FAILED      a run exists and did not succeed

    python scripts/check_pr_gates.py 907        # exit 0 only if READY
    python scripts/check_pr_gates.py 907 --wait # poll while a run is in flight
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

POLL_SECONDS = 20
DEFAULT_WAIT_MINUTES = 10


def gh(*args: str) -> str:
    """Run gh and return stdout. Raises on failure so a broken auth is loud."""
    out = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {out.stderr.strip()[:300]}")
    return out.stdout.strip()


def pr_facts(pr: int) -> tuple[str, str, str]:
    """Return (head_sha, mergeable, state) for the PR."""
    data = json.loads(
        gh("pr", "view", str(pr), "--json", "headRefOid,mergeable,state,headRefName")
    )
    return data["headRefOid"], data.get("mergeable", "UNKNOWN"), data["state"]


def gates_run_for(sha: str) -> dict | None:
    """The newest gates run whose head commit is exactly this sha, or None."""
    runs = json.loads(
        gh(
            "api",
            "repos/{owner}/{repo}/actions/runs?per_page=50",
            "--jq",
            "[.workflow_runs[] | {name, head_sha, status, conclusion, html_url}]",
        )
    )
    for r in runs:
        if r["head_sha"] == sha and r["name"] == "gates":
            return r
    return None


def assess(pr: int) -> tuple[str, str]:
    """Return (verdict, message). Verdict is READY, NOT-RUN, FAILED or PENDING."""
    sha, mergeable, state = pr_facts(pr)
    short = sha[:8]

    if state != "OPEN":
        return "NOT-RUN", f"PR #{pr} is {state}, not open."

    run = gates_run_for(sha)

    if run is None:
        if mergeable == "CONFLICTING":
            return "NOT-RUN", (
                f"No gates run exists for `{short}`, and the PR is CONFLICTING.\n"
                "  That is the cause, not a coincidence: pull_request workflows run against\n"
                "  the merge commit, and a conflicting branch has none to run against.\n"
                "  Fix: git fetch origin && git rebase origin/main, resolve, force-push.\n"
                "  The run appears within about 20 seconds of the conflict clearing."
            )
        return "NOT-RUN", (
            f"No gates run exists for `{short}` (PR is {mergeable}).\n"
            "  Nothing has checked this commit. Do not merge on the assumption it is fine."
        )

    if run["status"] != "completed":
        return "PENDING", f"gates is {run['status']} for `{short}` — {run['html_url']}"

    if run["conclusion"] != "success":
        return "FAILED", (
            f"gates concluded **{run['conclusion']}** for `{short}`.\n  {run['html_url']}"
        )

    return "READY", f"gates passed for `{short}` — {run['html_url']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int, help="pull request number")
    ap.add_argument(
        "--wait",
        action="store_true",
        help="poll while a run is in flight rather than reporting PENDING",
    )
    ap.add_argument("--wait-minutes", type=int, default=DEFAULT_WAIT_MINUTES)
    args = ap.parse_args()

    deadline = time.time() + args.wait_minutes * 60
    while True:
        try:
            verdict, message = assess(args.pr)
        except RuntimeError as exc:
            # An unreachable API is not a pass. Refuse rather than assume.
            print(f"UNKNOWN  {exc}", file=sys.stderr)
            print("Refusing: could not establish the PR's check state.", file=sys.stderr)
            return 2

        if verdict == "PENDING" and args.wait and time.time() < deadline:
            print(f"  {message} — waiting…", flush=True)
            time.sleep(POLL_SECONDS)
            continue
        break

    print(f"{verdict}  {message}")

    if verdict == "READY":
        return 0
    print(
        "\nNot safe to merge. A missing run is not a passing run — an empty check\n"
        "list looks exactly like 'not finished yet', which is why this exists.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
