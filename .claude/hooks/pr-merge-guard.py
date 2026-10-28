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

The merge must also be PINNED to the commit the gate checked:
    gh pr merge 123 --squash --match-head-commit <full head sha>
(REST: `-f sha=<full head sha>`). Without the pin, a push landing between the
check and the merge would be merged unchecked; with it, GitHub refuses.

Fails CLOSED: a merge whose PR cannot be resolved (`pulls/$PR/merge`), a gate
that cannot run, or an override that cannot be recorded is blocked. The escape
must prefix the merge command itself and leaves a record:
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MIN_OVERRIDE_CHARS = 15
REPO = Path(__file__).resolve().parents[2]
OVERRIDE_LOG = REPO / ".claude" / ".merge-gate-overrides.jsonl"

# Text that is DATA, not a command: commit messages, PR bodies, heredoc bodies.
# Without this, `git commit -m "run gh pr merge 902 next"` would be gated.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?^\s*\2\s*$", re.S | re.M)
_MESSAGE_ARG = re.compile(
    r"(?:-m|--message|-b|--body|-t|--title|--subject)(?:\s+|=)(\"[^\"]*\"|'[^']*')")
# Bash backslash-newline and PowerShell backtick-newline continuations.
_CONTINUATION = re.compile(r"[\\`]\r?\n")
# A shell comment: `#` at a word start, unless it is a `#123` PR reference.
_COMMENT = re.compile(r"(^|\s)#(?!\d+\b)[^\n]*", re.M)
# One shell command per segment: an override only counts on its own segment.
_SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|&\n]")
_GH_MERGE = re.compile(r"\bgh(?:\.exe)?\b.*?\bpr\s+merge\b(?P<args>.*)", re.I)
# REST merge endpoint: PUT /repos/o/r/pulls/<anything>/merge, via gh api or curl.
# Any selector, not just digits: `pulls/$PR/merge` must be caught and then fail
# to resolve, not slip past (Sol finding, 2026-10-27).
_API_MERGE = re.compile(r"pulls/(?P<sel>[^/\s\"']+)/merge\b", re.I)
_PR_URL = re.compile(r"/pull/(?P<num>\d+)\b")
_LEADING_OVERRIDE = re.compile(
    r"^\s*MERGE_GATE_OVERRIDE=(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<bare>\S+))\s+")
_PIN_FLAG = re.compile(r"--match-head-commit(?:\s+|=)['\"]?(?P<sha>[0-9a-fA-F]+)")
# The pin only counts as a request FIELD (`-f sha=...`) or a JSON body (`"sha": "..."`). A `?sha=` in the URL is
# ignored by GitHub, so it pins nothing (cross-review 2026-10-28).
_PIN_API = re.compile(r"(?:(?:^|\s)(?:-f|-F|--field|--raw-field)\s+['\"]?sha=|\"sha\"\s*:\s*\")(?P<sha>[0-9a-fA-F]+)")
# Inside a DOUBLE-quoted message the shell still runs `$( ... )` and backticks: `git commit -m "$(gh pr merge 902)"`
# merges. Those parts are kept as their own segments; the rest of the message is data (cross-review 2026-10-28).
_SUBSTITUTION = re.compile(r"\$\(([^()]*(?:\([^()]*\)[^()]*)*)\)|`([^`]*)`")
# gh pr merge flags that take a value: their value is not the PR selector.
_VALUE_FLAGS = {"-b", "--body", "-F", "--body-file", "-t", "--subject", "-A",
                "--author-email", "--match-head-commit", "-R", "--repo"}


@dataclass
class Merge:
    selector: str | None     # None = the current branch's PR
    override: str | None     # reason from a MERGE_GATE_OVERRIDE prefix on THIS segment
    pin: str | None          # sha the merge is pinned to, if any


def _keep_substitutions(m: re.Match) -> str:
    quoted = m.group(1)
    if not quoted.startswith('"'):
        return " "            # single quotes: nothing inside runs
    runs = [a or b for a, b in _SUBSTITUTION.findall(quoted)]
    return " ; " + " ; ".join(runs) + " ; " if runs else " "


