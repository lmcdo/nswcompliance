#!/usr/bin/env python
"""Block a work turn from ending without a DONE WHEN line and a number.

WHY THIS EXISTS
---------------
The user asked, repeatedly, for one thing: say what "finished" means BEFORE
starting, as a command and a value, then report that number first. On
2026-10-03 the model wrote that format itself, used it once, and had silently
stopped using it four turns later -- in the same session in which it had just
explained why the absence of it causes the loop. The user's words: "how the
fuck to ensure you never fail to use the done when format".

CLAUDE.md and MEMORY.md already carry roughly sixty behavioural rules and the
drift happened anyway. A rule a model has to remember is not a control. This
repo's own lesson, memory/feedback-incident-rule-machine.md, is
incident -> rule -> MACHINE: the QA tier line, the branch guard and the
liability scan are all hooks for exactly this reason.

WHY A `Stop` HOOK AND NOT THE ALTERNATIVES
------------------------------------------
  Stop             fires on EVERY turn end and can BLOCK. The only option that
                   enforces rather than reminds.
  UserPromptSubmit injects text but cannot check the answer.
  PreToolUse       fires before the work, when the report does not exist yet.
  Skill            loads on invocation; does nothing about mid-session drift.
  CLAUDE.md        is where the sixty rules that did not hold already live.

WHAT IT CHECKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
Shape only: a `DONE WHEN` line, and a digit in the opening of the final
message. It CANNOT judge whether the criterion is meaningful and must not
pretend to -- a hook claiming to verify substance would be the "check that
cannot fail" shape this repo keeps finding (DQ-30, DQ-69, DQ-115's first
draft). The user's own "number first" correction stays the real quality
control.

ONLY WORK TURNS ARE GATED. A turn that answered a question, read files or ran
read-only commands is exempt: demanding a completion criterion for "what does
this function do" is noise, and a noisy gate gets switched off within a day --
see tests/test_railway_cron_drift.py, where whitespace false alarms are called
out as the thing that trains people to ignore a check.

FAIL-OPEN, ALWAYS. Any internal error exits 0. A bug in this file must never be
able to stop real work, and `stop_hook_active` is honoured so a blocked turn
can never loop.
"""
import json
import re
import sys

# Tools whose use means the turn CHANGED something and therefore owes a criterion.
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}

# Bash/PowerShell count only when the command looks like it mutated state. A turn
# that only grepped, read and counted is not a work turn.
#
# TWO PATTERNS, not one, and the split is a bug fix. The first version put
# `--apply` inside a group wrapped in \b...\b, which made that alternative
# UNMATCHABLE: a word boundary cannot occur between a space and a `-`. So
# `python scripts/retag_applicability_slug_docids.py --councils x --apply`
# — the actual production write this session performed — sailed through the gate
# ungated, and only the two hard-coded script names were ever caught. Found by
# the pre-push review on 2026-10-03, not by my own tests, which is why
# test_done_when_gate.py now carries a case for an UNKNOWN script name.
MUTATING = re.compile(
    r"\b(git\s+(commit|push|merge|revert|reset|rebase|cherry-pick)"
    r"|gh\s+pr\s+(merge|create)"
    r"|UPDATE\s|INSERT\s+INTO|DELETE\s+FROM|ALTER\s+TABLE"
    r"|pip\s+install|npm\s+(install|publish)"
    r"|dcp_commit_approved|dcp_approve_graded)\b",
    re.I,
)

# Flags and redirections that mean a write, whatever script carries them. These
# cannot sit inside the \b group above, so they are matched on their own with
# lookarounds that require the token to stand alone rather than be part of a
# longer word.
MUTATING_FLAG = re.compile(
    r"(?<!\S)(--apply|--write|--commit|--force|--no-dry-run|--execute)(?!\S)"
    r"|(?<!\S)(>|>>)(?!\S)"
    r"|(?<!\S)tee(?!\S)",
    re.I,
)


def mutates(command: str) -> bool:
    """Does this command look like it changed something outside the process?

    False positives cost a nag on a read-only turn; false negatives let a
    production write be reported with no number at all. So this errs toward
    gating, and the read-only exemption is carried by the tool name instead.
    """
    return bool(MUTATING.search(command) or MUTATING_FLAG.search(command))

DONE_WHEN = re.compile(r"done\s*when", re.I)
HAS_DIGIT = re.compile(r"\d")


def _is_tool_result(entry) -> bool:
    for block in (entry.get("message") or {}).get("content") or []:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            return True
    return False


def _tail(path, limit=80):
    """Last `limit` transcript entries, oldest first. [] if unreadable."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()[-limit:]
    except Exception:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    # A turn this hook already blocked must never be blocked again.
    if payload.get("stop_hook_active"):
        return 0

    entries = _tail(payload.get("transcript_path") or "")
    if not entries:
        return 0

    # Walk back to the last real user message; everything after it is this turn.
    turn = []
    for entry in reversed(entries):
        if entry.get("type") == "user" and not _is_tool_result(entry):
            break
        turn.append(entry)
    turn.reverse()
    if not turn:
        return 0

    did_work = False
    final_text = ""
    for entry in turn:
        for block in (entry.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name = block.get("name") or ""
                if name in WRITE_TOOLS:
                    did_work = True
                elif name in ("Bash", "PowerShell"):
                    if mutates(str((block.get("input") or {}).get("command") or "")):
                        did_work = True
            elif block.get("type") == "text" and entry.get("type") == "assistant":
                final_text = block.get("text") or ""

    if not did_work or not final_text.strip():
        return 0

    opening = final_text.strip()[:400]
    if DONE_WHEN.search(final_text) and HAS_DIGIT.search(opening):
        return 0

    missing = []
    if not DONE_WHEN.search(final_text):
        missing.append("no DONE WHEN line")
    if not HAS_DIGIT.search(opening):
        missing.append("no number in the opening")

    sys.stderr.write(
        "DONE-WHEN GATE: this turn changed things, but the report is missing "
        + " and ".join(missing) + ".\n\n"
        "Rewrite the final message so it OPENS with the measured number and carries "
        "the completion criterion. For example:\n\n"
        "  DQ-115: 141 (was 176).\n"
        "  DONE WHEN: python scripts/dq_probe_applicability_config.py --id DQ-115 prints 0.\n\n"
        "If the number is not known because a measurement has not finished, say so and give "
        "the command that will print it. An unmeasured claim is not a report.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)   # fail-open, always
