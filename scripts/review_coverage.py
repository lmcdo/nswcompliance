#!/usr/bin/env python3
"""Did a Sol review actually read every code commit on this branch?

prior-art-checked: reuse not viable. Sweeps 2026-10-27 against origin/main:
  (1) scripts/cross_review.py keeps an --adjudicated record of FINDINGS. It
      stores what was found, never whether a review ran, so an outage leaves
      no trace in it at all.
  (2) scripts/sol_review_base.sh picks the incremental base from the last
      PUSH (@{u}), not the last REVIEW. A push whose review was skipped still
      moves @{u}, so its commits are treated as already read.
  (3) scripts/check_pr_gates.py checks the CI run only; CI dropped the
      cross-review on purpose (.github/workflows/gates.yml step 7).
  (4) ~/.claude/plans + memory: feedback-say-when-cross-review-did-not-run,
      reference-cross-review-sol-vs-deepseek — the gap is recorded as a rule
      for people, not as a check.

WHY THIS EXISTS
---------------
On 2026-10-11 five PRs merged with no review: the pre-push review hit a 429,
printed a line, and `|| true` let the push through. From 2026-10-18 every
push with OpenAI out of credits was reviewed by DeepSeek instead, which found
0 real HIGH issues out of 3, against Sol's 7 out of 15 on the same diffs. Both
looked like a reviewed push.

WHAT IT DOES
------------
cross_review.py appends one row per run to a per-branch ledger:
    {base, head, requested, model, outcome}
The row is written by an exit handler and starts as "did-not-finish", so a
crash, a sys.exit, a too-large diff or a timeout all leave a row that does NOT
count. It becomes "reviewed" only once the model has answered.

At merge time, every non-merge commit on the branch that touches reviewable
code must be covered by a "reviewed" row whose model is Sol (an OpenAI id, not
an OpenRouter "vendor/model" id). Coverage is matched by `git patch-id`, so a
clean rebase keeps it and a changed commit loses it.

KNOWN LIMITS, stated:
  * Merge commits are not checked. A conflict resolution inside one is unread.
  * The ledger is local (under the git common dir). A merge from another clone
    has no ledger and is refused — fail closed, not open.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from qa_report_path import git_env

#: Same path filter as SOL_CHANGED in .githooks/pre-push — what the review reads.
#: tests/test_review_coverage.py runs both on the same paths, so they cannot drift.
#: Test files are matched by PATH SHAPE, not the substring "test": the old
#: filter skipped services/contest.py and src/attestation.ts (Sol, 2026-10-27).
#: .claude/hooks/*.py is code too: the merge gate itself lives there.
REVIEWABLE = re.compile(
    r"^((services|scripts|src|frontend-nextjs/(app|components|lib))/.*\.(py|ts|tsx)"
    r"|\.claude/hooks/[^/]+\.py)$")
NOT_REVIEWABLE = re.compile(
    r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]*$|_test\.py$|\.(spec|test)\.[jt]sx?$")

OUTCOME_REVIEWED = "reviewed"
OUTCOME_UNFINISHED = "did-not-finish"
OUTCOME_OVERRIDE = "override"
MIN_OVERRIDE_CHARS = 15


def _git(repo: Path, *args: str, stdin: str | None = None) -> str:
    out = subprocess.run(
        ["git", *args], cwd=repo, input=stdin, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=60, env=git_env(),
    )
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()[:300]}")
    return out.stdout


def branch_slug(ref: str) -> str:
    """The per-branch state name .githooks/pre-push uses (SOL_BRANCH)."""
    return f"{ref.replace('/', '-')}-{hashlib.sha1(ref.encode()).hexdigest()[:10]}"


def log_path(repo: Path, ref: str) -> Path:
    common = Path(_git(repo, "rev-parse", "--git-common-dir").strip())
    if not common.is_absolute():
        common = repo / common
    return common / "sol-review" / f"{branch_slug(ref)}.reviews.jsonl"


def is_sol(model: object) -> bool:
    """An OpenAI model id. OpenRouter ids carry a vendor prefix: "deepseek/..."."""
    return isinstance(model, str) and bool(model.strip()) and "/" not in model


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **row}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # a torn line is not evidence of a review
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _patch_ids(repo: Path, base: str, head: str) -> dict[str, str]:
    """{commit: patch-id} for the non-merge commits in base..head."""
    patches = _git(repo, "log", "--no-merges", "-p", "--format=commit %H", f"{base}..{head}")
    if not patches.strip():
        return {}
    out = _git(repo, "patch-id", "--stable", stdin=patches)
    ids = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            ids[parts[1]] = parts[0]
    return ids


def reviewable_commits(repo: Path, base: str, head: str) -> list[str]:
    """Non-merge commits in base..head that touch code the review reads."""
    log = _git(repo, "log", "--no-merges", "--name-only", "--format=@@%H", f"{base}..{head}")
    hits, current = [], None
    for line in log.splitlines():
        if line.startswith("@@"):
            current = line[2:].strip()
        elif current and REVIEWABLE.match(line) and not NOT_REVIEWABLE.search(line):
            if current not in hits:
                hits.append(current)
    return hits


def uncovered(repo: Path, base: str, head: str, rows: list[dict]) -> list[str]:
    """Reviewable commits in base..head that no completed Sol review read."""
    needed = reviewable_commits(repo, base, head)
    if not needed:
        return []
    covered: set[str] = set()
    for row in rows:
        if row.get("outcome") != OUTCOME_REVIEWED or not is_sol(row.get("model")):
            continue
        try:
            covered.update(_patch_ids(repo, str(row["base"]), str(row["head"])).values())
        except (KeyError, RuntimeError):
            continue  # objects gone (gc'd, other clone): that row proves nothing here
    ids = _patch_ids(repo, base, head)
    return [c for c in needed if ids.get(c) not in covered]


def has_override(rows: list[dict], head: str) -> str | None:
    """A recorded override for exactly this head commit, or None."""
    for row in reversed(rows):
        if row.get("outcome") == OUTCOME_OVERRIDE and row.get("head") == head:
            return str(row.get("reason") or "")
    return None