def parse_merges(command: str) -> list[Merge]:
    """Every merge a command would perform, one per shell segment."""
    command = _MESSAGE_ARG.sub(_keep_substitutions, _HEREDOC.sub(" ", command))
    # The shell joins continuations before it runs anything, so join them first,
    # or `gh pr \<newline>merge 902` splits into two harmless-looking segments.
    command = _CONTINUATION.sub(" ", command)
    # A comment is not an argument: `gh pr merge 902 # --match-head-commit <sha>`
    # runs unpinned. `#902` (a PR reference) is kept.
    command = _COMMENT.sub("", command)
    merges: list[Merge] = []
    for seg in _SEGMENT_SPLIT.split(command):
        gh = _GH_MERGE.search(seg)
        api = _API_MERGE.search(seg)
        if not gh and not api:
            continue
        ov = _LEADING_OVERRIDE.match(seg)
        override = next((g for g in ov.group("dq", "sq", "bare") if g is not None), "") if ov else None
        if gh:
            pin = _PIN_FLAG.search(seg)
            merges.append(Merge(_selector(gh.group("args")), override, pin and pin.group("sha")))
        else:
            pin = _PIN_API.search(seg)
            merges.append(Merge(api.group("sel"), override, pin and pin.group("sha")))
    return merges


def find_merges(command: str) -> list[str | None]:
    """Every PR selector a command would merge. None = the current branch's PR."""
    return [m.selector for m in parse_merges(command)]


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


def pr_head(pr: int, cwd: str) -> str | None:
    """The PR's current full head sha, or None if it cannot be read."""
    try:
        out = subprocess.run(["gh", "pr", "view", str(pr), "--json", "headRefOid"],
                             capture_output=True, text=True, cwd=cwd, timeout=30)
        return json.loads(out.stdout)["headRefOid"] if out.returncode == 0 else None
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


def _record_override(command: str, reason: str) -> bool:
    """Append the override. False if it could not be written: no record, no merge."""
    try:
        with OVERRIDE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "reason": reason, "command": command[:300]}) + "\n")
        return True
    except OSError:
        return False


def _block(msg: str) -> int:
    sys.stderr.write(f"MERGE GATE: {msg}\n")
    return 2


def main() -> int:
    data = _payload()
    tool_input = data.get("tool_input") or data.get("toolInput") or data
    command = (tool_input.get("command") if isinstance(tool_input, dict) else "") or ""
    merges = parse_merges(command)
    if not merges:
        return 0

    # The repo this hook lives in, not the payload's cwd: a cwd in MSYS form
    # (/c/Users/...) is not a path Windows Python can open, and the gate then
    # "fails closed" for the wrong reason (measured 2026-10-27).
    root = str(REPO)

    for m in merges:
        if m.override is not None:
            if len(m.override.strip()) < MIN_OVERRIDE_CHARS:
                return _block(f"MERGE_GATE_OVERRIDE needs a reason of at least "
                              f"{MIN_OVERRIDE_CHARS} characters.")
            if not _record_override(command, m.override.strip()):
                return _block(f"the override could not be recorded in {OVERRIDE_LOG}; "
                              "an override with no record is not allowed.")
            continue

        pr = resolve_number(m.selector, root)
        if pr is None:
            return _block(f"could not tell which PR `{m.selector or '(current branch)'}` is, so "
                          "it cannot be checked. Name it by number.")
        rc, out = run_gate(pr, root)
        if rc != 0:
            return _block(
                f"PR #{pr} is not ready to merge.\n\n{out}\n\n"
                "This is scripts/check_pr_gates.py. Fix what it says, or merge on the record:\n"
                f"  MERGE_GATE_OVERRIDE=\"<why>\" gh pr merge {pr} ...")
        head = pr_head(pr, root)
        if head is None:
            return _block(f"could not read PR #{pr}'s head commit to pin the merge to.")
        if not m.pin or m.pin.lower() != head.lower():
            return _block(
                f"PR #{pr} passed the gate at {head[:8]}, but the merge is not pinned to that "
                "commit, so a push landing in between would be merged unchecked. Re-run as:\n"
                f"  gh pr merge {pr} --squash --match-head-commit {head}\n"
                f"  (REST: add -f sha={head})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
