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
  NOT-REVIEWED  CI passed, but a code commit on the branch was never read by a
              finished Sol review (2026-10-27; see scripts/review_coverage.py).
              An outage, a 429 or a DeepSeek fallback counts as not reviewed.

    python scripts/check_pr_gates.py 907        # exit 0 only if READY
    python scripts/check_pr_gates.py 907 --wait # poll while a run is in flight
    python scripts/check_pr_gates.py 907 --review-override "why no review is acceptable"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # for the sibling module
import review_coverage

REPO = Path(__file__).resolve().parents[1]

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
    data = pr_view(pr)
    return data["headRefOid"], data.get("mergeable", "UNKNOWN"), data["state"]


def pr_view(pr: int) -> dict:
    return json.loads(
        gh("pr", "view", str(pr), "--json", "headRefOid,mergeable,state,headRefName,baseRefName")
    )


def review_gap(pr: int, override: str | None) -> tuple[str, str]:
    """(verdict, message): READY, or NOT-REVIEWED with the commits nobody read.

    Raises RuntimeError when the facts cannot be established, which main()
    reports as a refusal: an unreadable ledger is not a reviewed branch.
    """
    data = pr_view(pr)
    head, ref = data["headRefOid"], data["headRefName"]
    base_ref = f"origin/{data.get('baseRefName') or 'main'}"
    review_coverage._git(REPO, "fetch", "-q", "origin", ref, data.get("baseRefName") or "main")
    base = review_coverage._git(REPO, "merge-base", base_ref, head).strip()
    log = review_coverage.log_path(REPO, ref)
    rows = review_coverage.read_rows(log)

    gap = review_coverage.uncovered(REPO, base, head, rows)
    if not gap:
        return "READY", "every code commit was read by a finished Sol review"

    recorded = review_coverage.has_override(rows, head)
    if override is not None:
        if len(override.strip()) < review_coverage.MIN_OVERRIDE_CHARS:
            return "NOT-REVIEWED", (
                f"--review-override needs a reason of at least "
                f"{review_coverage.MIN_OVERRIDE_CHARS} characters; it is the only record "
                "of why unreviewed code was merged."
            )
        review_coverage.append_row(log, {
            "base": base, "head": head, "outcome": review_coverage.OUTCOME_OVERRIDE,
            "reason": override.strip(), "uncovered": gap,
        })
        recorded = override.strip()
    if recorded:
        return "READY", (
            f"{len(gap)} code commit(s) unreviewed, merged on a recorded override: {recorded}"
        )

    listing = "\n".join(f"    {c[:8]}" for c in gap[:10])
    more = f"\n    ... and {len(gap) - 10} more" if len(gap) > 10 else ""
    return "NOT-REVIEWED", (
        f"{len(gap)} code commit(s) on {ref} were never read by a finished Sol review:\n"
        f"{listing}{more}\n"
        "  A 429, a timeout, a too-large diff, SOL_REVIEW=0, --no-verify or a DeepSeek\n"
        "  fallback all leave a commit here. The next push will NOT re-read them: its\n"
        "  base is the last push, not the last review. Review them now:\n"
        f"    git checkout {ref} && python scripts/cross_review.py --base {base[:12]} \\n"
        f"      --max-diff-kb 512 --review-log \"{log}\"\n"
        "  Or merge anyway, on the record:\n"
        f"    python scripts/check_pr_gates.py {pr} --review-override \"<why>\""
    )


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
    ap.add_argument(
        "--review-override",
        metavar="REASON",
        help="merge although a code commit was never Sol-reviewed; the reason is recorded",
    )
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

    if verdict == "READY":
        print(f"{verdict}  {message}")
        try:
            verdict, message = review_gap(args.pr, args.review_override)
        except (RuntimeError, OSError, KeyError) as exc:
            print(f"UNKNOWN  {exc}", file=sys.stderr)
            print("Refusing: could not establish whether the branch was reviewed.", file=sys.stderr)
            return 2

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
