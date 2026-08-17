#!/usr/bin/env python3
"""PreToolUse hook — a NEW file nothing else mentions may not be committed.

WHY THIS EXISTS
---------------
2026-08-17. Asked to check whether the solar UI displayed correctly, the session
wrote `frontend-nextjs/scripts/verify-solar-delivered.tsx`: a new file, with a
prior-art justification header, wired into the QA report as a permanent tool.
The task was "render it once and look".

That is the habit this blocks. Every throwaway check becomes a committed,
documented artefact, and the cost is not the file - it is the QA report entry,
the prior-art header, the extra commit, the extra review round, and the extra
restamp each of those forces.

WHY "REFERENCED" AND NOT A WRITTEN REASON
-----------------------------------------
The prior-art guard already asks for a sentence of justification, and this
session wrote one every time it was blocked - three times - and proceeded. An
escape a machine cannot distinguish from compliance is not an escape hatch, it
is a formality. Writing sentences is free.

So the test is a FACT rather than a claim: does anything else in the repository
mention this file? Product code gets imported. A CLI check gets named in
.claude/dq_checks.json or a workflow. A one-off written to answer a question is
mentioned by nothing, because nothing needed it before and nothing will call it
after.

Measured against the real cases:
  verify-solar-delivered.tsx        - referenced NOWHERE      -> blocked
  check_control_subject_mismatch.py - named in dq_checks.json -> allowed
  lib/solar/delivered.ts            - imported by 4 surfaces  -> allowed

WHAT IT DOES NOT TOUCH
----------------------
Tests, migrations, QA reports, docs, and anything under .claude/. Those are
referenced by convention rather than by name, and blocking them would make the
hook fire on ordinary work - which is how a guard gets switched off.

Exit codes:  0 = allow   2 = block (message on stderr)
"""
import json
import os
import re
import subprocess
import sys

# Paths whose files are found by convention, not by being named somewhere.
EXEMPT_DIRS = (
    "tests/", "test/", "__tests__/", "migrations/", "docs/",
    ".qa/", ".claude/", ".github/", ".githooks/",
)
EXEMPT_SUFFIXES = (".md", ".json", ".yml", ".yaml", ".txt", ".sql", ".toml", ".lock")

# Where a real caller would name it. Deliberately NOT all of .claude/ — that
# tree carries .claude/docs/history/, archived prose in which a generic word
# appears constantly. Searching it made `lib/solar/delivered.ts` read as
# "referenced" because two 2026-01 strategy documents contain the word
# "delivered". A guard that passes on prose is not checking for a caller.
SEARCH_DIRS = (
    "scripts", "services", "src", "enrichment",
    "frontend-nextjs/app", "frontend-nextjs/lib",
    "frontend-nextjs/components", "frontend-nextjs/scripts",
    ".github/workflows", ".githooks",
    ".claude/dq_checks.json", ".claude/DATA_QUALITY_TRACKER.md",
    ".claude/settings.json", "package.json", "Makefile",
)


def sh(args, cwd=None):
    try:
        r = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def main():
    try:
        data = json.loads(os.environ.get("TOOL_INPUT", "{}"))
    except json.JSONDecodeError:
        sys.exit(0)
    command = data.get("command", "")

    if "git commit" not in command:
        sys.exit(0)

    cd = re.search(r"cd\s+\"([^\"]+)\"|cd\s+'([^']+)'", command)
    cwd = next((g for g in cd.groups() if g), None) if cd else None
    if cwd and not os.path.isdir(cwd):
        cwd = None

    added = [
        p.strip().replace("\\", "/")
        for p in sh(["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
                    cwd=cwd).splitlines()
        if p.strip()
    ]
    if not added:
        sys.exit(0)

    root = (sh(["git", "rev-parse", "--show-toplevel"], cwd=cwd) or "").strip() \
        or (cwd or ".")

    orphans = []
    for rel in added:
        if any(rel.startswith(d) or f"/{d}" in rel for d in EXEMPT_DIRS):
            continue
        if rel.endswith(EXEMPT_SUFFIXES):
            continue
        base = os.path.basename(rel)
        stem = os.path.splitext(base)[0]
        parent = os.path.basename(os.path.dirname(rel))
        # Two forms, both SPECIFIC. A bare stem is not one of them: "delivered"
        # matches ordinary prose, which is how the first version passed a file
        # on the strength of two strategy documents from January.
        #   base           "check_control_subject_mismatch.py"  — CLI + ledger
        #   parent/stem    "solar/delivered"                    — import path
        needles = [base]
        if parent:
            needles.append(f"{parent}/{stem}")
        args = ["git", "grep", "-l", "-F"]
        for n in needles:
            args += ["-e", n]
        hits = sh(args + ["--"] + list(SEARCH_DIRS), cwd=cwd).splitlines()
        hits = [h.strip().replace("\\", "/") for h in hits if h.strip()]
        hits = [h for h in hits if h != rel and not h.startswith(".qa/")]
        if not hits:
            orphans.append(rel)

    if orphans:
        sys.stderr.write(
            "\nNEW-FILE GUARD — nothing in this repository mentions these files:\n\n"
            + "".join(f"    {o}\n" for o in orphans)
            + "\nA file that nothing imports, calls or names is usually one written to\n"
            "ANSWER A QUESTION rather than to change what the product does. On\n"
            "2026-08-17 that was verify-solar-delivered.tsx: created to check\n"
            "whether a page rendered, then given a prior-art header and a QA report\n"
            "entry and committed as a permanent tool. The task was to look once.\n\n"
            "If it is throwaway: run it, report what it said, delete it.\n"
            "  git restore --staged <file> && rm <file>\n\n"
            "If it is real: give it a caller. A CLI check belongs in\n"
            ".claude/dq_checks.json or a workflow; a module belongs to whatever\n"
            "imports it. Being named by something is the evidence this asks for,\n"
            "because a written justification is free and was supplied three times\n"
            "that day while the habit continued.\n"
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
