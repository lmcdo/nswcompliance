#!/usr/bin/env python3
"""PreToolUse hook — a REPEATED `git push` may not hide its own error output.

WHY THIS EXISTS
---------------
2026-08-17, fix/solar-dc-vs-delivered. Six push attempts in a row failed. Every
one was run as:

    git push 2>&1 | grep -aE "error:|QA-GATE: FAILED|->" | head -3

which printed `QA-GATE: FAILED - 1 validation errors:` and cut off the very next
line, the one that said WHAT the error was. So the session assumed the failure
was the QA-report stamp problem it had diagnosed earlier, did a pointless
restamp, pushed again, saw the same truncated message, and repeated.

The actual error the whole time was one line in a new file: `=== null` where
the type-boundary gate wants `== null`. A ten-second fix, found the moment the
gate was run without the grep.

That is not carelessness, it is a filter that can only confirm its author's
hypothesis. The same defect class this repo keeps finding in its own data:
a check keyed on the wrong thing, a guard that can only pass.

WHAT IT DOES
------------
Counts push attempts per (branch, HEAD sha). The remote-tracking ref tells it
whether the previous attempt actually landed - if origin/<branch> still does not
contain HEAD, the last push did not succeed. On the SECOND attempt at the same
unpushed sha, a command that pipes push output through grep/head/tail/awk/sed
is BLOCKED, with instructions to re-run it unfiltered.

The first attempt is never blocked: filtering a push that is going to succeed
costs nothing, and a hook that fires constantly gets bypassed.

Exit codes:  0 = allow   2 = block (message on stderr)
"""
import json
import os
import re
import subprocess
import sys

STATE = ".claude/.push-attempts.json"

# Anything that can swallow the line after the one it matched.
FILTERS = re.compile(r"\|\s*(?:grep|head|tail|awk|sed|findstr|select-string)\b", re.I)


def sh(*args, cwd=None):
    try:
        r = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def main():
    try:
        data = json.loads(os.environ.get("TOOL_INPUT", "{}"))
    except json.JSONDecodeError:
        sys.exit(0)
    # `or ""` not a default: a key PRESENT with value null skips the
    # default and would hand None to the `in` test below.
    command = data.get("command") or ""

    if "git push" not in command:
        sys.exit(0)
    if "--no-verify" in command:
        sys.exit(0)  # an explicit emergency bypass is its own decision

    # Where is the push actually happening? A `cd <path> && git push` targets
    # that directory, not the session's project dir - this repo runs everything
    # from worktrees, so resolving it wrong would read another branch's state.
    cd = re.search(r"cd\s+\"([^\"]+)\"|cd\s+'([^']+)'", command)
    cwd = next((g for g in cd.groups() if g), None) if cd else None
    if cwd and not os.path.isdir(cwd):
        cwd = None

    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=cwd)
    head = sh("git", "rev-parse", "HEAD", cwd=cwd)
    if not branch or not head:
        sys.exit(0)  # cannot tell - never block on ignorance

    root = sh("git", "rev-parse", "--show-toplevel", cwd=cwd) or (cwd or ".")
    path = os.path.join(root, STATE)

    state = {}
    if os.path.exists(path):
        try:
            state = json.loads(open(path, encoding="utf-8").read())
        except Exception:
            state = {}

    # Did the previous attempt land? If the remote-tracking ref already contains
    # HEAD there is nothing outstanding and any count is stale.
    # --is-ancestor answers by EXIT CODE and prints nothing, so it has to be
    # run directly rather than through sh(), which reads stdout.
    upstream = sh("git", "rev-parse", f"origin/{branch}", cwd=cwd)
    landed = False
    if upstream:
        try:
            landed = subprocess.run(
                ["git", "merge-base", "--is-ancestor", head, f"origin/{branch}"],
                capture_output=True, cwd=cwd, timeout=15,
            ).returncode == 0
        except Exception:
            landed = False

    prev = state.get(branch) or {}
    if landed or prev.get("sha") != head:
        attempts = 0
    else:
        attempts = int(prev.get("attempts") or 0)

    attempts += 1
    state[branch] = {"sha": head, "attempts": attempts}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1)
    except Exception:
        pass

    if attempts >= 2 and FILTERS.search(command):
        sys.stderr.write(
            "\nPUSH-RETRY GUARD — this is attempt %d at pushing %s on %s, and the\n"
            "previous one did not land. The command filters its own output:\n\n"
            "    %s\n\n"
            "That is how six attempts were spent on one branch on 2026-08-17: the\n"
            "grep printed 'QA-GATE: FAILED' and cut off the NEXT line, the one\n"
            "naming the error. The real cause was a single `=== null`.\n\n"
            "Re-run it unfiltered and read the whole thing:\n\n"
            "    git push\n\n"
            "Or ask the gate directly, which prints the reason in full:\n\n"
            "    python scripts/qa_gate.py\n"
            % (attempts, head[:8], branch, command.strip()[:200])
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
