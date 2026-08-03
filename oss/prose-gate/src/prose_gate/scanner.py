# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Core scan: run the compiled term pattern over candidate lines."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .exclusions import ExclusionRules, allowed_terms, is_excluded_line


@dataclass
class Finding:
    path: str
    line: int
    term: str
    text: str

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "line": self.line,
            "term": self.term,
            "text": self.text.strip(),
        }


def scan(
    files: dict[str, list[tuple[int, str]]],
    pattern: re.Pattern[str] | None,
    rules: ExclusionRules,
) -> list[Finding]:
    """Scan {path: [(line_no, text)]} and return findings in file order."""
    if pattern is None:
        return []
    findings: list[Finding] = []
    for path, lines in files.items():
        for line_no, text in lines:
            if is_excluded_line(text, path, rules):
                continue
            allowed = allowed_terms(text)
            if allowed is not None and not allowed:
                continue  # bare pragma: whole line waived
            for match in pattern.finditer(text):
                term = match.group(1)
                if allowed is not None and term.lower() in allowed:
                    continue
                findings.append(Finding(path, line_no, term, text))
    return findings
