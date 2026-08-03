# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Extract only the ADDED lines from a git diff.

Scanning added lines instead of whole files is what makes the tool
adoptable in an existing codebase: the day it is installed, nothing old
is flagged — only text written from that day on is held to the rule.
"""

from __future__ import annotations

import re
import subprocess

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

AddedLines = dict[str, list[tuple[int, str]]]


class GitError(Exception):
    """Raised when git cannot produce the requested diff."""


def _run_diff(args: list[str]) -> str:
    result = subprocess.run(
        ["git", "diff", "-U0", "--no-color", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode not in (0, 1):
        raise GitError(result.stderr.strip() or "git diff failed")
    return result.stdout


def parse_added_lines(diff_text: str) -> AddedLines:
    """Parse unified diff output (-U0) into {path: [(line_no, text), ...]}."""
    files: AddedLines = {}
    current: str | None = None
    line_no = 0

    for raw in diff_text.split("\n"):
        if raw.startswith("+++ "):
            target = raw[4:]
            current = target[2:] if target.startswith("b/") else None
            if target == "/dev/null":
                current = None
            continue
        if raw.startswith("@@"):
            match = _HUNK.match(raw)
            if match and current is not None:
                line_no = int(match.group(1))
            continue
        if current is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            files.setdefault(current, []).append((line_no, raw[1:]))
            line_no += 1
    return files


def added_since(base: str) -> AddedLines:
    """Added lines between merge-base(base, HEAD) and HEAD."""
    return parse_added_lines(_run_diff([f"{base}...HEAD"]))


def added_staged() -> AddedLines:
    """Added lines currently staged for commit."""
    return parse_added_lines(_run_diff(["--cached"]))
