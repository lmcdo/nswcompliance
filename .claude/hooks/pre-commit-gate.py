#!/usr/bin/env python3
"""PreToolUse hook — intercepts `git commit` Bash commands.

Blocks the commit if this branch's QA report doesn't exist or fails validation.
The path is per-branch and resolved by scripts/qa_report_path.py, never
hardcoded. This is a HARD GATE — the LLM cannot bypass it without the user
approving the tool use rejection.

Environment variables (set by Claude Code):
  TOOL_INPUT — JSON with the Bash command being run

Exit codes:
  0 = allow the command
  2 = block the command (with message to stderr)
"""

import json
import os
import sys
import subprocess


def main():
    # Parse the tool input to get the bash command
    tool_input = os.environ.get("TOOL_INPUT", "{}")
    try:
        data = json.loads(tool_input)
    except json.JSONDecodeError:
        sys.exit(0)  # Not JSON, allow

    command = data.get("command", "")

    # Only intercept git commit commands
    if "git commit" not in command:
        sys.exit(0)

    # Allow --allow-empty (used for testing hooks)
    # Skip check for merge commits
    if "--allow-empty" in command and "test" in command.lower():
        sys.exit(0)

    # Which checkout is this commit actually happening in? CLAUDE_PROJECT_DIR
    # is the directory the session started in, which for this repo's worktree
    # workflow is the MAIN checkout — not the worktree being committed to. That
    # was already wrong before the report went per-branch (the hook validated
    # main's report against a worktree's staged files); with a per-branch report
    # it would be wrong in the blocking direction, because main carries no
    # report at all. So prefer the working tree the command is running in and
    # fall back to the session directory.
    candidates = []
    for start in (os.getcwd(), os.environ.get("CLAUDE_PROJECT_DIR", "")):
        if not start or not os.path.isdir(start):
            continue
        try:
            top = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=10, cwd=start,
            )
        except Exception:
            continue
        root = top.stdout.strip()
        if top.returncode == 0 and root and root not in candidates:
            candidates.append(root)
    if not candidates:
        sys.exit(0)  # not a git repo — nothing this hook can assert

    project_dir = candidates[0]
    report_path = None
    for root in candidates:
        resolver = os.path.join(root, "scripts", "qa_report_path.py")
        if not os.path.exists(resolver):
            continue
        try:
            found = subprocess.run(
                [sys.executable, resolver, "--project-dir", root],
                capture_output=True, text=True, timeout=15, cwd=root,
            )
        except Exception:
            continue
        if found.returncode == 0 and found.stdout.strip():
            project_dir, report_path = root, found.stdout.strip()
            break

    # Gate 1: Report must exist
    if report_path is None:
        target = "<.qa/reports/branch-slug.json>"
        resolver = os.path.join(project_dir, "scripts", "qa_report_path.py")
        if os.path.exists(resolver):
            try:
                shown = subprocess.run(
                    [sys.executable, resolver, "--target", "--relative",
                     "--project-dir", project_dir],
                    capture_output=True, text=True, timeout=15, cwd=project_dir,
                )
                if shown.returncode == 0 and shown.stdout.strip():
                    target = shown.stdout.strip()
            except Exception:
                pass
        print(
            f"BLOCKED: no QA report for this branch.\n"
            f"Expected at: {target}\n"
            f"Create it from scripts/qa_report_template.json, then run:\n"
            f"  python scripts/qa_gate.py\n"
            f"before committing.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Gate 2: Report must pass validation
    gate_script = os.path.join(project_dir, "scripts", "qa_gate.py")
    if not os.path.exists(gate_script):
        # qa_gate.py not present (e.g. other repo) — allow if report exists
        sys.exit(0)

    # Get staged files for cross-check
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10,
            cwd=project_dir,
        )
        diff_files = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception:
        diff_files = []

    # Run qa_gate.py
    cmd = [sys.executable, gate_script, report_path]
    if diff_files:
        cmd += ["--diff-files"] + diff_files

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=project_dir,
        )
    except Exception as e:
        print(f"BLOCKED: qa_gate.py failed to run: {e}", file=sys.stderr)
        sys.exit(2)

    if result.returncode != 0:
        print(
            f"BLOCKED: QA gate validation failed.\n{result.stdout}\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(2)

    # Passed — allow the commit
    sys.exit(0)


if __name__ == "__main__":
    main()
