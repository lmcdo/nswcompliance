#!/usr/bin/env python3
# prior-art-checked: no script in scripts/ or .github/ maps a diff to the live-data gate steps; gates.yml ran
# every live check on every PR.
"""Which live-data gate steps a change touches. Prints RUN_<KEY>=1|0 lines for $GITHUB_ENV.

WHY (user decision 2026-10-25, ~/.claude/plans/ce-gates-split-PLAN-2026-10-25.md): a PR's live-data checks read
data the PR has not changed yet -- extraction and commit run after the merge -- so they cannot see the PR's own
effect, only other people's data and a slow database. That week every blocked PR was blocked by live state it
did not touch (DQ-79, DQ-118 twice, DQ-103/104/105 timing out, the nightly freshness rule). Those checks now run
nightly (data-watch.yml) and right after rules go live; a PR runs one only when the PR changes that check, its
baseline, or the ledger row it reports.

Fails CLOSED: if the changed files cannot be read, or the gate wiring itself changed, every key is 1.

Usage (gates.yml, after a checkout with fetch-depth >= 2):
    python scripts/gate_touched_checks.py >> "$GITHUB_ENV"
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys

#: Each live-data gate step and the files that can change its answer.
CHECKS: dict[str, tuple[str, ...]] = {
    "LEDGER": (".claude/dq_checks.json", ".claude/DATA_QUALITY_TRACKER.md", "scripts/dq_check.py",
               "scripts/dq_probe_*.py", "scripts/dq_db.py", "scripts/dq_*.py"),
    "OUTREACH": (".claude/dq_checks.json", "scripts/outreach_claim_checks.py", "scripts/dq_check.py"),
    "COVERAGE_RATCHETS": ("scripts/check_dcp_as_at_coverage.py", "scripts/check_satellite_manifests.py",
                          "scripts/brief_field_coverage_ratchet.py", "*coverage*baseline*", "*manifest*baseline*",
                          "*brief_field_coverage*"),
    # The served-answer check calls the serving code itself, so a change there must run it too (Sol).
    "SERVED_ANSWER": ("scripts/check_served_answer_quality.py", ".claude/served_answer_quality_baseline.json",
                      "scripts/conveyancing_db.py", "scripts/check_dcp_as_at_coverage.py"),
    "CONTROL_VALUES": ("scripts/validate_control_source_values.py", "scripts/control_source_values_baseline.json",
                       "services/extracted_data_integrity.py"),
    "CONTROLS_PROVENANCE": ("scripts/validate_controls_provenance.py",),
    "PAGE_MAPS": ("scripts/dcp_page_map_gate.py", "*dcp_page_map_baseline.json", "*dcp_page_map_check.json"),
    "RAILWAY_CRON": ("scripts/check_railway_cron_drift.py", "railway*.toml"),
}

#: A change to the wiring itself runs everything, so this file cannot switch a check off unseen.
RUN_ALL: tuple[str, ...] = (".github/workflows/gates.yml", "scripts/gate_touched_checks.py")


def decide(changed: list[str] | None) -> dict[str, bool]:
    """KEY -> run? None (could not read the diff) runs everything."""
    if changed is None or any(f in RUN_ALL for f in changed):
        return {k: True for k in CHECKS}
    return {k: any(fnmatch.fnmatch(f, p) for f in changed for p in pats) for k, pats in CHECKS.items()}


def changed_files(base: str | None = None) -> list[str] | None:
    """Files changed since `base` (a push: the commit before it, so every pushed commit counts - Sol), else
    HEAD~1..HEAD (a pull_request merge commit: exactly the PR's changes). None when git cannot answer."""
    base = (base or "").strip()
    if base and set(base) == {"0"}:  # a new branch: no "before" commit
        return None
    try:
        out = subprocess.run(["git", "diff", "--name-only", base or "HEAD~1", "HEAD"], capture_output=True,
                             text=True, check=True, timeout=60).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]


def main() -> int:
    changed = changed_files(os.environ.get("GATE_DIFF_BASE"))
    for key, run in decide(changed).items():
        print(f"RUN_{key}={'1' if run else '0'}")
    note = "could not read the diff: running every live check" if changed is None else f"{len(changed)} files changed"
    print(f"gate_touched_checks: {note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
