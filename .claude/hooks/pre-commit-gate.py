#!/usr/bin/env python3
"""PreToolUse hook — intercepts `git commit` Bash commands.

Blocks the commit if .qa_report.json doesn't exist or fails validation.
This is a HARD GATE — the LLM cannot bypass it without the user approving
the tool use rejection.

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

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    report_path = os.path.join(project_dir, ".qa_report.json")

    # Gate 1: Report must exist
    if not os.path.exists(report_path):
        print(
            "BLOCKED: .qa_report.json not found.\n"
            "Create the QA report and run: python scripts/qa_gate.py .qa_report.json\n"
            "before committing.",
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
