"""Tell the owner, from GitHub's own machines, whenever a guardrail is changed or bypassed.

prior-art-checked: plan none (user-approved 2026-11-03); sends through the existing
verifyops_outside_ping.send_telegram rather than a seventh copy of a Telegram sender.

WHY. On 2026-11-03 the assistant wrote a prior-art escape line without opening the
approved plan it was meant to check. Hooks run on this PC, where the assistant can also
edit them, their logs and their escape lines. This runs on GitHub-hosted runners against
merged history, so it reports what actually landed on main, not what anyone says landed.

It lists, for a git range:
  * changed guardrail files (hooks, settings, git hooks, workflows, the gate scripts), and
  * added lines that bypass or loosen a guard (escape lines, overrides, skipped reviews).

    python scripts/guardrail_watch.py --range <before>..<after>   # one push
    python scripts/guardrail_watch.py --since "7 days ago"        # weekly digest
Exit 0 = nothing to report, or reported and Telegram confirmed it; 1 = Telegram failed or
not configured while there WAS something to report (an alarm must not fail quietly).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

GUARD_PATHS = (
    ".claude/hooks/",
    ".claude/settings.json",
    ".githooks/",
    ".github/workflows/",
    "scripts/qa_gate.py",
    "scripts/check_pr_gates.py",
    "scripts/guardrail_watch.py",
)

BYPASS = re.compile(
    r"prior-art-checked:|RULE_WRITE_OK=|MERGE_GATE_OVERRIDE|--no-verify|SOL_REVIEW=0|"
    r"real_layer_exempt|rule_write_guard\s+SET\s+mode|collect_ignore|pytest\.mark\.skip",
    re.I)


def is_guard_path(path: str) -> bool:
    return any(path == g or path.startswith(g) for g in GUARD_PATHS)


def parse_diff(diff: str) -> tuple[list[str], list[tuple[str, str]]]:
    """(changed guard files, [(file, added bypass line)]) from `git diff` / `git log -p` text."""
    guards: list[str] = []
    bypasses: list[tuple[str, str]] = []
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[4:].removeprefix("b/").strip()
            if current != "/dev/null" and is_guard_path(current) and current not in guards:
                guards.append(current)
        elif line.startswith("--- a/") and current is None:
            continue
        elif line.startswith("diff --git "):
            current = None
            m = re.match(r"diff --git a/(\S+) b/(\S+)", line)
            if m and is_guard_path(m.group(2)) and m.group(2) not in guards:
                guards.append(m.group(2))     # catches deletions, where +++ is /dev/null
        elif line.startswith("+") and not line.startswith("+++") and current:
            if BYPASS.search(line):
                bypasses.append((current, line[1:].strip()[:160]))
    return guards, bypasses


def message(label: str, guards: list[str], bypasses: list[tuple[str, str]]) -> str | None:
    if not guards and not bypasses:
        return None
    out = [f"Guardrail watch ({label})"]
    if guards:
        out.append(f"Guardrail files changed ({len(guards)}):")
        out += [f"  - {g}" for g in guards[:30]]
    if bypasses:
        out.append(f"Escape/override lines added ({len(bypasses)}):")
        out += [f"  - {f}: {t}" for f, t in bypasses[:30]]
    out.append("Check each on GitHub: is it one you approved?")
    return "\n".join(out)[:3900]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True,
                          encoding="utf-8", errors="replace").stdout


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--range", help="before..after")
    g.add_argument("--since", help='e.g. "7 days ago"')
    ap.add_argument("--print-only", action="store_true", help="print, do not send")
    a = ap.parse_args(argv)
    if a.range:
        diff, label = _git("diff", a.range), f"push {a.range}"
    else:
        diff, label = _git("log", "-p", "--first-parent", f"--since={a.since}", "HEAD"), f"since {a.since}"
    text = message(label, *parse_diff(diff))
    if text is None:
        print("guardrail watch: nothing changed or bypassed")
        return 0
    print(text)
    if a.print_only:
        return 0
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("::error::TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set; this report was not delivered")
        return 1
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from verifyops_outside_ping import send_telegram
    if not send_telegram(text, token, chat):
        print("::error::Telegram did not confirm the message; report not delivered")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
