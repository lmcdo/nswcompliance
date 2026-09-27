#!/usr/bin/env python3
# prior-art-checked: reuse not viable, four sweeps 2026-09-27 on origin/main
# b8b49369. (1) DB content: N/A, this is a session hook and reads no table of its
# own. (2) Frontend: grep over frontend-nextjs/{app,components,hooks} for a
# session/status surface returns the internal review page (/internal/dcp-review),
# which lists PENDING EXTRACTIONS for approval - a different question from "what
# is still undecided", and a web page cannot brief a terminal session anyway.
# (3) Python: .claude/hooks/ holds ten hooks and exactly one SessionStart hook,
# session-capability-index.py. It enumerates service modules, spatial overlays and
# portal constraints by WALKING THE CODEBASE - no database, no DQ row, no exit
# code that can be wrong. Putting live probes inside it would make a static index
# fail whenever Supabase is slow, and it is the file every session depends on to
# know what exists. Deliberately separate. (4) Plans + memory: MEMORY.md and
# ~/.claude/plans/INDEX.md record no session-start status printer; the nearest
# thing is the standing instruction "state = ask a command, never a memory note",
# which is what this obeys.
"""Print what is still UNDECIDED about who each rule applies to, live, at session start.

WHY THIS EXISTS
---------------
On 2026-09-27 the user asked how the applicability work keeps getting called
finished and then found broken. The answer is not that anyone lied. The 16
council configs are real, well written, and quote each chapter's own scope
section. What went wrong is that "done" was declared when a config FILE was
written, and nothing between that moment and the next session's first prompt
ever asked whether an address now returns the right rules.

So the next session must not be able to start from prose. It starts from a
number a command produced thirty seconds ago:

    DQ-114  scope keys reading ALL because nobody decided them   -> target 0
    DQ-115  declared keys whose authority no machine can read    -> target 0

Both are read-only. Both print the command that produced them, so any figure
here can be re-run rather than trusted - CLAUDE.md's standing rule applied to a
session banner.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not re-derive the per-council breakdown. Grouping DQ-114 would mean a
second copy of its SQL living here, and two copies of a measurement are how two
baselines start disagreeing about what "worse" means (the reason
check_served_answer_quality.py imports _ratchet instead of copying it). The
probes stay the single definition; this prints their counts and the command for
the detail.

It does not cache. A cached status with a timestamp is still a status somebody
has to remember to refresh, which is the failure being fixed.

It never reports UNKNOWN as clean. An unreachable database prints as UNKNOWN and
says so, because "no number" and "zero" are the confusion this whole effort
exists to remove.

It always exits 0. A slow or unreachable database must not stop a session from
starting; the banner says it could not measure, and that is the honest output.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])

#: (label, argv, one-line meaning). Kept to probes that answer in well under a
#: second - measured 0.4s and 0.1s on 2026-09-27. DQ-102 and DQ-103 run the
#: tagger over all 17,440 served rows and are printed as commands instead: a
#: session banner that takes ten seconds gets turned off, and a hook that is
#: turned off measures nothing.
FAST = [
    ("DQ-114", [sys.executable, "scripts/dq_probe_live.py", "--id", "DQ-114"],
     "scope keys reading ALL because nobody decided them"),
    ("DQ-115", [sys.executable, "scripts/dq_probe_applicability_config.py",
                "--id", "DQ-115"],
     "declared keys whose authority no machine can read"),
]

SLOW = [
    ("DQ-102", "scripts/dq_probe_applicability_config.py --id DQ-102",
     "a chapter onboarded with no config entry"),
    ("DQ-103", "scripts/dq_probe_applicability_config.py --id DQ-103",
     "the row's own text evidence discarded"),
]

PLAN = "~/.claude/plans/ce-applicability-answer-PLAN-2026-09-27.md"

_COUNT = re.compile(r"^\s*count\s*:\s*([\d,]+)", re.M)


def _measure(argv: list[str]) -> str:
    """The probe's count, or an UNKNOWN string. Never raises."""
    try:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                           timeout=25)
    except subprocess.TimeoutExpired:
        return "UNKNOWN (probe timed out - not the same as zero)"
    except Exception as exc:  # noqa: BLE001
        return f"UNKNOWN (could not run: {exc})"
    if r.returncode == 2:
        return "UNKNOWN (database unreachable - not the same as zero)"
    m = _COUNT.search(r.stdout or "")
    if not m:
        return "UNKNOWN (probe printed no count)"
    return m.group(1)


def main() -> int:
    lines = ["APPLICABILITY - who each rule applies to (measured now, read-only)"]
    for pid, argv, means in FAST:
        lines.append(f"  {pid}  {_measure(argv):>9}  {means}")
    lines.append("  target for both: 0. Neither is clearable by typing ALL -")
    lines.append("  DQ-115 requires every declared scope to carry the council's own words.")
    lines.append("  slower companions, on demand:")
    for pid, cmd, means in SLOW:
        lines.append(f"    python {cmd}   # {pid}: {means}")
    lines.append(f"  plan: {PLAN}")
    lines.append('  "done" = these reach 0 AND the test addresses pass. Not "config merged".')
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # A banner must never stop a session from starting.
        print(f"APPLICABILITY: status unavailable ({exc}). Run "
              f"`python scripts/dq_check.py --id DQ-114` by hand.")
        sys.exit(0)
