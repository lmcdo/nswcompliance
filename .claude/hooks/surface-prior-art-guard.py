#!/usr/bin/env python3
"""Surface prior-art guard — blocks Artifact publishes until existing surfaces
were actually checked.

Why: the 2026-07 CDC/DCP investigation produced four prior-art misses in one
session — including building an artifact review sheet while /internal/dcp-review
already existed — despite the rule living in memory. Instructions demonstrably
don't guarantee the check; this hook does, the same way pre-impl-gate.js and
prior-art-guard.py already gate code edits.

Mechanism: publishing an Artifact requires a FRESH marker file
  .claude/.prior-art-surfaces.json
    {"timestamp": "<ISO>", "sweeps": ["<grep/query run>", ...],
     "verdict": "<why no existing surface serves this / which one was reused>"}
The marker must be newer than MAX_AGE_HOURS and list at least two sweeps.
Listing-only Artifact calls (action: "list") pass through.

Exit codes per Claude Code hook contract: 0 allow, 2 block (stderr shown).
"""

import json
import os
import sys
from datetime import datetime, timezone

MAX_AGE_HOURS = 4

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Artifact":
        return 0
    tool_input = payload.get("tool_input") or {}
    if tool_input.get("action") == "list":
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    marker_path = os.path.join(project_dir, ".claude", ".prior-art-surfaces.json")

    problem = None
    if not os.path.exists(marker_path):
        problem = "marker missing"
    else:
        try:
            marker = json.load(open(marker_path, encoding="utf-8"))
            ts = datetime.fromisoformat(str(marker.get("timestamp") or "").replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            sweeps = marker.get("sweeps") or []
            if age_h > MAX_AGE_HOURS:
                problem = f"marker stale ({age_h:.1f}h old, max {MAX_AGE_HOURS}h)"
            elif len(sweeps) < 2 or not marker.get("verdict"):
                problem = "marker must list >=2 sweeps and a verdict"
        except Exception as exc:
            problem = f"marker unreadable: {exc}"

    if problem:
        sys.stderr.write(
            "BLOCKED: Artifact publish requires a fresh prior-art surfaces check "
            f"({problem}).\n"
            "Before building a new page/sheet, sweep for an existing surface that "
            "already serves this need:\n"
            "  1. frontend: grep the CONCEPT across frontend-nextjs/app (incl. "
            "app/internal), components/, hooks/\n"
            "  2. existing artifacts/plans: Artifact list + ~/.claude/plans INDEX\n"
            "  3. (data claims) DB content: documents by name pattern + "
            "regulatory_provisions by document_id\n"
            "Then write .claude/.prior-art-surfaces.json with {timestamp, sweeps "
            "(the greps/queries you actually ran), verdict (reuse X / nothing "
            "exists because ...)} and re-issue. If an existing surface serves the "
            "need, USE IT instead of publishing.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
