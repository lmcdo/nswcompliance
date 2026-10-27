#!/usr/bin/env python3
"""PreToolUse hook — no PR merge unless scripts/check_pr_gates.py says READY.

prior-art-checked: no existing hook guards a merge. Sweep 2026-10-27:
`grep -il "pr merge" .claude/hooks/*` and `.claude/settings.json` -> nothing.
check_pr_gates.py exists but is a rule someone has to remember to run.

WHY THIS EXISTS
---------------
PR #902 was merged 10 seconds BEFORE its CI run was created (2026-08-10).
Five PRs merged with no review on 2026-10-11. CLAUDE.md says to run
check_pr_gates.py first; both happened anyway, because a rule is not a gate.
Branch protection would be the real gate and needs a paid plan (API 403).

WHAT IT DOES
------------
Finds every merge in a Bash or PowerShell command — `gh pr merge` in any
argument order, by number, URL or branch, with or without --auto, and the REST
merge endpoint via `gh api` or curl — and runs check_pr_gates.py for each.
Anything but exit 0 blocks the command, with the gate's own message.

Fails CLOSED: a merge whose PR cannot be resolved, or a gate that cannot run,
is blocked. The escape is explicit and leaves a record:
    MERGE_GATE_OVERRIDE="<reason, 15+ chars>" gh pr merge 123 --squash

Input: Claude Code sends the hook payload as JSON on stdin. TOOL_INPUT is read
only as a fallback; several older hooks here read ONLY that variable.

Exit codes: 0 = allow, 2 = block (message on stderr)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MIN_OVERRIDE_CHARS = 15
REPO = Path(__file__).resolve().parents[2]
OVERRIDE_LOG = REPO / ".claude" / ".merge-gate-overrides.jsonl"

# `gh [global flags] pr merge ...` up to the next shell separator.
_GH_MERGE = re.compile(r"\bgh(?:\.exe)?\b(?P<pre>[^;&|\n]*?)\bpr\s+merge\b(?P<args>[^;&|\n]*)", re.I)
# REST merge endpoint: PUT /repos/o/r/pulls/N/merge, via gh api or curl.
_API_MERGE = re.compile(r"pulls/(?P<num>\d+)/merge\b", re.I)
_PR_URL = re.compile(r"/pull/(?P<num>\d+)\b")
_OVERRIDE = re.compile(r"MERGE_GATE_OVERRIDE=(?:\"([^\"]*)\"|'([^']*)'|(\S+))")
# gh pr merge flags that take a value: their value is not the PR selector.
# Text that is DATA, not a command: commit messages, PR bodies, heredoc bodies.
# Without this, `git commit -m "run gh pr merge 902 next"` would be gated.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?^\s*\2\s*$", re.S | re.M)
_MESSAGE_ARG = re.compile(
    r"(?:-m|--message|-b|--body|-t|--title|--subject)(?:\s+|=)(\"[^\"]*\"|'[^']*')")
_VALUE_FLAGS = {"-b", "--body", "-F", "--body-file", "-t", "--subject", "-A",
                "--author-email", "--match-head-commit", "-R", "--repo"}


def find_merges(command: str) -> list[str | None]:
    """Every PR a command would merge. None = the current branch's PR."""
    command = _MESSAGE_ARG.sub(" ", _HEREDOC.sub(" ", command))
    targets: list[str | None] = []
    for m in _GH_MERGE.finditer(command):
        targets.append(_selector(m.group("args")))
    for m in _API_MERGE.finditer(command):
        targets.append(m.group("num"))
    return targets


def _selector(args: str) -> str | None:
    tokens = args.split()
    skip = False
    for tok in tokens:
        if skip:
            skip = False
            continue
        if tok.startswith("-"):
            if "=" not in tok and tok in _VALUE_FLAGS:
                skip = True
            continue
        tok = tok.strip("\"'")
        url = _PR_URL.search(tok)
        if url:
            return url.group("num")
        return tok.lstrip("#")
    return None


def override_reason(command: str) -> str | None:
    m = _OVERRIDE.search(command)
    if not m:
        return None
    return next((g for g in m.groups() if g is not None), "")


def resolve_number(selector: str | None, cwd: str) -> int | None:
    if selector and selector.isdigit():
        return int(selector)
    args = ["gh", "pr", "view", "--json", "number"]
    if selector:
        args.insert(3, selector)
    try:
        out = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=30)
        return int(json.loads(out.stdout)["number"]) if out.returncode == 0 else None
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return None


def run_gate(pr: int, root: str) -> tuple[int, str]:
    gate = os.path.join(root, "scripts", "check_pr_gates.py")
    if not os.path.exists(gate):
        return 2, f"gate script missing: {gate}"
    try:
        out = subprocess.run([sys.executable, gate, str(pr)], capture_output=True,
                             text=True, cwd=root, timeout=180)
        return out.returncode, (out.stdout + out.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 2, f"gate could not run: {exc}"


def _payload() -> dict:
    raw = ""
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
    except OSError:
        raw = ""
    raw = raw.strip() or os.environ.get("TOOL_INPUT", "")
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _record_override(command: str, reason: str) -> None:
    try:
        with OVERRIDE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "reason": reason, "command": command[:300]}) + "\n")
    except OSError:
        pass


def main() -> int:
    data = _payload()
    tool_input = data.get("tool_input") or data.get("toolInput") or data
    command = (tool_input.get("command") if isinstance(tool_input, dict) else "") or ""
    targets = find_merges(command)
    if not targets:
        return 0

    # The repo this hook lives in, not the payload's cwd: a cwd in MSYS form
    # (/c/Users/...) is not a path Windows Python can open, and the gate then
    # "fails closed" for the wrong reason (measured 2026-10-27).
    root = str(REPO)

    reason = override_reason(command)
    if reason is not None:
        if len(reason.strip()) >= MIN_OVERRIDE_CHARS:
            _record_override(command, reason.strip())
            return 0
        sys.stderr.write(f"MERGE GATE: MERGE_GATE_OVERRIDE needs a reason of at least "
                         f"{MIN_OVERRIDE_CHARS} characters.\n")
        return 2

    for sel in targets:
        pr = resolve_number(sel, root)
        if pr is None:
            sys.stderr.write(
                f"MERGE GATE: could not tell which PR `{sel or '(current branch)'}` is, so it "
                "cannot be checked. Name it by number.\n")
            return 2
        rc, out = run_gate(pr, root)
        if rc != 0:
            sys.stderr.write(
                f"MERGE GATE: PR #{pr} is not ready to merge.\n\n{out}\n\n"
                "This is scripts/check_pr_gates.py. Fix what it says, or merge on the record:\n"
                f"  MERGE_GATE_OVERRIDE=\"<why>\" gh pr merge {pr} ...\n")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
