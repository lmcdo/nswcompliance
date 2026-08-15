#!/usr/bin/env python3
"""Update the CORRUPTION_PREVENTION_QUICKSTART.md with latest run status."""

import sys
import re
from datetime import datetime
from pathlib import Path

def update_status(task_type, run_time):
    """Update the quickstart document with task run status."""

    quickstart_path = Path(__file__).parent.parent / "CORRUPTION_PREVENTION_QUICKSTART.md"

    if not quickstart_path.exists():
        print(f"Warning: {quickstart_path} not found")
        return

    try:
        content = quickstart_path.read_text(encoding='utf-8')

        # Find or create the status section
        status_marker = "## 📊 Automated Task Status"

        if status_marker not in content:
            # Add status section before "Current Status" section
            current_status_pos = content.find("## Current Status")
            if current_status_pos > 0:
                status_section = f"\n{status_marker}\n\n"
                status_section += "| Task | Last Run | Status |\n"
                status_section += "|------|----------|--------|\n"
                status_section += "| Nightly Maintenance | Never | Waiting |\n"
                status_section += "| Weekly Vacuum | Never | Waiting |\n"
                status_section += "| Health Check | Never | Waiting |\n\n"
                status_section += "**Log files:**\n"
                status_section += "```\n"
                status_section += "C:\\Users\\lawre\\downloads\\solvyra\\projects\\compliance engine\\compliance-engine\\logs\\maintenance.log\n"
                status_section += "C:\\Users\\lawre\\downloads\\solvyra\\projects\\compliance engine\\compliance-engine\\logs\\health_check.log\n"
                status_section += "```\n\n---\n\n"

                content = content[:current_status_pos] + status_section + content[current_status_pos:]

        # Update the specific task row
        if task_type == "nightly_maintenance":
            pattern = r"\| Nightly Maintenance \| .* \| .* \|"
            replacement = f"| Nightly Maintenance | {run_time} | ✅ Success |"
        elif task_type == "weekly_vacuum":
            pattern = r"\| Weekly Vacuum \| .* \| .* \|"
            replacement = f"| Weekly Vacuum | {run_time} | ✅ Success |"
        elif task_type == "health_check":
            pattern = r"\| Health Check \| .* \| .* \|"
            replacement = f"| Health Check | {run_time} | ✅ Passed |"
        elif task_type == "health_check_failed":
            pattern = r"\| Health Check \| .* \| .* \|"
            replacement = f"| Health Check | {run_time} | ❌ Issues Found |"
        else:
            print(f"Unknown task type: {task_type}")
            return

        content = re.sub(pattern, replacement, content)

        # Write back
        quickstart_path.write_text(content, encoding='utf-8')
        print(f"Updated status for {task_type}")

    except Exception as e:
        print(f"Error updating status: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: update_quickstart_status.py <task_type> <run_time>")
        sys.exit(1)

    task_type = sys.argv[1]
    run_time = sys.argv[2]

    update_status(task_type, run_time)
